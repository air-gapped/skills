---
name: ubuntu-netplan
description: >-
  Author, validate, and debug netplan network configuration (`/etc/netplan/*.yaml`)
  for Ubuntu Server LTS 24.04 and 26.04, focused on on-premise and air-gapped hosts —
  static addressing, bonds, bridges, VLANs, VRFs, routing/policy-routing, DNS,
  interface matching/renaming, and the systemd-networkd renderer (NetworkManager and
  desktop covered briefly). Also the shared `network:` substrate for the
  ubuntu-autoinstall and ubuntu-cloud-init skills, which both use netplan v2.
when_to_use: >-
  Use whenever the task touches netplan or `/etc/netplan`, the
  `netplan generate|apply|try|get|set|status` commands, configuring a server's
  IP / gateway / DNS / bond / bridge / VLAN / MTU, diagnosing "no connectivity after
  netplan apply" or boot hangs on a NIC, pinning predictable interface names, or the
  `network:` block of an Ubuntu autoinstall or cloud-init config — even when the user
  only says "set a static IP", "bond two NICs", or "fix my Ubuntu networking".
---

# ubuntu-netplan

Netplan is Ubuntu's network-configuration abstraction: declarative YAML under
`/etc/netplan/` that netplan renders to a backend — **systemd-networkd** (servers,
the default) or **NetworkManager** (desktop) — and uses to bring the network up.
This skill is authoring-led (produce correct YAML from a description) with a strong
validation/debug path, aimed at **on-prem / air-gapped Ubuntu Server LTS**.

Netplan is also the shared network substrate for the sibling skills: cloud-init's
network-config **v2 is netplan format**, and an autoinstall `network:` block **is**
netplan v2. See **Boundaries** at the end.

## Authoring workflow

1. **Confirm target & renderer.** Server → `renderer: networkd` (the default).
   Desktop/Wi-Fi → `renderer: NetworkManager`. Check the running version with
   `netplan info` (24.04 ships ~1.0.x, 26.04 tracks 1.2.x — see version notes).
2. **Pick the device type(s):** `ethernets`, `bonds`, `bridges`, `vlans`, `vrfs`,
   `tunnels`, `dummy-devices`, `virtual-ethernets`, `wifis`, `modems`. Stack them
   bottom-up: ethernets → bond → vlans-on-bond → bridges-on-bond/vlan.
3. **Write the YAML** under `/etc/netplan/`, choosing a filename that orders
   correctly (see precedence). Use 2-space indentation, **never tabs**.
4. **Validate** without applying: `netplan generate` (fails loudly on errors).
5. **Apply safely.** On a remote/SSH host use `netplan try` (auto-rollback), never
   a blind `netplan apply` — see "Apply safely".
6. **Verify:** `netplan status --all`, `ip addr`, `ip route`, and reachability.

## The envelope

Every file is wrapped in:

```yaml
network:
  version: 2                 # only 2 is accepted (v1 does not exist for netplan)
  renderer: networkd         # default if omitted; or NetworkManager
  ethernets: { ... }
  bonds: { ... }
  # ...other device types
```

## File model & precedence (a real source of bugs)

- Files live in `/etc/netplan/*.yaml` (also `/run/netplan/` > `/etc/netplan/` >
  `/lib/netplan/` by directory priority).
- **Same filename in a higher-priority dir fully replaces** the lower one.
- **Different filenames are merged in lexicographic order of the basename**, across
  all directories. So `20-foo.yaml` overrides `10-bar.yaml` even if `10-bar.yaml`
  sits in a higher-priority directory.
- **Per-key merge:** scalars → later wins; **sequences are concatenated, not
  replaced** (two files each listing `addresses:` will *accumulate* both — a classic
  "why do I have an extra IP?" trap); mappings → merged key by key.
- Conventional files commonly present: `50-cloud-init.yaml` (written by cloud-init),
  `00-installer-config.yaml` (Subiquity), `90-NM-<uuid>.yaml` (NetworkManager
  desktop). Use a high number like `99-*.yaml` for hand overrides.
- **Permissions:** netplan only *warns* if a file is group/other-readable; it does
  not refuse or auto-fix. YAML can hold Wi-Fi/WireGuard/EAP secrets, so
  `chmod 600 /etc/netplan/*.yaml`, root-owned. Files netplan writes itself
  (`netplan set`) are already `0600`.

## Quick patterns (the on-prem bread-and-butter)

**Static IPv4 server** (no DHCP — the air-gapped default):

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp1s0:
      dhcp4: false
      dhcp6: false
      addresses: [10.0.10.20/24]
      routes:
        - to: default          # NOT the deprecated gateway4:
          via: 10.0.10.1
      nameservers:
        addresses: [10.0.10.2, 10.0.10.3]
        search: [corp.internal]
