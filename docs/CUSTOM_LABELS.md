# Custom labels

Tugtainer supports several custom Docker labels to control container behavior, dependencies, and automated tasks.

## Priority over UI settings

Labels defined on containers have **priority over UI settings** in the database for automated (scheduled) jobs:
- If a container defines `dev.quenary.tugtainer.auto_check` or `dev.quenary.tugtainer.auto_update`, its value is enforced during scheduled runs.
- In the web UI, the corresponding switch is hidden and replaced with an informative tag showing the label state (`ON` or `OFF`).
- These labels only affect **scheduled (automated)** background tasks. **Manual** actions (checking or updating manually via the UI or API) are not restricted by `auto_check` or `auto_update` labels.

---

## Supported labels

### `dev.quenary.tugtainer.protected=true`

This label indicates that the container cannot be stopped, restarted, killed, or updated from the app. Even if a newer image exists, the app refuses to update protected containers (both in scheduled and manual runs).

This label is primarily used for **tugtainer** itself, **tugtainer-agent**, and **socket-proxy** in the provided docker-compose setups.

### `dev.quenary.tugtainer.depends_on="my_postgres,my_redis"`

An alternative to the Docker Compose dependency label. Allows declaring dependencies across containers even if they are not in the same compose project.

- Value: Comma-separated list of container names.
- When an updated container starts, its dependencies are started first; when it stops, dependent containers are stopped before it.

### `dev.quenary.tugtainer.auto_check="true" | "false"`

Controls whether the container is included in scheduled (automated) update checks.

- Values: `"true"` / `"1"` / `"yes"` / `"on"` to enable, or `"false"` / `"0"` / `"no"` / `"off"` to disable.
- When set, overrides the container's `check_enabled` database setting during scheduled cron checks.
- In the web UI, the check toggle is replaced by a status tag indicating that auto-check is managed by this label.
- Does not block manual checks (e.g. clicking "Check" on the container or "Check all").

### `dev.quenary.tugtainer.auto_update="true" | "false"`

Controls whether the container is automatically updated when an update is available during scheduled update runs.

- Values: `"true"` / `"1"` / `"yes"` / `"on"` to enable, or `"false"` / `"0"` / `"no"` / `"off"` to disable.
- When set, overrides the container's `update_enabled` database setting during scheduled cron updates.
- In the web UI, the auto-update toggle is replaced by a status tag indicating that auto-update is managed by this label.
- Does not block manual updates (e.g. clicking "Update" on the container).
- If `dev.quenary.tugtainer.protected=true` is also set, protection takes precedence and the container will never be updated.
