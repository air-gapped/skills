# tetragon — compat (sifted from release_notes)

- **Primary source:** https://github.com/cilium/tetragon/releases
- **Secondary sources:** https://tetragon.io/docs/installation/faq/ (kernel floor + required `CONFIG_*`), `install/kubernetes/tetragon/Chart.yaml` at release tags (chart↔app mapping)
- **Truth source type:** `release_notes`
- **Axis type:** `multi`  (k8s axis is loose; the **kernel** axis is the load-bearing one)
- **min_tracked_version:** 1.5
- **Last sifted:** 2026-07-21 (re-probed: **1.7.0 still latest**, no 1.8 — entry unchanged)
- **Last release-verified:** 2026-05-30  (anchored on `gh api repos/cilium/tetragon/releases/latest` → `v1.7.0`; minors enumerated + `sort -V`; Chart.yaml read at `v1.7.0`/`v1.6.0`/`v1.5.0` tags)

In-scope set: current stable **1.7** + prior 2 (**1.6**, **1.5**). Latest patch
per line at sift (grounded by enumeration, none newer than `releases/latest` =
`v1.7.0`): **1.7.0**, **1.6.1**, **1.5.0**. Chart version == app version (1:1,
no chart/app skew — like cert-manager); the `tetragon` Helm chart sets **no
`kubeVersion:`** constraint, so there is no chart-metadata k8s gate.

Tetragon is Cilium's eBPF runtime-security / observability sibling
(`cilium/tetragon`, image `quay.io/cilium/tetragon`). It is a **separate
component from Cilium core** — independent release train, its own chart, and it
runs standalone (does not require Cilium as the CNI). Detection: shares the
`cilium.io` CRD api-group with Cilium, so it is identified by the
`tracingpolicies.cilium.io` CRD (and the `tetragon` DaemonSet /
`tetragon-operator` Deployment), **not** by the api-group alone. See
`references/cluster-survey.md`.

## Kernel axis — the dominant compatibility constraint

This is the axis that actually blocks a Tetragon deployment; the k8s minor
rarely does. Sources (all read at the `v1.7.0` tag / its release): the kernel
floor, arm64 caveat, BTF requirement, and `CONFIG_*` list are from
`tetragon.io/docs/installation/faq/`; the LSM-sensor kernel gate is from the
tracing-policy hooks doc; the ring-buffer default is from the 1.6.0 release
notes (tagged inline below).

- **Minimum kernel: Linux 4.19.** Tetragon CI runs LTS kernels **4.19, 5.4,
  5.10, 5.15, and bpf-next**. Not all features work on older kernels — upstream
  recommends the most recent stable kernel available.
- **arm64 floor is higher: 5.10+.** On arm64, kernels 4.19 and 5.4 have a kernel
  bug that breaks reading exec arguments (the fix was rejected from stable). For
  full functionality on arm64, use **≥ 5.10**.
- **BTF is required.** Tetragon needs `/sys/kernel/btf/vmlinux`
  (`CONFIG_DEBUG_INFO_BTF=y`) for CO-RE. Kernels built without BTF need a
  supplied BTF file or Tetragon fails to start. RKE2's common node OSes (SLE
  Micro, Ubuntu ≥ 20.04, RHEL/Rocky 8.2+) ship BTF; minimal/old images may not.
- **Enforcement (SIGKILL / override actions) needs `CONFIG_BPF_KPROBE_OVERRIDE=y`.**
  Without it, observation works but `Sigkill`/`Override` TracingPolicy actions
  silently do not enforce. Verify with `tetra probe` (`override_return: true`).
- **The LSM sensor needs `CONFIG_BPF_LSM=y`** (kernel ≥ 5.7, and `lsm=bpf` on the
  kernel cmdline; source: tracing-policy hooks doc). `tetra probe` reports
  `lsm: true/false`.
- **BPF ring buffer is the default from kernel ≥ 5.11** (changed in 1.6; source:
  1.6.0 release notes). On older kernels Tetragon falls back to the perf ring
  buffer — functional, but the event path differs.
- **cgroup v1 on kernel ≥ 6.11** additionally requires `CONFIG_MEMCG_V1=y` and
  `CONFIG_CPUSETS_V1=y` for process/pod tracking. `CGROUP_FAVOR_DYNMODS=y`
  (optional, ≥ 6.0) reduces pod/container association issues on churny nodes.
- **Benign-noise (kernel 6.17), and why it isn't Tetragon's:** a once-per-boot
  BPF verifier `WARN` (`reg_bounds_sanity_check … verifier.c:2752`) on kernel 6.17
  is attributed to `Comm=cilium-agent` and comes from the tc/`cls_bpf` datapath —
  **Tetragon uses kprobe/fentry, not `cls_bpf`, so it is not the trigger.** Because
  it's a `WARN_ONCE` and Cilium loads first, a Tetragon attachment that hit the same
  verifier path would be **masked** — the observable trigger surfaces as Cilium.
  Cosmetic; does not reject the program. Full detail: `compat/cilium.md` (intro,
  benign kernel-noise).
