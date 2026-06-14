# autoinstall schema reference (version 1)

Grounded in `canonical/subiquity` `autoinstall-schema.json`,
`doc/reference/autoinstall-reference.rst`, and `doc/reference/autoinstall-schema.rst`.
Only `version` is schema-required; `additionalProperties: true`, so unknown keys are a
*warning* in v1 (documented to become fatal in a future version).

## Contents

1. All top-level keys
2. identity
3. ssh
4. apt (mirror-selection, components, proxy, fallback)
5. storage (layouts + curtin actions)
6. packages / snaps / kernel / drivers / source
7. command hooks (early/late/error) & timing
8. interactive-sections, reporting, updates, shutdown

---

## 1. All top-level keys

| Key | Purpose | Notes |
|---|---|---|
| `version` | format version | **required**, `1` |
| `interactive-sections` | sections to still prompt for | list; `['*']` = all; disables `reporting` |
| `early-commands` | run at installer start, before probing | config re-read afterward |
| `locale` | installed-system locale | default `en_US.UTF-8` |
| `refresh-installer` | `{update: bool, channel}` | self-update installer snap; set `update: false` air-gapped |
| `keyboard` | `{layout, variant, toggle}` | → `/etc/default/keyboard` |
| `source` | `{id, search_drivers}` | install source; `id: ubuntu-server-minimal` for small footprint |
| `network` | **netplan v2** | → ubuntu-netplan skill; default DHCPv4 on en*/eth* |
| `proxy` | URL or null | install + target apt/snapd; NOT applied to geoip |
| `apt` | mirror/repo config | see §4 |
| `storage` | disk layout | see §5 |
| `identity` | initial user | required at runtime unless `user-data:` present; see §2 |
| `active-directory` | `{admin-name, domain-name}` | AD join |
| `ubuntu-pro` | `{token}` | Pro attach (`ubuntu-advantage` is the deprecated alias) |
| `ssh` | ssh server + keys | see §3 |
| `codecs` | `{install: bool}` | restricted addons |
| `drivers` | `{install: bool}` | third-party drivers |
| `oem` | `{install: bool\|"auto"}` | OEM meta-packages; don't combine with a pinned `kernel:` |
| `snaps` | list of `{name, channel?, classic?}` | store-dependent (fails offline) |
| `debconf-selections` | multi-line string | debconf set-selections |
| `packages` | list of strings | `apt-get install`; supports `pkg=ver`, tasks `name^` |
| `kernel` | `{package}` OR `{flavor}` | mutually exclusive |
| `kernel-crash-dumps` | `{enabled: bool\|null}` | **24.10+** (not 24.04); null = dynamic on capable HW |
| `timezone` | tz string | |
| `updates` | `security` (default) \| `all` | which pockets to pull before reboot |
| `shutdown` | `reboot` (default) \| `poweroff` | |
| `late-commands` | post-install commands | target at `/target`; see §7 |
| `early-commands` | pre-probe commands | |
| `error-commands` | on-failure commands | non-zero exit ignored here |
| `reporting` | progress reporting | ignored if any interactive section |
| `user-data` | cloud-config for installed system | → ubuntu-cloud-init skill; satisfies the identity requirement |
| `zdevs` | IBM Z device enablement | **24.10+** (not 24.04) |

Command-list items are a string (run via `sh -c`) or a list (run directly), as root;
non-zero exit aborts the install (except `error-commands`).

## 2. identity

```yaml
identity:
  realname: "Deploy User"
  username: deploy
  hostname: app-01
  password: "$6$rounds=4096$...hashed..."   # quote it; mkpasswd --method=SHA-512
```
Required at runtime unless `user-data:` is present. Users here are created **during
install** (vs first-boot for `user-data` users).

## 3. ssh

```yaml
ssh:
  install-server: true
  allow-pw: false
  authorized-keys:
    - ssh-ed25519 AAAA... admin@bastion
```

## 4. apt

The `apt` object is **not** locked down (`additionalProperties` open) — full curtin
apt config passes through. Default uses `mirror-selection` with country mirrors and
`geoip: true`.

```yaml
apt:
  preserve_sources_list: false
  geoip: false                       # air-gapped: kill the geoip.ubuntu.com lookup
  mirror-selection:
    primary:
      - uri: "http://mirror.internal/ubuntu"
        arches: [amd64]
  fallback: abort                    # abort | offline-install | continue-anyway — SET EXPLICITLY
  disable_components: [multiverse]   # enum: multiverse, universe, restricted, contrib, non-free
  preferences:
    - package: "*"
      pin: "origin mirror.internal"
      pin-priority: 1000
  sources:                           # PPAs / extra repos (curtin passthrough)
    internal.list:
      source: "deb http://mirror.internal/app stable main"
```

