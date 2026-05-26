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
module: srlinux_l3_interface
short_description: Configure L3 routed interfaces on Nokia SR Linux
description:
  - Create, update, or delete L3 routed interfaces and subinterfaces on Nokia SR Linux.
  - Handles physical properties, subinterface indexes, IP address assignments, and VRF bindings.
options:
  config:
    description:
      - List of target L3 interface configuration objects to batch process.
    type: list
    elements: dict
    suboptions:
      interface:
        description:
          - Complete interface or subinterface name string (e.g., ethernet-1/1 or ethernet-1/1.100).
        type: str
        required: true
      admin_state:
        description:
          - Administrative state control configuration.
        type: str
        choices: [enable, disable]
      description:
        description:
          - Custom descriptive text string attached to the interface.
        type: str
      ipv4_address:
        description:
          - IPv4 address and subnet mask prefix string defined in CIDR format.
        type: str
      ipv6_address:
        description:
          - IPv6 address and subnet mask prefix string defined in CIDR format.
        type: str
      network_instance:
        description:
          - Target network-instance (ip-vrf name) where this subinterface should be explicitly bound.
        type: str
        required: false
  state:
    description:
      - Control whether targeted configurations should be provisioned (merged) or destroyed (deleted).
    type: str
    choices: [merged, deleted]
    default: merged
author:
  - Uzma Saman (@NetOpsChic)
'''

EXAMPLES = r'''
- name: Batch provision explicit L3 interfaces and cross-bind to a VRF
  netopschic.srlinux.srlinux_l3_interface:
    config:
      - interface: "ethernet-1/1.10"
        admin_state: "enable"
        ipv4_address: "10.10.10.1/30"
        description: "Core Uplink to Spine01"
        network_instance: "VRF-PROD-TEST"
    state: merged

- name: Securely tear down a subinterface and remove its VRF binding context
  netopschic.srlinux.srlinux_l3_interface:
    config:
      - interface: "ethernet-1/1.10"
    state: deleted
'''

RETURN = r'''
results:
  description: Evaluation statuses indicating transaction histories showing before and after parameter values.
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

def map_config_to_obj(client, want_ifaces):
    get_commands = [
        {"path": "/interface[name=*]", "datastore": "running"},
        {"path": "/network-instance[name=*]/interface[name=*]", "datastore": "running"}
    ]
    get_rpc = build_rpc("get", get_commands, rpcID())
    get_response = client.post(payload=json.dumps(get_rpc))
    
    have_ifaces = {}
    if get_response.get('error'):
        return have_ifaces
        
    result_list = get_response.get("result", [])

    for result in result_list:
        iface_key = next((k for k in result.keys() if "interface" in k and "network-instance" not in k), None)
        
        if iface_key:
            iface_list = result.get(iface_key, [])
            for iface_data in iface_list:
                iface_name = iface_data.get("name")
                phys_description = iface_data.get("description")

                for sub_iface_data in iface_data.get("subinterface", []):
                    index = sub_iface_data.get("index")
                    full_iface_name = f"{iface_name}.{index}"
                    
                    if iface_name in want_ifaces:
                        v4_list = sub_iface_data.get("ipv4", {}).get("address", [])
                        v4_address = v4_list[0].get("ip-prefix") if v4_list else None

                        v6_list = sub_iface_data.get("ipv6", {}).get("address", [])
                        v6_address = v6_list[0].get("ip-prefix") if v6_list else None

                        raw_type = sub_iface_data.get("type")
                        clean_type = raw_type.split(":")[-1] if raw_type else None

                        have_ifaces[full_iface_name] = {
                            "name": full_iface_name,
                            "description": phys_description,
                            "admin_state": sub_iface_data.get("admin-state"),
                            "index": index,
                            "ipv4_address": v4_address,
                            "ipv6_address": v6_address,
                            "type": clean_type
                        }

    for result in result_list:
        ni_key = next((k for k in result.keys() if "network-instance" in k), None)
        
        if ni_key:
            ni_list = result.get(ni_key, [])
            for ni_data in ni_list:
                vrf_name = ni_data.get("name")
                
                bind_list = ni_data.get("interface", [])
                for bind_data in bind_list:
                    full_iface_name = bind_data.get("name")
                    
                    if full_iface_name in have_ifaces:
                        have_ifaces[full_iface_name]["network_instance"] = vrf_name

    return have_ifaces
         
