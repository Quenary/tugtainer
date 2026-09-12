# Healthcheck monitoring

Tugtainer can periodically inspect Docker healthchecks across all enabled hosts. It tracks container health status transitions, automatically restarts failing containers with backoff, sends notifications when containers become unhealthy or recover, and keeps an audit history log.

## How it works

1. **Detection**: Runs periodically on a crontab schedule (`HEALTH_MONITOR_CRON_EXPR`). Containers without configured Docker healthchecks are skipped.
2. **Failure tracking**: Tracks consecutive unhealthy checks (`consecutive_failures`) and restart attempts per container in the database.
3. **Automatic restarts (backoff)**:
   - When consecutive failures reach `(restart_attempts + 1) * HEALTH_MONITOR_N_TO_RESTART`, Tugtainer restarts the container.
   - Restarts are capped at `HEALTH_MONITOR_RESTART_ATTEMPTS`.
   - After restart, Tugtainer waits for the container to become healthy up to the configured timeout.
   - **Disabled by default** (`HEALTH_MONITOR_N_TO_RESTART = -1`) to avoid unexpected or unsafe container restarts. Set to a positive number (e.g. `3`) to enable.
4. **Notifications**:
   - Sent when consecutive failures reach `HEALTH_MONITOR_N_TO_NTFY` and the container has not been notified yet.
   - When an unhealthy container recovers to `healthy`, a recovery notification is sent, and failure counters are reset.
   - Set `HEALTH_MONITOR_N_TO_NTFY` to a value less than `0` (or `0`) to disable notifications.
   - See [Notifications](./NOTIFICATIONS.md#health-monitor-notifications) for template details.
5. **History and retention**:
   - Each healthcheck status event is saved to the history database.
   - Old history records older than `HEALTH_MONITOR_HISTORY_DAYS` are automatically cleaned up.
   - Set `HEALTH_MONITOR_HISTORY_DAYS` to a value less than `0` to keep records indefinitely.

## Settings

Settings can be adjusted in the Web UI (**Menu -> Settings**):

| Setting | Default | Description |
|---|---|---|
| `HEALTH_MONITOR_CRON_EXPR` | `*/3 * * * *` | Crontab expression for the periodic healthcheck job. |
| `HEALTH_MONITOR_N_TO_RESTART` | `-1` | Number of consecutive unhealthy checks before attempting restart (`-1` disables restarts by default). |
| `HEALTH_MONITOR_N_TO_NTFY` | `3` | Number of consecutive unhealthy checks before sending a notification (`< 0` disables notifications). |
| `HEALTH_MONITOR_RESTART_ATTEMPTS` | `3` | Maximum restart attempts for an unhealthy container. |
| `HEALTH_MONITOR_HISTORY_DAYS` | `7` | Days to retain healthcheck history records (`< 0` retains indefinitely). |
| `HEALTH_MONITOR_NTFY_BODY_TMPL` | (built-in) | Jinja2 template for healthcheck notification body. |

## Timeouts and container overrides

When waiting for a container to become healthy after restart, Tugtainer uses the following timeout resolution (in seconds):

1. Per-container override: configured in the container card UI.
2. Host setting: `CONTAINER_HC_TIMEOUT` configured in Host Settings.
3. Fallback default: 60 seconds.

## Web UI

- **Dashboard**: Host dashboard displays a summary of healthy and unhealthy containers, along with a **Healthcheck Monitoring** tile.
- **History table**: Clicking the tile opens `/hosts/:id/health`, showing a paginated history table with timestamp, container name, health status, restart flag, and notification flag.
