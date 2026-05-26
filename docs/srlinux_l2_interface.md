# Module: `netopschic.srlinux.srlinux_l2_interface`

> Advanced batch-processing configuration engine for Layer 2 bridged interfaces and subinterfaces on Nokia SR Linux via JSON-RPC.

---

## Synopsis

This module provisions, updates, or deletes Layer 2 interface attributes and subinterfaces natively within Nokia SR Linux. It configures operational parameters including administrative states, custom descriptions, single-tagged VLAN encapsulation keys (`vlan_id`/`access_vlan`), trunking parameters, and handles direct interface cross-binding into switching contexts (`mac-vrf`).

---

## Parameter Specifications

### Core Options

| Parameter | Type | Required | Choices / Defaults | Description |
| --- | --- | --- | --- | --- |
| **config** | `list` | **Yes** | Elements: `dict` | List of target Layer 2 interface configuration objects to process in a single batch transaction. |
| **state** | `str` | No | Choices: `[merged, deleted]`<br>

<br>Default: `merged` | Operational behavior intent. `merged` applies configurations; `deleted` unprovisions the targeted subinterface definitions and clears switching domain associations. |

### Suboptions under `config[]`

| Attribute | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| **interface** | `str` | **Yes** | `null` | Complete interface or subinterface name string identifier (e.g., `ethernet-1/2` or `ethernet-1/2.20`). |
| **admin_state** | `str` | No | `null` | Administrative state configuration control applied to the target (`enable` or `disable`). |
| **description** | `str` | No | `null` | Custom cleartext annotation metadata attached to the physical interface layer. |
| **vlan_id** | `int` | No | `null` | Specific explicit VLAN ID tag encapsulation value applied to the subinterface block. |
| **access_vlan** | `int` | No | `null` | Alternative configuration key indicating an access port or untagged VLAN ID mapping intent. |
| **trunk_vlans** | `list` | No | Elements: `int` | List of explicit VLAN IDs allowed across a trunk context (automatically programs subinterface encapsulation constraints to match any). |
| **network_instance** | `str` | No | `null` | Target Layer 2 broadcast switching instance (`mac-vrf` name) where this bridged subinterface should be cross-bound. |

---

## Blueprint Reference (Examples)

```yaml
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

```

---

## Return Values

| Return Key | Type | Returned | Description |
| --- | --- | --- | --- |
| **results** | `list` | Always | List of operational outcome dictionaries summarizing pre-change and post-change states for auditing execution results. |

---

### Metadata

* **Version Added:** `0.0.1` (Extended L2 Core)
* **Author:** Uzma Saman (@NetOpsChic)
