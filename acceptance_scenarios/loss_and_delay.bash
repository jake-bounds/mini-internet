#!/usr/bin/env bash

SEED="${1:-1}"
PROBE_TIMEOUT=5

export RUN_ID=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 6)
export PYTHONUNBUFFERED=1

PIDS=()
stop() {
    kill "${PIDS[@]}" 2>/dev/null || true
    wait 2>/dev/null || true
    PIDS=()
}
trap stop EXIT

echo "Run Id: $RUN_ID  Seed: $SEED"

# run_case <name> <topology> <conditions> <num_probes>
run_case() {
    local name="$1"
    local topology="topology/$2.toml"
    local conditions="conditions/$3.toml"
    local num_probes="$4"
    LOG_DIR="logs/loss_and_delay/$name"
    mkdir -p "$LOG_DIR"
    rm -f "$LOG_DIR"/*.log

    echo
    echo "=== $name  Topology: $topology  Conditions: $conditions"

    for r in "Router A" "Router B" "Router C" "Router D"; do
        uv run router \
            --addr "$r" --topology "$topology" --network-conditions "$conditions" --seed "$SEED" \
            >"$LOG_DIR/${r}.log" 2>&1 &
        PIDS+=($!)
    done

    sleep $((PROBE_TIMEOUT + 5)) | uv run host \
        --addr "Host 2" --topology "$topology" --network-conditions "$conditions" --seed "$SEED" \
        >"$LOG_DIR/Host 2.log" 2>&1 &
    PIDS+=($!)

    {
        sleep 1
        seq -f "Host 2:$name-%g" 1 "$num_probes"
        sleep $((PROBE_TIMEOUT + 2))
    } | uv run host \
        --addr "Host 1" --topology "$topology" --network-conditions "$conditions" --seed "$SEED" \
        >"$LOG_DIR/Host 1.log" 2>&1 &
    PIDS+=($!)
    wait "${PIDS[@]: -1}"

    stop
}

show() {
    echo "-- $1"
    grep -v "^Using seed\|^To send" "$LOG_DIR/$1.log"
}

# Forced drop
run_case forced_drop upper forced_loss 1
show "Router A"
show "Host 1"

# Random loss
run_case random_loss upper loss 20
ok=$(grep -c "^Response received" "$LOG_DIR/Host 1.log")
lost=$(grep -c "^No response received" "$LOG_DIR/Host 1.log")
drops=$(grep -c "drop" "$LOG_DIR/Router A.log")
echo "Host 1: $ok/20 responses, $lost timeouts. Router A: $drops drops"

# Delay
run_case delay upper delay 3
show "Host 1"

# Late response
run_case late_response lower delay 1
show "Router C"
show "Host 1"
