#!/usr/bin/env bash
# Scan an opencode NDJSON transcript for leaked special-token text.
#
# Flags special tokens (e.g. `<tool_call>`, `<|im_end|>`, `<|channel|>`)
# that leaked into text, reasoning, tool arguments or error messages.
#
# Usage:
#   scan-token-leakage.sh <transcript.ndjson> <model-dir-OR-specials-file>
#
# model-dir modes:
#   1. Directory containing tokenizer_config.json — reads
#      .added_tokens_decoder[].content where .special==true.
#   2. Directory with .jinja chat templates — extract literal
#      <|...|> and <...> patterns from the template.
#   3. Plain text file with one special token per line.
#
# Output: for each special token found leaking, report the transcript
# event type, location, and a snippet of context. Exit 0 if clean,
# 1 if any leak detected.

set -euo pipefail

if [[ $# -ne 2 ]]; then
  sed -n '2,19p' "$0" >&2
  exit 2
fi

TRANSCRIPT="$1"
SOURCE="$2"
[[ -f "$TRANSCRIPT" ]] || { echo "ERROR: transcript not found: $TRANSCRIPT" >&2; exit 2; }

# --- Build specials list ---
SPECIALS_FILE=$(mktemp)
trap 'rm -f "$SPECIALS_FILE"' EXIT

if [[ -d "$SOURCE" ]]; then
  # Search both root and a configs/ subdir
  for cfg_path in \
    "$SOURCE/tokenizer_config.json" \
    "$SOURCE/configs/tokenizer_config.json"; do
    [[ -f "$cfg_path" ]] || continue
    jq -r '.added_tokens_decoder // {} | to_entries[] | select(.value.special==true) | .value.content' \
      "$cfg_path" 2>/dev/null >> "$SPECIALS_FILE" || true
  done
  # tokenizer.json added_tokens[] covers models whose added_tokens_decoder is empty.
  for tj_path in \
    "$SOURCE/tokenizer.json" \
    "$SOURCE/configs/tokenizer.json"; do
    [[ -f "$tj_path" ]] || continue
    jq -r '.added_tokens // [] | .[] | select(.special==true) | .content' \
      "$tj_path" 2>/dev/null >> "$SPECIALS_FILE" || true
  done
  for map_path in \
    "$SOURCE/special_tokens_map.json" \
    "$SOURCE/configs/special_tokens_map.json"; do
    [[ -f "$map_path" ]] || continue
    jq -r '[.bos_token, .eos_token, .pad_token, .unk_token, (.additional_special_tokens // [])[]] | .[] | if type=="object" then .content else . end | select(. != null and . != "")' \
      "$map_path" 2>/dev/null >> "$SPECIALS_FILE" || true
  done
  # Also sweep jinja templates for literal token patterns (always, as enrichment)
  for jinja in "$SOURCE"/*.jinja; do
    [[ -f "$jinja" ]] || continue
    grep -oE '<\|[^|> ]+\|>|<(tool_call|/tool_call|reasoning|/reasoning|thinking|/thinking|think|/think|channel|/channel|message|/message|start_of_turn|end_of_turn|tool_response|/tool_response|bos|eos|pad|unk)>' \
      "$jinja" 2>/dev/null >> "$SPECIALS_FILE" || true
  done
elif [[ -f "$SOURCE" ]]; then
  cat "$SOURCE" >> "$SPECIALS_FILE"
else
  echo "ERROR: source not a dir or file: $SOURCE" >&2
  exit 2
fi

# Clean + dedupe
sort -u "$SPECIALS_FILE" | grep -v '^$' > "${SPECIALS_FILE}.dedup"
mv "${SPECIALS_FILE}.dedup" "$SPECIALS_FILE"

specials_count=$(wc -l < "$SPECIALS_FILE")
if [[ "$specials_count" -eq 0 ]]; then
  echo "WARN: no specials extracted from $SOURCE" >&2
  echo "       (empty added_tokens_decoder? pass a dir with .jinja templates instead)" >&2
  exit 2
fi

echo "[scan] $specials_count special tokens loaded from $SOURCE"

# --- Scan transcript ---
# Two classes:
#   CRITICAL = model-emitted fields the parser should have scrubbed:
#     text, reasoning, tool_use.state.input (args model wrote),
#     error.message
#   INFO = tool_use.state.output (raw tool result; specials here are
#     normal if the tool read a file containing them — informational
#     only, NOT a parser bug)

critical_leaks=0
info_leaks=0

scan_field() {
  # $1 token, $2 field_label, $3 text_body, $4 severity (CRITICAL|INFO)
  local token="$1" label="$2" text_body="$3" sev="$4"
  [[ -z "$text_body" ]] && return
  if printf '%s' "$text_body" | grep -qF -- "$token"; then
    local ctx
    ctx=$(printf '%s' "$text_body" | awk -v tok="$token" '
      { idx = index($0, tok); if (idx > 0) {
          s = (idx > 40 ? idx-40 : 1);
          print substr($0, s, 80 + length(tok)); exit } }')
    echo "[$sev] token=\"$token\" in $label context=\"...${ctx}...\""
    if [[ "$sev" == "CRITICAL" ]]; then
      critical_leaks=$((critical_leaks + 1))
    else
      info_leaks=$((info_leaks + 1))
    fi
  fi
}

while IFS= read -r token; do
  [[ -z "$token" ]] && continue
  while IFS= read -r line; do
    etype=$(printf '%s' "$line" | jq -r '.type' 2>/dev/null)
    case "$etype" in
      text)
        body=$(printf '%s' "$line" | jq -r '.part.text // empty' 2>/dev/null)
        scan_field "$token" "text" "$body" "CRITICAL"
        ;;
      reasoning)
        body=$(printf '%s' "$line" | jq -r '.part.text // empty' 2>/dev/null)
        scan_field "$token" "reasoning" "$body" "CRITICAL"
        ;;
      tool_use)
        in_body=$(printf '%s' "$line" | jq -r '.part.state.input | tostring // empty' 2>/dev/null)
        out_body=$(printf '%s' "$line" | jq -r '.part.state.output // empty' 2>/dev/null)
        scan_field "$token" "tool_use.input" "$in_body" "CRITICAL"
        scan_field "$token" "tool_use.output" "$out_body" "INFO"
        ;;
      error)
        body=$(printf '%s' "$line" | jq -r '(.error.message // .data.error.message) // empty' 2>/dev/null)
        scan_field "$token" "error" "$body" "CRITICAL"
        ;;
    esac
  done < "$TRANSCRIPT"
done < "$SPECIALS_FILE"

echo
events=$(wc -l < "$TRANSCRIPT")
if [[ "$critical_leaks" -eq 0 ]]; then
  echo "[scan] CLEAN (model-emitted): 0 critical leaks, $info_leaks info-only hits in tool outputs across $specials_count tokens × $events events"
  exit 0
else
  echo "[scan] LEAKAGE: $critical_leaks CRITICAL (model-emitted) + $info_leaks INFO (tool outputs) across $specials_count tokens × $events events"
  exit 1
fi
