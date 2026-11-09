#!/usr/bin/env bash
# jq-based assertion helpers for opencode NDJSON transcripts.
#
# Usage:
#   assert_tool_order transcript.ndjson glob read
#   assert_tool_called transcript.ndjson read
#   assert_no_errors transcript.ndjson
#   assert_turn_count transcript.ndjson 3
#   assert_tool_input_matches transcript.ndjson read '.path' '/tmp/.*\.py$'
#   assert_final_text_matches transcript.ndjson '40'
#
# v2 tool names: shell, read, glob, grep, edit, ... A call the model made
# as `bash` (run as shell from v2.2.5) is treated as `shell` here.
# Turn count = number of step_start events.
#
# Source this file, then call the functions.
# All functions: return 0 on success, non-zero on failure;
# print a diagnostic line to stderr on failure.
# Every assertion fails on a transcript that is missing, empty or not
# NDJSON events: a run that delivered nothing passes no assertion.

set -euo pipefail

_require_events() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "FAIL transcript not found: $file" >&2
    return 1
  fi
  if ! jq -e -s 'length > 0 and all(.[]; type == "object" and has("type"))' "$file" >/dev/null 2>&1; then
    echo "FAIL transcript has no NDJSON events (empty, or not a --format json transcript): $file" >&2
    return 1
  fi
}

_tools_in_order() {
  local file="$1"
  # v2 emits one tool_use per call, after it settles (status completed|error).
  jq -r 'select(.type=="tool_use") | .part.tool | if . == "bash" then "shell" else . end' "$file"
}

assert_tool_order() {
  local file="$1"; shift
  local expected=("$@")
  local actual
  _require_events "$file" || return 1
  mapfile -t actual < <(_tools_in_order "$file")
  if [[ "${actual[*]}" != "${expected[*]}" ]]; then
    echo "FAIL tool order: expected [${expected[*]}] got [${actual[*]}]" >&2
    return 1
  fi
}

assert_tool_called() {
  local file="$1"; local tool="$2"
  _require_events "$file" || return 1
  if ! _tools_in_order "$file" | grep -Fxq "$tool"; then
    echo "FAIL tool not called: $tool" >&2
    echo "  called tools: $(_tools_in_order "$file" | tr '\n' ' ')" >&2
    return 1
  fi
}

assert_no_errors() {
  local file="$1"
  local errs
  _require_events "$file" || return 1
  errs=$(jq -c 'select(.type=="error")' "$file" | wc -l)
  if [[ "$errs" -gt 0 ]]; then
    echo "FAIL $errs error events in transcript" >&2
    jq -c 'select(.type=="error")' "$file" >&2
    return 1
  fi
}

assert_turn_count() {
  local file="$1"; local want="$2"
  local actual
  _require_events "$file" || return 1
  actual=$(jq -s 'map(select(.type=="step_start")) | length' "$file")
  if [[ "$actual" != "$want" ]]; then
    echo "FAIL turn count: expected $want got $actual" >&2
    return 1
  fi
}

assert_tool_input_matches() {
  # Assert that at least one tool_use event for $tool has $path
  # matching $regex. Non-string values are matched on their JSON text.
  local file="$1"; local tool="$2"; local path="$3"; local regex="$4"
  _require_events "$file" || return 1
  # Slurp and `any`: with a stream, jq -e reports only the LAST call's result.
  if ! jq -e -s --arg tool "$tool" --arg regex "$regex" --arg path "$path" '
    ($path | split(".") | map(select(length>0))) as $p |
    any(.[];
      .type=="tool_use"
      and ((.part.tool | if . == "bash" then "shell" else . end) == $tool)
      and ((.part.state.input | getpath($p)) as $v
           | $v != null and (($v | if type=="string" then . else tojson end) | test($regex))))
  ' "$file" > /dev/null; then
    echo "FAIL no $tool call with $path matching /$regex/" >&2
    jq -c --arg tool "$tool" 'select(.type=="tool_use" and ((.part.tool | if . == "bash" then "shell" else . end) == $tool)) | .part.state.input' "$file" >&2
    return 1
  fi
}

assert_final_text_matches() {
  local file="$1"; local regex="$2"
  local final
  _require_events "$file" || return 1
  if ! jq -e -s 'any(.[]; .type=="text")' "$file" >/dev/null; then
    echo "FAIL no text event in transcript: the run produced no final text" >&2
    return 1
  fi
  final=$(jq -rs 'map(select(.type=="text")) | last | .part.text // ""' "$file")
  if ! echo "$final" | grep -Eq -- "$regex"; then
    echo "FAIL final text doesn't match /$regex/: '$final'" >&2
    return 1
  fi
}

# If sourced with no args, just load functions.
# If called directly with a command, dispatch.
if [[ "${BASH_SOURCE[0]}" == "$0" && $# -gt 0 ]]; then
  cmd="$1"; shift
  "$cmd" "$@"
fi
