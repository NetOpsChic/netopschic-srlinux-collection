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
module: srlinux_bgp
short_description: Configure BGP on Nokia SR Linux
description:
  - Configure BGP global parameters, peer groups, neighbors, and AFI/SAFI settings on Nokia SR Linux.
options:
  config:
    description:
      - Master dictionary containing BGP configuration parameters.
    type: dict
    required: true
    suboptions:
      network_instance:
        description: Target network-instance (ip-vrf name or default) where BGP is configured.
        type: str
        required: true
      autonomous_system:
        description: Local autonomous system (AS) number.
        type: int
        required: true
      router_id:
        description: BGP router ID string (typically an IPv4 loopback address).
        type: str
      admin_state:
        description: Enable or disable BGP globally within the network instance.
        type: str
        choices: [enable, disable]
      afi_safi:
        description: List of global address family indicators (AFI/SAFI) to activate.
        type: list
        elements: dict
        suboptions:
          afi_safi_name:
            description: Name of the address family (e.g., ipv4-unicast, ipv6-unicast).
            type: str
            required: true
          admin_state:
            description: Administrative state of the global address family.
            type: str
            choices: [enable, disable]
      groups:
        description: List of peer group configuration blocks.
        type: list
        elements: dict
        suboptions:
          group_name:
            description: Unique name identifying the BGP peer group.
            type: str
            required: true
          peer_as:
            description: Peer autonomous system number for the group.
            type: int
          description:
            description: Custom description string for the peer group.
            type: str
          admin_state:
            description: Administrative state of the peer group.
            type: str
            choices: [enable, disable]
          afi_safi:
            description: List of address families to activate for this specific group.
            type: list
            elements: dict
            suboptions:
              afi_safi_name:
                description: Address family name string.
                type: str
                required: true
              admin_state:
                description: Administrative state of the family inside the group.
                type: str
                choices: [enable, disable]
      neighbors:
        description: List of BGP neighbor configuration blocks.
        type: list
        elements: dict
        suboptions:
          peer_address:
            description: Remote gateway IP address of the BGP neighbor.
            type: str
            required: true
          peer_group:
            description: Name of the pre-defined peer group assigned to this neighbor.
            type: str
          peer_as:
            description: Explicit remote autonomous system number overrides.
            type: int
          description:
            description: Custom description string for the neighbor relationship.
            type: str
          export_policy:
            description: Routing policy name used to filter outbound advertisements.
            type: str
          import_policy:
            description: Routing policy name used to filter inbound advertisements.
            type: str
          timers:
            description: BGP session advertisement and hold timer blocks.
            type: dict
            suboptions:
              hold_time:
                description: Hold time duration in seconds.
                type: int
              keepalive_interval:
                description: Keepalive interval duration in seconds.
                type: int
          afi_safi:
            description: List of address families to activate for this specific neighbor.
            type: list
            elements: dict
            suboptions:
              afi_safi_name:
                description: Address family name string.
                type: str
                required: true
              admin_state:
                description: Administrative state of the family for this neighbor.
                type: str
                choices: [enable, disable]
              default_export_policy:
                description: Default export policy behavior flag (e.g., accept, reject).
                type: str
              default_import_policy:
                description: Default import policy behavior flag (e.g., accept, reject).
                type: str
  state:
    description: Control whether the targeted configurations should be provisioned (merged) or destroyed (deleted).
    type: str
    choices: [merged, deleted]
    default: merged
author:
  - Uzma Saman (@NetOpsChic)
'''

EXAMPLES = r'''
- name: Batch configure a production BGP context with groups and neighbors
  netopschic.srlinux.srlinux_bgp:
    config:
      network_instance: "VRF-PROD-TEST"
      autonomous_system: 65000
      router_id: "1.1.1.1"
      admin_state: "enable"
      groups:
        - group_name: "SPINE-PEERS"
          peer_as: 65001
      neighbors:
        - peer_address: "10.10.10.2"
          peer_group: "SPINE-PEERS"
          export_policy: "export-local"
          timers:
            hold_time: 9
            keepalive_interval: 3
    state: merged

