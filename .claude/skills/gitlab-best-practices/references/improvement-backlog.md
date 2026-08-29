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
