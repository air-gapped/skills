# Rollout mechanics, aborting, and rollback

What physically happens during `helm upgrade`, how to stop it safely, and what is genuinely irreversible.

## Contents
1. [How the rollout-operator sequences a roll](#1-how-the-rollout-operator-sequences-a-roll)
2. [The `kubectl rollout restart` story, corrected](#2-the-kubectl-rollout-restart-story-corrected)
3. [Don't POST prepare-shutdown before a version bump](#3-dont-post-prepare-shutdown-before-a-version-bump)
4. [Ordered rollout sequence for one hop](#4-ordered-rollout-sequence-for-one-hop)
5. [Abort levers](#5-abort-levers)
6. [Rollback matrix](#6-rollback-matrix)

## 1. How the rollout-operator sequences a roll

The operator acts only on StatefulSets carrying a `rollout-group` label whose `updateStrategy.type` is
`OnDelete`, and it guarantees that pods in two different StatefulSets of a group never roll simultaneously —
a zone rolls only when every pod in every sibling zone is Ready. [UG]

Details that matter in practice: [UG][RFC]

- **The chart only sets `OnDelete` when zone-awareness is on.** Single-zone ingesters/store-gateways get plain
  `RollingUpdate` and the operator refuses the group entirely. Ingester and store-gateway ship
  `zoneAwareReplication.enabled: true` by default, so multi-zone is the normal posture.
- **Zone order is deterministic by sorted StatefulSet name** (zone-a, zone-b, zone-c), with one override: a
  StatefulSet that already has not-Ready pods is moved to the front. If **two or more** have not-Ready pods, the
  operator refuses to act at all and logs *"StatefulSets have some not-Ready pods, skipping reconcile"*. That is
  the safety net, not a bug.
- **In-zone parallelism is `rollout-max-unavailable`, which the chart sets to 50** for both components — i.e.
  effectively "roll the whole zone at once", matching Mimir's own guidance that with zone-aware replication you
  may roll a whole zone together.
- **The operator deletes pods via the Pods API, not the Eviction API** — so PodDisruptionBudgets do not constrain
  it. The chart's PDB is also zone-blind (one PDB covering all zones), so it governs node drains only.
- **`min-time-between-zones-downscale` is about scaling, not rolling.** It is consumed by the prepare-downscale
  webhook on replica *decreases* and has no effect on an image bump.
- Reconcile interval default is **5 seconds** (the runbook's "every 5m" is the informer resync ceiling). [UG]

## 2. The `kubectl rollout restart` story, corrected

The widespread warning — *"never `kubectl rollout restart` an ingester StatefulSet, it causes hash-ring
split-brain"* — does not survive checking, and this skill previously repeated it. Correcting it matters because
a rule nobody can source is a rule people quietly break, taking the real constraints with it.

- **No upstream document prohibits it.** Not in `docs/sources/mimir/**`, not in the runbooks, not in the
  rollout-operator README. [UG]
- **The "it errors on OnDelete" variant is false.** kubectl's `objectrestarter.go` has no `OnDelete` guard — it
  only stamps `kubectl.kubernetes.io/restartedAt` on the pod template. On zone-aware StatefulSets it deletes
  nothing; the operator then rolls that zone through its normal gated path. [UG]
- **The resharding mechanism is real but the chart defuses it.** Mimir's own default is
  `-ingester.ring.unregister-on-shutdown=true`, but the chart pins `unregister_on_shutdown: false` plus
  `tokens_file_path: /data/tokens` for **both** ingester and store-gateway in every version in scope. Upstream
  states the reason: *"Rolling restarts of ingesters are now less likely to cause spikes in resource usage."*
  [UG] If anyone overrides `unregister_on_shutdown: true`, the folklore becomes true again — check before
  assuming.

**So what is actually true:**

- The real cost of `rollout restart` on a zone-aware STS is **manifest drift** from the Helm-rendered state, and
  that it rolls only the zone you named. Both are reasons to prefer driving rolls through Helm, but neither is
  data loss.
- **The genuinely dangerous configuration is single-zone**: the chart emits `RollingUpdate`, the operator refuses
  the group, `podManagementPolicy: Parallel` (the ingester default) removes ordering, and PDBs don't gate
  controller-driven deletion. [RFC]
- **The real limit is capacity, not tokens.** [UG] With RF=3, *"Grafana Mimir tolerates up to one unavailable
  ingester. To ensure no query fails during a rolling update, roll out changes to one ingester at a time"* — and
  *"If you enabled zone-aware replication for ingesters, you can roll out changes to all ingesters in one zone at
  the same time."*

## 3. Don't POST prepare-shutdown before a version bump

`/ingester/prepare-shutdown` makes the ingester unregister from the ring and flush in-memory series on the next
SIGTERM — *even if* `unregister-on-shutdown` is disabled. [UG] That is the **scale-down** path.

A version bump changes `spec.template` with replicas unchanged, so the prepare-downscale webhook is not in the
path at all; pods keep their PVC, keep `/data/tokens`, keep their ring entry, and replay the WAL on restart.
[RFC] Forcing `prepare-shutdown` first converts a cheap restart into a full unregister + flush for every pod —
slower, heavier, and it reintroduces exactly the resharding the chart is configured to avoid.

## 4. Ordered rollout sequence for one hop

```
0. PRE-FLIGHT (no mutation)     -> references/per-hop-runbook.md
   Gate: rendered diff shows only the intended delta; no unintended replica
         decrease; kubeVersion gate satisfiable; images + CRDs staged.

1. ROLL THE ROLLOUT-OPERATOR ALONE, FIRST (6.x hops)
   A helm upgrade changing only the operator/subchart version.
   Why first: from 6.0 its webhooks default on with failurePolicy: Fail on
   statefulsets UPDATE in this namespace. If the operator is unhealthy, every
   later StatefulSet write -- including helm rollback -- is rejected.
   Gate: operator Deployment 1/1; Service has a ready endpoint;
         rollout_operator_last_successful_group_reconcile_timestamp_seconds
         advancing for rollout_group="ingester" and "store-gateway".

2. helm upgrade THE MAIN RELEASE
   Do NOT rely on --wait (see Abort levers). Helm applies ConfigMap ->
   Deployment -> StatefulSet, and checksum/config in podAnnotations means any
   config change rolls every component.
   Gate: helm status deployed; no webhook denial in output.

3. STATELESS TIER settles (distributor, querier, query-frontend, scheduler,
   ruler, gateway) -- ordinary Deployments.
   Gate: updatedReplicas == replicas == readyReplicas; request error ratio flat.

4. STORE-GATEWAY ZONES, one at a time (operator-driven; no operator action)
   Each pod re-registers without ring churn, re-reads or rebuilds its
   index-header, and holds /ready for wait_stability_min_duration (1m).
   Gate per zone: all pods Ready; block-consistency-check failures flat;
                  query error rate at baseline.

5. INGESTER ZONES, one at a time (operator-driven)
   terminationGracePeriodSeconds is 1200 -- budget the window.
   Gate per zone: all pods Ready and min_ready_duration (15s) elapsed;
                  cortex_ring_members{state="Unhealthy",name="ingester"} == 0;
                  write + read error rates at baseline.
   Expect MimirRingMembersMismatch to flap -- silence it for the window.

6. COMPACTOR / ALERTMANAGER.
   Gate: compactor ring healthy; compaction running.

7. SOAK at least one compaction cycle and one head-block cut before the next hop.
```

## 5. Abort levers

Know which one you have **before** starting the hop — the set changes with the operator version.

| Lever | Verdict |
|---|---|
| `grafana.com/rollout-paused: "true"` on the STS | The correct pause — the operator skips that StatefulSet and moves on. **Requires rollout-operator ≥ v0.36.0.** Bundled appVersions: 5.7.0→v0.24.0, 5.8.0→v0.28.0, 6.0.6→v0.32.0, 6.1.0→**v0.38.0**. So on this ladder it exists **only on the final hop**. [UG] |
| Scale the rollout-operator to 0 | **Deadlocks the namespace on 6.x.** The prepare-downscale MutatingWebhookConfiguration matches UPDATE on `statefulsets` *and* `statefulsets/scale` with `failurePolicy: Fail`. No ready endpoint ⇒ the apiserver rejects every matching request — `helm upgrade`, `helm rollback`, and `kubectl scale` alike. Correct only on 5.7.0/5.8.0, which ship no webhooks. [UG] |
| Break-glass: delete the webhook configurations | `kubectl delete validatingwebhookconfiguration no-downscale-<NS> pod-eviction-<NS>` and `kubectl delete mutatingwebhookconfigurations prepare-downscale-<NS>`, then `helm upgrade … --reset-values`. Upstream-documented recovery. Stage these commands **before** the 6.0 hop. [UG] |
| Restarting the operator pod casually | Don't. It keeps in-memory state of recently evicted pods; upstream warns of a race that can breach a zone-aware PDB. [UG] |

**Two things that look like gates and are not:** [RFC]

- **`helm upgrade --wait`.** Helm's `statefulSetReady()` short-circuits for any non-`RollingUpdate` StatefulSet
  and returns true immediately, so Helm reports success the moment the STS object is patched — before a single
  ingester pod is replaced. Gate on the per-zone signals in §4, not on the command exiting 0.
- **`helm diff` / `--dry-run`.** The prepare-downscale webhook auto-allows dry-run requests, so a replica
  reduction that will be **denied** on real apply looks perfectly clean in the diff.

## 6. Rollback matrix

**The universal caveat:** upstream has never stated that Mimir supports downgrade. `CHANGELOG.md` and the chart
CHANGELOG contain **zero** occurrences of "downgrade"/"rollback"; `about-versioning.md` guarantees only that
*future* versions read old data; grafana/mimir#2807 asking for the converse has been open and unanswered since
2022. [UG] Plan every hop as forward-only at the **data** layer and treat `helm rollback` as a *workload*
rollback (image + config), not a data rollback.

| Hop | Reversible? | Mechanism | One-way doors |
|---|---|---|---|
| **5.7.0 → 5.8.0** | **Yes, cleanly** — least risky hop | `helm rollback`. The operator explicitly handles reverted revisions. No CRDs, no webhooks on either operator version. | New `grafana.com/*` labels persist (inert without webhooks). Rolling the app back to 2.16 changes query semantics (MQE→Prometheus engine). No block/ring/schema barrier. |
| **5.8.0 → 6.0.6** | **Chart layer yes; app + architecture layer effectively no** | `helm rollback` reverts workloads, **but delete the three webhook configurations first** — with `failurePolicy: Fail` and no operator behind them, they block the rollback itself. Then `--reset-values`. | **(a)** If ingest storage was allowed to default on, the write path moved to Kafka and there is **no documented reverse migration** — the official path is a parallel-cluster migration. Pin classic *before* the hop and this door stays shut. **(b)** CRDs survive forever — Helm never deletes them. **(c)** 3.0 removed **159** flags 2.17 knew, and 2.17 rejects **70** flags 3.0 introduced, so a binary downgrade fails loudly. **(d)** HA-tracker default KV flipped to memberlist — a silent rollback loses dedup state. |
| **6.0.6 → 6.1.0** | **Chart rollback yes; app downgrade risky only with ingest storage** | `helm rollback`. Operator subchart downgrades; CRDs and webhooks stay (harmless, same API group). | **(a)** 3.1 defaults `-ingest-storage.kafka.producer-record-version=2`. 3.0.4 reads V2; **2.16 cannot** (`pkg/storage/ingest/version.go` does not exist at that tag). So 3.1→3.0 is survivable, 3.1→2.16 is not. Irrelevant on classic. **(b)** `kafka.extraEnv` removal makes values files diverge in both directions. **(c)** 3.1 requires index v2 on ingest and drops v1 index-header generation. **(d)** 3.1 tightened per-query memory accounting — "queries that previously succeeded may now fail". |

**What is *not* a barrier in this window:** TSDB block format. Both 2.16.0 and 3.1.2 write index `FormatV2` and
`meta.json` `TSDBVersion1`, and the sparse index-header proto is field-identical across 2.16.0/2.17.0/3.0.4/3.1.2.
[UG] The sharp edge is the Kafka record version, and only if you adopted ingest storage — which is one more
reason the classic path keeps your options open.