- name: Wipe the entire BGP routing protocol instance from a VRF context
  netopschic.srlinux.srlinux_bgp:
    config:
      network_instance: "VRF-PROD-TEST"
    state: deleted
'''

RETURN = r'''
results:
  description: Evaluation statuses indicating transaction histories before and after processing.
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
    """Recursively removes SR Linux YANG namespaces from JSON keys to ensure clean parsing."""
    if isinstance(data, dict):
        return {k.split(':')[-1]: strip_namespaces(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [strip_namespaces(item) for item in data]
    else:
        return data
    
global_debug_diffs = []

def is_diff(intent, current, context_key="unknown"):
    """Deep normalized comparison with aggressive debugging."""
    if current is None:
        global_debug_diffs.append(f"DIFF [{context_key}]: Router has nothing, Intent is {intent}")
        return True
    
    def remove_none(obj):
        """Recursively strip None values from dictionaries and lists."""
        if isinstance(obj, dict):
            return {k: remove_none(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [remove_none(v) for v in obj if v is not None]
        return obj

    clean_intent = remove_none(intent)
    clean_current = remove_none(current)
    
    str_intent = json.dumps(clean_intent, sort_keys=True)
    str_current = json.dumps(clean_current, sort_keys=True)

    if str_intent != str_current:
        global_debug_diffs.append(f"DIFF [{context_key}]: \nINTENT: {str_intent} \nROUTER: {str_current}")
        return True
    
    return False
def _norm_afi_name(af: dict):
    return af.get("afi_safi_name") or af.get("afi-safi-name")

def map_config_to_obj(client, ni):
    get_commands = [
        {"path": f"/network-instance[name={ni}]/protocols/bgp", "datastore": "running"}
    ]
    get_rpc = build_rpc("get", get_commands, rpcID())
    get_response = client.post(payload=json.dumps(get_rpc))

    have_global = {}
    have_groups = {}
    have_neighbors = {}
    have_afis = {}

    if get_response.get('error'):
        return have_global, have_groups, have_neighbors, have_afis
        
    clean_result = strip_namespaces(get_response.get("result", []))

    for result in clean_result:
        ni_list = result.get("network-instance", [result]) 
        
        for ni_data in ni_list:
            bgp = ni_data.get("protocols", {}).get("bgp", {})
            if not bgp:
                bgp = result.get("bgp", result) if "admin-state" in result.get("bgp", result) else {}
            
            if not bgp:
                continue

            have_global = {
                "admin-state": bgp.get("admin-state"),
                "router-id": bgp.get("router-id"),
                "autonomous-system": bgp.get("autonomous-system")
            }

            for afi in bgp.get("afi-safi", []):
                afi_name = afi.get("afi-safi-name", "").split(':')[-1] 
                have_afis[f"global::{afi_name}"] = {"admin-state": afi.get("admin-state")}

            for grp in bgp.get("group", []):
                gname = grp.get("group-name")
                have_groups[gname] = {
                    "admin-state": grp.get("admin-state"),
                    "peer-as": grp.get("peer-as"),
                    "description": grp.get("description")
                }
                
                for afi in grp.get("afi-safi", []):
                    afi_name = afi.get("afi-safi-name", "").split(':')[-1] 
                    have_afis[f"group::{gname}::{afi_name}"] = {"admin-state": afi.get("admin-state")}

         
            for nbr in bgp.get("neighbor", []):
                naddr = nbr.get("peer-address")
                
                timers = nbr.get("timers", {})
                have_timers = {}
                if "hold-time" in timers:
                    have_timers["hold-time"] = timers["hold-time"]
                if "keepalive-interval" in timers:
                    have_timers["keepalive-interval"] = timers["keepalive-interval"]

                have_neighbors[naddr] = {
                    "admin-state": nbr.get("admin-state"),
                    "peer-group": nbr.get("peer-group"),
                    "peer-as": nbr.get("peer-as"),
                    "description": nbr.get("description"),
                    "export-policy": nbr.get("export-policy", [None])[0] if nbr.get("export-policy") else None,
                    "import-policy": nbr.get("import-policy", [None])[0] if nbr.get("import-policy") else None,
                    "timers": have_timers if have_timers else None
                }
                
                for afi in nbr.get("afi-safi", []):
                    afi_name = afi.get("afi-safi-name", "").split(':')[-1] 
                    have_afis[f"neighbor::{naddr}::{afi_name}"] = {
                        "admin-state": afi.get("admin-state"),
                        "default-export-policy": afi.get("default-export-policy"),
                        "default-import-policy": afi.get("default-import-policy")
                    }
                    
    return have_global, have_groups, have_neighbors, have_afis


def main():
    argument_spec = dict(
        config=dict(type='dict', required=True),
        state=dict(type='str', choices=['merged', 'deleted'], default='merged') 
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    client = JSONRPCClient(module)

    config = module.params.get("config") or {}
    state = module.params["state"]

    ni = config.get("network_instance")
    bgp_path = f'/network-instance[name={ni}]/protocols/bgp'
    
    have_global, have_groups, have_neighbors, have_afis = map_config_to_obj(client, ni)
    global_debug_diffs.append(f"PARSED GROUPS: {list(have_groups.keys())}")
    global_debug_diffs.append(f"PARSED NEIGHBORS: {list(have_neighbors.keys())}")

    change = False
    set_commands = []

    if state == "deleted":
        if have_global:
            change = True
            set_commands.append({
                "path": bgp_path,
                "action": "delete"
            })

    elif state == "merged":
            intent_global = {
                "admin-state": config.get("admin_state", "enable"),
                "router-id": config.get("router_id"),
                "autonomous-system": config.get("autonomous_system")
            }

            if not have_global or is_diff(intent_global, have_global, "GLOBAL"):
                change = True
                set_commands.append({
                    "action": "update",
                    "path": bgp_path,
                    "value": intent_global
                })
                
            global_afis = config.get("afi_safi", []) or [{"afi_safi_name": "ipv4-unicast", "admin_state": "enable"}]
            for afi in global_afis:
                afi_name = _norm_afi_name(afi)
                if not afi_name:
                    continue
                    
                intent_afi = {"admin-state": afi.get("admin_state", "enable")}
                afi_key = f"global::{afi_name}"

                if afi_key not in have_afis or is_diff(intent_afi, have_afis.get(afi_key), f"GLOBAL_AFI_{afi_key}"):
                    change = True
                    set_commands.append({
                        "action": "update",
                        "path": f"{bgp_path}/afi-safi[afi-safi-name={afi_name}]",
                        "value": intent_afi
                    })

            for group in config.get("groups", []):
                gname = group.get("group_name") or group.get("group-name")
                gp_path = f'{bgp_path}/group[group-name={gname}]'
                
                intent_group = {
                    "admin-state": group.get("admin_state", "enable")
                }
                if "peer_as" in group or "peer-as" in group:
                    intent_group["peer-as"] = group.get("peer_as") or group.get("peer-as")
                if "description" in group:
                    intent_group["description"] = group.get("description")
               
                if gname not in have_groups or is_diff(intent_group, have_groups.get(gname), f"GROUP_{gname}"):
                    change = True
                    set_commands.append({"action": "update", "path": gp_path, "value": intent_group})

                gafis = group.get("afi_safi", []) or [{"afi_safi_name": "ipv4-unicast", "admin_state": "enable"}]
                for gaf in gafis:
                    gaf_name = _norm_afi_name(gaf)
                    if not gaf_name:
                        continue
                        
                    intent_gafi = {"admin-state": gaf.get("admin_state", "enable")}
                    gafi_key = f"group::{gname}::{gaf_name}"
                    
                    if gafi_key not in have_afis or is_diff(intent_gafi, have_afis.get(gafi_key), f"GROUP_AFI_{gafi_key}"):
                        change = True
                        set_commands.append({
                            "action": "update",
                            "path": f"{gp_path}/afi-safi[afi-safi-name={gaf_name}]",
                            "value": intent_gafi
                        })

            for nbr in config.get("neighbors", []):
                naddr = nbr.get("peer_address") or nbr.get("peer-address")
                n_path = f'{bgp_path}/neighbor[peer-address={naddr}]'
                
                intent_nbr = {
                    "admin-state": nbr.get("admin_state", "enable")
                }
                if "peer_group" in nbr or "peer-group" in nbr:
                    intent_nbr["peer-group"] = nbr.get("peer_group") or nbr.get("peer-group")
                if "peer_as" in nbr or "peer-as" in nbr:
                    intent_nbr["peer-as"] = nbr.get("peer_as") or nbr.get("peer-as")
                if "description" in nbr:
                    intent_nbr["description"] = nbr.get("description")
                if "export_policy" in nbr or "export-policy" in nbr:
                    intent_nbr["export-policy"] = nbr.get("export_policy") or nbr.get("export-policy")
                if "import_policy" in nbr or "import-policy" in nbr:
                    intent_nbr["import-policy"] = nbr.get("import_policy") or nbr.get("import-policy")
                    
                if "timers" in nbr:
                    intent_timers = {}
                    if "hold_time" in nbr["timers"] or "hold-time" in nbr["timers"]:
                        intent_timers["hold-time"] = nbr["timers"].get("hold_time") or nbr["timers"].get("hold-time")
                    if "keepalive_interval" in nbr["timers"] or "keepalive-interval" in nbr["timers"]:
                        intent_timers["keepalive-interval"] = nbr["timers"].get("keepalive_interval") or nbr["timers"].get("keepalive-interval")
                    if intent_timers:
                        intent_nbr["timers"] = intent_timers

                if naddr not in have_neighbors or is_diff(intent_nbr, have_neighbors.get(naddr), f"NEIGHBOR_{naddr}"):
                    change = True
                    set_commands.append({"action": "update", "path": n_path, "value": intent_nbr})

                nafis = nbr.get("afi_safi", []) or [{"afi_safi_name": "ipv4-unicast", "admin_state": "enable"}]
                for naf in nafis:
                    naf_name = _norm_afi_name(naf)
                    if not naf_name:
                        continue
                    
                    intent_nafi = {"admin-state": naf.get("admin_state", "enable")}
                    def_exp = naf.get("default_export_policy") or naf.get("default-export-policy")
                    def_imp = naf.get("default_import_policy") or naf.get("default-import-policy")
                    
                    if def_exp:
                        intent_nafi["default-export-policy"] = def_exp
                    if def_imp:
                        intent_nafi["default-import-policy"] = def_imp
                        
                    nafi_key = f"neighbor::{naddr}::{naf_name}"
                    
                    if nafi_key not in have_afis or is_diff(intent_nafi, have_afis.get(nafi_key), f"NEIGHBOR_AFI_{nafi_key}"):
                        change = True
                        set_commands.append({
                            "action": "update",
                            "path": f"{n_path}/afi-safi[afi-safi-name={naf_name}]",
                            "value": intent_nafi
                        })

    if change and not module.check_mode and set_commands:
        response = client.post(payload=json.dumps(build_rpc("set", set_commands, rpcID())))
        if response.get("error"):
            module.fail_json(
                msg="Server error (BATCH)",
                response=pprint.pformat(response)
            )
    module.exit_json(changed=change, msg="Successfully processed routing policy intent")

if __name__ == "__main__":
    main()