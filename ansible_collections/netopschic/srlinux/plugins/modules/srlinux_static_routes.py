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
module: srlinux_static_routes
short_description: Configure static routes (and next-hop-groups) on Nokia SR Linux
description:
  - Configure next-hop-groups and static routes explicitly using batch list execution.
options:
  config:
    description:
      - List containing network_instance, next_hop_groups, and routes block configurations.
    type: list
    elements: dict
    suboptions:
      network_instance:
        description: Network-instance name (VRF/Routing context).
        type: str
        required: true
      next_hop_groups:
        description: List of explicit next-hop-groups to configure.
        type: list
        elements: dict
        suboptions:
          name:
            description: Unique name identifying the next-hop-group.
            type: str
            required: true
          admin_state:
            description: Administrative state of the next-hop-group.
            type: str
            choices: [enable, disable]
          nexthops:
            description: List of explicit next-hop pathways belonging to this group.
            type: list
            elements: dict
            suboptions:
              index:
                description: Numerical identifier/index for the specific next-hop path.
                type: int
                required: true
              ip_address:
                description: Gateway target IP address for the next-hop path.
                type: str
                required: true
      routes:
        description: List of static routes to configure.
        type: list
        elements: dict
        suboptions:
          prefix:
            description: Target IP prefix in CIDR format (v4 or v6).
            type: str
            required: true
          admin_state:
            description: Administrative state of the static route.
            type: str
            choices: [enable, disable]
          metric:
            description: Metric value for the static route.
            type: int
          preference:
            description: Administrative distance/preference value.
            type: int
          next_hop_group:
            description: The name of the explicit next-hop-group assigned to this prefix.
            type: str
          description:
            description: Optional custom text description for the static route.
            type: str
          blackhole:
            description: Flag to turn this route into a silent discard/blackhole drop entry.
            type: bool
  state:
    description: Control whether configuration targets should be provisioned (merged) or deleted (deleted).
    type: str
    choices: [merged, deleted]
    default: merged
author:
  - Uzma Saman (@NetOpsChic)
'''

EXAMPLES = r'''
- name: Explicitly apply a batch of next-hop groups and static routes
  netopschic.srlinux.srlinux_static_routes:
    config:
      - network_instance: "VRF-PROD-TEST"
        next_hop_groups:
          - name: "NHG-SPINE1"
            admin_state: "enable"
            nexthops:
              - index: 0
                ip_address: "10.10.10.2"
        routes:
          - prefix: "192.168.100.0/24"
            admin_state: "enable"
            next_hop_group: "NHG-SPINE1"
            description: "Production App Subnet"
    state: merged

- name: Teardown specific routes explicitly from a network-instance
  netopschic.srlinux.srlinux_static_routes:
    config:
      - network_instance: "VRF-PROD-TEST"
        next_hop_groups:
          - name: "NHG-SPINE1"
        routes:
          - prefix: "192.168.100.0/24"
    state: deleted
'''

RETURN = r'''
results:
  description: Per-route-block summary objects showing configuration states before and after processing.
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

def map_config_to_obj(client, want_routes, want_nhgs):
    get_commands = [
        {"path": "/network-instance[name=*]/static-routes/route[prefix=*]", "datastore": "running"},
        {"path": "/network-instance[name=*]/next-hop-groups/group[name=*]", "datastore": "running"}
    ]
    get_rpc = build_rpc("get", get_commands, rpcID())
    get_response = client.post(payload=json.dumps(get_rpc))
    
    have_routes = {}
    have_nhgs = {}
    
    if get_response.get('error'):
        return have_routes, have_nhgs
        
    result_list = get_response.get("result", [])

    for result in result_list:
        ni_key = next((k for k in result.keys() if "network-instance" in k), None)
        if not ni_key:
            continue
            
        ni_list = result.get(ni_key, [])
        for ni_data in ni_list:
            vrf_name = ni_data.get("name")
            
            # Bulletproof Route Parsing
            static_routes_container = ni_data.get("static-routes", ni_data)
            if isinstance(static_routes_container, list):
                static_routes_container = static_routes_container[0] if static_routes_container else {}
                
            sr_key = next((k for k in static_routes_container.keys() if "static-routes" in k), None)
            sr_data = static_routes_container.get(sr_key, {}) if sr_key else static_routes_container
            
            if isinstance(sr_data, list):
                sr_data = sr_data[0] if sr_data else {}
                
            route_list = sr_data.get("route", []) if isinstance(sr_data, dict) else []

            for route_data in route_list:
                prefix = route_data.get("prefix")
                route_key = f"{vrf_name}::{prefix}"
                if route_key in want_routes:
                    have_routes[route_key] = {
                        "network_instance": vrf_name,
                        "prefix": prefix,
                        "admin_state": route_data.get("admin-state"),
                        "metric": route_data.get("metric"),
                        "preference": route_data.get("preference"),
                        "next_hop_group": route_data.get("next-hop-group")
                    }

            # Bulletproof Next-Hop-Group Parsing
            nhg_container = ni_data.get("next-hop-groups", ni_data)
            if isinstance(nhg_container, list):
                nhg_container = nhg_container[0] if nhg_container else {}

            nhg_key = next((k for k in nhg_container.keys() if "next-hop-groups" in k), None)
            nhg_data = nhg_container.get(nhg_key, {}) if nhg_key else nhg_container
            
            if isinstance(nhg_data, list):
                nhg_data = nhg_data[0] if nhg_data else {}

            group_list = nhg_data.get("group", []) if isinstance(nhg_data, dict) else []

            for group_data in group_list:
                nhg_name = group_data.get("name")
                nhg_key_str = f"{vrf_name}::{nhg_name}"
                
                if nhg_key_str in want_nhgs:
                    nexthops_raw = group_data.get("nexthop", [])
                    parsed_nexthops = []
                    for nh in nexthops_raw:
                        parsed_nexthops.append({
                            "index": nh.get("index"),
                            "ip_address": nh.get("ip-address")
                        })
                        
                    have_nhgs[nhg_key_str] = {
                        "name": nhg_name,
                        "admin_state": group_data.get("admin-state"),
                        "nexthops": parsed_nexthops
                    }

    return have_routes, have_nhgs
         
