# Isolation envelope (opencode v2)

`scripts/isolated-run.sh` applies all of this. Use this file when building a
variant of the runner or checking that isolation held.

## Envelope

| Setting | Value | Effect |
|---|---|---|
| `--standalone` | flag on every `run`/`models`/`auth`/`session` call | Private server child that inherits this env and exits on stdin EOF. Without it the CLI attaches to the operator's background service |
| `OPENCODE_TEST_HOME`, `HOME` | scratch dir | Home for `~/.claude` and `~/.agents` compatibility roots (skills, instructions) |
| `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME` | under the scratch dir | Global config, credential DB, model cache, service registry |
| `TMPDIR` | under the scratch dir | Contains runtime extracts |
| `OPENCODE_CONFIG_PROJECT_DISABLE=1` (+ `OPENCODE_DISABLE_PROJECT_CONFIG=1`) | | No `.opencode/` `.claude/` `.agents/` walk-up from the workdir |
| `OPENCODE_DISABLE_MODELS_FETCH=1` | `--base-url` runs only | No catalog download; `--credential` runs need the catalog |
| `OPENCODE_LOG_LEVEL=DEBUG` + `--print-logs` | | Server logs on stderr |
| unset `OPENCODE_CONFIG`, `OPENCODE_CONFIG_DIR`, `OPENCODE_CONSOLE_TOKEN`, `OPENCODE_SERVER_URL`, `OPENCODE_PASSWORD` | | Caller overrides that bypass the scratch home |
| `cd "$WORKDIR"` | | `run` takes its project root from `$PWD` |
| `</dev/null` when the prompt is an argument | | `run` appends any non-TTY stdin to the message |

## Config (`OPENCODE_CONFIG_CONTENT`)

v1-shaped keys are accepted and migrated by v2. The runner writes:

```json
{
  "provider": { "eng": {
    "npm": "@ai-sdk/openai-compatible",
    "options": { "baseURL": "BASE_URL/v1", "apiKey": "sk-dummy" },
    "models": { "MODEL_NAME": { "name": "MODEL_NAME" } } } },
  "model": "eng/MODEL_NAME",
  "agent": { "build": { "steps": 12 } },
  "mcp": {},
  "plugin": [],
  "autoupdate": false,
  "share": "disabled",
  "permission": { "*": "deny", "read": "allow", "glob": "allow", "grep": "allow", "list": "allow", "bash": "allow" }
}
```

- Permission rules: last match wins, so `"*": "deny"` goes first. `bash` maps to the v2 action `shell`.
- Rules that resolve to `ask` are auto-rejected in `run`; never pass `--auto` in CI.
- `apiKey` must be non-empty even when the engine ignores it.
- Extra request-body fields (openai-compatible only): put them in the model's `options`; v2 sends unknown model options in the body. Do not wrap them in `providerOptions`.
- The default agent is `build`; `steps` caps its loop.
- `--credential` runs: omit `provider` entirely.

## Credential injection (`--credential`)

The v2 credential store is the `credential` table in `$XDG_DATA_HOME/opencode/opencode.db`. Value types: `key`, `oauth` (`access`, `refresh`, `expires` ms, `methodID`, `metadata`), `external`.

- A legacy `auth.json` in a fresh data dir is NOT imported (fresh DBs are bootstrapped from the schema). Use `opencode auth import --standalone`, which reads an `opencode auth export` JSON array on stdin.
- OAuth refresh happens only when `expires` is within 5 min, and writes the rotated token back. A copy that refreshes can invalidate the operator's login. So `inject-credential.py` copies `access` with an empty `refresh`, and refuses when `expires` is earlier than now + `--timeout` + 600 s.
- `external` credentials: refused (secrets live outside the store).

Manual injection, e.g. to list an integration's models:

```bash
T=$(mktemp -d /tmp/oc-ci-XXXXXX); trap 'rm -rf "$T"' EXIT
SRC=${XDG_DATA_HOME:-$HOME/.local/share}/opencode/opencode.db   # resolve BEFORE redirecting XDG
export OPENCODE_TEST_HOME=$T HOME=$T XDG_CONFIG_HOME=$T/config XDG_DATA_HOME=$T/data \
  XDG_CACHE_HOME=$T/cache XDG_STATE_HOME=$T/state TMPDIR=$T/tmp OPENCODE_CONFIG_PROJECT_DISABLE=1 \
  OPENCODE_CONFIG_CONTENT='{"mcp":{},"plugin":[]}'
mkdir -p $T/{config,data,cache,state,tmp,wd}; cd $T/wd
python3 -I ${CLAUDE_SKILL_DIR}/scripts/inject-credential.py "$SRC" INTEGRATION 1200 |
  opencode auth import --standalone
opencode models --standalone </dev/null | grep '^INTEGRATION/'
```

## Verify isolation held

Before and after a batch:

```bash
snap() { find ~/.local/share/opencode -maxdepth 1 -type f -exec sha256sum {} +
         find ~/.config/opencode -path '*/node_modules' -prune -o -type f -exec sha256sum {} +
         sqlite3 -readonly "file:$HOME/.local/share/opencode/opencode.db?mode=ro" \
           'select id, value, time_updated from credential order by id' | sha256sum; }
snap > before.txt; <runs>; snap | diff before.txt - && echo unchanged
```

- A live operator background service may write `opencode.db` on its own; then the credential-row hash and a session lookup decide: `select count(*) from session_message where session_id='<sessionID from transcript>'` must be 0.
- `pgrep -af '[o]pencode serve'` afterwards must show only processes that existed before the batch. Never `pkill` a pattern; kill by PID.
- `ls /tmp | grep '^oc-ci-'` must be empty unless `OC_CI_KEEP=1`.

## Residual leaks

| Leak | Mitigation |
|---|---|
| System config dir (`/etc/opencode`, macOS `/Library/Application Support/opencode`, macOS MDM preferences) still loads | Check it is absent on the CI host |
| `.well-known` remote config fetched for credentials that declare one | Block egress for air-gapped CI |
| Built-in (internal) plugins still run; `"plugin": []` only adds none | Accept; external plugins load only from the isolated config dirs |
