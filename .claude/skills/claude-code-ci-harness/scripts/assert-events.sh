#!/usr/bin/env bash
set -Eeuo pipefail

die() {
  printf 'assert-events: %s\n' "$*" >&2
  exit 1
}

[[ $# -ge 1 ]] || die "usage: assert-events.sh TRANSCRIPT [EXPECTED_TOOL,...]"
transcript=$1
shift
expected=''
expected_model=''
min_turns=''
max_turns=''

while (($# > 0)); do
  case "$1" in
    --expect-tools)
      (($# >= 2)) || die "--expect-tools requires a value"
      expected=$2
      shift 2
      ;;
    --expect-model)
      (($# >= 2)) || die "--expect-model requires a value"
      expected_model=$2
      shift 2
      ;;
    --min-turns)
      (($# >= 2)) || die "--min-turns requires a value"
      [[ "$2" =~ ^[0-9]+$ ]] || die "--min-turns must be an integer"
      min_turns=$2
      shift 2
      ;;
    --max-turns)
      (($# >= 2)) || die "--max-turns requires a value"
      [[ "$2" =~ ^[0-9]+$ ]] || die "--max-turns must be an integer"
      max_turns=$2
      shift 2
      ;;
    --help|-h)
      printf 'usage: assert-events.sh TRANSCRIPT [EXPECTED_TOOL,...]\n'
      printf '       assert-events.sh TRANSCRIPT [--expect-tools CSV] [--expect-model MODEL] [--min-turns N] [--max-turns N]\n'
      exit 0
      ;;
    --*)
      die "unknown option: $1"
      ;;
    *)
      [[ -z "$expected" ]] || die "tool sequence specified more than once"
      expected=$1
      shift
      ;;
  esac
done

[[ -s "$transcript" ]] || die "transcript is empty: $transcript"
command -v jq >/dev/null || die "jq is required"

jq -s -e 'any(.[]; type == "object" and .type == "system" and .subtype == "init")' "$transcript" >/dev/null \
  || die "missing system/init event"

result=$(jq -s -r '[.[] | select(type == "object" and .type == "result") | .subtype] | .[-1] // empty' "$transcript")
[[ "$result" == success ]] || die "result subtype is ${result:-missing}, expected success"

if [[ -n "$expected_model" ]]; then
  actual_model=$(jq -s -r '[.[] | select(type == "object" and .type == "system" and .subtype == "init") | .model] | .[-1] // empty' "$transcript")
  [[ "$actual_model" == "$expected_model" ]] || die "model was ${actual_model:-missing}, expected $expected_model"
fi

result_turns=$(jq -s -r '[.[] | select(type == "object" and .type == "result") | .num_turns] | .[-1] // 0' "$transcript")
if [[ -n "$min_turns" ]] && ((result_turns < min_turns)); then
  die "result had $result_turns turns, expected at least $min_turns"
fi
if [[ -n "$max_turns" ]] && ((result_turns > max_turns)); then
  die "result had $result_turns turns, expected at most $max_turns"
fi

if jq -s -e 'any(.[]; type == "object" and .type == "error")' "$transcript" >/dev/null; then
  die "transcript contains an error event"
fi

if [[ -n "$expected" ]]; then
  actual=$(jq -s -r '[.[] | select(type == "object" and .type == "assistant") | (.message.content // [])[]? | select(type == "object" and .type == "tool_use") | .name] | join(",")' "$transcript")
  [[ "$actual" == "$expected" ]] || die "tool sequence was ${actual:-none}, expected $expected"
fi

printf 'pass: result=success'
if [[ -n "$expected" ]]; then
  printf ' tools=%s' "$expected"
fi
printf '\n'
