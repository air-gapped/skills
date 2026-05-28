# harbor — compat (sifted from release_notes)

- **Primary source:** https://github.com/goharbor/harbor/releases
- **Secondary sources:** https://github.com/goharbor/harbor-helm (chart → app pinning, k8s test matrix), https://goharbor.io/docs/
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 2.13
- **Last sifted:** 2026-05-28

Harbor is plain Deployments — no CRDs, no operator. The compat surface is
(a) which k8s minors the chart was tested on, (b) DB schema migrations that
the chart runs on upgrade, and (c) one-way changes (replication adapter
allowlist, scanner removals, base image bumps) that bite when crossing a
minor.

Chart → app pinning (`harbor-helm` → `harbor`): **1.19.x → 2.15.x**, **1.18.x →
2.14.x**, **1.17.x → 2.13.x**. The chart's `Chart.yaml` does NOT declare a
`kubeVersion:` constraint (still `apiVersion: v1`), so the only authoritative
k8s window is the integration-test matrix baked into
`.github/workflows/integration.yaml` at each chart tag, plus the
`docs/kubernetes-version-matrix` table merged into `README.md` (harbor-helm
PR #2241). Helm will not block install on an out-of-matrix cluster — the
operator owns that decision.

## 2.15 — chart 1.19.x (1.19.0 → 1.19.1)

- **k8s floor:** **tested on 1.32 – 1.34** (chart 1.19 integration matrix:
  `v1.32.8, v1.33.4, v1.34.0`). README still claims "Kubernetes v1.20+"
  generically — trust the matrix, not the README.
- **Breaking:**
  - Trivy bumped to v0.69.3 + trivy-adapter v0.35.1 (cherry-picked in 2.15.0
    rc2 after a Trivy supply-chain incident, PR #22911 / #22929). If running
    a custom Trivy/Trivy-adapter image override, re-verify it builds against
    the new adapter API. Known issue at GA: proxy-cache projects to Docker
    Hub broken — fixed in 2.15.1 + chart 1.19.1.
  - Pull-through cache **replaced by proxy cache** (PR #22766). Any
    operator-side automation that distinguished "pull-through" vs
    "proxy-cache" surface needs to collapse onto proxy-cache only.
  - Cosign **v3 bundle signature format** is now the supported shape (PR
    #22628). Cosign v2 signatures continue to verify; downstream signing
    pipelines staying on v2 keep working but should plan the bump.
  - Base image moved to `goharbor/photon:5.0` (2.15.1, PR #23180) — any
    CVE-allowlist that named photon 4 packages needs refresh.
- **CRD migrations:** none (Harbor has no CRDs).
- **Upgrade ordering:** DB-schema migration runs as part of the standard
  chart `helm upgrade` (PR #22788 adds 2.15.0 migration). PostgreSQL major
  bumps are out of scope here — the chart bundles its own PG. **Take a
  snapshot of the registry DB PVC before upgrading**; failed migrations on
  2.15 leak schema state that requires manual SQL to roll back.
- **Deprecations:** replication adapter **allowlist** introduced in 2.14
  still in force — `gitlab` and `gcr` replication endpoints removed
  upstream (PR #22298, #22309). Operators still on those endpoint types
  must migrate before bumping.
- **Notable:**
  - PDBs now installed automatically when `replica > 1` (chart 1.19, PR
    #1509). Existing manually-managed PDBs will collide — delete them or
    set `podDisruptionBudget.enabled: false`.
  - HTTPRoute (Gateway API) support landed in chart 1.18 and stabilised in
    1.19 — `parentRefs` value-shape fix in 1.19.0 (PR #2256). Switching
    from Ingress to HTTPRoute is a one-way change to the values file; not
    auto-migrated.
  - Cosign keyless signing now applied to Harbor release artifacts (PR
    #22578); air-gapped operators mirroring tarballs should also mirror
    `.sigstore.json` assets if they verify signatures downstream.
  - `pprof` endpoint exposed on core (PR #22005) — NetworkPolicy should
    block external access if cluster ingress is permissive.

## 2.14 — chart 1.18.x (1.18.0 → 1.18.4)

- **k8s floor:** **tested on 1.32 – 1.34** (matrix bumped from `1.29/1.30/1.31`
  to `1.32/1.33/1.34` in harbor-helm PR #2238, cherry-picked into 1.18 line).
  The published support matrix table in README still shows the older
  `1.32.8/1.33.4/1.34.0` numbers for 1.18 — those are correct.
- **Breaking:**
  - **Replication adapter allowlist** introduced (PR #22198) — only
    actively-supported adapters are loadable. Replication policies pointing
    at unlisted adapter types fail at policy-load time, not silently. Audit
    `/api/v2.0/replication/adapters` before bumping. **GitLab replication
    removed entirely** (PR #22298); operators using GitLab as a replication
    target must rebuild that pipeline outside Harbor.
  - **GCR replication removed** (PR #22309) — upstream GCR account no
    longer maintained. Migrate to Artifact Registry adapter before
    upgrading.
  - Single Active Replication enforces serialized runs per policy. Any
    operator-side concurrency assumption (e.g. parallel replication for
    throughput) breaks silently — replication policies now queue.
- **CRD migrations:** none.
- **Upgrade ordering:** DB-schema migration script for 2.14 added in PR
  #22247; runs in the standard chart upgrade path. Snapshot the registry
  DB PVC first.
- **Deprecations:** none formally announced in 2.14 release notes beyond
  the adapter-allowlist tightening.
- **Notable:**
  - HTTPRoute (Gateway API) support added in chart 1.18 (PR #2175);
    requires Gateway API CRDs ≥ v1.0.0 installed cluster-side. Not the
    chart's job to install them.
  - Dual-stack service support (PR #2226).
  - CNAI raw model format support (PR #22040) — only matters if Harbor is
    being used as an AI model registry; otherwise no compat impact.

## 2.13 — chart 1.17.x (1.17.0 → 1.17.4)

- **k8s floor:** **tested on 1.29 – 1.31** (chart 1.17 integration matrix:
  `v1.29.8, v1.30.4, v1.31.1`).
- **Breaking:**
  - **CSRF key generation changed** (PR #21154) — sessions issued by
    pre-2.13 cores are invalidated. Plan a maintenance window; expect
    re-logins. OIDC tokens unaffected.
  - **`with_signature` field removed** (PR #21420) from artifact APIs.
    External clients reading the artifact list response shape break if
    they relied on that field. Cosign signature presence is now derived
    from accessory artifacts.
  - **robotV1 removed from the codebase** (PR #20991). Any robot account
    still on the v1 token shape stops authenticating. Operators must
    rotate to robotV2 before upgrading.
  - Project maintainer/developer/guest roles no longer have permission to
    list project logs (issue #22037) — UI feature change, but RBAC-aware
    automation may break.
- **CRD migrations:** none.
- **Upgrade ordering:**
  - Redis TLS support is *new* in 2.13. If pointing at an external Redis
    with TLS, **chart 1.17.0 has a known config-render bug** (Harbor
    issue #21913) — TLS config not propagated to the registry component.
    Upgrade to chart **1.17.3 or later** before enabling external Redis
    TLS. Internal Redis unaffected.
  - DB-schema migration script for 2.13 in PR #21680; standard chart
    upgrade path.
- **Deprecations:** robotV1 removed (see above); no other formal
  deprecations.
- **Notable:**
  - OIDC PKCE support (PR #21702) — recommended to flip on after upgrade
    if the IdP supports it; old non-PKCE flow continues to work.
  - OIDC logout flow added (PR #21718). If the operator's IdP was
    configured with a back-channel-logout endpoint, this now actually
    fires.
  - CNAI integration GA — same caveat as 2.14: only matters if used as an
    AI model registry.
