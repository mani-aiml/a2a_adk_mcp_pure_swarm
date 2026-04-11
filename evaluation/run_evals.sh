#!/usr/bin/env bash
# run_evals.sh: Execute the full evaluation suite in one command.
#
# Usage:
#   ./evaluation/run_evals.sh              # full suite
#   ./evaluation/run_evals.sh --unit-only  # unit tests only
#   ./evaluation/run_evals.sh --trace-only # trace tests only (requires otel.log)
#   ADK_EVAL_CONFIG=evaluation/test_config.ci.json ./evaluation/run_evals.sh  # adk eval without judge criteria
#
# Requires: pip install -r requirements.txt adk pytest pyyaml
# Docker swarm for integration + trace (or copy otel.log).

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL_DIR="$ROOT/evaluation"
CONFIG="${ADK_EVAL_CONFIG:-$EVAL_DIR/test_config.json}"
RESULTS_DIR="${EVAL_RESULTS_DIR:-$ROOT/eval_results}"
mkdir -p "$RESULTS_DIR"

echo "======================================================="
echo " Swarm Agent Evaluation Suite"
echo " Root: $ROOT"
echo " Config: $CONFIG"
echo "======================================================="

UNIT_ONLY=false
TRACE_ONLY=false

for arg in "$@"; do
    case $arg in
        --unit-only) UNIT_ONLY=true ;;
        --trace-only) TRACE_ONLY=true ;;
    esac
done

if [ "$TRACE_ONLY" = false ]; then
    echo ""
    echo "--- UNIT EVALUATIONS (ADK eval, registry-driven) ---"

    while IFS= read -r pkg; do
        echo "Running: adk eval $pkg"
        adk eval "$pkg" "$EVAL_DIR/golden/$pkg/evalset.json" --config_file_path "$CONFIG"
    done < <(python3 "$EVAL_DIR/list_eval_packages.py")

    echo ""
    echo "--- UNIT TESTS (pytest) ---"
    pytest "$EVAL_DIR/unit/" -v --junitxml="$RESULTS_DIR/unit_tests.xml"

    if [ "$UNIT_ONLY" = false ]; then
        echo ""
        echo "--- INTEGRATION TESTS (pytest, requires Docker swarm) ---"
        pytest "$EVAL_DIR/integration/" -v --junitxml="$RESULTS_DIR/integration_tests.xml"

        echo ""
        echo "--- FULL SWARM TRAJECTORY EVAL (ADK eval) ---"
        adk eval orchestrator \
            "$EVAL_DIR/golden/swarm/trajectory_evalset.json" \
            --config_file_path "$CONFIG"
    fi
fi

if [ "$UNIT_ONLY" = false ]; then
    echo ""
    echo "--- TRACE QUALITY TESTS (requires OTEL JSONL) ---"
    TRACE_LOG=""
    for p in "$ROOT/otel_logs/otel.log" "$ROOT/otel.log"; do
        if [ -f "$p" ]; then TRACE_LOG="$p"; break; fi
    done
    if [ -n "$TRACE_LOG" ]; then
        pytest "$EVAL_DIR/trace_eval/test_trace_quality.py" -v --log-path "$TRACE_LOG" --junitxml="$RESULTS_DIR/trace_tests.xml"
    else
        echo "Skipping trace tests: no file at $ROOT/otel_logs/otel.log or $ROOT/otel.log"
        echo "After docker compose orchestrator, traces are under otel_logs/otel.log (directory bind mount)."
    fi
fi

echo ""
echo "--- COLLECTING EVAL RESULTS ---"
for agent_dir in "$ROOT"/*/; do
    hist="$agent_dir.adk/eval_history"
    if [ -d "$hist" ]; then
        agent_name="$(basename "$agent_dir")"
        mkdir -p "$RESULTS_DIR/adk_eval/$agent_name"
        cp "$hist"/*.json "$RESULTS_DIR/adk_eval/$agent_name/" 2>/dev/null || true
    fi
done
echo "Results saved to $RESULTS_DIR"

echo ""
echo "--- GENERATING HTML REPORT ---"
python3 "$EVAL_DIR/generate_report.py" --results-dir "$RESULTS_DIR"

echo ""
echo "======================================================="
echo " Evaluation suite complete."
echo " HTML report: $RESULTS_DIR/eval_report.html"
echo "======================================================="
