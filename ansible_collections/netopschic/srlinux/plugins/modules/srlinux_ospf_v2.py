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
module: srlinux_ospf_v2
short_description: Configure OSPFv2 on Nokia SR Linux (all settings)
description:
  - Configure OSPFv2 with global, area, interface, and redistribution settings on SR Linux.
options:
  config:
    description:
      - OSPF configuration parameters.
    type: dict
    suboptions:
      network_instance:
        description: Network-instance name (VRF).
        type: str
        required: true
      router_id:
        description: Router ID.
        type: str
        required: true
      admin_state:
        description: Enable or disable OSPF.
        type: str
        choices: [enable, disable]
      reference_bandwidth:
        description: Reference bandwidth for OSPF.
        type: int
      max_metric:
        description: Set max-metric options.
        type: dict
        suboptions:
          on_startup:
            description: Set max-metric on startup with specified timeout.
            type: bool
          router_lsa:
            description: Set max-metric on router LSA.
            type: int
      spf_timers:
        description: SPF timers.
        type: dict
        suboptions:
          initial_delay:
            description: Initial SPF delay in milliseconds.
            type: int
          secondary_delay:
            description: Secondary SPF delay in milliseconds.
            type: int
          max_delay:
            description: Maximum SPF delay in milliseconds.
            type: int
      lsa_timers:
        description: LSA timers.
        type: dict
        suboptions:
          initial_delay:
            description: Initial LSA generation delay in milliseconds.
            type: int
          secondary_delay:
            description: Secondary LSA generation delay in milliseconds.
            type: int
          max_delay:
            description: Maximum LSA generation delay in milliseconds.
            type: int
          min_arrival_interval:
            description: Minimum LSA arrival interval in milliseconds.
            type: int
      graceful_restart:
        description: Enable/disable OSPF graceful-restart.
        type: bool
      export_policy:
        description: Policy for exporting routes into OSPF.
        type: str
      areas:
        description: List of areas.
        type: list
        elements: dict
        suboptions:
          area_id:
            description: Area ID (e.g. 0.0.0.0).
            type: str
            required: true
          type:
            description: Area type (normal, stub, nssa).
            type: str
          range:
            description: List of area ranges.
            type: list
            elements: dict
            suboptions:
              prefix:
                description: IP prefix with mask used for summarization (e.g. 10.0.0.0/8).
                type: str
              advertise:
                description: Whether to advertise this area range.
                type: bool
          interfaces:
            description: List of interfaces in this area.
            type: list
            elements: dict
            suboptions:
              name:
                description: Interface name (e.g. ethernet-1/1.10).
                type: str
                required: true
              admin_state:
                description: Enable or disable OSPF on this interface.
                type: str
                choices: [enable, disable]
              cost:
                description: Cost for this interface.
                type: int
              priority:
                description: Priority for this interface.
                type: int
              hello_interval:
                description: Hello interval for this interface.
                type: int
              dead_interval:
                description: Dead interval timeout duration in seconds for this interface.
                type: int
              network_type:
                description: OSPF interface network type behavior configuration.
                type: str
                choices: [broadcast, point-to-point]
              authentication:
                description: Cryptographic or simple authentication configuration container.
                type: dict
                suboptions:
                  type:
                    description: Authentication type selection string.
                    type: str
                  key_id:
                    description: Numeric index identifying the specific key.
                    type: int
                  key:
                    description: Cleartext passphrase or hashed authentication key string.
                    type: str
              passive:
                description: Suppress OSPF packet transmission while continuing prefix advertisement.
                type: bool
      redistribute:
        description: List of redistribution rules.
        type: list
        elements: dict
        suboptions:
          protocol:
            description: Protocol to redistribute (static, direct, bgp).
            type: str
            choices: [static, direct, bgp]
          policy:
            description: Policy for redistribution.
            type: str
  state:
    description: merged (set/update) or deleted (remove config)
    type: str
    choices: [merged, deleted]
    default: merged
author:
  - Uzma Saman (@NetOpsChic)
'''

EXAMPLES = r'''
- name: Configure global OSPFv2 area and interface definitions
  netopschic.srlinux.srlinux_ospf_v2:
    config:
      network_instance: "VRF-PROD-TEST"
      admin_state: "enable"
      router_id: "1.1.1.1"
      areas:
        - area_id: "0.0.0.0"
          interfaces:
            - name: "ethernet-1/1.10"
              admin_state: "enable"
              network_type: "point-to-point"
    state: merged

- name: Completely purge OSPF instance configuration
  netopschic.srlinux.srlinux_ospf_v2:
    config:
      network_instance: "VRF-PROD-TEST"
    state: deleted
'''

RETURN = r'''
results:
  description: Evaluation statuses indicating transaction histories before and after script modifications.
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

