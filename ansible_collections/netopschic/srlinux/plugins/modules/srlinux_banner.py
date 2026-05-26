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
module: srlinux_banner
short_description: Manage system banner on Nokia SR Linux via JSON-RPC
description:
  - Retrieve, set, or delete the system login banner and message of the day (MOTD) using JSON-RPC against SR Linux.
version_added: "0.0.1"
options:
  config:
    description:
      - System banner configuration dictionary block.
    type: dict
    required: false
    suboptions:
      login_banner:
        description:
          - The custom interactive login banner string displayed prior to authentication.
        type: str
      motd_banner:
        description:
          - The custom message of the day (MOTD) string displayed immediately after successful login.
        type: str
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
- name: Set only the MOTD banner
  netopschic.srlinux.srlinux_banner:
    config:
      motd_banner: "Maintenance scheduled for midnight."
    state: merged

- name: Set only the Login banner
  netopschic.srlinux.srlinux_banner:
    config:
      login_banner: "UNAUTHORIZED ACCESS PROHIBITED."
    state: merged

- name: Set BOTH banners at the same time
  netopschic.srlinux.srlinux_banner:
    config:
      login_banner: "Authorized Personnel Only."
      motd_banner: "Welcome to Router 01."
    state: merged

- name: Remove ALL banners from the node
  netopschic.srlinux.srlinux_banner:
    state: deleted
'''

RETURN = r'''
before:
  description: State dictionary containing the login and MOTD banners captured prior to execution.
  type: dict
  returned: always
  suboptions:
    login_banner:
      description: The pre-existing system login banner string.
      type: str
    motd_banner:
      description: The pre-existing message of the day string.
      type: str
after:
  description: State dictionary containing the login and MOTD banners verified immediately after execution.
  type: dict
  returned: always
  suboptions:
    login_banner:
      description: The newly applied system login banner string (or null if dropped).
      type: str
    motd_banner:
      description: The newly applied message of the day string (or null if dropped).
      type: str
changed:
  description: Flag indicating if a modification transaction was explicitly pushed to the device.
  type: bool
  returned: always
'''
PATH = "/system/banner"

def json_rpc(method, commands, req_id):
        return {
            "jsonrpc": JSON_RPC_VERSION,
            "method": method,
            "params": {"commands": commands},
            "id": req_id
        }

# The "have" state is the current state of the banner on the device.
def map_config_to_obj(module, client): 
    get_command = [{"path": PATH, "datastore": "running"}]
    get_rpc = json_rpc("get", get_command, rpcID())
    get_response = client.post(payload=json.dumps(get_rpc))
    if get_response.get("error"):
        module.fail_json(msg="Server error (GET)", response=pprint.pformat(get_response))
    have_login = None
    have_motd = None
# Normalizing the response we got from router so we dont treat treat a List like a Dictionary
    result = get_response.get("result", [])
    if isinstance(result, list) and len(result) > 0:
        data = result[0]

        normalized_result = data.get("value", data)

        if isinstance(normalized_result, dict):
            have_login = normalized_result.get("login-banner")
            have_motd = normalized_result.get("motd-banner")

    return {"login_banner": have_login, "motd_banner": have_motd}

def main():
      # what user can type in playbook
    argument_spec = dict(
        config=dict(type='dict', required=False, options=dict(
            login_banner=dict(type='str'),
            motd_banner=dict(type='str')
        )),
        state=dict(type='str', choices=['merged', 'deleted'], default='merged'),
    )

    # initiate the module
    module = AnsibleModule(
         argument_spec=argument_spec,
         supports_check_mode=True
    )

    client = JSONRPCClient(module)
    # Get the current "have" state of the banner(gather before)
    have = map_config_to_obj(module, client)

    before_login = have.get("login_banner")
    before_motd = have.get("motd_banner")

    # gather the intent which is in playbook yaml
    config = module.params.get("config") or {}
    desired_login = config.get("login_banner")
    desired_motd = config.get("motd_banner")
    state = module.params["state"]
    
    # 4. Setup tracking variables
    change = False
    set_commands = []

    
    after_login = before_login
    after_motd = before_motd

    # Evaluate each banner independently

    if state == "merged":
         # check login banner
        if desired_login is not None and desired_login != before_login:
            set_commands.append({"action": "update", "path": "/system/banner/login-banner", "value": desired_login})
            after_login = desired_login
            change = True
                
        if desired_motd is not None and desired_motd != before_motd:
            set_commands.append({"action": "update", "path": "/system/banner/motd-banner", "value": desired_motd})
            after_motd = desired_motd
            change = True

        if change and not module.check_mode:
            set_rpc = json_rpc("set", set_commands, rpcID())
            response = client.post(payload=json.dumps(set_rpc))
            if response.get("error"):
                module.fail_json(
                    msg="Server error (MERGE)",
                    response=pprint.pformat(response)
                )
                
    elif state == "deleted":
        del_commands = []
        if before_login is not None:
            del_commands.append({"action": "delete", "path": "/system/banner/login-banner"})
            after_login = None
            change = True
        
        if before_motd is not None:
            del_commands.append({"action": "delete", "path": "/system/banner/motd-banner"})
            after_motd = None
            change = True
        
        if change and not module.check_mode:
            del_rpc = json_rpc("set", del_commands, rpcID())
            response = client.post(payload=json.dumps(del_rpc))
            if response.get("error"):
                module.fail_json(
                    msg="Server error (DELETE)",
                    response=pprint.pformat(response)
                )
       
    module.exit_json(
        changed=change, 
        before={"login_banner": before_login, "motd_banner": before_motd}, 
        after={"login_banner": after_login, "motd_banner": after_motd}
    )
if __name__ == "__main__":
    main()