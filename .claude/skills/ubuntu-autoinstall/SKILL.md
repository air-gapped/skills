---
name: ubuntu-autoinstall
description: >-
  Author, validate, and debug Ubuntu Server autoinstall configuration (the Subiquity
  installer's `autoinstall:` schema, version 1) for Ubuntu Server LTS 24.04 and 26.04,
  focused on unattended on-premise and air-gapped installs — identity, storage
  (LVM/direct/ZFS/encryption/RAID), apt mirror-selection + proxy + offline fallback,
  ssh, packages, kernel, late-commands/early-commands, and zero-touch delivery via a
  NoCloud seed. The `network:` block is netplan v2 (use the ubuntu-netplan skill); the
  `user-data:` block is cloud-config for the installed system (use the
  ubuntu-cloud-init skill).
when_to_use: >-
  Use whenever the task mentions autoinstall, Subiquity, unattended/zero-touch Ubuntu
  Server installation, an `autoinstall.yaml` / `user-data` install seed (on ISO/USB, an
  HTTP seed, or a `#cloud-config` carrying the `autoinstall:` key), a custom install
  ISO, a local install mirror, or validating an autoinstall file — even when the user
  just says "automate an Ubuntu Server install" or "PXE/USB install a server".
---

# ubuntu-autoinstall

Autoinstall is the configuration format for Ubuntu Server's **Subiquity** installer.
A `version: 1` document tells the installer how to partition, install, and configure
the system unattended. This skill is authoring-led (produce a correct
autoinstall config from a description) with a strong validation/debug path, aimed at
**unattended on-prem / air-gapped Ubuntu Server LTS** installs.

Autoinstall **nests the other two domains**:
- its `network:` key is **netplan v2** → use the **ubuntu-netplan** skill;
- its `user-data:` key is **cloud-config for the installed system** → use the
  **ubuntu-cloud-init** skill;
- and the config is itself **delivered via cloud-init NoCloud**.

See **The two delegation boundaries** and **Delivery**.

## Authoring workflow

1. **Pick the delivery method** (Delivery, below). Air-gapped → usually a NoCloud
   seed on the ISO/USB or an HTTP seed.
2. **Write the `version: 1` document.** `version` is the only schema-required key, but
   `identity` is required at *runtime* unless `user-data:` is present.
3. **Set the air-gapped essentials** — local mirror, proxy, offline fallback (see the
   Air-gapped essentials section below for the exact keys).
4. **Author `network:`** as netplan v2 (ubuntu-netplan skill) and any installed-system
   first-boot config under `user-data:` (ubuntu-cloud-init skill).
5. **Validate** with the subiquity repo's `validate-autoinstall-user-data.py` (see
   Validation — the script ships in the installer source, not in this skill).
6. **Boot with the `autoinstall` kernel keyword** to skip the disk-wipe confirmation
   for true zero-touch.

## The two delegation boundaries (critical)

```yaml
#cloud-config
# (1) top-level cloud-config here configures the EPHEMERAL installer environment
autoinstall:                  # processed by Subiquity → configures the TARGET system
  version: 1
  network:                    # (2) netplan v2  → ubuntu-netplan skill
    version: 2
    ethernets: { ... }
  identity: { ... }
  user-data:                  # (3) cloud-config → ubuntu-cloud-init skill
    # runs on the INSTALLED system's FIRST BOOT (not at install time)
    packages: [ ... ]
```

- **`network:` is netplan v2 only.** Default if omitted is DHCPv4 on `en*`/`eth*`.
  `match:` inside `ethernets` accepts only `name`/`macaddress`/`driver`. (A rarely-used
  double-wrapped `network: {network: {...}}` form also validates; prefer the plain
  form.)
- **`user-data:` is cloud-config for the installed system**, merged with the
  installer-generated user-data. **Timing matters:** users from `identity` are created
  *during install*; users defined in `user-data` are created on *first boot*.
  Supplying `user-data` makes `identity` optional — but then ensure a login path
  exists. Don't define the same user in both.

## Delivery & the NoCloud seed

Autoinstall config reaches the installer in two families:

- **Via cloud-init `#cloud-config` user-data** — requires the `#cloud-config` first
  line **and** the config nested under a top-level `autoinstall:` key.
- **Directly on the install media** as a file named `autoinstall.yaml` — here the
  `autoinstall:` wrapper is optional (a bare `version: 1 ...` works). This wrapper
  acceptance for on-media files arrived in 24.04.

**Precedence — the installer uses the FIRST that exists:**
1. `--autoinstall <path>` CLI arg (empty string explicitly *disables* autoinstall)
2. kernel cmdline `subiquity.autoinstallpath=...`
3. `autoinstall.yaml` at the root of the install system
4. cloud-config-supplied `run/subiquity/cloud.autoinstall.yaml`
5. `cdrom/autoinstall.yaml` baked into the ISO

So **kernel cmdline and on-media files outrank cloud-config.**

**NoCloud seeding** (the on-prem workhorse — see the **ubuntu-cloud-init** skill for
full NoCloud detail):
- **HTTP seed:** kernel cmdline `autoinstall ds=nocloud-net;s=http://SERVER:PORT/`,
  serving `user-data` + `meta-data` (+ optional `network-config`) at that base URL.
- **Volume seed (USB/ISO):** build with `cloud-localds seed.iso user-data meta-data`;
  cloud-init finds it by the `cidata`/`CIDATA` filesystem label. `meta-data` must
  exist (may be empty: `touch meta-data`).
- The bare **`autoinstall` kernel keyword** is *separate* from `ds=` — it suppresses
  the interactive "Continue with autoinstall?" disk-wipe confirmation. True zero-touch
  needs **both** the config delivery and `autoinstall` on the cmdline.
