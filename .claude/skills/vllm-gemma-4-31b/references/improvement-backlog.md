# Improvement backlog — vllm-gemma-4-31b

Carries findings across `/skill-improver` runs. Skill-improver reads this in
Phase 0 and updates it in Phase 6. Do NOT delete entries — move to "Resolved
this pass" instead.

## Open

_All four items below carried forward unchanged at the 2026-07-21 freshen._

### 1. Narrow trigger surface (Dim 1 — locked by author mandate, carried 2026-05-28)

**Pointer:** `SKILL.md:6-7` (`when_to_use`)

**Finding:** Blind scoring agent (2026-04-30 final pass) flagged that
`when_to_use` requires both "Gemma 4 31B" AND {vLLM, deployment, tuning,
performance} to fire. Misses common operator shorthand: "AWQ-4bit gemma",
"cyankiwi", "RedHatAI", "EAGLE3 speculator gemma", "serving gemma-4 on H100".

**Why skill-improver couldn't apply it:** the author explicitly rejected
broader trigger surfaces in this skill's authoring session (2026-04-30):

> "no one writes like this... sorry but remove those triggers '31B
> replacement for our 27B', 'long-document summarizer', 'why does
> throughput plateau' — the only triggers are really gemma 4 31b"

> "you do not need the exact words with or without dashes do you? you
> would understand anyway would you not?"

The score is by design, not by oversight. **Do not auto-fix in `improve`
or `freshen` mode.** If trigger misses become a problem in practice, switch
to `/skill-improver trigger vllm-gemma-4-31b --missed "<phrase>"` mode to
measure empirically — that's the only mode the author has consented to.

**2026-05-28:** RECON re-proposed enriching `when_to_use` with quoted
trigger-phrase + model-id variants (its highest-leverage Dim 1 hypothesis).
NOT applied — same author mandate above still binds. Left for `trigger` mode.

### 2. "Why gemma-4 behaves differently" + "What was NOT measured" are speculative/backlog content inline in SKILL.md (Dim 2/6 — carried 2026-05-28)

**Pointer:** `SKILL.md` "Why gemma-4-31B-AWQ behaves differently…" section
and "What was NOT measured" section (both still inline).

**Finding:** The four numbered "likely reasons" (AWQ vs fp8 weight size,
TRITON_ATTN scaling, EAGLE3 spec-dec topology, 31B vs 27B layer count) are
plausible mechanisms but none carry a measurement or upstream-source citation;
the "What was NOT measured" list is backlog content, not a deploy decision.
RECON proposed relocating both to a new `references/analysis.md`.

**Why it could not be applied this pass:** the relocation was attempted but
the `Write` of `references/analysis.md` was rejected by the runtime subagent
guard ("return findings as text, not write report files"). With no destination
file creatable, shipping the SKILL.md pointer would have dangled and the
content would have been lost, so the relocation was reverted. A net-neutral
"plausible mechanisms, not measured attributions" framing line WAS added to
the why-different section inline.

**Why the citation gap also can't close in one edit:** confirming each
mechanism needs a follow-up empirical run measuring TP=1 vs TP=2 on Gemma 4
with one mechanism varied at a time (FLASH_ATTN forced, EAGLE3 disabled, fp8
vs AWQ). That's a multi-hour GPU-instance investigation.

**Trigger to revisit:** re-run APPLY in an environment that permits creating
`references/*.md` (the guard here blocks subagent file writes outside edits to
existing files) to land the relocation; and/or run a new Gemma 4 audit to
attach data to each mechanism.

### 3. PUSH recipe duplicates ~90% of LIGHT flags (Dim 6/2 — user-vetoed 2026-05-28)

**Pointer:** `SKILL.md` PUSH recipe code block

**Finding:** RECON proposed collapsing the PUSH recipe to a 5-flag diff
against LIGHT to save ~12 lines toward the 150-line target.

**Why it was NOT applied:** the user prioritises copy-paste-ability of BOTH
full recipes over the line savings. This is a settled author-preference
decision, not a pending task. Do NOT re-propose the collapse in `improve` mode.

### 4. "Reproduction artifacts" tree points to a private repo (Dim 6/8 — minor, carried 2026-05-28)

**Pointer:** `SKILL.md:246-262`

**Finding:** Block lists paths in the `model-preflight` repo
(`findings/cyankiwi/gemma-4-31B-it-AWQ-4bit/...`). Useful for the author's
future reference but inert for any other skill consumer.

**Why skill-improver couldn't apply it:** removing it might violate
"Preserve the Author's Intent" — the author is the primary consumer of
this skill (this is a personal-knowledge capture, not a public-facing
artifact). Author should decide explicitly whether to keep, trim, or
gate behind a `<details>` block.

**Trigger to revisit:** if the skill ever ships to a public skills index or
gets shared with collaborators, drop the section then.

## Resolved — 2026-07-21 (freshen)

- **chat_template staleness: converted from inference to measurement (highest
  value).** Prior passes asserted the community quant "is stale until they
  re-pull." This pass diffed the two files. `cyankiwi/gemma-4-31B-it-AWQ-4bit`
  ships a `chat_template.jinja` hashing `94899c0f…25bff413` — byte-identical to
  the 2026-04-30 canonical — while canonical is now `ae53464b…8de4c6d4`
  (18683 B), **114 lines apart**. Rewrote SKILL.md fact #3 to name the five
  concrete behaviours the frozen copy gives up (`preserve_thinking`,
  `continues_into_next` turn closure, `<|channel>thought` re-open after
  `tool_response`, null tool-argument → `null`, empty-`messages` guards) and to
  quote the template's own new header: *"Published: 2026-07-09 — Fixed
  tool-calling loops, turn closures, and thinking content-ordering."*
