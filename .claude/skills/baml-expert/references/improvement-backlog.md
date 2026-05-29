# Improvement backlog — baml-expert

Tracks issues attempted but not fully resolvable in one keep/discard iteration, plus what each pass actually changed. Append-only history; carry open items forward with a `(carried <date>)` marker.

## Open

- **Re-confirm docs.boundaryml.com rows online** — Dim 9 — `references/sources.md` (all `docs.boundaryml.com` rows still `Last verified: 2026-04-19`). These are Mintlify SPA pages (JS-rendered); curl returns an empty shell and could not be re-verified this pass. Still 39 days old (within the 90-day no-cap window, so Dim 9 is uncapped), but they should be re-stamped on the next freshen with a JS-capable fetch.

- **Sweep `0.221.0+` references against the published changelog** — Dim 9 — `references/canary-features.md`, `references/cli.md:104-105`, `references/providers.md:24,152`. 0.221.0 (2026-04-14) and 0.222.0 (2026-04-27) are now released, so features the skill labels "canary / 0.221.0+" (lambdas, `?.`/`??`, `ns_*`, void returns, AWS Bedrock token caching, `baml grep`/`baml describe`) have actually SHIPPED. The "canary-only, repo-internal" framing in canary-features.md is now partly inaccurate — those features are reachable from a stock `pip install baml-py>=0.221`. A multi-file reframe (canary vs released) is bigger than one atomic iteration; deferred. No false version numbers remain, but the "only relevant on the BAML repo itself" guidance over-restricts.

- **Add evals coverage for the decision-table rows not yet exercised** — Dim 10 — `evals/evals.json` (3 cases exist: add-function, fix-broken-file, stream-to-fastapi). Uncovered intents: provider/client-block authoring (round-robin/fallback), ClientRegistry/TypeBuilder runtime override, multimodal (image/pdf) input, BAML_LOG debugging. Adding cases is additive content, not a one-line edit; deferred to a dedicated evals pass.

## Resolved this pass (2026-05-28)

- Freshen: corrected `sources.md` GitHub pin `canary @ 0.221.0` → `latest release 0.222.0 (2026-04-27)`; re-stamped to 2026-05-28 (verified via PyPI + npm + GitHub tags: latest 0.222.0).
- Freshen: added `@boundaryml/baml` npm row (latest 0.222.0, exposes both `baml-cli` and `baml` binaries — confirmed in package `bin`) and re-stamped the PyPI row to 2026-05-28 (latest 0.222.0).
- Freshen: added a verified-latest-release note to the sources header (0.222.0, 2026-04-27).
- Freshen: confirmed `baml_options (since 0.216)` is ACCURATE — 0.216.0 released 2025-12-31 per the repo changelog; restored the precise "0.216.0+" pin in `sources.md` after an interim over-cautious reword.
- Improve (Dim 1): added a `defer to jinja-expert` negative-scope clause to the description, disambiguating BAML's Minijinja prompts from standalone Jinja/chat-template authoring.
- Improve (Dim 1/2, simplification): compressed the verbose "Trigger even when the user doesn't name BAML — …, this is the skill." framing to a tighter form, keeping every trigger phrase while staying under the 1024-char description cap (~895 chars).

## Notes for next pass

- Recon input for this pass was stale/hallucinated (described 10 differently-named ref files, `0.70.x` pins, a `2025-01-15` date, and "no evals dir"). NONE of that matched the real skill: 7 ref files, sources dated 2026-04-19, a `canary @ 0.221.0` pin, and an existing `evals/evals.json` with 3 cases. Future passes should re-recon against the live files, not trust a handed-in snapshot.
- Tool session was degraded mid-pass (Bash/Read visible output intermittently empty). All mutations went through `Edit`/`Write`, which returned explicit success; on-disk state is authoritative via those confirmations. A clean-session grep of version strings is advisable next pass as a belt-and-suspenders check.