- Quote the whole kernel `-append '... ds=nocloud-net;s=...'` — `;` is a shell
  metacharacter (and ends a GRUB statement).

Full delivery/seeding detail (precedence source, ISO remastering, the on-media
"only the autoinstall key" rule) is in `references/delivery-and-seeding.md`.

## Top-level schema (version 1) — quick reference

Only `version` is schema-required; unknown keys produce a *warning* in v1 (will be
fatal in a future version). Common keys:

| Key | Purpose |
|---|---|
| `version` | Must be `1`. **Required.** |
| `identity` | Initial user `{realname, username, hostname, password}`. Required at runtime unless `user-data:` present. |
| `storage` | Disk layout — `layout: {name: lvm\|direct\|zfs\|hybrid}` or a curtin action list. |
| `network` | **netplan v2** (→ ubuntu-netplan skill). |
| `ssh` | `{install-server, authorized-keys, allow-pw}`. |
| `apt` | Mirror selection, proxy, components, fallback (air-gapped core). |
| `proxy` | HTTP proxy for install + target apt/snapd. |
| `packages` / `snaps` | Extra packages / snaps to install. |
| `user-data` | cloud-config for the installed system (→ ubuntu-cloud-init skill). |
| `late-commands` | Commands after install (**target mounted at `/target`**). |
| `early-commands` | Commands before probing (config is re-read after). |
| `interactive-sections` | Sections to still prompt for; must be a **list** (`['*']`, not `'*'`). |
| `updates` | `security` (default) or `all`. |
| `refresh-installer` | `{update: bool, channel}` — installer self-update (set `false` air-gapped). |
| `kernel` | `{package}` or `{flavor}`. |
| `timezone`, `locale`, `keyboard`, `source`, `drivers`, `codecs`, `oem`, `reporting`, `error-commands` | see `references/schema.md`. |
| `kernel-crash-dumps`, `zdevs` | **24.10+ only — not in 24.04.** |

Full per-key reference (storage layouts, apt mirror-selection details, identity, ssh,
command timing) is in `references/schema.md`.

## Air-gapped essentials

```yaml
refresh-installer:
  update: false                      # don't try to self-update from the snap store
proxy: http://proxy.internal:3128    # NOT applied to the geoip lookup
apt:
  geoip: false                       # disable geoip.ubuntu.com lookup (10s hang otherwise)
  preserve_sources_list: false
  mirror-selection:
    primary:
      - uri: "http://mirror.internal/ubuntu"
        arches: [amd64]
  fallback: abort                    # set explicitly; don't silently go offline-from-ISO
updates: security
```

- Wrapping `primary` inside `mirror-selection` enables Subiquity's mirror probing
  (picks the first usable). A bare `primary:` list uses legacy curtin behavior.
- `apt.fallback` ∈ `abort` | `offline-install` | `continue-anyway`. The docs disagree
  on the default — **always set it explicitly.** `offline-install` falls back to the
  ISO's seed; `continue-anyway` is not recommended.
- Snaps requiring the store fail offline — only ship snaps seeded on the ISO, or omit
  `snaps:`. `source.id: ubuntu-server-minimal` reduces footprint.

## storage (quick)

```yaml
storage:
  layout:
    name: lvm                  # lvm | direct | zfs | hybrid
    password: LUKS_PASSPHRASE  # LVM + LUKS
    sizing-policy: all         # use whole VG ('scaled' default leaves snapshot room)
```
Pick a disk with `match: {ssd: true}` / `{serial: ...}` / `{size: largest}`. For
advanced partitioning use a curtin `config:` action list (when `layout` is present,
`config` is ignored). See `references/schema.md`.

## Validation & debugging

```bash
# validate-autoinstall-user-data.py ships in the subiquity SOURCE repo — it is NOT
# bundled in this skill. Get it with: git clone https://github.com/canonical/subiquity
# && cd subiquity && make install_deps. Run from that checkout, NEVER as sudo:
python3 scripts/validate-autoinstall-user-data.py user-data            # #cloud-config-wrapped
python3 scripts/validate-autoinstall-user-data.py --no-expect-cloudconfig autoinstall.yaml
cloud-init schema -c user-data                                         # validate the cloud-config body
```
Install logs live in `/var/log/installer/`; the delivered autoinstall (with password
hash) is saved to `/var/log/installer/autoinstall-user-data`. Full validation
workflow, the JSON schema location, and common pitfalls are in
`references/validation-and-debugging.md`.

## Common pitfalls

- Missing `#cloud-config` header, or a misspelled `autoinstall:` key → the installer
  goes interactive instead of crashing.
- In the **on-media** `autoinstall.yaml`, no other top-level keys may sit beside
  `autoinstall:` — it's fatal. (The `#cloud-config` delivery is the opposite: top-level
  cloud-config configures the installer env.)
- `late-commands` run in the **installer** environment; the target is at `/target`.
  Use `curtin in-target -- <cmd>` to run inside the installed system.
- `interactive-sections: '*'` (string) fails schema — use `['*']`. If any interactive
  section is set, `reporting` is ignored.
- Quote the password hash and the kernel `-append` string.
- Don't pin a `kernel:` together with `oem.install: true` (conflicting requirements).

## Reference files

- `references/schema.md` — full top-level key reference: storage layouts & curtin
  actions, apt mirror-selection, identity/ssh, command timing, all keys. (Has a TOC.)
- `references/delivery-and-seeding.md` — delivery precedence, NoCloud seeds, ISO/USB,
  HTTP serving, zero-touch, the on-media rules.
- `references/validation-and-debugging.md` — the validator script, JSON schema, logs,
  pitfalls, and 24.04-vs-26.04 version notes.
- `references/examples.md` — minimal config + a complete air-gapped server install.
