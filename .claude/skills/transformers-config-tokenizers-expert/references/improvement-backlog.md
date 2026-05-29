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

## Resolved this pass (2026-05-28)

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
