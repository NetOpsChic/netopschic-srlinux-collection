#!/usr/bin/python
# Copyright 2023 Nokia
# Licensed under the BSD 3-Clause License.

from __future__ import absolute_import, division, print_function
import json
import pprint

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.netopschic.srlinux.plugins.module_utils.const import JSON_RPC_VERSION
from ansible_collections.netopschic.srlinux.plugins.module_utils.srlinux import (
    JSONRPCClient,
    rpcID,
)

__metaclass__ = type

DOCUMENTATION = r'''
---
module: srlinux_routing_policy
short_description: Configure routing policies on Nokia SR Linux
description:
  - Configure routing policies, prefix sets, and policy statements explicitly on Nokia SR Linux.
options:
  config:
    description:
      - Structured dictionary defining the targeted prefix sets and routing policies.
    type: dict
    required: true
    suboptions:
      prefix_sets:
        description: List of prefix sets used for route matching.
        type: list
        elements: dict
        suboptions:
          name:
            description: Unique name identifying the prefix set.
            type: str
            required: true
          prefixes:
            description: List of IP prefixes and mask rules belonging to this set.
            type: list
            elements: dict
            suboptions:
              ip_prefix:
                description: The IPv4 or IPv6 prefix string in CIDR notation.
                type: str
                required: true
              mask_length_range:
                description: Mask matching length modifier constraint (e.g., exact, 24..32).
                type: str
                required: true
      policies:
        description: List of routing policies containing statements and match/action definitions.
        type: list
        elements: dict
        suboptions:
          name:
            description: Unique name identifying the routing policy.
            type: str
            required: true
          statements:
            description: Ordered list of policy statements evaluated sequentially.
            type: list
            elements: dict
            suboptions:
              name:
                description: Unique name identifying the individual statement block.
                type: str
                required: true
              match:
                description: Condition criteria matrix for route matching.
                type: dict
                suboptions:
                  prefix_set:
                    description: Reference name of a pre-defined prefix set.
                    type: str
              action:
                description: Result actions applied if match criteria evaluate to true.
                type: dict
                suboptions:
                  policy_result:
                    description: The final verdict outcome for matching routes (e.g., accept, reject).
                    type: str
                    choices: [accept, reject]
  state:
    description: Control whether the configurations should be provisioned (merged) or destroyed (deleted).
    type: str
    choices: [merged, deleted]
    default: merged
author:
  - Uzma Saman (@NetOpsChic)
'''

EXAMPLES = r'''
- name: Apply explicit prefix sets and route export policies
  netopschic.srlinux.srlinux_routing_policy:
    config:
      prefix_sets:
        - name: "local-subnets"
          prefixes:
            - ip_prefix: "10.10.10.0/30"
              mask_length_range: "exact"
      policies:
        - name: "export-local"
          statements:
            - name: "match-local"
              match:
                prefix_set: "local-subnets"
              action:
                policy_result: "accept"
    state: merged

- name: Purge targeted routing policies and prefix sets
  netopschic.srlinux.srlinux_routing_policy:
    config:
      prefix_sets:
        - name: "local-subnets"
      policies:
        - name: "export-local"
    state: deleted
'''

RETURN = r'''
results:
  description: Operational status showing evaluated transaction changes before and after processing.
  type: list
  elements: dict
  returned: always
'''

def build_rpc(method, commands, req_id):
    return {
        "jsonrpc": JSON_RPC_VERSION,
        "method": method,
        "params": {"commands": commands},
        "id": req_id
    }

