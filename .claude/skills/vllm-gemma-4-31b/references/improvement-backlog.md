# Improvement backlog — vllm-gemma-4-31b

Carries findings across `/skill-improver` runs. Skill-improver reads this in
Phase 0 and updates it in Phase 6. Open holds only items blocked on something
absent; a resolved item is deleted from Open and recorded under its pass.

## Open

### Measured H200 141GB recipe (Dim 5 — added 2026-10-18)

**Pointer:** `SKILL.md` § "H200 141GB — start point, not a measured recipe".

**Finding:** fact #2 states the H200 knee (~128) but no H200 run backs a
copy-paste recipe; the section gives a start point and the sweep that finds
the knee and the util cliff.

**Blocked on:** an H200 141GB measurement run (knee sweep plus util-cliff
search). No H200 is reachable (re-checked 2026-11-09); renting one is a spend
decision. With the run, replace the start point with a LIGHT/PUSH-style
recipe and add its rows to `bench-numbers.md`.

### Re-measure LIGHT / PUSH on a current engine (Dim 9 — added 2026-11-09)

**Pointer:** `references/bench-numbers.md`; `SKILL.md` recipes, decision guide
and the 0.94 util cliff.

**Finding:** every figure is a v0.20.0 observation on the all-Triton path.
From v0.31.0, H100 with `--kv-cache-dtype fp8` runs per-layer FA3/FA4 (fact
#1); from v0.32.0 the WNA16 kernel on SM90 is Humming; from v0.29.0 MRv2
reserves CUDA-graph memory, which moves the util cliff.

**Blocked on:** a 2× H100 80GB run of the `bench-numbers.md` phases on
v0.33.0 or newer. No H100 is reachable (checked 2026-11-09); renting is a
spend decision. With the run, replace the tables and re-derive the TP
decision guide and the util cliff.

## Decided — do not re-propose

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

### 3. PUSH recipe duplicates ~90% of LIGHT flags (Dim 6/2 — user-vetoed 2026-05-28)

**Pointer:** `SKILL.md` PUSH recipe code block

**Finding:** RECON proposed collapsing the PUSH recipe to a 5-flag diff
against LIGHT to save ~12 lines toward the 150-line target.

**Why it was NOT applied:** the user prioritises copy-paste-ability of BOTH
full recipes over the line savings. This is a settled author-preference
decision, not a pending task. Do NOT re-propose the collapse in `improve` mode.

**2026-10-18:** the blind scorer re-proposed adding user phrasings (OOM at
startup, `<turn|>` leak, `tool_choice` ignored, AWQ chat template, EAGLE3
acceptance) to the trigger text. Not applied — same author mandate. Use
`trigger` mode to measure misses.

### 4. No version ceiling (operator decision 2026-10-18)

**Pointer:** `SKILL.md` "Version floor" callout

**Decision:** the skill states a floor (0.29.0+, the #49955 fix) and no upper
bound. Do NOT introduce a "hold at" or "do not take" version from an open
upstream issue. A source-confirmed breakage on a specific release is written
as a known failure: symptom, affected versions, fix or mitigation.

## Resolved this pass (2026-10-18, improve)

Blind baseline 63 (snapshot of 68dca10); self 63 → 71 over 5 kept iterations,
72 after post-cap fixes; final blind score and A/B comparator are run by the
operator. Stop: cap reached (5), zero discards — no ceiling mapped.
- Kept: chat-template drift detail moved to `references/chat-template-drift.md`
  (fact #3 now an 11-line directive with re-vet procedure in the reference).
- Kept: `<turn|>` leak pitfall condensed to status table, mechanism, test.
- Kept: unreachable external memo paths, reproduction-artifacts tree and
  site-specific hardware/tool names removed (SKILL.md, bench-numbers.md) —
  closes former Open #4.
- Kept: unmeasured gemma-3-vs-gemma-4 mechanisms and bench questions moved to
  `references/open-questions.md` — closes former Open #2.
- Kept: second-person phrasing converted to imperative.
- Post-cap: parser section decision-first; H200 start point with a
  v0.32.0-checked sweep command; contents lists on references over 100 lines.
  SKILL.md 503 → 385 lines.
