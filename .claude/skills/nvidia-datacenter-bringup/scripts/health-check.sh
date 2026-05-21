#!/usr/bin/env bash
# Usage: ./health-check.sh
#
# One-shot health summary for an NVIDIA HGX/DGX host on Ubuntu 24.04 LTS.
# Run after install (per [[recipe]]) or anytime to triage a degraded host.
# Exit 0 if every check passes; exit 1 if any check fails.
#
# Healthy B300 (8 GPUs) expected output (sample):
#   sb-state:     SecureBoot enabled
#   nvidia-smi:   8 GPUs visible
#   fabricmanager: active
#   nvidia-nvlsm: active   (B200/B300 only — N/A on H100/L40S)
#   persistenced: active
#   ib_umad:      loaded   (B200/B300 only — N/A on L40S)
#   fabric-state: Completed / Success
#
# On L40S/L4 (no NVSwitch), fabricmanager / nvidia-nvlsm / ib_umad checks
# return SKIPPED rather than FAIL.

set -u
fail=0
pass() { printf "  %-15s %s\n" "$1" "OK: $2"; }
warn() { printf "  %-15s %s\n" "$1" "WARN: $2"; }
fail() { printf "  %-15s %s\n" "$1" "FAIL: $2"; fail=1; }
skip() { printf "  %-15s %s\n" "$1" "SKIPPED: $2"; }

echo "=== nvidia-datacenter-bringup health-check ==="
echo

# Secure Boot state
if command -v mokutil >/dev/null 2>&1; then
  sb=$(mokutil --sb-state 2>&1 | head -1)
  pass "sb-state" "$sb"
else
  skip "sb-state" "mokutil not installed"
fi

# GPU enumeration
if command -v nvidia-smi >/dev/null 2>&1; then
  gpus=$(nvidia-smi --query-gpu=count --format=csv,noheader -i 0 2>&1 | head -1)
  case "$gpus" in
    [1-9]*) pass "nvidia-smi"  "$gpus GPUs visible" ;;
    *)      fail "nvidia-smi"  "no GPUs reported ($gpus)" ;;
  esac
else
  fail "nvidia-smi" "nvidia-smi not found — driver not installed?"
fi

# Detect whether this host has NVSwitch fabric (B200/B300/H100/A100)
has_fabric=0
if [ "$fail" -eq 0 ] && nvidia-smi -q -i 0 2>/dev/null | grep -q "Fabric"; then
  has_fabric=1
fi

# Persistence daemon
state=$(systemctl is-active nvidia-persistenced 2>&1)
case "$state" in
  active)   pass "persistenced" "active" ;;
  *)        warn "persistenced" "$state (recommended but not required)" ;;
esac

# Fabric Manager — only required on NVSwitch systems
if [ "$has_fabric" -eq 1 ]; then
  state=$(systemctl is-active nvidia-fabricmanager 2>&1)
  case "$state" in
    active)   pass "fabricmanager" "active" ;;
    *)        fail "fabricmanager" "$state — required on NVSwitch hosts" ;;
  esac
else
  skip "fabricmanager" "no NVSwitch fabric on this host (L40S/L4-class)"
fi

# NVLSM — only required on 4th-gen NVSwitch (B200/B300/B100)
# Detect by presence of CX bridge devices (SMDL=SW_MNG VPD)
if [ "$has_fabric" -eq 1 ] && lspci -nn 2>/dev/null | grep -qi "mellanox"; then
  state=$(systemctl is-active nvidia-nvlsm 2>&1)
  case "$state" in
    active)        pass "nvidia-nvlsm" "active" ;;
    inactive|not*) skip "nvidia-nvlsm" "$state — only required on B200/B300/B100" ;;
    *)             fail "nvidia-nvlsm" "$state" ;;
  esac
else
  skip "nvidia-nvlsm" "no CX bridge devices (pre-B200 fabric)"
fi

# ib_umad kernel module — only needed for B200/B300 CX bridge access
if lspci -nn 2>/dev/null | grep -qi "mellanox.*MT2910\|mellanox.*ConnectX"; then
  if lsmod | awk '$1=="ib_umad" {found=1} END {exit !found}'; then
    pass "ib_umad" "loaded"
  else
    fail "ib_umad" "not loaded — DOCA-OFED install order pitfall (see [[troubleshooting]])"
  fi
else
  skip "ib_umad" "no ConnectX devices on this host"
fi

# Fabric registration
if [ "$has_fabric" -eq 1 ]; then
  state=$(nvidia-smi -q -i 0 2>/dev/null | awk '/Fabric/{f=1; next} f && /State/{print $3; exit}')
  status=$(nvidia-smi -q -i 0 2>/dev/null | awk '/Fabric/{f=1; next} f && /Status/{print $3; exit}')
  case "$state" in
    Completed) pass "fabric-state" "$state / $status" ;;
    "In Progress") warn "fabric-state" "$state — wait 30-90s on fresh boot" ;;
    *)         fail "fabric-state" "$state / $status" ;;
  esac
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "HEALTHY — all required checks passed."
  exit 0
else
  echo "DEGRADED — at least one required check failed. See [[troubleshooting]]."
  exit 1
fi
