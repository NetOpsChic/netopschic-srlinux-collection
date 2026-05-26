# Module: `netopschic.srlinux.srlinux_banner`
> Manage system login banner and message of the day (MOTD) configurations on Nokia SR Linux nodes via JSON-RPC.

---

## Synopsis
This module connects to the Nokia SR Linux JSON-RPC management server to retrieve, provision, update, or completely purge operational banner contexts. It evaluates the current running datastore state to ensure modification actions are executed with absolute idempotency.

---

## Parameter Specifications

| Parameter | Type | Required | Choices / Defaults | Description |
| :--- | :--- | :--- | :--- | :--- |
| **config** | `dict` | No | Default: `null` | Master dictionary block containing the target text layout attributes. |
| &emsp; ↳ *login_banner* | `str` | No | Default: `null` | The interactive banner text block rendered on the terminal session prior to user authentication. |
| &emsp; ↳ *motd_banner* | `str` | No | Default: `null` | The Message of the Day (MOTD) string displayed immediately following successful authentication. |
| **state** | `str` | No | Choices: `[merged, deleted]`<br>Default: `merged` | Controls the operational intent. `merged` updates or provisions configurations; `deleted` strips them from the active schema. |

---

## Examples

```yaml
- name: Provision both corporate access and daily operational banners simultaneously
  netopschic.srlinux.srlinux_banner:
    config:
      login_banner: "WARNING: UNAUTHORIZED ACCESS IS STRICTLY PROHIBITED."
      motd_banner: "Welcome to Core-Leaf-01. Maintenance window: Sundays 0200-0400 UTC."
    state: merged

- name: Completely purge all text banner contexts from the system datastore
  netopschic.srlinux.srlinux_banner:
    state: deleted

```

---

## Return Values

| Return Key | Type | Returned | Description |
| --- | --- | --- | --- |
| **changed** | `bool` | Always | Indicates whether an active configuration change transaction payload was transmitted to the target platform. |
| **before** | `dict` | Always | State dictionary summarizing the active text configurations discovered on the device before execution block routing. |
|   ↳ *login_banner* | `str` | Always | Pre-existing system login banner text content string. |
|   ↳ *motd_banner* | `str` | Always | Pre-existing message of the day text content string. |
| **after** | `dict` | Always | State dictionary summarizing the configuration structures active on the node following execution. |
|   ↳ *login_banner* | `str` | Always | Newly applied system login banner text string (evaluates to `null` on deletions). |
|   ↳ *motd_banner* | `str` | Always | Newly applied message of the day text string (evaluates to `null` on deletions). |

---

### Metadata

* **Version Added:** `0.0.1`
* **Author:** Uzma Saman (@NetOpsChic)