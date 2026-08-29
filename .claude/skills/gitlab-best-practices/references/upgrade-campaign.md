# Upgrade campaign — required stops, the layered diff, and the chart-10 wall

Method and hazards for moving a self-managed GitLab across multiple versions on
the official Helm chart.

**Tag convention.** Untagged claims were verified against a primary source or a
live install on 2026-08-29. **[A]** = reported but not independently
re-verified — re-check before acting.

## Table of contents
- [Build the ladder from machine-readable sources](#build-the-ladder-from-machine-readable-sources)
- [The layered diff](#the-layered-diff)
- [Four rules that keep the diff honest](#four-rules-that-keep-the-diff-honest)
- [Reading a prerequisite before complying with it](#reading-a-prerequisite-before-complying-with-it)
- [The chart-10 wall](#the-chart-10-wall)
- [Diffs that look like damage and are not](#diffs-that-look-like-damage-and-are-not)
- [Per-hop verification](#per-hop-verification)
- [Rollback is a restore plan](#rollback-is-a-restore-plan)

## Build the ladder from machine-readable sources

Never take the stop list, the chart↔app mapping, or the latest version from
memory or from a prose docs page.

```bash
# required stops — authoritative, minor-level
curl -sS https://gitlab.com/gitlab-org/gitlab/-/raw/master/config/upgrade_path.yml

# chart <-> app mapping, unfiltered
helm repo add gitlab https://charts.gitlab.io && helm repo update gitlab
helm search repo gitlab/gitlab --versions | head -30
```

**Chart major = app major − 9.** Chart `9.x` → GitLab `18.x`, chart `10.x` →
GitLab `19.x`. Chart patch and app patch drift apart (chart 9.11.12 carries app
18.11.11) — never assume they are equal, and name both numbers in any artifact.

Three things operators get wrong about stops:

| Belief | Reality |
|---|---|
| Stops are patch-precise (18.8.7) | `upgrade_path.yml` is **minor-level** (`major: 18, minor: 8`). Take the highest patch of that minor. Patch-level entries existed for some 17.x historically, which is where the confusion starts. |
| The `.0` of a new major is a stop | There is no `19.0` entry. The path is 18.11 → **19.2**, crossing every 19.0 and 19.1 breaking change in one hop with no intermediate resting point. Satisfy 19.0's prerequisites *before leaving 18.11*. |
| The required-stop path is the schedule | It is the floor. Out-of-band CVE hops land between stops and must be budgeted for. |

Stops for 18→19: **18.2 → 18.5 → 18.8 → 18.11 → 19.2**, then any later minor.

There is an official Support upgrade-path calculator, but it renders
client-side and cannot be scraped — use the YAML. **[A]**

**Background migrations gate every hop, not just the last.**

```bash
kubectl exec -n <ns> deploy/<release>-toolbox -- \
  gitlab-rake gitlab:background_migrations:status
```

SQL equivalent when the rake task is unavailable — empty result means done. `3`
and `6` are the finished/finalized status codes: **[A]**

```sql
SELECT job_class_name, table_name, status
FROM batched_background_migrations WHERE status NOT IN (3, 6);
```

## The layered diff

One diff cannot see everything, because the information lives in structurally
different places. Run all six; each catches what the others cannot.

| Layer | Compares | Catches |
|---|---|---|
| `default-diff` | stock values V vs V+1 | keys added / removed / **renamed**, and **default flips** |
| `stock-diff` | stock *render* V vs V+1 | RBAC, probes, container args, hardcoded configmap keys — none of which exist in `values.yaml` at all |
| `values-diff` | site values vs stock | the site delta, isolated |
| `verify` | set difference | edit-set intact, no invented keys, no stale version pins |
| `template-diff` | site render V vs V+1 | what actually reaches the cluster |
| `diff` | site render vs **live cluster** | last gate before apply |

**The default-flip layer is the one that pays.** A site inheriting a default
cannot see it change by looking at what it *sets*. Crossing chart 9.11.12 →
10.2.5, a hand-built breaking-change table written a week earlier from the
release notes still missed one of five flips
(`global.ingress.configureCertmanager`); only the mechanical stock-values diff
caught it. Diff stock values every hop, including against your own notes.

## Four rules that keep the diff honest

**1. Never `patch` a values delta onto a new version — use `diff3`.** `patch`
has two inputs and cannot know what the file looked like when it was edited.
Replaying a site delta with `patch -F3` once fuzz-matched a
`hostPort.enabled: false→true` hunk onto the adjacent, identically-shaped
`hostFirewall.enabled`, silently enabling host firewall cluster-wide, exit 0.
`diff3` has three inputs and raises a conflict. Keep the stock values file of
the version currently running — it is the common ancestor for the next merge.
Merge mechanics live in the **`helm`** skill, in its own
`references/values-porting.md` — not in this skill.

**2. `helm lint` is not a typo check.** Charts that ship
`values.schema.json` usually generate it from values keys and never set
`additionalProperties: false`, so a misspelled key renders exit 0 and is
silently ignored.

**3. Never `kubectl apply` the rendered template.** It rotates
lookup-generated TLS/CA secrets. Only `helm upgrade`.

**4. Offline `helm template` misreports API versions, badly.** A cluster-less
render cannot populate `.Capabilities.APIVersions`, so any chart choosing an
apiVersion via `Capabilities.APIVersions.Has` falls to its **oldest** branch.
On a chart 9.x render the offline output emitted `autoscaling/v2beta1`
(removed in k8s 1.26), `extensions/v1beta1` Ingress (removed in 1.22),
`policy/v1beta1` PDB (removed in 1.25), and **dropped the HPA `behavior` block
entirely**. `helm upgrade` is unaffected because it talks to the cluster — so
this corrupts *only the artifacts the diff layers read*, which is precisely the
gate being trusted.

```bash
# enumerate what the chart probes, then what the cluster actually has
grep -rhoE 'Capabilities\.APIVersions\.Has "[^"]+"' <unpacked-chart> | sort -u
kubectl api-versions
helm template ... -a autoscaling/v2 -a policy/v1/PodDisruptionBudget ...
```

`--kube-version` does **not** fix this; only `-a` / `--api-versions` does.
Refresh the flag list against `kubectl api-versions` at every hop.

### Two umbrella-chart traps

**`helm show values` lies by omission.** The gitlab chart is an umbrella, and
`helm show values` prints only the *parent* `values.yaml`. Every subchart key —
`gitlab.sidekiq.*`, `registry.*` — is invisible to it. A verify step that asks
"does this key exist in stock values" will flag legitimate subchart keys as
invented. Allow-list them after confirming against the subchart's own
`values.yaml` inside the tarball.

**Subchart settings can be silently shadowed.** Sidekiq renders per-pod from a
`pods:` list, and every tunable is read as `default $.Values.X .X` — the global
is only a *fallback*. A per-pod override wins, so setting the global on an
install that defines per-pod values is a **silent no-op that renders clean and
diffs clean**. Confirm which one the template actually reads.

## Reading a prerequisite before complying with it

**A prerequisite in release notes is written for the DEFAULT configuration.**
The most reusable finding of a four-hop campaign.

Chart 10.3.0 ships a manual step Helm cannot do: apply the Envoy Gateway and
Gateway API 1.9.0 CRDs *before* upgrading, or the upgrade "fails on the GitLab
Shell TCPRoute". That reads as mandatory for everyone. It is not — the named
failure is on a **Gateway API object**, and with `global.gatewayApi.enabled:
false` the chart renders none, so there is nothing for the API server to
reject. Verified by upgrading with **zero** Gateway API CRDs installed
(`kubectl get tcproute` → *the server doesn't have a resource type "tcproute"*).

Two-step test, cheaper than both guessing and complying blindly:

1. Render the target chart **with the real values** and grep for the object kind
   the prerequisite names.
2. If it does not render, the prerequisite cannot fire. Record *why*, so the
   next person does not re-derive it.

Complying "just in case" is not free: Gateway API CRDs are cluster-scoped, and
installing them to satisfy a step you do not need leaves another controller's
API surface in the cluster permanently.

**Deprecation removals cluster on required stops.** `global.appConfig.knowledgeGraph`
was deprecated for `orbit` with removal planned for 19.5 — itself the next
required stop. Sites are forced through stops, so that is where removals are
aimed. After finishing a campaign, grep the new stock values for `Deprecated`
and note anything whose removal milestone equals the next stop.

**The chart enforces its own sequencing.** The upgrade-check hook carries
`MIN_VERSION` / `CHART_MIN_VERSION` (19.2 / 10.2 at chart 10.3.1) and refuses a
jump from too far back — observed twice in one campaign. Useful as a safety
net; do not use it as the plan, because it enforces chart minimums, not
GitLab's required-stop list.

## The chart-10 wall

Everything below lands in the single 18.11 → 19.2 hop.

### Five default flips, four documented

| key | 9.11.12 | 10.2.5 |
|---|---|---|
| `global.ingress.enabled` | true | **false** |
| `global.gatewayApi.enabled` | false | **true** |
| `global.gatewayApi.installEnvoy` | false | **true** |
| `global.gatewayApi.configureCertmanager` | false | **true** |
| `global.ingress.configureCertmanager` | true | **false** |

Left unpinned, `global.ingress.enabled: false` alone stops every Ingress object
rendering and takes the instance off the network behind its ingress controller.

### Chart 10.0 makes external dependencies MANDATORY, not merely unbundled

Chart 10.0 deletes bundled PostgreSQL, Redis and MinIO **and** adds hard `fail`s
in `NOTES.txt`. A render with **default** values now aborts:

```
postgresql:
    You must configure an PostgreSQL connetion. Please set `global.psql.host`.
    Since chart v10.0.0, external PostgreSQL became required.
```

(the typo is upstream's). This breaks **tooling**, not the deployment — any
"render the chart with defaults" step dies, and an all-features image sweep for
air-gap mirroring dies with it. Minimum scaffold to restore a default-values
render, all throwaway placeholders that must never reach a deployed manifest:

```bash
--set certmanager-issuer.email=x@x.com \
--set global.psql.host=x --set global.psql.password.secret=x \
--set global.redis.host=x \
--set global.appConfig.object_store.enabled=true \
--set global.appConfig.object_store.connection.secret=x \
--set registry.storage.secret=x --set registry.storage.key=config \
--set gitlab.toolbox.backups.objectStorage.config.secret=x
```

**Generalise it:** when a chart drops bundled dependencies, budget for the
release to break the diffing and mirroring tooling, not just the values.
Nothing in a values delta predicts it.

### The rest of the 19.0 wall

- **PostgreSQL 17 is minimum *and* maximum** for 19.x → `references/external-deps.md`.
- **NGINX Ingress replaced by Gateway API with Envoy Gateway** as the chart
  default; NGINX stays opt-in until removal in GitLab 20.0. Sites on a
  third-party ingress with the chart's nginx disabled are largely insulated.
- **Redis 6 support removed** — 7.0+ or Valkey 7.2+; 7.2 recommended.
- **Spamcheck removed** from Linux package and chart.
- **OAuth Resource Owner Password Credentials grant removed.** **[A]**
- **Container registry `s3` driver "replaced" by `s3_v2`** — read the scope
  note in `references/external-deps.md` before doing any work for this. It is
  not a breaking change.

### Version distance does not predict risk

10.2.5 → 10.3.1 is 126 lines of stock values delta with **zero** default flips;
the values file carried forward byte-identical. 9.11.12 → 10.2.5 is one chart
minor too. **Budget review time from the diff, not from the version number.**

## Diffs that look like damage and are not

Neither is a defect.

- **`web_exporter.address: "0.0.0.0"` → empty.** Upstream set the default to
  `null`, commented *"binds IPv4 and IPv6"*. The empty value is **broader** than
  the old one. Check the subchart's `values.yaml` default before escalating an
  emptied bind address.
- **Gitaly's configmap stops being TOML** and becomes a gomplate
  `data.JSON | data.ToTOML` expression, so a line diff replaces the whole file
  with one long line. Key-for-key equivalent.
- **`BIND_IP6` false → true** on webservice at 19.3.1. Safe by construction:
  `listen_all_addr = PumaIPv6.resolve_bind_addr('[::]', '0.0.0.0')` falls back
  to IPv4 when IPv6 is unusable. Knob: `gitlab.webservice.puma.bindIp6`.
  Generalisable: when a bind address or protocol default flips, read the
  consuming config for a fallback before assuming an outage.

## Per-hop verification

In order of how much each proves, cheapest first:

1. `helm list` — chart and app version actually recorded.
2. `kubectl get ingress` — objects exist **and** carry an external address.
3. `kubectl get gateway,httproute` — returns nothing, proving the ingress pins
   held (invert if Gateway API is the intended path).
4. HTTP 200 on the web host.
5. Registry `/v2/` returns **401** — the correct answer for an authenticated
   registry, and proof the storage driver initialised.
6. Background migrations: active is fine, **paused or failed is not**.

**A failed `helm upgrade` is frequently a timeout on a long migration, not a
broken release.** A `context canceled` revision sitting immediately before a
successful retry of the same version is the signature. Check before reacting.

## Rollback is a restore plan

Official position: rollback means reverting the **database schema**, which
requires *"a database backup created at the exact version and edition you're
downgrading to"*, and the restore *"overwrites all newer GitLab database
content"*. **There is no supported path to `helm rollback` after migrations
have run against production data.** The documented remedy for a bad
mid-migration state is to go **forward** to a required stop. **[A]**

`helm rollback` recovers a bad values change. It does not recover a bad
upgrade. Build the restore plan instead → `references/backup-restore.md`.