def main():
    argument_spec = dict(
        config=dict(type='list', elements='dict', options=dict(
            network_instance=dict(type='str', required=True),
            next_hop_groups=dict(type='list', elements='dict', options=dict(
                name=dict(type='str', required=True),
                admin_state=dict(type='str', choices=['enable', 'disable']),
                nexthops=dict(type='list', elements='dict', options=dict(
                    index=dict(type='int', required=True),
                    ip_address=dict(type='str', required=True)
                ))
            )),
            routes=dict(type='list', elements='dict', options=dict(
                prefix=dict(type='str', required=True),
                admin_state=dict(type='str', choices=['enable', 'disable']),
                metric=dict(type='int'),
                preference=dict(type='int'),
                next_hop_group=dict(type='str'),
                description=dict(type='str'),
                blackhole=dict(type='bool')
            ))
        )),
        state=dict(type='str', choices=['merged', 'deleted'], default='merged') 
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )
    client = JSONRPCClient(module)

    config = module.params.get("config") or []
    state = module.params["state"]
    
    want_nhgs = []
    want_routes = []
    for vrf_block in config:
        vrf_name = vrf_block.get("network_instance")
        nhg_intent = vrf_block.get("next_hop_groups") or []
        routes_intent = vrf_block.get("routes") or []
        
        want_nhgs.extend([f"{vrf_name}::{n.get('name')}" for n in nhg_intent])
        want_routes.extend([f"{vrf_name}::{r.get('prefix')}" for r in routes_intent])
    
    have_routes, have_nhgs = map_config_to_obj(client, want_routes, want_nhgs) 

    change = False
    nhg_commands = []
    route_commands = []

    for vrf_block in config:
        vrf_name = vrf_block.get("network_instance")
        nhg_intent = vrf_block.get("next_hop_groups") or []
        routes_intent = vrf_block.get("routes") or []

        for desired_nhg in nhg_intent:
            nhg_name = desired_nhg.get("name")
            nhg_key = f"{vrf_name}::{nhg_name}"
            have = have_nhgs.get(nhg_key) or {}

            if state == "merged":
                nhg_payload = {}
                if desired_nhg.get("admin_state") and desired_nhg.get("admin_state") != have.get("admin_state"):
                    nhg_payload["admin-state"] = desired_nhg.get("admin_state")
                    
                if desired_nhg.get("nexthops") and desired_nhg.get("nexthops") != have.get("nexthops"):
                    formatted_nexthops = []
                    for nh in desired_nhg.get("nexthops"):
                        formatted_nexthops.append({
                            "index": nh.get("index"),
                            "ip-address": nh.get("ip_address")
                        })
                    nhg_payload["nexthop"] = formatted_nexthops
                    
                if nhg_payload or not have:
                    change = True
                    nhg_commands.append({
                        "path": f"/network-instance[name={vrf_name}]/next-hop-groups/group[name={nhg_name}]",
                        "action": "update",
                        "value": nhg_payload
                    })
                    
            elif state == "deleted" and have:
                change = True
                nhg_commands.append({
                    "path": f"/network-instance[name={vrf_name}]/next-hop-groups/group[name={nhg_name}]",
                    "action": "delete"
                })
                
        for desired_route in routes_intent:
            prefix = desired_route.get("prefix")
            route_key = f"{vrf_name}::{prefix}"
            have = have_routes.get(route_key) or {}

            if state == "merged":
                route_payload = {}
                if desired_route.get("next_hop_group") and desired_route.get("next_hop_group") != have.get("next_hop_group"):
                    route_payload["next-hop-group"] = desired_route.get("next_hop_group")
                if desired_route.get("admin_state") and desired_route.get("admin_state") != have.get("admin_state"):
                    route_payload["admin-state"] = desired_route.get("admin_state")
                if desired_route.get("metric") is not None and desired_route.get("metric") != have.get("metric"):
                    route_payload["metric"] = desired_route.get("metric")
                if desired_route.get("preference") is not None and desired_route.get("preference") != have.get("preference"):
                    route_payload["preference"] = desired_route.get("preference")

                if route_payload or not have:
                    change = True
                    route_commands.append({
                        "path": f"/network-instance[name={vrf_name}]/static-routes/route[prefix={prefix}]",
                        "action": "update",
                        "value": route_payload
                    })
                    
            elif state == "deleted" and have:
                change = True
                route_commands.append({
                    "path": f"/network-instance[name={vrf_name}]/static-routes/route[prefix={prefix}]",
                    "action": "delete"
                })

    set_commands = []
    if state == "merged":
        set_commands.extend(nhg_commands)
        set_commands.extend(route_commands)
    else:
        set_commands.extend(route_commands)
        set_commands.extend(nhg_commands)

    if change and not module.check_mode:
        set_rpc = build_rpc("set", set_commands, rpcID())
        response = client.post(payload=json.dumps(set_rpc))

        if response.get("error"):
            module.fail_json(
                msg="Server error (BATCH)",
                response=pprint.pformat(response)
            )  
            
    module.exit_json(changed=change, msg="Successfully processed intent explicitly")

if __name__ == "__main__":
    main()