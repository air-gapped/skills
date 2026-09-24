# rancher-logging — compat (sifted from enumerated_artifacts)

- **Primary source:** https://github.com/rancher/charts (assets/rancher-logging on release-v2.1x branches)
- **Secondary sources:** https://github.com/rancher/ob-team-charts (chart fork) ; https://github.com/kube-logging/logging-operator/releases (upstream base)
- **Truth source type:** `enumerated_artifacts` (no published matrix exists — versions read from Chart.yaml/values.yaml per branch)
- **Axis type:** `dual` (Rancher minor gate + kube-version gate, both from catalog annotations)
- **min_tracked_version:** 106.x (Rancher 2.11)
- **Last sifted:** 2026-09-24 — cross-checked against `generated.json` (compat.py sync 2026-09-24)
  `edges.rancher_logging`: chart version, kube-version gate and rancher-version gate for all five
  lines match this file's 2026-09-15 values exactly (no chart moved since); added the rancher-version
  gate column below since generated.json now carries it as data. Prior sift 2026-09-15 — all four
  branches re-enumerated; **every newest chart is still `+up4.10.0`**, so the freeze this file exists
  to describe is intact. The CVE-2026-54680 backport search was re-run across `rancher/charts` and
  `rancher/ob-team-charts`: still zero hits, still no SUSE advisory, so Rancher's shipped 4.10.0
  remains below the 6.6.0 fix floor. Component images unchanged (operator 4.10.0, fluentd
  v1.16-4.10-full, fluentbit 3.1.8, config-reloader v0.0.6). ob-team-charts #218 still open.
- **Last release-verified:** 2026-09-24 — no new patch to verify against `gh`; the
  `edges.rancher_logging` cross-check above is against the machine-generated registry, not a fresh
  API call. Prior release-verify 2026-09-15 — `assets/rancher-logging` enumerated on
  `release-v2.15`. **The `rancher.24` respin that was unreleased at sift has now
  shipped on every line**, and the 2.15 chart line is **released, not an rc**.
  Upstream base is **still 4.10.0** across all of them — the freeze the sift
  predicted continues. Chart contents not sifted; the kube gates below are
  unchanged.

Chart version scheme: `<prefix>.<minor>.<patch>+up<upstreamOperator>[-rancher.N]`;
prefix↔Rancher mapping verified empirically via `catalog.cattle.io/rancher-version`:
102=2.7 · 103=2.8 · 104=2.9 · 105=2.10 · 106=2.11 · 107=2.12 · 108=2.13 · 109=2.14 ·
110=2.15(dev). The `-rancher.N` respins live in rancher/ob-team-charts and are
**chart-level only** (per-distro journald sources, Windows agents, SELinux,
template fixes) — the operator image is a stock upstream mirror.

⚠️ **The upstream base is FROZEN at 4.10.0 (released 2024-10-03) across every
tracked line 106→110**, while upstream is at **6.9.0 (2026-09-17)** — two further releases since
last sift (6.8.0, 6.9.0), widening the gap again. Operator ≤6.5.2 —
including 4.10.0 — is affected by **CVE-2026-54680** (CVSS 9.9 fluentd
config-injection → RCE, GHSA-mjqf-28ph-426h); fix exists only in upstream 6.6.0+
(use 6.7.0 — 6.6.0 has a newline-password regression). **No SUSE fix or advisory
exists as of 2026-09-24** (re-swept `rancher/charts` and `rancher/ob-team-charts` code search for
the CVE ID, zero hits both) and none can ship as a `-rancher.N` respin. Migration
path: the `rancher-logging-exit` skill.

