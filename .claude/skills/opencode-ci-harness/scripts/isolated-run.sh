#!/usr/bin/env bash
# Isolated opencode (v2) CI run. Sets the isolation envelope and
# launches `opencode run --standalone --format json`, capturing the
# NDJSON transcript on stdout and debug logs on stderr.
#
# Usage (endpoint: any OpenAI/Responses/Messages-compatible URL, local or remote):
#   isolated-run.sh \
#     --model "eng/MODEL_NAME" \
#     --base-url "http://localhost:8000/v1" \
#     [--api-key "sk-dummy"] \
#     [--workdir /tmp/scratch] \
#     [--max-turns 15] \
#     [--npm "@ai-sdk/openai-compatible"] \
#     [--prompt "..."] \          # or pass on stdin
#     [--provider-options-json '{"chat_template_kwargs":{"enable_thinking":true}}']
#
# Usage (stored credential: any API key or login already in an opencode store):
#   isolated-run.sh --credential INTEGRATION --model "INTEGRATION/MODEL_ID" ...
#   Copies only that integration's credential from the operator store
#   (${OPENCODE_SOURCE_DB:-$XDG_DATA_HOME/opencode/opencode.db}) into the
#   scratch home (inject-credential.py | opencode auth import); no provider
#   block is written.
#   OAuth logins are copied without their refresh token and refused when
#   the access token would expire during the run.
#
# --model is required; --base-url is required unless --credential is set.
# --npm selects the AI SDK provider package, which selects the engine
# API the run exercises:
#   @ai-sdk/openai-compatible → POST /v1/chat/completions  (default)
#   @ai-sdk/openai            → POST /v1/responses         (Responses API)
#   @ai-sdk/anthropic         → POST /v1/messages          (Anthropic API)
# Same --base-url ".../v1" works for all three (the SDK appends the
# endpoint path).
# --max-turns caps agent steps (config `agent.build.steps`); at the cap
# opencode disables tools and asks the model for a final answer.
# --provider-options-json fields are sent verbatim in every request body
# (openai-compatible only), e.g. `chat_template_kwargs`.
# --allow-shell permits the shell tool (tiers 3, 7); denied by default.
# Transcript on stdout. Debug on stderr.
# Exit status: opencode v2 exits 1 on error events, but still assert on
# transcript content, not on $?.

set -euo pipefail

MODEL=""
BASE_URL=""
API_KEY="sk-dummy"
WORKDIR=""
MAX_TURNS=15
PROMPT=""
TIMEOUT=600
PROVIDER_OPTIONS_JSON=""
NPM_PKG="@ai-sdk/openai-compatible"
CREDENTIAL=""
ALLOW_SHELL=0

usage() {
  sed -n '2,40p' "$0"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)     MODEL="$2"; shift 2 ;;
    --base-url)  BASE_URL="$2"; shift 2 ;;
    --api-key)   API_KEY="$2"; shift 2 ;;
    --workdir)   WORKDIR="$2"; shift 2 ;;
    --max-turns) MAX_TURNS="$2"; shift 2 ;;
    --prompt)    PROMPT="$2"; shift 2 ;;
    --timeout)   TIMEOUT="$2"; shift 2 ;;
    --npm)       NPM_PKG="$2"; shift 2 ;;
    --provider-options-json) PROVIDER_OPTIONS_JSON="$2"; shift 2 ;;
    --credential) CREDENTIAL="$2"; shift 2 ;;
    --allow-shell) ALLOW_SHELL=1; shift ;;
    -h|--help)   usage ;;
    *) echo "Unknown: $1" >&2; usage ;;
  esac
done

