# cloud-init CLI, boot stages, debugging & version notes

Grounded in `canonical/cloud-init` `doc/rtd/reference/cli.rst`,
`explanation/boot.rst`, `first_boot.rst`, and `breaking_changes.rst`.

Contents: Boot stages (units, module order) · CLI reference · Logs & paths ·
Debugging playbook · Version notes (24.04 reverts, changes by version)

## Boot stages

| Stage | systemd unit | Network | Module list |
|---|---|---|---|
| Detect | ds-identify (generator) | none | — enables/disables cloud-init |
| **Local** | `cloud-init-local.service` | blocks net | datasource find + render network |
| **Network** | `cloud-init-network.service` (24.04: `cloud-init.service`) | up | `cloud_init_modules` |
| **Config** | `cloud-config.service` | online | `cloud_config_modules` |
| **Final** | `cloud-final.service` | online | `cloud_final_modules` |

> **24.3 architecture change:** the four stages now run as one process talking to the
> init system over a Unix socket, and `cloud-init.service` was **renamed to
> `cloud-init-network.service`**. External units should order after
> `cloud-config.target`. 25.3 changed the socket protocol. 26.04 runs the
> single-process model; the 24.04 build reverts it (see Version notes).

Ubuntu module ordering (abridged, from `config/cloud.cfg.tmpl`):
- **Network:** seed_random, bootcmd, write_files, growpart, resizefs, disk_setup,
  mounts, set_hostname, update_hostname, update_etc_hosts, **ca_certs**, rsyslog,
  users_groups, ssh, set_passwords.
- **Config:** wireguard, snap, ubuntu_autoinstall, ssh_import_id, keyboard, locale,
  grub_dpkg, apt_pipelining, **apt_configure**, ubuntu_pro, ntp, timezone, runcmd,
  byobu.
- **Final:** package install/upgrade, fan, landscape, lxd, ubuntu_drivers,
  write_files_deferred, puppet/chef/ansible/salt, scripts_*, phone_home,
  final_message, power_state_change.

Note `ca_certs` (Network) runs before `apt_configure` (Config) — internal-CA trust is
in place before apt hits an internal HTTPS mirror.

## CLI reference

```bash
# Validate
cloud-init schema -c user-data --annotate              # a file; errors inline
cloud-init schema -c netcfg.yaml -t network-config     # validate network-config
sudo cloud-init schema --system --annotate             # the live system's user-data
cloud-init schema --docs cc_apt_configure             # one module's docs (or: all)

# Status & introspection
cloud-init status --long --wait                        # exit 0=ok 1=error 2=recoverable
cloud-init query --list-keys                           # instance-data keys
cloud-init query --format '{{ v1.instance_id }}'       # render one value
cloud-init analyze blame                               # per-module timing (also: show, dump, boot)
cloud-id                                               # detected cloud/datasource

# Re-run / golden image
sudo cloud-init clean --logs --machine-id --seed --configs all   # golden image: strip everything
sudo cloud-init single --name set_hostname --frequency always   # re-run one module

# Build helpers
cloud-init devel make-mime -a config.yaml:cloud-config -a setup.sh:x-shellscript
cloud-init-per once mkswap mkswap /dev/vdb             # runs once ever, keyed by name (also: instance, always)
```

- `cloud-init clean` wipes `/var/lib/cloud` so the next boot is treated as first boot.
  `--logs` also clears `/var/log/cloud-init*.log`; `--machine-id` sets
  `/etc/machine-id` to `uninitialized` (the golden-image best practice); `--seed`
  removes `/var/lib/cloud/seed/`.

## Logs & paths

- `/var/log/cloud-init.log`, `/var/log/cloud-init-output.log`
- `/run/cloud-init/` — `ds-identify.log`, `result.json`, `instance-data.json`
- `/var/lib/cloud/` — cache, `seed/`, `instance/`
- `/etc/cloud/cloud.cfg` + `/etc/cloud/cloud.cfg.d/*.cfg`

## Debugging playbook

