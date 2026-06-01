# The version ladder, the edition reality, the target, and version detection

## The ladder (no minor skipping)

Authoritative: Harvester docs `upgrade/automatic.md` (supported-paths table + component table + the k8s
version-skew note). The only supported paths are one minor at a time:

```
1.5.x → 1.6.x → 1.7.x → 1.8.x
```

- No `1.5→1.7` or `1.6→1.8` row exists. Each Harvester minor bumps embedded RKE2 exactly one k8s minor, and
  skipping a k8s minor is unsupported upstream (version-skew policy).
- You **may** skip intermediate **patches** within a jump: `1.5.2 → 1.6.1` directly is supported and is the
  recommended way (land on each minor's latest patch). Any `1.5.x` goes to `1.6.x` — you do not need to install
  1.5.1/1.5.2 first.
- **Never hand-edit embedded RKE2** — it is locked to the Harvester version and rides with the bundle.
  Hand-editing bricks the node (`compat/harvester.md` ordering rule).

### Per-minor bundled stack (`automatic.md` component table)

| Component | 1.5.x | 1.6.x | 1.7.x | 1.8.x |
|---|---|---|---|---|
| KubeVirt | v1.4 | v1.5 | v1.6 | v1.7 |
| Longhorn | v1.8 | v1.9 | v1.10 | v1.11 |
| **Rancher (pair)** | **v2.11** | **v2.12** | **v2.13** | **v2.14** |
| RKE2 (embedded) | v1.32 | v1.33 | v1.34 | v1.35 |
| **SUSE Linux Micro** | 5.5 | **5.5** | **6.1** | **6.2** |

The OS base bump lands at **1.7 (5.5→6.1)** and again at **1.8 (6.1→6.2)** — none at 1.5→1.6. The Rancher pair
is what couples this to the external Rancher (`external-rancher-coupling.md`).

## Editions — community vs Prime (corrected; House Rule #1)

**Patch releases are community.** SUSE's "SUSE Virtualization" / Prime is a **paid support subscription on the
same bits** — not a separate, paywalled artifact set. Evidence (verify the real artifact, never infer):

- Every patch ISO downloads publicly: `curl -I releases.rancher.com/harvester/<tag>/harvester-<tag>-amd64.iso`
  → **HTTP 200**, multi-GB, for v1.5.2 / v1.6.1 / v1.7.1 / v1.8.0.
- All are real GA releases (`gh release ... --json isPrerelease` → `prerelease=false`).
- Zero Prime-gating language in patch release notes. The only edition-ish line is v1.5.2's advisory: *"Only
  SUSE Virtualization customers affected by issues listed in the Bug Fixes section must install this patch"* —
  i.e. patches are *optional unless you hit a listed bug*, not paywalled.
- The official lifecycle doc (`automatic.md`): *"Four-month minor cadence (Apr/Aug/Dec); two-month patch
  cadence (best effort)"*, and the upgrade-path table literally uses **"from v1.5.2 to v1.6.1"** as the
  canonical community hop.

→ A community operator **can and should run the latest patch of each minor**. The path is **not `.0`-only**:
`1.5.x → 1.6.1 → 1.7.1`, not `1.5.0 → 1.6.0 → 1.7.0`.

> **Note for maintainers:** `k8s-components-checker/references/compat/harvester.md` historically claimed
> "`x.y.0`=community, `x.y.[1..z]`=Prime (paid)". That *mechanism* is wrong (its rough EOL dates may be fine).
> If that file still says this, fix it — verdicts that treat 1.6.1/1.7.1 as Prime-only will misdirect operators.

## Choosing the target ("latest stable")

"Latest stable" usually means the **newest minor that already has a patch released** and a settled Rancher
pair — **not** a fresh `.0`. For a controlled upgrade off EOL hardware hosting control planes:

- A first-of-minor `.0` (no patch yet, possibly experimental subsystems) is the early-adopter slot — avoid it.
- Landing one minor lower often **also** keeps the external Rancher one minor lower, dodging the newest Rancher
  minor's churn (e.g. a Rancher minor that removes embedded CAPI / flips CRDs one-way / bumps Fleet to Helm v4).
- Ground the actual latest patch of each minor via `gh` (House Rule #2, anti-confirmation), and apply
  look-ahead (House Rule #5): pick the target that also covers the next planned hop; re-evaluate a fresh `.0`
  once its `.1` ships.

State the chosen target with its grounded GA/patch evidence; do not assert a patch number from memory.

## Version detection on an air-gapped cluster (kubectl-only)

Do not assume the starting patch — read it.

```bash
# --- Harvester server version (authoritative running version) ---
kubectl get settings.harvesterhci.io server-version -o jsonpath='{.value}'; echo
kubectl get managedchart harvester -n fleet-local -o jsonpath='{.spec.version}'; echo   # deployed chart

# --- embedded RKE2 / Kubernetes (maps to the Harvester minor) ---
kubectl get nodes -o wide
kubectl get nodes -o jsonpath='{range .items[*]}{.status.nodeInfo.kubeletVersion}{"\n"}{end}'
#   v1.32.x → Harvester 1.5.x · 1.33 → 1.6.x · 1.34 → 1.7.x · 1.35 → 1.8.0

# --- bundled stack (sanity vs the component table above) ---
kubectl get kubevirt -n harvester-system -o jsonpath='{.items[*].status.observedKubeVirtVersion}'; echo
kubectl get settings.longhorn.io current-longhorn-version -n longhorn-system -o jsonpath='{.value}'; echo
#   fallback for any of these: kubectl get <res> -A -o yaml | grep -i version

# --- on the EXTERNAL Rancher (its local cluster): Rancher + harvester UI-extension ---
helm list -n cattle-system | grep rancher
kubectl get uiplugins.catalog.cattle.io -A \
  -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.plugin.version}{"\n"}{end}'
```

The exact 1.5 patch does not change the path (any 1.5.x → 1.6.x) but confirms the floor and whether a
patch-specific note applies. Map the result onto the ladder, then read `per-hop-runbook.md` for the first hop.
</content>
