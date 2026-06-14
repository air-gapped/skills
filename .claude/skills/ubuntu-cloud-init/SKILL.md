---
name: ubuntu-cloud-init
description: >-
  Author, validate, and debug cloud-init configuration for Ubuntu Server LTS 24.04
  and 26.04, focused on on-premise and air-gapped hosts via the NoCloud datasource —
  `#cloud-config` user-data, the cloud-config modules (users, ssh, write_files,
  runcmd, apt with local mirrors, ca_certs for internal CAs, ntp, disk_setup),
  NoCloud seeding (seed dir, `cidata` ISO, `ds=nocloud;s=...` kernel cmdline, SMBIOS
  serial), boot stages, and pinning `datasource_list`. Public-cloud datasources
  (EC2/Azure/GCE…) are pointers only. For the `network:` block use the ubuntu-netplan
  skill; for the installer schema use the ubuntu-autoinstall skill.
when_to_use: >-
  Use whenever the task mentions cloud-init, `#cloud-config`, user-data / meta-data /
  vendor-data, NoCloud, a seed ISO, first-boot provisioning,
  `cloud-init schema|status|clean|query`, or what an Ubuntu host does on first boot —
  even when the user just says "set up users and packages on first boot" or "seed a
  VM with cloud-init".
---

# ubuntu-cloud-init

cloud-init runs early in boot, reads configuration from a **datasource**, and applies
it through **modules** across four boot stages. This skill is authoring-led (produce
correct cloud-config from a description) with a strong validation/debug path, aimed
at **on-prem / air-gapped Ubuntu Server LTS** using the **NoCloud** datasource.

Mapping: 24.04 LTS ≈ cloud-init 24.x; 26.04 LTS ≈ 26.1.

## Authoring workflow

1. **Identify the goal & datasource.** On-prem/air-gapped → **NoCloud** (seed dir,
   `cidata` ISO/USB, HTTP seed, or SMBIOS serial). Pin
   `datasource_list: [NoCloud]` to stop cloud-init probing cloud metadata services
   and timing out.
2. **Choose the user-data format** — almost always `#cloud-config`. Use MIME multipart
   only to combine cloud-config with scripts. (Formats table below.)
3. **Write the `#cloud-config`** using the modules needed (see Quick reference).
4. **Validate:** `cloud-init schema -c user-data --annotate`.
5. **Seed it** (NoCloud) and set a unique `instance-id` in `meta-data`.
6. **Test on a throwaway boot**, then `cloud-init clean --logs` to re-run as if
   first boot.

## user-data formats

First line determines the format:

| Header (line 1) | Format |
|---|---|
| `#cloud-config` | YAML config processed by modules (the usual choice). |
| `#!/bin/sh` (shebang) | A script, run once per instance in the Final stage. |
| `#cloud-boothook` | Runs very early, **every boot** (guard with `cloud-init-per`). |
| `#include` | List of URLs, each fetched as user-data. |
| `Content-Type: multipart/mixed` | MIME — combine cloud-config + scripts. Build with `cloud-init devel make-mime`. |
| `## template: jinja` | Jinja template (line 1); real header on line 2. Variables = instance-data keys, e.g. `{{ v1.instance_id }}`. |

Any of these may be gzipped.

## Quick reference — the modules that matter on-prem

**users / ssh** (created in the Network stage):

```yaml
#cloud-config
ssh_pwauth: false
users:
  - default                          # KEEP this first to retain the distro user + cloud keys
  - name: deploy
    groups: [sudo]
    sudo: "ALL=(ALL) NOPASSWD:ALL"
    lock_passwd: true
    shell: /bin/bash
    ssh_authorized_keys:
      - ssh-ed25519 AAAA... deploy@site
```
`passwd` (a hash) applies only to *new* users; `hashed_passwd` applies even to
existing ones. Generate a hash with `mkpasswd --method=SHA-512 --rounds=4096`.

**write_files:**
```yaml
write_files:
  - path: /etc/myapp/app.conf
    owner: root:root
    permissions: '0640'
    content: |
      backend = db.internal:5432
  - encoding: b64                     # also gz, gz+b64
    content: aGVsbG8K
    path: /etc/motd.d/banner
    defer: true                       # write in Final stage (after users/packages)
```

**runcmd vs bootcmd:** `runcmd` runs once per instance in the Config stage (later);
`bootcmd` runs early on *every* boot (guard once-only work with
`cloud-init-per once <name> ...`).
```yaml
runcmd:
  - [systemctl, enable, --now, myapp]
```

**apt — local mirror + internal repo** (the air-gapped essential):
```yaml
apt:
  preserve_sources_list: false
  primary:
    - arches: [default]
      uri: http://mirror.internal/ubuntu
  security:
    - arches: [default]
      uri: http://mirror.internal/ubuntu
  sources:
    internal-app.list:
      source: "deb [signed-by=$KEY_FILE] http://mirror.internal/app stable main"
      key: |
        -----BEGIN PGP PUBLIC KEY BLOCK-----
        ...embed the key inline; do NOT rely on a keyserver air-gapped...
        -----END PGP PUBLIC KEY BLOCK-----
  conf: |
    Acquire::http::Proxy "http://apt-cache.internal:3142";
```

**ca_certs — trust an internal CA** (runs in the Network stage, *before* apt, so
HTTPS to the internal mirror works):
```yaml
ca_certs:
  trusted:
    - |
      -----BEGIN CERTIFICATE-----
      <internal root CA>
      -----END CERTIFICATE-----
```

