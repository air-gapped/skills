# gitlab — compat (sifted from published_matrix)

- **Primary source:** https://docs.gitlab.com/charts/installation/cloud/
- **Secondary sources:**
  - https://docs.gitlab.com/charts/installation/version_mappings/ (chart → app)
  - https://docs.gitlab.com/charts/installation/upgrade/ (upgrade ordering)
  - https://docs.gitlab.com/update/upgrade_paths/ (required app stops)
  - https://docs.gitlab.com/update/versions/gitlab_19_changes/
  - https://docs.gitlab.com/update/versions/gitlab_18_changes/
  - https://docs.gitlab.com/update/versions/gitlab_17_changes/
  - https://gitlab.com/gitlab-org/charts/gitlab/-/raw/master/CHANGELOG.md
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 8.11      # chart minors: current (10.x) + prior 2 (9.x, 8.x)
- **Last sifted:** 2026-11-25 — chart ceiling now **v10.6.1 / app v19.6.1** (2026-11-19; 10.6.0 2026-11-18); cloud-install matrix at v10.6.1 unchanged (1.35–1.37 supported, 1.37 needs GitLab ≥ 19.5) plus a new hard install floor of k8s 1.30 from chart 10.6.0; PostgreSQL 17.x–18.x and Redis ≥ 7.0 / Valkey 7.2 for 19.x re-read at master; required stops 19.2 / 19.5 / 19.8 / 19.11 added; chart CHANGELOG 10.5.3–10.6.1 and 10.6 / 10.4 / 10.3 upgrade notes read; GitLab 19.2–19.6 upgrade notes read.
- **Last release-verified:** 2026-11-25 — newest per line **`v10.6.1`**, `v10.5.9`, `v10.4.11`, `v10.3.11`, `v10.2.10`, `v10.1.10`, `v10.0.11`, `v9.11.16` (GitLab API tags + `compat.py sync` drift); chart → app per tag message: `10.6.1` → 19.6.1, `10.5.9` → 19.5.8, `10.4.11` → 19.4.10, `10.3.11` → 19.3.9, `10.2.10` → 19.2.10, `10.1.10` → 19.1.10, `10.0.11` → 19.0.11, `9.11.16` → 18.11.14 (pattern chart `10.Y.Z` → app `19.Y.Z` no longer holds for patch Z on 10.3–10.5; use the tag message or `version_mappings.md`).

## Reading the file

GitLab ships two parallel version lines: the **Helm chart** (`gitlab/gitlab` on
gitlab.com) and the **GitLab application** it deploys. Chart minors map to app
minors deterministically:

| Chart minor | GitLab app minor |
|---|---|
| 10.x | 19.x |
| 9.x  | 18.x |
| 8.x  | 17.x |

Compat verdicts cite the **chart** version (that's what the operator picks at
`helm upgrade` time). The k8s floor below is from the cloud-install matrix,
which is authoritative for the chart even when GitLab support docs lag.

**Community-edition note.** The operator runs the EE binary as CE (no license
attached). Treat as one product. EE-tier feature deprecations (security
scanners, value-stream analytics dashboards, etc.) are out of scope and not
sifted here.

## 10.x  (GitLab 19.x — current chart minor)

