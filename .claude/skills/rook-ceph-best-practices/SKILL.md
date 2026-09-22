---
name: rook-ceph-best-practices
description: >-
  Operate, configure and upgrade Rook-managed Ceph on Kubernetes (ceph.rook.io
  CephCluster, CephBlockPool, CephFilesystem, CephObjectStore; rook-ceph and
  rook-ceph-cluster Helm charts; ceph-csi and ceph-csi-operator). Core
  knowledge: the Rook -> Ceph -> key-rotation upgrade order and its version
  gates; the CVE-2025-30156 fix (new AES256K CephX key type, daemon key
  rotation, the six AUTH_INSECURE_* health codes, kernel 7.0 for CSI keys);
  the Rook v1.20 move of CSI to ceph-csi-operator and the new ceph-csi-drivers
  chart; disabling the rook mgr module before Tentacle; Helm monitoring RBAC.
when_to_use: >-
  Use for any Rook/Ceph operator task: "upgrade rook", "upgrade ceph under
  rook", "bump cephVersion.image", "rook helm chart upgrade", "rook v1.20",
  "ceph-csi-drivers chart", "ceph-csi-operator", "CVE-2025-30156", "aes256k",
  "cephx key rotation", "keyRotationPolicy", "keyGeneration",
  "AUTH_INSECURE_SERVICE_KEY_TYPE", "muteHealthWarning", "allowedCiphers",
  "rook toolbox permission denied", "rook mgr module", "rook-ceph monitoring
  ServiceMonitor forbidden", "which Ceph versions does Rook support".
  Symptoms: HEALTH_ERR after a Ceph point-release bump, CSI ctrlplugin 0/2
  after a Rook upgrade, toolbox `handle_auth_bad_method` / errno 13, mgr
  crash-looping on Tentacle, PVC mounts failing after key rotation.
  NOT for generic Ceph triage (PG states, slow ops, OSD flapping) - that is
  ceph-troubleshooting; tuning is ceph-performance; RGW/S3 behaviour is ceph-s3.
argument-hint: "[upgrade|cephx|csi|monitoring] (optional focus area)"
---

# rook-ceph-best-practices

Facts verified **2026-09-23** against rook/rook releases v1.16.0–v1.20.7
(unfiltered), the Rook docs at tag v1.20.7, the ceph.io release posts,
the rook/rook and ceph/ceph-csi issue trackers, and one live upgrade
(Rook v1.19.6 → v1.19.11, Ceph 19.2.3 → 19.2.6 with daemon key rotation).
Everything here is version-gated: re-check `references/sources.md` before
relying on it for a newer release.

## Version gates (2026-09-23)

| Rook | Kubernetes | Ceph supported | Notes |
|---|---|---|---|
| v1.18.x | 1.29–1.34 | Reef 18.2, Squid 19.2 | Last line that runs Reef. ceph-csi-operator becomes the default CSI config path. Key rotation experimental. |
| v1.19.x | 1.30–1.35 | Squid 19.2.0+, Tentacle | **Reef dropped** (min Ceph 19.2.0). AES256K from **v1.19.9**; CVE floor **v1.19.10**. v1.19.11 ships ceph-csi 3.16.3 (AES256K backport). |
| v1.20.x | 1.31–1.36 | Squid 19.2.0+, Tentacle 20.2.1+ | **Rook no longer deploys CSI** — ceph-csi-operator + new `ceph-csi-drivers` chart required. AES256K from v1.20.5; CVE floor **v1.20.6**. v1.20.7 ships ceph-csi 3.17.1. |

