#!/usr/bin/env bash
# leak-gate.sh — gitleaks over what `gitleaks git --pre-commit --staged` cannot
# see: that mode reads only the staged diff, never the commit message, and a
# commit made with --no-verify skips it entirely.
#
#   leak-gate.sh commit-msg <msg-file>   scan the message being committed
#   leak-gate.sh pre-push                scan every outgoing commit, diff and message
#
# Runs the default rules, then .gitleaks-custom.toml when present; the two run
# separately because gitleaks masks low-entropy custom rules under useDefault.

set -euo pipefail

configs=("")
[ -f .gitleaks-custom.toml ] && configs+=(.gitleaks-custom.toml)

rc=0
case "${1:-}" in
  commit-msg)
    for c in "${configs[@]}"; do
      grep -v '^#' "$2" | gitleaks stdin --redact --verbose --no-banner ${c:+-c "$c"} || rc=1
    done
    ;;
  pre-push)
    to="${PRE_COMMIT_TO_REF:-}"
    from="${PRE_COMMIT_FROM_REF:-}"
    [[ -z "$to" || "$to" =~ ^0+$ ]] && exit 0 # branch delete: nothing outgoing
    if [[ -n "$from" && ! "$from" =~ ^0+$ ]]; then
      range=("$from..$to")
    else
      range=("$to" --not --remotes)
    fi
    for c in "${configs[@]}"; do
      gitleaks git --log-opts="${range[*]}" --redact --verbose --no-banner ${c:+-c "$c"} || rc=1
      git log --format=%B "${range[@]}" | gitleaks stdin --redact --verbose --no-banner ${c:+-c "$c"} || rc=1
    done
    ;;
  *)
    echo "usage: $0 commit-msg <msg-file> | pre-push" >&2
    exit 2
    ;;
esac
exit "$rc"