- **k8s floor (re-read 2026-11-25 at chart v10.6.1): 1.35 – 1.37 on chart 10.5+ / GitLab 19.5+; 1.35 – 1.36 on chart ≤ 10.4** — 1.37 is supported only from GitLab 19.5 (chart 10.5.0), `1.34` deprecated, `1.33` and below unsupported. Min GitLab per minor: **19.5 on k8s 1.37**, 19.3 on 1.36, 18.9 on 1.35, 18.6 on 1.34 (deprecated), 18.1 on 1.33 (unsupported). **Hard install floor from chart 10.6.0: k8s 1.30** — `helm install`/`helm upgrade` fail on older clusters (webservice and registry `preStop` use the Kubernetes `sleep` action, gated on 1.30+). The window is a *live rolling* matrix keyed to the current release; re-read it every pass. Current chart **v10.6.1 / appVersion v19.6.1** (2026-11-19).
- **Caveat on the older rows below:** that same page shows only the current window, so the chart-9.x/8.x floors recorded here can no longer be re-verified against it. They are unconfirmed, not contradicted — do not silently "refresh" them from a page that no longer carries them.
- **Breaking:**
  - **Bundled Redis chart dropped.** Operator must provide external **Redis 7.0+ or Valkey 7.2** — 7.2 is *recommended*, not the floor (corrected 2026-09-15; a vendor-maintained 7.0/7.1, e.g. ElastiCache 7.1, is explicitly acceptable). No more `helm upgrade` rolling out a fresh in-cluster Redis.
  - **Bundled PostgreSQL chart dropped.** Operator must provide external Postgres ≥ 17.x. Single-node Linux package installs trigger auto-upgrade to PG 17.7; chart-based installs do NOT — the operator owns the PG upgrade.
  - **Bundled MinIO chart dropped.** Object storage is now BYO (S3, GCS, Azure, Ceph RGW, anything S3-compatible). Migrate before upgrade or the chart refuses.
  - **Spamcheck subchart removed.**
  - **Mattermost bundled removal** (chart-side; operator-tier impact unless Mattermost was actually deployed).
  - **NGINX Ingress is NOT discontinued — corrected 2026-09-15.** Envoy Gateway + Gateway API became the **default** in 19.0; NGINX reached end-of-life *as the default* in March 2026 but remains available as an opt-in conditional subchart, and GitLab's own 19.0 changes doc says it stays *"until its proposed removal in GitLab 20.0"*. Verified in `Chart.yaml` at both v10.0.0 and v10.3.2: `- name: nginx-ingress` with `condition: nginx-ingress.enabled` is still a live dependency. **Migrating to Gateway API is not forced on 10.x** — plan it before 20.0, do not treat it as a 10.x upgrade blocker. Bundled Envoy Gateway is now **v1.9.1** (v1.9.0 at chart 10.3.x, v1.8.0 at the 19.0 launch tag).
  - **Redis 6 removed** (app-tier). Floor is **Redis 7.0** (or Valkey 7.2); 7.2 is recommended, not required.
  - **PostgreSQL 16 support ended.** App 19.x accepts PG **17.x – 18.x** (`doc/install/requirements.md` at master, max raised to 18.x on 2026-10-01, commit `4dc318dd`). App 18.x accepts 16.5 – 17.x, so **PG 17 is the only major valid on both sides of the 18.x → 19.x hop** — move PG to 17 before the chart 9.x → 10.x bump; PG 18 only after landing on 19.x.
  - **Heroku builder image retired** (CI-tier — Auto DevOps users only).
- **CRD migrations:** N/A. GitLab uses standard `Deployment` + `StatefulSet`; no custom CRDs in scope.
- **Upgrade ordering:**
  1. **Backup is mandatory** (`/charts/backup-restore/`). Chart docs phrase as MUST.
  2. **Single-minor steps.** Do not jump 9.x → 10.x without landing on chart 9.11.z first. The chart's pre-migration jobs assume schema continuity.
  3. **Required app stops** between 18.x and 19.x: 18.2 → 18.5 → 18.8 → 18.11 → 19.x; within 19.x: **19.2 → 19.5 → 19.8 → 19.11** (target the latest patch of each stop). Each stop runs background migrations; let them drain (Sidekiq queue length on `database_background_migration_*`) before the next bump.
  4. **Zero-downtime sequence inside one minor bump** (per upgrade doc): pause Webservice + Sidekiq → `helm upgrade` skipping post-deploy migrations → wait for pre-migrations → resume Sidekiq → resume Webservice → final `helm upgrade` for post-deploy migrations.
  5. **Pre-bump 9.x → 10.x checklist:** external PG 17 (not 18 — 18.x apps reject it), external Redis ≥ 7.0 (Valkey 7.2), external object storage configured. **Gateway API CRDs and removing NGINX are NOT required for 10.x** — Gateway API is the new default, NGINX stays opt-in until 20.0; do both before 20.0, not as a gate on this hop. Skipping any one of these breaks the install.
  6. **`db-migrate` job timeout:** default 600s. Bump for large datasets — past failure mode is the job OOM/timeouts mid-migration, leaving partial schema.
