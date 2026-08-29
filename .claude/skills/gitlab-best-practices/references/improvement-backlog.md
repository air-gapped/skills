# Improvement backlog — gitlab-best-practices

Carries ceiling findings across skill-improver runs. Append-only history.

## Open

- **`backup-utility`'s `db` component against operator-managed PostgreSQL is
  unresolved** (Dim 5, completeness). No source found states whether it
  succeeds, fails, or silently skips when PostgreSQL is external and managed by
  an operator, and therefore whether `--skip db` is required, harmless, or
  wrong. The chart docs are silent; searching produced nothing either way.
  **Absent thing:** a restore rehearsal on a live install with a maintenance
  window — the question is only answerable empirically, and the answer changes
  what a backup runbook says. Recorded in `references/backup-restore.md` as an
  open question rather than guessed at.

- **No trigger-mode measurement** (Dim 1, empirical). The `description` and
  `when_to_use` were written by hand and sized with
  `frontmatter-lengths.py` (655 / 808, combined 1,463 of 1,536) but never
  measured for fire/silence behaviour. **Absent thing:** a
  `/skill-improver trigger gitlab-best-practices` run. The trigger space
  overlaps `helm` (values porting, chart bumps), `k8s-components-checker`
  (version verdicts) and `postgres-operator-best-practices` (the mandatory PG 17
  move), so the run must test both directions of confusion, not just this
  skill's own recall.

## Resolved this pass — 2026-08-29 (freshen + improve)

Freshen: 24 upstream issue states probed via `glab api`. Five citations were
stale; the state table now lives in `sources.md` so the next pass diffs rather
than re-derives.

- **`gitlab#388094` reads `closed` but was never fixed.** Closed 2023-09-18 on a
  triage ping — *"Thanks for the reminder. I will close this issue"* — with the
  last substantive comment placing the safe ordering in the **Operator** and
  leaving the chart case open. The skill presented it as a live hazard, which is
  right, but anyone re-checking the issue would have dropped the mitigation.
  Now states that the issue is closed and the hazard is not, with the closing
  quote and a general rule: housekeeping closes and fix closes are
  indistinguishable in the state field.
- `charts#1444`, `charts#3021`, `runner#4509` corrected from open to closed;
  `charts#3338` corrected and its 404 crash located in the body, not the title.

Improve: 4 keeps, 1 discard (later re-proposed on a changed basis and kept).
Self 76 → 81; blind **85 → 86 → 86**, with **Dim 3 confirmed 7 → 9** on the
last run. The A/B comparator returned **IMPROVED 3–0**, high confidence, no
regressions found by any of the three. The absolute delta sits inside the
instrument's own 2–4 point spread and is *not* the verdict; the comparator is.

One caveat on that verdict: one comparator disclosed that the session's
`gitStatus` block named the very transformation under test. Excluding its vote
entirely still leaves **2–0 for the final**, and the other two identified the
same two changes from the diff alone.

- iter 1 (keep, Dim 8): `references/values-porting.md` was cited in SKILL.md and
  `upgrade-campaign.md` in a shape that reads as a local path. The file belongs
  to the `helm` skill. Independently flagged by the baseline blind scorer as a
  top-three issue.
- iter 2 (keep, Dim 3): 13 second-person occurrences swept out of SKILL.md,
  meaning unchanged, file still 199 lines. The blind scorer's single
  highest-impact recommendation.

- iter 4 (keep, Dim 3): the iteration-2 sweep covered SKILL.md only, so the
  final blind still scored Dim 3 at 7 and named `duo-ai.md` as the concentrated
  source. 22 further prose occurrences rewritten across seven reference files.
  **Quoted upstream text was left alone** — ten occurrences remain inside
  blockquotes, inline citations, or a URL placeholder from GitLab's own docs;
  editing a quotation to satisfy a register rule would misquote the source.

**Discard — iter 3: tables of contents, on Dim 2 formatting grounds.** Bare +1
on the self-score while adding ~27 lines, so the noise-zone rule discarded it.
The stated rationale was that the first blind scored Dim 2 **9 without** the
TOCs and SkillLens measured format-only changes as non-significant.

- **iter 5 (keep, Dim 8): re-proposed on a changed basis, and the discard's
  own evidence turned out to be scorer-specific.** The second blind scored
  Dim 2 **8**, named the missing TOCs its **#1 recommendation**, and framed it
  as an **internal inconsistency** rather than formatting — 3 of 8 reference
  files carried a TOC and the rest did not. That is a different dimension from
  the one iteration 3 was rejected under. All six reference files over 100
  lines now carry one; `air-gap.md` (97) and this backlog (96) stay under the
  threshold.
  **Standing caution:** two blind scorers disagreed 9 vs 8 on this exact
  question, so the metric never resolved it — the tie was broken on internal
  consistency, not on a score movement. Do not re-litigate it from a score
  alone in either direction.

**Ceiling not mapped.** One discard in one category is short of the 5-across-2
the ceiling claim requires, so the remaining improvement space is unmeasured
rather than known-empty. This pass stopped early, not finished.

## Resolved during authoring — 2026-08-29

Not a scored improve pass; recorded because each item corrects a claim that
would otherwise have shipped wrong.

- **charts#3813 (gitlab-exporter ignores Sentinel) was carried as open.** It is
  **closed at milestone 17.1**, with #5376 alongside it. Rewritten from a live
  limitation into a smoke-test note.
- **Default replica counts were assumed to be 1 across the board.** Read from
  the unpacked chart at 10.3.1: webservice, kas, gitlab-shell and registry all
  default to `minReplicas: 2`; **sidekiq defaults to 1**. The assumption was
  backwards, and the sidekiq value is the one that matters — it is already the
  setting that avoids the dedup race.
- **The Duo serving-platforms page was recorded as 403/unfetchable.** The page
  had **moved**; the `gitlab_duo_self_hosted/` path returns 200. This upgraded
  the vLLM pin (v0.18.1+), the LiteLLM provider layer, the validated provider
  list, the `/v1` URL suffix and the `custom_openai/<id>` identifier format from
  reported to verified.
- **"GitLab walked back an HA promise and staff objected" could not be
  substantiated.** Recorded as unsupported in `references/sources.md`, with the
  documented-and-citable finding (a stalled epic reporting "No progress" at ~5
  contributor hours/week) written in its place.
