# autoinstall delivery & NoCloud seeding

Grounded in `canonical/subiquity` `doc/tutorial/providing-autoinstall.rst`,
`doc/howto/autoinstall-quickstart.rst`, `doc/explanation/zero-touch-autoinstall.rst`,
`doc/explanation/cloudinit-autoinstall-interaction.rst`, and `subiquity/server/server.py`.
For full NoCloud datasource detail, see the **ubuntu-cloud-init** skill's
`nocloud-and-airgapped.md`.

## Two delivery families

1. **Via cloud-init `#cloud-config` user-data** — the file MUST start with
   `#cloud-config` and nest the install config under a top-level `autoinstall:` key.
   Top-level cloud-config keys (alongside `autoinstall:`) configure the **ephemeral
   installer environment**, not the target.
2. **Directly on the install media** as a file named `autoinstall.yaml` — the
   `autoinstall:` wrapper is **optional** here (a bare `version: 1 ...` works). On a
   media file, **no other top-level keys may sit beside `autoinstall:`** — that is a
   fatal error. (On-media wrapper acceptance arrived in 24.04.)

## Precedence (installer uses the FIRST that exists)

1. `--autoinstall <path>` CLI argument — `--autoinstall ""` (empty) explicitly
   **disables** autoinstall.
2. kernel cmdline `subiquity.autoinstallpath=path/to/autoinstall.yaml` (relative to
   the installer root).
3. `autoinstall.yaml` at the root of the install system.
4. cloud-config-supplied `run/subiquity/cloud.autoinstall.yaml`.
5. `cdrom/autoinstall.yaml` baked into the ISO.

So **kernel cmdline and on-media files outrank cloud-config delivery.**

## The cloud-init ⇄ autoinstall interaction (three zones in one file)

```
#cloud-config            # (1) directives here affect the EPHEMERAL installer env
autoinstall:             # processed by Subiquity, configures the TARGET
  version: 1
  ...
  user-data:             # (2) cloud-config here affects the TARGET, on first boot
    ...
```

cloud-init *delivers* but does not *process* autoinstall — the `cc_ubuntu_autoinstall`
module explicitly ignores the key and hands it to Subiquity. cloud-init runs in the
ephemeral installer, then again on the target's first boot (applying `user-data`),
then goes inert.

## NoCloud seeding methods (on-prem)

### HTTP seed
```
# kernel cmdline (quote the whole append string; ';' is a shell/GRUB metachar)
autoinstall ds=nocloud-net;s=http://10.0.0.1:8000/
```
Serve `user-data` and `meta-data` (and, for cloud-init ≥24.3, an empty or real
`network-config`) at that base URL. A quick local server:
```bash
mkdir seed && cd seed
cp autoinstall.yaml user-data        # user-data IS the #cloud-config+autoinstall file
touch meta-data
python3 -m http.server 8000
```

### Volume seed (USB / second ISO)
```bash
cloud-localds seed.iso user-data meta-data      # needs cloud-image-utils
# or:
genisoimage -output seed.iso -volid cidata -joliet -rock user-data meta-data
```
cloud-init finds it by the `cidata`/`CIDATA` filesystem label. `meta-data` must exist
(may be empty). Attach as a second drive / USB stick.

### Baked into the install ISO
Place `autoinstall.yaml` at the ISO root (or `cdrom/autoinstall.yaml`), or add
`autoinstall` + a seed to the GRUB/isolinux append line when remastering.

### PXE / netboot
Netbooting is the HTTP-seed method delivered over the network instead of from media.
Boot the installer's `vmlinuz` + `initrd` via TFTP/iPXE, and put the autoinstall seed
on the kernel append line — the installer fetches the config over HTTP:
```
# iPXE / PXELINUX APPEND line
... ip=dhcp url=http://10.0.0.1/ubuntu/ autoinstall ds=nocloud-net;s=http://10.0.0.1:8000/
```
Serve `user-data` + `meta-data` from the seed URL exactly as for the HTTP seed above.
No media is involved, so there is no disk-wipe prompt to suppress beyond the bare
`autoinstall` keyword (see Zero-touch).

## Zero-touch: the bare `autoinstall` keyword

The bare `autoinstall` kernel keyword is **separate** from `ds=...`. It suppresses the
interactive "Continue with autoinstall? (yes|no)" disk-wipe confirmation. For true
zero-touch you need **both**:
- the config delivery (a `ds=` seed, on-media file, or cmdline path), **and**
- `autoinstall` on the kernel cmdline.

Example GRUB append line:
```
linux /casper/vmlinuz autoinstall ds=nocloud-net;s=http://10.0.0.1:8000/ ---
```

## Quoting & escaping gotchas

- The `;` in `ds=nocloud-net;s=...` is a shell metacharacter and ends a GRUB
  statement — quote the entire `-append '...'` value, or escape the `;`.
- Quote the `identity.password` hash (it contains `$`).