def main():
    argument_spec = dict(
        config= dict(type='list', elements='dict', options=dict(
            interface=dict(type='str', required=True),
            admin_state=dict(type='str', choices=['enable', 'disable']),
            description=dict(type='str'),
            ipv4_address=dict(type='str'),
            ipv6_address=dict(type='str'),
            network_instance=dict(type='str', required=False)
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

    want_ifaces_name = []
    for desired in config:
        full_iface = desired.get("interface", "")
        phys_name = full_iface.split(".")[0] if "." in full_iface else full_iface
        if phys_name not in want_ifaces_name:
            want_ifaces_name.append(phys_name)

    have_ifaces = map_config_to_obj(client, want_ifaces_name) 

    change = False
    set_commands = []
    results = []

    for desired in config:
         full_ifaces_name = desired.get("interface")
         if "." in full_ifaces_name:
             ifaces_name, s_ifaces_name = full_ifaces_name.split(".")
         else:
             ifaces_name = full_ifaces_name
             s_ifaces_name = "0"
             full_ifaces_name = f"{ifaces_name}.{s_ifaces_name}"

         have = have_ifaces.get(full_ifaces_name) or {}

         ifaces_result = {
            "name": full_ifaces_name,
            "before": have,
            "after": {}
        }
        
         if state == "merged":
            phys_payload = {}
            sub_payload = {}

            if desired.get("description") and desired.get("description") != have.get("description"):
                 phys_payload["description"] = desired.get("description")

            if desired.get("ipv4_address") and desired.get("ipv4_address") != have.get("ipv4_address"):
               sub_payload["ipv4"] = {
                   "address": [{"ip-prefix": desired.get("ipv4_address")}]
               }
            
            if desired.get("ipv6_address") and desired.get("ipv6_address") != have.get("ipv6_address"):
               sub_payload["ipv6"] = {
                   "address": [{"ip-prefix": desired.get("ipv6_address")}]
               }
               
            if desired.get("admin_state") and desired.get("admin_state") != have.get("admin_state"):
                 phys_payload["admin-state"] = desired.get("admin_state")
                 sub_payload["admin-state"] = desired.get("admin_state")
            
            if have.get("type") != "routed":  
               sub_payload["type"] = "routed"

            # FIX: Pushing the physical interface changes
            if phys_payload:
                change = True
                set_commands.append({
                    "path": f"/interface[name={ifaces_name}]",
                    "action": "update",
                    "value": phys_payload
                })
                
            # FIX: Pushing the subinterface changes
            if sub_payload:
                change = True
                set_commands.append({
                    "path": f"/interface[name={ifaces_name}]/subinterface[index={s_ifaces_name}]",
                    "action": "update",
                    "value": sub_payload
                })

            # FIX: A single, clean check for Network Instance binding
            ni_name = desired.get("network_instance")
            if ni_name and ni_name != have.get("network_instance"):
               change = True
               set_commands.append({
                    "path": f"/network-instance[name={ni_name}]/interface[name={full_ifaces_name}]",
                    "action": "update",
                    "value": {}
                })
            
            after_normalized = have.copy()
            after_normalized.update(desired)
            if "admin-state" in after_normalized:
                after_normalized.pop("admin-state")
            ifaces_result["after"] = after_normalized
   
         elif state == "deleted":
             if have:
                change = True
                ni_name = have.get("network_instance")

                if ni_name:
                  set_commands.append({
                      "path": f"/network-instance[name={ni_name}]/interface[name={full_ifaces_name}]",
                      "action": "delete"
                  })
                set_commands.append({
                    "path": f"/interface[name={ifaces_name}]/subinterface[index={s_ifaces_name}]",
                    "action": "delete"
                })
             ifaces_result["after"] = None
         results.append(ifaces_result)
           
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