**ntp — point at local time source:**
```yaml
ntp:
  enabled: true
  servers: [ntp.internal]
  pools: []
```

Other on-prem-relevant modules: `packages`/`package_update`/`package_upgrade`
(avoid `package_upgrade` without a full mirror), `disk_setup`+`fs_setup`+`mounts`,
`growpart`/`resize_rootfs`, `timezone`/`locale`/`keyboard`, `set_passwords`/`chpasswd`,
`seed_random`, `power_state`, hostname (`hostname`/`fqdn`/`manage_etc_hosts`). **Avoid
`phone_home`** air-gapped — it only calls out to a URL and retries on failure. Full
per-module detail (keys, snippets, stage, frequency) in `references/modules.md`.

## NoCloud seeding (the air-gapped core)

cloud-init finds NoCloud config from (in precedence order) SMBIOS serial → kernel
cmdline → seed dirs → labeled block device. The common methods:

- **Seed directory:** drop `meta-data` + `user-data` (and optionally `vendor-data`,
  `network-config`) into `/var/lib/cloud/seed/nocloud/`.
- **`cidata` ISO/USB:** a `vfat`/`iso9660` filesystem labeled `CIDATA` (case-insensitive)
  containing those files in its root.
  `genisoimage -output seed.iso -volid cidata -joliet -rock user-data meta-data network-config`
  (or `cloud-localds seed.iso user-data meta-data`).
- **HTTP seed:** kernel cmdline `ds=nocloud;s=http://10.0.0.1:8000/` (the scheme
  decides local vs network; **trailing slash required** — files are appended as
  `<uri>/user-data` etc.).
- **SMBIOS serial** (QEMU/libvirt): `-smbios type=1,serial=ds=nocloud;s=http://10.0.0.1:8000/`.

**Required files:** `meta-data` and `user-data`. **Optional:** `vendor-data`,
`network-config`. Since cloud-init 24.3, an HTTP/seed source that *omits*
`network-config` triggers a boot retry/timeout — ship an **empty `network-config`**
for back-compat, or a real netplan-v2 one.

**`instance-id` re-run rule:** cloud-init only re-applies user-data when the
`instance-id` in `meta-data` *changes* (or after `cloud-init clean`). Bump it
whenever the config changes.

Full seeding detail (cmdline grammar + aliases, DMI variable expansion, FTP, GRUB
escaping, `seedfrom`, dsname deprecations) is in `references/nocloud-and-airgapped.md`.

## Network config (hand-off to netplan)

cloud-init network-config has v1 (its own schema) and **v2 (which IS netplan
format)**. On Ubuntu the renderer is netplan; cloud-init writes
`/etc/netplan/50-cloud-init.yaml`. **user-data cannot set network config** —
networking comes from the datasource, system config, or kernel cmdline.

To author the network block, or to hand network control back to netplan entirely
(`network: {config: disabled}` in `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg`),
use the **ubuntu-netplan** skill.

## Validation & debugging (fast path)

```bash
cloud-init schema -c user-data --annotate     # validate a file, errors inline
sudo cloud-init schema --system --annotate     # validate the live system's user-data
cloud-init status --long --wait                # 0=ok, 1=error, 2=recoverable error
cloud-init query --all                         # inspect instance-data
sudo cloud-init clean --logs                   # wipe state → next boot is "first boot"
```
Logs: `/var/log/cloud-init.log`, `/var/log/cloud-init-output.log`,
`/run/cloud-init/` (incl. `ds-identify.log`, `result.json`, `instance-data.json`).
Config: `/etc/cloud/cloud.cfg` + `/etc/cloud/cloud.cfg.d/*.cfg`. Full CLI, the boot
stages, and re-run/golden-image notes in `references/cli-and-debugging.md`.

## Air-gapped checklist

- Pin `datasource_list: [NoCloud]` (or `[NoCloud, None]`) in a `cloud.cfg.d` drop-in
  — stops cloud probing/timeouts.
- Local apt mirror via the `apt` module; embed repo signing keys inline.
- Internal CA via `ca_certs.trusted`.
- Local NTP via `ntp.servers`.
- Omit `phone_home`; don't `package_upgrade` without a full mirror; avoid `snap`
  unless a local store / pre-acked assertions are available.
- Use `vendor-data` for site-wide defaults (mirror, CA, NTP, base users); per-host
  `user-data` overrides it.

## Boundaries (sibling skills)

- **`network:`** → **ubuntu-netplan** skill (v2 is netplan format).
- **Ubuntu Server install automation** → **ubuntu-autoinstall** skill. The installer
  is itself driven by a NoCloud `user-data` carrying a top-level `autoinstall:` key;
  cloud-init *ignores* `autoinstall` and passes it to Subiquity. Inside that document,
  the nested `user-data:` is cloud-config for the *installed* system (first boot).

## Reference files

- `references/nocloud-and-airgapped.md` — every NoCloud seeding method, cmdline
  grammar, SMBIOS/DMI, `instance-id`, `datasource_list` pinning, DataSourceNone,
  vendor-data, deprecations.
- `references/modules.md` — full cloud-config module reference (on-prem modules in
  depth; the rest listed by stage). Has a TOC.
- `references/cli-and-debugging.md` — CLI, boot stages & module ordering, re-run /
  golden-image, version notes (24.x vs 26.1).
- `references/examples.md` — minimal and realistic air-gapped configs with matching
  `meta-data`.
