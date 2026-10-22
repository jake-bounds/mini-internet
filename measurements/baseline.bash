#!/usr/bin/env bash

TOPOLOGY="topology/upper.toml"
CONDITIONS=(delay0_loss0 delay0_loss05 delay100_loss0 delay100_loss05)
SEEDS=(1 2 3)
NUM_PROBES=20
PROBE_INTERVAL=0.2
PROBE_TIMEOUT=5

export RUN_ID=$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 6)
export PYTHONUNBUFFERED=1

OUT_DIR="logs/baseline"
mkdir -p "$OUT_DIR"
RESULTS="$OUT_DIR/results.csv"
echo "condition,seed,probes,responses,timeouts,mean_rtt_ms" >"$RESULTS"

PIDS=()
stop() {
    kill "${PIDS[@]}" 2>/dev/null || true
    wait 2>/dev/null || true
    PIDS=()
}
trap stop EXIT

echo "Run Id: $RUN_ID"
echo "Topology: $TOPOLOGY  Probes: $NUM_PROBES  Interval: ${PROBE_INTERVAL}s  Timeout: ${PROBE_TIMEOUT}s"

for cond in "${CONDITIONS[@]}"; do
    conditions="conditions/baseline/$cond.toml"
    for seed in "${SEEDS[@]}"; do
        LOG_DIR="$OUT_DIR/$cond/seed$seed"
        mkdir -p "$LOG_DIR"
        rm -f "$LOG_DIR"/*.log
        echo "$cond seed $seed"

        for r in "Router A" "Router B" "Router C" "Router D"; do
            uv run router \
                --addr "$r" --topology "$TOPOLOGY" --network-conditions "$conditions" --seed "$seed" \
                >"$LOG_DIR/${r}.log" 2>&1 &
            PIDS+=($!)
        done

        sleep $((PROBE_TIMEOUT + 8)) | uv run host \
            --addr "Host 2" --topology "$TOPOLOGY" --network-conditions "$conditions" --seed "$seed" \
            >"$LOG_DIR/Host 2.log" 2>&1 &
        PIDS+=($!)

        {
            sleep 1
            for i in $(seq 1 "$NUM_PROBES"); do
                echo "Host 2:baseline-$i"
                sleep "$PROBE_INTERVAL"
            done
            sleep $((PROBE_TIMEOUT + 1))
        } | uv run host \
            --addr "Host 1" --topology "$TOPOLOGY" --network-conditions "$conditions" --seed "$seed" \
            >"$LOG_DIR/Host 1.log" 2>&1 &
        PIDS+=($!)
        wait "${PIDS[@]: -1}"
        stop

        log="$LOG_DIR/Host 1.log"
        responses=$(grep -c "^Response received" "$log")
        timeouts=$(grep -c "^No response received" "$log")
        mean_rtt=$(grep "^Response received" "$log" | awk '{ s += $(NF-1) } END { if (NR) printf "%.1f", s / NR * 1000 }')
        echo "$cond,$seed,$NUM_PROBES,$responses,$timeouts,$mean_rtt" >>"$RESULTS"
    done
done

# Summary
echo
uv run python - "$RESULTS" <<'EOF'
import csv, statistics, sys

rows = list(csv.DictReader(open(sys.argv[1])))
print(f"{'condition':<18}{'success %':>18}{'mean RTT ms':>22}{'timeouts':>16}")
for cond in dict.fromkeys(r["condition"] for r in rows):
    runs = [r for r in rows if r["condition"] == cond]
    success = [100 * int(r["responses"]) / int(r["probes"]) for r in runs]
    rtt = [float(r["mean_rtt_ms"]) for r in runs if r["mean_rtt_ms"]]
    timeouts = [int(r["timeouts"]) for r in runs]

    def fmt(xs, p=1):
        if not xs:
            return "-"
        sd = statistics.stdev(xs) if len(xs) > 1 else 0
        return f"{statistics.mean(xs):.{p}f} ± {sd:.{p}f}"

    print(f"{cond:<18}{fmt(success):>18}{fmt(rtt, 2):>22}{fmt(timeouts):>16}")
EOF
