# Failure modes where the symptom does not identify the cause

**Tag convention.** Untagged claims were verified against a primary source or a
live install on 2026-08-29. **[A]** = reported but not independently
re-verified — re-check before acting.

## Table of contents
- [Research an upstream bug with `glab`, not a scraper](#research-an-upstream-bug-with-glab-not-a-scraper)
- [Pre-flight SQL](#pre-flight-sql)
- [Stuck background migrations are two different bugs](#stuck-background-migrations-are-two-different-bugs)
- [Sidekiq](#sidekiq)
- [Others worth recognising](#others-worth-recognising)

## Research an upstream bug with `glab`, not a scraper

GitLab's own issues live on gitlab.com, and `glab` is to GitLab what `gh` is to
GitHub. This changes answers, it is not a style preference.

Measured: a research pass using web fetch and search concluded an issue had **no
backport** and was therefore unfixed in the 18.x line — it received `401` on the
notes endpoint and the comments are JS-rendered. An authenticated
`glab api .../related_merge_requests` returned three backport MRs immediately
and proved the opposite: the fix *was* in the target version. Acting on the
scraped answer would have meant cancelling a safe upgrade or building an
elaborate workaround for a bug that could not occur.

```bash
glab issue view <iid> --repo gitlab-org/gitlab
glab api projects/gitlab-org%2Fgitlab/issues/<iid>/notes --paginate
glab api projects/gitlab-org%2Fgitlab/issues/<iid>/related_merge_requests
```

**An issue's milestone tells you when it was fixed on master, not whether the
fix reached the version you are going to.** Only the backport MRs and their
`target_branch` answer that. A milestone of 19.0 does not mean 18.11 is unfixed.

Reading public repos is fine. Never post, comment or open anything upstream.

## Pre-flight SQL

Three landmines, all checkable in seconds, all cheaper to check than to hit.
Run against the GitLab database as superuser before every 18.x hop.

```sql
-- #597558: 18.10 -> 18.11 migration fails if this index was previously dropped
SELECT indexname FROM pg_indexes
 WHERE indexname='index_deployments_on_id_and_status_and_created_at';

-- award_emoji CheckViolation variant of the single-record BBM bug (check_8ef14b7067)
SELECT count(*) FROM award_emoji
 WHERE namespace_id IS NULL AND organization_id IS NULL;

-- anything not finished(3) / finalized(6)
SELECT job_class_name, table_name, status
  FROM batched_background_migrations WHERE status NOT IN (3,6);
```

## Stuck background migrations are two different bugs

Two structurally different faults produce the identical "stuck migration"
report. **Read the actual error class before applying any fix** — the symptom
cannot diagnose this.

| Fault | Presents as |
|---|---|
| A later schema migration dropped the table an earlier backfill depends on | `PG::UndefinedTable` |
| The Sidekiq dedup race (below) | **no SQL error at all** — just repeated `deduplicated: dropped` log lines |

### The `label_links_archived` trap — a worked example of reading a bug properly

Headline migration hazard for 18.8 → 18.11:

| milestone | what happened |
|---|---|
| 18.5 | `BackfillShardingKeyAndCleanLabelLinksTable` queued; needs `label_links_archived` |
| 18.6 | a *separate* single-record bug marked it **finished without running** |
| 18.10 | `ExecuteBatchedBackgroundMigrationsAffectedBySingleRecordBug` tries to finalize it → the archive table was dropped in between → `PG::UndefinedTable` |

The issue carries **milestone 19.0**, which reads as "not fixed in 18.x". It is
fixed in 18.x — backports went to `18-11-stable-ee`, `18-10-stable-ee` and
`18-9-stable-ee`, so any 18.11.1+ carries it.

Two lessons generalise:

1. **Check the backports, not the milestone.**
2. **Being in the latent shape is not the same as being broken.** The exposed
   state is `label_links_archived` absent *and* the migration sitting at status
   6. That describes a healthy-looking instance where every status check reports
   finished — which is exactly why it surprises people mid-upgrade.

These finalize hazards were **18.x-scoped** and did not recur crossing into
19.2, which queued 9 fresh background migrations, all active, none paused, none
failed.

## Sidekiq

### The one that silently does nothing

**Issue #388094 — deduplication race during a rolling upgrade.** With **multiple
Sidekiq replicas**, an *old*-version pod can pick up a
`Database::BatchedBackgroundMigrationWorker` job before it terminates, crash
with `NameError: uninitialized constant`, and leave an orphaned deduplication
key in Redis. New pods then log `deduplicated: dropped until executing` forever
and **background migrations never run — while the install looks completely
green.** **[A]**

Mitigations, in order of preference: scale Sidekiq to 0 before upgrading and
back up after; or run a **single Sidekiq replica**; or clear the `DuplicateJob`
idempotency key from Rails console afterwards.

This is a strong argument against elastic Sidekiq autoscaling on a small
instance — and a single replica removes the race for a whole multi-hop campaign.

### The HPA flaps by construction on a small install

The stock HPA CPU target is `350m` while the pod's own CPU request is `900m` —
it scales out at **39% of its own reservation**. Measured: 50 rescales in 21
days, 13 in one 48-hour window, with peak CPU (277m) never approaching the
request.

The damage is not the churn. Each scale-down deleted the newest pod with
`terminationGracePeriodSeconds: 30` against `SIDEKIQ_TIMEOUT: 25`, **SIGKILLing
any job running longer than 25s.**

Fix: pin `maxReplicas: 1`, and raise the drain — `timeout: 110` with grace
`120`. **Grace must exceed timeout or the kernel truncates the drain.** Add a
memory limit as a kernel backstop above the in-process memory killer (a `3Gi`
limit against `maxRss 2000000` KB ≈ 1953Mi).

Proof the drain fix works: after a later scale-to-zero maintenance, the dead set
held **zero jobs dead in the previous 6 hours**. Under the stock 30s/25s pairing
anything mid-flight would have been SIGKILLed into it. **Do the drain fix
before any maintenance that scales Sidekiq down, not after.**

### `GITLAB_SIDEKIQ_MAX_REPLICAS` — a fix that becomes an input

From 18.9 the chart sets this env var in the Sidekiq pod, derived from
`maxReplicas`. On installs without KEDA it activates the concurrency limiter
unexpectedly — job backlogs, Redis memory growth, delayed webhook and audit
workers. Buggy in 18.9.0–18.9.5 and 18.10.0–18.10.3; fixed in 18.9.6 / 18.10.4.

**The interaction worth noticing:** pinning `maxReplicas: 1` to stop HPA
flapping also feeds `1` — the smallest possible value — into this limiter.
Landing past 18.10.4 means the *bug* is gone but the feature is live at its
lowest setting. **Check queue depth after the hop rather than assuming.**

The chart wraps the env in `checkDuplicateKeyFromEnv`, so setting
`GITLAB_SIDEKIQ_MAX_REPLICAS` via `gitlab.sidekiq.extraEnv` suppresses the
chart's own copy instead of conflicting with it — a clean override path.

### Stale schema cache

Errors like `Unknown primary key for table ci_runners` *after* migrations report
complete (issue #241672). Fixed only by restarting Sidekiq pods. **[A]**

## Others worth recognising

| Symptom | Cause |
|---|---|
| `BackfillSentNotificationsAfterPartition` fails on upgrade to 18.2.8 with `PG::CheckViolation: no partition of relation ... found for row` | known; GitLab published KB #27529828806812 as the fix **[A]** |
| `RenameWebHookLogsSequence` fails with `PG::ObjectNotInPrerequisiteState: sequence must have same owner as table it is linked to` | external/operator-managed PG where ownership is not what GitLab assumes; thread unresolved **[A]** |
| Explicit KAS/agentk registration error | KAS↔agentk compatibility is **major.minor** — mismatch fails loudly, not silently **[A]** |
| `gitlab-migrations-*` Job fails to start under Argo CD | charts issue #3021 — GitOps hook-ordering interaction, distinct from any SQL failure **[A]** |
