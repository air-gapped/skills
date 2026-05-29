# gpu-host-tuning — improvement backlog

Carries findings across `/skill-improver` runs. Open = work the loop
attempted but couldn't apply atomically; Resolved = mutations the loop
made and the metric registered.

## Open

### 1. Supermicro / HPE chassis references missing (Dim 5 — Completeness)
- **Where:** `SKILL.md` description names "Dell/Supermicro/HPE BIOS guidance",
  but only `dell-xe9680.md` and `dell-xe9780.md` are stocked. Supermicro and
  HPE are mentioned briefly in `tuned-profiles.md` (5-line stubs) and
  `recommended-tunings.md:473-475`, no chassis-specific reference files.
- **Why not auto-applied:** authoring chassis-specific BIOS guidance for
  Supermicro AS-8125GS / SYS-821GE-TNHR and HPE Apollo 6500 ML270 / ProLiant
  XL645d requires real BIOS-menu names + slot-map + DDR5 expectations the
  author has access to and the loop does not. Two paths: (a) add `smc-*.md`
  + `hpe-*.md` companion files (author content needed), or (b) trim
  description to "Dell BIOS guidance" only (deletion-friendly per the
  Karpathy "remove for equal results" rule).
- **Recommendation:** option (b) is faster and honest about current
  coverage; option (a) increases value but requires SMC/HPE chassis
  expertise.

### 2. `bringup-recipe.md` procedural depth — Boris-alignment candidate (Dim 6)
- **Where:** `references/bringup-recipe.md`, 322 lines of numbered Phase 0-7
  procedural steps.
- **Why not auto-applied:** placement in `references/` (not SKILL.md body)
  keeps the Boris "strict workflow scaffolding" cap from triggering — but
  the file is dense procedural prescription that plan mode could discover
  much of. Compressing requires author judgment about which steps are
  "must-do" (e.g. dcgmi diag levels, Phase 7 tear-up checklist) vs which
  Claude could derive (most of Phase 4 stability testing).
- **Recommendation:** target compression in a future pass after measuring
  whether the full recipe is referenced often enough to justify its
  length, or split into `bringup-recipe-checklist.md` (the Phase 7
  one-page version) + a longer narrative.

### 3. Quick-start `--bench` torch availability caveat (Dim 4 — Actionability)
- **Where:** `SKILL.md:43` — `# Audit + pinned-memcpy bench (needs torch + CUDA, ~5 min)`
- **Why not auto-applied:** the comment says "needs torch + CUDA" but
  doesn't note the common reality that torch lives inside the vLLM
  container, not on the host. `scripts/collect.sh` already handles graceful
  fallback (its bench section probes for torch and skips if absent), but
  the SKILL.md comment could surface the "run inside vllm container"
  caveat one level up. Atomic enough but cosmetic — bumped to backlog
  for reviewer attention.
- **Recommendation:** one-line addition to SKILL.md Quick start:
  `# (run inside the vllm container if host torch is unavailable)`

### 4. Remaining 2nd-person prose slips in 5 reference files (Dim 3)
- **Where:** dell-xe9680.md (~6 slips), dell-xe9780.md (~4 slips),
  virt-and-cloud-quirks.md (1 slip), session-findings.md (1 slip),
  tuned-profiles.md (3 slips). Worst offenders (recommended-tunings.md and
  probe-interpretation.md) were cleaned in iters 6-7.
- **Why not auto-applied:** Dim 3 lift saturated at +1 per file; remaining
  slips are scattered across BIOS-table and operator-instruction prose
  where conversion to imperative occasionally clashes with shell-comment
  conventions ("# adjust to your HCAs") that are idiomatic. Diminishing
  returns within 10-iteration cap.
- **Recommendation:** one targeted pass per file (5 minor iterations),
  preserving shell-comment "your" usage.

## Resolved this pass

Run: 2026-05-28 — 1 keep (currency precision), 1 freshen stamp. Self 85 → 86/100.

- **Iter 1 (KEEP, Dim 5/9):** `probe-interpretation.md:87` — refined the
  `amd_pstate.status = active or guided (kernel 6.3+)` parenthetical. The old
  wording attached `6.3+` to `active`, implying active/EPP needs 6.3, which is
  wrong: the base `amd_pstate` driver shipped in 5.17, `active` (EPP) landed in
  6.1, `guided` and default-on arrived in 6.3. New text states each milestone
  precisely. (`recommended-tunings.md:71` says "guided EPP mode (kernel 6.3+)"
  which is correct — left unchanged.)
