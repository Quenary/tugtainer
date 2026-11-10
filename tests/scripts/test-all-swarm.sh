#!/usr/bin/env bash
# Init Swarm only when this engine is not already a node, run the suite, and
# leave only when this script performed the init.
set -euo pipefail
cd "$(dirname "$0")/.."

state="$(docker info --format '{{.Swarm.LocalNodeState}}')"
inited=0
if [ "$state" != active ]; then
  docker swarm init --advertise-addr 127.0.0.1
  inited=1
else
  echo "Docker is already a Swarm node; this script will not leave the swarm."
fi

cleanup() {
  if [ "$inited" = 1 ]; then
    docker swarm leave --force || true
  fi
}
trap cleanup EXIT

npm run test:all
