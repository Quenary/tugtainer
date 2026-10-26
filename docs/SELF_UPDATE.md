# Self-update

Tugtainer can update its own app container. It is off by default.
Enable it with `ALLOW_SELF_UPDATE=true` on the app container.

The update is started manually: click the "Update available" tag next to the version, then **Self-update** in the dialog.
The UI is unavailable for a moment while the container is replaced. The page reloads when the app is back and shows the result.
The result is also sent to the configured [notification](NOTIFICATIONS.md) URLs.

Self-update covers only the app container. The agent and the socket-proxy are not updated by it.

## How it works

A container cannot recreate itself, because stopping it also stops the process that would create the new one.
So the app hands the swap over to a short-lived helper container.

1. The app finds its own container (by id from `/proc/self/mountinfo`, verified with inspect on the enabled hosts).
2. It pulls the image of its current tag, e.g. `ghcr.io/quenary/tugtainer:1`.
   If the pulled image is the one already running, the update stops here with "No newer image" and nothing is changed.
   This is the case for a pinned tag such as `:1.44.3`: the dialog compares GitHub releases, but the self-update pulls the current tag.
3. It writes a plan to `/tugtainer/self_update/plan.json` (mode `0600`) and starts the helper container `<name>-self-update` from the **new** image.
   The helper gets only the Docker access of the app (`DOCKER_HOST` and its network, or the socket mount) and the data volume.
   It has the `dev.quenary.tugtainer.protected` label, so scheduled updates never touch it, and it is removed when it exits.
4. The helper reads the plan, deletes it right away and runs plain Docker operations:
   - rename the app container to `<name>-old`;
   - create the new container under the original name, with the same config as a normal update;
   - stop `<name>-old`;
   - copy the SQLite database files (`tugtainer.db`, `-wal`, `-shm`) to `/tugtainer/self_update/backup/`;
   - start the new container and wait until it is healthy (or running, without a healthcheck), using the healthcheck timeout of the container or its host;
   - remove `<name>-old` and the database copy.
5. If any step fails or the new container is not healthy in time, the helper rolls back:
   it removes the new container, restores the database copy (the new version may have migrated the database already), renames `<name>-old` back and starts it again.
   The old container is only stopped, never removed, until the new one is healthy.
   If the new container cannot be removed, or the database cannot be restored, the rollback stops there and reports `failed`,
   so the old version never starts next to the new one or on a migrated database.

Every step is written to the journal in `/tugtainer/self_update/state.json`.
After the start, the app (new or rolled back) waits for the helper to finish, reports the result once and deletes the state file.
A leftover `<name>-old` is removed only when its id is recorded in that journal as the old container of a successful update.

## Requirements and limitations

- `/tugtainer` must be a volume or a bind mount. Otherwise the data would be lost and the update is refused.
- With SQLite (the default), the database must be inside `/tugtainer`. Other databases are not copied, so a failed update cannot undo their migrations.
- Docker access must work for the helper with what the app has: `DOCKER_HOST` and the app's networks, or a socket mount at `/var/run/docker.sock`.
  TLS settings for a remote Docker host (`DOCKER_TLS_VERIFY`, `DOCKER_CERT_PATH`) are not passed to the helper.
- With the provided socket-proxy setup, the proxy must allow container renames. `CONTAINERS=1` and `POST=1` cover that.
- Without `JWT_SECRET_KEY`, the new container generates a new secret, so you have to sign in again after the update.

## If something goes wrong

If the helper reports `failed` (the rollback did not complete) or `interrupted` (the helper is gone without a result), check the containers:

```bash
docker ps -a --filter name=tugtainer
docker logs <name>-self-update   # only while the helper still exists
cat /path/to/tugtainer_data/self_update/state.json
```

The journal in `state.json` lists the steps that were done.
The database copy stays in `self_update/backup/` in these cases.
To go back by hand: remove the new container if it exists, copy the files from `backup/` back next to `tugtainer.db`, rename `<name>-old` to `<name>` and start it.
