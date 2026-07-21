# Improvement backlog — baml-expert

Tracks issues attempted but not fully resolvable in one keep/discard iteration, plus what each pass actually changed. Append-only history; carry open items forward with a `(carried <date>)` marker.

## Open

- **Re-stamp the 6 remaining `docs.boundaryml.com` rows** — Dim 9 — `references/sources.md` (`/home`, `/guide/introduction/what-is-baml`, `/ref/baml/class`, `/ref/baml/attributes`, `/ref/baml/test`, `/guide/baml-advanced/prompt-caching` still `Last verified: 2026-04-19`). *Not* the blocker the 2026-05-28 entry described: WebFetch renders these Mintlify SPA pages fine — four rows were re-verified and stamped 2026-07-21 this pass. The rest were left only because the probe budget went to the version-drift findings. Straightforward next pass. (carried 2026-07-21, reduced in scope)

- **`/ref/baml-cli` no longer documents the subcommand catalogue** — Dim 9 — `references/cli.md`. The public page now covers `init` and nothing else, so `cli.md`'s `generate/test/serve/dev/fmt/grep/describe/optimize/run` catalogue has no upstream page backing it. Not wrong — the commands are real, sourced from the repo and changelog — but the sources.md row's scope text ("baml-cli commands (init/generate/test/serve/dev/fmt)") now overstates what that URL proves. Fixing properly means re-sourcing `cli.md` against `baml-cli/` in the repo, which is a research pass, not a freshen mutation.

- **Add evals coverage for the decision-table rows not yet exercised** — Dim 10 — `evals/evals.json` (3 cases exist: add-function, fix-broken-file, stream-to-fastapi). Uncovered intents: provider/client-block authoring (round-robin/fallback), ClientRegistry/TypeBuilder runtime override, multimodal (image/pdf) input, BAML_LOG debugging. Adding cases is additive content, not a one-line edit; deferred to a dedicated evals pass. (carried 2026-07-21)

## Resolved — 2026-07-21 (freshen)

- **Version drift 0.222.0 → 0.223.0** (published 2026-06-23; verified against PyPI, npm, and the repo changelog, which tops out at 0.223.0). Header, GitHub row, PyPI row, and npm row updated and re-stamped.
- **New in-scope feature: `ctx.output_format(render_null_as=...)`** — PR #3822, merged 2026-06-23, shipped in 0.223.0. Added to SKILL.md's tunables line and to the version-sensitive-claims list. In scope because `ctx.output_format` is a named trigger in the skill's own description.
- **Two-version-line trap documented** — the repo began cutting `baml-language-0.NN.N` releases (0.11.x in June, 0.15.0 on 2026-07-14) for the `baml_language` Rust workspace (the `compiler2` / `sys_llm` compiler and VM), plus per-commit nightlies. `gh release list` therefore returns `baml-language-0.15.1-nightly...` as `isLatest`, and a future freshen reading that as "the version" would downgrade a 0.22x SDK pin to 0.15. Warned against explicitly in `sources.md`. This is the memo'd `releases/latest` blind spot firing on a real repo.
- **Closed the carried "canary vs released" item.** The 0.221.0 feature set has shipped; `canary-features.md` is retitled and its load rule rewritten from audience-based ("only if you work on the BAML repo") to feature-based ("project pins `baml-py>=0.221`"), with the docs-lag — not the release status — named as the reason the file exists. SKILL.md's pointer updated to match.
- **Closed the carried "docs are unfetchable" item** as stated — WebFetch renders the Mintlify pages. `/ref/baml/function`, `/ref/llm-client-providers`, `/guide/baml-basics/streaming` all probed `fresh` (provider catalogue and the three `@stream.*` attributes unchanged); `/ref/baml-cli` probed as content-shrunk and is now its own Open item.

## Resolved — 2026-05-28

- Freshen: corrected `sources.md` GitHub pin `canary @ 0.221.0` → `latest release 0.222.0 (2026-04-27)`; re-stamped to 2026-05-28 (verified via PyPI + npm + GitHub tags: latest 0.222.0).
- Freshen: added `@boundaryml/baml` npm row (latest 0.222.0, exposes both `baml-cli` and `baml` binaries — confirmed in package `bin`) and re-stamped the PyPI row to 2026-05-28 (latest 0.222.0).
- Freshen: added a verified-latest-release note to the sources header (0.222.0, 2026-04-27).
- Freshen: confirmed `baml_options (since 0.216)` is ACCURATE — 0.216.0 released 2025-12-31 per the repo changelog; restored the precise "0.216.0+" pin in `sources.md` after an interim over-cautious reword.
- Improve (Dim 1): added a `defer to jinja-expert` negative-scope clause to the description, disambiguating BAML's Minijinja prompts from standalone Jinja/chat-template authoring.
- Improve (Dim 1/2, simplification): compressed the verbose "Trigger even when the user doesn't name BAML — …, this is the skill." framing to a tighter form, keeping every trigger phrase while staying under the 1024-char description cap (~895 chars).

## Notes for next pass

- Recon input for this pass was stale/hallucinated (described 10 differently-named ref files, `0.70.x` pins, a `2025-01-15` date, and "no evals dir"). NONE of that matched the real skill: 7 ref files, sources dated 2026-04-19, a `canary @ 0.221.0` pin, and an existing `evals/evals.json` with 3 cases. Future passes should re-recon against the live files, not trust a handed-in snapshot.
- Tool session was degraded mid-pass (Bash/Read visible output intermittently empty). All mutations went through `Edit`/`Write`, which returned explicit success; on-disk state is authoritative via those confirmations. A clean-session grep of version strings is advisable next pass as a belt-and-suspenders check.
