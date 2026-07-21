---
name: mimir-upgrade
description: >-
  Plan and run a controlled, COMMUNITY-edition Grafana Mimir upgrade on the `mimir-distributed` Helm chart,
  air-gap first — the chart↔app co-pinned ladder (5.7→5.8→6.0.6→6.1.0 = app 2.16→2.17→3.0.4→3.1.2), the
  classic-vs-ingest-storage decision (the chart ships a supported `classic-architecture.yaml`; `kafka.enabled:
  false` alone is NOT the switch and causes an ingestion outage), the community-specific nginx→gateway rename
  that silently moves the proxy's DNS name and breaks every remote_write client, the silent-no-op vs crashloop
  asymmetry between stale chart keys and stale app config, rollout-operator sequencing and the abort levers that
  deadlock a namespace, per-hop verification, and air-gap image/CRD/egress work. Companion to
  k8s-components-checker.
when_to_use: >-
  Use when the user mentions upgrading Grafana Mimir or the mimir-distributed Helm chart, a Mimir 2.x→3.x move,
  chart 5.x→6.x, "mimir upgrade", staying on classic architecture vs adopting ingest storage / Kafka,
  `classic-architecture.yaml`, the Kafka-based ingest storage architecture, migrating nginx→gateway on the Mimir
  chart, rollout-operator behaviour for ingesters/store-gateways, or air-gapped Mimir image staging. Also symptom
  prompts: remote_write broke after a Mimir chart upgrade, ingestion stopped after enabling/disabling Kafka,
  helm upgrade hangs or is rejected by a webhook, ingesters not going Ready, "can I roll back Mimir".
  NOT for querying Mimir or PromQL (use prometheus-mimir-grafana); NOT for compat verdicts
  (use k8s-components-checker).
---

# mimir-upgrade

Plan, sequence, and de-risk a **community-edition Grafana Mimir** upgrade deployed via the `mimir-distributed`
Helm chart, in an **air-gapped** environment. The hard part is not `helm upgrade`. It is that chart 6.0 changes
the **write-path architecture**, the **proxy's DNS name**, and the **admission-webhook posture** all in one hop —
and the chart validates none of the operator's stale values, so most of the damage is silent.

**Community editions only.** Ignore Grafana Enterprise Metrics (GEM) gating; the whole GEM values surface is
removed from the chart at 6.0 anyway.

## Evidence tags — do not flatten these

Every claim in this skill is tagged:

- **[UG] upstream-grounded** — a doc, changelog, release note, or source file says it.
- **[RFC] reasoned-from-config** — derived by reading chart templates, values, or Go source.

Both tags mean *researched*. The grounding runs to tagged upstream source (`help-all.txt.tmpl`,
`config-descriptor.json`, `pkg/ingester`, `pkg/usagestats`, `pkg/storage/ingest`), kubectl's and Helm's own
source, both CHANGELOGs, the docs, and six issues cited as evidence of absence. Two claims were settled by
experiment rather than reading: the `classic-architecture.yaml` render was diffed against upstream's golden CI
fixture (79/79 config keys), and the `null`-semantics question was settled by compiling a probe against Mimir's
exact YAML library.

What is missing is a third level: **behavioural observation on a running cluster.** No lab cluster existed when
this was written, so no claim here has been watched working. That gap is narrow and specific — see the first
Open item in `references/improvement-backlog.md` for the three questions only a cluster can answer — but it is
real, and it is why a `[RFC]` is not a `[UG]`.

Keep the distinction when extending this skill, and never promote an `[RFC]` to `[UG]` without citing the
source that justifies it. An operator betting a production write path on an inference deserves to know it is
one.

## Companion to k8s-components-checker — who owns what

| Question | Skill |
|---|---|
| **Compat verdicts** — `kubeVersion` floors, per-minor support windows, what is in scope, whether a hop is legal on a given k8s minor | **k8s-components-checker** — `references/compat/mimir.md` is the source of truth. **Cite it; don't restate.** Those numbers drift and a second copy goes stale silently. |
| How to query Mimir, PromQL, dashboards | **prometheus-mimir-grafana** |
| How to plan/sequence/execute the upgrade, and what breaks | **this skill** |

## Step 0 — the fleet-facts interview, before any planning

Five facts change the plan materially and **cannot be inferred from the chart**. Ask, or read them off the
cluster. Do not draft a plan without them — a plan built on the wrong answer to #1 is a plan that schedules an
outage.

