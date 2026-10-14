# Known gaps (opencode v2 as a test harness)

| Gap | Workaround |
|---|---|
| No prompt-render-only / dry-run mode | Render the chat template offline with the tokenizer (`apply_chat_template`) |
| No `--seed` / `--temperature` flag | Set sampling defaults on the engine, or send them via `--provider-options-json` |
| Request/response bodies are not logged | Engine access log, or mitmproxy between opencode and the engine |
| No assertion DSL or scenario-file format | `scripts/assert-tool-sequence.sh`; prompts in `scenario-bank.md` |
| No `--max-turns` flag | `agent.build.steps` in config (runner `--max-turns`) |
| Exit code is 1 after any `error` event, even when a retried step then succeeded | Decide pass/fail from events: last step completed + expected tools + final text |
| Final `step_finish` often missing from `--format json` | Never require it; read final-step tokens from `opencode session export` |
| Auto-compaction summaries appear as ordinary `text` events | Keep scenarios below the compaction threshold, or match final text on content, not position |
| A killed run leaves its session resumable; any opencode service sharing that data dir resumes it unattended | Never share `XDG_DATA_HOME`; delete the scratch home (runner default) |
| Wedged tunnel: zero events while `/v1/models` still answers | Connect to the engine directly instead of through the tunnel; restart the run |
| Exit 124 after a `step_finish` with no errors | `--timeout` hit during final text; raise it (runner default 600 s) |
| `opencode run --agent <unknown>` does not fail closed | Only use `build` (default) or agents defined in the config |

## When not to use this harness

| Need | Use instead |
|---|---|
| Template render check only | Offline template render |
| Single-turn tool-call fixtures | Fixture tests against the engine directly |
| Throughput / latency numbers | A load-testing benchmark against the endpoint; the agent loop adds variable overhead |
| Interactive exploration | Plain `opencode` with your own profile |
