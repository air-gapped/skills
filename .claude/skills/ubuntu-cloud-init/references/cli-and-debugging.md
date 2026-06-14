# cloud-init CLI, boot stages, debugging & version notes

Grounded in `canonical/cloud-init` `doc/rtd/reference/cli.rst`,
`explanation/boot.rst`, `first_boot.rst`, and `breaking_changes.rst`.

## Boot stages

| Stage | systemd unit | Network | Module list |
|---|---|---|---|
| Detect | ds-identify (generator) | none | — enables/disables cloud-init |
| **Local** | `cloud-init-local.service` | blocks net | datasource find + render network |
| **Network** | `cloud-init-network.service` | up | `cloud_init_modules` |
| **Config** | `cloud-config.service` | online | `cloud_config_modules` |
| **Final** | `cloud-final.service` | online | `cloud_final_modules` |

> **24.3 architecture change:** the four stages now run as one process talking to the
> init system over a Unix socket, and `cloud-init.service` was **renamed to
> `cloud-init-network.service`**. External units should order after
> `cloud-config.target`. 25.3 changed the socket protocol. (24.04 and 26.1 both have
> the single-process model.)

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
cloud-init schema --docs all|<cc_name>                 # module documentation

# Status & introspection
cloud-init status --long --wait                        # exit 0=ok 1=error 2=recoverable
cloud-init query --all | --list-keys | <key> | --format '{{ v1.instance_id }}'
cloud-init analyze blame|show|dump|boot                # timing
cloud-id                                               # detected cloud/datasource

# Re-run / golden image
sudo cloud-init clean [--logs] [--reboot] [--machine-id] [--seed] [--configs all]
sudo cloud-init single --name set_hostname --frequency always   # re-run one module

# Build helpers
cloud-init devel make-mime -a config.yaml:cloud-config -a setup.sh:x-shellscript
cloud-init devel net-convert ...
cloud-init-per once <name> <cmd>                       # frequency-guarded command
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
6. Full re-run on a test box: `cloud-init clean --logs && reboot` (remember to also
   bump `instance-id` if you only changed user-data, or `clean` handles it).
7. Air-gapped boot is slow/hangs → check `ds-identify.log`; you almost certainly need
   to pin `datasource_list: [NoCloud]` (see `nocloud-and-airgapped.md`).

## Version notes (24.04 / 24.x vs 26.04 / 26.1)

- **NoCloud:** `nocloud-net` dsname deprecated 24.1; ENI `network-interfaces` in
  meta-data deprecated 24.3; NoCloud `network-config` support added 24.3 (missing file
  on an HTTP seed → boot retry/timeout, so ship an empty one). Canonical cmdline is
  `ds=nocloud;s=<uri>/`. All present on both 24.04 and 26.1.
- **datasource_list:** 24.1 stopped auto-appending `None` to single-entry lists — add
  it explicitly if wanted.
- **Architecture:** 24.3 single-process + service rename; 25.1 `/usr` merge; 25.3
  socket-protocol change; 25.3 build system moved to meson.
- **26.1 specifics:** ntp client moved `ntp`→`ntpsec`; dropped Python 3.8; OpenStack
  bond-name change (cloud-only, irrelevant to NoCloud). None affect the NoCloud
  authoring path.
- **deb822 apt sources** (since 23.4): deb822 `sources_list` content is written to
  `/etc/apt/sources.list.d/ubuntu.sources` on both releases.

> Where the repo and prior knowledge disagree, trust the repo. In particular, the
> `99-disable-network-config.cfg` filename is a *documented convention*, not a
> hard-coded constant — the load-bearing mechanism is `network: {config: disabled}` in
> any `/etc/cloud/cloud.cfg.d/*.cfg`.
