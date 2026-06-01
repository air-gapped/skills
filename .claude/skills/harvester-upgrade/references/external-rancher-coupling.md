# External Rancher coupling — the hard gate at every hop

When Harvester is **imported into an external/central Rancher** (not standalone embedded-only), the external
Rancher version *gates* the Harvester version, and the external Rancher must move first.

## The three-step order (per hop, mandatory)

Source: `docs/rancher/virtualization-management.md` (Upgrades) + `docs/upgrade/automatic.md` (*"you must
upgrade Rancher **before** upgrading Harvester"*).

```
1. Upgrade the EXTERNAL Rancher        → to the paired minor
2. Upgrade the Harvester UI Extension  → to the matching minor (in that Rancher)
3. Upgrade Harvester
```

The two upgrade *processes* are independent (Harvester stays reachable on its VIP during the Rancher bump) —
only the **order** is mandatory.

## The required pairing

`harvester-ui-extension.md` support matrix + `compat/harvester.md`:

| Harvester | needs Rancher ≥ | needs harvester-ui-extension | air-gap `ui-plugin-catalog` image |
|---|---|---|---|
| 1.5.x | 2.11.0 | 1.5.x | 4.0.5 |
| 1.6.x | 2.12.0 | 1.6.x | 4.1.0 |
| 1.7.x | 2.13.0 | 1.7.x | 4.13.0 |
| 1.8.x | 2.14.0 | 1.8.x | 4.23.0 |

- The **UI extension is the join of both axes** — its minor must match the Harvester minor *and* be supported
  by the Rancher minor. For an external Rancher you must **install/upgrade it yourself** (the embedded path
  ships it inside the ISO; external does not).
- **Mismatch failure mode:** "VM tab missing" / cluster shown but unmanageable / Harvester features absent
  (`virtualization-management.md`; `compat/harvester.md`). Using a Rancher a minor behind/ahead of the pair is
  the #1 cause of these tickets.

## Air-gapped UI-extension install

Network install is impossible air-gapped. Instead (`docs/airgap.md`):
1. Mirror the **`ui-plugin-catalog` image** matching the extension version (table above) into the private
   registry.
2. Rancher → **Extensions → Manage Extension Catalogs**, add the catalog from that image, with an image-pull
   secret in namespace `cattle-ui-plugin-system`.
3. Install/upgrade the `harvester` extension to the matching minor.

Debug a stuck extension: `kubectl get uiplugins -A` and check `ui-plugin-catalog-svc` endpoint reachability.

## The interleaved 1.5→1.7 sequence (target 1.7.x example)

```
Rancher 2.11→2.12  →  UI-ext →1.6.x  →  Harvester 1.5.x→1.6.x
Rancher 2.12→2.13  →  UI-ext →1.7.x  →  Harvester 1.6.x→1.7.x
( + Rancher 2.13→2.14 → UI-ext →1.8.x → Harvester 1.7.x→1.8.x  — only if going to 1.8 )
```

Each Harvester step is gated on the external Rancher *already being at* the paired minor. Neither axis may skip
a minor.

## The external Rancher's own chain is the real prerequisite — defer to `rancher-upgrade`

To reach the pairs above, the external Rancher must itself walk 2.11→2.12→2.13(→2.14), no minor skipping. The
gates that can block the campaign live in the **`rancher-upgrade`** skill — cite it, don't re-derive:

- **cert-manager** must be in the chart-supported window before each Rancher bump (hard at 2.14: the version-
  check shims are removed).
- **Helm client ≥ 3.18** from Rancher 2.12 onward.
- **RKE1 sweep** gates entry to 2.12 — delete stale RKE1 `cluster.management.cattle.io` or the helm upgrade
  fails. (Likely a non-event if guests are self-managed RKE2, but the check still fires against the mgmt
  cluster's resource set.)
- **2.14 = a one-way boundary:** embedded CAPI removed → Rancher Turtles, CAPI CRDs bumped to v1beta2
  (one-way rollback), Fleet → Helm v4, Google OAuth broken in 2.14.0 (use 2.14.1+). Reason in itself to stop a
  controlled campaign at the 1.7/Rancher-2.13 rung unless 1.8/2.14 is specifically needed.
- **mgmt-cluster k8s window** per Rancher minor (`compat/rancher.md`): 2.13 = k8s 1.32–1.34; 2.14 = 1.33–1.35
  (drops 1.32). Reaching only 2.13 likely needs no mgmt-cluster k8s bump; **only 2.14 forces the mgmt cluster
  off 1.32**.
- **Back up the Rancher mgmt cluster's RKE2 etcd before each Rancher step** (the real rollback floor).

## Scope — self-managed guest RKE2 clusters are OUT of Rancher's provisioning path

If the guest RKE2 clusters are **not Rancher-provisioned**, Rancher's KDM downstream matrix does **not** gate
them and the Rancher upgrade does **not** touch them (`compat/rancher.md`; `kdm-downstream-matrix.md`). The only
Rancher concern is managing the **Harvester** cluster itself.

**Exception:** the *Harvester* upgrade (not the Rancher upgrade) touches guests indirectly — moving guest RKE2
to 1.35 hits harvester#10188 (CNI Pending; need RKE2 ≥1.35.4 / Rancher 2.14.1), and guest RKE2 must stay within
the Harvester minor's CSI/CCM Node-Driver range (`guest-rke2-survivability.md`).
</content>