```

**Bond (802.3ad / LACP):**

```yaml
network:
  version: 2
  bonds:
    bond0:
      interfaces: [enp1s0, enp2s0]
      parameters:
        mode: 802.3ad
        mii-monitor-interval: 1000     # no suffix = milliseconds
        lacp-rate: fast
      addresses: [10.0.10.20/24]
      routes: [{to: default, via: 10.0.10.1}]
```

**Bridge for a KVM/LXD host** (put the host IP on the bridge so guests attach):

```yaml
network:
  version: 2
  ethernets:
    enp1s0: {dhcp4: false}
  bridges:
    br0:
      interfaces: [enp1s0]
      parameters: {stp: true, forward-delay: 4}
      addresses: [10.0.10.20/24]
      routes: [{to: default, via: 10.0.10.1}]
      nameservers: {addresses: [10.0.10.2]}
```

**VLAN:**

```yaml
network:
  version: 2
  ethernets:
    enp1s0: {dhcp4: false}
  vlans:
    vlan40:
      id: 40
      link: enp1s0
      addresses: [10.0.40.20/24]
```

For the full schema (every device type and property), the bond/bridge parameter
tables, and a complete bonded-VLAN-bridge virtualization-host config, read
`references/schema.md` and `references/examples.md`.

## CLI essentials

| Command | Purpose |
|---|---|
| `netplan generate` | Render YAML → backend files. **Doubles as the validator.** |
| `netplan apply` | Generate, then apply to the running system. |
| `netplan try [--timeout 120]` | Apply with **auto-rollback** if not confirmed. Use over SSH. |
| `netplan get [path]` | Show the merged config (e.g. `netplan get ethernets.enp1s0.addresses`). |
| `netplan set k=v` | Write a key into `/etc/netplan/` (validated; new files `0600`). |
| `netplan status [--all] [--diff]` | Show running state; `--diff` compares system vs YAML. |
| `netplan info` | Show version + supported feature flags. |

`--debug` is a **global** flag placed *before* the subcommand: `netplan --debug apply`.

## Apply safely (don't lock yourself out)

`netplan apply` can drop the SSH session. Prefer:

```bash
netplan generate            # validate first
netplan try --timeout 120   # applies, then rolls back unless confirmed at the prompt
```

`netplan apply` also **does not remove stale virtual devices** (a bond/bridge removed
from YAML lingers until `ip link delete dev <name>` or reboot). See
`references/cli-and-debugging.md` for the `--state` backup-diff workaround.

## Validation & debugging (fast path)

1. `netplan generate` — catches YAML/schema errors with a location.
2. `netplan get` — confirm the *merged* result (remember sequences concatenate
   across files).
3. `netplan --debug apply` — see backend invocation.
4. Inspect the actual emitted backend config in `/run/systemd/network/10-netplan-*`.
5. `networkctl status <iface>` and `netplan status --diff` — carrier, routes, DNS,
   system-vs-YAML divergence.

Common "applied but no connectivity": off-subnet gateway needs `on-link: true`;
duplicate default-route metrics; a stale virtual device from a prior apply;
renderer mismatch. Full playbook in `references/cli-and-debugging.md`.

## Air-gapped / on-prem notes

- Static everything: set `dhcp4: false`, `dhcp6: false`; for a truly static link
  also `accept-ra: false` and `link-local: []` to silence autoconfiguration.
- Point `nameservers.addresses` at internal resolvers and set `search:` to the
  local domain. Set `search: []` on bridges that should not inherit domains.
- Mark disconnected/optional NICs `optional: true` (networkd) so boot doesn't wait
  ~2 minutes for carrier.
- Pin predictable names with `match: {macaddress: ...}` + `set-name:`. **Match by
  MAC** (not name) whenever setting `mtu`, `wakeonlan`, `macaddress`, or offloads —
  name-only matching races udev renaming on networkd.

## Boundaries (when to hand off to a sibling skill)

- **The network block of an autoinstall config is netplan v2.** When working inside
  an `autoinstall:` document, author the `network:` block with this skill, but use
  the **ubuntu-autoinstall** skill for the surrounding install schema.
- **cloud-init network-config v2 is netplan format**; cloud-init writes
  `/etc/netplan/50-cloud-init.yaml` on first boot. To stop cloud-init managing the
  network and own `/etc/netplan` directly, drop
  `/etc/cloud/cloud.cfg.d/99-disable-network-config.cfg` containing
  `network: {config: disabled}`. For first-boot/cloud-config concerns use the
  **ubuntu-cloud-init** skill.

## Reference files

- `references/schema.md` — full YAML schema: all device types, every addressing
  property, complete bond/bridge/vlan/tunnel/vrf parameter tables. (Has a TOC.)
- `references/examples.md` — copy-paste-ready realistic server configs
  (static, multi-NIC multi-gateway, bond+VLAN+bridge VM host, source routing,
  MAC-matching/rename).
- `references/cli-and-debugging.md` — full CLI reference, the debugging playbook,
  and 24.04-vs-26.04 version notes.
