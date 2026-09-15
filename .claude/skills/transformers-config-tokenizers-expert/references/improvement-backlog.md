# Improvement backlog

Tracks issues found during skill-improver passes that could not be resolved
in a single atomic iteration, plus what each pass actually changed.

## Resolved — 2026-09-15 (CI pin vs runtime floor: two numbers, one file apart)

- **vLLM's v0.28.0 release note "Transformers bumped to 5.15.0 (#51668)" is not a
  floor bump.** #51668 moved the **test** pin (`requirements/test/{cuda,cpu,rocm}.txt`
  → `transformers==5.15.0`). The **runtime** requirement
  (`requirements/common.txt`) stayed at `>= 5.5.3`, and is `>= 5.10.4` on v0.29.0.
- **The gap is the finding.** vLLM validates 5.15.0 in CI and permits 5.5.3+ at
  install, so the combination most installs actually get is *below* anything
  anyone tested. Now recorded as a two-row table, because the two numbers live in
  different files and only one binds an install.
- **It also makes this file's existing recommendation non-arbitrary:** 5.15.0 is
  simultaneously the floor clearing all three tokenizer-path fixes **and** the
  version CI exercises. Two independent reasons, same pin.
- **Self-check, worth recording:** the release note appeared to contradict the
  requirements file cited in this skill earlier today. Grepping *every*
  requirements file rather than trusting either source showed both were correct
  about different things. A release note that names a version is not automatically
  naming the version an install will resolve.

## Resolved — 2026-09-15 (the engine floor does not reach the security floor)

- **Corrected: "≥ 5.15.0 … is also vLLM v0.28.0's floor".** It is not. Read from
  `requirements/common.txt` at the tags today: **v0.27.0 and v0.28.0 pin
  `transformers >= 5.5.3`; v0.29.0 and `main` pin `>= 5.10.4`.** Neither reaches
  5.15.0.
- **The sentence it supported was the dangerous part** — "the version you need
  for engine compatibility is the version you need for these" — because it is
  reassuring and false. An install resolving `transformers` from vLLM's floor
  alone lands on 5.10.4, which clears #46191 and leaves the arbitrary-file-read
  (#46279, 5.13.0) and the ReDoS (#47498, 5.15.0) open. Replaced with a
  four-row table showing exactly which fixes each floor clears, and an explicit
  instruction to pin `transformers` rather than inherit it.
- **New, and the reason this is worth more than a number swap:** the advisory's
  `first_patched_version: 5.10.0` points at a version that **is on PyPI and
  fully yanked** — yank reason, verbatim: *"We pushed from a week old main
  branch … mostly it is missing a bunch of fixes!"*. A resolver picking latest
  skips it, **but `transformers==5.10.0` pinned exactly still installs**, because
  pip honours an exact pin over a yank. That is precisely how an air-gapped
  mirror built from a pinned requirements file acquires a build the advisory
  calls patched and upstream calls broken.
- The skill was already **ahead of the advisory database** on the 5.10.0-vs-5.10.1
  distinction, and that is what stopped this pass from "correcting" a right
  floor down to a wrong one on the strength of the feed. The fleet advisory
  sweep surfaced this via the *ecosystem* database (`/advisories?ecosystem=pip
  &affects=transformers`), which lists four 2026 advisories the repo feed shows
  as empty — the blind spot the sweep's `no repo feed` marker exists to flag.
- Verified but unchanged: PR #47498 is merged 2026-07-24, "Fix potential ReDoS by
  escaping tokenizer filename used as regex pattern", matching the table.

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

_None._ Nothing here is waiting on an absent ruling, credential, release, or
measurement nobody can run.

## Resolved — 2026-09-15 (the re-probe already happened; only a header said otherwise)

- **The item was stale and the stale thing was a heading.** It asked a future
  freshen to re-probe the HuggingFace model-repo rows, still stamped 2026-04-21.
  That re-probe landed on 2026-08-18: all 21 rows in that section carry that date,
  as do 67 of the 77 rows in the file. Only the section header still read
  "(verified 2026-04-21)".
- **Header removed rather than updated.** A date in the heading duplicates the
  per-row `Last verified` column and can only drift away from it — which is exactly
  what happened, leaving a header claiming five months where every row underneath
  claimed four weeks. The row stamp is the truth; the heading now says nothing about
  time.

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
