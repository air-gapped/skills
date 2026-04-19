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
for RATE in "${RATES[@]}"; do
  OUT="sweep-${TAG}-${RATE}.json"
  [[ -f "$OUT" ]] || continue
  python3 -c "
import json, sys
d = json.load(open('$OUT'))
rps = d.get('request_throughput', d.get('requests_per_second', 0))
p99_ttft = d.get('p99_ttft_ms', 0)
p99_itl = d.get('p99_itl_ms', 0)
tok_s = d.get('total_token_throughput', d.get('output_throughput', 0))
print(f'rate=$RATE  rps={rps:.2f}  p99_ttft={p99_ttft:.0f}ms  p99_itl={p99_itl:.0f}ms  tok/s={tok_s:.0f}')
"
done
