#!/bin/sh
set -eu

# Start FalkorDB locally inside this container.
 /var/lib/falkordb/bin/run.sh redis-server \
  --bind 127.0.0.1 \
  --port 6379 \
  --protected-mode yes \
  --dir /tmp \
  --loadmodule /var/lib/falkordb/bin/falkordb.so &

DB_PID=$!

# Wait for FalkorDB before starting FastAPI.
READY=0
for attempt in $(seq 1 30); do
  if redis-cli -h 127.0.0.1 -p 6379 ping 2>/dev/null | grep -q PONG; then
    READY=1
    break
  fi
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "FalkorDB did not start."
  kill "$DB_PID" 2>/dev/null || true
  exit 1
fi

echo "FalkorDB is ready. Starting TraceFix API."

exec uvicorn api.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-10000}"