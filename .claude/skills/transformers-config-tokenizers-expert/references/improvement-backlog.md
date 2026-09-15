# Improvement backlog

Tracks issues found during skill-improver passes that could not be resolved
in a single atomic iteration, plus what each pass actually changed.

## Resolved — 2026-09-15 (an obsolete process artifact)

- **RECON/APPLY version mismatch — CLOSED as obsolete.** The entry records that a
  2026-05-28 recon JSON described a 69-line stub while the on-disk skill was a
  mature 334-line SKILL.md with a full `references/` tree, so every hypothesis it
  produced targeted content that did not exist. That is a fact about one stale
  artifact from one run, not a defect in this skill, and the artifact is long
  gone. Its stated fix — "re-run recon" — happens automatically on the next pass.
- Nothing in the skill was ever wrong because of it. Carrying it in Open made the
  skill look like it had an outstanding content problem when it did not.

## Resolved — 2026-09-15 (freshen to v5.17.0)

- **Three 2026 security fixes land in exactly this skill's subject — the
  tokenizer/config loading path — and all three are reachable with NO
  `trust_remote_code`.** #46279 (v5.13.0): a `"vocab_file": "/etc/x"` or
  `"../x"` in `tokenizer_config.json` was kept and opened verbatim, giving
  **arbitrary local file read** from a plain `AutoTokenizer.from_pretrained`.
  #47498 (v5.15.0): the tokenizer filename went straight into `re.search()` as
  a pattern, so regex metacharacters in a repo-controlled name gave **ReDoS**.
  #46191 (v5.10.1): chat-template names became `<name>.jinja` paths under a
  directory join, so `"../../foo"` made `save_pretrained` **write outside the
  target directory**. Added as a table with the floor.
- **The floor is transformers ≥ 5.15.0, which is also vLLM v0.28.0's floor** —
  the version needed for engine compatibility is the version needed for these.
- **A patched-version field that names a release you cannot install.** The
  advisory for #46191 records `first_patched_version: 5.10.0`. **v5.10.0 does
  not exist**: it was yanked for being published from a corrupted branch, and
  v5.10.1's own release notes say so verbatim. First installable fix is 5.10.1.
  Worth keeping as a worked example of why a patched-version field is a lead
  rather than an answer.
- **Chat-template precedence is now documented upstream, so it stops being
  folklore.** `docs/source/en/chat_templating_writing.md` §"Loading precedence"
  (PR #47650, shipped v5.15.0): the loader reads any embedded `chat_template`
  from `tokenizer_config.json`, then **overrides it** with a root
  `chat_template.jinja` if present, then merges `additional_chat_templates/`.
  When both exist the embedded value is read and discarded — so a repo with a
  *current* inline template beside a *stale* sidecar silently serves the stale
  one. The docs now call the embedded field and `chat_template.json`
  "load-only legacy format[s]"; writers only ever emit the sidecar.

### Checked — one citation that does not resolve

- **`transformers_keys_to_ignore_compat` returns 0 hits** in a code search over
  `huggingface/transformers`. The real, populous analogs are
  `_keys_to_ignore_on_load_missing` / `_keys_to_ignore_on_load_unexpected` and
  `keys_to_ignore_at_inference`. Recorded as **unverified rather than removed**:
  the name surfaced in a *vLLM Omni* requirements comment referring to that
  project's own `model_executor/models/utils.py`, so it may be a vllm-omni-side
  symbol rather than a transformers one. Do not cite it as a transformers
  attribute without resolving it there first.

## Open


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
