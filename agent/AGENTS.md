# AGENTS.md — Agent

FastAPI daemon on a Docker host. The backend calls it over HTTP; this process talks to the local Docker socket through `python_on_whales`. Python `>=3.13`.

General rules (scope, Python, tests, checks) are in the root [AGENTS.md](../AGENTS.md). Repo workflow: [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md). Deploy notes: [README.md](README.md). Local entry: `uv run python -m agent.dev` (port 8001).

## Layout

- `app.py` — app (`root_path="/api"`), router includes, `lifespan()`, exception handlers.
- `config.py` — `Config.load()` reads env at import.
- `auth.py` — `verify_signature` checks `shared/util/signature.py`.
- `docker_client.py` — shared `DOCKER` client.
- `unil/asyncall.py` — runs blocking Docker calls in a thread pool. Default timeout is `Config.DOCKER_TIMEOUT`.
- `api/` — routers. Request and response models live in `shared/schemas/`.

Routers: `container`, `image`, `command`, `network`, `common`, `service`, `public`.

## Requests

Every router depends on `verify_signature`, except `GET /public/health`. `ALLOW_UNAUTHENTICATED_AGENT=true` skips the check. Exec inside a container stays off unless `ALLOW_EXEC=true`.

`asyncio.TimeoutError` becomes HTTP 500. `DockerException` becomes HTTP 424. `GET /public/health` catches a Docker failure itself and returns 424.

Swarm routes require a manager (`control_available`). Service list merges `service inspect` with replica counts from `service ls`.

## Tests

Router tests use `TestClient(app)`.

- Factories live in `agent/testing.py`. Fixtures live in `conftest.py`.
- `agent/conftest.py` restores `dependency_overrides`. `agent/api/conftest.py` stubs `verify_signature`. Auth coverage stays in `agent/test_auth.py`.
