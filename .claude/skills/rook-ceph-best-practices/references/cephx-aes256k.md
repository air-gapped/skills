# CephX key types, AES256K and Rook key rotation

Source of truth: Rook `Documentation/Storage-Configuration/Advanced/cephx-key-rotation.md`
(identical at v1.19.11 and v1.20.7), Ceph `doc/rados/configuration/auth-config-ref.rst`,
Linux `include/linux/ceph/ceph_fs.h` / `net/ceph/crypto.c`.

## Key types

Ceph has exactly two CephX key types. "aes256" is not one of them.

| Type | Kernel constant | Construction | Status |
|---|---|---|---|
| `aes` | `CEPH_CRYPTO_AES` (0x1) | AES-CBC, fixed hard-coded IV, 16-byte key, no effective integrity check | Legacy. Tickets are malleable (CVE-2025-30156). |
| `aes256k` | `CEPH_CRYPTO_AES256KRB5` (0x2) | Kerberos enctype aes256-cts-hmac-sha384-192 (RFC 8009): AES-256-CTS + HMAC-SHA384/192 | Ceph 19.2.6+, 20.2.4+. Kernel clients: Linux 7.0+ (7.2+ under FIPS enforcing). |

The CVE is an integrity flaw, not a key-length flaw: with any stolen CephX key
an attacker flips bits in an AES service ticket until it grants admin, in
linear time, without decrypting it. The HMAC in AES256K rejects the tampered
ticket. The CVE closes when **mon, mgr, osd and mds** keys are AES256K; from
then on every client, `aes` or not, receives AES256K service tickets.

Linux kernel support: commit "libceph: add support for CEPH_CRYPTO_AES256KRB5"
(2025-12-22), first in Linux 7.0.

Userspace mounters (rbd-nbd, ceph-fuse) use librados from the cephcsi image,
not the kernel. Whether they accept AES256K keys on a pre-7.0 kernel is not
stated anywhere upstream — treat as untested; keep CSI on `aes` if any node
could use them on an old kernel.

## Rook key categories

| Category | CR field | Covers | Rotation |
|---|---|---|---|
| Daemon | `CephCluster.spec.security.cephx.daemon` | mon, mgr, osd, crash collector, exporter, admin; plus MDS, RGW, NFS-Ganesha main key, NVMe-oF gateways of child CRs | With daemon restarts — combine with a Rook or Ceph image bump. Rook picks the key type; set `daemon.keyType` only as the `allowedCiphers` recovery workaround. |
| CSI | `CephCluster.spec.security.cephx.csi` | `client.csi-rbd-node`, `-rbd-provisioner`, `-cephfs-node`, `-cephfs-provisioner` | Independent. One key per role for the whole cluster, so one node on a pre-7.0 kernel pins every node to `aes`. |
| CephClient | `CephClient.spec.security.cephx` | custom app clients | Independent. `aes256k` only if the client's Ceph libs are 19.2.6+/20.2.4+ and kernel mounts are 7.0+. |
| RBD mirror peer | `CephCluster.spec.security.cephx.rbdMirrorPeer` | `peerToken` on mirrored pools | Independent. `aes` while any peer cluster lacks AES256K. |

Rotation: `keyRotationPolicy: KeyGeneration` plus `keyGeneration` greater than
the current `status.cephx` value. Changing `keyType` also triggers a rotation.
Always set `keyType` explicitly on CSI, CephClient and rbdMirrorPeer.

## Health codes

| Code | Severity | Clears when | Mute? |
|---|---|---|---|
| `AUTH_INSECURE_SERVICE_KEY_TYPE` | ERR | core daemon keys are AES256K | No — fix it |
| `AUTH_INSECURE_SERVICE_TICKETS` | ERR | core daemon keys are AES256K | No — fix it |
| `AUTH_INSECURE_ROTATING_SERVICE_KEY_TYPE` | WRN | 2–3 h after core daemons migrate (rotating service tickets keep the old cipher meanwhile). Field reports say it can persist — check again after 3 h before investigating. | Yes |
| `AUTH_INSECURE_CLIENT_KEY_TYPE` | WRN | all client keys (CSI, CephClient, RBD mirror, NFS per-export) are AES256K | Yes |
| `AUTH_INSECURE_KEYS_ALLOWED` | WRN | `allowedCiphers: [aes256k]` | Yes |
| `AUTH_INSECURE_KEYS_CREATABLE` | WRN | `allowedCiphers: [aes256k]` | Yes |

A stale auth entity for a removed daemon (e.g. `osd.N` absent from
`ceph osd ls`) is listed under `AUTH_INSECURE_SERVICE_KEY_TYPE` and never
rotates. Remove it (see SKILL.md) — it is the usual leftover ERR.

