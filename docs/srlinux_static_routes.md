# Module: `netopschic.srlinux.srlinux_static_routes`

> Advanced batch-processing configuration engine for Next-Hop-Groups (NHGs) and static routes on Nokia SR Linux via JSON-RPC.

---

## Synopsis

This module provisions, updates, or deletes next-hop groups and static route prefixes natively inside a specified Nokia SR Linux `network-instance`. It supports explicit multi-path gateway index tracking, metric overrides, administrative distances (`preference`), custom cleartext route descriptions, and deterministic packet-discard entries (`blackhole`).

---

## Parameter Specifications

### Core Options

| Parameter | Type | Required | Choices / Defaults | Description |
| --- | --- | --- | --- | --- |
| **config** | `list` | **Yes** | Elements: `dict` | List containing explicit routing contexts, next-hop group lists, and prefix arrays to process inside a single transactional batch. |
| **state** | `str` | No | Choices: `[merged, deleted]`<br>

<br>Default: `merged` | Operational behavior intent. `merged` applies modifications; `deleted` unprovisions explicit routes or next-hop groups from the node tree. |

### Suboptions under `config[]`

| Attribute | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| **network_instance** | `str` | **Yes** | `null` | Target routing context (`default` or explicit `ip-vrf` instance name) where the static routes are applied. |
| **next_hop_groups** | `list` | No | `[]` | List collection specifying explicit next-hop gateway path structures (see next-hop group parameters below). |
| **routes** | `list` | No | `[]` | List collection defining destination target prefix rules (see static route parameters below). |

---

### Nested Configuration Layout Matrices

#### `config[].next_hop_groups[]` Block Parameters

| Attribute | Type | Required | Description |
| --- | --- | --- | --- |
| **name** | `str` | **Yes** | Unique identifying string name for the explicit next-hop group entry block. |
| **admin_state** | `str` | No | Operational administrative state of the group tracking container (`enable`/`disable`). |
| **nexthops** | `list` | No | List of explicit multi-path gateway pathways belonging to this group context (requires properties **index** (int) and **ip_address** (str)). |

#### `config[].routes[]` Block Parameters

| Attribute | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| **prefix** | `str` | **Yes** | `null` | Destination network target IP prefix written in standard CIDR notation (v4 or v6 format). |
| **next_hop_group** | `str` | No | `null` | The associated next-hop group lookup string token assigned to resolve this prefix. |
| **admin_state** | `str` | No | `enable` | Operational administrative state of the static route prefix mapping entry. |
| **metric** | `int` | No | `1` | Relative path cost metric value injected into the route properties. |
| **preference** | `int` | No | `5` | Administrative distance selection preference constraint prioritizing source routes. |
| **blackhole** | `bool` | No | `false` | Boolean flag configuring this target space to drop match traffic silently. |
| **description** | `str` | No | `null` | Optional custom description tracking text annotation string. |

---

## Blueprint Reference (Example)

```yaml
- name: Explicitly apply a batch of next-hop groups and static routes
  netopschic.srlinux.srlinux_static_routes:
    config:
      - network_instance: "VRF-PROD-TEST"
        next_hop_groups:
          - name: "NHG-SPINE1"
            admin_state: "enable"
            nexthops:
              - index: 0
                ip_address: "10.10.10.2"
              - index: 1
                ip_address: "10.10.10.6"
        routes:
          - prefix: "192.168.100.0/24"
            admin_state: "enable"
            next_hop_group: "NHG-SPINE1"
            metric: 10
            preference: 10
            description: "Production App Subnet via ECMP Spines"
          - prefix: "172.16.0.0/12"
            admin_state: "enable"
            blackhole: true
            description: "Discard RFC1918 leak block"
    state: merged

```

---

## Return Values

| Return Key | Type | Returned | Description |
| --- | --- | --- | --- |
| **results** | `list` | Always | List of transactional execution status dictionaries tracking configuration parameters evaluated both prior to and following execution. |

---

### Metadata

* **Version Added:** `0.0.1` (Production Core Infrastructure)
* **Author:** Uzma Saman (@NetOpsChic)