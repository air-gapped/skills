#!/usr/bin/env bash
set -Eeuo pipefail

die() {
  printf 'cleanup: %s\n' "$*" >&2
  exit 2
}

usage() {
  cat >&2 <<'EOF'
Usage:
  cleanup.sh --run-dirs
  cleanup.sh --file PATH [--file PATH ...]
EOF
}

mode=''
files=()
while (($# > 0)); do
  case "$1" in
    --run-dirs)
      [[ -z "$mode" ]] || die "choose one cleanup mode"
      mode=run_dirs
      shift
      ;;
    --file)
      (($# >= 2)) || die "--file requires a path"
      [[ -z "$mode" || "$mode" == files ]] || die "choose one cleanup mode"
      mode=files
      files+=("$2")
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$mode" ]] || { usage; exit 2; }

if [[ "$mode" == run_dirs ]]; then
  shopt -s nullglob
  for run_dir in /tmp/claude-code-ci.*; do
    [[ -d "$run_dir" ]] || continue
    case "$run_dir" in
      /tmp/claude-code-ci.[A-Za-z0-9]* ) rm -rf -- "$run_dir" ;;
      *) die "refusing unexpected path: $run_dir" ;;
    esac
  done
else
  for file in "${files[@]}"; do
    case "$file" in
      /tmp/*) rm -f -- "$file" ;;
      *) die "refusing to remove a file outside /tmp: $file" ;;
    esac
  done
fi
