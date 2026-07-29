# zalando-postgres-operator — compat (sifted from release_notes)

- **Primary source:** https://github.com/zalando/postgres-operator/releases
- **Secondary sources:** https://github.com/zalando/spilo (image tag history; GitHub releases stop at 3.0-p1 in 2023 — newer Spilo tags live only on `ghcr.io/zalando/spilo-NN:X.Y-pZ` and are referenced from each operator release's "Default Spilo image" line)
- **Truth source type:** `release_notes`
- **Axis type:** `multi`        # (operator version → bundled Spilo image → bundled PostgreSQL majors)
- **min_tracked_version:** 1.13.0
- **Last sifted:** 2026-07-29 (**v2.0.0 (2026-07-27) + v2.0.1 (2026-07-29) released** — first releases since 2025-12; new major sifted below)
- **Last release-verified:** 2026-07-29 (full release listing enumerated via `gh api`; v2.0.0/v2.0.1 notes read in full)

The axis tuple `(operator, Spilo image, PG majors)` is the verdict-load-bearing
unit. The operator has a loose k8s floor (works on any currently-supported
upstream minor it has been built against — community CI runs against
recent k8s minors but Zalando does not publish a hard matrix), so the
verdict turns on the **Spilo image** (which PG major) and on whether
`kubernetes_use_configmaps` semantics have shifted under the operator.

Spilo image naming reads `ghcr.io/zalando/spilo-<PG_DEFAULT_MAJOR>:<X.Y>-p<Z>`.
The PG major in the image tag is the **default** primary major Spilo will
initdb with; the Patroni/Spilo bundle inside that image also ships several
older majors so `pg_upgrade` flows work.

## 2.0.1  (2026-07-29)

- **k8s floor:** unstated by upstream (as before); the release exists because k8s is deprecating the bare Endpoints API — see the configmaps flip under 2.0.0.
- **Bundled Spilo image:** `ghcr.io/zalando/spilo-17:4.1-p2` (default PG17)
- **Bundled PostgreSQL majors:** 14 – 18 (PG13 dropped, PG18 added at 2.0.0)
- **Breaking:** none beyond 2.0.0 — hotfix release.
- **CRD migrations:** fixes the 2.0.0 OperatorConfiguration CRD type mismatch that broke GitOps pipelines (diff/apply loops). **Use 2.0.1, never 2.0.0.**
- **Notable:** same use-the-patch pattern as 1.15.x (1.15.0 shipped broken images, 1.15.1 fixed; 2.0.0 shipped a broken CRD, 2.0.1 fixed — turnaround this time was 2 days, not 2 months).

## 2.0.0  (2026-07-27)

