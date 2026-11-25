# rancher-logging — compat (sifted from enumerated_artifacts)

- **Primary source:** https://github.com/rancher/charts (assets/rancher-logging on release-v2.1x branches)
- **Secondary sources:** https://github.com/rancher/ob-team-charts (chart fork) ; https://github.com/kube-logging/logging-operator/releases (upstream base)
- **Truth source type:** `enumerated_artifacts` (no published matrix exists — versions read from Chart.yaml/values.yaml per branch)
- **Axis type:** `dual` (Rancher minor gate + kube-version gate, both from catalog annotations)
- **min_tracked_version:** 106.x (Rancher 2.11)
- **Last sifted:** 2026-11-25 — read `rancher/charts` `assets/rancher-logging` on `release-v2.11`…`release-v2.16` and `index.yaml` gates; unpacked `rancher-logging-110.0.1+up4.10.0-rancher.27` and `…110.0.0+up4.10.0-rancher.24` and diffed them; read `rancher/ob-team-charts` PR #337 and commits since 2026-11-19; upstream `kube-logging/logging-operator` releases 6.7.0–6.9.0. **The 2.12–2.15 lines moved to `rancher.27` and their images changed:** from `rancher.25` (2026-11-19) the chart's images are Rancher-built BCI rebuilds under new repository names (see Component images). **Every newest chart is still `+up4.10.0`**: the operator is still the 4.10.0 source, so the CVE-2026-54680 exposure is unchanged. The CVE-ID search was re-run: zero hits in `rancher/charts`, `rancher/ob-team-charts` and rancher-org issues (hits only in `rancher/scans` scanner report pages); still no SUSE fix or advisory. ob-team-charts #218 still open.
- **Last release-verified:** 2026-11-25 — chart versions per branch enumerated from `assets/rancher-logging`: 2.11 `106.0.8+up4.10.0-rancher.24` (no `rancher.27` build; Rancher 2.11 is past EOL), 2.12 `107.0.7+up4.10.0-rancher.27`, 2.13 `108.0.6+up4.10.0-rancher.27`, 2.14 `109.0.2+up4.10.0-rancher.27`, 2.15 `110.0.1+up4.10.0-rancher.27`; kube and rancher gates re-read from each newest chart's `Chart.yaml` and unchanged. Upstream latest is **6.9.0 (2026-09-17)**, unchanged since the last sift. Chart contents beyond images and gates not sifted.

Chart version scheme: `<prefix>.<minor>.<patch>+up<upstreamOperator>[-rancher.N]`;
prefix↔Rancher mapping verified empirically via `catalog.cattle.io/rancher-version`:
102=2.7 · 103=2.8 · 104=2.9 · 105=2.10 · 106=2.11 · 107=2.12 · 108=2.13 · 109=2.14 ·
110=2.15. The `-rancher.N` respins live in rancher/ob-team-charts. Up to `rancher.24` they are
**chart-level only** (per-distro journald sources, Windows agents, SELinux,
template fixes) with stock upstream mirror images. From `rancher.25` (2026-11-19, "Update images to reduce CVE counts") the images are Rancher-built BCI rebuilds of the same 4.10.0 sources; `rancher.26` (2026-11-20) adds a debug image; `rancher.27` (2026-11-23) is an un-rc rebuild.

⚠️ **The upstream base is FROZEN at 4.10.0 (released 2024-10-03) across every
tracked line 106→110**, while upstream is at **6.9.0 (2026-09-17)** (6.8.0 2026-08-11; no newer release since). Operator ≤6.5.2 —
including 4.10.0 — is affected by **CVE-2026-54680** (CVSS 9.9 fluentd
config-injection → RCE, GHSA-mjqf-28ph-426h); fix exists only in upstream 6.6.0+
(use 6.7.0 — 6.6.0 has a newline-password regression). **No SUSE fix or advisory
exists as of 2026-11-25** (code search for the CVE ID in `rancher/charts` and `rancher/ob-team-charts`: zero hits both; the `rancher.25` image rebuild keeps the 4.10.0 operator tag `v4.10.0_rancher.1`, so it is not a fix) and none can ship as a `-rancher.N` respin. Migration
path: the `rancher-logging-exit` skill.

Component images, **two naming generations** (air-gap mirror lists must carry the one
matching the chart installed):

| Chart | operator | fluentd | fluentbit | config-reloader |
|---|---|---|---|---|
| 2.11 line `106.0.8` (`rancher.24`) and every chart up to `rancher.24` | `rancher/mirrored-kube-logging-logging-operator:4.10.0` | `rancher/mirrored-kube-logging-fluentd:v1.16-4.10-full` | `rancher/mirrored-fluent-fluent-bit:3.1.8` (+`3.1.8-debug`) | `rancher/mirrored-kube-logging-config-reloader:v0.0.6` |
| 2.12–2.15 newest charts `107.0.7` / `108.0.6` / `109.0.2` / `110.0.1` (`rancher.27`) | `rancher/kube-logging-logging-operator:v4.10.0_rancher.1` | `rancher/fluentd:v1.16-4.10_rancher.1` | `rancher/fluent-bit:v3.1.8_rancher.1` (+`v3.1.8_rancher.1_debug`) | `rancher/kube-logging-config-reloader:v0.0.6_rancher.1` |

