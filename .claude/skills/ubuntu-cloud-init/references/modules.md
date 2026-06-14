# cloud-config module reference

Grounded in `canonical/cloud-init` `cloudinit/config/schemas/schema-cloud-config-v1.json`,
`cloudinit/config/cc_*.py`, `config/cloud.cfg.tmpl` (Ubuntu ordering/defaults), and
`doc/module-docs/cc_*/example*.yaml`. Validate any config with
`cloud-init schema -c <file> --annotate`, and read per-module docs with
`cloud-init schema --docs <cc_name>`.

## Contents

1. Module stages & frequency (how to read this file)
2. users / groups
3. ssh / set_passwords
4. write_files
5. runcmd / bootcmd
6. apt (full)
7. packages / package upgrade
8. ca_certs
9. disk_setup / fs_setup / mounts / growpart / resizefs
10. ntp
11. timezone / locale / keyboard / hostname
12. power_state / phone_home / snap / seed_random
13. Other modules (by stage)

---

## 1. Module stages & frequency

Modules run in one of three lists (configured in `/etc/cloud/cloud.cfg`):
`cloud_init_modules` (Network stage), `cloud_config_modules` (Config stage),
`cloud_final_modules` (Final stage). Default frequency is **per-instance**; change a
list entry from `modname` to `[modname, always]` to run every boot (`per-boot`),
`once` for `per-once`.

## 2. users / groups (`cc_users_groups`, Network stage)

User keys: `name` (required), `gecos`, `groups` (list or comma-string), `homedir`,
`primary_group`, `system` (no home), `uid`, `shell`, `expiredate`, `inactive`,
`lock_passwd` (**default true**), `passwd` (hash, applied **only to new users**),
`hashed_passwd` (hash, applied **even to existing**), `plain_text_passwd`
(discouraged), `sudo` (string/list/`null`; not validated by cloud-init), `doas`,
`ssh_authorized_keys` (list), `ssh_import_id`, `ssh_redirect_user` (reject login,
redirect to default user), `no_create_home`, `no_user_group`, `create_groups`,
`snapuser`, `selinux_user`.

- Keep `default` as the **first** list item to retain the distro user + cloud SSH
  keys. Omitting it skips that user entirely.
- Groups are added before users; group members must already exist.
- Hash: `mkpasswd --method=SHA-512 --rounds=4096`.

## 3. ssh / set_passwords (Network stage)

`cc_ssh`: `ssh_authorized_keys`, `allow_public_ssh_keys` (default true),
`disable_root` (default true), `disable_root_opts`, `ssh_deletekeys` (regen image
host keys on first boot, default true), `ssh_genkeytypes` (default
`[rsa, ecdsa, ed25519]`), `ssh_quiet_keygen`, and **host-key injection** via
`ssh_keys: {rsa_private, rsa_public, ed25519_private, ...}`. `ssh_publish_hostkeys`
is a no-op on NoCloud (nowhere to publish).

`cc_set_passwords`: `ssh_pwauth` (rewrites sshd config; **Ubuntu default false**),
`password` (default user), `chpasswd: {expire (default true!), users: [{name,
password, type: text|RANDOM|hash}]}`. For console debugging: set `password:` +
`ssh_pwauth: true` + `chpasswd: {expire: false}`.

## 4. write_files (`cc_write_files` Network; deferred copy in Final)

Keys: `path`, `content`, `source: {uri, headers}` (fetch remote — point at the local
seed server air-gapped), `owner` (default `root:root`), `permissions` (octal string,
default `'0644'`), `encoding` (`text/plain` default; `b64`/`base64`, `gz`/`gzip`,
`gz+b64`), `append` (default false), `defer: true` (write in the Final stage, after
users + packages).

## 5. runcmd / bootcmd

- `bootcmd` (`cc_bootcmd`, **Network stage, every boot**) — guard once-only work with
  `cloud-init-per once <name> <cmd>`.
- `runcmd` (`cc_runcmd`, **Config stage, once per instance**) — each item is a shell
  string or an argv list (`[systemctl, enable, --now, foo]`, no shell).

## 6. apt (`cc_apt_configure`, Config stage) — full

Top key `apt:`:

- `preserve_sources_list` (bool) — Ubuntu cloud images default **false** (regenerate);
  Debian base default **true**.
- `primary` / `security` — list of per-arch entries. Each: `arches: [...]` (`default`
  = catch-all), then **`uri:`** (one mirror) **or** `search: [url, ...]` (first
  resolvable wins) **or** `search_dns: true` (`<distro>-mirror` lookup). If `primary`
  is set but not `security`, primary is reused for security.
