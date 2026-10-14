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
# v2 tool names: shell (was bash), read, glob, grep, edit, ...
# Turn count = number of step_start events.
#
# Source this file, then call the functions.
# All functions: return 0 on success, non-zero on failure;
# print a diagnostic line to stderr on failure.

set -euo pipefail

_tools_in_order() {
  local file="$1"
  # v2 emits one tool_use per call, after it settles (status completed|error).
  jq -r 'select(.type=="tool_use") | .part.tool' "$file"
}

assert_tool_order() {
  local file="$1"; shift
  local expected=("$@")
  local actual
  mapfile -t actual < <(_tools_in_order "$file")
  if [[ "${actual[*]}" != "${expected[*]}" ]]; then
    echo "FAIL tool order: expected [${expected[*]}] got [${actual[*]}]" >&2
    return 1
  fi
}

assert_tool_called() {
  local file="$1"; local tool="$2"
  if ! _tools_in_order "$file" | grep -Fxq "$tool"; then
    echo "FAIL tool not called: $tool" >&2
    echo "  called tools: $(_tools_in_order "$file" | tr '\n' ' ')" >&2
    return 1
  fi
}

assert_no_errors() {
  local file="$1"
  local errs
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
  actual=$(jq -s 'map(select(.type=="step_start")) | length' "$file")
  if [[ "$actual" != "$want" ]]; then
    echo "FAIL turn count: expected $want got $actual" >&2
    return 1
  fi
}

assert_tool_input_matches() {
  # Assert that at least one tool_use event for $tool has $path
  # matching $regex.
  local file="$1"; local tool="$2"; local path="$3"; local regex="$4"
  if ! jq -e --arg tool "$tool" --arg regex "$regex" --arg path "$path" '
    select(.type=="tool_use" and .part.tool==$tool) |
    .part.state.input | getpath($path | split(".") | map(select(length>0))) | test($regex)
  ' "$file" > /dev/null; then
    echo "FAIL no $tool call with $path matching /$regex/" >&2
    jq -c --arg tool "$tool" 'select(.type=="tool_use" and .part.tool==$tool) | .part.state.input' "$file" >&2
    return 1
  fi
}

assert_final_text_matches() {
  local file="$1"; local regex="$2"
  local final
  final=$(jq -rs 'map(select(.type=="text")) | last | .part.text // ""' "$file")
  if ! echo "$final" | grep -Eq "$regex"; then
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
