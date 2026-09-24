# cilium — compat (sifted from published_matrix)

- **Primary source:** https://docs.cilium.io/en/stable/network/kubernetes/compatibility/
- **Secondary sources:** https://github.com/cilium/cilium/releases, https://docs.cilium.io/en/v1.20/operations/upgrade/, https://docs.cilium.io/en/v1.19/operations/upgrade/, https://docs.cilium.io/en/v1.18/operations/upgrade/, https://docs.cilium.io/en/v1.17/operations/upgrade/
- **Truth source type:** `published_matrix`
- **Axis type:** `single`
- **min_tracked_version:** 1.17
- **Last sifted:** 2026-09-24 — added `## 1.20.0` (was header-note-only since GA). Latest patch per line re-enumerated: **1.20.2**, **1.19.8**, **1.18.14** (all 2026-09-16), **1.17.18** (2026-07-16, unchanged). The 1.20.1→1.20.2, 1.19.7→1.19.8, 1.18.13→1.18.14 hops are bugfix/CI-only — no compat-verdict change. `v1.21.0-pre.2` (2026-09-09) remains pre-release only, not GA.
- **Last release-verified:** 2026-09-24
- **k8s windows (re-read 2026-09-24 off the per-minor pages, all unchanged):** 1.20 → 1.33–1.36 · 1.19 → 1.32–1.35 · 1.18 → 1.30–1.33 · 1.17 → 1.29–1.32. Support policy verbatim: *"Three stable branches are maintained at a time: One for the most recent minor release, and two for the prior two minor releases"* — in-scope set is **1.20/1.19/1.18**; 1.17 is out-of-window but kept below (equals `min_tracked_version`).

CRD schema versions per minor, unchanged since the 2026-09-15 sift (no bump in the 2026-09-16 patches): 1.17.x → 1.30.8, 1.18.x → **1.31.12**, 1.19.x → **1.32.7**, 1.20.x → **1.33.11**. **Cite the per-minor URL, not `/en/stable/`** — the `stable` alias follows whichever minor is current. CNP/CCNP API stays `cilium.io/v2` across all four minors.

**Benign kernel-noise (kernel 6.17, cross-Cilium-version) — do not escalate.** On
Linux **6.17** (e.g. after an RKE2/OS bump pulls 6.17.0-35-generic) the agent emits
a once-per-boot kernel `WARN`: `verifier bug: REG INVARIANTS VIOLATION …
reg_bounds_sanity_check+0x.. at kernel/bpf/verifier.c:2752`, `Comm=cilium-agent`.
**Cosmetic** — it's a `WARN_ONCE` that does **not** reject the BPF program;
`cilium status` is healthy, all pods stay managed, the dataplane is fine. Triggered
by Cilium's tc/`cls_bpf` datapath (observed with 1.19.4). Track it for a future
kernel bump; ignore operationally. (Cross-ref: this is **not** Tetragon — see
`compat/tetragon.md` § Kernel axis for why a Tetragon trigger of the same verifier
path is masked.) Field-observed 2026-05-30.

## 1.20.0

- **k8s floor:** 1.33 – 1.36 (e2e-tested, per `docs.cilium.io/en/v1.20/network/kubernetes/compatibility/`). 1.20.0 release highlights confirm the dependency bump to Kubernetes v1.36.
- **Breaking:**
  - Envoy Go Extensions (proxylib) **removed** (deprecated since 1.18). Any `CiliumNetworkPolicy`/`CiliumClusterwideNetworkPolicy` with `.spec.ingress[].toPorts[].rules` / `.spec.egress[].toPorts[].rules` sub-fields `kafka`, `l7`, or `l7proto` must have those rules stripped **before** upgrading.
  - Gateway API support now requires **Gateway API ≥ v1.6.1** (TLSRoute moves v1alpha2 → v1). Clusters using `TLSRoute` must install the v1.6.1 Experimental CRD bundle (still carries v1alpha2) and back up existing `TLSRoute` objects before upgrading Cilium — installing the v1.6 Standard CRD instead makes existing `TLSRoute` objects unreadable from etcd.
  - Default CNI config version moves to **1.0.0** (was 0.3.1). Custom CNI configs should request the new version.
  - `CiliumNetworkPolicy`/`CiliumClusterwideNetworkPolicy` with neither `spec` nor `specs` are now **rejected at admission** (CEL validation) instead of silently accepted; pre-existing empty policies are grandfathered.
  - Mutual Authentication (Beta) is now **deprecated** (already off-by-default since 1.19) — plan migration to Ztunnel Transparent Encryption.
- **CRD migrations:**
  - `CiliumNodeConfig`: `cilium.io/v2alpha1` → `cilium.io/v2` — update manifests/tooling that still reference the old API version.
  - MCS-API CRDs move to `v1beta1`; `v1alpha1` remains fully supported, migrate `ServiceExport` resources when convenient.
