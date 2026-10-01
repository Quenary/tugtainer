# Custom labels

Tugtainer supports several custom Docker labels to control container behavior, dependencies, and automated tasks.

## Priority over UI settings

Labels defined on containers have **priority over UI settings** in the database for automated (scheduled) jobs:
- If a container defines `dev.quenary.tugtainer.auto_check` or `dev.quenary.tugtainer.auto_update`, its value is enforced during scheduled runs.
- In the web UI, the corresponding switch is hidden and replaced with an informative tag showing the label state (`ON` or `OFF`).
- These labels only affect **scheduled (automated)** background tasks. **Manual** actions (checking or updating manually via the UI or API) are not restricted by `auto_check` or `auto_update` labels.

---

## Boolean values

`hidden`, `protected`, `auto_check`, and `auto_update` share the same values. Comparison ignores case and surrounding whitespace.

- Enabled: `"true"`, `"1"`, `"yes"`, `"on"`.
- Disabled: `"false"`, `"0"`, `"no"`, `"off"`.
- An empty or unknown value is treated as if the label is not set.

## Supported labels

### `dev.quenary.tugtainer.hidden=true`

This label removes the container from Tugtainer entirely. It does not appear in container lists or public counts, and it is excluded from checks, updates, health monitoring, and manual control. A direct request for that container is answered as if the container does not exist.

- Images used only by a hidden container still count as in use, and the container still counts as present when clearing stale database rows.
- If `dev.quenary.tugtainer.protected` is also set, the container stays hidden. Protection is not shown, because the container is outside the app.

### `dev.quenary.tugtainer.protected=true`

This label indicates that the container cannot be stopped, restarted, killed, or updated from the app. Even if a newer image exists, the app refuses to update protected containers (both in scheduled and manual runs). The container stays visible.

This label is primarily used for **tugtainer** itself, **tugtainer-agent**, and **socket-proxy** in the provided docker-compose setups.

### `dev.quenary.tugtainer.depends_on="my_postgres,my_redis"`

An alternative to the Docker Compose dependency label. Allows declaring dependencies across containers even if they are not in the same compose project.

- Value: Comma-separated list of container names.
- When an updated container starts, its dependencies are started first; when it stops, dependent containers are stopped before it.

### `dev.quenary.tugtainer.auto_check="true" | "false"`

Controls whether the container is included in scheduled (automated) update checks.

- When set, overrides the container's `check_enabled` database setting during scheduled cron checks.
- In the web UI, the check toggle is replaced by a status tag indicating that auto-check is managed by this label.
- Does not block manual checks (e.g. clicking "Check" on the container or "Check all").

### `dev.quenary.tugtainer.auto_update="true" | "false"`

Controls whether the container is automatically updated when an update is available during scheduled update runs.

- When set, overrides the container's `update_enabled` database setting during scheduled cron updates.
- In the web UI, the auto-update toggle is replaced by a status tag indicating that auto-update is managed by this label.
- Does not block manual updates (e.g. clicking "Update" on the container).
- If `dev.quenary.tugtainer.protected` is enabled, protection takes precedence and the container will never be updated.
- If `dev.quenary.tugtainer.hidden` is enabled, the container is outside the app and is not updated.
