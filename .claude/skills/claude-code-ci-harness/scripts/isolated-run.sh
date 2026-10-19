#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

die() {
  printf 'claude-code-ci-harness: %s\n' "$*" >&2
  exit 2
}

usage() {
  cat >&2 <<'EOF'
Usage:
  isolated-run.sh --model MODEL [--base-url URL] [options]

Required:
  --model MODEL          Model name exactly as the endpoint serves it, or a
                         Claude model/alias (sonnet, opus) in subscription mode.
  --prompt TEXT          Prompt to send to Claude Code.
  --prompt-file PATH     Read the prompt from PATH instead.

Options:
  --base-url URL         Root URL of an Anthropic Messages-compatible endpoint;
                         Claude Code appends /v1/messages itself. Omit for
                         subscription mode: the token from --token-var
                         (default CLAUDE_CODE_OAUTH_TOKEN, made by
                         `claude setup-token`) authenticates against Anthropic.
  --token-var NAME       Variable in the secrets file holding the token.
                         Omit for endpoints that need no authentication.
  --secrets-file PATH    KEY=value token store; default:
                         ~/.config/claude-code-ci-harness/targets.env
  --x-api-key            Also send the token as X-Api-Key. Default: send it only
                         as ANTHROPIC_AUTH_TOKEN and empty ANTHROPIC_API_KEY.
  --workdir PATH         Working directory; defaults to a throwaway directory.
  --tools LIST           Comma-separated built-in tools; default: Read,Glob.
  --timeout SECONDS      Wall-clock timeout; default: 180; 0 disables it.
  --transcript PATH      Also write stdout NDJSON to PATH and stderr to PATH.stderr.
  --help                 Show this help.
EOF
}

[[ -n "${BASH_VERSION:-}" ]] || die "bash is required"
command -v mktemp >/dev/null || die "mktemp is required"
command -v timeout >/dev/null || die "timeout is required"

default_secrets_file="${HOME:-~}/.config/claude-code-ci-harness/targets.env"
secrets_file="${CLAUDE_CODE_CI_SECRETS_FILE:-$default_secrets_file}"
base_url=''
model=''
token_var=''
x_api_key=0
prompt=''
prompt_set=0
workdir=''
tools_csv='Read,Glob'
timeout_seconds=180
transcript=''