Tags in the second row are read from `110.0.1`; the `107.0.7` / `108.0.6` / `109.0.2` repository names match, their tags were not read. Windows fluent-bit is `rancher/fluent-bit:3.1.8` in both. No
syslog-ng image (`syslogNG: {}` stub — bundled installs are fluentd-mode only).
fluent-bit 3.1.8 is version-in-range for the Nov-2025 CVE set
(CVE-2025-12969/…/12978) but the default tail→k8s-filter→forward pipeline does not
enable the vulnerable plugins.

Gate caveat: Chart.yaml `kubeVersion` and the `catalog.cattle.io/kube-version`
annotation disagree (106.0.8: `>=1.22.0-0` vs `>= 1.30.0-0 < 1.33.0-0`; 107.0.7 / 108.0.6 / 109.0.2 / 110.0.1: `>=` the annotation's lower bound, no upper bound).
Helm CLI enforces the former, Rancher UI the latter — **carry the annotation as
the real gate**.

## Per-line matrix

Rancher-version gate below is `generated.json` `edges.rancher_logging[*].rancher-version` — the
catalog's own SemVer constraint on which Rancher minor may install that chart line, distinct from
the kube-version gate. Gates re-read from each newest chart's Chart.yaml 2026-11-25.

| Rancher | Chart line (released) | Upstream base | kube gate (annotation) | rancher gate (annotation) | Notes |
|---|---|---|---|---|---|
| 2.11 | 106.0.0+up4.10.0-rancher.1 → **106.0.8+up4.10.0-rancher.24** | 4.10.0 | ≥1.30 <1.33 | ≥2.11.0-0 <2.12.0-0 | last build on this line; Rancher 2.11 community EOL 2026-10-24; mirrored-* images |
| 2.12 | 107.0.0+up4.10.0-rancher.6 → **107.0.7+up4.10.0-rancher.27** | 4.10.0 | ≥1.31 <1.34 | ≥2.12.0-0 <2.13.0-0 | ⚠ two artifacts share helm version `107.0.1` (+…rancher.10 vs rancher.13; `+` is build metadata to helm). From rancher.25 BCI images |
| 2.13 | 108.0.0+up4.10.0-rancher.15 → **108.0.6+up4.10.0-rancher.27** | 4.10.0 | ≥1.32 <1.35 | ≥2.13.0-0 <2.14.0-0 | from rancher.25 BCI images |
| 2.14 | 109.0.0+up4.10.0-rancher.23 → **109.0.2+up4.10.0-rancher.27** | 4.10.0 | ≥1.33 <1.36 | ≥2.14.0-0 <2.15.0-0 | `rancher.24` ("node info for rke2") shipped; from rancher.25 BCI images |
| 2.15 | **110.0.1+up4.10.0-rancher.27** (released) | **still 4.10.0** | `>= 1.34.0-0 < 1.37.0-0` | ≥2.15.0-0 <2.16.0-0 | Rancher 2.15 GA'd 2026-07-30 and this chart line released with it; gates re-read from the `110.0.1` Chart.yaml 2026-11-25. Freeze continues; no chart for Rancher 2.16 exists yet |

Historical anchors: 102.x/2.7 bundled 3.17.10 (7 CRDs only — no fluentbitagents/
syslogng*/loggingroutes); base hops on record: 3.17.10 → 4.4 → 4.8 → 4.10 (during
2.8–2.10), frozen since 105.1.0 (~mid-2024).

Not formally deprecated (no release-note deprecation through 2.14; SUSE docs still
document the app) — de-facto frozen. ob-team-charts known open bug: #218
eventtailer nil-pointer regression in 4.10-rancher.16+.

Sift notes: enumerate `assets/rancher-logging` on each `release-v2.1x` branch via
`gh api repos/rancher/charts/contents/...?ref=<branch>`; read Chart.yaml
annotations of the newest asset per line. Re-sift on: new Rancher minor branch
creation (2.16 has none yet), any `+up` base change (would be headline news), SUSE advisory for
CVE-2026-54680.

Migration target note: upstream 6.8.0 bumps Fluent Bit to 5.1.0, where a `customParsers` entry reusing a built-in name (`json`, `docker`, `cri`, `kube-custom`) crash-loops the DaemonSet; rename it before the move or pin the Fluent Bit image to `5.0.5` (upstream release notes).
