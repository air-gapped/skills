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

Improve: 2 keeps, 1 discard. Self 76 → 81; blind baseline **85**.

- iter 1 (keep, Dim 8): `references/values-porting.md` was cited in SKILL.md and
  `upgrade-campaign.md` in a shape that reads as a local path. The file belongs
  to the `helm` skill. Independently flagged by the baseline blind scorer as a
  top-three issue.
- iter 2 (keep, Dim 3): 13 second-person occurrences swept out of SKILL.md,
  meaning unchanged, file still 199 lines. The blind scorer's single
  highest-impact recommendation.

**Discard — iter 3: tables of contents for the three reference files over 200
lines.** Bare +1 on the self-score while adding ~27 lines, so the noise-zone
rule discards it; the blind scored Dim 2 **9 without** the TOCs, and SkillLens
measured format-only changes as non-significant. Do not re-propose a
formatting-only Dim 2 change against these files without new evidence that a
reader actually mis-navigates them.

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