while (($# > 0)); do
  case "$1" in
    --base-url)
      (($# >= 2)) || die "--base-url requires a value"
      base_url=$2
      shift 2
      ;;
    --model)
      (($# >= 2)) || die "--model requires a value"
      model=$2
      shift 2
      ;;
    --token-var)
      (($# >= 2)) || die "--token-var requires a value"
      [[ "$2" =~ ^[A-Z][A-Z0-9_]*$ ]] || die "--token-var must be an uppercase variable name"
      token_var=$2
      shift 2
      ;;
    --secrets-file)
      (($# >= 2)) || die "--secrets-file requires a value"
      secrets_file=$2
      shift 2
      ;;
    --x-api-key)
      x_api_key=1
      shift
      ;;
    --prompt)
      (($# >= 2)) || die "--prompt requires a value"
      prompt=$2
      prompt_set=1
      shift 2
      ;;
    --prompt-file)
      (($# >= 2)) || die "--prompt-file requires a value"
      [[ -f "$2" ]] || die "prompt file does not exist: $2"
      prompt=$(<"$2")
      prompt_set=1
      shift 2
      ;;
    --workdir)
      (($# >= 2)) || die "--workdir requires a value"
      workdir=$2
      shift 2
      ;;
    --tools)
      (($# >= 2)) || die "--tools requires a value"
      tools_csv=$2
      shift 2
      ;;
    --timeout)
      (($# >= 2)) || die "--timeout requires a value"
      [[ "$2" =~ ^(0|[1-9][0-9]*)$ ]] || die "timeout must be a non-negative integer"
      timeout_seconds=$2
      shift 2
      ;;
    --transcript)
      (($# >= 2)) || die "--transcript requires a value"
      transcript=$2
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

if [[ -z "$base_url" ]]; then
  token_var=${token_var:-CLAUDE_CODE_OAUTH_TOKEN}
  ((x_api_key == 0)) || die "--x-api-key needs --base-url"
fi
[[ -n "$model" ]] || die "--model is required"
((prompt_set == 1)) || die "one of --prompt or --prompt-file is required"

if [[ -n "$base_url" ]]; then
  base_url=${base_url%/}
  [[ "$base_url" == */v1 ]] && base_url=${base_url%/v1}
fi

token='ci-dummy'
if [[ -n "$token_var" ]]; then
  [[ -f "$secrets_file" ]] || die "secrets file does not exist: $secrets_file"
  [[ ! -L "$secrets_file" ]] || die "secrets file must not be a symlink"
  secrets_real=$(realpath -e -- "$secrets_file")
  secrets_mode=$(stat -c '%a' -- "$secrets_real")
  [[ "$secrets_mode" == *00 ]] || die "secrets file must not be group/world readable: $secrets_real"
  [[ "$(stat -c '%u' -- "$secrets_real")" == "$(id -u)" ]] || die "secrets file must be owned by the current user"

  command -v git >/dev/null || die "git is required for secrets-path safety checks"
  secrets_root=$(git -C "$(dirname -- "$secrets_real")" rev-parse --show-toplevel 2>/dev/null || true)
  if [[ -n "$secrets_root" ]]; then
    secrets_root=$(realpath -e -- "$secrets_root")
    case "$secrets_real" in
      "$secrets_root"|"$secrets_root"/*) die "secrets file must be outside Git: $secrets_real" ;;
    esac
  fi

  token=''
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^([A-Z][A-Z0-9_]*)=(.*)$ ]] || die "invalid secrets-file line (expected KEY=value)"
    key=${BASH_REMATCH[1]}
    value=${BASH_REMATCH[2]}
    [[ "$key" == "$token_var" ]] || continue
    if ((${#value} >= 2)) && [[ ${value:0:1} == '"' && ${value: -1} == '"' ]]; then
      value=${value:1:${#value}-2}
    elif ((${#value} >= 2)) && [[ ${value:0:1} == "'" && ${value: -1} == "'" ]]; then
      value=${value:1:${#value}-2}
    fi
    token=$value
  done < "$secrets_real"
  [[ -n "$token" ]] || die "secrets file has no non-empty value for $token_var"
fi

# ANTHROPIC_API_KEY is always set (empty unless --x-api-key) so no inherited
# credential can win.
if [[ -n "$base_url" ]]; then
  api_key=''
  ((x_api_key == 1)) && api_key=$token
  auth_env=(
    "ANTHROPIC_BASE_URL=$base_url"
    "ANTHROPIC_API_KEY=$api_key"
    "ANTHROPIC_AUTH_TOKEN=$token"
    "ANTHROPIC_MODEL=$model"
    "ANTHROPIC_DEFAULT_OPUS_MODEL=$model"
    "ANTHROPIC_DEFAULT_SONNET_MODEL=$model"
    "ANTHROPIC_DEFAULT_HAIKU_MODEL=$model"
    # Deferred tools (defer_loading) 400 on endpoints that do not implement them.
    "ENABLE_TOOL_SEARCH=false"
  )
else
  auth_env=(
    "ANTHROPIC_API_KEY="
    "CLAUDE_CODE_OAUTH_TOKEN=$token"
  )
fi

run_dir=$(mktemp -d /tmp/claude-code-ci.XXXXXX)
cleanup() {
  rm -rf -- "$run_dir"
}
trap cleanup EXIT

if [[ -n "$workdir" ]]; then
  [[ -d "$workdir" ]] || die "workdir does not exist: $workdir"
  workdir=$(realpath -e -- "$workdir")
else
  workdir="$run_dir/work"
  mkdir -- "$workdir"
fi

if [[ -n "$transcript" ]]; then
  transcript_parent=$(dirname -- "$transcript")
  [[ -d "$transcript_parent" ]] || die "transcript parent does not exist: $transcript_parent"
  stderr_file="$transcript.stderr"
fi

mcp_config="$run_dir/mcp.json"
settings_file="$run_dir/settings.json"
printf '%s\n' '{"mcpServers":{}}' >"$mcp_config"
printf '%s\n' '{"disableAllHooks":true}' >"$settings_file"
mkdir -p "$run_dir/home" "$run_dir/config" "$run_dir/xdg-config" "$run_dir/xdg-data" \
  "$run_dir/xdg-state" "$run_dir/xdg-cache" "$run_dir/tmp"

cli=${CLAUDE_CODE_CI_CLAUDE_BIN:-$(command -v claude || true)}
[[ -x "$cli" ]] || die "claude executable not found"
cli=$(realpath -e -- "$cli")
cli_dir=$(dirname -- "$cli")
safe_path="$cli_dir:${HOME:-/nonexistent}/.local/bin:/usr/local/bin:/usr/bin:/bin"

allowed_tools=()
IFS=',' read -r -a requested_tools <<<"$tools_csv"
for raw_tool in "${requested_tools[@]}"; do
  read -r tool <<<"$raw_tool" || true  # trims surrounding whitespace
  [[ "$tool" =~ ^[A-Za-z][A-Za-z0-9_]*$ ]] || die "tools must be comma-separated built-in names"
  allowed_tools+=("$tool")
done

printf 'base_url=%s\nmodel=%s\nworkdir=%s\nauth=%s\n' \
  "${base_url:-anthropic-subscription}" "$model" "$workdir" \
  "$([[ -n "$token_var" ]] && printf 'token-var %s' "$token_var" || printf 'none')" >&2

claude_args=(
  -p
  --model "$model"
  --output-format stream-json
  --verbose
  --include-partial-messages
  --no-session-persistence
  --safe-mode
  --disable-slash-commands
  --strict-mcp-config
  --mcp-config "$mcp_config"
  --settings "$settings_file"
  --permission-mode dontAsk
  --tools "${allowed_tools[@]}"
  --allowed-tools "${allowed_tools[@]}"
  --disallowed-tools 'mcp__*'
  --no-chrome
)

set +e
if [[ -n "$transcript" ]]; then
  printf '%s\n' "$prompt" | (
    cd -- "$workdir"
    env -i \
      "HOME=$run_dir/home" \
      "CLAUDE_CONFIG_DIR=$run_dir/config" \
      "XDG_CONFIG_HOME=$run_dir/xdg-config" \
      "XDG_DATA_HOME=$run_dir/xdg-data" \
      "XDG_STATE_HOME=$run_dir/xdg-state" \
      "XDG_CACHE_HOME=$run_dir/xdg-cache" \
      "TMPDIR=$run_dir/tmp" \
      "PATH=$safe_path" \
      LANG=C.UTF-8 LC_ALL=C.UTF-8 TERM=dumb NO_COLOR=1 CI=1 \
      CLAUDE_CODE_SKIP_PROMPT_HISTORY=1 \
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
      DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1 \
      "${auth_env[@]}" \
      timeout --signal=TERM --kill-after=10s "${timeout_seconds}s" \
      "$cli" "${claude_args[@]}" \
      > >(tee -- "$transcript") 2> >(tee -- "$stderr_file" >&2)
  )
else
  printf '%s\n' "$prompt" | (
    cd -- "$workdir"
    env -i \
      "HOME=$run_dir/home" \
      "CLAUDE_CONFIG_DIR=$run_dir/config" \
      "XDG_CONFIG_HOME=$run_dir/xdg-config" \
      "XDG_DATA_HOME=$run_dir/xdg-data" \
      "XDG_STATE_HOME=$run_dir/xdg-state" \
      "XDG_CACHE_HOME=$run_dir/xdg-cache" \
      "TMPDIR=$run_dir/tmp" \
      "PATH=$safe_path" \
      LANG=C.UTF-8 LC_ALL=C.UTF-8 TERM=dumb NO_COLOR=1 CI=1 \
      CLAUDE_CODE_SKIP_PROMPT_HISTORY=1 \
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
      DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1 \
      "${auth_env[@]}" \
      timeout --signal=TERM --kill-after=10s "${timeout_seconds}s" \
      "$cli" "${claude_args[@]}"
  )
fi
status=$?
set -e
exit "$status"