def strip_namespaces(data):
    if isinstance(data, dict):
        return {k.split(':')[-1]: strip_namespaces(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [strip_namespaces(item) for item in data]
    else:
        return data

def is_diff(intent, current):
    """Deep normalized comparison using sorted JSON to ignore key order."""
    if current is None:
        return True
    
    # Dump both dictionaries to strings with sorted keys to guarantee identical format
    return json.dumps(intent, sort_keys=True) != json.dumps(current, sort_keys=True)

def map_config_to_obj(client):
    get_commands = [{"path": "/routing-policy", "datastore": "running"}]
    get_rpc = build_rpc("get", get_commands, rpcID())
    get_response = client.post(payload=json.dumps(get_rpc))
    
    have_ps, have_prefixes, have_policies, have_statements = {}, {}, {}, {}

    if get_response.get('error'):
        return have_ps, have_prefixes, have_policies, have_statements
        
    clean_result = strip_namespaces(get_response.get("result", []))

    for result in clean_result:
        # Prefix Sets
        for ps in result.get("prefix-set", []):
            ps_name = ps.get("name")
            have_ps[ps_name] = True
            for pfx in ps.get("prefix", []):
                ip = pfx.get("ip-prefix")
                mask = pfx.get("mask-length-range", "exact")
                have_prefixes[f"{ps_name}::{ip}::{mask}"] = True
            
        # Policies
        for pol in result.get("policy", []):
            pol_name = pol.get("name")
            have_policies[pol_name] = True
            for stmt in pol.get("statement", []):
                stmt_name = stmt.get("name")
                
                # FIX: Only add match/action to our parsed dictionary if they actually exist
                # This prevents injecting empty `{}` which breaks idempotency comparisons
                parsed_stmt = {}
                if stmt.get("match"):
                    parsed_stmt["match"] = stmt["match"]
                if stmt.get("action"):
                    parsed_stmt["action"] = stmt["action"]
                
                have_statements[f"{pol_name}::{stmt_name}"] = parsed_stmt
                
    return have_ps, have_prefixes, have_policies, have_statements

def main():
    module = AnsibleModule(
        argument_spec=dict(
            config=dict(type='dict', required=True),
            state=dict(type='str', choices=['merged', 'deleted'], default='merged') 
        ),
        supports_check_mode=True
    )
    client = JSONRPCClient(module)
    config = module.params.get("config") or {}
    state = module.params["state"]
    have_ps, have_prefixes, have_policies, have_statements = map_config_to_obj(client)

    change, set_commands = False, []

    if state == "deleted":
        for pol in config.get("policies", []):
            if pol.get("name") in have_policies:
                change = True
                set_commands.append({"path": f"/routing-policy/policy[name={pol['name']}]", "action": "delete"})
        for ps in config.get("prefix_sets", []):
            if ps.get("name") in have_ps:
                change = True
                set_commands.append({"path": f"/routing-policy/prefix-set[name={ps['name']}]", "action": "delete"})
    
    elif state == "merged":
        for ps in config.get("prefix_sets", []):
            ps_name = ps.get("name")
            if ps_name not in have_ps:
                change = True
                set_commands.append({"path": f"/routing-policy/prefix-set[name={ps_name}]", "action": "update", "value": {"name": ps_name}})
            for pfx in ps.get("prefixes", []):
                ip, mask = pfx.get("ip_prefix"), pfx.get("mask_length_range", "exact")
                if f"{ps_name}::{ip}::{mask}" not in have_prefixes:
                    change = True
                    set_commands.append({"path": f"/routing-policy/prefix-set[name={ps_name}]/prefix[ip-prefix={ip}][mask-length-range={mask}]", "action": "update", "value": {"ip-prefix": ip, "mask-length-range": mask}})
        
        for pol in config.get("policies", []):
            pol_name = pol.get("name")
            if pol_name not in have_policies:
                change = True
                set_commands.append({"path": f"/routing-policy/policy[name={pol_name}]", "action": "update", "value": {}})

            for stmt in pol.get("statements", []):
                s_name = stmt.get("name")
                stmt_payload = {}
                
                # Only build the match key if it exists in the YAML
                if "match" in stmt:
                    stmt_payload["match"] = {"prefix": {"prefix-set": stmt["match"]["prefix_set"]}}
                if "action" in stmt:
                    stmt_payload["action"] = {"policy-result": stmt["action"]["policy_result"]}
                
                if f"{pol_name}::{s_name}" not in have_statements or is_diff(stmt_payload, have_statements.get(f"{pol_name}::{s_name}")):
                    change = True
                    set_commands.append({"path": f"/routing-policy/policy[name={pol_name}]/statement[name={s_name}]", "action": "update", "value": stmt_payload})

    if change and not module.check_mode and set_commands:
        response = client.post(payload=json.dumps(build_rpc("set", set_commands, rpcID())))
        if response.get("error"):
            module.fail_json(msg="Server error", response=pprint.pformat(response))
    
    module.exit_json(changed=change, msg="Successfully processed routing policy intent")

if __name__ == "__main__":
    main()