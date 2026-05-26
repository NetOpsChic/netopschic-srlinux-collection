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
module: srlinux_hostname
short_description: Manage system hostname on Nokia SR Linux via JSON-RPC
description:
  - Retrieve, set, or delete the system hostname using JSON-RPC against SR Linux.
version_added: "0.0.1"
options:
  config:
    description:
      - Hostname configuration dictionary block.
    type: dict
    required: false
    suboptions:
      hostname:
        description:
          - The system hostname string.
        type: str
        required: true
  state:
    description:
      - Control whether the targeted configurations should be provisioned (merged) or destroyed (deleted).
    type: str
    choices: [merged, deleted]
    default: merged
author:
  - Uzma Saman (@NetOpsChic)
'''

EXAMPLES = r'''
- name: Set SR Linux hostname
  netopschic.srlinux.srlinux_hostname:
    config:
      hostname: srl01
    state: merged

- name: Remove SR Linux hostname
  netopschic.srlinux.srlinux_hostname:
    state: deleted
'''

RETURN = r'''
before:
  description: State dictionary containing the system hostname configuration captured prior to execution.
  type: dict
  returned: always
  suboptions:
    hostname:
      description: The pre-existing system hostname string.
      type: str
after:
  description: State dictionary containing the system hostname configuration verified immediately after execution.
  type: dict
  returned: always
  suboptions:
    hostname:
      description: The newly applied system hostname string (or null if dropped).
      type: str
changed:
  description: Flag indicating if a modification transaction was explicitly pushed to the device.
  type: bool
  returned: always
'''

PATH = "/system/name"

def json_rpc(method, commands, req_id):
        return {
            "jsonrpc": JSON_RPC_VERSION,
            "method": method,
            "params": {"commands": commands},
            "id": req_id
        }

# The "have" state is the current state of the hostname on the device.
def map_config_to_obj(module, client): 
    get_command = [{"path": PATH, "datastore": "running"}]
    get_rpc = json_rpc("get", get_command, rpcID())
    get_response = client.post(payload=json.dumps(get_rpc))

    if get_response.get("error"):
        module.fail_json(msg="Server error (GET)", response=pprint.pformat(get_response))
    have = None
# Normalizing the response we got from router so we dont treat treat a List like a Dictionary
    result = get_response.get("result", [])
    if isinstance(result, list) and len(result) > 0:
            # For a leaf path, result[0] is often the string itself or a simple dict
            data = result[0]
            if isinstance(data, str):
                have = data
            elif isinstance(data, dict):
                # Fallback for different API versions
                have = data.get("value", data.get("host-name"))
    return {"hostname": have}

def main():
     # what user can type in playbook
    argument_spec = dict(
         config=dict(type='dict', required=False, options=dict(
    hostname=dict(type='str', required=True)
    )),
         state=dict(type='str', choices=['merged', 'deleted'], default='merged'),
    )

    # initiate the module
    module = AnsibleModule(
         argument_spec=argument_spec,
         supports_check_mode=True
    )

    result = {"changed": False}

    client = JSONRPCClient(module)

    # Get the current "have" state of the hostname (gather before)
    have = map_config_to_obj(module, client)
    before = have.get("hostname")

    # gather the intent which is in playbook yaml
    config = module.params.get("config") or {}
    desired = config.get("hostname")
    state = module.params["state"]

    # get the "after"
    after = before
    change = False

    # Diff between desired and have to determine if we need to make a change

    if state == "merged":
        if desired != before:
            after = desired
            change = True
            if not module.check_mode:
                set_commands = [{"action": "update", "path": PATH, "value": {"host-name": desired}}]
                set_rpc = json_rpc("set", set_commands, rpcID())
                response = client.post(payload=json.dumps(set_rpc))
                if response.get("error"):
                    module.fail_json(
                        msg="Server error (MERGE)",
                        response=pprint.pformat(response)
                    )
                after = desired
    elif state == "deleted":
        if before is not None:
            change = True
            if not module.check_mode:
                del_commands = [{"action": "delete", "path": PATH}] 
                del_rpc = json_rpc("set", del_commands, rpcID())
                response = client.post(payload=json.dumps(del_rpc))
                if response.get("error"):
                    module.fail_json(
                        msg="Server error (DELETE)",
                        response=pprint.pformat(response)
                    )
                after = None   
    module.exit_json(changed=change, before={"hostname": before}, after={"hostname": after})

if __name__ == "__main__":
    main()