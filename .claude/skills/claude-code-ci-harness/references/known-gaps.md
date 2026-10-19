# Known Gaps

| Symptom | Cause | Check |
|---|---|---|
| `No such tool available: X` although `--tools` lists it | `--bare` was added | Remove `--bare`. Check the `tools` array in `system/init`. |
| 401 in subscription mode | The `setup-token` token expired or was revoked | Regenerate it with `claude setup-token` outside the agent session. |
| 401/403 from an endpoint | Wrong `--token-var`, or the endpoint expects `X-Api-Key` | Check the key name. Retry with `--x-api-key`. |
| `400 Deferred custom tools are only supported on Anthropic models` (`result.is_error=true`) | Tool search was on, so tools went out with `defer_loading` | Keep `ENABLE_TOOL_SEARCH=false` in the runner's endpoint env. |
| `model not found` | The served name does not match `--model` | Compare `system/init.model` with the endpoint's model list. |
| No events at all | The endpoint is unreachable, or auth was rejected before streaming | `curl` the model list with the same auth header. |
| The gateway rejects prompts near 200K tokens | A Claude model name behind `ANTHROPIC_BASE_URL` gets the 1M window | Add `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` to the runner's `env -i` list. |
| The model repeats the same tool call | The tool error does not steer the model, or the argument schema is wrong | Read the `tool_result` the model received. |
| `result.subtype=error_during_execution` with `stop_reason=tool_use` | The stream ended in the middle of a tool call | Inspect the partial input JSON in the last `assistant` event. |
| Tool arguments arrive as `{}` | The server's chat template drops `tojson(arguments)` | Run the same prompt on a second endpoint to tell server from CLI. |

## Limits

- Exit status is not evidence. Assert on `result.subtype` and the error events.
- The runner does not capture raw HTTP bodies. For wire-level evidence, use the endpoint's server log.
- Record `claude --version` with every CI result. The `stream-json` fields change between releases.
