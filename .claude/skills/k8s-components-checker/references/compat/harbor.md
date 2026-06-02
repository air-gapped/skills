# harbor — compat (sifted from release_notes)

- **Primary source:** https://github.com/goharbor/harbor/releases
- **Secondary sources:** https://github.com/goharbor/harbor-helm (chart → app pinning, k8s test matrix), https://goharbor.io/docs/
- **Truth source type:** `release_notes`
- **Axis type:** `single`
- **min_tracked_version:** 2.11
- **Last sifted:** 2026-06-02
- **Last release-verified:** 2026-06-02
- **2026-05-31 release-verified (gh):** enumerating `goharbor/harbor`
  non-prerelease tags (no version named) returns **`v2.15.1` / `v2.15.0` as real,
  higher releases** alongside the maintained **2.14 line (`v2.14.4`)**.
  `releases/latest` = **v2.14.4** is *recency, not rank* — Harbor keeps the
  "Latest" flag on the 2.14 maintenance line while 2.15 is the newer feature line
  (a 2.14 patch published after 2.15.x). **The prior banner here ("2.15 NOT
  released — the list query was contamination") was WRONG** and is corrected:
  2.15.x is real. Both 2.14 and 2.15 are tested only to **k8s 1.34** (§§ below) —
  so neither adds 1.35. See `references/version-verification.md` § Three
  orthogonal failure modes (#2 `releases/latest` ≠ highest version).

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

## 2.15 — chart 1.19.x  (RELEASED; latest patch v2.15.1 — gh-enumerated 2026-05-31. `releases/latest` stays v2.14.4 = recency, not rank. Tested k8s 1.32–1.34 — does NOT add 1.35.)

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

## 2.12 — chart 1.16.x (1.16.0 → 1.16.4; chart→app +3 offset: 1.16.x → 2.12.x)

- **k8s floor:** **tested on 1.29 – 1.31** (chart 1.16.4 integration matrix:
  `v1.29.8, v1.30.4, v1.31.1`). README at chart tag v1.16.4 still has only the
  generic "Kubernetes cluster 1.20+" line (the per-version matrix table from
  harbor-helm PR #2241 landed in the 1.17+ era) — trust the integration matrix,
  not the README.
- **Breaking:** none that bites on the minor crossing. The 2.13 forward
  hazards (robotV1 removal, CSRF-key regeneration, `with_signature` removal)
  are NOT yet present in 2.12 — they land at 2.13. An operator migrating
  2.12 → 2.13+ must clear all three then (see § 2.13).
- **CRD migrations:** none (Harbor has no CRDs).
- **Upgrade ordering:** DB-schema migration runs in the standard chart
  `helm upgrade` (prepare/migration script for 2.12.0 in PR #21022). The robot
  account expansion changes the robot creator DB schema (PR #20918). **Snapshot
  the registry DB PVC before upgrading** — a failed 2.12 migration leaks schema
  state that needs manual SQL to roll back.
- **Deprecations:** none formally announced in the 2.12 release notes. The
  replication-adapter **allowlist** that removes `gitlab`/`gcr` does NOT exist
  yet at 2.12 — it is introduced at 2.14 (see § 2.14); operators on those
  endpoint types are still fine on 2.12 but must migrate before crossing to
  2.14+.
- **Notable:**
  - Enhanced robot accounts (full-access + creator + audit-logging, PR #20754 /
    #20843 / #20846 / #20918) — robot token shape stays robotV2; no auth break
    at 2.12, but this is the robotV2 baseline that 2.13's robotV1 removal
    assumes.
  - Proxy-cache adapters extended: ACR / ACR EE (PR #19658) and Alibaba ACR
    proxy-cache (PR #19692). Net-new adapters only; no existing adapter removed.
  - 2.12 line ceiling is v2.12.4. As of the current 2.15/2.14 maintenance
    window, the 2.12 line no longer receives patches — treat as a
    migration-source EOL line, not an upgrade target.

## 2.11 — chart 1.15.x (1.15.0 → 1.15.2; chart→app +3 offset: 1.15.x → 2.11.x)

- **k8s floor:** **tested on 1.23 – 1.25** (chart 1.15.2 integration matrix:
  `v1.23.13, v1.24.7, v1.25.3`). README at chart tag v1.15.2 only carries the
  generic "Kubernetes cluster 1.20+" line — trust the integration matrix. Note
  the large jump from this 1.23–1.25 window to 1.29–1.31 at the very next chart
  minor (1.16 / app 2.12): a cluster left on a 2.11-era k8s minor is far below
  the 2.12 test floor and must move k8s minors in step with the Harbor bump.
- **Breaking:**
  - **PostgreSQL bumped 14 → 15** (PR #19789). The chart bundles its own
    Postgres; the 2.11 upgrade migrates the bundled DB engine from PG14 to
    PG15. This is a one-way data-directory upgrade — an external/managed
    Postgres must be on 15 (or the operator must run the PG14→15 dump/restore)
    before/with the Harbor 2.11 upgrade. **Snapshot the DB PVC first**; a
    half-completed PG major upgrade is not cleanly reversible.
- **CRD migrations:** none.
- **Upgrade ordering:** DB-schema migration runs in the standard chart upgrade
  (prepare/migration script for 2.11.0 in PR #20315). SBOM support adds a new
  `sbom_report` table (PR #20473 / #20482) and separates the SBOM execution
  vendor type from `image_scan` (PR #20504); the SBOM accessory mediatype was
  renamed `harbor.sbom` → `sbom.harbor` (PR #20359). Combined with the PG14→15
  bump above, snapshot the registry DB PVC before upgrading.
- **Deprecations:** none formally announced beyond the dependency bumps. The
  replication-adapter allowlist (gitlab/gcr removal) is still 2.14; robotV1 /
  `with_signature` / CSRF-key changes are still 2.13 — none apply at 2.11.
- **Notable:**
  - OCI Distribution Spec **v1.1.0** fully supported, and Cosign adopted with
    OCI-spec 1.1 (PR #20245). **Known issue #20412:** an artifact replicated to
    a destination Harbor carries only one signature when signed by legacy
    cosign — sign with oci-1.1 mode (cosign v2.2.1+) to replicate multiple
    signatures. Matters for any cross-Harbor replication of signed images.
  - **Known issue #20691 (LDAP):** LDAP servers offering only old
    `TLS_RSA_*` cipher suites fail the handshake on 2.11 (Go 1.22 dropped RSA
    key exchange by default). Workaround: set `GODEBUG="tlsrsakex=1"` on the
    core env and restart. Verdict-relevant for LDAP-auth deployments.
  - **Known issue #20565:** SBOM generation returns HTTP 404 behind an
    external reverse proxy in 2.11.0 — verify SBOM-on-push works through your
    ingress before relying on it.
  - 2.11 line ceiling is v2.11.2 (the line ended at v2.11.2). Well below the
    current 2.15/2.14 maintenance window — treat as a migration-source EOL
    line, not an upgrade target.
