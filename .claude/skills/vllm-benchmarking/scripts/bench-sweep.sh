#!/usr/bin/env bash
#
# Parametrized request-rate sweep for vLLM. Emits one JSON per rate for plotting
# throughput-vs-P99 curves. Use for change comparison — run this twice (before
# and after the change) with identical args, then diff the output files.
#
# Usage: bench-sweep.sh <model> <base-url> <dataset-path> [tag] [rates...]
#   model:        model ID passed to --model
#   base-url:     e.g. http://vllm.svc.cluster.local:8000
#   dataset-path: path to sharegpt JSON or custom JSONL
#   tag:          label baked into output filenames (default: "run")
#   rates:        space-separated rates (default: 1 2 4 8 16 32 inf)
#
# Output: sweep-<tag>-<rate>.json in the current directory.
# Exit:   0 only when every rate has its JSON with failed == 0 and the P99
#         TTFT/ITL fields; 2 otherwise (the summary names the unusable rates).
#
# Every rate replays the same seeded prompts, so a warm prefix cache from the
# previous run would inflate the next one. The script resets the server's caches
# before each measured run; that needs VLLM_SERVER_DEV_MODE=1 on the server. Without
# it the script warns and the numbers after the first rate are cache-assisted.

set -euo pipefail

MODEL="${1:?model is required, e.g. meta-llama/Llama-3.1-70B-Instruct}"
BASE_URL="${2:?base-url is required, e.g. http://localhost:8000}"
DATASET_PATH="${3:?dataset-path is required}"
TAG="${4:-run}"
shift 4 2>/dev/null || shift 3 2>/dev/null || true
if [ "$#" -eq 0 ]; then
  RATES=(1 2 4 8 16 32 inf)
else
  RATES=("$@")
fi

# Detect dataset format by extension
if [[ "$DATASET_PATH" == *.jsonl ]]; then
  DATASET_NAME=custom
else
  DATASET_NAME=sharegpt
fi

reset_caches() {
  local ep
  for ep in reset_prefix_cache reset_mm_cache reset_encoder_cache; do
    if ! curl -sf -X POST "${BASE_URL}/${ep}" >/dev/null; then
      echo "WARN: POST ${BASE_URL}/${ep} failed (server lacks VLLM_SERVER_DEV_MODE=1?); this run reuses a warm cache" >&2
      return 0
    fi
  done
}

# Pre-flight warmup — 50 requests at a modest rate
echo "=== Warmup ==="
vllm bench serve \
  --model "$MODEL" \
  --base-url "$BASE_URL" \
  --dataset-name "$DATASET_NAME" \
  --dataset-path "$DATASET_PATH" \
  --num-prompts 50 \
  --request-rate 4 \
  --save-result --output-json "sweep-${TAG}-warmup.json" \
  >/dev/null
echo "Warmup complete."
echo

for RATE in "${RATES[@]}"; do
  OUT="sweep-${TAG}-${RATE}.json"
  echo "=== rate=${RATE} -> ${OUT} ==="
  reset_caches
  vllm bench serve \
    --model "$MODEL" \
    --base-url "$BASE_URL" \
    --dataset-name "$DATASET_NAME" \
    --dataset-path "$DATASET_PATH" \
    --num-prompts 1000 \
    --request-rate "$RATE" \
    --percentile-metrics ttft,tpot,itl,e2el \
    --metric-percentiles 50,90,95,99 \
    --save-result --output-json "$OUT"
  echo
done

echo "=== Summary ==="
BAD=0
for RATE in "${RATES[@]}"; do
  OUT="sweep-${TAG}-${RATE}.json"
  if [[ ! -f "$OUT" ]]; then
    echo "rate=${RATE}  MISSING ${OUT}"
    BAD=1
    continue
  fi
  python3 - "$OUT" "$RATE" <<'PY' || BAD=1
import json
import sys

path, rate = sys.argv[1], sys.argv[2]
d = json.load(open(path))


def fmt(key, spec, unit=""):
    v = d.get(key)
    return f"{v:{spec}}{unit}" if isinstance(v, (int, float)) else "n/a"


failed = d.get("failed")
print(
    f"rate={rate}  rps={fmt('request_throughput', '.2f')}"
    f"  p99_ttft={fmt('p99_ttft_ms', '.0f', 'ms')}"
    f"  p99_itl={fmt('p99_itl_ms', '.0f', 'ms')}"
    f"  tok/s={fmt('total_token_throughput', '.0f')}"
    f"  completed={d.get('completed', 'n/a')}  failed={failed if failed is not None else 'n/a'}"
)
missing = [k for k in ("request_throughput", "p99_ttft_ms", "p99_itl_ms") if k not in d]
if failed != 0 or missing:
    print(f"  NOT USABLE: failed={failed} missing={missing or 'none'}", file=sys.stderr)
    sys.exit(1)
PY
done

if [[ "$BAD" -ne 0 ]]; then
  echo "One or more rates failed requests or lack metrics. Re-run them before comparing." >&2
  exit 2
fi
