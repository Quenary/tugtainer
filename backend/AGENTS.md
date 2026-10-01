# AGENTS.md — Backend

FastAPI app that serves the UI and runs container check, update, health, and cleanup jobs. Python `>=3.13`. Docker work goes through host agents, not a local Docker socket.

Repo workflow and commits: [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md). How to run the app: [README.md](README.md).

## Layout

- `app.py` — FastAPI app (`root_path="/api"`), router includes, `lifespan()`, exception handlers, Socket.IO mount.
- `config.py` — `Config.load()` reads env once. `const.py` holds defaults such as crontab expressions.
- `dev.py` — local entry: Alembic `upgrade head`, then uvicorn with reload.
- `db/` — `BaseModel`, async engine, `async_session_maker`, `get_async_session`.
- `modules/<domain>/` — HTTP and persistence for one area: `*_router.py`, `*_model.py`, `*_schemas.py`, `*_util.py`.
- `core/` — agent HTTP client, cron, sockets, notifications, `jobs/`, `container_util/`.
- `enums/`, `util/` — shared backend helpers.
- `alembic/` — migrations. `env.py` imports every model so autogenerate sees it.

Domains: `auth`, `hosts`, `containers`, `images`, `services`, `health`, `settings`, `public`.

## Startup

`lifespan` runs in this order: issue the password setup code, sync the local agent secret, `load_agents_on_init`, `SettingsStorage.load_all`, `schedule_jobs_on_init`, then stale-container cleanup. Cleanup failures are logged and do not stop startup. Shutdown calls `AgentClientManager.remove_all`.

`socket_manager.init_socket(app)` mounts Socket.IO on the same app. Connections are checked with `is_authorized_cookies`. Job progress is emitted from `jobs_tracker` / `jobs_cache`.

## Request path

Routers are `APIRouter`s with a prefix and `dependencies=[Depends(is_authorized_req)]`. `public_router` and `auth_router` apply that dependency per route. Handlers take `AsyncSession` from `get_async_session`.

A module splits four roles:

- `*_router.py` — routes and HTTP status codes.
- `*_schemas.py` — Pydantic request and response models.
- `*_model.py` — SQLAlchemy rows (`Mapped`, `mapped_column` on `BaseModel`).
- `*_util.py` — queries and rules reused by routers and jobs.

Convert a row with `Schema.model_validate(row)`.

## Agents

The backend does not talk to Docker itself. `AgentClient` (`core/agent_client.py`) signs requests (`shared/util/signature.py`) and calls the host agent over aiohttp. Bodies are `shared/schemas/` models. Inspect results come back as `python_on_whales` models (`ContainerInspectResult`, `ImageInspectResult`).

`AgentClientManager` keeps one client per enabled host and is filled in `lifespan`. `TugAgentClientError` and aiohttp `ClientError` become HTTP 424.

New agent URLs go through `validate_agent_url_against_ssrf` before they are stored. The same helper guards notification URLs.

## Database

`get_async_session` is the request-scoped session. Jobs and startup code open `async_session_maker()` themselves. `expire_on_commit` is off.

`Config.DB_URL` may be plain `sqlite:`, `postgresql+psycopg2:`, or `mysql:`. `db/session.py` rewrites those to the async drivers (`aiosqlite`, `asyncpg`, `asyncmy`).

A model change needs an Alembic revision. Register the model module in `alembic/env.py` before autogenerate. `python -m backend.dev` applies `upgrade head` on startup.

The database stores Tugtainer state, not a copy of the Docker daemon. `HostsModel` is an agent endpoint (URL, secret, TLS, Swarm flag). The local agent is `LOCAL_AGENT_URL` in `const.py`. `ContainersModel` keeps check and update flags, digest cache, previous image identity, and hooks. Live lists and inspect come from the agent on each request.

Container behavior is also driven by labels in `const.py`: `dev.quenary.tugtainer.protected`, `.hidden`, `.depends_on`, `.auto_check`, `.auto_update`. Compose `com.docker.compose.depends_on` is read the same way.

## Jobs

`CronManager` (`aiocron`) schedules check, update, cleanup, and health from `SettingsStorage` during `lifespan`. Subsystems:

- `core/jobs/check/` — per-host and per-container image checks, Swarm services.
- `core/jobs/update/` — recreate and service update, hooks, job plan.
- `core/jobs/health/` — health monitor and history rotation.
- `core/jobs/cleanup/` — clear flags on containers that disappeared from the host.
- `jobs_tracker.py`, `jobs_cache.py`, `jobs_results.py` — progress shared with the UI over Socket.IO.

`host_job_coordinator` stops a second check or update from running on the same host. Check and update functions catch their own failures and return a `ContainerJobResult`. They record slots on `HostJobTracker` instead of raising into the cron runner.

`container_util/` maps inspect data (ports, env, healthcheck, labels) into recreate kwargs. Hidden and protected containers are label filters in `container_labels.py`. Image digests and registry metadata go through `modules/images/`.

`core/notifications_core.py` sends Apprise messages from job results. Templates render in a sandboxed Jinja environment. Notification URLs come from `SettingsStorage`.

Manual check and update from the UI call the same `check_all_hosts` / `update_all_hosts` entry points as cron. Per-container hooks (`EHookName`, `ContainerHooks`) run as agent execs around an update when both `Config.ALLOW_HOOKS` and the agent's exec permission are on. `public_router` exposes version, update availability, and host summaries; the unauthenticated routes stay open only while `Config.ENABLE_PUBLIC_API` is on.

## Settings and auth

`SettingsStorage` is an in-memory snapshot of the `settings` table, loaded in `lifespan`. Read it with `SettingsStorage.get(ESettingKey.…)` so the return type stays overloaded. Cron and job code use this cache, not a query per read.

Auth is JWT (`python-jose`). Password and OIDC providers live in `modules/auth/providers/` and are selected by `AuthProviderType`. `is_authorized_req` is the router dependency. `Config.DISABLE_AUTH` skips it.

Domain errors subclass `TugException` in `exception.py`. Raise `HTTPException` at the router edge; let `TugAgentClientError` reach the app handler.

## Tests

Tests sit next to the code as `test_*.py`. Async tests use `@pytest.mark.asyncio`. Patch with `pytest-mock` (`mocker.patch`) and `AsyncMock`. Router tests build `TestClient(app)`, replace `is_authorized_req` and `get_async_session` through `app.dependency_overrides`, and stub `AgentClientManager`. `backend/modules/conftest.py` restores overrides after each test.

Import `backend` and `shared` as top-level packages. Run pytest from the repo root (`python -m pytest`, or a path under `backend/`).

- Shared factories live in `backend/testing.py` (`patch_async_session`, `make_service`). Fixtures live in `conftest.py`.
- Parametrize near-duplicate cases. Do not add tests for trivial getters.
- Type helpers where it stays simple. Match ruff and mypy.

## Style

Ruff and mypy are configured in the repo `pyproject.toml` (Ruff selects E, F, I, B, UP; mypy allows missing imports and unset optionals). Match the surrounding file.

- Prefer `list[str]`, `str | None`, and `Final` over `typing` aliases the codebase has already dropped.
- Log with `logging`; include the job or container name in the logger. Do not add `print` outside `dev.py`.
- Keep a change inside one module and its tests. A new SQLAlchemy model still needs the `alembic/env.py` import and a migration.
