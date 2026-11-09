# AGENTS.md — Agent

FastAPI daemon on a Docker/Podman host. The backend calls it over HTTP; this process talks to the local container runtime API directly via asynchronous HTTP (`RuntimeClient`). Python `>=3.13`.

General rules (scope, Python, tests, checks) are in the root [AGENTS.md](../AGENTS.md). Repo workflow: [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md). Deploy notes: [README.md](README.md). Local entry: `uv run python -m agent.dev` (port 8001).

## Layout

- `app.py` — app (`root_path="/api"`), router includes, `lifespan()`, exception handlers.
- `config.py` — `Config.load()` reads env at import.
- `auth.py` — `verify_signature` checks `shared/util/signature.py`.
- `docker_client.py` — shared `RUNTIME_CLIENT` instance (`RuntimeClient`).
- `api/` — routers. Request and response models live in `shared/schemas/`.

Routers: `container`, `image`, `network`, `common`, `service`, `public`.

## Requests

Every router depends on `verify_signature`, except `GET /public/health`. `ALLOW_UNAUTHENTICATED_AGENT=true` skips the check. Exec inside a container stays off unless `ALLOW_EXEC=true`.

`asyncio.TimeoutError` becomes HTTP 500. `RuntimeNotFoundError` becomes HTTP 404. `RuntimeConflictError` becomes HTTP 409. `RuntimeClientError` and `RuntimeEngineError` become HTTP 424. `GET /public/health` catches runtime failures and returns 424.

Swarm routes require a manager (`control_available`). Service list queries Docker Swarm service endpoints directly.

## Tests

Router tests use `TestClient(app)`.

- Factories live in `agent/testing.py`. Fixtures live in `conftest.py`.
- `agent/conftest.py` restores `dependency_overrides`. `agent/api/conftest.py` stubs `verify_signature`. Auth coverage stays in `agent/test_auth.py`.
