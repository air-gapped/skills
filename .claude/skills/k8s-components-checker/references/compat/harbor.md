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
- **2026-06-11 lab-verified (helm-managed):** 2.14.0 → 2.15.1 (chart
  1.18.0 → 1.19.1) upgraded clean on k8s 1.34.8/RKE2; the SAME install earlier
  jumped **2.11.1 → 2.14.0 DIRECT** (three minors, 2025-12-09) and ran 6 months
  without issue. See § Multi-minor upgrade path below, plus the lab-verified
  annotations under § 2.15 (incl. a PDB-claim CORRECTION).

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

## Multi-minor upgrade path 2.11 → 2.15 (lab-verified 2026-06-11)

For operators still on 2.11.x planning the jump to the 2.15 line.

- **Official span:** the upgrade guide for the current version covers
  "migration from v2.11.0 and later to the current version"
  (goharbor/website `docs/administration/upgrade/_index.md`) — 2.11.x → 2.15.x
  is inside the documented window, no forced intermediate stop.
- **No rollback:** the Helm upgrade doc (`helm-upgrade.md`) states the DB
  schema "cannot be downgraded automatically, so the `helm rollback` is not
  supported", and migration downtime "cannot be avoid[ed]". Recovery from a
  failed hop is DB-restore only — the pre-upgrade DB snapshot is the whole
  rollback plan.
- **Lab data point A — 2.11.1 → 2.14.0 DIRECT (chart 1.15.1 → 1.18.0,
  2025-12-09, RKE2, external Zalando/Spilo PG, external Redis sentinel, S3/Ceph
  RGW registry storage):** three-minor hop in ONE `helm upgrade`. The schema
  migrations are sequential golang-migrate steps that the core pod replays on
  startup, so skipped minors' migrations all run in the single hop. Ran clean;
  stable for 6 months after. CAVEAT: every one-way item from 2.12/2.13/2.14
  lands AT ONCE in such a hop — pre-clear the § 2.13 set (robotV1 rotation,
  `with_signature` consumers, CSRF re-login window) and the § 2.14 set
  (replication-adapter allowlist, gitlab/gcr adapter removal) BEFORE it.
- **Adapter-allowlist nuance (verified on 2.14):** endpoints that point at
  gcr.io / registry.gitlab.com using the GENERIC "Docker Registry" provider
  survive the 2.14 allowlist and stay Healthy — only the dedicated `gcr` /
  `gitlab` ADAPTER types were removed. Audit `/api/v2.0/replication/adapters`
  + the provider column under Registries, not just endpoint URLs.
- **Lab data point B — 2.14.0 → 2.15.1 (chart 1.18.0 → 1.19.1, 2026-06-11,
  k8s 1.34.8):** schema migration `171/u 2.14.1_schema` + `180/u 2.15.0_schema`
  ran inside core startup, sub-second each on a small DB (~50 GiB registry, 24
  repos); with `replicas: 2` both cores race the migration and the loser
  no-ops. Full rollout settled in ~2 min. Proxy-cache project → Docker Hub
  verified working on 2.15.1 (manifest pull through `<harbor>/docker.io/...`),
  including decryption of the stored upstream credential.
- **Chart-side secret churn (any version, helm-managed installs):** the chart
  REGENERATES `CSRF_KEY`, `JOBSERVICE_SECRET`, `REGISTRY_HTTP_SECRET`, the
  registry htpasswd salt, core `secret`, and the token-service CA on EVERY
  `helm upgrade` (no `lookup`), unless pinned via the `existingSecret*` values.
  Consequence: every chart upgrade logs out active UI sessions — so 2.13's
  one-time CSRF-key regeneration is a non-event for chart-managed installs
  (they re-login every upgrade anyway).
