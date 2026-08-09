# Tugtainer application tests (Playwright)

This directory holds **non-unit** tests for Tugtainer: system, integration, and
end-to-end checks against a real app stack. Unit tests live next to the code in
the corresponding application modules.

Layout:

- [`integration/`](./integration) — API / service-level checks (Playwright `request`)
- [`e2e/`](./e2e) — browser flows against the UI
- [`fixtures/`](./fixtures) — shared Playwright fixtures
- [`shared/`](./shared) — shared code used by fixtures/tests

Tests run inside the official Playwright Docker image so the host does not need
browsers or a display.

## Prerequisites

- Docker with Compose v2 (`docker compose`)
- Node.js `^22.12 || ^24` (same as frontend) for `npm ci` in this directory

## Setup

```bash
cd tests
npm ci
```

## Run all tests (app + Playwright in Docker)

Builds and starts the app stack, waits until it is healthy, runs the full
Playwright suite in a container, then tears the stack down (including volumes):

```bash
npm run test:all
```

## Manual steps

Useful when iterating on tests against a long-lived app:

```bash
npm run app:up         # build + start app on http://localhost:9412
npm run test:docker    # run all projects against http://app.tugtainer.test
npm run app:down       # stop and remove volumes
```

## Lint / format

```bash
npm run lint
npm run prettier-check
```

Pre-commit runs the same checks via lint-staged (see root `.pre-commit-config.yaml`).

## Against a running app

Requires the app already up (`npm run app:up`). Defaults to
`BASE_URL=http://localhost:9412`.

```bash
npx playwright install chromium   # once, host browsers
npm test                          # all projects
npm run test:integration          # API only
npm run test:e2e                  # UI only
```

## Image version pin

`docker-compose.test.yml` uses `mcr.microsoft.com/playwright:v1.62.1-jammy`. Keep
that tag in sync with the `@playwright/test` version in `package.json` when
upgrading.

## Notes

- App and runner Compose projects use separate names (`tugtainer-tests-app` /
  `tugtainer-tests-runner`) and share the external network `tugtainer-tests`.
- Inside Docker, tests use `BASE_URL=http://app.tugtainer.test` (FQDN network
  alias). Chromium does not reliably open single-label hosts like `http://app`.
- The Playwright runner mounts `/var/run/docker.sock` so tests can create
  containers via `dockerode` on the same engine the app reaches through
  socket-proxy.