- **Deprecations:** Ubuntu 20.04 package support removed. SUSE distros support ending. Bitbucket Cloud import API changed (CI-tier). Slack slash command removed. Spamcheck removed. Heroku builder retired.
- **Notable:**
  - Container Registry to v4.40.0-gitlab. Registry metadata DB migration must have completed in 17.x — if skipped, the 19.x registry refuses to start. Verify before bumping.
  - Cert-manager **Gateway API enabled by default** (the chart's bundled cert-manager values now target Gateway API resources, not Ingress).
  - Gitaly Cluster (the new Raft-based replacement for Praefect) is the supported path; legacy Praefect is on borrowed time. Not removed in 19.0 but plan the migration.
  - **Chart 10.6.0 (2026-11-18) upgrade notes:** images supplied for `global.certificates.image` / `shared-secrets.selfsign.image` must ship `/scripts/bundle-certificates` and `/scripts/generate-certificates`; the registry init container renders `config.yml` with `gomplate` (custom `registry.init.image` must provide it; `{% %}` in registry values no longer evaluated; `delete.enabled` in the storage Secret now always honored); webservice/registry `preStop` hooks use the k8s `sleep` action (needs k8s ≥ 1.30; a replaced Webservice image needs PID 1 = Puma or a SIGINT-forwarding `tini`); the `configure` init containers are removed from every chart except registry (Pods need `fsGroup`; restart Pods after Secret changes; GitLab Shell reads host keys from `/etc/gitlab-ssh-host-keys`); the Praefect Service lost its Prometheus scrape annotations and its port is now `tcp-praefect` (was `grpc-praefect`); Ingress only accepts `networking.k8s.io/v1`. Bundled Envoy Gateway is **v1.10.0** → apply the Envoy Gateway v1.10.0 CRDs (`helm template … gateway-crds-helm --version v1.10.0 … | kubectl apply --server-side`) before `helm upgrade`; Helm never upgrades CRDs. 10.6.1 (2026-11-19) only sets the Envoy `drainTimeout` default to 240s.
  - **GitLab 19.6.0 – 19.6.1 (= chart 10.6.0 – 10.6.1) can fail the `DropAiEventsCounts` post-deploy migration** (`PG::DependentObjectsStillExist`, when detached `ai_events_counts` partitions exist); fixed in app **19.6.2**, no chart carrying it yet at the 2026-11-25 read. Wait for 19.6.2 or drop the detached partitions first (GitLab 19 upgrade notes carry the SQL). Helm-chart installs of GitLab Secrets Manager (OpenBao) must run the `gitlab:secrets_management:openbao:secrets_manager_policy:update` Rake task after 19.6.
  - **Chart 10.3.0+ needs new Envoy Gateway CRDs** (1.9.1 and Gateway API 1.6 CRDs; later charts need the CRDs of the bundled `gateway-helm` version): without them the upgrade fails on the GitLab Shell `TCPRoute` or the API server silently prunes `Host` header fields.
  - **Container registry `s3` driver is `s3_v2` (AWS SDK v2) since 19.0:** for S3-compatible backends (Ceph RGW, MinIO) `regionendpoint` must be a full URI with scheme; a bare hostname stops the registry starting.
  - **Chart 10.5.0 (2026-10-15):** KAS advertises `grpcs` to agents by default; toolbox backup CronJob defaults to `batch/v1` and HPAs to `autoscaling/v2`; Envoy Gateway v1.9.2, gateway-crds-helm v1.9.1, container-registry v4.42.0-gitlab. 10.5.1 / 10.4.3 / 10.3.7 (2026-10-20) carry no chart changes; 10.5.2 / 10.4.4 / 10.3.8 (2026-10-27) bump the bundled cert-manager to v1.21.3; 10.5.3 – 10.5.9, 10.4.5 – 10.4.11 and 10.3.9 – 10.3.11 (2026-10-28 – 11-19) carry only Envoy Gateway v1.9.3 (10.5.4 / 10.4.6 / 10.3.9) and gitlab-runner 0.94.3 (10.5.6) or nothing; 10.2.10 / 10.1.10 / 10.0.11 / 9.11.16 (2026-10-28/29) bump Envoy Gateway (v1.8.6 on 10.x, v1.7.5 on 9.11) and cert-manager to v1.21.3 (10.2) or v1.20.5 (10.1, 10.0, 9.11).
  - Envoy Gateway is the chart-native ingress now. The skill's verdict treats this as a separate ingress axis — flag it if Cilium Gateway API or another gateway is already in the cluster (conflict on `GatewayClass` and Listener ports).

## 9.x  (GitLab 18.x)

- **k8s floor:** 1.31 – 1.34 (matrix lists 18.1 on 1.33, 18.6 on 1.34; chart 9.x covers the 18.x app range; 1.32 deprecated on the *current* matrix).
- **Breaking:**
  - **PostgreSQL 14 removed.** Upgrade external PG to 16.5+ **before** moving to app 18.0. Chart 9.0 install refuses on PG 14.
  - **`git_data_dirs` legacy setting removed.** Gitaly storage must be in the new format. Operator-config change, not a chart change.
  - **Sidekiq concurrency limiter (18.9+).** Chart sets `GITLAB_SIDEKIQ_MAX_REPLICAS` by default → unexpected job throttling and Redis backlog on non-KEDA deployments. Workaround: set to `0` or feature-flag off. Open trap — flag this for any 9.9+ chart with KEDA absent.
  - **Auto PG 17.7 upgrade triggered by app 18.11** (Linux package single-node only). Chart deployments are NOT auto-upgraded — operator handles PG upgrade out-of-band.
- **CRD migrations:** N/A.
- **Upgrade ordering:**
  1. Same single-minor-step rule.
  2. **Required app stops** within 18.x: 18.2 → 18.5 → 18.8 → 18.11. Required stops from 17.x: see 8.x section.
  3. **PG 14 → 16.5+ migration before any chart 8.x → 9.x bump.** Mandatory.
  4. Background migrations must drain at each stop. The `gitlab-rails runner Gitlab::Database::BackgroundMigration::BatchedMigration.queued.count` check is the operator's gate.
  5. **Geo deployments:** out of scope here; the operator's cluster is single-region. Geo upgrade coordination is documented but ignored.
- **Deprecations:** SLES 12.5 deprecated in 18.9 (chart-irrelevant; OS-tier). Grafana removal (was on the way out in 17.x; chart-bundled Grafana already gone). NGINX Ingress on its way out (removed in 10.x — see above).
- **Notable:**
  - Gateway API HTTP→HTTPS redirect (9.10+) and Gateway API backend TLS (9.11+) — operator can start dual-stacking Ingress + Gateway here, easing the 10.x migration.
  - Container Registry v4.38.0-gitlab on chart 9.10. Registry metadata DB migration is **strongly recommended** in 18.x — required before 19.x.
  - Zoekt chart bumped to 3.11.0 (advanced search backend; mostly invisible to k8s-axis verdicts).
  - **`GITLAB_SIDEKIQ_MAX_REPLICAS` footgun** (above) — the most operator-visible 9.x regression. Worth a survey-time check on the chart values.

## 8.x  (GitLab 17.x)

- **k8s floor:** 1.29 – 1.32 (matrix listed `1.32` supported on 17.11+, deprecated as of the current sift; `1.31` was the floor add for chart 8.11).
- **Breaking:**
  - **PostgreSQL 13 binaries removed; PG 14 required** before any app 17.0 upgrade.
  - **Container Registry metadata DB migration introduced.** Mandatory in 17.x — if skipped, the 18.x → 19.x chain stalls at the registry. The 8.x chart series is when the operator must complete this. Verify with `registry database migrate status`.
  - **Legacy runner registration tokens disabled by default (17.0).** Migrate to the new token workflow before upgrading runners along with the chart.
  - **Bundled Grafana removed** (`gitlab.rb` `grafana[*]` keys must be unset before upgrading to 17.0; chart-side Grafana already gone earlier).
  - **OpenSSL 3 (17.7+):** TLS 1.2+ mandatory, RSA/DSA keys ≥ 2048-bit, cert chains require ≥ 112-bit security. Old internal CAs break.
  - **AWS SDK v2 default in 17.4+** for Workhorse object-storage uploads. v1 available via feature flag if needed.
  - **Gitaly storages can no longer share the same path** — config-level break.
- **CRD migrations:** N/A.
- **Upgrade ordering:**
  1. **Required app stops** within 17.x: 17.1.8 (only if large `ci_pipeline_messages` tables) → 17.3.7 → 17.5.5 → 17.8.7 → 17.11.7. Always target the latest patch at each stop (e.g. 17.11.7, not 17.11.0).
  2. **Git binary bumps within the series:** 17.1 needs Git 2.44, 17.3 needs 2.45, 17.4 needs 2.46, 17.7 needs 2.47. Chart-side this is the Gitaly image — bumps come with the chart bump, but Praefect deployments must coordinate.
  3. Pre-18.x checklist (= pre 9.x chart): PG 14 → 16.5+ done, Registry metadata DB migration done, OpenSSL 3 cert chain audited, Grafana keys removed from any `gitlab.rb`, runner registration migrated.
- **Deprecations:** Ubuntu 18.04 packages stopped (17.0 floor). KAS auto-config tightened in 17.8 (operator must set `OWN_PRIVATE_API_URL` explicitly in `gitlab_kas['env']` — Linux package; chart equivalent is `global.kas.privateApi.url`).
- **Notable:**
  - Chart 8.11 raised min Helm to **3.10**. Older Helm clients break on `lookup` template behavior.
  - Chart 8.11 added k8s 1.32 support.
  - Chart 8.11 bumped bundled NGINX Ingress to v1.11.5, Redis chart 17.x → 18.19.4, PG chart → 12.12.10 (bundled — all gone in chart 10.x).
  - New encryption secrets in 17.8 (`active_record_encryption_*`) must be **unified across multi-node deployments** before bumping past 17.8. Missing this corrupts encrypted columns on the next minor.

## Cross-version sanity checks (apply at survey time)

- **External datastore versions** — verify before any cross-major bump: PG (14 / 16.5+ / 17.x), Redis or Valkey (7.2+ from 19.x onward), object storage reachable.
- **Registry metadata DB migration status** — completed before 19.x.
- **Ingress posture** — Gateway API + Envoy Gateway is the default on 10.x; NGINX is opt-in until its removal in 20.0. Bundled Envoy Gateway CRDs must match the target chart (Helm never upgrades them).
- **Sidekiq concurrency cap** — chart 9.9+ sets `GITLAB_SIDEKIQ_MAX_REPLICAS` by default; unset or `0` on non-KEDA deployments.
- **Bundled cert-manager** (`installCertmanager: true`) — newest charts 9.11.16, 10.0.11 and 10.1.10 pin v1.20.5, 10.2.10 and 10.3.11+ pin v1.21.3: all at or above the 1.20.3 security floor (CVE-2026-62290, `compat/cert-manager.md` § 1.20.0). Older patches (9.11.15, 10.0.10, 10.1.9 and below: v1.20.2; 10.2.9: v1.21.0) are below it → `⚠ needs bump` to the newest patch of the line.
- **Background migrations drained** — pre any minor jump.
- **Backup taken** — chart docs phrase as MUST.

## Out of scope

- Geo (single-region deployment).
- Prime/EE-tier features (operator runs EE binary as CE; no license attached).
- GitLab Pages routing changes (not deployed in this cluster).
- Container Registry GCS migration (cluster uses S3-compatible object storage, not GCS).
