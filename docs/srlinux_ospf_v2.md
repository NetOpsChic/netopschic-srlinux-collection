# Module: `netopschic.srlinux.srlinux_ospf_v2`

> Advanced batch-processing configuration engine for Open Shortest Path First version 2 (OSPFv2) on Nokia SR Linux via JSON-RPC.

---

## Synopsis

This module provisions, updates, or deletes OSPFv2 protocol instances within specific Nokia SR Linux `network-instance` contexts. It handles global router settings, link-state advertisement (LSA) and shortest path first (SPF) throttling timers, traffic engineering parameters, area definitions, summarization range boundaries, interface link metrics, and explicit route redistribution properties.

---

## Parameter Specifications

### Core Options

| Parameter | Type | Required | Choices / Defaults | Description |
| --- | --- | --- | --- | --- |
| **config** | `dict` | **Yes** | Default: `null` | Master configuration dictionary block containing the structural routing protocol settings. |
| **state** | `str` | No | Choices: `[merged, deleted]`<br>

<br>Default: `merged` | Operational intent behavior switch. `merged` applies targeted changes; `deleted` unprovisions the entire routing protocol instance from the active database context. |

### Suboptions under `config:`

| Attribute | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| **network_instance** | `str` | **Yes** | `null` | Target routing context (`default` or explicit `ip-vrf` name string) where OSPFv2 is attached. |
| **router_id** | `str` | **Yes** | `null` | System Router ID identifier string specified in standard dotted-quad IPv4 format. |
| **admin_state** | `str` | No | `null` | Global operational administrative state of the OSPFv2 protocol instance (`enable`/`disable`). |
| **reference_bandwidth** | `int` | No | `null` | Reference bandwidth value in Mbps used to dynamically calculate interface metric costs. |
| **graceful_restart** | `bool` | No | `null` | Toggle switch controlling OSPF graceful-restart high-availability helper/restart capabilities. |
| **export_policy** | `str` | No | `null` | Policy map reference name string used for exporting active system routes into OSPF. |
| **max_metric** | `dict` | No | `null` | Container managing maximum metric/stub-router traffic engineering overrides. |
| **spf_timers** | `dict` | No | `null` | Container managing calculation delay values (see suboption details below). |
| **lsa_timers** | `dict` | No | `null` | Container managing LSA generation and throttling rates (see suboption details below). |
| **areas** | `list` | No | `[]` | List collection specifying OSPF area and link properties (see area block matrix below). |
| **redistribute** | `list` | No | `[]` | List collection detailing explicit protocol injection rules (see redistribution matrix below). |

---

### Nested Engine Timers & Overrides

#### `config.max_metric`

* **on_startup** (`bool`): Set maximum cost metric flags on system startup loops.
* **router_lsa** (`int`): Inject specific fixed maximum metrics into local Router LSAs.

#### `config.spf_timers` & `config.lsa_timers`

| Attribute | Type | Default | Unit | Description |
| --- | --- | --- | --- | --- |
| **initial_delay** | `int` | `null` | Milliseconds | The initial holdoff window duration before performing an execution loop. |
| **secondary_delay** | `int` | `null` | Milliseconds | The incremental backoff holdoff window used during consecutive network changes. |
| **max_delay** | `int` | `null` | Milliseconds | The absolute maximum holdoff wait ceiling for backoff schedules. |
| **min_arrival_interval** | `int` | `null` | Milliseconds | (*LSA Timers Only*) The minimum arrival filter delay constraint between identical LSAs. |

---

### Area, Range, and Interface Layout Matrix

#### `config.areas[]` Block Attributes

| Attribute | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| **area_id** | `str` | **Yes** | `null` | Area identification token written in standard dotted-quad notation (e.g., `0.0.0.0`). |
| **type** | `str` | No | `normal` | Area type category classification constraint. Choices: `[normal, stub, nssa]` |
| **range** | `list` | No | `[]` | List of IP summarization network blocks defined by properties `prefix` (str) and `advertise` (bool). |
| **interfaces** | `list` | No | `[]` | Logical interface attachments belonging to this area context (see parameters below). |

#### `config.areas[].interfaces[]` Property Specifications

| Attribute | Type | Required | Description |
| --- | --- | --- | --- |
| **name** | `str` | **Yes** | Precise subinterface name token identifier matching playbook intent (e.g., `ethernet-1/1.10`). |
| **admin_state** | `str` | No | Enable or disable OSPF protocol processing on this single subinterface node (`enable`/`disable`). |
| **network_type** | `str` | No | Network type mode simulation override model string. Choices: `[broadcast, point-to-point]` |
| **cost** | `int` | No | Static metric link cost override assigned to the interface path (bypasses auto-reference maths). |
| **priority** | `int` | No | Router priority metric used to skew Designated Router (DR/BDR) election choices. |
| **hello_interval** | `int` | No | The transmission cycle frequency timer for Hello packets, defined in seconds. |
| **dead_interval** | `int` | No | The dead neighbor failure timeout window timer, defined in seconds. |
| **passive** | `bool` | No | Flag suppressing packet transmissions on the link while maintaining local network prefix advertising. |
| **authentication** | `dict` | No | Container managing cryptographic interface security keys: `type` (str), `key_id` (int), and cleartext `key` (str). |

---

#### `config.redistribute[]` Block Attributes

| Attribute | Type | Required | Choices | Description |
| --- | --- | --- | --- | --- |
| **protocol** | `str` | **Yes** | `[static, direct, bgp]` | The origin source protocol selected for core ingestion routing. |
| **policy** | `str` | No | `null` | Pre-defined match-action routing policy name string filtering imported prefixes. |

---

## Blueprint Reference (Example)

```yaml
- name: Batch configure multi-area OSPFv2 core loopback and link states
  netopschic.srlinux.srlinux_ospf_v2:
    config:
      network_instance: "VRF-PROD-TEST"
      admin_state: "enable"
      router_id: "1.1.1.1"
      reference_bandwidth: 100000
      areas:
        - area_id: "0.0.0.0"
          type: "normal"
          interfaces:
            - name: "ethernet-1/1.10"
              admin_state: "enable"
              network_type: "point-to-point"
              cost: 10
              authentication:
                type: "hmac-sha-256"
                key_id: 1
                key: "SecretCoreToken"
        - area_id: "0.0.0.1"
          type: "stub"
          interfaces:
            - name: "system0.0"
              admin_state: "enable"
              passive: true
    state: merged

```

---

## Return Values

| Return Key | Type | Returned | Description |
| --- | --- | --- | --- |
| **results** | `list` | Always | List of operation dictionaries tracking internal server batch arrays before and after execution tuning tasks. |

---

### Metadata

* **Version Added:** `0.0.1` (Production Framework Expansion)
* **Author:** Uzma Saman (@NetOpsChic)