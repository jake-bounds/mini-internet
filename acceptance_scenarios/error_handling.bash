#!/usr/bin/env bash

TOPOLOGY="topology/loop.toml"
SEED="${2:-1}"
CONDITIONS="conditions/none.toml"
PROBE_TIMEOUT=5

export RUN_ID=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 6)

LOG_DIR="logs/error_handling"
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

# Launch host 2
uv run host \
    --addr "Host 2" --topology "$TOPOLOGY" --network-conditions "$CONDITIONS" --seed "$SEED" \
    >"$LOG_DIR/Host 2.log" 2>&1 &
PIDS+=($!)

# Invalid packet
sleep 1
printf '\xff\xfe\x00garbage' > /dev/udp/127.0.0.1/31217

# Host 1
{
    echo "Host 3:unknown destination"
    echo "Host 2:packettoolarge$(head -c 2000 /dev/zero | tr '\0' 'A')"
    sleep 6
} | uv run host \
    --addr "Host 1" --topology "$TOPOLOGY" --network-conditions "$CONDITIONS" --seed "$SEED" \
    >"$LOG_DIR/Host 1.log" 2>&1 &
PIDS+=($!)
wait "${PIDS[@]: -1}"

sleep 1

# Logs
for r in "Host 1" "Router A"; do
    echo
    echo "== $r"
    cat "$LOG_DIR/${r}.log"
done