- `sources_list` — template for the generated file; vars `$MIRROR`, `$RELEASE`,
  `$PRIMARY`, `$SECURITY`, `$KEY_FILE`. **deb822-aware since 23.4:** deb822 content
  (`Types:`/`URIs:`/`Suites:`/`Components:`) is written to
  `/etc/apt/sources.list.d/ubuntu.sources` instead of `/etc/apt/sources.list`.
- `disable_suites` — comment out suites; aliases `updates`→`$RELEASE-updates`,
  `backports`, `security`, `proposed`, `release`→`$RELEASE`.
- `sources` — dict of `id: {source, keyid, key, keyserver, filename, append}`.
  `source` supports the `$MIRROR/$PRIMARY/$SECURITY/$RELEASE/$KEY_FILE` vars. **Embed
  `key:` inline** (a raw PGP block) air-gapped; don't rely on `keyserver`.
- `proxy` / `http_proxy` / `https_proxy` / `ftp_proxy`.
- `conf` — raw APT config string. `debconf_selections` — debconf preseeds.
  `add_apt_repo_match` — regex for `add-apt-repository`.

## 7. packages / upgrade (`cc_package_update_upgrade_install`, Final stage)

`packages:` (names, `[name, version]` pairs, or `{apt: [...], snap: [...]}`),
`package_update` (apt-get update; forced true if packages/upgrade requested),
`package_upgrade` (dist-upgrade — **avoid air-gapped without a full mirror**),
`package_reboot_if_required`.

## 8. ca_certs (`cc_ca_certs`, Network stage) — internal CA

`ca_certs: {trusted: [<PEM cert(s)>], remove_defaults: <bool>}`. Runs in the Network
stage, **before** apt in the Config stage, so HTTPS to an internal mirror/registry
works during the same boot. `remove_defaults: true` wipes shipped CAs
(security-sensitive — use only deliberately).

## 9. disk_setup / fs_setup / mounts / growpart / resizefs (Network stage)

- `device_aliases: {alias: /dev/X}`
- `disk_setup: {<dev>: {table_type: mbr|gpt, layout: true|[pct,...], overwrite: bool}}`
- `fs_setup: [{device, filesystem, label, cmd?}]`
- `mounts: [[dev, mountpoint, fstype, opts, dump, pass], ...]`, `mount_default_fields`,
  `swap: {filename, size, maxsize}`
- `growpart: {mode: auto|growpart|off, devices: [/], ignore_growroot_disabled}`;
  `resize_rootfs: true|false|noblock`

## 10. ntp (`cc_ntp`, Config stage) — local time source

`ntp: {enabled, ntp_client (auto|chrony|ntp|systemd-timesyncd), pools: [...],
servers: [...], peers, allow, config: {confpath, template, packages, service_name,
check_exe}}`. Ubuntu default `ntp_client: auto`. (26.1: the `ntp` client package
moved to `ntpsec`.)

## 11. timezone / locale / keyboard / hostname (Config / Network)

`timezone: America/New_York`; `locale: en_US.UTF-8` (+ `locale_configfile`);
`keyboard: {layout, model, variant, options}`; hostname via `hostname`, `fqdn`,
`preserve_hostname`, `create_hostname_file`, `manage_etc_hosts`
(true/false/`localhost`).

## 12. power_state / phone_home / snap / seed_random (Final)

- `power_state: {mode: poweroff|halt|reboot, delay: now|<min>, timeout: <s>, message,
  condition: true|false|<cmd>}` — runs last.
- `phone_home: {url, post: all|[keys], tries}` — **AVOID air-gapped** (network
  call-out; only retries+logs failures).
- `snap: {assertions: {...}, commands: {...}}` — largely unusable fully air-gapped
  without a local store; pre-`snap ack` assertions + install from local `.snap`.
  Hold updates: `snap refresh --hold=forever`.
- `seed_random: {file, data, encoding, command, command_required}`.

## 13. Other modules (present, by stage)

**Network:** `set_hostname`, `update_hostname`, `update_etc_hosts`, `rsyslog`,
`seed_random`. **Config:** `wireguard`, `ssh_import_id`, `keyboard`, `grub_dpkg`,
`apt_pipelining`, `ubuntu_pro`, `disable_ec2_metadata`, `byobu`, `ubuntu_autoinstall`
(passes the `autoinstall` key to Subiquity — cloud-init ignores it). **Final:** `fan`,
`landscape`, `lxd`, `ubuntu_drivers`, `puppet`, `chef`, `ansible`, `mcollective`,
`salt_minion`, `reset_rmc`, `scripts_*`, `ssh_authkey_fingerprints`,
`keys_to_console`, `install_hotplug`, `final_message`. RedHat/SUSE-only:
`yum_add_repo`, `zypper_add_repo`, `rh_subscription`. Alpine: `apk_configure`. Newer:
`raspberry_pi` (24.x).
