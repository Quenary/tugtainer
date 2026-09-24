# Hooks

You can configure shell commands to run inside a container at points of the
update lifecycle: `pre_update`, `post_update`, `pre_stop`, `pre_rollback`,
`post_rollback`. Each command runs as `sh -c "<command>"` inside the target
container via the agent.

Tugtainer has no built-in database/service-specific backup logic — writing
the actual backup/notification commands (e.g. `pg_dump`) and managing where
their output goes is entirely up to you.

This feature is off by default and requires two things to be true at once:

- `ALLOW_HOOKS=true` on the Tugtainer backend (feature gate — hides the UI
  form and stops the backend from ever calling the agent's exec endpoint
  when false).
- `ALLOW_EXEC=true` on the Tugtainer-Agent for the specific host you want to
  run hooks on (defense in depth — an agent that hasn't opted in refuses to
  execute commands even if asked).

Failure semantics:

- A failing `pre_update` or `pre_stop` hook aborts that container's update —
  the container is left running as-is, same as any other pre-flight check
  failure.
- `post_update`, `pre_rollback` and `post_rollback` hook failures are
  report-only (logged) and never block anything — by the time these run,
  either the update already succeeded or a rollback is already underway and
  must complete regardless.
- `pre_rollback` runs while the failed container is still alive, right
  before Tugtainer stops it to roll back.

The hooks form is hidden in the UI for protected containers (see
[Custom labels](CUSTOM_LABELS.md#devquenarytugtainerprotectedtrue)), since protected containers are never
updated by the app.