Component images (IDENTICAL across the newest chart of every line 106.0.7 →
110.0.0-rc.1): operator `rancher/mirrored-kube-logging-logging-operator:4.10.0` ·
fluentd `rancher/mirrored-kube-logging-fluentd:v1.16-4.10-full` · fluentbit
`rancher/mirrored-fluent-fluent-bit:3.1.8` (+`-debug`; Windows `rancher/fluent-bit:3.1.8`)
· config-reloader `rancher/mirrored-kube-logging-config-reloader:v0.0.6` · no
syslog-ng image (`syslogNG: {}` stub — bundled installs are fluentd-mode only).
fluent-bit 3.1.8 is version-in-range for the Nov-2025 CVE set
(CVE-2025-12969/…/12978) but the default tail→k8s-filter→forward pipeline does not
enable the vulnerable plugins.

Gate caveat: Chart.yaml `kubeVersion` and the `catalog.cattle.io/kube-version`
annotation disagree (e.g. 106.0.7: `>=1.22.0-0` vs `>= 1.30.0-0 < 1.33.0-0`).
Helm CLI enforces the former, Rancher UI the latter — **carry the annotation as
the real gate**.

## Per-line matrix

Rancher-version gate below is `generated.json` `edges.rancher_logging[*].rancher-version` — the
catalog's own SemVer constraint on which Rancher minor may install that chart line, distinct from
the kube-version gate. All five match this file's chart/kube values exactly (cross-checked
2026-09-24).

| Rancher | Chart line (released) | Upstream base | kube gate (annotation) | rancher gate (annotation) | Notes |
|---|---|---|---|---|---|
| 2.11 | 106.0.0+up4.10.0-rancher.1 → **106.0.8+up4.10.0-rancher.24** | 4.10.0 | ≥1.30 <1.33 | ≥2.11.0-0 <2.12.0-0 | all rancher.N respins (was 106.0.7/rancher.23 at sift) |
| 2.12 | 107.0.0+up4.10.0-rancher.6 → **107.0.6+up4.10.0-rancher.24** | 4.10.0 | ≥1.31 <1.34 | ≥2.12.0-0 <2.13.0-0 | ⚠ two artifacts share helm version `107.0.1` (+…rancher.10 vs rancher.13; `+` is build metadata to helm). Was 107.0.5/rancher.23 at sift |
| 2.13 | 108.0.0+up4.10.0-rancher.15 → **108.0.5+up4.10.0-rancher.24** | 4.10.0 | ≥1.32 <1.35 | ≥2.13.0-0 <2.14.0-0 | was 108.0.4/rancher.23 at sift |
| 2.14 | 109.0.0+up4.10.0-rancher.23 → **109.0.1+up4.10.0-rancher.24** | 4.10.0 | ≥1.33 <1.36 | ≥2.14.0-0 <2.15.0-0 | the `rancher.24` respin ("node info for rke2") **shipped** — it was an rc at sift |
| 2.15 | **110.0.0+up4.10.0-rancher.24** (released) | **still 4.10.0** | `>= 1.34.0-0 < 1.37.0-0` | ≥2.15.0-0 <2.16.0-0 | Rancher 2.15 GA'd 2026-07-30 and this chart line released with it; confirmed unchanged against generated.json 2026-09-24. Freeze continues |

Historical anchors: 102.x/2.7 bundled 3.17.10 (7 CRDs only — no fluentbitagents/
syslogng*/loggingroutes); base hops on record: 3.17.10 → 4.4 → 4.8 → 4.10 (during
2.8–2.10), frozen since 105.1.0 (~mid-2024).

Not formally deprecated (no release-note deprecation through 2.14; SUSE docs still
document the app) — de-facto frozen. ob-team-charts known open bug: #218
eventtailer nil-pointer regression in 4.10-rancher.16+.

Sift notes: enumerate `assets/rancher-logging` on each `release-v2.1x` branch via
`gh api repos/rancher/charts/contents/...?ref=<branch>`; read Chart.yaml
annotations of the newest asset per line. Re-sift on: new Rancher minor branch
creation, any `+up` base change (would be headline news), SUSE advisory for
CVE-2026-54680.
