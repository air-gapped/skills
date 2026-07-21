# netplan CLI, debugging & version notes

Grounded in `canonical/netplan` `doc/netplan-*.md` man pages and
`netplan_cli/cli/commands/*`.

## CLI reference

`netplan [--debug] <command>` — `--debug` is global and goes **before** the
subcommand.

### generate
`netplan generate [--root-dir DIR] [--mapping MAP]` — render YAML → backend files.
Does not apply. **This is your validator** when run from the CLI (it fails loudly on
parse/schema errors with a location). Note: as a *boot-time systemd generator* it
silently ignores errors, so an invalid file can yield partial config and lost
connectivity — always validate via the CLI before rebooting.

### apply
`netplan apply [--sriov-only] [--only-ovs-cleanup] [--state DIR]` — generate, then
bring interfaces up via the backend, unbind/rebind down NICs (lets udev rename rules
run), re-invoke backends if anything rebound.

**Stale virtual devices are not removed.** A bond/bridge/vlan you deleted from YAML
persists until reboot or `ip link delete dev <name>`. To make netplan diff and delete
removed virtual links: keep a backup of the *previous* `/etc/netplan`, then
`netplan apply --state /path/to/backup`.

### try (use this over SSH)
`netplan try [--config-file FILE] [--timeout 120] [--state DIR]` — apply with
automatic rollback. Default timeout is **120 s** (60 s is too short for STP to
settle). Confirm at the prompt to keep, or let it roll back. Send `SIGUSR1` to
accept / `SIGINT` to reject programmatically.

### get / set
- `netplan get [--root-dir DIR] [KEY]` — merged view across `/{etc,lib,run}/netplan`.
  `KEY` defaults to `all`; use a path: `netplan get ethernets.enp1s0.addresses`.
  Output is re-serialized (key order/quoting may differ from source, semantically
  equal).
- `netplan set [--root-dir DIR] [--origin-hint NAME] KEY=VALUE` — write into
  `/etc/netplan/`, validated. Scalar: `netplan set ethernets.eth0.addresses=[1.2.3.4/24]`;
  subtree: `netplan set ethernets.eth0='{dhcp4: true}'`. `--origin-hint=70-foo` →
  `/etc/netplan/70-foo.yaml`. New files are written `0600`.

### status
`netplan status [IFACE] [-a|--all] [--diff] [--diff-only] [-f json|yaml] [--root-dir DIR]`
— running network state. Data source is **systemd-networkd** (it will start networkd
if not masked) + systemd-resolved for DNS. `--all` includes inactive/unmanaged links.
`--diff` compares system vs YAML (IPs, routes, MACs, DNS, search domains, missing
interfaces; `+`/green = system-only, `-`/red = YAML-only). `--format json` for tooling.

### others
- `netplan ip leases <iface>` — DHCP leases.
- `netplan rebind <pf...>` — rebind SR-IOV VFs of the given PF interfaces.
- `netplan info [--json|--yaml]` — version + compiled feature flags.
- `netplan migrate [--dry-run]` — convert legacy `/etc/network/interfaces` →
  netplan YAML (this is where `gateway4/6` get emitted from old `gateway` stanzas).
- `netplan-dbus` — system-bus daemon `io.netplan.Netplan` (used by snapd, libvirt).

## Debugging playbook — "applied but no connectivity"

1. **Validate:** `netplan generate` (and `netplan --debug generate`) — rule out
   syntax/schema errors.
2. **Confirm the merged config:** `netplan get`. Watch for sequence-merge surprises —
   the same `addresses:`/`routes:` key in two files *concatenates*, so you may have
   accumulated an extra address or a duplicate default route.
3. **Watch the apply:** `netplan --debug apply` shows backend invocation.
4. **Inspect emitted backend files** (under `/run`, ephemeral):
   - networkd: `/run/systemd/network/10-netplan-*.{network,netdev,link}`
   - NetworkManager: `/run/NetworkManager/system-connections/*.nmconnection`,
     `/run/NetworkManager/conf.d/netplan.conf`, `/run/udev/rules.d/90-netplan.rules`
5. **Runtime state:** `networkctl status <iface>` / `networkctl list`,
   `ip addr show dev <iface>`, `ip route`, `resolvectl status` for DNS.
6. **Divergence:** `netplan status --diff` flags system-vs-YAML deltas.

Frequent root causes:
- Off-subnet gateway without `on-link: true`.
- Two default routes with the same/colliding metric.
- A stale bond/bridge from a prior apply (netplan won't delete it — see `apply`).
- Renderer mismatch: networkd silently ignores NM-only fields (`modems`,
  `access-points.mode: ap`, NM-only key flags) and vice-versa.
- `dhcp4-overrides` ≠ `dhcp6-overrides` when both DHCP families are on (networkd) →
  apply error.
- Tabs in YAML (illegal) or mis-indentation silently re-scoping keys.

## Pitfalls (quick list)

- **YAML forbids tabs** — spaces only, consistent 2-space nesting.
- **`gateway4`/`gateway6` are deprecated** — use `routes: [{to: default, via: ...}]`.
- **Secrets are world-readable unless you `chmod 600`** — netplan only warns.
- **`apply` doesn't tear down old virtual devices.**
- **`match` + `set-name` must match uniquely** — non-unique match renames only the
  first device, the rest keep their kernel name and log a dmesg error.
- **Apply over SSH = lockout risk** — use `netplan try`.

## Version notes (24.04 LTS vs 26.04 LTS)

- The YAML schema version is always `2`; this is unrelated to the netplan package
  version. (`meson.build` declaring `1.1` is stale — trust git tags / `netplan info`
  / `dpkg -l netplan.io`.)
- **24.04 LTS (Noble)** ships netplan **~1.0 / 1.0.1**. Has `hairpin`,
  `port-mac-learning` (since 1.0), `netplan status --diff`, veth/dummy (0.107),
  vrf/vxlan (0.105). **Does NOT have** `ra-overrides` or route `advertised-mss`
  (both since 1.1).
- **26.04 LTS** tracks the **1.2.x** line (latest **1.2.2**, 2026-07-20 — bug fixes only, no new YAML). Adds `ra-overrides`
  and `advertised-mss` (1.1) plus later fixes.
- **Authoring rule of thumb:** for 24.04 targets avoid `ra-overrides` and
  `routes[].advertised-mss`; both are safe on 26.04. Everything else in
  `schema.md` works on both. Run `netplan info` on the target to confirm feature
  flags (`sriov`, `eswitch-mode`, `infiniband`, `openvswitch`, `regdom`, `vrf`,
  `vxlan`, `virtual-ethernet`) before relying on edge features.
