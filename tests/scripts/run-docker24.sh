#!/usr/bin/env bash
# Check, update (rollback, static IP and MAC, extra network), and self-update
# against a real Docker 24 daemon. The host engine is left alone.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
root=$(cd "$script_dir/../.." && pwd)
name=tugtainer-docker24
api_port=23754
app_port=9414
export DOCKER_HOST="tcp://127.0.0.1:${api_port}"

compose() {
  docker compose -p tugtainer-docker24-app -f "$root/tests/docker-compose.app.yml" "$@"
}

host_docker() {
  docker -H unix:///var/run/docker.sock "$@"
}

cleanup() {
  local status=$?
  compose down -v || true
  # The dind image declares VOLUME /var/lib/docker. -v drops that anonymous
  # volume; otherwise each run leaves the Engine 24 graph on the host.
  host_docker rm -fv "$name" >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT

host_docker rm -fv "$name" >/dev/null 2>&1 || true
host_docker run -d --name "$name" --privileged \
  -v "$root:$root" \
  -p "127.0.0.1:${api_port}:2375" \
  -p "127.0.0.1:${app_port}:9412" \
  -p "127.0.0.1:5000:5000" \
  docker:24.0.9-dind \
  dockerd \
    --host=unix:///var/run/docker.sock \
    --host=tcp://0.0.0.0:2375 \
    --tls=false \
    --insecure-registry=localhost:5000 \
    --insecure-registry=localhost:5001 \
    --insecure-registry=localhost:5002

ready=0
for _ in $(seq 1 60); do
  if docker version >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  echo "Docker 24 daemon did not become ready" >&2
  host_docker logs "$name" >&2 || true
  exit 1
fi

compose up -d --build --wait
# The app image build cache is not needed once the containers are up.
# Dropping it leaves room in the dind volume for the self-update pull.
docker builder prune -af >/dev/null

# Same runner as test:all: on the app network, talking to app.tugtainer.test.
# The published port on the host goes through two proxies, and a request on a
# reused connection is reset after the self-update spec attaches a network.
status=0
docker run --rm \
  --network tugtainer-tests \
  -v "$root/tests:/tests" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e BASE_URL=http://app.tugtainer.test \
  -e CI=true \
  -e DOCKER_SOCKET=/var/run/docker.sock \
  -w /tests \
  --label dev.quenary.tugtainer.protected=true \
  mcr.microsoft.com/playwright:v1.62.1-jammy \
  sh -c 'npm ci && npx playwright test --no-deps integration/check-container.spec.ts integration/update-container.spec.ts && npx playwright test --no-deps self-update/self-update.spec.ts' \
  || status=$?
if [[ "$status" -ne 0 ]]; then
  echo '--- docker 24 containers ---' >&2
  docker ps -a >&2 || true
  echo '--- app logs ---' >&2
  docker logs tests-tugtainer --tail 200 >&2 || true
  echo '--- helper logs ---' >&2
  docker logs tests-tugtainer-self-update --tail 200 >&2 || true
fi
exit "$status"