- **Rotating `secretKey` (lab-verified the hard way, 2026-06-11):** the 16-char
  `secretKey` AES-encrypts values at rest in the DB. Rotating it invalidates
  ALL of them at once: registry/replication endpoint credentials, the **OIDC
  provider client secret** (browser SSO breaks at token exchange — recover by
  logging in as the LOCAL `admin`, whose password is hashed not encrypted, and
  re-entering it under Administration→Configuration), **every user's OIDC CLI
  secret** ("failed to verify the secret: secret mismatch" in core logs;
  users reset in profile + re-do `docker login`), and the LDAP search password
  where applicable. Check `/api/v2.0/systeminfo` `auth_mode` BEFORE rotating
  and enumerate the re-entry list up front. The chart consumes a rotated key
  cleanly via `existingSecretSecretKey` (secret key name `secretKey`).
  Also verified-safe `existingSecret` paths at chart 1.19.x: S3
  (`REGISTRY_STORAGE_S3_*` envFrom), external DB (`key: password` secretKeyRef
  — an external Zalando-operator credential secret can be referenced directly;
  core AND exporter consume it). NOT safe: `redis.external.existingSecret` —
  render-time `lookup` embeds the password into 5 configmap URLs (open issues
  #2291/#2207; maintainer: "not supported with helm template") — keep the
  redis password inline in values until upstream reworks it.
- **Benign startup noise after the bump (don't chase these):** jobservice
  `[ERROR] no task found for execution: SYSTEM_ARTIFACT_CLEANUP:<id>` =
  boot-time scheduler sync against a stale execution row, stops after startup;
  core `find: '/etc/harbor/ssl': No such file or directory` + `init global
  config instance failed ... app.conf` = normal when `internalTLS` is disabled.

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
  - **Trivy supply-chain incident fallout (2026-03-01, verified 2026-06-11)
    — matters to ALL Harbor lines, especially air-gapped mirrors:** all
    `aquasecurity/trivy` GitHub Releases v0.27.0–v0.69.1 were PERMANENTLY
    DELETED in the attack (Harbor PR #22896/#22911); v0.69.2 was the
    emergency re-release. Consequences: (a) any mirror/build pipeline that
    fetches trivy RELEASE TARBALLS by version URL 404s for every pre-incident
    version — including the engines Harbor ≤2.14 pins (e.g. 2.11.1 pins
    v0.54.1 via `releases/download/...` in its Makefile) — so EOL-line
    adapter images can no longer be rebuilt from upstream artifacts;
    (b) trivy-db OCI publishing had outages ~2026-03-23 (trivy-db #651) and
    2026-04-16→20 (trivy-db #658/#660, disabled build workflow) but RESUMED —
    both `ghcr.io/aquasecurity/trivy-db:2` and `mirror.gcr.io/aquasec/trivy-db:2`
    verified freshly published 2026-06-11; (c) DB schema is STILL v2 — old
    engines (v0.54.x in Harbor 2.11) consume the current DB fine, so a stale
    scanner DB on an old Harbor means the operator's MIRROR PIPELINE broke
    (likely during the March/April outages or by fetching deleted release
    assets), not an upstream compat break. Re-verify checksums of anything
    mirrored around the incident window. Newer trivy also prefers
    `mirror.gcr.io/aquasec/trivy-db:2` as first DB source; and from trivy
    v0.72.0 release packaging changes again (no arch-specific image tags,
    APT `generic` dist only — discussions #10824/#10819) — re-check mirror
    automation that scrapes those.
  - **Air-gap Trivy-DB mirroring pattern (verified against chart 1.15.1 +
    adapter v0.31.4 source, 2026-06-11):** Harbor itself stores the trivy-db
    OCI artifact fine (`skopeo copy docker://ghcr.io/aquasecurity/trivy-db:2
    docker://<harbor>/mirror/trivy-db:2` into a PUBLIC project; tag is
    mutable — exempt it from immutability rules, and let untagged-artifact
    GC reclaim superseded builds). Tag inventory (verified live): trivy-db
    has ONLY `1` (dead v1 schema), `2` (live, ~100 MiB layer, re-pushed
    every build) and `latest` (parallel push of the same build — do NOT
    mirror it; it would jump schema on a future v3). trivy-java-db has only
    `1` (its live schema, ~880 MiB layer — needed for JAR/WAR scanning;
    skipping it via `skipJavaDBUpdate: true` makes Java-image scans
    degrade/fail, so mirror it too rather than turning it off). For
    `skopeo sync` automation use EXPLICIT tags — semver rules coerce bare
    `1`/`2` to `1.0.0`/`2.0.0` (dry-run-verified), so a `>= 1.0.0`
    constraint silently mirrors the dead v1 schema forever and would
    auto-pull an incompatible future v3:

    ```yaml
    ghcr.io:
      images:
        aquasecurity/trivy-db: ["2"]
        aquasecurity/trivy-java-db: ["1"]
    ```

    Pointing the scanner at it: chart ≥1.18 has first-class `trivy.dbRepository` /
    `trivy.javaDBRepository` values; on OLDER charts (1.15.x) use
    `trivy.extraEnvVars` with `TRIVY_DB_REPOSITORY` /
    `TRIVY_JAVA_DB_REPOSITORY` — the adapter passes its full env to the
    trivy subprocess (`cmd.Env = ambassador.Environ()` in wrapper.go), and
    trivy reads flags from `TRIVY_*` envs. Keep `skipUpdate: false` AND
    `skipJavaDBUpdate: false` (trivy now self-refreshes BOTH DBs from the
    internal repos — re-enable the java one if it was disabled as a
    workaround for failing downloads) + `offlineScan: true`. Tag
    semantics (verified in trivy SOURCE at tag v0.54.1,
    `pkg/flag/db_flags.go` ToOptions): the value is parsed as a full OCI
    reference — an EXPLICIT tag is respected as-is; if NO tag is given the
    schema version (`:2`) is appended "for backward compatibility". So both
    `<harbor>/<proj>/trivy-db` and `<harbor>/<proj>/trivy-db:2` work on
    v0.54.1+. Multi-segment repo paths (e.g. a per-upstream-registry project
    layout `<harbor>/ghcr.io/aquasecurity/trivy-db:2`) are fine — parsing is
    go-containerregistry `name.ParseReference`, and Harbor allows nested
    repository paths within a project. The adapter (verified v0.31.4
    `prepareScanCmd`) passes NO `--db-repository` CLI flag, so the env var is
    never overridden. INTERNAL-CA mirrors: set top-level
    `caBundleSecretName` (present since ≤1.15.x; secret key `ca.crt`) — the
    chart mounts it at `/harbor_cust_cert/` into core/jobservice/registry/
    trivy and every photon image's entrypoint appends it to the system
    trust bundle (`install_cert.sh`), so trivy's DB pull verifies against
    the internal CA (also how CORE trusts internal replication/proxy-cache
    endpoints — the alternative is per-endpoint "Verify Remote Cert" off).
    `trivy.insecure: true` exists but disables TLS verify for EVERYTHING
    trivy pulls — prefer the CA bundle. This supersedes hand-rolled
    curl-the-blob-into-the-container DB injection (which is usually a
    workaround for exactly this missing CA trust).
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
  - PDB support added per component (chart 1.19, PR #1509). **CORRECTION
    (2026-06-11, verified against the chart 1.19.1 default render): PDBs are
    OPT-IN — every `podDisruptionBudget` block defaults to `enabled: false`,
    nothing is auto-installed at `replica > 1`.** The prior claim here
    ("installed automatically … will collide") was wrong: no collision risk
    unless you enable them. Enabled with `minAvailable: 1` on replicas=2
    components they render and apply clean (lab-verified).
  - Chart 1.19 default image refs gained an explicit `docker.io/` prefix
    (`goharbor/harbor-core` → `docker.io/goharbor/harbor-core`). Air-gap
    mirror lists and containerd/registry rewrite rules that match the bare
    `goharbor/...` form must be updated for the new canonical refs.
  - New chart knobs: per-component liveness/readiness probe tuning exposed,
    and `jobservice.registryHttpClientTimeout` (default 30, rendered as
    `REGISTRY_HTTP_CLIENT_TIMEOUT` minutes).
  - 2.15 core now logs an explicit WARNING at startup: "Admin password from
    config (HARBOR_ADMIN_PASSWORD) ignored: password already exists in
    database." — confirms `harborAdminPassword` is a first-install seed only;
    on upgrades it is dead config.
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