- **Upgrade ordering:** strip Kafka/L7/`l7proto` CNP rules and confirm Gateway API ≥ v1.6.1 (with the TLSRoute Experimental CRD if in use) **before** rolling agents to 1.20.
- **Deprecations:**
  - BGP peer/route/route-policy listing via the local REST API and `cilium-dbg bgp` — use `cilium shell -- bgp/*` instead.
  - Azure IPAM `status.azure.interfaces[].addresses[].subnet` and flat `status.azure.interfaces[].cidr` — mirrored for one release, then removed; read `status.azure.interfaces[].subnet` instead.
- **Cross-component:** RKE2 1.37.0 bundles Cilium **v1.20.1** (chart `rke2-cilium 1.20.103`) — generated.json (compat.py sync 2026-09-24).
- **Notable:** Gateway API bumped to v1.6.1 (from v1.4). GoBGP moves to v4.6.1. `cilium-cni` binary shrunk ~77 MB → ~16 MB. CRD schema version 1.33.11.

## 1.19.0

- **k8s floor:** 1.32 – 1.35 (e2e-tested, per `docs.cilium.io/en/v1.19/network/kubernetes/compatibility/`). Discrepancy: 1.19.0 release notes claim "Cilium dependencies were updated to Kubernetes v1.35" — the lower bound shifted to 1.32 vs 1.18's 1.30, so a cluster on k8s 1.30/1.31 falls outside the tested set on a 1.18 → 1.19 bump.
- **Cross-component:** RKE2 1.34–1.36 bundle Cilium **v1.19.6** (chart `rke2-cilium 1.19.601`) — generated.json (compat.py sync 2026-09-24).
- **Breaking:**
  - `CiliumBGPPeeringPolicy` (v1 BGP API) **removed**. Must migrate to v2 BGP CRDs (`CiliumBGPClusterConfig` et al.) **before** the agent rolls.
  - DNS NetworkPolicy `**.` wildcard now actually matches multilevel subdomains (was treated as `*.`). Audit any `matchPattern: "**.example.com"` — semantics widened.
  - `policy-default-local-cluster` now **on by default**. Policies that previously selected endpoints across all ClusterMesh clusters now only select local. Add explicit cluster selectors to cross-cluster policies before upgrade.
  - Mutual Authentication (`mesh-auth-enabled`) defaults to **off**. Re-enable explicitly if mTLS policies are in use.
  - `clustermesh.apiserver.tls.authMode` defaults to `migration`. With `clustermesh.useAPIServer=true` and no `clustermesh.config.enabled`, must create the `clustermesh-remote-users` ConfigMap or pin `authMode=legacy`.
- **CRD migrations:**
  - `CiliumLoadBalancerIPPool`: `cilium.io/v2alpha1` → `cilium.io/v2` before upgrade.
  - All BGP v2 CRDs already at `cilium.io/v2` (promoted in 1.18); v1 `CiliumBGPPeeringPolicy` gone.
- **Upgrade ordering:** migrate BGP v1 → v2 CRDs and `CiliumLoadBalancerIPPool` to v2 **before** rolling agents. ClusterMesh policy audit must precede the agent roll or cross-cluster traffic drops.
- **Deprecations:**
  - `FromRequires` / `ToRequires` CNP fields enforced-empty (kept-but-deprecated in 1.18 → no-op in 1.19).
  - Kafka protocol matcher in CNP deprecated.
  - `--aws-pagination-enabled` → `--aws-max-results-per-call`.
  - `--enable-ipsec-encrypted-overlay` is a no-op, removal slated for 1.20.
  - `--enable-encryption-strict-mode` variants → egress-specific replacements.
  - `clustermesh.enableMCSAPISupport` → `clustermesh.mcsapi.enabled`.
- **Removed flags (deprecated in 1.18, gone now):** `--bpf-lb-proto-diff`, `--enable-recorder`, `--enable-session-affinity`, `--enable-internal-traffic-policy`, `--enable-svc-source-range-check`, `--enable-node-port`, `--enable-host-port`, `--enable-external-ips`, `--enable-custom-calls`, `--enable-ipv4-egress-gateway`, `--egress-multi-home-ip-rule-compat`, `--l2-pod-announcements-interface`.
- **Notable:** `--unmanaged-pod-watcher-interval` type changed int-seconds → `time.Duration` (e.g. `15s`). Helm `operator.unmanagedPodWatcher.intervalSeconds` still accepts both. Helm charts also published to OCI at `quay.io/cilium/charts/cilium`. Gateway API bumped to v1.4.

## 1.18.0

