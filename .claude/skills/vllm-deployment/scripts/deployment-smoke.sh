#!/usr/bin/env bash
# deployment-smoke.sh — verify a vLLM Kubernetes deployment is observable, healthy, and multi-node-capable.
#
# Usage:
#   ./deployment-smoke.sh <pod-name> [namespace]
#   ./deployment-smoke.sh vllm-0 inference
#
# Exits non-zero on any fail.

set -u
POD="${1:?usage: $0 <pod-name> [namespace]}"
NS="${2:-default}"
KUBECTL="kubectl -n $NS"
RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
FAIL=0

pass() { echo "${GREEN}[PASS]${RESET} $*"; }
warn() { echo "${YELLOW}[WARN]${RESET} $*"; }
fail() { echo "${RED}[FAIL]${RESET} $*"; FAIL=$((FAIL + 1)); }

echo "=== vLLM deployment smoke test — pod=$POD ns=$NS ==="

# 1. Pod exists and is Running
phase=$($KUBECTL get pod "$POD" -o jsonpath='{.status.phase}' 2>/dev/null)
if [[ "$phase" != "Running" ]]; then
  fail "pod phase is '$phase' (expected Running)"
  exit $FAIL
fi
pass "pod is Running"

# 2. /health returns 200
if $KUBECTL exec "$POD" -- curl -fsS --max-time 5 http://localhost:8000/health >/dev/null 2>&1; then
  pass "/health returns 200"
else
  fail "/health did not return 200 — engine not ready or wrong port"
fi

# 3. /v1/models returns at least one model
if $KUBECTL exec "$POD" -- curl -fsS --max-time 5 http://localhost:8000/v1/models 2>/dev/null | grep -q '"id"'; then
  pass "/v1/models lists at least one model"
else
  fail "/v1/models empty or unreachable"
fi

# 4. /dev/shm is at least 1 GiB (required for TP>1)
shm_size=$($KUBECTL exec "$POD" -- sh -c 'df -m /dev/shm | tail -1 | awk "{print \$2}"' 2>/dev/null)
if [[ -z "$shm_size" ]]; then
  warn "could not read /dev/shm size"
elif (( shm_size < 1024 )); then
  fail "/dev/shm is ${shm_size} MiB — multi-GPU will segfault on first all-reduce. Mount emptyDir{medium: Memory, sizeLimit: 10Gi}."
else
  pass "/dev/shm is ${shm_size} MiB"
fi

# 5. Prometheus /metrics surface present (pair with vllm-observability skill)
metrics=$($KUBECTL exec "$POD" -- curl -sS --max-time 5 http://localhost:8000/metrics 2>/dev/null | grep -c '^vllm:' || true)
if (( metrics >= 10 )); then
  pass "/metrics exposes $metrics vllm: series"
else
  warn "/metrics has $metrics vllm: series (expected ≥10 — check engine fully initialised)"
fi

# 6. NCCL / multi-node env present on multi-GPU pods
tp=$($KUBECTL exec "$POD" -- printenv 2>/dev/null | grep -oP 'tensor-parallel-size[= ]+\K[0-9]+' | head -1)
nccl_iface=$($KUBECTL exec "$POD" -- printenv NCCL_SOCKET_IFNAME 2>/dev/null || true)
vllm_ip=$($KUBECTL exec "$POD" -- printenv VLLM_HOST_IP 2>/dev/null || true)
if [[ -n "$tp" && "$tp" -gt 1 ]]; then
  [[ -n "$nccl_iface" ]] && pass "NCCL_SOCKET_IFNAME=$nccl_iface" || warn "NCCL_SOCKET_IFNAME not pinned (TP=$tp, multi-NIC hosts at risk)"
  [[ -n "$vllm_ip"    ]] && pass "VLLM_HOST_IP=$vllm_ip"        || warn "VLLM_HOST_IP not set from status.podIP (multi-node only)"
fi

# 7. Usage-stats opt-out on regulated/air-gapped clusters
stats=$($KUBECTL exec "$POD" -- printenv VLLM_NO_USAGE_STATS 2>/dev/null || true)
if [[ -z "$stats" ]]; then
  warn "VLLM_NO_USAGE_STATS not set — vLLM will POST to stats.vllm.ai (set to 1 on regulated/air-gapped)"
fi

# 8. Image tag discipline
img=$($KUBECTL get pod "$POD" -o jsonpath='{.spec.containers[0].image}' 2>/dev/null)
if [[ "$img" == *":latest" || "$img" != *":"* ]]; then
  fail "image tag is ':latest' or missing — pin to a version (image: $img)"
else
  pass "image pinned: $img"
fi

echo
if (( FAIL > 0 )); then
  echo "${RED}=== $FAIL check(s) failed ===${RESET}"
  exit 1
fi
echo "${GREEN}=== all critical checks passed ===${RESET}"
