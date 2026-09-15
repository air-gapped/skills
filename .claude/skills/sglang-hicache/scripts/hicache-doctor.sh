#!/usr/bin/env bash
# hicache-doctor.sh — surface SGLang HiCache boot-time auto-rewrites.
#
# handle_hicache() (arg_groups/hicache_hook.py; formerly server_args.py
# _handle_hicache) never errors on an incompatible layout x io x storage
# combination. It rewrites the combination and logs a WARNING. A server started
# with the flags from a recipe can therefore be running a different
# configuration than the recipe describes, and the only evidence is one line in
# the boot log. That is the usual cause of "benchmark numbers do not match the
# recipe".
#
# Usage:
#   hicache-doctor.sh                       # auto-detect source
#   hicache-doctor.sh --systemd [UNIT]      # journalctl (default unit: sglang)
#   hicache-doctor.sh --docker [NAME|ID]    # docker logs
#   hicache-doctor.sh --kubectl POD [-n NS] # kubectl logs (add -c NAME if needed)
#   hicache-doctor.sh --file PATH           # a captured log
#   ... | hicache-doctor.sh --stdin         # a pipeline
#
# Exit: 0 no rewrites found, 1 rewrites found, 2 no log source usable.

set -uo pipefail

# Exact strings from arg_groups/hicache_hook.py at upstream main, read
# 2026-09-15. "switching to" is the invariant across all three rewrite sites;
# the longer patterns are kept so the output names which rule fired.
REWRITE='switching to'
CONTEXT='Hierarchical cache|HiCache|hicache|storage backend|mem layout|io backend|prefetch'

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }

mode=""
ns=""
arg=""

while [ $# -gt 0 ]; do
  case "$1" in
    --systemd) mode=systemd; arg="${2:-sglang}"; [ $# -ge 2 ] && shift; shift ;;
    --docker)  mode=docker;  arg="${2:-}"; [ $# -ge 2 ] && shift; shift ;;
    --kubectl) mode=kubectl; arg="${2:-}"; [ $# -ge 2 ] && shift; shift ;;
    --file)    mode="file";    arg="${2:-}"; [ $# -ge 2 ] && shift; shift ;;
    --stdin)   mode=stdin; shift ;;
    -n)        ns="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *)         echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

read_log() {
  case "$mode" in
    systemd) journalctl -u "$arg" --no-pager -n 5000 2>/dev/null ;;
    docker)  docker logs "$arg" 2>&1 ;;
    kubectl)
      if [ -n "$ns" ]; then kubectl logs "$arg" -n "$ns" 2>/dev/null
      else kubectl logs "$arg" 2>/dev/null; fi ;;
    file)    cat "$arg" 2>/dev/null ;;
    stdin)   cat ;;
    *)       return 1 ;;
  esac
}

autodetect() {
  # Try each source that exists, in the order an operator is most likely on.
  if command -v journalctl >/dev/null 2>&1 &&
     journalctl -u sglang --no-pager -n 1 >/dev/null 2>&1; then
    mode=systemd; arg=sglang; return 0
  fi
  if command -v docker >/dev/null 2>&1; then
    local c
    c=$(docker ps --filter 'ancestor=lmsysorg/sglang' --format '{{.Names}}' 2>/dev/null | head -1)
    [ -z "$c" ] && c=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -i sglang | head -1)
    if [ -n "$c" ]; then mode=docker; arg="$c"; return 0; fi
  fi
  if command -v kubectl >/dev/null 2>&1; then
    local p
    p=$(kubectl get pods -o name 2>/dev/null | grep -i sglang | head -1 | cut -d/ -f2)
    if [ -n "$p" ]; then mode=kubectl; arg="$p"; return 0; fi
  fi
  return 1
}

if [ -z "$mode" ]; then
  if ! autodetect; then
    echo "no sglang log source found (tried journalctl -u sglang, docker, kubectl)." >&2
    echo "Point at one explicitly: --systemd UNIT | --docker NAME | --kubectl POD [-n NS] | --file PATH | --stdin" >&2
    exit 2
  fi
  echo "# auto-detected source: $mode $arg"
fi

log=$(read_log)
if [ -z "$log" ]; then
  echo "log source produced no output: $mode $arg" >&2
  exit 2
fi

echo "# source: $mode ${arg:-}"
echo
echo "== resolved HiCache configuration (as the server actually started) =="
printf '%s\n' "$log" | grep -E "$CONTEXT" | grep -vE "$REWRITE" | tail -20
echo
echo "== auto-rewrites (flags the server silently changed) =="
hits=$(printf '%s\n' "$log" | grep -E "$REWRITE" || true)

if [ -z "$hits" ]; then
  echo "none found."
  echo
  echo "Absence is weak evidence: it means no rewrite appears in the log window"
  echo "read here, not that the flags were honoured. Confirm against the resolved"
  echo "configuration above, and make sure the window covers server startup —"
  echo "journalctl -n 5000 and 'docker logs' may both have rolled past it."
  exit 0
fi

printf '%s\n' "$hits"
echo
echo "Each line is a flag combination the server rejected and replaced. The"
echo "recipe you started from no longer describes this server. Re-read the"
echo "resolved configuration above before trusting any benchmark from it."
exit 1
