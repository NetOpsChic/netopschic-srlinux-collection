# Module: `netopschic.srlinux.srlinux_l3_interface`

> Advanced batch-processing configuration engine for Layer 3 routed interfaces and subinterfaces on Nokia SR Linux via JSON-RPC.

---

## Synopsis

This module provisions, updates, or deletes Layer 3 routed interfaces and subinterfaces natively within Nokia SR Linux platforms. It handles physical or logical subinterface attributes, explicit IPv4/IPv6 prefix routing assignments in CIDR notation, and orchestrates atomic cross-bindings into targeted Layer 3 routing contexts (`ip-vrf`).

---

## Parameter Specifications

### Core Options

| Parameter | Type | Required | Choices / Defaults | Description |
| --- | --- | --- | --- | --- |
| **config** | `list` | **Yes** | Elements: `dict` | List of target Layer 3 routed interface configuration objects to process inside a single, transactional JSON-RPC batch. |
| **state** | `str` | No | Choices: `[merged, deleted]`<br>

<br>Default: `merged` | Operational behavior intent. `merged` provisions or modifies active states; `deleted` tears down the logical subinterface and completely untethers its VRF configuration context. |

### Suboptions under `config[]`

| Attribute | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| **interface** | `str` | **Yes** | `null` | Complete parent interface or indexed subinterface name string token (e.g., `ethernet-1/1` or `ethernet-1/1.100`). |
| **admin_state** | `str` | No | `null` | Administrative state configuration toggle applied to both the physical interface layer and the logical subinterface node (`enable`/`disable`). |
| **description** | `str` | No | `null` | Custom metadata cleartext annotation string attached to the logical interface entity. |
| **ipv4_address** | `str` | No | `null` | Explicit IPv4 address prefix assignment string represented in standard Classless Inter-Domain Routing (CIDR) notation (e.g., `10.10.10.1/30`). |
| **ipv6_address** | `str` | No | `null` | Explicit IPv6 address prefix assignment string represented in standard Classless Inter-Domain Routing (CIDR) notation (e.g., `2001:db8::1/64`). |
| **network_instance** | `str` | No | `null` | Target Layer 3 routing instance (`ip-vrf` name context) where this specific subinterface should be cross-bound. |

---

## Blueprint Reference (Examples)

```yaml
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

```

---

## Return Values

| Return Key | Type | Returned | Description |
| --- | --- | --- | --- |
| **results** | `list` | Always | List of transactional execution summary dictionaries tracking parameters evaluated both before and after execution routing logic blocks run. |

---

### Metadata

* **Version Added:** `0.0.1` (Production Core)
* **Author:** Uzma Saman (@NetOpsChic)
