---
name: opencode-ci-harness
description: >-
  Run opencode (v2) CLI as a headless, fully-isolated test harness against
  any OpenAI-, Responses- or Messages-compatible endpoint (local inference
  engine or remote API), or against any provider credential already stored
  in an opencode profile (API key or login). Drives multi-step tool-calling
  scenarios, dumps NDJSON transcripts, and diagnoses model + chat-template +
  tool-parser failures without touching the caller's opencode profile (no
  MCP servers, no plugins, no project config, no shared background service).
when_to_use: >-
  When the user says "test this model with opencode", "run a scenario",
  "repro this tool-calling bug", "CI-test the parser", "run opencode
  headless", "bench the template against real agent behavior", "check
  why the model fails at multi-step tool use", or "smoke-test an opencode
  provider". ALSO when iterating on a chat_template / tool-parser pair
  and needing a real agent loop beyond single-turn fixtures. NOT for
  interactive human use — use `opencode` directly for that.
---

# opencode-ci-harness

Targets opencode **v2** (`opencode --version` → `v2.x`). On v1 the runner
fails: v1 has no `--standalone`.

## Rules

| Never | Instead |
|---|---|
| Call `opencode run` directly for a test | `scripts/isolated-run.sh` — sets the whole envelope |
| Run without `--standalone` | The default connects to the operator's background service, which uses the operator's config, credentials and MCP servers |
| Share a data dir with any other opencode process | Fresh scratch `XDG_DATA_HOME` per run (runner does it). The background service resumes unfinished sessions it finds in its data dir, without the run's permissions or step limit |
| Pass/fail on `$?` | Assert on NDJSON events (`scripts/assert-tool-sequence.sh`) |
| Print, log or copy a credential value | `--credential` pipes it into the scratch DB; it never touches disk outside it |
| Copy an OAuth refresh token | `inject-credential.py` withholds it and refuses tokens expiring within `--timeout` + 10 min |
| Use `--pure`, `--dir`, `OPENCODE_PURE`, `OPENCODE_AUTH_CONTENT`, `OPENCODE_DISABLE_DEFAULT_PLUGINS` | Removed in v2 — see `references/isolation.md` |

## Run against an endpoint

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/isolated-run.sh \
  --model "eng/MODEL_NAME" \
  --base-url "BASE_URL/v1" \
  --api-key "$API_KEY" \
  --workdir "$W" --max-turns 12 --timeout 600 \
  --prompt "$SCENARIO" > t.ndjson 2> t.stderr
```

- `--model` is `<provider-alias>/<served-model-id>`; the alias is arbitrary.
- `--base-url` is any reachable endpoint, local or remote. `--api-key` defaults to `sk-dummy` for endpoints without auth.
- `--max-turns` sets `agent.build.steps`; at the cap tools are disabled and the model must answer.
- Shell is denied unless `--allow-shell`. Pass it only for tiers 3 and 7; the shell is not sandboxed.
- Scenario on stdin when `--prompt` is omitted.
- `OC_CI_KEEP=1` keeps the scratch home (copied credentials are deleted).

### Engine API selection (`--npm`)

| `--npm` | Endpoint hit | Use |
|---|---|---|
| `@ai-sdk/openai-compatible` (default) | `POST /v1/chat/completions` | Only one accepting `--provider-options-json` (fields sent verbatim in the request body, e.g. `{"chat_template_kwargs":{"enable_thinking":false}}`) |
| `@ai-sdk/openai` | `POST /v1/responses` | Responses API path |
| `@ai-sdk/anthropic` | `POST /v1/messages` | Messages API path |

- Confirm the endpoint actually hit in the engine access log (`grep -E 'POST /v1/(chat/completions|responses|messages)'`).
- A failure on all three = engine parser/template. A failure on one = that API translation layer.
- Give each variant a distinct alias (`eng-oai/…`, `eng-anthropic/…`). Do not diff token counts across variants.

## Run with a stored credential

Uses one provider credential (API key or OAuth login) from an existing opencode store, so no endpoint config is needed.

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/isolated-run.sh \
  --credential INTEGRATION --model "INTEGRATION/MODEL_ID" \
  --workdir "$W" --timeout 300 --prompt "$SCENARIO" > t.ndjson 2> t.stderr
```

- `INTEGRATION` = `integration_id` in the source store. List them without secrets:
  `sqlite3 -readonly "file:$HOME/.local/share/opencode/opencode.db?mode=ro" "select integration_id, label, active, json_extract(value,'\$.type') from credential"`
- List an integration's models: inject into a scratch home, then `opencode models --standalone` (see `references/isolation.md`).
- Exit 3 with `REFUSED` = OAuth access token too close to expiry or an `external` credential. Ask the operator to refresh it in their own opencode; never work around it.
- Source store: `$OPENCODE_SOURCE_DB`, default `${XDG_DATA_HOME:-~/.local/share}/opencode/opencode.db`. Opened read-only.

