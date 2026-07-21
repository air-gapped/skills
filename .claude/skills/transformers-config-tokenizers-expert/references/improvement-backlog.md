# Improvement backlog

Tracks issues found during skill-improver passes that could not be resolved
in a single atomic iteration, plus what each pass actually changed.

## Open

- **RECON/APPLY version mismatch — recon scored a different skill** (process, not a content dim).
  The 2026-05-28 recon JSON handed to the APPLY stage described a 69-line stub
  (no references/, no sources.md, third-person-but-thin, total 52/100). The
  actual on-disk skill is a mature 334-line SKILL.md with a full references/
  tree (config-files, tokenizer-classes, chat-template-contract, engine-knobs,
  precedence-rules, hall-of-shame, snippets.py) and a pre-existing dated
  sources.md. Every recon hypothesis (add sources.md, fix a "chat_template only
  in tokenizer_config.json" stub line, add an AutoTokenizer snippet, add a
  precedence table) targets content that does not exist in this version or is
  already present and correct. Cannot be acted on in one iteration: the fix is
  to re-run recon against the real skill so the score loop has a valid baseline.
  File-set: whole skill vs recon JSON.

- **sources.md per-file / per-model-repo rows still dated 2026-04-21** (Dim 9, freshness).
  This pass re-confirmed and re-stamped only the release/tag-tracking rows
  (transformers releases, vLLM releases, tokenizers tags) to 2026-05-28 from
  authenticated `gh` lookups. The ~45 per-source-file (github blob) and
  per-model-repo (huggingface.co) rows were NOT individually re-fetched this
  pass, so they correctly retain their 2026-04-21 stamp (re-stamping unverified
  rows would be false). They are 37 days old — under the 90-day Dim 9 cap, so no
  cap fires, but a future freshen should re-probe the HF model-repo configs
  (Kimi-K2.6, GLM-5.1, Gemma-4, DeepSeek-V3) since lab configs churn fastest.
  File: references/sources.md.

## Resolved — 2026-07-21 (freshen)

- **transformers v5.9.0 → v5.14.1** (2026-07-16; five minors since the last
  stamp). The load-bearing claim — *no breaking tokenizer/chat-template API
  change* — now extends **through 5.14.1**, and not by assumption: the
  `Breaking changes` sections of 5.13.0 and 5.14.0 are entirely `kernels`
  integration plus generation/SDPA work, and 5.10–5.12 carry none touching this
  surface. Independently corroborated the same day by the `jinja-expert` freshen,
  which re-read `chat_template_utils.py` on `main` and found the Jinja env
  contract byte-identical to the 5.9-era description.
- **#45205 shows CLOSED but is not fixed.** GitHub reports closed 2026-06-10 with
  `stateReason: COMPLETED`; the closing comment is HuggingFace's inactivity bot.
  A freshen trusting `state`/`stateReason` would have deleted the Gemma-4
  chat-template gotcha from `SKILL.md`, `config-files.md`,
  `chat-template-contract.md` and `hall-of-shame.md`. Re-labelled as
  *stale-closed, unresolved* in each, and a warning added to `sources.md`.
  **The identical pattern was found in `sgl-project/sglang` the same day**, so
  it is recorded as the default assumption rather than a repo quirk.
- **vLLM v0.21.0 → v0.25.1** (2026-07-14) — four minors in two months. The vLLM
  rows are `blob/main` links so the URLs do not rot, but their *claims* were
  verified against a v0.21-era tree and were **not** re-read this pass.
  `engine-knobs.md` now says so explicitly instead of implying currency. This is
  the largest un-re-verified surface in the skill and the obvious next pass.
- **`tokenizers` (Rust) still v0.23.1** — no v0.24 tag; only rc's beneath it.
- **PR #43104 still OPEN**, unmerged since 2026-01; #45359 confirmed MERGED
  2026-04-13. The five older cited issues were already closed before the previous
  stamp and are cited as history, so their state is not load-bearing.

## Resolved — 2026-05-28

- Freshened `references/tokenizer-classes.md` version timeline: "Current stable"
  moved from v5.5.4 (2026-04-13) / 5.6.0.dev0 to v5.9.0 (2026-05-20), noting the
  weekly-minor cadence continued (5.6–5.9) with no breaking tokenizer/chat-template
  API change — verified against the v5.9.0 release body via `gh release view`.
- Freshened `references/engine-knobs.md` vLLM primary-source label from
  "~v0.19.1, 2026-04-18" to "~v0.21.0, latest release 2026-05-15" — verified via
  `gh release view vllm-project/vllm`.
- Re-stamped + added release-tracking rows in `references/sources.md`
  (transformers releases v5.9.0, vLLM releases v0.21.0, tokenizers tag v0.23.1),
  each Last-verified 2026-05-28 from authenticated `gh` lookups. Restored the
  file to its pristine HEAD blob first to clear contamination from an errant
  early-session Write.
