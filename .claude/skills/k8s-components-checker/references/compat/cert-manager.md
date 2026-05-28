# cert-manager — compat (sifted from published_matrix)

- **Primary source:** https://cert-manager.io/docs/releases/
- **Secondary sources:** https://github.com/cert-manager/cert-manager/releases
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 1.17
- **Last sifted:** 2026-05-28

Support policy: each release is supported until two subsequent minors ship, so
exactly two minors are "current" at any time. Minors cadence ~4 months. Current
matrix at sift time: 1.20 (current), 1.19 (current), 1.21 (upcoming, Jun 2026),
1.18 (EOL since 2026-03-10 when 1.20 shipped — kept in scope per the
registry's "current + prior 2 minors" floor).

## 1.20.0 (2026-03-10)

- **k8s floor:** 1.32 – 1.35
- **Breaking:** Default container UID changed from 1000 → 65532, GID 0 → 65532
  (PR #8408). PodSecurityPolicy / SecurityContextConstraints / RunAsUser pinning
  in operator overlays will reject the new pod spec; review chart values
  `securityContext.runAsUser/runAsGroup` before upgrading. `DefaultPrivateKey
  RotationPolicyAlways` feature gate is now GA and **cannot be disabled** —
  every Certificate without an explicit `rotationPolicy` rotates the private
  key on every renewal (this was already the 1.18 default but is now locked).
- **CRD migrations:** None. CRDs ship in `cert-manager.crds.yaml` alongside the
  bundle; `helm upgrade --set crds.enabled=true` continues to manage them.
- **Upgrade ordering:** Apply new CRDs before the controller (standard cert-
  manager upgrade rule; the Helm chart does this automatically when
  `crds.enabled=true`). No special pre-bump ordering for k8s itself.
- **Deprecations:** None new at the API surface. `XListenerSets` feature gate
  promoted to `ListenerSets` (rename, not removal).
- **Notable:** Adds Azure Private DNS support, Gateway-API `parentRef` no
  longer required for ACME, `OtherNames` SAN type promoted to Beta. New
  `extraContainers` Helm value for sidecars (e.g. AWS IAM Roles Anywhere).
  Security fix for a controller-panic-via-DNS-cache (CVE-class MODERATE,
  PR #8469) — bump 1.20.0 → 1.20.2 to also pick up CVE-2025-61727 /
  CVE-2025-61729 Go fixes.

## 1.19.0 (2025-10-07)

- **k8s floor:** 1.31 – 1.35
- **Breaking:** API defaults added for Certificate `issuerRef.kind` (`Issuer`)
  and `issuerRef.group` (`cert-manager.io`). Per release-note bug item #8160,
  Certificates created on ≤1.18 with omitted kind/group were unnecessarily
  renewed once on upgrade to 1.19.x; mitigated in 1.19.1+. Plan for a
  re-issuance burst on the LE / step-CA / Vault path if jumping straight from
  1.17→1.19.0; use 1.19.5 or later to avoid this.
- **CRD migrations:** None — schema-additive only.
- **Upgrade ordering:** Apply CRDs before controller. From 1.18: no extra step.
- **Deprecations:** ACME client core metrics drop the `path` label
  (PR #8109) — Grafana dashboards / Prometheus alerts grouping on `path` will
  go empty. Reverted: `global.rbac.disableHTTPChallengesRole` Helm option
  introduced in 1.18 was rolled back here (#7836) — if a chart values file
  references it, the upgrade will warn but not fail.
- **Notable:** `CAInjectorMerging` feature gate promoted to Beta and on by
  default. Server-side-apply `applyconfigurations` generated for all CRDs.
  IPv6 rules added to default network policy. `certmanager_certificate
  _challenge_status` metric added.

## 1.18.0 (2025-06-10, EOL 2026-03-10)

- **k8s floor:** 1.29 – 1.33
- **Breaking:**
  - Default `Certificate.spec.privateKey.rotationPolicy` flipped `Never` →
    `Always` (#7723). Every renewal now rotates the private key by default;
    HPKP / certificate-pinning consumers must explicitly set `rotationPolicy:
    Never` or break clients.
  - Default `Certificate.spec.revisionHistoryLimit` set to `1` (#7758).
    Prior behaviour kept unbounded `CertificateRequest` history; rollback
    workflows that read older CR revisions need to set this explicitly.
  - HTTP-01 ingress `pathType` default flipped `ImplementationSpecific` →
    `Exact` (#7767). With ingress-nginx as of 1.18 release time, this hit a
    known issue (#7791) where the validating webhook rejected the path —
    pinned `pathType: ImplementationSpecific` via the new feature gate
    `ACMEHTTP01IngressPathTypeExact` (1.19 adds the gate to flip back).
- **CRD migrations:** None. CRD schema is additive.
- **Upgrade ordering:** Apply CRDs before controller. From 1.17: standard
  Helm upgrade path.
- **Deprecations:** `ValidateCAA` feature gate removed (was deprecated; setting
  it now logs a warning and does nothing — #7553). `UseDomainQualifiedFinalizer`
  promoted to GA. `AdditionalCertificateOutputFormats` promoted to GA (always
  on).
- **Notable:** Adds ACME profiles extension support (draft RFC). New `iss` /
  `ciss` short names for `kubectl get`. Vault issuer gains `serverName` for SNI
  validation. Venafi issuer rebranded internally to CyberArk (no API change).

## 1.17.0 (2025-02-03, EOL 2025-10-07)

- **k8s floor:** 1.29 – 1.33 (latest patch: 1.17.4, 2025-07-02). **Floor jumped
  from 1.25 (1.16) → 1.29 here** — operators on k8s 1.25–1.28 cannot land on
  1.17; must bump k8s first or stay on 1.16.x.
- **Breaking:**
  - CA / SelfSigned issuers now use SHA-384 for RSA ≥ 3072-bit and SHA-512 for
    RSA ≥ 4096-bit signatures (#7368). Previously always SHA-256. Validate
    downstream verifiers (legacy HSMs, older Java truststores) accept the new
    hash before upgrade if you mint large RSA CAs.
  - Unstructured controller log lines replaced with structured logs (#7461) —
    log-scrapers / Loki / Splunk alerts that grep raw strings will go silent.
- **CRD migrations:** None. Schema additive — adds literal `keystores.jks
  .password` / `keystores.pkcs12.password` fields, mutually exclusive with the
  existing `passwordSecretRef`.
- **Upgrade ordering:** Apply CRDs before controller. From 1.16: standard Helm
  upgrade path — but k8s floor jump (see above) is the gating constraint.
- **Deprecations:** `ValidateCAA` feature gate deprecated, scheduled for removal
  in 1.18 (carried through — see 1.18 section). Enabling it in 1.17 only logs a
  warning.
- **Notable:** `NameConstraints` and `UseDomainQualifiedFinalizer` feature gates
  promoted to Beta (on by default). New `CAInjectorMerging` feature gate added
  (alpha, off by default — promoted to Beta in 1.19). Helm gains
  `webhook.extraEnv` / `cainjector.extraEnv` / `startupapicheck.extraEnv`. New
  Azure DNS `tenantID` field for managed-identity + service-principal combos.
  Security fix GHSA-r4pg-vg54-wxx4 (low: PEM-size DoS in controller) shipped in
  1.17.0; later patches 1.17.1–1.17.4 are bug-only (no compat impact).

## Matrix vs release-notes discrepancy

The matrix page lists 1.18 as "Recently EOL'd" (EOL 2026-03-10 when 1.20
shipped) but supports k8s 1.29–1.33, which means **1.18 has no overlap with
k8s 1.34 or 1.35**. If operators are still on 1.18 in 2026-05-28, any plan
to bump k8s past 1.33 requires bumping cert-manager to ≥1.19 (k8s 1.31–1.35)
first. Verdict-relevant: 1.18 on k8s 1.34+ is unsupported by the matrix
even though the release-notes never call it out — matrix is authoritative.

1.17 sits below the floor entirely: 1.29–1.33 means **1.17 has no overlap
with k8s 1.34+**, and at 2026-05-28 1.17 has been EOL since 2025-10-07. Any
cluster still on 1.17 is unsupported regardless of the k8s minor — citation:
matrix row "1.17 → 1.29 → 1.33" (cert-manager.io/docs/releases) cross-checked
against v1.17.0 / v1.17.4 release notes (no contradicting floor signal).