- **k8s floor:** 1.30 – 1.33 (e2e-tested, per `docs.cilium.io/en/v1.18/network/kubernetes/compatibility/`). 1.18.0 release notes confirm dependency bump to k8s v1.33.
- **Breaking:**
  - **Hard kernel floor: Linux 5.10+** (RHEL 8.6 or similar). 1.17 had no such explicit floor — nodes on 5.4/older RHEL 8.5 will break on agent restart.
  - High-scale ipcache mode **removed**.
  - External Workloads feature **removed entirely**.
  - Docker mode `--datapath-mode=lb-only` **removed**.
  - `cilium-docker-plugin` **removed**.
  - Single-IPsec-key support gone; per-tunnel keys required (deprecation landed in 1.17, removal in 1.18).
  - `policy-default-local-cluster` flag introduced (defaults off in 1.18, **on in 1.19**) — start preparing cross-cluster policy selectors now or 1.19 upgrade breaks ClusterMesh traffic.
  - ENI mode `enableIPv4Masquerade` default flipped `true` → `false`. Set `upgradeCompatibility=1.X` to preserve prior behaviour during rollout.
  - Identity label set gains `io.cilium.k8s.policy.serviceaccount` — temporary identity-count spike + possible packet drops during upgrade window.
- **CRD migrations:**
  - All BGP CRDs (`CiliumBGPClusterConfig`, `CiliumBGPPeerConfig`, `CiliumBGPAdvertisement`, `CiliumBGPNodeConfigOverride`) promoted: `cilium.io/v2alpha1` → `cilium.io/v2`. Old apiVersion still served but write the new one.
  - `CiliumCIDRGroup`: `v2alpha1` → `v2` (promoted stable).
  - `CiliumLoadBalancerIPPool`: stable, still at v2alpha1 in 1.18 (v2 migration is the 1.19 ask).
- **Upgrade ordering:** kernel upgrade (≥ 5.10) **before** agent roll; node-by-node node drain works. IPsec users: from 1.17 → 1.18 needs extra care; on GKE update firewall rules to permit ESP.
- **Deprecations (removed in 1.19):**
  - `--bpf-lb-proto-diff`, `--enable-recorder`, hubble-recorder flags.
  - `--enable-session-affinity` (unconditionally on), `--enable-internal-traffic-policy`, `--enable-svc-source-range-check`, `--enable-node-port`, `--enable-host-port`, `--enable-external-ips`.
  - `--enable-custom-calls`, `--enable-ipv4-egress-gateway` (use generic egress gateway).
  - `--egress-multi-home-ip-rule-compat`, `--l2-pod-announcements-interface`.
  - Hubble exporter configuration options.
  - `--enable-k8s-terminating-endpoint`, CONNTRACK_LOCAL, ARP refresh period config — all gone in 1.18 itself.
- **Notable:** Migrated to slog across all components (operator log parsing may need updates). LLVM 19.1, Envoy v1.34, CNI v1.1.

## 1.17.0

- **k8s floor:** 1.29 – 1.32 (e2e-tested, per `docs.cilium.io/en/v1.17/network/kubernetes/compatibility/`).
- **Breaking:**
  - **Consul support removed** (deprecated since 1.12).
  - **In-pod etcd management removed** — external etcd is now mandatory for KVStore deployments.
  - L7 proxy-visibility Pod annotation `policy.cilium.io/proxy-visibility` **removed** (deprecated 1.15).
  - **Single-IPsec-key removed**, per-tunnel keys required.
  - `metallb-bgp` integration and flags (`bgp-config-path`, `bgp-announce-lb-ip`, `bgp-announce-pod-cidr`) removed. Migrate to Cilium BGP control plane.
  - WireGuard userspace fallback (`wireguard.userspaceFallback`) removed; needs in-kernel WireGuard.
  - `cilium-health status --probe` (synchronous) no longer functional.
  - Cluster name strictly validated: ≤32 chars, lowercase alphanumeric + `-`. Long names break upgrade.
  - **Service protocol differentiation on by default** — pre-existing Services without protocol set must be deleted and recreated to use the new path.
- **CRD migrations:** none required at 1.17.0.
- **Upgrade ordering:** if running in-pod etcd, migrate to external etcd **before** 1.17. If using metallb-bgp, migrate to Cilium BGPv2 **before** 1.17.
- **Deprecations (removed in 1.18):**
  - High-scale ipcache mode.
  - External Workloads.
  - `cilium-docker-plugin`.
  - `--k8s-watcher-endpoint-selector`, `--enable-k8s-terminating-endpoint`.
  - `--datapath-mode=lb-only`.
- **Notable:**
  - Operator k8s-client default rate limits raised to 100 QPS / 200 Burst (configurable via `--operator-k8s-client-qps` / `--operator-k8s-client-burst`).
  - TLS secrets handling restructured: `tls.secretsBackend` → `tls.readSecretsOnlyFromSecretsNamespace`; new `tls.secretSync` controls SDS. **Upgraded clusters default `tls.secretSync.enabled: false`** — fresh installs get SDS, upgrades do not.
  - MTU auto-detect now picks the lowest MTU across external interfaces (not just primary).
  - Gateway API bumped to v1.2.1.
