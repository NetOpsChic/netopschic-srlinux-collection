#!/usr/bin/python
# Copyright 2023 Nokia
# Licensed under the BSD 3-Clause License.
# SPDX-License-Identifier: BSD-3-Clause

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
module: srlinux_network_instance
short_description: Manage network-instances (VRF, bridge-table) on Nokia SR Linux
description:
  - Create, update, or delete network-instances (L2 mac-vrf, L3 ip-vrf, default) on Nokia SR Linux devices.
options:
  config:
    description:
      - List of network-instances to batch configure.
    type: list
    elements: dict
    suboptions:
      name:
        description: Network-instance name.
        type: str
        required: true
      type:
        description: Network-instance type like ip-vrf (L3), mac-vrf (L2), or default.
        type: str
        choices: [ip-vrf, mac-vrf, default]
        required: true
      description:
        description: Custom description string for the network-instance.
        type: str
      admin_state:
        description: Administrative state configuration.
        type: str
        choices: [enable, disable]
      router_id:
        description: The system router ID for the network instance (typically an IPv4 address).
        type: str
      interfaces:
        description: List of physical or subinterfaces to explicitly bind to this network instance.
        type: list
        elements: str
  state:
    description: Control whether the targeted configurations should be provisioned (merged) or destroyed (deleted).
    type: str
    choices: [merged, deleted]
    default: merged
author:
  - Uzma Saman (@NetOpsChic)
'''

EXAMPLES = r'''
- name: Ensure NIs exist
  netopschic.srlinux.srlinux_network_instance:
    config:
      - name: lan-vrf
        type: mac-vrf
        description: L2 VRF
      - name: blue
        type: ip-vrf
        description: L3 VRF
        interfaces:
          - ethernet-1/1.10
      - name: default
        type: default
        description: Default NI
    state: merged

- name: Remove a network-instance
  netopschic.srlinux.srlinux_network_instance:
    config:
      - name: old-vrf
        type: ip-vrf
    state: deleted
'''

RETURN = r'''
results:
  description: Per-network-instance configuration state summaries showing before/after structural objects.
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

def map_config_to_obj(client, want_vrfs): 
    get_commands = [{"path": "/network-instance", "datastore": "running"}]
    get_rpc = build_rpc("get", get_commands, rpcID())
    get_response = client.post(payload=json.dumps(get_rpc))
    
    have_vrfs = {}
    if get_response.get("error"):
        return have_vrfs
    
    result_list = get_response.get("result", [])

    for item in result_list:
        # Get the list nested under the namespace key
        data_key = next((k for k in item.keys() if "network-instance" in k), None)
        if not data_key: continue
        
        vrf_list = item.get(data_key, [])
        for vrf_data in vrf_list:
            vrf_name = vrf_data.get("name")
            
            if vrf_name in want_vrfs:
                # Strip namespace from type
                raw_type = vrf_data.get("type", "")
                clean_type = raw_type.split(':')[-1] if ":" in raw_type else raw_type

                have_vrfs[vrf_name] = {
                    "name": vrf_name,
                    "type": clean_type,
                    "admin_state": vrf_data.get("admin-state"),
                    "description": vrf_data.get("description"),
                    "router_id": vrf_data.get("router-id")
                }
    return have_vrfs

def main():
    argument_spec = dict(
        config=dict(type='list', elements='dict', required=False, options=dict(
            name=dict(type='str', required=True), 
            type=dict(type='str', choices=['ip-vrf', 'mac-vrf', 'default']),
            description=dict(type='str'),
            admin_state=dict(type='str', choices=['enable', 'disable']),
            router_id=dict(type='str'),
            interfaces=dict(type='list', elements='str')
        )),
        state=dict(type='str', choices=['merged', 'deleted'], default='merged'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
     )
    client = JSONRPCClient(module)

    # gather the intent which is in playbook yaml
    config = module.params.get("config") or []
    state = module.params["state"]

    # Get the current have state of network instances (VRFs)
    want_vrfs_name = [vrf.get("name") for vrf in config]
    have_vrfs = map_config_to_obj(client, want_vrfs_name)

    # Setup tracking variables
    change = False
    set_commands = []
    results = []

    # The Batch Processor Loop
    for desired in config:
        vrf_name = desired.get("name")
        # Grab the current state of THIS specific VRF (or an empty dict if it's new)
        have = have_vrfs.get(vrf_name) or {}

        PATH = f"/network-instance[name={vrf_name}]"
        vrf_result = {
            "name": vrf_name,
            "before": have,
            "after": {}
        }

        if state == "merged":
            payload = {}
            # Check every variable. If the user provided it AND it's different than the router, add it

            if desired.get("type") and desired.get("type") != have.get("type"):
                payload["type"] = desired["type"]
            
            if desired.get("description") and desired.get("description") != have.get("description"):
                payload["description"] = desired["description"]
            
            if desired.get("admin_state") and desired.get("admin_state") != have.get("admin_state"):
                payload["admin-state"] = desired.get("admin_state")
            
            if desired.get("router_id") and desired.get("router_id") != have.get("router_id"):
                payload["router-id"] = desired["router_id"]
            
            # If there is anything inside update_payload, OR the VRF doesn't exist at all, we must create/update it
            if payload or not have:
                change = True
                set_commands.append({
                    "path": PATH,
                    "action": "update",
                    "value": payload
                })
            if desired.get("interfaces"):
                have_interfaces = have.get("interfaces", [])
                for intf in desired["interfaces"]:
                    if intf not in have_interfaces:
                        change = True
                        set_commands.append({
                            "path": f"{PATH}/interface[name={intf}]",
                            "action": "update",
                            "value": {} 
                        })

            vrf_result["after"] = dict(have, **payload) if have else payload
            vrf_result["after"] = dict(have, **payload) if have else payload

        elif state == "deleted" and have:
            if have:
                change = True
                set_commands.append({
                    "path": PATH,
                    "action": "delete"
                })
            vrf_result["after"] = None
        
        results.append(vrf_result)

        
    # Send the entire batch in a single transaction
    if change and not module.check_mode:
        set_rpc = build_rpc("set", set_commands, rpcID())
        response = client.post(payload=json.dumps(set_rpc))

        if response.get("error"):
            module.fail_json(
                msg="Server error (BATCH)",
                response=pprint.pformat(response)
            )   

    module.exit_json(changed=change, results=results)

if __name__ == "__main__":
    main() 