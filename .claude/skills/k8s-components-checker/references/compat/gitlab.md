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
- **Last sifted:** 2026-07-21 (re-probed: latest app tag **v19.2.0**, still within the chart-10.x / GitLab-19.x row — no chart-minor shift)

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

- **k8s floor:** 1.33 – 1.35 (`1.32` deprecated, `1.31` and below unsupported on chart 10.x; GitLab 19.0 requires app ≥ 18.9 on k8s 1.35, ≥ 18.6 on 1.34, ≥ 18.1 on 1.33).
- **Breaking:**
  - **Bundled Redis chart dropped.** Operator must provide external Redis 7.2+ (or Valkey 7.2+). No more `helm upgrade` rolling out a fresh in-cluster Redis.
  - **Bundled PostgreSQL chart dropped.** Operator must provide external Postgres ≥ 17.x. Single-node Linux package installs trigger auto-upgrade to PG 17.7; chart-based installs do NOT — the operator owns the PG upgrade.
  - **Bundled MinIO chart dropped.** Object storage is now BYO (S3, GCS, Azure, Ceph RGW, anything S3-compatible). Migrate before upgrade or the chart refuses.
  - **Spamcheck subchart removed.**
  - **Mattermost bundled removal** (chart-side; operator-tier impact unless Mattermost was actually deployed).
  - **NGINX Ingress support discontinued** (medium impact). Chart moves to Envoy Gateway v1.8.0 + Gateway API. Operator must migrate Ingress → Gateway API or hold on 9.x.
  - **Redis 6 removed** (app-tier). Redis ≥ 7.2 required.
  - **PostgreSQL 16 support ended.** PG 17.x is min AND max for app 19.x.
  - **Heroku builder image retired** (CI-tier — Auto DevOps users only).
- **CRD migrations:** N/A. GitLab uses standard `Deployment` + `StatefulSet`; no custom CRDs in scope.
- **Upgrade ordering:**
  1. **Backup is mandatory** (`/charts/backup-restore/`). Chart docs phrase as MUST.
  2. **Single-minor steps.** Do not jump 9.x → 10.x without landing on chart 9.11.z first. The chart's pre-migration jobs assume schema continuity.
  3. **Required app stops** between 18.x and 19.x: 18.2 → 18.5 → 18.8 → 18.11 → 19.x. Each stop runs background migrations; let them drain (Sidekiq queue length on `database_background_migration_*`) before the next bump.
  4. **Zero-downtime sequence inside one minor bump** (per upgrade doc): pause Webservice + Sidekiq → `helm upgrade` skipping post-deploy migrations → wait for pre-migrations → resume Sidekiq → resume Webservice → final `helm upgrade` for post-deploy migrations.
  5. **Pre-bump 9.x → 10.x checklist:** external PG ≥ 17, external Redis ≥ 7.2, external object storage configured, Gateway API CRDs installed, NGINX Ingress removed from `values.yaml`. Skipping any one of these breaks the install.
  6. **`db-migrate` job timeout:** default 600s. Bump for large datasets — past failure mode is the job OOM/timeouts mid-migration, leaving partial schema.
- **Deprecations:** Ubuntu 20.04 package support removed. SUSE distros support ending. Bitbucket Cloud import API changed (CI-tier). Slack slash command removed. Spamcheck removed. Heroku builder retired.
- **Notable:**
  - Container Registry to v4.40.0-gitlab. Registry metadata DB migration must have completed in 17.x — if skipped, the 19.x registry refuses to start. Verify before bumping.
  - Cert-manager **Gateway API enabled by default** (the chart's bundled cert-manager values now target Gateway API resources, not Ingress).
  - Gitaly Cluster (the new Raft-based replacement for Praefect) is the supported path; legacy Praefect is on borrowed time. Not removed in 19.0 but plan the migration.
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
- **Ingress posture** — NGINX still serving in 10.x = stop. Gateway API + Envoy Gateway is the only supported path on 10.x.
- **Sidekiq concurrency cap** — chart 9.9+ sets `GITLAB_SIDEKIQ_MAX_REPLICAS` by default; unset or `0` on non-KEDA deployments.
- **Background migrations drained** — pre any minor jump.
- **Backup taken** — chart docs phrase as MUST.

## Out of scope

- Geo (single-region deployment).
- Prime/EE-tier features (operator runs EE binary as CE; no license attached).
- GitLab Pages routing changes (not deployed in this cluster).
- Container Registry GCS migration (cluster uses S3-compatible object storage, not GCS).