- **Self-check, no guessing:** `tetra probe config` (kernel `CONFIG_*`) and
  `sudo tetra probe` (runtime feature probe) report exactly what the running
  kernel supports. Run on a representative node before any upgrade that changes
  the node OS/kernel.

**Verdict guidance.** For a k8s anchor bump (e.g. 1.32 → 1.33), Tetragon is
almost always `✓ ready` on the k8s axis — but the row's reason must point at the
kernel: confirm the post-upgrade **node image/kernel** still meets the floor
above (≥ 4.19, ≥ 5.10 arm64, BTF present, plus the `CONFIG_*` for any
enforcement/LSM policies in use). A node-OS bump bundled with the k8s upgrade is
the real risk, not the k8s minor.

## k8s axis — loose, no published matrix

- Tetragon publishes **no formal Kubernetes support matrix**, and the `tetragon`
  chart carries **no `kubeVersion:`**. It runs as a DaemonSet (agent) + a
  Deployment (`tetragon-operator`, manages CRDs) and works on any currently
  supported k8s minor.
- CRDs are `cilium.io/v1alpha1` (`TracingPolicy`, `TracingPolicyNamespaced`,
  `PodInfo`). **No CRD version migration across 1.5 → 1.7** — the upgrade notes
  for all three minors contain no CRD rename/conversion step.
- The operator manages CRD install/upgrade; standard k8s-version-skew rules for
  a controller using `controller-runtime` apply, but nothing in 1.5–1.7 sets a
  hard k8s floor.

## 1.7.0

- **k8s floor:** loose (unchanged). Kernel floor unchanged (see Kernel axis).
- **Breaking (protobuf/gRPC API):**
  - Legacy **stacktrace-tree API removed**: `GetStackTraceTree` gRPC, the
    `tetra stacktrace-tree` CLI command, `stack.proto`, and related types are
    gone. Migrate to TracingPolicy `kernelStackTrace` / `userStackTrace` in the
    `Post` action to get stack traces in `ProcessKprobe` events.
  - `EnableTracingPolicy` / `DisableTracingPolicy` gRPC methods (already
    deprecated) **now return an error** when used. Temporary opt-out:
    `enable-deprecated-tracingpolicy-grpc`. **The next release removes them
    entirely** — migrate any controller that toggles policies over gRPC.
- **Helm:** default agent **server-address changed** `localhost:54321` →
  `/var/run/tetragon/tetragon.sock`. Any third-party program / sidecar that
  connects to the agent must update the address.
- **Metrics (breaking for dashboards/alerts):** `tetragon_generic_kprobe_merge_errors_total`
  and `tetragon_generic_kprobe_merge_ok_total` **removed**, consolidated into
  `tetragon_generic_kprobe_merge_total` with a `status="ok"|"error"` label (plus
  `curr_type`/`prev_type`/`curr_fn`/`prev_fn`). Update Prometheus rules.
- **CRD migrations:** none.
- **Notable:** CEL-in-BPF policy evaluation, `fentry` sensor, `matchParentBinaries`
  and `spec.hostSelector` selectors, env-var retrieval; policies now load even
  when `kptr_restrict=2`.

## 1.6.0  (latest patch 1.6.1)

- **k8s floor:** loose (unchanged). Kernel floor unchanged.
- **Helm (behavior change — watch on restrictive clusters):** the
  **tetragon-operator now defaults to non-root** (UID **65532**). Set
  `tetragonOperator.runAsRoot: true` to restore the previous root behavior.
  Check this against restrictive PodSecurity / SCC or any hostPath the operator
  needs to write.
- **Helm (deprecation):** `tetragonOperator.securityContext` deprecated in favor
  of `tetragonOperator.containerSecurityContext` (old still honored, may be
  removed later).
- **Removed:** the deprecated `enable-process-ancestors` boolean flags (the ones
  deprecated in 1.5 — see below). Switch to `--enable-ancestors`.
- **CRD migrations:** none.
- **Notable:** BPF **ring buffer becomes the default on kernel ≥ 5.11** (older
  kernels fall back to perf buffer); USDT sensor added; non-k8s deployment can
  now run the k8s control plane disabled.

## 1.5.0

- **k8s floor:** loose (unchanged). Kernel floor unchanged.
- **Deprecations (removed in 1.6):** the per-type process-ancestors flags
  `--enable-process-ancestors`, `--enable-process-kprobe-ancestors`,
  `--enable-process-tracepoint-ancestors`, `--enable-process-uprobe-ancestors`,
  `--enable-process-lsm-ancestors` are replaced by a single `--enable-ancestors`.
- **Logging (breaking for log parsers):** migrated `logrus` → `log/slog`;
  `level=warning` is now `level=warn`. Update any log-scraping regex.
- **Helm:** default ServiceMonitor `scrapeInterval` raised **10s → 60s** for both
  agent and operator (`tetragon.prometheus.serviceMonitor.scrapeInterval`,
  `tetragonOperator.prometheus.serviceMonitor.scrapeInterval`). Metrics
  resolution drops unless overridden.
- **Removed:** `OciHookSetup` Helm section (deprecated in 1.2).
- **CRD migrations:** none.