Mute (Rook ≥ v1.19.10), and flip to `unmute` after full migration so a new
`aes` key shows up again:

```yaml
spec:
  healthCheck:
    muteHealthWarning:
      AUTH_INSECURE_ROTATING_SERVICE_KEY_TYPE:
        policy: mute
      AUTH_INSECURE_CLIENT_KEY_TYPE:
        policy: mute
      AUTH_INSECURE_KEYS_ALLOWED:
        policy: mute
      AUTH_INSECURE_KEYS_CREATABLE:
        policy: mute
```

## Migrating CSI keys to AES256K

Preconditions: every node on Linux 7.0+ (7.2+ FIPS), verified from
`.status.nodeInfo.kernelVersion`; cephcsi ≥ 3.17.1 (Rook 1.20 line) or the
3.16.3 backport shipped by Rook v1.19.11.

1. Patch:
   ```yaml
   spec:
     security:
       cephx:
         csi:
           keyRotationPolicy: KeyGeneration
           keyGeneration: 3          # current + 1
           keepPriorKeyCountMax: 1   # keeps the in-use key valid
           keyType: aes256k
   ```
2. Wait for `status.cephx.csi.keyGeneration` to reach the new value.
3. Only new mounts use the new key. Cordon, drain, optionally reboot, and
   uncordon each node in turn so its PVCs remount.
4. Optional: `keepPriorKeyCountMax: 0` to delete the old keys.

Revert (kernel or CSI trouble): `keyType: aes`, a higher `keyGeneration`,
`keepPriorKeyCountMax: 2`. This rotates again, back to `aes`.

After CSI is on AES256K, gate every node join and every kernel fallback
(GRUB default entry, rollback image) on 7.0+: a pre-7.0 node cannot mount
new PVCs.

## allowedCiphers

Set `spec.security.cephx.allowedCiphers: [aes256k]` only after
`ceph auth dump-keys --format=json-pretty` reports `aes256k` for every key.
If any daemon key is still `aes`, Ceph fails with
`[errno 13] RADOS permission denied (error connecting to the cluster)` and
Rook stops reconciling. Recovery:

```yaml
spec:
  security:
    cephx:
      allowedCiphers:
        - aes
        - aes256k
      daemon:
        keyType: aes   # workaround only
```

Once every `rook-ceph-mon` pod shows `--mon-auth-emergency-allowed-ciphers`
and reconcile continues, remove `daemon.keyType`. Leave `allowedCiphers`
alone afterwards. This recovery is for the `allowedCiphers` mistake only; it
did not help the stuck-generation OSD outage in rook#18240.

Outside Rook the same Ceph knobs are `ceph mon set auth_allowed_ciphers
aes,aes256k` and `ceph mon set auth_preferred_cipher aes256k`. The rescue
option `mon_auth_emergency_allowed_ciphers` takes a cipher **list**
(e.g. `aes`), not a boolean — `= true` fails with
`init: invalid cipher: true`. A cluster
with `auth_allowed_ciphers=aes256k` but `auth_preferred_cipher=aes` locks
restarted daemons out.

## Never during a rotation

- Rebuild or re-create a mon (`monmaptool --mkfs`, fresh mon store). A
  2026-09-11 ceph-users report: after a cipher-policy lockout, a rebuilt mon
  diverged epoch history, OSDs crashed in `PGLog::merge_log`, leaving 278
  unfound objects and incomplete/down PGs.
- Force `skipUpgradeChecks: true` to push past HEALTH_ERR.
- Restart pods in the Rook namespace to "unstick" it before the operator log
  is saved.

## Outside Rook (cephadm / packages)

`ceph auth rotate --key-type=aes256k <entity>` per entity, starting with
`mon.`. cephadm rotates daemon keys during the upgrade itself, which is why
those upgrades run noticeably longer. Rotating a client key (e.g.
`client.crash`) and restarting it before the service side accepts AES256K
gives `handle_auth_bad_method server allowed_methods [2] and I support [1]`.

## External clusters

`python3 create-external-cluster-resources.py <other-flags> --cephx-key-rotate rotate --cephx-key-type aes256k`,
import the new keys, then remount PVCs by node drain as above.

## Known gaps

- NFS-Ganesha per-export keys cannot be rotated; Ceph has no mechanism.
- Ceph Umbrella (v21) is not released as of 2026-09-23: tags go v21.1.1 →
  v21.3.0 with no v21.2.0. Rook docs name 21.2.0 as the planned AES256K floor.
