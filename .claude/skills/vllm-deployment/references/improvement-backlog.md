# Improvement backlog — vllm-deployment

Work-not-done log for the skill-improver loop. `## Open` lists issues attempted as
hypotheses that could not be applied (or safely verified) in a single iteration.
`## Resolved this pass` lists changes the metric actually registered.

## Open

- **Body still feature-list / pointer-map shaped, not operator-workflow ordered** (Dim 2) — `SKILL.md` (top third: lines ~16-98, the decision-guide table → load-bearing facts → pod shape → sibling boundaries → structure ordering). Hypothesis was to lead with the operator workflow (audit → cache mount → HF_TOKEN → probes → serve_args → autoscale) before the vendor-named decision table. Not applied: medium-complexity structural rewrite that must preserve every existing pointer, keep SKILL.md < 500 lines, and not disturb trigger-relevant keyword placement in the body — needs reliable read-back to cold-score honestly and confirm no pointer/frontmatter regression. (carried 2026-05-29)
- **probe-trigger.py all-zero measurement bug** (Dim 1) — skill-improver probe tooling, not a `vllm-deployment` file. Trigger precision cannot be measured/tuned for this skill until the harness probe returns non-zero scores. Not single-iteration-breakable inside this skill. (carried 2026-05-29)
- **Trigger eval-set mining** (Dim 1) — `references/trigger-evals.json` needs a larger, mined positive/negative query set before the description can be tuned against real false-positive/under-trigger data. Belongs to skill-improver's trigger mode, not a one-iteration content edit here. (carried 2026-05-29)
- **Cross-cluster / sibling-skill over-trigger batch** (Dim 1) — documented over-trigger steal vs sibling vLLM skills (e.g. "without restarting" vs spec-decode). Resolving it requires a batched trigger-measurement run across the whole vLLM skill family, not an isolated `vllm-deployment` edit. (carried 2026-05-29)

## Resolved this pass (2026-05-29)

- llm-d version bump v0.6.0 → v0.7.0 (2026-05-12) in `references/ecosystem.md`; sources.md row re-stamped. (Dim 9)
- NVIDIA Dynamo version bump v1.0.2 → v1.1.1 (2026-05-09) in `references/ecosystem.md`; sources.md row re-stamped. (Dim 9) — note: `references/disagg.md` carries no Dynamo version string, so no edit needed there (recon hypothesis assumed one that does not exist).
- Envoy AI Gateway version bump v0.5.0 → v0.6.0 (2026-05-05) in `references/ecosystem.md`; sources.md row re-stamped. (Dim 9)
- vLLM upstream v0.21.0 (2026-05-15) note added to `references/openshift.md` RHAIIS mapping (reinforces "pin the RHAIIS tag, roll forward with release notes"; RHAIIS↔upstream pin still flagged unverifiable); sources.md upstream row re-stamped. (Dim 9)
- Gateway-API-on-OpenShift version-gate table deduplicated: removed the verbatim copy from `references/routing.md`, replaced with a one-line pointer to `references/openshift.md`. (Dim 6)
- `references/sources.md` re-stamped all rows to 2026-05-29 (4 bumped via direct `gh api` release probes: llm-d, Dynamo, Envoy AI Gateway, vLLM; 4 re-confirmed current: LWS, AIBrix, GAIE, semantic-router); Classifications + freshen-pass header updated. (Dim 9 staleness ceiling refreshed)
