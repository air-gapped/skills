#!/usr/bin/env bash
# deployment-smoke-selftest.sh — run deployment-smoke.sh against a fake kubectl with
# planted failures and an unreachable cluster. Needs no cluster. Exits non-zero if a
# planted failure is not reported.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d -t deployment-smoke-selftest.XXXX)"
cat > "$TMP/kubectl" <<'SHIM'
#!/usr/bin/env bash
[[ -n "${K_BROKEN:-}" ]] && { echo "error: connection refused" >&2; exit 1; }
case "$*" in
  *"get pod"*"status.phase"*) printf '%s' "${K_PHASE:-Running}";;
  *"get pod"*"containers[0].image"*) printf '%s' "${K_IMG-vllm/vllm-openai:v0.33.0}";;
  *"get pod"*"args"*) printf '%s' '["--tensor-parallel-size=8"]';;
  *exec*"/health"*) [[ "${K_HEALTH:-ok}" == ok ]] || exit 22;;
  *exec*"/v1/models"*) echo '{"data":[{"id":"m"}]}';;
  *exec*"df -m /dev/shm"*) printf '%s\n' "${K_SHM-10240}";;
  *exec*"/metrics"*) for i in $(seq 1 12); do echo "vllm:metric_$i 1"; done;;
  *exec*"printenv NCCL_SOCKET_IFNAME"*) echo eth0;;
  *exec*"printenv VLLM_HOST_IP"*) echo 10.0.0.1;;
  *exec*"printenv VLLM_NO_USAGE_STATS"*) [[ -n "${K_STATS-1}" ]] || exit 1; echo "${K_STATS-1}";;
  *) exit 1;;
esac
SHIM
chmod +x "$TMP/kubectl"

BAD=0
# expect <label> <exit-code> <output-substring> VAR=value ...
expect() {
  local label="$1" want_rc="$2" want_text="$3"; shift 3
  local out rc
  out="$(env PATH="$TMP:$PATH" "$@" bash "$HERE/deployment-smoke.sh" pod ns 2>&1)"; rc=$?
  if [[ "$rc" -ne "$want_rc" || "$out" != *"$want_text"* ]]; then
    echo "SELFTEST FAIL: $label (exit $rc, wanted $want_rc with '$want_text')"; BAD=$((BAD + 1))
  else
    echo "ok: $label"
  fi
}
expect "healthy pod passes"              0 "all critical checks passed" K_NONE=1
expect "unreachable cluster fails"       1 "pod phase is ''"            K_BROKEN=1
expect "Pending pod fails"               1 "expected Running"           K_PHASE=Pending
expect ":latest fails"                   1 "pin to a version"           K_IMG=vllm/vllm-openai:latest
expect "untagged image fails"            1 "pin to a version"           K_IMG=vllm/vllm-openai
expect "registry port is not a tag"      1 "pin to a version"           K_IMG=registry.local:5000/vllm/vllm-openai
expect "digest pin passes"               0 "image pinned"               K_IMG=vllm/vllm-openai@sha256:abc
expect "64 MiB /dev/shm fails"           1 "/dev/shm is 64 MiB"         K_SHM=64
expect "dead /health fails"              1 "/health did not return 200" K_HEALTH=dead
expect "VLLM_NO_USAGE_STATS=true warns"  0 "only the value 1 opts out"  K_STATS=true
expect "VLLM_NO_USAGE_STATS unset warns" 0 "is 'unset'"                 K_STATS=
exit $(( BAD > 0 ))
