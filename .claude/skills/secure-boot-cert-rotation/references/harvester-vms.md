# Harvester HCI / KubeVirt VMs — two layers, the v1.6.0 floor, and NVRAM triage

A Harvester-on-Dell deployment has **two independent firmware surfaces**. Keep them separate — conflating them
is the #1 source of wrong advice here.

## Where guest Secure Boot keys actually come from (verified, not inferred)

A Harvester VM's virtual UEFI firmware does **NOT** come from the node OS. It ships inside the SUSE-built
**KubeVirt `virt-launcher` container** that Harvester pins per release (`harvester-images-list-amd64.txt`); the
node SL Micro image doesn't even contain `qemu-ovmf-x86_64`. So the SUSE *node-OS* OVMF backport
(bsc#1257019 / SUSE-RU-2026:1157-1, SLE Micro 5.5, 2026-03-10) is a **separate code path** (host firmware
tooling) and is **irrelevant to guest VMs**. What governs guest certs is:
**Harvester version → its virt-launcher → its `qemu-ovmf-x86_64`.**

> **Proof method (apply House Rule #4 — verify the artifact, not upstream tags).** The floor below was pinned by
> pulling each release's virt-launcher and reading the actual varstore bytes:
> ```bash
> docker run --rm registry.suse.com/suse/sles/15.7/virt-launcher:<ver> rpm -q qemu-ovmf-x86_64
> # extract ovmf-x86_64-smm-ms-vars.bin from the image and:
> openssl ... # parse X.509 subjects → look for "KEK 2K CA 2023" / "Microsoft UEFI CA 2023"
> ```

## Minimum Harvester version with 2023 certs in guest OVMF = `v1.6.0`

At 1.6.0 Harvester moved virt-launcher to the **SLES-15.7 / `qemu-ovmf-x86_64-202408`** base, whose `-ms`
varstore has had the 2023 KEK + UEFI CA 2023 baked in (via `virt-fw-vars`) since mid-2024.

| Harvester line | virt-launcher base | 2023 certs in guest OVMF? |
|---|---|---|
| **1.5.x** (incl. 1.5.2, last GA; EOL) | SLES 15.6 / `ovmf-202308` | ❌ **No — 2011-only** |
| **1.6.0 / 1.6.1** | SLES 15.7 / `ovmf-202408` | ✅ Yes |
| **1.7.x** | SLES 15.7 / `ovmf-202408` | ✅ Yes |
| **1.8.0** (GA 2026-04-24) | SLES 15.7 / `ovmf-202408` | ✅ Yes |

→ **No 1.5.x release contains the 2023 certs**, and there is no node patch that adds them to guests — a 1.5.x
cluster must **upgrade to ≥ 1.6.0.** The template only re-seeds **new/ephemeral** VMs; a pre-existing
**persistent** varstore keeps its 2011-only keys until fixed. (Re-pin this table via `gh release list/view -R
harvester/harvester` + the per-release virt-launcher image at use time — versions move.)

## Layer 1 — the Dell host firmware (only if the host runs Secure Boot ON)

Harvester *can* boot SB-on (the SLE Micro shim is Microsoft-UEFI-CA-signed → SUSE keys for grub/kernel), but
1.5.x is commonly installed **SB-off** because of bug **harvester#7343** — the 1.5.x ISO's stale shim fails the
SBAT self-check (`Security Policy Violation` / `SBAT self-check failed`) when booting on a Secure-Boot host;
the documented workaround is install with SB off, optionally re-enable after (fixed only in 1.8.0-dev, so
**1.5.x is still affected**). Check: iDRAC/BIOS Secure Boot setting, or `mokutil --sb-state` on the node.
**ON** → iDRAC BIOS update + reboot (`dell-poweredge.md`). **OFF** → host firmware certs are irrelevant to the
host.

## Layer 2 — the guest VMs (iDRAC never touches these)

### Step 1 — which VMs even use Secure Boot?
Harvester's UI defaults new VMs to `secureBoot: false`, so many are **moot** (nothing to fix). In-scope subset
(treat `efi` present + `secureBoot` *unset* as ON — the KubeVirt default for kubectl-created VMs):
```bash
kubectl get vm -A -o json | jq -r '.items[]
  | select(.spec.template.spec.domain.firmware.bootloader.efi != null)
  | select(.spec.template.spec.domain.firmware.bootloader.efi.secureBoot != false)
  | "\(.metadata.namespace)/\(.metadata.name)"'          # the ONLY VMs in scope
```

### Step 2 — persistent or ephemeral NVRAM?
```bash
kubectl get vm -A -o json | jq -r '.items[]
  | select(.spec.template.spec.domain.firmware.bootloader.efi.persistent==true)
  | "\(.metadata.namespace)/\(.metadata.name)  PERSISTENT"'
kubectl get pvc -A | grep persistent-state-for          # backing PVC: persistent-state-for-<vmname>
```
Any in-scope VM not listed is **ephemeral** (empty `grep` = all ephemeral). Harvester enables the
`VMPersistentState` gate cluster-wide (`kubectl get kubevirt -n harvester-system kubevirt -o
jsonpath='{.spec.configuration.developerConfiguration.featureGates}'`), but the per-VM default is ephemeral.
Harvester UI field names: "Booting in EFI mode" → `efi`; "Secure Boot" → `efi.secureBoot`; "EFI Persistent
State" → `efi.persistent`.

### Step 3 — fix by type
The crux: **ephemeral NVRAM is re-templated from the virt-launcher firmware on every cold stop/start.**
- **secureBoot off / BIOS** → nothing to do.
- **Secure Boot + ephemeral NVRAM** (the common case) → **upgrade Harvester to ≥ 1.6.0, then cold stop→start
  the VM** — it re-templates off the 2023 virt-launcher and picks up the certs (*a soft guest reboot does NOT
  re-seed* — the launcher pod must be recreated). ⚠️ On a `< 1.6.0` cluster, an in-guest append is **wiped on
  the next cold stop/start** (re-templated from the 2011-only launcher), so it is **not durable** — don't rely
  on it until you've upgraded, or convert the VM to persistent NVRAM first.
- **Secure Boot + persistent NVRAM** → not auto-refreshed (varstore in the `persistent-state-for-<vm>` PVC,
  `nvram` subpath). Either in-guest append (durable here), or offline-inject with the VM stopped:
  ```bash
  virt-fw-vars --input <varstore-from-PVC-nvram> --output <same> \
      --secure-boot --microsoft-kek 2023 --microsoft-db win23
  ```
  (`virt-fw-vars` from `virt-firmware`; `--microsoft-kek {none,2011,2023,all}`.)

### In-guest append (Linux guest — durable only on persistent NVRAM)
```bash
mokutil --sb-state                                   # confirm enabled
curl -fLO https://raw.githubusercontent.com/microsoft/secureboot_objects/main/PostSignedObjects/Optional/DB/amd64/DBUpdate3P2023.bin
sudo chattr -i /sys/firmware/efi/efivars/db-d719b2cb-3d3a-4596-a3bc-dad00e67656f
sudo efi-updatevar -a -f DBUpdate3P2023.bin db
sudo chattr +i /sys/firmware/efi/efivars/db-d719b2cb-3d3a-4596-a3bc-dad00e67656f
```
(Windows guests: apply the Microsoft Secure Boot servicing update instead; suspend BitLocker first.)

### Verify which OVMF a node's virt-launcher actually ships (do NOT `rpm -q` the node — OVMF isn't there)
```bash
POD=$(kubectl get pod -A -l kubevirt.io=virt-launcher -o jsonpath='{.items[0].metadata.name}')
NS=$(kubectl get pod -A -l kubevirt.io=virt-launcher -o jsonpath='{.items[0].metadata.namespace}')
kubectl exec -n "$NS" "$POD" -- sh -c 'strings /usr/share/qemu/ovmf-x86_64-smm-ms-vars.bin | grep -i 2023'
```

## Bottom line for a 1.5.0 fleet

No 1.5.x has the 2023 certs and no node patch adds them to guests. The durable, clean fix is **upgrade
1.5.0 → ≥ 1.6.0** (sequential: 1.5.0 → 1.5.2 → 1.6.x → … → 1.8.0 — and you must leave EOL 1.5.x anyway), then
**cold stop/start each Secure-Boot Linux VM** (ephemeral → re-templates and picks up 2023). Low urgency: VMs
keep booting regardless; the 2023 db cert only bites once a guest's shim updates to a 2023-only-signed build,
and distros dual-sign shim meanwhile — so fold this into the (already-needed) Harvester upgrade rather than
doing per-VM surgery on an EOL release. Harvester 1.5.x is past End-of-Maintenance (2025-12-30), EOL 2026-12-30.
