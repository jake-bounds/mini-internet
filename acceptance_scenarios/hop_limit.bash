#!/usr/bin/env bash

TOPOLOGY="topology/loop.toml"
SEED="${2:-1}"
CONDITIONS="conditions/none.toml"
PROBE_TIMEOUT=5

export RUN_ID=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 6)

LOG_DIR="logs/hop_limit"
mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR"/*.log

export PYTHONUNBUFFERED=1

PIDS=()
cleanup() {
    kill "${PIDS[@]}" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT

echo "Run Id: $RUN_ID"
echo "Topology: $TOPOLOGY Conditions: $CONDITIONS  Seed: $SEED"
echo "Logs: $LOG_DIR"

# Launch routers
for r in "Router A" "Router B" "Router C" "Router D"; do
    uv run router \
        --addr "$r" --topology "$TOPOLOGY" --network-conditions "$CONDITIONS" --seed "$SEED" \
        >"$LOG_DIR/${r}.log" 2>&1 &
    PIDS+=($!)
done

# Launch hosts
{
    echo "Host 2:loop test"
} | uv run host \
    --addr "Host 1" --topology "$TOPOLOGY" --network-conditions "$CONDITIONS" --seed "$SEED" \
    >"$LOG_DIR/Host 1.log" 2>&1 &
PIDS+=($!)
wait "${PIDS[@]: -1}"

# Router logs
for r in "Router A" "Router C"; do
    echo
    echo "== $r"
    cat "$LOG_DIR/${r}.log"
done