- **Corrected an over-broad claim.** Fact #3 previously implicated
  "cyankiwi/RedHatAI quants." `RedHatAI/gemma-4-31B-it-speculator.eagle3` ships
  **no `chat_template.jinja` at all** (4 files: README, config.json, config.py,
  model.safetensors) and is untouched since 2026-04-14. Scoped the claim to
  cyankiwi.
- **Closed the 2026-05-28 honest gap: r05/r06 re-pinned at v0.25.1.** Both
  source claims survived five minors. `get_batch_defaults` moved 2207-2288 →
  2397-2478 with GPU-branch logic unchanged (H100/H200 still share a path); the
  P-EAGLE requirement moved 341 → 352-366 and **reversed check order**
  (`dflash_config.mask_token_id` now first). Replaced the line-number pins in
  SKILL.md and `hbm-saturation.md` with symbol pins — these numbers have now
  been rewritten twice for zero semantic change.
- **Qualified "the only hardware-aware default."** v0.25.1 added a
  `current_platform.is_tpu()` sub-branch (V6E/V5E) *inside*
  `get_batch_defaults`. The claim now reads as "only function," not "only
  branch." The H100-vs-H200 conclusion is unaffected.
- **§3.0 catch on r08.** Issue #22780 was recorded as "closed," implying the
  BnB-4bit concurrency regression was addressed. It was closed `NOT_PLANNED` on
  2025-12-14 by the inactivity bot. Re-annotated as unaddressed — which
  *strengthens* the skill's AWQ-over-BnB recommendation. Also flagged #6801 as
  stale-bot-marked and likely to close for the same non-reason.
- **r04 re-stamped:** vLLM v0.21.0 → **v0.25.1** (2026-07-14). The "0.20+"
  floor stays valid; recorded that the v0.20.0 audit baseline behind
  `bench-numbers.md` is now five minors old.

**Not done (needs GPU time, not a probe):** re-running the benchmark set against
0.25, and re-checking the EAGLE3 / TRITON_ATTN / spec-config CLI surface across
0.21–0.25. Open items #1–#4 above all carry forward unchanged — each is blocked
on an author decision or an environment guard, none on evidence.

## Resolved this pass (2026-05-28)

- **Freshen — chat_template SHA DRIFTED (highest-value finding).** Re-pulled
  `google/gemma-4-31B-it/raw/main/chat_template.jinja` (curl, HTTP 200,
  17466 B) and recomputed the hash: it moved from `94899c0f…25bff413`
  (2026-04-30) to `36e3a42e…bead3f0` (2026-05-28). Google re-patches the
  `main` template, so the pinned SHA was stale. Updated SKILL.md fact #3 to
  record BOTH hashes and reframe it as a moving target ("re-pull and re-pin
  per deploy rather than trusting any historical SHA"); re-stamped sources.md
  r01 to 2026-05-28 with the new hash and a **DRIFTED** marker. This
  strengthens — not weakens — the skill's core staleness thesis (community
  quants ship a stale template). Dim 9 lifted.
- **Freshen — vLLM version landscape.** Re-confirmed via `gh release list
  vllm-project/vllm`: v0.21.0 now latest (2026-05-15), v0.20.2 (2026-05-10),
  v0.20.1 (2026-05-04), v0.20.0 audit baseline (2026-04-27). Re-stamped
  sources.md r04 to 2026-05-28 and rewrote the stale "latest is v0.20.0 /
  when v0.21 ships" Notes line. The "vLLM 0.20+" floor and 0.20.0 baseline
  remain valid — no body version bump warranted.
- **Improve — none kept.** Both improve-mode hypotheses were discarded (see
  below). The Dim 2/6 relocation of the "why-different" + "not-measured"
  sections to a new `references/analysis.md` was ATTEMPTED but the file Write
  was blocked by the subagent guard ("return findings as text, not write
  report files"). Rather than ship a dangling `references/analysis.md`
  pointer with the content lost, the relocation was fully reverted — both
  sections remain inline in SKILL.md (the "why-different" section did gain the
  one-line "plausible mechanisms, not measured attributions" framing as a
  net-neutral edit). SKILL.md stays at ~243 lines; Open item #3 (length) and
  Open item #2 (relocate the speculative section) remain OPEN.

**NOT re-stamped (honest gap):** r05/r06 line-pinned vLLM source paths were
not re-probed against v0.21.0 (line numbers drift); flagged in sources.md
Notes for a future freshen. They keep their 2026-04-30 dates.

**Score this pass (self):** 80/100 (up from 78). Dim 9 7→8 (SHA + version
re-stamp lifts the staleness picture; the SHA-drift catch is a real freshen
win). No improve-mode structural edit landed — two discards (Dim 1 trigger
surface: author mandate; PUSH-recipe collapse: user veto) plus the reverted
analysis.md relocation (blocked by environment guard).

## Resolved 2026-04-30

- Created `references/sources.md` with 10 verified upstream refs (HF
  models, vLLM source paths, GH issues / PRs) all stamped
  `Last verified: 2026-04-30`. Lifted Dim 9 from 6/10 (capped) to 9/10.
- Swept SKILL.md to imperative voice — removed `your`/`we`/`us`
  constructions at original lines 14, 126, 146, 150, 152, 200, 219.
  Lifted Dim 3 from 5-7/10 to 9/10 (blind).
- Removed personal-memory absolute path at original line 163
  (`~/.claude/projects/.../feedback_one_restart_means_fail.md`).
  Surrounding paragraph already explains the rule. Lifted Dim 8 to 9/10.
- Added `references/sources.md` pointer to SKILL.md References list so the
  new file is discoverable.

**Final score (2026-04-30):** self 84/100, blind 86/100. Up from baseline
self 78 / blind 79. Four kept iterations, zero discards.