## Context budget

Baseline input ≈ 9K tokens per turn before the user prompt (system prompt + tool schemas). Read it with
`jq 'select(.type=="step_finish") | .part.tokens.input' t.ndjson`.

| Served `max_model_len` | Usable |
|---|---|
| 8192 | No |
| 16384 | 1–2 turns, short tool outputs |
| 32768+ | Yes |

Read the served context length from the engine (`GET /v1/models` `max_model_len`, or its startup log); auto-fit settings can land far below the model maximum.

## Scenario tiers

Run in order; stop at the first break; the break class is the diagnosis. Prompts and pass criteria: `references/scenario-bank.md`.

| Tier | Scenario | Stresses |
|---|---|---|
| 0 | glob + reads | Wiring |
| 1 | Parallel reads in one turn | Parallel tool-call format |
| 2 | Read A → decide → read B | tool_result round trip |
| 3 | Nested-JSON / quoted shell args | `tojson(arguments)` fidelity |
| 4 | No tool needed | Hallucinated calls |
| 5 | Missing path | Error → re-plan |
| 6 | 30K-token input + tool call | Long-context parser |
| 7 | Quote-heavy shell | Raw-string serialization |
| 8 | Read a JSON file | Output not re-parsed |
| 9 | Write while edit is denied | Honesty under denial |

## NDJSON events (v2)

Every line: `{type, timestamp, sessionID, ...}`.

| `type` | Fields |
|---|---|
| `step_start` | `part` |
| `text` | `part.text` |
| `reasoning` | `part.text` |
| `tool_use` | `part.tool`, `part.state.status` (`completed`\|`error`), `part.state.input`, `part.state.output` — one event per call, after it settles |
| `step_finish` | `part.reason`, `part.tokens`, `part.cost` — the final one is often missing; do not require it |
| `error` | `error.message` |

Tool names: `shell` (not `bash`), `read`, `glob`, `grep`, `edit`. Turn count = `step_start` count.

## Diagnose

| Symptom | Cause | Next step |
|---|---|---|
| Model text contains tool-call syntax, no `tool_use` | Parser does not recognize the format, or tools absent from the rendered prompt | `OC_CI_KEEP=1`, then `opencode session export <sessionID> --standalone` in the kept home; inspect raw assistant parts |
| `tool_use` with `state.input` `{}` or mangled | Template renders arguments with `repr()`/`str()` instead of `tojson` | Check the template's `tool_call.arguments` rendering |
| `error` event with a parser traceback | Engine-side tool parser crashed | Grep engine log for `tool_parser|Traceback|ValueError` |
| No events, process exits | HTTP failure to the engine | `grep -iE 'ECONNREFUSED|timeout|50[0-9]' t.stderr` |
| Correct round 1, garbage round 2 | Template drops prior `tool_calls` / tool results in the message loop | Inspect the template's history loop |
| `error` event but the run finished with a correct answer | A transient provider error was retried | Treat as pass if the final step completed; exit code is 1 regardless |
| Run hangs, zero events, `/v1/models` still answers | Wedged tunnel or proxy that serves short requests but stalls streams | Connect to the engine directly; restart the run |
| Exit 124 after a `step_finish` with no errors | `--timeout` hit during final text | Raise `--timeout` |

Wrong tool, wrong path, wrong arithmetic with correct tool outputs, or a hallucinated call on tier 4 = model behavior, not a pipeline bug. Separate the two by running the same scenario on two models with the same parser: one passes → model; both fail and another parser passes → parser.

## Special-token leakage

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/scan-token-leakage.sh t.ndjson <model-source>
```

`<model-source>`: model dir with `tokenizer_config.json`, a dir of `.jinja` templates, or a file with one token per line. Exit 0 clean, 1 leak, 2 usage. Zero leaks only means these scenarios did not trigger one — escalate tiers before concluding.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/isolated-run.sh` | Isolated `opencode run --standalone --format json`; `--help` for flags |
| `scripts/inject-credential.py` | Emits one store credential for `opencode auth import` (used by `--credential`) |
| `scripts/assert-tool-sequence.sh` | `assert_tool_order`, `assert_tool_called`, `assert_no_errors`, `assert_turn_count`, `assert_tool_input_matches`, `assert_final_text_matches` |
| `scripts/scan-token-leakage.sh` | Special-token leakage scan |
| `scripts/cleanup.sh` | Remove leftover `/tmp/oc-ci-*` homes |

## References

- `references/isolation.md` — envelope, env vars, credential injection, verification
- `references/scenario-bank.md` — tier prompts, workdir scaffold, pass criteria
- `references/scenario-and-debug.md` — jq recipes, session export, failure rubric
- `references/known-gaps.md` — limits and workarounds
- `references/sources.md` — provenance and verification stamps
