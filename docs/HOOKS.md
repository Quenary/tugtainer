# Hooks

A container can run a shell command at `pre_update`, `post_update`, `pre_stop`, `pre_rollback`, and `post_rollback`. The agent executes it as `sh -c` inside that container. The app does not ship database or service backup commands. The command and its output are part of the container configuration.

Both gates must be on. `ALLOW_HOOKS` on the backend hides the form and never calls exec while it is off. `ALLOW_EXEC` on that host's agent refuses exec even when the backend asks.

Every command in a hook runs. Any error counts as a failure of that hook. Other containers in the same batch continue.

| Hook | When | On failure |
| --- | --- | --- |
| `pre_stop` | Every container the update is about to stop, including a dependent that is only restarted | That container is not stopped |
| `pre_update` | The container being recreated, after `pre_stop` succeeded | That container is not stopped or recreated |
| `post_update` | After the new container is healthy | Recorded. The update is already done |
| `pre_rollback` | While the failed container is still running, before it is stopped for rollback | Recorded. Rollback continues |
| `post_rollback` | After the previous container has been started | Recorded. Rollback is already done |

The form is hidden for a [protected](CUSTOM_LABELS.md) container, because the app never updates one.
