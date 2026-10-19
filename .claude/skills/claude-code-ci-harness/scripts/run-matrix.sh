#!/usr/bin/env bash
set -Eeuo pipefail

die() {
  printf 'run-matrix: %s\n' "$*" >&2
  exit 2
}

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
prompt_file=''
workdir=''
output_dir=''
timeout_seconds=180
tools_csv='Read,Glob'
runs=()

usage() {
  cat >&2 <<'EOF'
Usage:
  run-matrix.sh --prompt-file PATH --run SPEC [--run SPEC ...] [options]

Each --run SPEC is one endpoint, pipe-separated:
  label|base-url|model[|token-var]
An empty base-url selects subscription mode, e.g. sub||sonnet.

Options:
  --workdir PATH       Shared working directory for every run.
  --output-dir PATH    Transcript directory; default: a /tmp mktemp dir.
  --timeout N          Wall-clock seconds per run; 0 disables. Default: 180.
  --tools CSV          Built-in tool allowlist. Default: Read,Glob.
EOF
}

while (($# > 0)); do
  case "$1" in
    --prompt-file)
      (($# >= 2)) || die "--prompt-file requires a path"
      prompt_file=$2
      shift 2
      ;;
    --run)
      (($# >= 2)) || die "--run requires a spec"
      runs+=("$2")
      shift 2
      ;;
    --workdir)
      (($# >= 2)) || die "--workdir requires a path"
      workdir=$2
      shift 2
      ;;
    --output-dir)
      (($# >= 2)) || die "--output-dir requires a path"
      output_dir=$2
      shift 2
      ;;
    --timeout)
      (($# >= 2)) || die "--timeout requires a value"
      [[ "$2" =~ ^(0|[1-9][0-9]*)$ ]] || die "timeout must be a non-negative integer"
      timeout_seconds=$2
      shift 2
      ;;
    --tools)
      (($# >= 2)) || die "--tools requires a value"
      tools_csv=$2
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

[[ -f "$prompt_file" ]] || die "prompt file does not exist"
((${#runs[@]} > 0)) || die "at least one --run spec is required"
[[ -n "$output_dir" ]] || output_dir=$(mktemp -d /tmp/claude-code-ci-matrix.XXXXXX)
mkdir -p -- "$output_dir"

status=0
for spec in "${runs[@]}"; do
  label='' spec_base_url='' spec_model='' spec_token_var=''
  IFS='|' read -r label spec_base_url spec_model spec_token_var <<<"$spec"
  [[ "$label" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die "invalid run label: $label"
  [[ -n "$spec_model" ]] || die "run spec needs label|base-url|model: $spec"

  transcript="$output_dir/$label.ndjson"
  args=(--model "$spec_model" \
    --prompt-file "$prompt_file" --tools "$tools_csv" \
    --timeout "$timeout_seconds" --transcript "$transcript")
  [[ -n "$spec_base_url" ]] && args+=(--base-url "$spec_base_url")
  [[ -n "$spec_token_var" ]] && args+=(--token-var "$spec_token_var")
  [[ -n "$workdir" ]] && args+=(--workdir "$workdir")

  if ! "$script_dir/isolated-run.sh" "${args[@]}"; then
    status=1
    printf 'run=%s status=failed transcript=%s\n' "$label" "$transcript" >&2
  elif ! "$script_dir/assert-events.sh" "$transcript" >&2; then
    status=1
    printf 'run=%s status=failed-assertions transcript=%s\n' "$label" "$transcript" >&2
  else
    printf 'run=%s status=passed transcript=%s\n' "$label" "$transcript" >&2
  fi
done
exit "$status"