1. **Does the release run `<release>-nginx` or `<release>-gateway`?**
   `kubectl get deploy -n <ns> | grep -E 'nginx|gateway'`. Community fleets on 5.x almost always run **nginx**,
   and that is precisely the case chart 6.0 breaks. This is the single highest-value question here.
2. **`ingester.ring.replication_factor`** — the fan-out verification check assumes RF=3.
3. **Is `rbac.type: psp` still set?** `templates/podsecuritypolicy.yaml` still emits `policy/v1beta1`, removed in
   k8s 1.25. Unchanged across every hop, but a live landmine on a modern cluster.
4. **Is the Mimir mixin vendored** into a separate Prometheus/ruler? Drives how much the ~22 alert renames at
   6.1.0 cost.
5. **The CoreDNS Service name.** On RKE2 it is `rke2-coredns-rke2-coredns`, not `kube-dns` — see the
   `global.dnsService` gotcha in `references/air-gap.md`, which crash-loops the gateway and looks like a
   network fault.

Also confirm: current chart + app version, k8s minor now and planned, whether an external object store or the
bundled minio is in use, and whether the operator has a maintenance window long enough for zone-serial rolls
(ingester `terminationGracePeriodSeconds` is 1200).

## The load-bearing facts

1. **Chart and app are co-pinned; walk one minor at a time.** [UG] Mimir's policy is that upgrading one minor to
   the next works and deprecated features survive two minors. Chart minors track app minors, so the two ladders
   are one walk. Skipping 6.0 to reach 6.1 is not possible — the architecture decision lands *at* 6.0.
2. **Chart 6.0 flips the write path by default.** [UG] `ingest_storage.enabled: true` and
   `ingester.push_grpc_method_enabled: false` are hardcoded in the chart's default Mimir config. A naive upgrade
   with a 5.x values file moves the entire write path onto a **single-node demo Kafka**. Decide the architecture
   *before* the hop → `references/architecture-decision.md`.
3. **`kafka.enabled: false` is not the architecture switch.** [RFC] It only stops the chart *deploying* Kafka.
   Alone it produces ingest-storage-configured Mimir with the classic push path disabled and no broker — a total
   ingestion outage that pod status will not reveal. The supported opt-out is the chart's own
   `classic-architecture.yaml`.
4. **The nginx→gateway rename is the highest-severity silent break, and it only hits community fleets.** [RFC]
   In 5.x the gateway was gated off for community, so community fleets ran `<release>-nginx`; 6.0 deletes it and creates
   `<release>-gateway` at a **different DNS name**. Every remote_write client, Grafana datasource, and ingress
   backend breaks at once. Mitigate with `nameOverride`, on 5.8.0, in its own `helm upgrade` →
   `references/per-hop-runbook.md`.
5. **Two opposite failure modes live in one values file.** [RFC] The chart ships **no `values.schema.json`** in
   any version in scope, so a stale *chart* key is a **silent no-op**. But Mimir **rejects removed app config at
   startup**, so a stale `structuredConfig` key is a **crashloop**. Audit both, expecting different symptoms.
6. **MQE becomes the querier default at 2.17 — the first hop.** [UG] Not at 3.0, which only extends the default
   to query-frontends. Pin `-querier.query-engine=prometheus` through 5.8.0 and flip the engine as a separate,
   revertible change, or a read-path regression is un-bisectable from the chart bump.
7. **`helm upgrade --wait` is not a gate, and the obvious abort lever deadlocks the namespace.** [RFC] Helm's readiness
   check short-circuits for non-`RollingUpdate` StatefulSets, so it reports success before any ingester rolls.
   And on 6.x, scaling the rollout-operator to 0 blocks *every* StatefulSet write in the namespace —
   including `helm rollback` → `references/rollout-and-rollback.md`.
8. **Downgrade is an unmade upstream claim.** [UG] Zero occurrences of "downgrade"/"rollback" in either
   changelog; grafana/mimir#2807 has been open and unanswered since 2022. Treat every hop as forward-only at the
   **data** layer; `helm rollback` is a workload rollback only.

## Workflow

1. **Run Step 0.** Without those five facts the plan is guesswork.
2. **Get the version verdict from `k8s-components-checker`** (`compat/mimir.md`) — chart→app mapping,
   `kubeVersion` floors, what is in scope. Do not re-derive it here.
