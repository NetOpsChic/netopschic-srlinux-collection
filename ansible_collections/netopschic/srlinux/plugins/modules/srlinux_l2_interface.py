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
module: srlinux_l2_interface
short_description: Configure L2 interfaces (trunk or access) on Nokia SR Linux
description:
  - Create, update, or delete L2 bridged interfaces and subinterfaces on Nokia SR Linux.
  - Handles physical properties, subinterface indexes, single-tagged VLAN encapsulations, and mac-vrf context bindings.
options:
  config:
    description:
      - List of Layer 2 interface configurations to batch process.
    type: list
    elements: dict
    suboptions:
      interface:
        description:
          - Complete interface or subinterface name string (e.g., ethernet-1/2 or ethernet-1/2.20).
        type: str
        required: true
      admin_state:
        description:
          - Administrative state control configuration.
        type: str
        choices: [enable, disable]
      description:
        description:
          - Custom descriptive text string attached to the physical interface layer.
        type: str
      trunk_vlans:
        description:
          - List of explicit VLAN IDs allowed across trunk-mode subinterfaces (sets encapsulation to any).
        type: list
        elements: int
      vlan_id:
        description:
          - Specific VLAN ID encapsulation value for the subinterface.
        type: int
      access_vlan:
        description:
          - Alternative configuration key defining the targeted untagged or access VLAN ID.
        type: int
      network_instance:
        description:
          - Target Layer 2 network-instance (mac-vrf name) where this subinterface should be bound.
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
- name: Batch provision explicit L2 access subinterfaces into a mac-vrf broadcast domain
  netopschic.srlinux.srlinux_l2_interface:
    config:
      - interface: "ethernet-1/2.20"
        admin_state: "enable"
        access_vlan: 20
        description: "Access Port Link to Host-01"
        network_instance: "MAC-VRF-PROD"
    state: merged

- name: Securely tear down an L2 subinterface mapping and remove its switching association
  netopschic.srlinux.srlinux_l2_interface:
    config:
      - interface: "ethernet-1/2.20"
    state: deleted
'''

RETURN = r'''
results:
  description: Operational status showing evaluated transaction changes before and after execution tuning.
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
          path_returned = result.get("path", "")
          data_key = next((k for k in result.keys() if "interface" in k), None)
          if not data_key: continue
          iface_list = result.get(data_key, [])

          if "network-instance" not in data_key:    
            for iface_data in iface_list:
                iface_name = iface_data.get("name")
                s_iface_name = iface_data.get("subinterface", [])
                for sub_iface_data in s_iface_name:
                     index = sub_iface_data.get("index")
                     full_interface_name = f"{iface_name}.{index}"
                     if iface_name in want_ifaces:
                          have_ifaces[full_interface_name] = {
                              "name": iface_name,
                              "index": index,
                              "admin_state": iface_data.get("admin-state"),
                              "description": iface_data.get("description"),
                              "vlan_tagging": iface_data.get("vlan-tagging"),
                              "type": sub_iface_data.get("type"),
                              "vlan_id": sub_iface_data.get("vlan", {}).get("encap", {}).get("single-tagged", {}).get("vlan-id")
                          }
          else:
              vrf_name = path_returned.split("name=")[1].split("]")[0].replace('"', '').replace("'", "")
              for ifaces_data in iface_list:
                  full_interface_name = ifaces_data.get("name")
                  if full_interface_name in have_ifaces:
                      have_ifaces[full_interface_name]["network_instance"] = vrf_name       
     return have_ifaces
         
def main():
    argument_spec = dict(
        config= dict(type='list', elements='dict', options=dict(
            interface=dict(type='str', required=True),
            admin_state=dict(type='str', choices=['enable', 'disable']),
            description=dict(type='str'),
            trunk_vlans=dict(type='list', elements='int'),
            access_vlan=dict(type='int'),
            vlan_id=dict(type='int'),
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
             ifaces_name, str_index = full_ifaces_name.split(".")
             s_ifaces_name = int(str_index)
         else:
             ifaces_name = full_ifaces_name
             s_ifaces_name = 0
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
            ni_payload = {}
            have_vlan_id = have.get("vlan_id")

            if desired.get("description") and desired.get("description") != have.get("description"):
                 phys_payload["description"] = desired.get("description")

            if have.get("vlan_tagging") != True:
               phys_payload["vlan-tagging"] = True 
            
            # Support both vlan_id and access_vlan from playbook input
            target_vlan = desired.get("vlan_id") or desired.get("access_vlan")

            if desired.get("trunk_vlans"):
                if have_vlan_id != "any":
                    sub_payload["vlan"] = {"encap": {"single-tagged": {"vlan-id": "any"}}}
            elif target_vlan is not None:
                if have_vlan_id != target_vlan:
                    sub_payload["vlan"] = {"encap": {"single-tagged": {"vlan-id": target_vlan}}}

            if desired.get("admin_state") and desired.get("admin_state") != have.get("admin_state"):
                 phys_payload["admin-state"] = desired.get("admin_state")
                 sub_payload["admin-state"] = desired.get("admin_state")

            if have.get("type") != "bridged":  
               sub_payload["type"] = "bridged"

            ni_name = desired.get("network_instance")
            if ni_name is not None and ni_name != have.get("network_instance"):
               change = True
               set_commands.append({
                    "path": f"/network-instance[name={ni_name}]/interface[name={full_ifaces_name}]",
                    "action": "update",
                    "value": {}
                })
            if sub_payload:
                change = True
                set_commands.append({
                    "path": f"/interface[name={ifaces_name}]/subinterface[index={s_ifaces_name}]",
                    "action": "update",
                    "value": sub_payload
                })

            if ni_payload is not None and ni_name and ni_name != have.get("network_instance"):
               change = True
               set_commands.append({
                    "path": f"/network-instance[name={ni_name}]/interface[name={full_ifaces_name}]",
                    "action": "update",
                    "value": ni_payload
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