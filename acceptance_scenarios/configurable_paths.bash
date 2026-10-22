#!/usr/bin/env bash

TOPOLOGY="topology/${1:-upper}.toml"
SEED="${2:-1}"
CONDITIONS="conditions/none.toml"
PROBE_TIMEOUT=5

export RUN_ID=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 6)

LOG_DIR="logs/configurable_paths"
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
for h in "Host 1" "Host 2"; do
    if [[ "$h" == "Host 1" ]]; then dest="Host 2"; tag="h1"; else dest="Host 1"; tag="h2"; fi
    {
        sleep 1
        echo "$dest:msg-$tag"
        sleep $((PROBE_TIMEOUT + 1))
    } | uv run host \
        --addr "$h" --topology "$TOPOLOGY" --network-conditions "$CONDITIONS" --seed "$SEED" \
        >"$LOG_DIR/${h}.log" 2>&1 &
    PIDS+=($!)
done
HOST_PIDS=("${PIDS[@]: -2}")

wait "${HOST_PIDS[@]}"

# Router logs
for r in "Router A" "Router B" "Router C" "Router D"; do
    echo
    echo "== $r"
    cat "$LOG_DIR/${r}.log"
done