1. `cloud-init status --long` — overall result + `recoverable_errors`.
2. `cloud-init schema --system --annotate` — catch a malformed config.
3. Grep `/var/log/cloud-init.log` for the failing module (search the module name,
   e.g. `cc_apt_configure`).
4. `cloud-init query --all` — confirm the instance-data the templates/modules saw.
5. Reproduce a single module: `cloud-init single --name <mod> --frequency always`.
6. Full re-run on a **test** box: `cloud-init clean --logs && reboot` (`clean`
   alone makes the next boot a first boot; no `instance-id` bump needed).
7. Air-gapped boot is slow/hangs → check `ds-identify.log`, then pin
   `datasource_list: [NoCloud]` (see `nocloud-and-airgapped.md`).

## Version notes (24.04 patched build vs 26.04)

Both LTS releases receive the same upstream version through SRUs (`-updates`).
Behaviour differs where 24.04's `debian/patches` revert an upstream change; 26.04
ships upstream behaviour:

| Upstream change | 26.04 | 24.04 build |
|---|---|---|
| 24.3 single process, `cloud-init-network.service` | yes | reverted — four processes, unit is `cloud-init.service`; order external units after `cloud-config.target` on both |
| 24.3 NoCloud `network-config` fetched from a `seedfrom` URI | yes | reverted — see `nocloud-and-airgapped.md` |
| Deprecated keys → DEPRECATED log → `cloud-init status` exit **2** | every deprecation | only deprecations dated ≤ 24.1; newer ones log at INFO, exit 0 |
| Network stage waits for network-online manually | yes | reverted — systemd ordering after `systemd-networkd-wait-online` |
| 26.1 OpenStack bond names from `network_data.json` | yes | reverted — `bond0`, `bond1`, … |

Upstream changes by version (`doc/rtd/reference/breaking_changes.rst` plus
deprecations); "24.04" marks the ones its build reverts:

| Version | Change | Action |
|---|---|---|
| 26.1 | ntp client package `ntp` → `ntpsec`; Python 3.8 dropped | none for `ntp_client: auto`/`chrony` |
| 26.1 | OpenStack bond names come from `network_data.json`, not `bond0`/`bond1` (24.04: reverted) | cloud-only |
| 25.3 | systemd socket protocol changed; build moved to meson | update any custom `ExecStart=` for cloud-init units |
| 25.1.4 | strict datasource identity (SKILL.md) — **not** reverted on 24.04 | pin `datasource_list` |
| 25.1 | `/usr` merge — nothing installed to `/lib` | none on Ubuntu |
| 24.4 | `cloud-final.service` ordering standardized | re-check custom units ordered against it |
| 24.3 | single process; `cloud-init.service` → `cloud-init-network.service` (24.04: reverted) | order external units after `cloud-config.target` |
| 24.3 | NoCloud `network-config` fetched from a `seedfrom` URI (24.04: reverted) | see `nocloud-and-airgapped.md` |
| 24.3 | ENI `network-interfaces` in NoCloud `meta-data` deprecated | use network v1/v2 |
| 24.1 | no wait for snapd seeding | a `runcmd` using a snap first runs `[snap, wait, system, seed.loaded]` |
| 24.1 | ds-identify no longer appends `None` to a single-entry `datasource_list` | add `None` explicitly if wanted |
| 24.1 | `nocloud-net` dsname deprecated | use `nocloud`; the `seedfrom` scheme picks Local vs Network |
| 23.4 | deb822 `sources_list` → `/etc/apt/sources.list.d/ubuntu.sources`, and `sources.list` becomes a stub comment | one-line `sources_list` content still goes to `sources.list`; look in both files when debugging apt |

> Where the repo and prior knowledge disagree, trust the repo. In particular, the
> `99-disable-network-config.cfg` filename is a *documented convention*, not a
> hard-coded constant — the load-bearing mechanism is `network: {config: disabled}` in
> any `/etc/cloud/cloud.cfg.d/*.cfg`.
