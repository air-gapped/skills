# Improvement backlog — vllm-deployment

Work-not-done log for the skill-improver loop. `## Open` lists issues attempted as
hypotheses that could not be applied (or safely verified) in a single iteration.
`## Resolved this pass` lists changes the metric actually registered.

## Open

- **(new 2026-07-18) URGENT: freshen by 2026-07-24** (Dim 9) — the two
  2026-04-24 rows in `references/sources.md` (production-stack,
  multi-node-serving.sh) cross the 91-day staleness band on 2026-07-24,
  capping Dim 9 at 7. Both blind agents flagged it. vLLM upstream has also
  moved past the stamped v0.21.0 (local clone at 2026-07-12). Run
  `freshen vllm-deployment`; verify online, downgrade nothing from memory.

- **(new 2026-07-18) ToCs for >100-line references** (Dim 2/7) —
  pod-shape.md (292 lines), docker-lab.md (248), and the other five
  100+-line reference files lack the official-best-practice table of
  contents (partial-read navigation). Planned as an iteration this run;
  displaced by the blind-flag Dim 5 work and the 90+ stop condition fired
  first. Single Pattern-8.2-style cross-file iteration next run.

- **(new 2026-07-18) OCP Route 60s timeout taught in three places** (Dim 6)
  — SKILL.md pitfall 6, routing.md §OpenShift Route, openshift.md §Routes.
  Final-blind finding. Candidate: keep the pitfall one-liner + one canonical
  treatment, pointer from the other. Not attempted (stop condition reached).

- **(new 2026-07-18) ecosystem.md verification-label drift** (Dim 8) —
  mixed "Apr 2026"/"May 2026" verified-as-of labels within one file.
  Final-blind finding; fold into the next freshen pass's re-stamp.

- **Body still feature-list / pointer-map shaped, not operator-workflow ordered** (Dim 2) — `SKILL.md` (top third: lines ~16-98, the decision-guide table → load-bearing facts → pod shape → sibling boundaries → structure ordering). Hypothesis was to lead with the operator workflow (audit → cache mount → HF_TOKEN → probes → serve_args → autoscale) before the vendor-named decision table. Not applied: medium-complexity structural rewrite that must preserve every existing pointer, keep SKILL.md < 500 lines, and not disturb trigger-relevant keyword placement in the body — needs reliable read-back to cold-score honestly and confirm no pointer/frontmatter regression. (carried 2026-05-29)
- **probe-trigger.py all-zero measurement bug** (Dim 1) — skill-improver probe tooling, not a `vllm-deployment` file. Trigger precision cannot be measured/tuned for this skill until the harness probe returns non-zero scores. Not single-iteration-breakable inside this skill. (carried 2026-05-29)
- **Trigger eval-set mining** (Dim 1) — `references/trigger-evals.json` needs a larger, mined positive/negative query set before the description can be tuned against real false-positive/under-trigger data. Belongs to skill-improver's trigger mode, not a one-iteration content edit here. (carried 2026-05-29)
- **Cross-cluster / sibling-skill over-trigger batch** (Dim 1) — documented over-trigger steal vs sibling vLLM skills (e.g. "without restarting" vs spec-decode). Resolving it requires a batched trigger-measurement run across the whole vLLM skill family, not an isolated `vllm-deployment` edit. (carried 2026-05-29)

## Resolved this pass (2026-07-18 — improve run, post-SkillLens rubric)

Baseline self 89 → **83 corrected** after grep-verifying the baseline blind's
Dim 5 flag (self-score had missed that four description-promised topics had
zero body coverage — the SkillLens fluency trap in miniature) / baseline
blind **83** → final self **90** (stop condition: 90+ with no dim <7) /
final blind **87**. 7 keeps, 0 discards, 7 iterations. Neither Boris nor
SkillLens caps fired at baseline or final — mechanism+remedy density and
blacklists confirmed by both blind agents.

- **iter 1 (keep, simplification):** SKILL.md 163→148 lines — deleted the
  ad-hoc smoke-command block (covered by deployment-smoke.sh) and the
  commented NCCL env dupes (in pod-shape template). Dim 2 8→9.
- **iters 2–4 (keep ×3, noise-confirmed):** landed the four
  description-promised topics that had no body coverage — compile-cache
  survival (`VLLM_CACHE_ROOT`; vLLM redirects TORCHINDUCTOR/TRITON cache
  dirs itself, verified at `vllm/compilation/compiler_interface.py:477-480`),
  serve-args review (`--enforce-eager` trade-off, MoE
  `--enable-expert-parallel` / ep2-dp2 layout-vs-GPU-count check), and the
  parser-plugin ConfigMap mount (`--tool-parser-plugin`,
  `cli_args.py:115`) — all in pod-shape.md with SKILL.md pointers extended
  in-line. All flag/env claims probed against the local vLLM clone
  (752a3a5044, 2026-07-12). Dim 5 6→9.
- **iter 5 (keep, noise-confirmed):** deployment-smoke.sh check 6 dead code
  fixed — TP is a CLI arg, invisible to `printenv`; now parsed from the pod
  spec args with a GPU-limit fallback; both arg formats tested, shellcheck
  clean. Dim 7 8→9. (Baseline-blind finding.)
- **iter 6 (keep, noise-confirmed):** sources.md prose note contradicted its
  own table (llm-d "v0.6.0 latest" vs verified v0.7.0 row). Dim 8.
- **iter 7 (keep, noise-confirmed):** pitfall 2 reconciled with pod-shape's
  startupProbe recommendation ("fixed at 600 s" → both options named).
  Dim 8 → 10.

## Resolved this pass (2026-05-29)

- llm-d version bump v0.6.0 → v0.7.0 (2026-05-12) in `references/ecosystem.md`; sources.md row re-stamped. (Dim 9)
- NVIDIA Dynamo version bump v1.0.2 → v1.1.1 (2026-05-09) in `references/ecosystem.md`; sources.md row re-stamped. (Dim 9) — note: `references/disagg.md` carries no Dynamo version string, so no edit needed there (recon hypothesis assumed one that does not exist).
- Envoy AI Gateway version bump v0.5.0 → v0.6.0 (2026-05-05) in `references/ecosystem.md`; sources.md row re-stamped. (Dim 9)
- vLLM upstream v0.21.0 (2026-05-15) note added to `references/openshift.md` RHAIIS mapping (reinforces "pin the RHAIIS tag, roll forward with release notes"; RHAIIS↔upstream pin still flagged unverifiable); sources.md upstream row re-stamped. (Dim 9)
- Gateway-API-on-OpenShift version-gate table deduplicated: removed the verbatim copy from `references/routing.md`, replaced with a one-line pointer to `references/openshift.md`. (Dim 6)
- `references/sources.md` re-stamped all rows to 2026-05-29 (4 bumped via direct `gh api` release probes: llm-d, Dynamo, Envoy AI Gateway, vLLM; 4 re-confirmed current: LWS, AIBrix, GAIE, semantic-router); Classifications + freshen-pass header updated. (Dim 9 staleness ceiling refreshed)
