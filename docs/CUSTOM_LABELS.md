# Custom labels

Labels on a container override the stored check and update switches for scheduled jobs. The UI hides the switch and shows the label state (`ON` or `OFF`). Manual check and update ignore `auto_check` and `auto_update`.

`hidden`, `protected`, `auto_check`, and `auto_update` share the same values. Comparison ignores case and surrounding whitespace.

| Effect | Values |
| --- | --- |
| Enabled | `true`, `1`, `yes`, `on` |
| Disabled | `false`, `0`, `no`, `off` |

An empty or unknown value counts as unset.

| Label | Effect |
| --- | --- |
| `dev.quenary.tugtainer.hidden` | The container is absent from lists, public counts, checks, updates, health monitoring, and manual control. A direct request is answered as if it does not exist. An image used only by it still counts as in use, and the row still counts when stale database rows are cleared. `protected` on the same container is not shown. |
| `dev.quenary.tugtainer.protected` | Start, stop, restart, kill, pause, unpause, and update are refused, including a manual run. The container stays visible. Health monitoring can still restart it. The provided Compose files set the label on the app, the agent, and the socket-proxy. |
| `dev.quenary.tugtainer.depends_on` | Comma-separated container names, including across Compose projects. Dependencies start first and stop after the dependent container. See [Check and update](CHECK_AND_UPDATE.md). |
| `dev.quenary.tugtainer.auto_check` | Forces scheduled checks on or off, overriding `check_enabled`. |
| `dev.quenary.tugtainer.auto_update` | Forces scheduled updates on or off, overriding `update_enabled`. `protected` and `hidden` still win. |
