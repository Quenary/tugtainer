#!/bin/bash
set -e
AGENT_ENABLED="${AGENT_ENABLED:-true}"
AGENT_ENABLED=$(echo "$AGENT_ENABLED" | tr '[:upper:]' '[:lower:]')
export AGENT_ENABLED
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf