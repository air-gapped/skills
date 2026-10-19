#!/usr/bin/env bash
set -Eeuo pipefail

die() {
  printf 'scan-token-leakage: %s\n' "$*" >&2
  exit 2
}

[[ $# -eq 2 ]] || die "usage: scan-token-leakage.sh TRANSCRIPT TOKEN_FILE_OR_MODEL_DIR"
transcript=$1
source_path=$2
[[ -s "$transcript" ]] || die "transcript is empty"
command -v jq >/dev/null || die "jq is required"
command -v sort >/dev/null || die "sort is required"

token_file=$(mktemp)
trap 'rm -f -- "$token_file"' EXIT

extract_json_tokens() {
  local path=$1
  if [[ "$(basename -- "$path")" == tokenizer_config.json ]]; then
    jq -r '.added_tokens_decoder // {} | .[] | select(.special == true) | .content // empty' "$path"
  else
    jq -r '.. | objects | select((.special == true) and (.content | type == "string")) | .content' "$path"
  fi
}

if [[ -d "$source_path" ]]; then
  if [[ -f "$source_path/tokenizer_config.json" ]]; then
    extract_json_tokens "$source_path/tokenizer_config.json"
  fi
  if [[ -f "$source_path/tokenizer.json" ]]; then
    extract_json_tokens "$source_path/tokenizer.json"
  fi
  if compgen -G "$source_path"'/*.jinja*' >/dev/null; then
    command -v perl >/dev/null || die "perl is required to inspect Jinja templates"
    for template in "$source_path"/*.jinja*; do
      [[ -f "$template" ]] || continue
      perl -ne 'while (/(?:<\|[^>\n]*\|>|<[^>\n]+>)/g) { print "$&\n" }' "$template"
    done
  fi
elif [[ -f "$source_path" ]]; then
  case "$source_path" in
    *.json) extract_json_tokens "$source_path" ;;
    *)
      while IFS= read -r token || [[ -n "$token" ]]; do
        [[ "$token" =~ ^[[:space:]]*$ ]] && continue
        [[ "$token" =~ ^[[:space:]]*# ]] && continue
        printf '%s\n' "$token"
      done < "$source_path"
      ;;
  esac
else
  die "token source does not exist"
fi | awk 'length($0) >= 2' | sort -u > "$token_file"

[[ -s "$token_file" ]] || die "no special tokens found"
leaks=0
while IFS= read -r token || [[ -n "$token" ]]; do
  count=$(jq -s --arg token "$token" '[.[] | .. | strings | select(contains($token))] | length' "$transcript")
  if ((count > 0)); then
    printf 'leak token=%s fields=%s\n' "$token" "$count"
    leaks=1
  fi
done < "$token_file"

if ((leaks)); then
  exit 1
fi
printf 'clean: no special-token leakage detected\n'