def is_diff(intent, current):
    """Bulletproof type-casting comparison for YAML vs JSON differences."""
    if current is None:
        return True
    return str(intent).lower() != str(current).lower()

def map_config_to_obj(client):
    get_commands = [
        {"path": "/network-instance[name=*]/protocols/ospf/instance[name=*]", "datastore": "running"}
    ]
    get_rpc = build_rpc("get", get_commands, rpcID())
    get_response = client.post(payload=json.dumps(get_rpc))
    
    have_base = {}
    have_areas = {}
    have_ifaces = {}

    if get_response.get('error'):
        return have_base, have_areas, have_ifaces
        
    clean_result = strip_namespaces(get_response.get("result", []))

    for result in clean_result:
        for ni_data in result.get("network-instance", []):
            vrf = ni_data.get("name")
            
            protocols = ni_data.get("protocols", {})
            ospf = protocols.get("ospf", {})
            instances = ospf.get("instance", [])

            for instance in instances:
                inst_name = instance.get("name", "default")
                
                # --- BASE OSPF ---
                base_key = f"{vrf}::{inst_name}"
                have_base[base_key] = {
                    "router_id": instance.get("router-id"),
                    "admin_state": instance.get("admin-state"),
                    "reference_bandwidth": instance.get("reference-bandwidth"),
                    "version": instance.get("version"),
                    "timers": instance.get("timers", {}),
                    "overload": instance.get("overload", {}) 
                }
                
                # --- AREAS ---
                for area in instance.get("area", []):
                    area_id = area.get("area-id")
                    area_key = f"{vrf}::{inst_name}::{area_id}"
                    
                    ranges_dict = {}
                    for ar in area.get("area-range", []):
                        ranges_dict[ar.get("ip-prefix-mask")] = ar.get("advertise")
                        
                    have_areas[area_key] = {
                        "area_id": area_id,
                        "area_range": ranges_dict
                    }
                    
                    # --- INTERFACES ---
                    for iface in area.get("interface", []):
                        iface_name = iface.get("interface-name")
                        iface_key = f"{vrf}::{inst_name}::{area_id}::{iface_name}"
                        have_ifaces[iface_key] = {
                            "admin_state": iface.get("admin-state"),
                            "metric": iface.get("metric"),
                            "priority": iface.get("priority"),
                            "hello_interval": iface.get("hello-interval"),
                            "dead_interval": iface.get("dead-interval"),
                            "interface_type": iface.get("interface-type"),
                            "passive": iface.get("passive")
                        }
                        
    return have_base, have_areas, have_ifaces
                        
