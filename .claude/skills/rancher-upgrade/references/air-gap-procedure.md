# air-gap-procedure.md — what to mirror + the air-gapped upgrade sequence

**Grounded via `gh` release assets + ranchermanager/rke2 docs + source: 2026-05-30.** Asset names
and flags re-ground at use time. **Scope:** this file lists the Rancher-specific *inputs* to mirror
and the upgrade sequence. The actual registry-sync / chart-vendoring **mechanics** are the
operator's separate `air_gapped/` repo + the `helm` skill — reference those, don't re-derive generic
mirror steps here.

## What to mirror for a Rancher upgrade

**Per-release image-list assets (exact names on a `rancher/rancher` GitHub release — grounded on
v2.14.2):**

```
rancher-images.txt                 rancher-load-images.sh / .ps1
rancher-images-sources.txt         rancher-save-images.sh / .ps1
rancher-images-origins.txt         rancher-components.txt
rancher-images-digests-linux.txt   rancher-windows-images.txt
rancher-images-digests-windows.txt rancher-windows-images-sources.txt
images-digests-sha256sum.txt       sha256sum.txt
```

> Digest files are **`-linux` / `-windows` (by OS), NOT `-amd64`/`-arm64`.** `rancher-images.txt` is
> the master mirror input ("images to install Rancher, provision clusters, and run Rancher tools").

Mirror flow (mechanics → `air_gapped/` repo + `helm` skill):
```bash
./rancher-save-images.sh --image-list rancher-images.txt              # → rancher-images.tar.gz
./rancher-load-images.sh --image-list rancher-images.txt --registry <internal-registry:port>
```

**cert-manager images** are NOT in `rancher-images.txt` — append them first (third-party chart, so
`systemDefaultRegistry` does NOT cover it):
```bash
helm template ./cert-manager-<ver>.tgz | awk '$1 ~ /image:/{print $2}' | sed 's/"//g' >> rancher-images.txt
sort -u rancher-images.txt -o rancher-images.txt
```
Air-gap cert-manager install needs **4 images** (controller, webhook, cainjector, **cert-manager-ctl**
= startupapicheck) with each repo prefixed by the mirror, plus CRDs via `kubectl apply -f
cert-manager-crd.yaml` (not `--set installCRDs`).

**Agent / installer images** (`rancher-agent`, `cattle-cluster-agent`, `system-agent-installer-rke2/k3s`)
are already folded into `rancher-images.txt` by the build — once mirrored and `systemDefaultRegistry`
is set, downstream agents pull from the internal registry automatically. No separate artifact.

**KDM + system images** for the newly-unlocked downstream minors — see `kdm-downstream-matrix.md`
(bundled-in-image is the usual air-gap posture; otherwise mirror the `release-v2.X` `data.json`).

## The single registry switch

`--set systemDefaultRegistry=<reg:port>` (Helm) → Rancher `system-default-registry` setting (env
default `CATTLE_BASE_REGISTRY`) → propagates to fleet/hosted/system charts **and** downstream CAPR
provisioning. Assumed auth-free. This is what makes every Rancher + downstream system pod pull from
the internal mirror.

## The air-gapped `helm upgrade`

Differs from a connected upgrade in three ways: local `.tgz` (not a remote repo), mandatory registry
flags, and bundled system charts.

```bash
helm upgrade rancher ./rancher-<VERSION>.tgz \
  --namespace cattle-system \
  --set hostname=<RANCHER.FQDN> \
  --set image.registry=<reg:port> \
  --set systemDefaultRegistry=<reg:port> \
  --set useBundledSystemChart=true \
  --set certmanager.version=<CERTMANAGER_VERSION>     # self-signed path; OR --set ingress.tls.source=secret (+ privateCA=true)
```

- **`rancherImage*` flags are DEPRECATED** → use `image.registry` / `image.repository` / `image.tag`.
- `useBundledSystemChart=true` makes Rancher use the system-charts + KDM baked into its image
  ("used for air-gapped installations") — so the new Rancher image carries the new branch.
- If originally installed via rendered manifests: `helm template … --output-dir . --no-hooks <same
  --set flags>` then `kubectl -n cattle-system apply -R -f ./rancher`.

## agentTLSMode gotcha (carries across every 2.11→2.14 hop)

Fresh installs default **`strict`** (since 2.9); **upgrades default to `system-store`** to avoid
breaking agents. Before switching an air-gap install to strict, verify every downstream reports the
readiness condition — else `cattle-cluster-agent` can't validate the chain (private/external CA) and
loses reconnection:
```bash
kubectl get cluster.management.cattle.io -o jsonpath='{range .items[?(@.metadata.name!="local")]}{.metadata.name},{.status.conditions[?(@.type=="AgentTlsStrictCheck")].status}{"\n"}{end}'
```
All must be `True`.

## Downstream RKE2 air-gapped k8s upgrade

- **Rancher-managed clusters:** Rancher's system-agent drives the upgrade from KDM. **Do NOT
  hand-apply system-upgrade-controller (SUC) Plans** on Rancher-managed clusters (it fights Rancher's
  version management). Mirror the rke2 images/tarballs for the KDM-listed versions the Rancher
  upgrade unlocks; bump via the Rancher UI/cluster spec.
- **Standalone RKE2 (SUC path):** mirror `rancher/rke2-upgrade:<target>` (image tag = the RKE2
  version with `+`→`-`, e.g. `v1.34.5+rke2r1` → `v1.34.5-rke2r1`), `rancher/system-upgrade-controller`,
  `rancher/kubectl`; per-node tarballs (`rke2-images*.linux-amd64.tar.zst`, `rke2.linux-amd64.tar.gz`,
  `sha256sum-amd64.txt`, `install.sh`) into `/var/lib/rancher/rke2/agent/images/`. SUC Plans: **server
  (control-plane) before agent**; respect k8s version-skew (no minor skipping).
