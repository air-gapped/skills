# Sources

External references backing this skill's claims, with verification stamps.
Freshen mode probes these rows first.

| Ref | URL | Last verified | Pinned |
|---|---|---|---|
| `opencode run` flags (`--standalone`, `--format json`, `--print-logs`, no `--pure`/`--dir`/`--max-turns`); `models`/`auth import`/`session export` take `--standalone` | `opencode <cmd> --help` (local run) | 2026-10-14 | opencode v2.0.28 |
| Background service vs standalone child; child inherits env, exits on stdin EOF | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/cli/src/services/standalone.ts | 2026-10-14 | v2.0.28 |
| Env vars honored: `OPENCODE_TEST_HOME` (`packages/util/src/global.ts`), `XDG_*` (`packages/util/src/global-roots.ts`), `OPENCODE_CONFIG_CONTENT` / `OPENCODE_CONFIG_PROJECT_DISABLE` / `OPENCODE_DISABLE_MODELS_FETCH` (`packages/cli/src/server-process.ts`), `OPENCODE_LOG_LEVEL` (`packages/util/src/observability/logging.ts`); `OPENCODE_PURE`, `OPENCODE_AUTH_CONTENT`, `OPENCODE_DISABLE_DEFAULT_PLUGINS` absent | https://github.com/anomalyco/opencode/tree/v2.0.28/packages | 2026-10-14 | v2.0.28 |
| `run` root from `$PWD`; non-TTY stdin appended to the message | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/cli/src/run/run.ts | 2026-10-14 | v2.0.28 |
| Config discovery: `~/.claude`/`~/.agents` compatibility roots under the home, project walk-up | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/core/src/config/discovery.ts | 2026-10-14 | v2.0.28 |
| v1 config migration (`permission`→rules, `bash`→`shell`, `agent.*.steps`, openai-compatible model options → request body) | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/core/src/config/normalize.ts, `packages/core/src/v1/config/migrate.ts`, `packages/core/src/v1/config/provider-options.ts` | 2026-10-14 | v2.0.28 |
| Permission rules: last match wins | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/core/src/permission.ts | 2026-10-14 | v2.0.28 |
| Default agent `build` | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/core/src/agent.ts | 2026-10-14 | v2.0.28 |
| NDJSON event types and fields; error → exit 1; questions cancelled in `run` | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/cli/src/run/noninteractive.ts | 2026-10-14 | v2.0.28 |
| Credential store = `credential` table; value types `key`/`oauth`/`external` | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/core/src/credential.ts, `packages/schema/src/credential.ts` | 2026-10-14 | v2.0.28 |
| OAuth refresh only within 5 min of expiry, result written back | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/core/src/integration.ts (`connection.resolve`) | 2026-10-14 | v2.0.28 |
| OAuth provider refresh stores the returned (rotated) refresh token | https://github.com/anomalyco/opencode/blob/v2.0.28/packages/core/src/plugin/provider/chatgpt.ts | 2026-10-14 | v2.0.28 |
| Legacy `auth.json` not imported into a schema-bootstrapped DB; `auth import` reads an export array | local run (credential table empty after bootstrap) + https://github.com/anomalyco/opencode/blob/v2.0.28/packages/cli/src/commands/handlers/auth/import.ts | 2026-10-14 | v2.0.28 |
| Killed standalone session resumed by background service sharing the data dir (open) | https://github.com/anomalyco/opencode/issues/55076 | 2026-10-14 | — |
| Final `step_finish` dropped in `--format json` (open; reproduced locally) | https://github.com/anomalyco/opencode/issues/53207 | 2026-10-14 | — |
| Exit 1 after a retried transient provider error (open) | https://github.com/anomalyco/opencode/issues/50062 | 2026-10-14 | — |
| Compaction internals emitted as `text` events (open) | https://github.com/anomalyco/opencode/issues/42238 | 2026-10-14 | — |
| `run --agent` does not fail closed on unknown names (open) | https://github.com/anomalyco/opencode/issues/47038 | 2026-10-14 | — |
| Local execution evidence: `--base-url` tier 0 over an OpenAI-compatible endpoint; `--credential` tiers 0 and 1 on one API-key and one OAuth integration (all assertions pass, leakage scan clean, source store byte-identical before/after, no server left running) | n/a (local run) | 2026-10-14 | opencode v2.0.28 |

v1-era issues previously cited here (#10012, #20799, #20823, #21427, #15558, #17978 and feature requests) are all closed; none is load-bearing for v2.
