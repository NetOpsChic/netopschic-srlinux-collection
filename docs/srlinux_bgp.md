# Module: `netopschic.srlinux.srlinux_bgp`

> Advanced batch-processing configuration engine for Border Gateway Protocol (BGP) on Nokia SR Linux platforms via JSON-RPC.

---

## Synopsis

This module provisions, updates, or deletes global BGP contexts, peer-groups, individual neighbor entries, and nested Address Family Indicators / Subsequent Address Family Indicators (AFI/SAFI) inside an explicit SR Linux `network-instance`.

---

## Parameter Specifications

### Core Options

| Parameter | Type | Required | Choices / Defaults | Description |
| --- | --- | --- | --- | --- |
| **config** | `dict` | **Yes** | Default: `null` | Master configuration dictionary block containing the structural routing parameters. |
| **state** | `str` | No | Choices: `[merged, deleted]`<br>

<br>Default: `merged` | Operational behavior intent. `merged` applies modifications; `deleted` unprovisions the entire routing context. |

### Suboptions under `config:`

| Attribute | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| **network_instance** | `str` | **Yes** | `null` | Target routing context (`default` or custom `ip-vrf` instance name) where the BGP process resides. |
| **autonomous_system** | `int` | **Yes** | `null` | Local Autonomous System (AS) number for the routing instance. |
| **router_id** | `str` | No | `null` | BGP Router Identification string (typically an IPv4 loopback assignment). |
| **admin_state** | `str` | No | `enable` | Global operational administrative state of the BGP process instance. |
| **afi_safi** | `list` | No | `ipv4-unicast` | Global address family structures to initialize under the BGP root hierarchy. |
| **groups** | `list` | No | `[]` | Peer-group assignment collections (see block specifications below). |
| **neighbors** | `list` | No | `[]` | Individual peer definitions (see block specifications below). |

---

### Group & Neighbor Nested Attribute Layouts

### `config.groups[]` Block Matrix

| Attribute | Type | Required | Description |
| --- | --- | --- | --- |
| **group_name** | `str` | **Yes** | Unique identifying string name for the BGP peer group. |
| **peer_as** | `int` | No | Remote AS number assignment explicitly enforced across all peers bound to this group. |
| **admin_state** | `str` | No | Administrative state of the specific group instance (`enable`/`disable`). |
| **description** | `str` | No | Optional documentation annotation text block. |
| **afi_safi** | `list` | No | Address families specifically activated for members belonging to this peer group. |

### `config.neighbors[]` Block Matrix

| Attribute | Type | Required | Description |
| --- | --- | --- | --- |
| **peer_address** | `str` | **Yes** | Remote peer gateway interface or loopback IP address. |
| **peer_group** | `str` | No | Pre-existing group identifier association to inherit parameters from. |
| **peer_as** | `int` | No | Autonomous System override option for specific targeted neighbors. |
| **export_policy** | `str` | No | Applied route-map/policy name filtering outbound update advertisements. |
| **import_policy** | `str` | No | Applied route-map/policy name filtering inbound update advertisements. |
| **timers** | `dict` | No | Dictionary defining session parameters: `hold_time` (int) and `keepalive_interval` (int). |
| **afi_safi** | `list` | No | Address families activated explicitly on this specific link neighbor context. |

---

## Blueprint Reference (Example)

```yaml
- name: Batch provision a production multi-tenant BGP core
  netopschic.srlinux.srlinux_bgp:
    config:
      network_instance: "VRF-PROD-TEST"
      autonomous_system: 65000
      router_id: "1.1.1.1"
      admin_state: "enable"
      groups:
        - group_name: "SPINE-PEERS"
          peer_as: 65001
          afi_safi:
            - afi_safi_name: "ipv4-unicast"
              admin_state: "enable"
      neighbors:
        - peer_address: "10.10.10.2"
          peer_group: "SPINE-PEERS"
          export_policy: "export-local"
          timers:
            hold_time: 9
            keepalive_interval: 3
    state: merged

```

---

## Return Values

| Return Key | Type | Returned | Description |
| --- | --- | --- | --- |
| **results** | `list` | Always | List of dictionaries capturing structural state changes on the transaction batch, providing audit logs of pre- and post-execution configurations. |

---

### Metadata

* **Version Added:** `0.0.1` (Extended Framework)
* **Author:** Uzma Saman (@NetOpsChic)