- **Freshen (sources.md:17):** re-confirmed `github.com/NVIDIA/nvbandwidth` is
  the NVIDIA-recommended bandwidth tool today; stamped Last verified 2026-05-28
  and added the cuda-samples `bandwidthTest` removal (v13.0) context to Notes.

### Recon/layout mismatch note (2026-05-28)

The RECON for this pass was generated against an imagined reference-file layout
(`verification-and-benchmarks.md`, `cpu-governor-and-pstate.md`,
`nccl-and-fabric.md`) that does NOT exist in this skill. Its headline
hypotheses were already satisfied by the real files and required no action:
- "swap bandwidthTest → nvbandwidth": already done — the skill uses
  `nvbandwidth` everywhere (`bringup-recipe.md:116-128`, `collect.sh:461-468`,
  `sources.md:17`); no `bandwidthTest`/`cuda-samples`/`demo_suite` reference
  exists anywhere in the skill.
- "fix amd_pstate=active >=5.17 gate": the skill never claimed `>=5.17`; it said
  `(kernel 6.3+)`. Addressed precisely in Iter 1 above.
- "add nvbandwidth source row" / "add 8xH100 busbw citation": both already
  present (`sources.md:17`; `bringup-recipe.md:143` cites Cisco/NVIDIA MLPerf
  for ~480 GB/s on H200 8×, `:130` cites Together.ai for H100 ~389 GB/s).
Future passes: ground hypotheses against the actual `references/` listing, not
the recon's assumed filenames.

---

Run: 2026-05-04 — 9 keeps, 1 discard, score 74 → 85/100 (self), 80 → 96/100 (blind).

- **Iter 1:** Split `description` (1079 chars, **violated 1024-char Agent
  Skills hard cap** — `skills-ref validate` would reject) into compliant
  `description` (548c) + `when_to_use` (535c). Cleared the Dim 9 hard-fail
  cap (3) and lifted Dim 1 listing scannability.
- **Iter 2:** Created `references/sources.md` with 17 dated entries,
  probing 8 URLs live (3 GitHub repos, NVIDIA DGX TuneD docs, SLES TuneD
  docs, Dell XE9780L product page, StorageReview, Dell XE9780 PDF) and
  marking 4 anti-bot-walled URLs as live-but-unverifiable. Lifted Dim 9
  staleness cap (was 6 from absence) to no cap (oldest 2026-05-04).
- **Iter 3-4:** Replaced `/tmp/gpu-host-tuning/scripts/collect.sh` and
  `./collect.sh` paths with `./scripts/collect.sh` in `bringup-recipe.md`.
  Resolved Quick-start vs bringup-recipe path inconsistency.
- **Iter 5:** Replaced 2nd-person table header `| You want to | Read |`
  with `| Goal | Read |` in SKILL.md (only 2nd-person slip in SKILL.md
  body).
- **Iter 6:** 6 prose 2nd-person → imperative conversions in
  `recommended-tunings.md` (worst offender, 11 hits → 5 acceptable
  shell-comment slips remaining).
- **Iter 7:** 4 prose 2nd-person → imperative conversions in
  `probe-interpretation.md`.
- **Iter 8:** Quick-start install-location agnostic — replaced absolute
  path `cd ~/.claude/skills/gpu-host-tuning` with comment naming both
  personal and project-install paths.
- **Iter 9:** Added 14-line section TOC to top of `recommended-tunings.md`
  (576 lines). Lifted Dim 2 partial-read previews.
- **Iter 10 (DISCARD):** Tried removing the "Three modes: Audit / Bench /
  Tune" preamble in SKILL.md as redundant with the later table.
  Discarded — the preamble is glance-level orientation that the table
  doesn't substitute (table maps modes to scripts; preamble defines what
  the modes ARE). Score stayed at 85; cold rescore confirmed Dim 6 didn't
  lift +1 and Dim 4 risked a fraction-point drop. Ceiling evidence:
  pure-deletion simplicity moves no longer pay back at this score level.