Ceph lines: Reef 18.2.x is EOL (last 18.2.8, 2026-03-20). Squid 19.2.x
latest 19.2.6. Tentacle 20.2.x latest 20.2.4. Do not run **20.2.0** (data
corruption with CSI read affinity, rook#16839) or **18.2.5/18.2.6**
(BlueStore corruption regression, fixed 18.2.7). `x.2.z` is a stable
release; a `v19.3.0`-style tag is a development tag, never deploy it.

## Upgrade order — never reorder

1. **Rook operator** (Helm `rook-ceph` chart; CRDs ship as chart templates
   when `crds.enabled`, so `helm upgrade` applies them).
2. **Ceph image** (`CephCluster.spec.cephVersion.image`).
3. **CephX key rotation** (can ride on step 2's restart — same patch).
4. **Toolbox image**, by hand. Nothing manages it.

A Rook minor hop must start from a supported patch: v1.19 → v1.20 requires
**v1.19.5+** first. Clusters below v1.18 heading for the CVE fix take the
path in `references/upgrade-path.md` — do not jump straight to Ceph 19.2.6.

### Gates between hops

| When | Check | Pass |
|---|---|---|
| Before any hop | `ceph status`, CephCluster `.status.phase` | HEALTH_OK, phase Ready, all PGs active+clean, all mons in quorum |
| Operator hop done | `kubectl -n <ns> get deploy -l rook_cluster=<ns> -o jsonpath='{range .items[*]}{.metadata.labels.rook-version}{"\n"}{end}' \| sort \| uniq -c` | one line |
| Ceph hop done | `ceph versions` | `overall` has one line whose count = total daemons |
| Rotation done | CephCluster `.status.cephx.<type>.keyGeneration` for admin, mon, mgr, osd, crashCollector, cephExporter; also CephFilesystem / CephObjectStore `.status.cephx.daemon` | every entry at the target generation |

`ceph versions` does not change during an operator-only hop — use the
`rook-version` label. Watch progress with the `ceph-version` label, not the
toolbox (the toolbox loses auth mid-rotation).

**HEALTH_ERR semantics.** The operator checks health *when an update is
requested* and refuses to start from HEALTH_ERR. HEALTH_ERR raised *during*
a started rolling upgrade by the new AUTH_INSECURE_* codes did not stop it
(observed on v1.19.11). Do not pre-emptively set `skipUpgradeChecks: true`;
in rook#18240 forcing past HEALTH_ERR mid-rotation preceded a full OSD
outage.

### Pin images by digest

Use full build tags plus digest: `quay.io/ceph/ceph:v19.2.6-20260818@sha256:…`.
A floating tag (`:v20`) with `imagePullPolicy: IfNotPresent` keeps running
a stale cached image — root cause of the toolbox `Malformed input` keyring
error in rook#18240. The v1.20.7 doc's quick-fix patch shows
`quay.io/ceph/ceph:v1.20.4-20260818` — a typo for `v20.2.4-20260818`; do
not copy it.

## CVE-2025-30156 and AES256K — the short path

Unaided models get this wrong in three ways, so do not repeat them:
`AUTH_INSECURE_*_KEY_TYPE` / `AUTH_INSECURE_SERVICE_TICKETS` are new in
19.2.6 / 20.2.4 and are **not** the 2021 `AUTH_INSECURE_GLOBAL_ID_RECLAIM*`
codes (CVE-2021-20288) — `auth_allow_insecure_global_id_reclaim` does
nothing here; `aes256k` **is** a real CephX key type; and
`spec.security.cephx.allowedCiphers` / `keyType` **are** real CephCluster
fields (Rook ≥ v1.19.9 / v1.20.5).

The image bump alone does **not** fix the CVE. The fix is Ceph ≥ 19.2.6 /
20.2.4 **plus** rotating the core daemon keys (mon, mgr, osd, mds) to
AES256K. Client kernels do not matter for this step: once daemon keys are
AES256K every client, including `aes` ones, receives AES256K service tickets.

Before the Ceph bump:

1. Check node kernels, never a note:
   `kubectl get nodes -o custom-columns=NODE:.metadata.name,KERNEL:.status.nodeInfo.kernelVersion`.
2. Pin CSI key type if any node is < 7.0 (FIPS: < 7.2):
   `spec.security.cephx.csi.keyType: aes`. With `keyRotationPolicy` unset
   this triggers no rotation; Rook only creates CSI keys that are missing.
3. Remove auth entities for OSDs that no longer exist — Rook only rotates
   live daemons, so a stale `osd.N` stays `aes` and is the one HEALTH_ERR
   left afterwards. Compare `ceph auth ls | grep ^osd.` with `ceph osd ls`;
   for each orphan: `ceph osd find N` (must be ENOENT) → `ceph auth get osd.N`
   (backup) → `ceph auth rm osd.N`.
4. Save a baseline: CephCluster YAML (`status.cephx`), `ceph auth ls`,
   `ceph osd tree`, pods, full operator log. Take `ceph auth ls` now — after
   the admin key rotates the toolbox cannot authenticate until restarted.

Then apply image + rotation in one patch:

```yaml
spec:
  cephVersion:
    image: quay.io/ceph/ceph:v19.2.6-20260818   # or v20.2.4-20260818; pin the digest
  security:
    cephx:
      daemon:
        keyRotationPolicy: KeyGeneration
        keyGeneration: 2          # any integer above current status
```

Expect, in order: HEALTH_ERR `AUTH_INSECURE_SERVICE_KEY_TYPE` +
`AUTH_INSECURE_SERVICE_TICKETS` as soon as the first daemons run the new
version; rotation admin → mon → mgr → OSDs one at a time → RGW/MDS/others;
OSD pods briefly 1/2 or Init (normal); the toolbox failing with
`handle_auth_bad_method … [errno 13] RADOS permission denied` (restart it).
The two errors clear when the core daemons are rotated. Remaining warnings
are expected — see the health-code table in `references/cephx-aes256k.md`
and mute them with `spec.healthCheck.muteHealthWarning.<CODE>.policy: mute`
(Rook ≥ v1.19.10).

**If rotation stalls** (a daemon type stuck at the old generation, OSDs
losing auth): per the maintainer in rook#18240 — apply no workarounds,
restart no pods in the Rook namespace, collect the operator log immediately.
`allowedCiphers` edits did not help that case.

**Never** set `allowedCiphers: [aes256k]` until
`ceph auth dump-keys --format=json-pretty` shows no `aes` key anywhere, and
never while any node kernel is < 7.0 with CSI keys that could rotate.
Recovery and the CSI key migration procedure: `references/cephx-aes256k.md`.

`status.cephx.osd` shows `keyGeneration` but not `keyType`; `ceph health
detail` / `ceph auth dump-keys` are the authority on key type.

## Rook v1.20: CSI moves to ceph-csi-operator

Rook v1.20 removed every CSI setting from `rook-ceph-operator-config` and
from the `rook-ceph` chart. Helm install/upgrade order becomes:
**`rook-ceph` → `ceph-csi-drivers` (new, required) → `rook-ceph-cluster`**.
Skipping `ceph-csi-drivers` leaves the CSI ServiceAccounts/RBAC missing:
ctrlplugin Deployments sit at 0/2 and every attach/detach in the cluster
fails (rook#17644). Migrate custom CSI settings to ceph-csi-operator
`OperatorConfig` / `Driver` CRs by hand before the hop.

The `ceph-csi-drivers` chart does not set
`operatorConfig.driverSpecDefaults.imageSet.name`, so ceph-csi-operator
falls back to its own hard-coded cephcsi image instead of the version
Rook pins (ceph-csi-operator#605). Verify the running cephcsi image after
the hop; AES256K needs cephcsi ≥ 3.17.1 on the 1.20 line.

## Tentacle: disable the rook mgr module first

Rook docs (v1.20.6+) recommend, before upgrading to Tentacle:

```yaml
spec:
  mgr:
    modules:
    - name: rook
      enabled: false
```

On Tentacle the enabled module makes the mgr crash-loop in the prometheus
module (`NotImplementedError` from `node_proxy_fullreport`, rook#18124,
ceph tracker 79106), and a day of crash records then breaks `ceph crash ls`
(tracker 79357). Its verbose logging is also one of two causes of mgr
OOM kills after Rook v1.20.1 / Ceph 20.2.2 (rook#17786; the other, a
`remote()` refcount leak, is tracker 77724). The only loss is some dashboard orchestrator pages; Rook
does not use the module. The chart default was flipped — check the live
CephCluster, not the chart.

## Monitoring with a Helm-installed operator

Needs the operator chart value `monitoring.enabled: true` (ServiceMonitor
RBAC) as well as `CephCluster.spec.monitoring.enabled`. After the RBAC
lands, restart the operator — it did not create the ServiceMonitors until
restarted. The operator never creates PrometheusRules.

## Other hazards worth checking before a hop

Per-release breaking changes (CRUSH rule deletion, MDS standby removal,
chart field splits, S3 credential purge) are in `references/upgrade-path.md`.

| Hazard | Source |
|---|---|
| 19.2.6 → Tentacle below 20.2.4 drops AES256K (20.2.0–20.2.3 predate it): go 19.2.6 → 20.2.4+ only | ceph-users 2026-09-03 |
| After 19.2.6 → 20.2.4, re-check `ceph config get mon auth_allowed_ciphers`: a cephadm upgrade reset `aes256k` to `aes, aes256k` | tracker 80295 |
| RGW SigV4 fix (19.2.6 / 20.2.4) rejects presigned PUTs with an unsigned Content-Type (restic, PHP clients); workaround `rgw_sigv4_insecure=true` until 19.2.7 / 20.2.5 | tracker 79674 |
| Squid→Tentacle: Rook rolls RGW/MDS before all OSDs are upgraded, breaking S3 multipart during the window | rook#18367 |
| RGW multisite on 19.2.6/20.2.4: SigV4 hardening rejects RGW's own inter-zone forwarding; set `rgw_sigv4_insecure=true` (and `rgw_s3_client_max_sig_ver=2`) **before** upgrading | tracker 79698; Rook ceph-upgrade.md |
| Fresh mon quorum never forms on kernel 7.0 cold bootstrap (existing quorums unaffected) — collides with the 7.0 AES256K kernel requirement | rook#18370, tracker 80470 |
| 1500-OSD-scale 18.2.8 → 19.2.6 upgrade: mon slow ops climbing into tens of thousands on each mon restart; did not reproduce in staging | ceph-users 2026-09-14 |
| NFS-Ganesha per-export keys cannot be rotated (Ceph has no mechanism) | Rook cephx-key-rotation.md |

## References

- `references/cephx-aes256k.md` — key types, all six health codes, CSI key
  migration and revert, `allowedCiphers` recovery, CephClient / RBD-mirror /
  external-cluster keys. Read before any rotation beyond the daemon keys.
- `references/upgrade-path.md` — release-by-release breaking changes
  v1.16–v1.20 and the multi-hop CVE path from older Rook.
- `references/sources.md` — every source with its verification stamp.
- Sibling skills: `ceph-troubleshooting`, `ceph-performance`, `ceph-s3`.
