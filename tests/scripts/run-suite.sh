#!/usr/bin/env bash
# One suite against the host engine or a nested Docker 24 daemon.
# TUGTAINER_ENGINE=24 starts that daemon and leaves the host engine alone.
# TUGTAINER_SWARM=1 inits Swarm on the target daemon when it is not already a
# node, and leaves only when this run performed the init.
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
tests_dir=$(cd "$script_dir/.." && pwd)
root=$(cd "$tests_dir/.." && pwd)
cd "$tests_dir"

engine=${TUGTAINER_ENGINE:-host}
dind_name=tugtainer-docker24
api_port=23754
app_port=9414
swarm_inited=0

host_docker() {
  docker -H unix:///var/run/docker.sock "$@"
}

compose_app() {
  docker compose -p tugtainer-tests-app -f "$tests_dir/docker-compose.app.yml" "$@"
}

compose_runner() {
  docker compose -p tugtainer-tests-runner -f "$tests_dir/docker-compose.test.yml" "$@"
}

cleanup() {
  local status=$?
  compose_app down -v || true
  if [[ "$swarm_inited" -eq 1 ]]; then
    docker swarm leave --force || true
  fi
  if [[ "$engine" == 24 ]]; then
    # The dind image declares VOLUME /var/lib/docker. -v drops that anonymous
    # volume; otherwise each run leaves the Engine 24 graph on the host.
    host_docker rm -fv "$dind_name" >/dev/null 2>&1 || true
  fi
  exit "$status"
}
trap cleanup EXIT

if [[ "$engine" == 24 ]]; then
  export DOCKER_HOST="tcp://127.0.0.1:${api_port}"
  # Playwright's npm cache is a bind mount. The nested daemon only sees the
  # repo mount, so the cache has to live inside it.
  cache=${TUGTAINER_NPM_CACHE:-}
  if [[ -z "$cache" || ( "$cache" != "$root" && "$cache" != "$root"/* ) ]]; then
    cache=$root/.npm
  fi
  mkdir -p "$cache"
  export TUGTAINER_NPM_CACHE=$cache

  host_docker rm -fv "$dind_name" >/dev/null 2>&1 || true
  host_docker run -d --name "$dind_name" --privileged \
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
    host_docker logs "$dind_name" >&2 || true
    exit 1
  fi
fi

if [[ "${TUGTAINER_SWARM:-}" == 1 ]]; then
  state=$(docker info --format '{{.Swarm.LocalNodeState}}')
  if [[ "$state" != active ]]; then
    if docker swarm init --advertise-addr 127.0.0.1; then
      swarm_inited=1
    else
      echo "Swarm init failed, Swarm specs will be skipped" >&2
      export TUGTAINER_SWARM=0
    fi
  else
    echo "Docker is already a Swarm node; this script will not leave the swarm."
  fi
fi

compose_app up -d --build --wait
if [[ "$engine" == 24 ]]; then
  # The build cache is not needed once the containers are up. Dropping it
  # leaves room in the dind volume for the self-update pull.
  docker builder prune -af >/dev/null
fi

# On the app network, talking to app.tugtainer.test. The published port on the
# host goes through two proxies, and a request on a reused connection is reset
# after the self-update spec attaches a network.
status=0
compose_runner run --rm playwright || status=$?
if [[ "$status" -ne 0 ]]; then
  echo '--- containers ---' >&2
  docker ps -a >&2 || true
  echo '--- app logs ---' >&2
  docker logs tests-tugtainer --tail 200 >&2 || true
  echo '--- helper logs ---' >&2
  docker logs tests-tugtainer-self-update --tail 200 >&2 || true
fi
exit "$status"