- **k8s floor:** unstated by upstream; CI against currently-supported upstream minors at release (2026-07). The `kubernetes_use_configmaps` default flip (below) is explicitly motivated by the upstream Endpoints API deprecation.
- **Bundled Spilo image:** `ghcr.io/zalando/spilo-17:4.1-p2` (default PG17; bundle includes PG18)
- **Bundled PostgreSQL majors:** 14 – 18 (**PG13 dropped**, **PG18 added**)
- **Breaking:**
  - **`kubernetes_use_configmaps` is now `true` by default** ("because endpoints will disappear", #3102/#3116) — the flip foreshadowed at 1.15.0 landed here. Fleets that never migrated their DCS off Endpoints get flipped by the operator bump; the 1.15.0 split-brain warning applies at upgrade time. To defer, explicitly set `kubernetes_use_configmaps: false` before bumping and plan the migration window separately (§1.15.0 for the two supported paths).
  - **`password_encryption` defaults to scram-sha-256** (#2962) — forces a rolling update of all pods on operator bump; md5-era clients/hashes must be handled first.
  - dropped support for **Postgres 13** — `pg_upgrade` PG13 clusters to 14+ **before** the operator bump.
  - dropped deprecated manifest fields `useLoadBalancer`, `replicaLoadBalancer`, `pod_priority_class_name`, `init_containers` (#3106) — clean manifests before bumping or the CRs fail validation.
  - dropped the `kubectl-pg` plugin (#3107) and GP2→GP3 EBS migration options (#3142); `aws-load-balancer-connection-idle-timeout` no longer set by default (#3054) — AWS-only impact.
  - removed all remaining references to `registry.opensource.zalan.do` (#3092); helm chart 1.10.1 releases dropped.
- **CRD migrations:** CRD manifests now generated from Go structs (#3004 et seq.) — no API group/version bump stated, but the regenerated OperatorConfiguration CRD in 2.0.0 carries a type mismatch (fixed in 2.0.1).
- **Upgrade ordering:** (1) `pg_upgrade` any PG13 cluster to 14+; (2) decide the configmaps stance — pin `false` or schedule the DCS migration window; (3) strip dropped manifest fields; (4) then operator bump → Spilo bump, Patroni rolls pods one at a time. Upstream migration guide: `docs/migrate.md` in the repo.
- **Deprecations:** —
- **Notable:** first Zalando release with PG18. Helm charts now also published to ghcr.io as OCI (`ghcr.io/zalando/charts/postgres-operator:2.0.1`) alongside GitHub Pages — relevant for air-gap chart mirroring. Maintenance windows now globally configurable/disable-able (#3038).

## 1.15.1  (2025-12-18)

- **k8s floor:** unstated by upstream; verified by operator CI against currently-supported k8s minors (≈ 1.28 – 1.34 at release time). Treat as "works on any currently-supported k8s minor", not pinned.
- **Bundled Spilo image:** `ghcr.io/zalando/spilo-17:4.0-p3`
- **Bundled PostgreSQL majors:** 13 – 17 (PG12 dropped at 1.14.0)
- **Breaking:** stopped pushing to `registry.opensource.zalan.do` — all images now ghcr.io-only. Air-gapped mirrors that pulled from the old registry must be repointed. 1.9.0 helm-chart releases removed.
- **CRD migrations:** removed unsupported `format` field for integer type in Postgresql CRD (#3017) — schema-clean, no manifest impact.
- **Upgrade ordering:** operator → Spilo bump in that order. Bump operator first (Spilo default image moves with it), let Patroni roll pods one at a time. Postgres major upgrade still runs through `pg_upgrade` via Spilo's bootstrap; gate behind `maintenanceWindows` + `majorVersionUpgradeMode: manual` if rolling fleet-wide.
- **Deprecations:** —
- **Notable:** bugfix-only on top of 1.15.0. Use 1.15.1, not 1.15.0 — 1.15.0 is missing UI and logical-backup ghcr images.

## 1.15.0  (2025-10-21)

- **k8s floor:** as 1.15.1.
- **Bundled Spilo image:** `ghcr.io/zalando/spilo-17:4.0-p3`
- **Bundled PostgreSQL majors:** 13 – 17.
- **Breaking:** **last release with `kubernetes_use_configmaps` disabled by default** — the flip landed at v2.0.0 (2026-07-27), see §2.0.0. Migration is **non-trivial for clusters with replicas**: switching Endpoints → ConfigMaps under a running multi-pod cluster risks Patroni split-brain because the DCS facts live in both resources during the rotation. Two supported migration paths (both require an outage window): (a) scale every cluster down to one primary via `max_instances: '1'`, flip the flag, then scale back out; (b) stand up a parallel operator with `CONTROLLER_ID` set, create standby clusters, promote. See release notes for full sequence.
- **CRD migrations:** —
- **Upgrade ordering:** if planning the `kubernetes_use_configmaps` flip, do it **at** 1.15 — don't carry a default-off setup forward into the next minor and rely on auto-migration. Auto-migration is not provided.
- **Deprecations:** WAL-E backup library removed from UI backend; WAL-G is the only supported logical-backup library now.
- **Notable:** second PDB introduced to protect pods during bootstrap (#2830). `bootstrap_labels` (Patroni) passthrough. Major-version-upgrade pre-checks tightened (#2772, #2810, #2842, #2849). 1.15.0 ghcr images for UI and logical-backup are missing — use 1.15.1 instead.

## 1.14.0  (2024-12-23)

- **k8s floor:** unstated; verified against then-current k8s minors (≈ 1.27 – 1.31 at release time).
- **Bundled Spilo image:** `ghcr.io/zalando/spilo-17:4.0-p2`
- **Bundled PostgreSQL majors:** 13 – 17  (**PG12 dropped at this release**)
- **Breaking:** dropped support for **Postgres 12**. Clusters still on PG12 must be `pg_upgrade`'d before the operator bump, otherwise the operator will refuse to manage them. Log-message format changed on SYNC/UPDATE events (only breaking if log-scraping alerts grep on exact strings).
- **CRD migrations:** —
- **Upgrade ordering:** PG12 → PG13+ `pg_upgrade` **before** operator bump to 1.14.0. The 1.13.0 operator can still drive the major upgrade in `manual` mode (`majorVersionUpgradeMode: manual` is the default since 1.13.0; switched to enabled-by-default at 1.13.0 release). Then bump operator → 1.14.0.
- **Deprecations:** —
- **Notable:** first release with **Postgres 17** support (via spilo-17:4.0-p2). Patroni 4 compatibility added (operator still uses old `master` label internally — relabel rollover deferred). QPS/burst limits added for the api client — useful for fleets > ~100 clusters where the operator was hitting kube-apiserver throttling. EBS CSI Driver support hardened.

## 1.13.0  (2024-08-22)

- **k8s floor:** unstated; verified against then-current k8s minors (≈ 1.26 – 1.30 at release time).
- **Bundled Spilo image:** `ghcr.io/zalando/spilo-16:3.3-p1`  (**warning**: wal-g out-of-the-box requires `ghcr.io/zalando/spilo-16:3.3-p3` — see Breaking below)
- **Bundled PostgreSQL majors:** 12 – 16  (**PG11 dropped at this release**)
- **Breaking:**
  - **wal-g backups do not work out-of-the-box with the default `3.3-p1` Spilo image** — must explicitly pin Spilo to `ghcr.io/zalando/spilo-16:3.3-p3` via `docker_image:` in the OperatorConfiguration. This is a known gotcha; the 1.14.0 default Spilo (`spilo-17:4.0-p2`) carries the fix.
  - dropped support for **Postgres 11**. `pg_upgrade` PG11 → PG12+ before this operator bump.
  - **automatic major version upgrades enabled by default** (`majorVersionUpgradeMode: manual`). Manual still requires explicit annotation per cluster, but the operator now considers the path live by default — review your `maintenanceWindows` before bumping to 1.13.
  - removing `streams` block from a manifest now actively deletes the database publication, slots, and FES resources (was previously a no-op).
  - dropped default for `additional_secret_mount_path` when configured via the CRD config (previously silently defaulted; now empty unless set).
- **CRD migrations:** —
- **Upgrade ordering:** PG11 → PG12+ `pg_upgrade` **before** operator bump. Per-cluster `maintenanceWindows` were introduced this release (#2710, #2731) — set them before flipping to 1.13 if any cluster runs writes 24/7.
- **Deprecations:** 1.8.2 helm-chart releases dropped.
- **Notable:** per-cluster `maintenanceWindows` for major-version upgrade gating. Owner-references on child resources (`enableOwnerReferences`) — affects GC behavior on `Postgresql` CR deletion. Stream resources skipped on publication/slot sync errors.

## Cross-cutting (all in-scope versions)

- **Operator k8s floor is loose.** Zalando does not publish a Kubernetes support matrix per release. The operator uses standard client-go and CRD v1; it has run cleanly on every supported upstream k8s minor in the 1.13 – 2.0 lifetime. Verdict against k8s ≥ 1.27 is "compatible barring CRD-conversion-webhook regressions". Below 1.25, treat as unverified.
- **Postgres 18 requires v2.** 1.15.x ships Spilo-17 4.0-p3 (PG 13–17, no PG18). PG18 landed at v2.0.0 (2026-07-27) via Spilo-17 4.1-p2 — the "Q1 2026" target slipped ~2 quarters and arrived as a major. Surveying for PG18 readiness: available on v2.0.1+ only.
- **Connection pooler (pgBouncer):** coupled to the operator version via the `connection_pooler_image` config default. Each operator minor bumps the default pgBouncer image; manually pinned values stick across upgrades. Verify after operator bump that the pooler image still pulls and is on a supported pgBouncer line.
- **logical-backup image:** versioned with the operator (`ghcr.io/zalando/postgres-operator/logical-backup:vX.Y.Z`). Bump in lockstep with the operator — mismatched logical-backup vs operator is unsupported.
- **standby cluster behavior:** unchanged through 1.13 – 1.15. The 1.15.0 release notes use standby clusters as a migration aid for the configmaps flip but introduce no semantic changes.
