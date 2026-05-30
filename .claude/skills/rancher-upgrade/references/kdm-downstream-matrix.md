# kdm-downstream-matrix.md — which downstream k8s a Rancher minor can manage

**Grounded via `gh` + live `data.json` + SUSE 2.14.1 matrix: 2026-05-30.** This is the load-bearing
gap that the per-cluster compat tooling does not cover: it prevents a host-Rancher bump from
stranding its sub-clusters.

## What KDM is and how the gate works

**Kontainer Driver Metadata (KDM)** — repo `rancher/kontainer-driver-metadata`, file
`data/data.json` — tells a running Rancher which downstream RKE2/K3s Kubernetes versions it may
provision/manage, plus per-version system images, server/agent args, and addon chart versions. The
modern downstream data lives under the top-level **`rke2`** and **`k3s`** objects (the legacy
`K8sVersion*` / `RancherDefaultK8sVersions` keys are RKE1-era).

Each entry in `rke2.releases[]` / `k3s.releases[]` carries **`minChannelServerVersion`** and
**`maxChannelServerVersion`**. A running Rancher `vX.Y.Z` offers a downstream k8s version **iff
`minChannelServerVersion ≤ vX.Y.Z ≤ maxChannelServerVersion`**. The `.99` cap (e.g. `v2.14.99`)
means "the whole 2.14 minor". The `releases[]` array holds k8s versions back to ~1.18, but the
channel window filters that to the ~3 minors actually offered — never read "what's in KDM" as
"what's offered".

Inspect live:
```bash
curl -s https://releases.rancher.com/kontainer-driver-metadata/release-v2.14/data.json \
 | jq -r '.rke2.releases[] | [.version,.minChannelServerVersion,.maxChannelServerVersion] | @tsv' \
 | grep -E '^v1\.3[0-5]\.'
```

## The matrix (grounded; SUSE 2.14.1 corroborates the 2.14 row exactly)

Rolling 3-minor window per Rancher minor — **downstream support, independent of the mgmt-cluster
k8s window**:

| Rancher minor | Downstream RKE2/K3s k8s minors it can provision/manage |
|---------------|--------------------------------------------------------|
| 2.11 | **1.30, 1.31, 1.32** |
| 2.12 | **1.31, 1.32, 1.33** |
| 2.13 | **1.32, 1.33, 1.34** |
| 2.14 | **1.33, 1.34, 1.35** |

Live channel windows confirming the new edge (release-v2.14 `data.json`): k8s 1.33 = `[v2.12.0,
v2.14.99]`, 1.34 = `[v2.13.0, v2.14.99]`, 1.35 = `[v2.14.0, v2.14.99]`.

**Windows extend per KDM branch.** The max for a fixed k8s minor moves up across `release-v2.X`
branches as newer Rancher qualifies it. So the answer to "can Rancher 2.X run downstream k8s 1.Y"
must be read from the **`release-v2.X` branch matching the running Rancher**, not a single branch.

## Decoupling rule & stranding

Docs, verbatim: introducing a downstream k8s **minor** requires upgrading Rancher; **patch**
versions arrive via a KDM refresh **without** a Rancher upgrade. Failure modes:

- **Upper-edge drop (the dangerous one):** a downstream still on the trailing minor (e.g. 1.30 under
  Rancher 2.11) falls out of **every** window from the next Rancher minor on (1.30 max =
  `v2.11.99`). Upgrading the host Rancher 2.11→2.12 leaves that downstream **unmanageable** until
  it's first lifted to 1.31+. **→ Lift trailing downstreams into the target Rancher's window BEFORE
  upgrading the host.**
- **Lower-edge gap:** a brand-new minor (1.35, min `v2.14.0`) is unprovisionable on Rancher 2.13 no
  matter how fresh the KDM mirror — refresh adds *patches* of in-window minors, never a new *minor*.
  New minor ⇒ upgrade Rancher + re-mirror the matching `release-v2.X` KDM + system images.

## Air-gapped KDM & system-charts

Two supported postures:

1. **Mirror the metadata.** Set the `rke-metadata-config` setting → `refresh-interval-minutes: 0`
   (stops live-refresh log spam) and point its `url` at an internal mirror of `data.json` ("must be
   a direct path to a JSON file"). Pull updates by re-syncing the mirror + the UI **Cluster
   Management → Drivers → Refresh Kubernetes Metadata** action. Default upstream URL form:
   `https://releases.rancher.com/kontainer-driver-metadata/release-v2.X/data.json`.
2. **Bundled (most air-gap installs).** `helm --set useBundledSystemChart=true` (or env
   `CATTLE_SYSTEM_CATALOG=bundled`) makes Rancher use the KDM + system-charts **baked into the
   Rancher container image**. Then a new Rancher *image* alone carries the new `release-v2.X`
   branch — no separate KDM mirror step — but bundled mode cannot refresh/sync between image bumps.

Either way, on a Rancher upgrade you must also mirror the **per-k8s-version system images** the new
KDM entries reference into your private registry (via `system-default-registry` /
`CATTLE_BASE_REGISTRY`) and, for downstream RKE2, the matching rke2 tarballs/images — see
`air-gap-procedure.md`. **Pinning the mirror to an old `release-v2.X` branch silently caps the
fleet** at the old window even after the Rancher upgrade.

Relevant settings (source `pkg/settings/setting.go`): `kdm-branch` (hardcoded `release-v2.X` per
Rancher release; env `CATTLE_KDM_BRANCH`), `rke-metadata-config`, `chart-default-branch`.