- **Wrapping `primary` inside `mirror-selection`** activates Subiquity's probing
  (tests each candidate, picks the first usable). A bare top-level `primary:` list is
  the legacy curtin path.
- `fallback: offline-install` flips the installer to an offline install from the ISO
  seed; `continue-anyway` is documented as not recommended (the install fails).

## 5. storage

`storage` is an open object — real validation is at runtime. Default is `lvm` on a
single disk; **no default for multi-disk**.

**Layouts** (`layout.name`): `lvm`, `direct`, `zfs`, `hybrid` (TPM-backed).

```yaml
# whole-disk LVM (the common server default)
storage: {layout: {name: lvm}}

# direct, choose disk by match spec
storage:
  layout:
    name: direct
    match: {ssd: true}               # or {serial: ...}, {path: ...}, {size: largest|smallest}

# LVM + LUKS
storage:
  layout:
    name: lvm
    password: LUKS_PASSPHRASE
    sizing-policy: all               # 'scaled' (default) leaves room for snapshots

# TPM-backed
storage: {layout: {name: hybrid, encrypted: yes}}
```

- `ptable: msdos` forces MBR (default GPT, except s390x).
- `reset-partition: true|<size>` and `reset-partition-only: true` for OEM provisioning.
- Match spec keys: `model`, `vendor`, `path`, `id_path`, `devpath`, `serial` (globbed),
  `ssd: bool`, `size: largest|smallest|<bytes>`, `install-media: true`. Since 24.08.1
  `match` may be an *ordered list* of specs.

**Advanced partitioning** uses a curtin action list under `config:` (`disk`,
`partition`, `lvm_volgroup`, `lvm_partition`, `raid`, `format`, `mount`). Sizes accept
`1G`/`512M`/`50%`/`-1` (fill). **When `layout` is present, `config` is ignored.** RAID
0/1/5/6/10 supported.

## 6. packages / snaps / kernel / drivers / source

```yaml
packages: [vim, htop, "nginx=1.24.*"]
snaps:
  - name: lxd
    channel: latest/stable
    classic: false
kernel: {flavor: hwe}                # OR {package: linux-image-...} — not both
drivers: {install: false}
source: {id: ubuntu-server-minimal, search_drivers: false}
```

### kernel: `flavor` vs `package`

`kernel` is a mutually-exclusive mapping — set exactly one of `flavor` or `package`.

`flavor` is resolved to a meta-package name:

| `flavor` | installed meta-package |
|---|---|
| `generic` | `linux-generic` (the GA kernel) |
| `hwe` | `linux-generic-hwe-<release>` → `linux-generic-hwe-24.04` on 24.04, `linux-generic-hwe-26.04` on 26.04 |
| any other `X` | `linux-X-<release>` |

`<release>` comes from `lsb_release` (the target's Ubuntu version). So `flavor: hwe`
is just shorthand for the release-pinned HWE metapackage; `package:` names a kernel
package literally (e.g. `linux-generic-hwe-24.04`, or a versioned
`linux-image-6.8.0-40-generic`).

**Defaults:** omit `kernel:` entirely and the default is ISO-build-specific —
generally `generic` for **Server**, `hwe` for **Desktop**. If `kernel:` is present but
neither sub-key is set, it defaults to `flavor: generic` → `linux-generic`.

`flavor` is interpolated straight into the package name without an existence check, so
a flavor with no kernel for that release (or a typo) builds a non-existent
`linux-<flavor>-<release>` that fails at install time, not validation.
(Don't combine a pinned `kernel:` with `oem.install: true` — see §8 pitfalls.)

## 7. command hooks & timing

- `early-commands` — before probing; the config is re-read afterward (you can rewrite
  `/autoinstall.yaml`).
- `late-commands` — after the install, **in the installer environment**; the target
  filesystem is mounted at **`/target`**. To run inside the installed system use
  `curtin in-target -- <cmd>`:

```yaml
late-commands:
  - curtin in-target -- systemctl disable systemd-networkd-wait-online.service
  - echo "deployed" > /target/etc/deploy-stamp
```

- `error-commands` — run on failure; their own non-zero exit is ignored.

## 8. interactive-sections, reporting, updates, shutdown

```yaml
interactive-sections: ['*']          # MUST be a list; '*' (string) fails schema
updates: security                    # or 'all'
shutdown: reboot                     # or 'poweroff'
reporting:                           # ignored if any interactive section is set
  builtin: {type: print}
```