3. **Decide the architecture** → `references/architecture-decision.md`. For an air-gapped community fleet with
   no capacity for a parallel cluster, staying classic is the supported low-risk answer.
4. **Sequence the ladder against the k8s upgrade.** The only hard ordering constraint is that the k8s minor
   required by the final chart lands *before* it. Putting the k8s hop mid-ladder keeps the Mimir major and the
   k8s minor from landing together.
5. **Per hop:** pre-flight → stage images/CRDs → upgrade → verify → soak.
   `references/per-hop-runbook.md`, then `references/verification.md`.
6. **Identify the abort lever before starting the hop, not during it.**
   `references/rollout-and-rollback.md`.

## Pre-flight gates (run before EVERY hop)

- `helm get values <rel> -o yaml > current.yaml` and `helm get manifest <rel> > before.yaml`. These are the diff baseline, and the record of what the release actually had.
- Snapshot the routed alert names: `helm get manifest <rel> | grep -oP '(?<=- alert: )\S+' | sort -u`.
- `helm template` the target chart against `current.yaml` and diff against `before.yaml`. Assert: proxy Service
  name unchanged, intended image/config delta only, **no unintended replica decrease** on any ingester or
  store-gateway zone.
- Audit stale keys **both ways** — chart keys (silent) and `structuredConfig` keys (crashloop):
  `${CLAUDE_SKILL_DIR}/scripts/audit-values.sh <current-values.yaml> <target-chart-version>`. It is advisory (grep cannot parse YAML
  structure) — verify each hit in context, then let the rendered diff catch what grep cannot.
- Stage every image for the hop into the internal registry, including `grafana/rollout-operator`.
- Apply any new rollout-operator CRDs **by hand** — Helm never installs `crds/` on upgrade.
- Confirm the k8s `kubeVersion` gate is satisfiable. There is no bypass flag.

## House rules

1. **Cite `compat/mimir.md` for compat verdicts; own the procedure here.** Two copies of a support matrix means
   one is wrong and nobody knows which. The line is not "no numbers appear in this skill" — the ladder
   (5.7→5.8→6.0.6→6.1.0) and the per-hop image tags are *worked examples of a procedure*, and a runbook without
   them is unusable. The rule is that **no floor, support window, or legality verdict is decided here.** When a
   hop's numbers and the registry's disagree, the registry wins and this skill's example is stale — re-derive
   the ladder per run rather than trusting the headings.
2. **Prefer the chart's shipped `classic-architecture.yaml` over the migration guide's snippet.** [RFC] The doc
   snippet omits `distributor.remote_timeout: null` and silently leaves the Kafka-tuned 5s in place.
3. **Land on the patch the compat registry names, never on `x.y.0`** when a known-bad `.0` is recorded (6.0.0 /
   6.0.1 carry a rollout-operator cert bug needing manual secret deletion).
4. **One change per `helm upgrade`.** The proxy migration, the engine flip, and the chart bump are three
   changes. Bundling them makes a regression un-bisectable — which is the same reason the ladder itself has no
   skips.
5. **Never POST `/ingester/prepare-shutdown` before a version bump.** [RFC] Replicas are unchanged so the
   webhook is not in the path; forcing it triggers unregister + full flush, the expensive scale-down path.
6. **Treat "pods are Running" as evidence of nothing.** Verify with the gates in `references/verification.md`.

## References

| File | Read it when |
|---|---|
| `references/architecture-decision.md` | Deciding classic vs ingest storage; the `kafka.enabled` trap; what running Kafka for Mimir actually costs |
| `references/per-hop-runbook.md` | Executing a hop — per-hop pre-flight checklists, the nginx→gateway migration, removed-key tables |
| `references/rollout-and-rollback.md` | Rollout-operator sequencing, the corrected `kubectl rollout restart` story, abort levers, the rollback matrix |
| `references/verification.md` | Proving a hop worked — mixin alert names, the 6.1.0 alert renames, sample-loss PromQL, MQE differencing |
| `references/air-gap.md` | Staging images, killing usage-stats egress, CRDs, the RKE2 `global.dnsService` gotcha |
| `references/sources.md` | Verifying or freshening a claim — per-row source + `Last verified` date |
| `references/improvement-backlog.md` | Before extending the skill — what was tried, what is unresolved, and the three questions only a cluster can answer |
| `${CLAUDE_SKILL_DIR}/scripts/audit-values.sh` | Pre-flight on every hop — flags removed chart keys (silent) and removed app config (crashloop) in a values file |