def main():
    argument_spec = dict(
        config=dict(type='dict', required=True),
        state=dict(type='str', choices=['merged', 'deleted'], default='merged') 
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    client = JSONRPCClient(module)

    config = module.params.get("config") or {}
    state = module.params["state"]
    
    vrf_name = config.get("network_instance")
    instance_name = config.get("instance_name", "default")
    have_base, have_areas, have_ifaces = map_config_to_obj(client)

    change = False
    set_commands = []
    base_key = f"{vrf_name}::{instance_name}"

    if state == "deleted":
        if have_base.get(base_key):
            change = True
            set_commands.append({
                "path": f"/network-instance[name={vrf_name}]/protocols/ospf/instance[name={instance_name}]",
                "action": "delete"
            })
    
    elif state == "merged":
        have_b = have_base.get(base_key, {})
        base_payload = {}

        if "router_id" in config and is_diff(config["router_id"], have_b.get("router_id")):
            base_payload["router-id"] = config["router_id"]
            
        if "admin_state" in config and is_diff(config["admin_state"], have_b.get("admin_state")):
            base_payload["admin-state"] = config["admin_state"]
            
        if "reference_bandwidth" in config and is_diff(config["reference_bandwidth"], have_b.get("reference_bandwidth")):
            base_payload["reference-bandwidth"] = config["reference_bandwidth"]
        
        # --- OVERLOAD ---
        if "overload" in config:
            ov = config["overload"]
            have_ov = have_b.get("overload", {}) 
            
            is_active = True if ov.get("admin_state") == "enable" else False
            ov_payload = {}
            
            if is_diff(is_active, have_ov.get("active")):
                ov_payload["active"] = is_active
                
            if "on_startup" in ov and "timeout" in ov["on_startup"]:
                timeout_intent = ov["on_startup"]["timeout"]
                have_boot = have_ov.get("overload-on-boot", {})
                
                if is_diff(timeout_intent, have_boot.get("timeout")):
                    ov_payload["overload-on-boot"] = {"timeout": timeout_intent}
                    
            if ov_payload:
                if "active" not in ov_payload: ov_payload["active"] = is_active
                base_payload["overload"] = ov_payload
                
        # --- TIMERS ---
        if "timers" in config:
            intent_timers = config["timers"]
            have_timers = have_b.get("timers", {})
            timers_payload = {}

            if "spf" in intent_timers:
                spf_intent = intent_timers["spf"]
                have_spf = have_timers.get("spf-wait", {})
                spf_payload = {}
                
                if "initial_delay" in spf_intent and is_diff(spf_intent["initial_delay"], have_spf.get("spf-initial-wait")):
                    spf_payload["spf-initial-wait"] = spf_intent["initial_delay"]
                if "secondary_delay" in spf_intent and is_diff(spf_intent["secondary_delay"], have_spf.get("spf-second-wait")):
                    spf_payload["spf-second-wait"] = spf_intent["secondary_delay"]
                if "max_delay" in spf_intent and is_diff(spf_intent["max_delay"], have_spf.get("spf-max-wait")):
                    spf_payload["spf-max-wait"] = spf_intent["max_delay"]
                
                if spf_payload:
                    timers_payload["spf-wait"] = spf_payload

            if "lsa" in intent_timers:
                lsa_intent = intent_timers["lsa"]
                have_lsa = have_timers.get("lsa-generate", {})
                lsa_payload = {}
                
                if "initial_delay" in lsa_intent and is_diff(lsa_intent["initial_delay"], have_lsa.get("lsa-initial-wait")):
                    lsa_payload["lsa-initial-wait"] = lsa_intent["initial_delay"]
                if "secondary_delay" in lsa_intent and is_diff(lsa_intent["secondary_delay"], have_lsa.get("lsa-second-wait")):
                    lsa_payload["lsa-second-wait"] = lsa_intent["secondary_delay"]
                if "max_delay" in lsa_intent and is_diff(lsa_intent["max_delay"], have_lsa.get("max-lsa-wait")):
                    lsa_payload["max-lsa-wait"] = lsa_intent["max_delay"]
                
                if lsa_payload:
                    timers_payload["lsa-generate"] = lsa_payload

            if timers_payload:
                base_payload["timers"] = timers_payload

        # Append Base OSPF Config
        if base_payload or not have_b:
            change = True
            if not have_b: 
                base_payload["version"] = "ospf-v2"
            set_commands.append({
                "path": f"/network-instance[name={vrf_name}]/protocols/ospf/instance[name={instance_name}]",
                "action": "update",
                "value": base_payload
            })

        # --- AREAS AND INTERFACES ---
        areas_intent = config.get("areas", [])
        for area in areas_intent:
            area_id = area.get("area_id")
            area_key = f"{vrf_name}::{instance_name}::{area_id}"
            have_a = have_areas.get(area_key, {})
            
            if area_key not in have_areas:
                change = True
                set_commands.append({
                    "path": f"/network-instance[name={vrf_name}]/protocols/ospf/instance[name={instance_name}]/area[area-id={area_id}]",
                    "action": "update",
                    "value": {} 
                })
              
            have_ranges = have_a.get("area_range", {})
            for ar in area.get("area_range", []):
                prefix = ar.get("prefix")
                advertise = ar.get("advertise", True)
                
                if prefix not in have_ranges or is_diff(advertise, have_ranges.get(prefix)):
                    change = True
                    set_commands.append({
                        "path": f"/network-instance[name={vrf_name}]/protocols/ospf/instance[name={instance_name}]/area[area-id={area_id}]/area-range[ip-prefix-mask={prefix}]",
                        "action": "update",
                        "value": {"advertise": advertise}
                    })

            for iface in area.get("interfaces", []):
                iface_name = iface.get("name")
                iface_key = f"{vrf_name}::{instance_name}::{area_id}::{iface_name}"
                have_i = have_ifaces.get(iface_key, {})
                
                iface_payload = {}
                mappings = {
                    "admin_state": "admin-state",
                    "metric": "metric",
                    "priority": "priority",
                    "hello_interval": "hello-interval",
                    "dead_interval": "dead-interval",
                    "interface_type": "interface-type",
                    "passive": "passive"
                }
                
                for ans_key, yang_key in mappings.items():
                    if ans_key in iface and is_diff(iface[ans_key], have_i.get(ans_key)):   # <--- FIX IS HERE
                        iface_payload[yang_key] = iface[ans_key]
                        
                if iface_payload or not have_i:
                    change = True
                    set_commands.append({
                        "path": f"/network-instance[name={vrf_name}]/protocols/ospf/instance[name={instance_name}]/area[area-id={area_id}]/interface[interface-name={iface_name}]",
                        "action": "update",
                        "value": iface_payload
                    })
        
    if change and not module.check_mode:
        if set_commands:
            set_rpc = build_rpc("set", set_commands, rpcID())
            response = client.post(payload=json.dumps(set_rpc))

            if response.get("error"):
                module.fail_json(
                    msg="Server error (BATCH)",
                    response=pprint.pformat(response)
                )  
            
    module.exit_json(changed=change, msg="Successfully processed intent", debug_commands=set_commands)

if __name__ == "__main__":
    main()