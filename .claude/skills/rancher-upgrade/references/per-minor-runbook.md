# per-minor-runbook.md — breaking changes 2.11→2.14 + the ordered runbook

**Grounded via `gh` release notes/issues + ranchermanager docs: 2026-05-30.** Community-relevant
items only; Prime-gated content excluded. Cross-check the issue numbers at use time. The
mgmt-cluster k8s window per minor is NOT restated — cite `compat/rancher.md`.

## Per-minor breaking changes & known issues

### 2.11 (GA 2025-03-31)
- **k8s 1.28 & 1.29 removed** (#48628) — clusters must be on k8s ≥1.30 before landing on 2.11.
- **Restricted Admin role removed** (#47875) — affected users lose privileges on upgrade; audit
  bindings first.
- **Multi-Cluster Apps removed** (#39525); legacy CLI + `globaldns` subcommand removed; telemetry /
  opt-out setting removed.
- Imperative API Extension / agg-layer default-on (#47010) — origin of the "agg-layer required" rule.
- **Deprecations *announced* here, enforced in 2.12:** RKE1 EOL (2025-07-31) and Rancher-Istio.

### 2.11 → 2.12 (the first hard wall)
- **RKE1 resource sweep first bites** (#50286) — a gating pre-upgrade check fails the helm upgrade if
  RKE1 leftovers remain. Many 2.11 clusters still carry them. Clean while Rancher is live.
- k8s floor moves 1.30→1.31 (#49679) — lift mgmt + hand-managed downstreams off 1.30 first.
- Helm client must be **≥3.18**.
- **ui-sql-cache disk audit** (see 2.12).

### 2.12 (GA 2025-07-31)
- **RKE1 EOL sweep** is gating (#50286).
- **Server-Side Pagination (`ui-sql-cache`) on by default** (#48691) → ephemeral-disk growth on
  Rancher server + `cattle-cluster-agent` pods → **DiskPressure / pod eviction** risk. Audit node
  ephemeral storage before upgrading.
- Helm **≥3.18** required.
- Rancher-Istio deprecated (community has no Rancher-managed Istio path forward).
- **CIS Benchmarks → Rancher Compliance App** (`cis.cattle.io` → `compliance.cattle.io`, #50795);
  scan history not migrated.
- k8s 1.30 removed (#49679). Imported-cluster reconnect issue on 2.11.x→2.12.0 (#51066).

### 2.13 (GA 2025-11-25)
- **Rancher Provisioning CAPI chart auto-replaced by Rancher Turtles** (#52254) — see
  `capi-turtles-fleet.md`.
- **OIDC Auth Provider settings may be lost** on 2.12.x→2.13.x (#53995, now CLOSED/fixed) — back up
  the OIDC AuthConfig anyway before upgrading.
- k8s 1.31 removed (#51253).
- **Air-gapped CAPI `capi-controller-manager` may fail to go Active**, blocking provisioning post-
  upgrade (#52816) — pre-stage CAPI controller images in the mirror; watch the pod after upgrade.
- *2.12.3→2.13.3 field-validated 2026-05-30 (standalone mgmt cluster):* Turtles auto-swap (#52254)
  ran exactly as described — CAPI relocated to the new Turtles namespaces, the old provisioning-capi
  namespace emptied; Fleet 0.13→0.14 rode the chart; OIDC survived (the #53995 backup was correct
  insurance, not needed). All post-upgrade errors were startup-transient.

### 2.14 (GA 2026-03-26; current community line, latest 2.14.2)
- **Embedded Cluster API removed** (#53291); **CAPI → v1beta2** (#52034/#53334) — one-way rollback
  boundary. See `capi-turtles-fleet.md`.
- **cert-manager compat shims removed** (#52922) — out-of-window cert-manager fails admission; bump
  cert-manager first.
- **Fleet → Helm v4** (v0.15.0); drift-correction issue **#4878 fixed in 2.14.1** — target 2.14.1+ if
  using Fleet drift correction.
- **Google OAuth broken in 2.14.0, fixed in 2.14.1** (#54387 main + #54416 v2.14 backport, both
  CLOSED) — if using Google OAuth, install 2.14.1+, skip the 2.14.0 GA.
- **CAAPF disabled by default at 2.14.1** (turtles#2176).
- Ingress proxy-timeout annotations dropped by default (#53272) — set explicitly if a custom proxy
  relied on them. 2.13.2→2.14 CrashLoop (#53854, CLOSED — fixed at 2.14.0 GA).
- *2.13.3→2.14.2 field-validated 2026-05-30 (standalone mgmt cluster) — completes the 2.12→2.14 path
  end-to-end:* CAPI v1beta1→v1beta2 **did** cross (served + stored), just lagging the helm return —
  the fresh pre-step etcd snapshot was correct discipline. Fleet 0.14→0.15 + Helm v3→v4 migrated clean
  (#4878 did not bite). cert-manager shim removal (#52922) a non-event with cert-manager already
  in-window. Embedded-CAPI removal (#53291) had no separate effect (Turtles owned CAPI from 2.13).
- **2.14 values gotchas:** `includeDefaultExtraAnnotations` default flips **`true→false`**
  (ingress-nginx retiring) — keep `false` for non-nginx ingress (Traefik); it drops nginx-only default
  annotations from the rendered Ingress. A new `gateway.gatewayClass.tls` block also carries a
  `source:` key, so when porting an ingress `tls.source` customization, disambiguate by indent (the
  ingress `source` is shallower) or the edit lands in the wrong block.

## The runbook — iterate ONCE PER MINOR STEP (2.11→2.12→2.13→2.14)

The supported path is one minor at a time on latest patches; run this whole block per step.

**Execution model (field-validated 2026-05-30).** Treat each step as `MANDATORY`, `CONDITIONAL`
(predicate stated — verify, then skip silently if it doesn't apply), or `MAY-NOT-APPLY`. Evaluate
each against the live cluster and drop the inapplicable ones in one line — don't re-litigate them as
open questions (image mirroring is air-gap-only; re-grounding is stale-date-only; BRO is if-installed).
The prep → port-values → template → diff → upgrade → verify chain is **reversible up to the
`helm upgrade`** — execute it continuously, no per-step sign-off. The one genuinely irreversible fork
is the **etcd-snapshot-then-CAPI-v1beta2 migration at 2.14**; stop and confirm there, nowhere else.

**PRE-FLIGHT**
0. **Kubeconfig not Rancher-proxied** (`server` ∌ `/k8s/clusters/`) — else switch to the RKE2/RKE
   admin kubeconfig FIRST; upgrading through the proxy severs the API mid-apply
   (`prereqs-and-ordering.md` § Pre-flight). Also silence any pre-existing reconcile-error loop now
   (e.g. an orphaned cloud credential whose token was deleted), so post-upgrade logs are clean signal.
1. Confirm you're on the **latest community patch of the current minor** (ground via `gh`).
2. **Back up:** BRO backup **and** an RKE2 etcd snapshot of the mgmt cluster (`prereqs-and-ordering.md`).
3. **k8s floor:** get the mgmt cluster (and hand-managed downstreams) onto the target minor's k8s
   floor (cite `compat/rancher.md`).
4. **Helm client ≥3.18** (2.12+).
5. **cert-manager** in the supported window (mandatory before 2.14 — shims are gone).
6. **Downstream coordination:** lift any *trailing* downstream cluster into the target Rancher's KDM
   window NOW (`kdm-downstream-matrix.md`), before the host upgrade.
7. **Step-specific gates:**
   - → 2.12: delete RKE1 leftovers (#50286); audit ui-sql-cache ephemeral disk (#48691); audit
     Restricted-Admin / MCA usage.
   - → 2.13: back up the OIDC AuthConfig (#53995); air-gap — pre-stage CAPI controller images (#52816).
   - → 2.14: re-enable Turtles if it was disabled (else v2prov breaks); target **2.14.1+** if Google
     OAuth or Fleet drift correction is in use; set Ingress timeout annotations explicitly (#53272);
     set `features.use-caapf.enabled: true` first if you used CAAPF.

**UPGRADE**
8. Upgrade the **management Rancher chart FIRST** (air-gap variant + `--set` flags from
   `air-gap-procedure.md`), to the **latest patch** of the target minor (avoid a `.0` with a known
   regression, e.g. 2.14.0).
9. Let CAPI/Turtles + CRD migrations reconcile before touching downstream.

**POST-FLIGHT**

> **Verify on the SETTLED state — never "correct" the plan from an unsettled snapshot.** After
> `helm upgrade` returns, the Fleet version bump, the Fleet **Helm v3→v4** migration, and the CAPI
> CRD version change are Rancher-driven ASYNC reconciliations that settle **~5–15 min later**, not in
> the helm output. Read them from durable truth — the **`fleet-version` setting**, CRD
> **`storedVersions`**, and **Job/helm-operation completion** — NOT the transient mid-reconcile pod
> image. Snapshotting too early reports **false negatives** ("Fleet didn't bump", "CAPI stayed
> v1beta1"); if such an observation contradicts this runbook, **re-check after settling — do not write
> the contradiction back into the plan.** (field-validated 2026-05-30: both transitions lagged the
> helm return, then completed exactly as predicted.) The values re-port between minors is usually
> trivial — a straight copy of the site's customizations if no keys moved.

10. Rancher pods healthy (watch CrashLoop @2.14, DiskPressure @2.12).
11. Auth intact — OIDC (@2.13), Google OAuth (@2.14).
12. CRD migrations landed — `compliance.cattle.io` replacing `cis.cattle.io` (@2.12); CAPI CRDs at
    v1beta2 with no orphaned v1beta1 (@2.14).
13. Imported/downstream clusters reconnected (@2.12 #51066); v2prov works (Turtles enabled, @2.14).
14. Fleet healthy (drift correction, #4878 @2.14).
15. **Now** bump downstream k8s minors that the new KDM unlocked.
16. Proceed to the next minor step (back to PRE-FLIGHT #1).
