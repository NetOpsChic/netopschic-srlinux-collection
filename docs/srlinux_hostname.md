# Module: `netopschic.srlinux.srlinux_hostname`

> Manage system hostname configuration on Nokia SR Linux nodes via JSON-RPC.

---

## Synopsis

This module connects to the Nokia SR Linux JSON-RPC server to retrieve, set, or completely delete the system hostname configuration. It handles the low-level string/list API payload normalization natively to guarantee clean, idempotent state verification.

---

## Parameter Specifications

| Parameter | Type | Required | Choices / Defaults | Description |
| --- | --- | --- | --- | --- |
| **config** | `dict` | No | Default: `null` | Dictionary block containing the system hostname definition. |
|   ↳ *hostname* | `str` | **Yes** | Default: `null` | The targeted system hostname string to enforce on the node. |
| **state** | `str` | No | Choices: `[merged, deleted]`<br>

<br>Default: `merged` | Operational behavior intent. `merged` applies modifications; `deleted` unprovisions the custom hostname, reverting to platform defaults. |

---

## Examples

```yaml
- name: Explicitly provision system node identity
  netopschic.srlinux.srlinux_hostname:
    config:
      hostname: srl-mesh-node1
    state: merged

- name: Purge custom hostname configuration from the system datastore
  netopschic.srlinux.srlinux_hostname:
    state: deleted

```

---

## Return Values

| Return Key | Type | Returned | Description |
| --- | --- | --- | --- |
| **changed** | `bool` | Always | Indicates whether an active JSON-RPC configuration transaction was pushed to the device. |
| **before** | `dict` | Always | State dictionary summarizing the active hostname details discovered on the platform before execution. |
|   ↳ *hostname* | `str` | Always | Pre-existing system hostname string. |
| **after** | `dict` | Always | State dictionary summarizing the verified configuration state active on the platform immediately following execution. |
|   ↳ *hostname* | `str` | Always | Newly applied system hostname string (evaluates to `null` on full deletions). |

---

### Metadata

* **Version Added:** `0.0.1` (Production Core)
* **Author:** Uzma Saman (@NetOpsChic)