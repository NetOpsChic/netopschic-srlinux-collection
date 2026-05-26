# SR Linux Ansible Collection (Community Edition)

[](https://www.google.com/search?q=https://galaxy.ansible.com/netopschic/srlinux)

This Ansible Collection provides modules and example playbooks for automating Nokia SR Linux devices. It is a community-driven extension of the official Nokia tools, designed to make lab and production automation more accessible.

## Disclaimer

**This work is not affiliated with, endorsed by, or supported by Nokia.** This is a community-maintained project. Use it at your own discretion.

## Credits

This collection is **based on and extends** the [Official Nokia SR Linux Ansible Collection](https://github.com/nokia/srlinux-ansible-collection).

  * Original copyright (c) 2021 Nokia.
  * Special thanks to Roman Dodin, Patrick Dumais, and Walter De Smedt for the foundational work.

-----

## Installation

You no longer need to clone this repository to use the modules. Simply install it via Ansible Galaxy:

```sh
ansible-galaxy collection install netopschic.srlinux
```

## Features

  - **Standardized Modules:** - `hostname`: System identity management.
      - `network_instance`: VRF and instance-level config.
      - `l2_interface` & `l3_interface`: Comprehensive port management.
      - `static_routes`: Next-hop groups and static routing.
      - `bgp` & `ospf_v2`: Dynamic routing protocol automation.
      - `routing_policy`: Prefix-sets and policy statements.

-----

## Usage Example

Once installed, reference the collection in your playbooks using the `netopschic.srlinux` namespace:

```yaml
- name: Configure SR Linux Lab
  hosts: srlinux_nodes
  gather_facts: false
  collections:
    - netopschic.srlinux

  tasks:
    - name: Set the system hostname
      hostname:
        host_name: "leaf-01"
```

## Structure

```text
plugins/
  ├── modules/          # Python logic for SR Linux YANG models
  └── module_utils/     # Helper scripts for JSON-RPC transport
playbooks/              # Ready-to-use automation examples
```

## License

[BSD 3-Clause License](https://www.google.com/search?q=LICENSE)

## Contributing & Support

I am not a "pro" developer just a fellow automation tinkler! This collection is a work in progress, and I’m learning every day. 

If you see a bug, have an idea for a better way to handle a YANG model, or want to add a new module:
* **Open an Issue:** If something isn't working as expected.
* **Pull Requests:** If you've got a fix or a new feature, I'd love to see it!
* **Feedback:** Feel free to reach out if you have suggestions on how to make this more "lab-friendly."

Community contributions are what will make this collection better for everyone using SR Linux with Containerlab!