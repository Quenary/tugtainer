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
- The `self-update` project replaces the app container, so it depends on the
  `integration` and `e2e` projects and runs last. The app runs from
  `localhost:5000/tugtainer:tests`; the test pushes images to the `registry:2`
  service, which publishes port `5000` on the host so the Docker daemon can
  pull from it.
- The Playwright runner mounts `/var/run/docker.sock` so tests can create
  containers via `dockerode` on the same engine the app reaches through
  socket-proxy.
- `fixtures/outdated-alpine-extra-network.fixture.ts` starts an outdated
  container with the host and network settings recreate has to keep: static
  addresses, ports, an exec-form healthcheck with nanosecond durations and
  `StartInterval`, resources, long-syntax mount options, a read-only bind with
  a SELinux flag, and `GwPriority` when the daemon API is 1.48 or newer.
  `VolumeOptions.Subpath` and `TmpfsOptions.Options` are set only when the
  daemon API allows them. `shared/util/container-config.util.ts`
  `pickPreservedConfig` compares those fields before and after an update, and
  `pickHostMounts` compares `HostConfig.Mounts`. Image id, runtime state,
  image labels, and addresses assigned by Docker are not part of that
  comparison.
- `integration/prune-images.spec.ts` prunes only images labeled
  `dev.quenary.tugtainer.prune=<suffix>`, so a dangling prune and a
  `prune_all` prune do not delete alpine or registry images used by other
  tests.
- Registry scenarios push to `registry:2` on `localhost:5000`. The daemon
  pulls that name from the published port. The app container forwards its own
  `localhost:5000` to the registry service so digest checks use the same name.
  Those tests set `INSECURE_REGISTRIES` to the local registry hosts and leave
  it there for the rest of the run.
- `private-registry` (`localhost:5001`) requires HTTP basic auth. The test
  user is `tugtest` and the password is `tugtest-secret`. The app mounts
  `fixtures/private-registry/config.json` at `/root/.docker/config.json`.
  `unauthorized-registry` (`localhost:5002`) uses the same password file and
  is absent from that config, so a pull is rejected.
