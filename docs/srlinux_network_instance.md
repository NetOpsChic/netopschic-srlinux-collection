# Module: `netopschic.srlinux.srlinux_network_instance`

> Transactional batch-configuration engine for virtual routing and switching instances (VRFs) on Nokia SR Linux via JSON-RPC.

---

## Synopsis

This module provisions, updates, or deletes network instances natively within Nokia SR Linux devices. It configures and manages Layer 2 broadcast environments (`mac-vrf`), Layer 3 multi-tenant routing environments (`ip-vrf`), system autonomous routing definitions (`default`), and coordinates the physical/logical network interface bindings to those instances.

---

## Parameter Specifications

### Core Options

| Parameter | Type | Required | Choices / Defaults | Description |
| --- | --- | --- | --- | --- |
| **config** | `list` | **Yes** | Elements: `dict` | List of targeted network-instance configuration blocks to process within a single JSON-RPC set transaction block. |
| **state** | `str` | No | Choices: `[merged, deleted]`<br>

<br>Default: `merged` | Controls configuration intent. `merged` provisions or builds out objects dynamically; `deleted` completely unprovisions the instance configuration tree. |

### Suboptions under `config[]`

| Attribute | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| **name** | `str` | **Yes** | `null` | Unique name string identifying the specific network-instance context (e.g., `mgmt`, `lan-vrf`, `blue`). |
| **type** | `str` | **Yes** | `null` | The structural operational footprint layout of the virtual instance.<br>

<br>Choices: `[ip-vrf, mac-vrf, default]` |
| **admin_state** | `str` | No | `null` | Administrative state configuration status enforced on the virtual block context (`enable`/`disable`). |
| **description** | `str` | No | `null` | Custom cleartext annotation text descriptive string attached directly to the network instance. |
| **router_id** | `str` | No | `null` | Explicit system routing identifier string (typically configured as an IPv4 loopback format address) inside L3 routing blocks. |
| **interfaces** | `list` | No | Elements: `str` | Ordered array list of physical interface tags or precise subinterface indicators (e.g., `ethernet-1/1.10`) bound securely to the instance layer. |

---

## Blueprint Reference (Examples)

```yaml
- name: Ensure targeted Layer 2 and Layer 3 VRFs exist simultaneously
  netopschic.srlinux.srlinux_network_instance:
    config:
      - name: lan-vrf
        type: mac-vrf
        description: L2 Switching Domain
      - name: blue
        type: ip-vrf
        description: L3 Routing Core Tenant
        router_id: "10.0.0.1"
        interfaces:
          - ethernet-1/1.10
      - name: default
        type: default
        description: Default Global System Routing Domain
    state: merged

- name: Securely unprovision an old virtual instance tree from the schema
  netopschic.srlinux.srlinux_network_instance:
    config:
      - name: old-vrf
        type: ip-vrf
    state: deleted

```

---

## Return Values

| Return Key | Type | Returned | Description |
| --- | --- | --- | --- |
| **results** | `list` | Always | List containing structural block state summaries indicating configuration states explicitly monitored both prior to and following execution routing. |

---

### Metadata

* **Version Added:** `0.0.1` (Production Core Infrastructure)
* **Author:** Uzma Saman (@NetOpsChic)