[[ -z "$MODEL" ]] && { echo "--model required" >&2; exit 1; }
[[ -z "$BASE_URL" && -z "$CREDENTIAL" ]] && { echo "--base-url or --credential required" >&2; exit 1; }
[[ "$MODEL" == */* ]] || { echo "--model must be provider-alias/model-id" >&2; exit 1; }
[[ -n "$CREDENTIAL" && -n "$PROVIDER_OPTIONS_JSON" ]] && { echo "--provider-options-json needs --base-url" >&2; exit 1; }
# Resolve the operator store BEFORE HOME/XDG are redirected.
SOURCE_DB="${OPENCODE_SOURCE_DB:-${XDG_DATA_HOME:-$HOME/.local/share}/opencode/opencode.db}"
if [[ -n "$PROVIDER_OPTIONS_JSON" ]]; then
  [[ "$NPM_PKG" == "@ai-sdk/openai-compatible" ]] || { echo "--provider-options-json needs --npm @ai-sdk/openai-compatible" >&2; exit 1; }
  jq -e 'type=="object"' <<<"$PROVIDER_OPTIONS_JSON" >/dev/null || { echo "--provider-options-json must be a JSON object" >&2; exit 1; }
fi

# Scratch home: HOME, XDG roots and OPENCODE_TEST_HOME all point inside it,
# so the global config dir, ~/.claude and ~/.agents compatibility roots,
# credential store, DB and service registry are all fresh.
OPENCODE_TEST_HOME="$(mktemp -d /tmp/oc-ci-XXXXXX)"
export OPENCODE_TEST_HOME
export HOME="$OPENCODE_TEST_HOME"
export XDG_CONFIG_HOME="$OPENCODE_TEST_HOME/config"
export XDG_DATA_HOME="$OPENCODE_TEST_HOME/data"
export XDG_CACHE_HOME="$OPENCODE_TEST_HOME/cache"
export XDG_STATE_HOME="$OPENCODE_TEST_HOME/state"
export TMPDIR="$OPENCODE_TEST_HOME/tmp"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_STATE_HOME" "$TMPDIR"

WORKDIR="${WORKDIR:-$OPENCODE_TEST_HOME/workdir}"
mkdir -p "$WORKDIR"

# No project config walk-up from the workdir (v2 name, then v1 fallback name).
export OPENCODE_CONFIG_PROJECT_DISABLE=1
export OPENCODE_DISABLE_PROJECT_CONFIG=1
# No models.dev catalog fetch for --base-url runs; stored-credential providers
# need the catalog to resolve their models.
[[ -z "$CREDENTIAL" ]] && export OPENCODE_DISABLE_MODELS_FETCH=1
export OPENCODE_LOG_LEVEL=DEBUG
# Caller overrides that would bypass the scratch home.
unset OPENCODE_CONSOLE_TOKEN OPENCODE_CONFIG OPENCODE_CONFIG_DIR OPENCODE_SERVER_URL OPENCODE_PASSWORD || true

PROVIDER_ALIAS="${MODEL%%/*}"
MODEL_ID="${MODEL#*/}"

cleanup() {
  if [[ "${OC_CI_KEEP:-0}" != "1" ]]; then
    rm -rf "$OPENCODE_TEST_HOME"
  else
    echo "OC_CI_KEEP=1 set; scratch home retained at $OPENCODE_TEST_HOME" >&2
    # Never retain a copied credential.
    if [[ -n "$CREDENTIAL" && -f "$XDG_DATA_HOME/opencode/opencode.db" ]]; then
      sqlite3 "$XDG_DATA_HOME/opencode/opencode.db" 'DELETE FROM credential;'
    fi
  fi
}
trap cleanup EXIT

# v1-shaped config; v2 migrates it (provider → providers, permission →
# permissions rules, agent → agents). Unknown openai-compatible model
# options are migrated into the request body.
MODEL_OPTIONS="${PROVIDER_OPTIONS_JSON:-{\}}"
OPENCODE_CONFIG_CONTENT="$(jq -n \
  --arg alias "$PROVIDER_ALIAS" --arg id "$MODEL_ID" --arg model "$MODEL" \
  --arg npm "$NPM_PKG" --arg url "$BASE_URL" --arg key "$API_KEY" \
  --argjson steps "$MAX_TURNS" --argjson mopts "$MODEL_OPTIONS" \
  --arg sub "$CREDENTIAL" --arg shell "$([[ $ALLOW_SHELL == 1 ]] && echo allow || echo deny)" '{
  "$schema": "https://opencode.ai/config.json",
  provider: (if $sub != "" then {} else { ($alias): {
    npm: $npm,
    options: { baseURL: $url, apiKey: $key },
    models: { ($id): ({ name: $id } + (if $mopts == {} then {} else { options: $mopts } end)) }
  } } end),
  model: $model,
  agent: { build: { steps: $steps } },
  mcp: {},
  plugin: [],
  autoupdate: false,
  share: "disabled",
  permission: {
    "*": "deny",
    read: "allow", glob: "allow", grep: "allow", list: "allow",
    bash: $shell
  }
}')"
export OPENCODE_CONFIG_CONTENT

# --standalone: private server child (dies on stdin EOF) instead of the
# operator's background service. cd: v2 `run` takes its root from $PWD.
cd "$WORKDIR"
if [[ -n "$CREDENTIAL" ]]; then
  # A fresh DB is bootstrapped from the schema, so a legacy auth.json is NOT
  # imported; pipe the one credential through `auth import` instead.
  python3 -I "$(dirname "$(readlink -f "$0")")/inject-credential.py" \
      "$SOURCE_DB" "$CREDENTIAL" "$(( TIMEOUT + 600 ))" |
    opencode auth import --standalone >&2
fi
args=(run --standalone --format json --print-logs --model "$MODEL")
if [[ -n "$PROMPT" ]]; then
  # opencode appends any non-TTY stdin to the message; close it.
  timeout "$TIMEOUT" opencode "${args[@]}" "$PROMPT" </dev/null
else
  timeout "$TIMEOUT" opencode "${args[@]}"   # scenario on stdin
fi
