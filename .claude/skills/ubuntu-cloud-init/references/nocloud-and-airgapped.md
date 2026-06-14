# NoCloud datasource & air-gapped operation

Grounded in `canonical/cloud-init` `cloudinit/sources/DataSourceNoCloud.py`,
`doc/rtd/reference/datasources/nocloud.rst`, `base_config_reference.rst`, and
`breaking_changes.rst`.

## Two NoCloud classes

- **`DataSourceNoCloud`** — runs in the **Local** stage (no network). Seeds from
  `file://` / absolute paths and labeled block devices.
- **`DataSourceNoCloudNet`** — runs in the **Network** stage. Seeds from
  `http://`, `https://`, `ftp://`, `ftps://`.

The dsname **`nocloud-net` is deprecated since 24.1** — use `nocloud`; the *scheme*
of the `seedfrom` URI decides whether the Local or Network class handles it. The old
name still works (with a deprecation log).

## Seeding methods (probed low → high precedence)

1. **SMBIOS / DMI system-serial-number** — the serial string is parsed as a line
   config (same grammar as the kernel cmdline). The QEMU/libvirt favourite for
   air-gapped VMs.
2. **Kernel command line** — `ds=nocloud;s=<uri>`.
3. **Seed directories** — `/var/lib/cloud/seed/nocloud/` and
   `/var/lib/cloud/seed/nocloud-net/`. First with the required files wins.
4. **System config `seedfrom`** — `datasource.NoCloud.seedfrom` in `cloud.cfg.d`.
5. **Inline** `user-data` + `meta-data` in system config.
6. **Labeled block device** — filesystem `vfat` or `iso9660` carrying LABEL
   `cidata`/`CIDATA` (case-insensitive; override via `datasource.NoCloud.fs_label`).
   Files live in the filesystem root.

If a `seedfrom` is produced by any of the above, cloud-init then fetches
`user-data`, `meta-data`, `vendor-data`, `network-config` from it. The scheme must
match the class's supported schemes or the datasource declines. Cmdline values
override seed values.

## Required / optional files

- **Required:** `meta-data`, `user-data`.
- **Optional:** `vendor-data`, `network-config`.

> **Breaking change (24.3):** NoCloud gained `network-config` support, and an
> HTTP/seed source that *omits* it now causes a boot retry/timeout. Ship an **empty**
> `network-config` file for back-compat, or a real netplan-v2 document.

## Line-config grammar (cmdline / SMBIOS serial)

Form: `ds=nocloud[;key=val;...]` (tokens space- or `;`-delimited).

| Key | Alias | Notes |
|---|---|---|
| `seedfrom` | `s` | The only effectively-required key. Trailing `/` required for dir-style seeds — files are appended (`<uri>/user-data`, …). |
| `local-hostname` | `h` | **Discouraged / may be removed** — set in `meta-data` instead. |
| `instance-id` | `i` | **Discouraged / may be removed** — set in `meta-data` instead. |

Examples:
```
ds=nocloud;s=https://10.42.42.42/configs/         # HTTP seed (Network stage)
ds=nocloud;s=file:///cidata/                       # local dir (Local stage)
```

- **GRUB gotcha:** an unescaped `;` ends a GRUB statement. Quote/escape the value on
  the kernel cmdline.
- **FTP(S)** supports userinfo + port: `ftps://user:pass@host:21/path/` (default user
  `anonymous`, port 21).
- **DMI variable expansion** in `seedfrom`: `__dmi.system-serial-number__`,
  `__dmi.chassis-serial-number__`, `__dmi.system-uuid__`, etc. — useful to make one
  serial fan out to a per-host path.

QEMU example:
```
-smbios type=1,serial=ds=nocloud;s=http://10.10.0.1:8000/__dmi.chassis-serial-number__/
```

## `instance-id` semantics (re-run control)

cloud-init caches the `instance-id` and treats a *changed* value as a new instance →
re-runs per-instance modules. So:

- **To force a re-run after editing user-data, change `instance-id`** in `meta-data`
  (or run `cloud-init clean`).
- The default `instance-id` if unset is literally `nocloud` — always set a real one.
- Security note: trusting an attacker-presented instance-id can re-provision a host.
  `manual_cache_clean: true` switches to "trust the cached instance, never auto-detect
  a new one" mode.

## `datasource_list` pinning (the #1 air-gapped fix)

Without pinning, `ds-identify` probes many datasources; several wait on metadata
services (link-local IPs, DHCP) and time out, slowing or hanging boot. Pin it in
`/etc/cloud/cloud.cfg.d/99-datasource.cfg`:

```yaml
datasource_list: [ NoCloud ]
```

- A **single-entry** list skips availability checks entirely (fastest).
- Add `None` only if you want the DataSourceNone fallback: `[ NoCloud, None ]`.
- **24.1 change:** ds-identify no longer auto-appends `None` to a single-entry list —
  add it explicitly if you want it.

## DataSourceNone fallback

Supply config directly in `cloud.cfg.d` when no seed media can be attached:

```yaml
datasource:
  None:
    metadata:
      instance-id: host01
    userdata_raw: |
      #cloud-config
      hostname: host01
```
It cannot render networking and logs a warning when used — last resort only.

## vendor-data for site defaults

Ship common, site-wide config (mirror, internal CA, NTP, base users) as
`vendor-data` in the seed; per-host `user-data` overrides it. Disable consumption
with `vendor_data: {enabled: false}` in base config.

## Building seed media

```bash
# ISO with the cloud-image-utils helper
cloud-localds seed.iso user-data meta-data
# or explicitly, controlling the volume label
genisoimage -output seed.iso -volid cidata -joliet -rock user-data meta-data network-config
```
The volume label MUST be `cidata`/`CIDATA`. Attach as a second drive (or a USB stick
with that filesystem label).

## Deprecations to avoid (24.x → 26.1)

- `nocloud-net` **dsname** → use `nocloud` (deprecated 24.1).
- ENI-style `network-interfaces` in NoCloud `meta-data` → use network v1/v2
  (deprecated 24.3).
- cmdline `h=`/`i=` aliases → set `local-hostname`/`instance-id` in `meta-data`.
