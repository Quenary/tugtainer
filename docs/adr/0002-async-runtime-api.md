# ADR 0002: Replace python-on-whales with asynchronous runtime API access

## Status

Accepted — 2026-11-09.

## Context

Tugtainer uses python-on-whales and the Docker/Podman CLI for runtime operations. These operations support container checks and updates, Swarm management and application self-update. Some existing users run Podman rather than Docker.

The backend owns business orchestration, while the agent provides a thin authenticated interface to the container runtime. The self-update helper must remain independent of backend modules.

Future Stacks support would benefit from a reusable runtime API layer, but Stacks and Compose implementation are outside the scope of this migration. Docker Engine API does not expose Compose operations.

## Problem

The current implementation introduces subprocess overhead and requires CLI binaries in application images. Its capabilities and behavior depend on CLI and wrapper versions, and application code relies on library-owned schemas and exception types.

Replacing this dependency must not introduce functional regressions or lose container configuration or data. The CLI currently supplies behavior that direct API access must implement explicitly, including streaming progress, error handling and orchestration details.

Docker and Podman expose different capabilities and API semantics. A single version threshold or an assumed lossless Docker-compatible representation cannot safely cover both runtimes.

## Alternatives

### Retain python-on-whales

Requires the least immediate work, but retains subprocess overhead, CLI dependencies and wrapper limitations. Rejected.

### Use a synchronous Docker SDK with thread offloading

Removes CLI execution but retains a synchronous runtime interface and requires thread management. It also does not eliminate the need to address Podman-specific behavior. Rejected as the target architecture.

### Maintain parallel CLI and HTTP implementations

Allows an incremental runtime fallback, but increases maintenance cost and complicates behavior guarantees. Rejected: the final implementation must not retain a legacy compatibility path.

### Use asynchronous HTTP APIs with runtime-specific adapters

Removes internal CLI execution and gives the application direct control over transport, schemas, streaming and capabilities. Requires explicit compatibility handling and integration coverage. Selected.

## Decision

Replace python-on-whales and internal Docker/Podman CLI execution with direct asynchronous HTTP API access.

### Architecture

- Use a shared asynchronous HTTP transport supporting Unix sockets and TCP, including existing socket-proxy deployments.
- Select the HTTP client during implementation planning based on streaming, cancellation, connection pooling, TLS and testability requirements.
- Keep runtime access thin in the agent and business orchestration in the backend.
- Isolate Docker and Podman differences behind focused adapters without unnecessarily duplicating common functionality.
- Use project-owned Pydantic schemas, separating runtime representations from application API contracts.
- Share necessary low-level functionality with the self-update helper without importing backend modules into the helper.
- Replace internal CLI commands with typed runtime operations. Preserve unrelated user hooks and intentional command execution.

### Compatibility

- Require Docker Engine 25.0 or newer and Docker API 1.44 or newer.
- Negotiate API versions within both the daemon's supported range and the client's explicitly supported/tested range. Do not automatically use untested future API versions.
- Distinguish the application's compatibility floor from upstream security support; recommend a currently supported Engine for production.
- Detect Podman separately and do not apply Docker's version floor to it.
- Use Podman's compatibility API where semantics are verified and native Libpod operations where necessary to preserve configuration.
- Establish the minimum supported Podman version during planning and integration testing, covering rootful and rootless deployments.
- Treat Swarm as a Docker-only capability.

### Behavior and safety

- Inventory existing functionality and implicit CLI behavior before implementation, and verify parity with tests.
- Preserve relevant container configuration and data during recreation, including existing anonymous volumes, networking, security settings and runtime-specific options.
- Reject operations before stopping or removing the original container when required configuration cannot be preserved.
- Preserve job coordination, registry authentication, progress reporting, health checks, rollback and self-update behavior, including SQLite backup and restoration.
- Handle streamed errors, cancellation and uncertain mutation outcomes explicitly. Do not blindly retry destructive operations.
- Verify runtime-specific self-identification and helper access rather than assuming Docker behavior applies to Podman.

### Migration and cleanup

- Deliver one coordinated breaking release. Compatibility between old and new backend, frontend and agent versions is not required.
- Preserve persistent application data and provide any necessary database migrations.
- Remove python-on-whales completely, including schemas, dependencies, mocks and obsolete code. Remove CLI installation where no longer required.
- Remove obsolete helpers, including `asyncall` if no consumers remain. Preserve thread offloading needed by unrelated blocking operations.
- Use modern Python syntax consistent with the supported Python version: built-in generic types and union syntax instead of legacy `typing.List`, `typing.Dict` and `typing.Optional`.
- Exclude Stacks, Compose implementation and unrelated features or refactoring.

Completion requires an audited functionality matrix, integration coverage for the established Docker and Podman support ranges, update/rollback/self-update tests, removal of legacy runtime paths, and updated deployment documentation and breaking-release notes.

## Consequences

### Positive

- Removes internal CLI and python-on-whales dependencies.
- Eliminates subprocess overhead for migrated operations.
- Enables direct control over streaming, cancellation and API capabilities.
- Decouples application contracts from library-owned schemas.
- Provides a reusable runtime access layer for future development without coupling this migration to Stacks.

### Negative

- Tugtainer becomes responsible for behavior previously supplied by the CLI or wrapper.
- API negotiation, schema mapping, streaming and runtime differences require ongoing maintenance.
- Faithful container recreation is the primary regression risk and requires substantial integration coverage.
- Podman requires separate capability checks and rootful/rootless testing.
- Users must coordinate backend, frontend and agent upgrades for the breaking release.
- Performance improvements must be measured; runtime-side operations may remain the dominant cost.
