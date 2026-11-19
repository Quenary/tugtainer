# ADR 0003: Support Docker API 1.43

## Status

Accepted — 2026-11-20. Supersedes the Docker compatibility floor in [ADR 0002](0002-async-runtime-api.md). The rest of that decision stays in effect.

## Context

ADR 0002 required Docker Engine 25.0 and API 1.44. Docker Engine 24 speaks API 1.43. That API is what many Synology DSM hosts run, and it is still widely used.

## Alternatives

### Do not support API 1.43

Keep the floor at Engine 25.0 and API 1.44. Rejected: it leaves out many Synology hosts.

### Support API 1.43

Lower the Docker floor to Engine 24.0 and API 1.43. Selected.

## Decision

Support Docker API 1.43. It ships on many Synology systems and remains popular.
