#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

skill_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
runner="$skill_dir/scripts/isolated-run.sh"
assert_events="$skill_dir/scripts/assert-events.sh"
tmp_dir=$(mktemp -d /tmp/claude-code-ci-test.XXXXXX)
trap 'rm -rf -- "$tmp_dir"' EXIT

fake_cli="$tmp_dir/fake-claude"
record="$tmp_dir/record"
transcript="$tmp_dir/transcript.ndjson"
secrets_file="$tmp_dir/secrets.env"

printf '%s\n' 'MY_TEST_TOKEN=offline-secret' > "$secrets_file"
chmod 600 "$secrets_file"

cat > "$fake_cli" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
{
  printf 'config=%s\n' "\$CLAUDE_CONFIG_DIR"
  printf 'home=%s\n' "\$HOME"
  printf 'auth_token_set=%s\n' "\$([[ -n "\${ANTHROPIC_AUTH_TOKEN:-}" ]] && printf yes || printf no)"
  printf 'api_key_empty=%s\n' "\$([[ -z "\${ANTHROPIC_API_KEY:-}" ]] && printf yes || printf no)"
  printf 'oauth_set=%s\n' "\$([[ -n "\${CLAUDE_CODE_OAUTH_TOKEN:-}" ]] && printf yes || printf no)"
  printf 'base_url_set=%s\n' "\$([[ -n "\${ANTHROPIC_BASE_URL:-}" ]] && printf yes || printf no)"
  printf 'tool_search=%s\n' "\${ENABLE_TOOL_SEARCH:-unset}"
  printf '%s\n' "\$@"
} > "$record"
printf '%s\n' '{"type":"system","subtype":"init","tools":["Read","Glob"],"model":"offline-model"}'
printf '%s\n' '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Glob","input":{"pattern":"*"}}]}}'
printf '%s\n' '{"type":"result","subtype":"success","num_turns":1}'
EOF
chmod 700 "$fake_cli"

# Run 1: unauthenticated endpoint, no secrets file involved.
CLAUDE_CODE_CI_CLAUDE_BIN="$fake_cli" \
  "$runner" --base-url http://offline.invalid:8000 --model offline-model \
  --timeout 0 --transcript "$transcript" --prompt 'offline test' >/dev/null

"$assert_events" "$transcript" --expect-tools Glob --expect-model offline-model --max-turns 1 >/dev/null
case "$(<"$record")" in
  *"config=/tmp/claude-code-ci."* ) ;;
  *) printf 'isolation test failed: config path was not temporary\n' >&2; exit 1 ;;
esac
case "$(<"$record")" in
  *"home=/tmp/claude-code-ci."* ) ;;
  *) printf 'isolation test failed: home path was not temporary\n' >&2; exit 1 ;;
esac
if while IFS= read -r arg; do [[ "$arg" == --max-budget-usd ]] && exit 0; done < "$record"; then
  printf 'budget cap unexpectedly present\n' >&2
  exit 1
fi

# Run 2: token-var resolved from the secrets file; API key stays empty by default.
: > "$record"
CLAUDE_CODE_CI_CLAUDE_BIN="$fake_cli" \
  "$runner" --base-url http://offline.invalid:8000 --model offline-model \
  --token-var MY_TEST_TOKEN --secrets-file "$secrets_file" \
  --timeout 0 --transcript "$transcript" --prompt 'offline test' >/dev/null

grep -q 'auth_token_set=yes' "$record" || { printf 'auth test failed: token not passed\n' >&2; exit 1; }
grep -q 'api_key_empty=yes' "$record" || { printf 'auth test failed: ANTHROPIC_API_KEY not empty\n' >&2; exit 1; }
grep -q 'tool_search=false' "$record" || { printf 'endpoint test failed: tool search not disabled\n' >&2; exit 1; }

# Run 3: subscription mode -- no base URL; OAuth token only, no gateway vars.
printf '%s\n' 'CLAUDE_CODE_OAUTH_TOKEN=offline-oauth' >> "$secrets_file"
: > "$record"
CLAUDE_CODE_CI_CLAUDE_BIN="$fake_cli" \
  "$runner" --model sonnet --secrets-file "$secrets_file" \
  --timeout 0 --transcript "$transcript" --prompt 'offline test' >/dev/null

grep -q 'oauth_set=yes' "$record" || { printf 'subscription test failed: OAuth token not passed\n' >&2; exit 1; }
grep -q 'base_url_set=no' "$record" || { printf 'subscription test failed: ANTHROPIC_BASE_URL set\n' >&2; exit 1; }
grep -q 'auth_token_set=no' "$record" || { printf 'subscription test failed: ANTHROPIC_AUTH_TOKEN set\n' >&2; exit 1; }
grep -q 'tool_search=unset' "$record" || { printf 'subscription test failed: ENABLE_TOOL_SEARCH set\n' >&2; exit 1; }
grep -q 'api_key_empty=yes' "$record" || { printf 'subscription test failed: ANTHROPIC_API_KEY not empty\n' >&2; exit 1; }

# An API error is reported as subtype=success with is_error=true; it must fail.
api_error="$tmp_dir/api-error.ndjson"
printf '%s\n' '{"type":"system","subtype":"init","tools":["Read","Glob"],"model":"offline-model"}' \
  '{"type":"result","subtype":"success","is_error":true,"num_turns":1,"result":"API Error: 400"}' > "$api_error"
if "$assert_events" "$api_error" >/dev/null 2>&1; then
  printf 'assert test failed: is_error=true passed\n' >&2
  exit 1
fi

printf 'pass: offline isolation, no-budget-cap, generic auth contract, subscription mode, event assertions\n'
