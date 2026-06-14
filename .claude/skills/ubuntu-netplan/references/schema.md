# netplan YAML schema reference

Grounded in `canonical/netplan` `doc/netplan-yaml.md` (~2200 lines, the
authoritative property list) and source (`src/parse.c`, `src/networkd.c`). Only
`network.version: 2` is accepted. `– since X.Y` markers indicate the netplan
release a property first appeared in (relevant to 24.04 ≈ 1.0.x vs 26.04 ≈ 1.2.x).

## Contents

1. Top-level device types
2. Common addressing & link properties (apply to every device)
3. ethernets
4. bonds (full parameter table)
5. bridges (full parameter table)
6. vlans
7. vrfs
8. tunnels (incl. WireGuard, VXLAN)
9. dummy-devices, virtual-ethernets
10. wifis, modems (brief)
11. nm-devices (passthrough)

---

## 1. Top-level device types

Under `network:` you may declare any of these maps (id → config):
`ethernets`, `bonds`, `bridges`, `vlans`, `vrfs`, `tunnels`, `dummy-devices`,
`virtual-ethernets`, `wifis`, `modems`, `nm-devices`.

The device id is the interface name **unless** `match:` is present, in which case
the id is just an opaque anchor and the real name comes from the match (and
optional `set-name`).

## 2. Common addressing & link properties

These apply to (almost) every device type.

| Property | Notes |
|---|---|
| `dhcp4` / `dhcp6` | booleans, both **default false**. `dhcp6: true` also does stateless DHCPv6. |
| `dhcp4-overrides` / `dhcp6-overrides` | mapping: `use-dns`, `use-ntp`, `send-hostname`, `use-hostname`, `use-mtu`, `hostname`, `use-routes`, `route-metric`, `use-domains`. Mostly networkd-only; **`use-routes` + `route-metric` work on NM too.** If both dhcp4 & dhcp6 are on (networkd), the two override blocks must be identical. |
| `accept-ra` | accept IPv6 Router Advertisements. |
| `ra-overrides` | **since 1.1** (NOT on 24.04), networkd-only: `use-dns`, `use-domains`, `table`. |
| `addresses` | list of `addr/prefixlen` (CIDR). Entries may be mappings with `lifetime: forever\|0` and `label:` (both networkd-only, since 0.100). |
| `routes` | list of `{to, via, from, metric, on-link, table, scope, type, mtu, advertised-mss}`. `to: default` replaces `gateway4/6`. `on-link: true` for an off-subnet gateway. `type` ∈ `unicast`(default), `blackhole`, `unreachable`, `prohibit`, `local`, `nat`, `throw`. `advertised-mss` is **since 1.1**. |
| `routing-policy` | policy routing (networkd): `{from, to, table, priority, mark, type-of-service}`. On NM `priority` is mandatory + unique. |
| `nameservers` | `{addresses: [...], search: [...]}`. |
| `gateway4` / `gateway6` | **DEPRECATED** — use a `routes:` default entry. Only one per family. |
| `match` | physical devices only: `name` (globs OK), `macaddress` (no globs), `driver` (udev DRIVER, networkd-only). All listed must match. |
| `set-name` | rename a matched device. Pair with a uniquely-matching `match`. |
| `mtu` | default 1500. |
| `macaddress` | set/override MAC. |
| `wakeonlan` | bool, default off. |
| `optional` | bool, networkd-only — don't wait for this link at boot. |
| `optional-addresses` | e.g. `[ipv4-ll, dhcp6]` — don't block "online" on these. |
| `critical` | keep IP across daemon restart (networkd-only). |
| `activation-mode` | `manual` / `off` (since 0.103; implies `optional`; networkd v248+). |
| `ignore-carrier` | since 0.104, networkd-only. |
| `link-local` | `[ipv4]`, `[ipv4, ipv6]`, or `[]` to disable link-local entirely. |

> **udev rename race warning (repeated in the docs):** name-only `match` + networkd
> is unreliable for `wakeonlan`, `mtu`, `macaddress`, and offload settings. Match by
> **MAC** when setting any of those.

## 3. ethernets

```yaml
ethernets:
  enp3s0:
    addresses: [10.10.10.2/24]
    routes: [{to: default, via: 10.10.10.1}]
    nameservers: {addresses: [10.10.10.1], search: [mydomain]}
```

Ethernet-only extras (SR-IOV / InfiniBand): `link:` (VF→PF, 0.99),
`virtual-function-count` (0.99), `embedded-switch-mode` (`switchdev`/`legacy`,
0.104), `delay-virtual-functions-rebind` (0.104), `infiniband-mode`
(`datagram`/`connected`, 0.105). You can also override loopback (`lo` with extra
addresses).

## 4. bonds

```yaml
bonds:
  bond0:
    interfaces: [enp1s0, enp2s0]      # members, defined elsewhere
    parameters:
      mode: 802.3ad
      mii-monitor-interval: 1000
    addresses: [10.0.0.5/24]
```

`parameters` keys:

| Key | Values / notes |
|---|---|
| `mode` | `balance-rr`(default), `active-backup`, `balance-xor`, `broadcast`, `802.3ad`, `balance-tlb`, `balance-alb` (+ OVS `balance-tcp`/`balance-slb`). |
| `mii-monitor-interval` | link check; **no suffix ⇒ milliseconds**. |
| `lacp-rate` | `slow`(30s, default) / `fast`(1s); 802.3ad only. |
| `transmit-hash-policy` | `layer2`/`layer3+4`/`layer2+3`/`encap2+3`/`encap3+4`. |
| `ad-select` | `stable`/`bandwidth`/`count` (802.3ad). |
| `primary` | preferred port (active-backup / balance-alb/tlb). |
| `min-links`, `up-delay`, `down-delay` | up/down delays in ms (miimon only). |
| `arp-interval`, `arp-ip-targets` (≤16), `arp-validate`, `arp-all-targets` | ARP monitoring. |
| `fail-over-mac-policy` | `none`/`active`/`follow`. |
| `gratuitous-arp` | 1–255 (the misspelling `gratuitious-arp` is also accepted). |
| `packets-per-member` | 0.106 (alias `packets-per-slave`). |
| `all-members-active` | 0.106 (alias `all-slaves-active`). |
| `primary-reselect-policy`, `resend-igmp`, `learn-packet-interval` | tuning. |

## 5. bridges

```yaml
bridges:
  br0:
    interfaces: [enp1s0]          # may be empty list (bridge up with no members)
    parameters:
      stp: true                   # DEFAULT true
      forward-delay: 4            # seconds (no suffix)
      priority: 32768
    addresses: [10.0.0.5/24]
```

`parameters` keys: `stp` (bool, **default true**), `forward-delay`
(→`ForwardDelaySec`), `priority` (0–65535, lower wins root election), `path-cost`
(per-member map `{eth0: 100}`), `port-priority` (per-member 0–63), `hello-time`,
`max-age`, `ageing-time`/`aging-time`. Time values: no suffix ⇒ seconds.

Bridge *port* properties live on the **member** interface: `neigh-suppress`
(0.105), `hairpin` (**since 1.0**), `port-mac-learning` (**since 1.0**,
networkd-only).

## 6. vlans

```yaml
vlans:
  vlan40:
    id: 40              # 0–4094
    link: enp1s0        # parent netplan id, must be defined
    addresses: [10.0.40.5/24]
```

Only `id` and `link` are VLAN-specific; all common addressing props apply.

## 7. vrfs

```yaml
vrfs:
  vrf1:
    table: 1            # compulsory (since 0.105)
    interfaces: [enp1s0]
    routes: [{to: default, via: 10.10.10.4}]
    routing-policy: [{from: 10.10.10.42}]
```

`routes`/`routing-policy` inside a VRF inherit the VRF's `table`.

## 8. tunnels

`mode` (required) ∈ `sit, gre, ip6gre, ipip, ipip6, ip6ip6, vti, vti6, wireguard,
vxlan, gretap, ip6gretap` (+ NM-only `isatap`). Keys: `local`, `remote`, `ttl`
(0.103), `key`/`keys`.

**WireGuard** (since 0.100):
```yaml
tunnels:
  wg0:
    mode: wireguard
    addresses: [10.9.0.1/24]
    port: 51820
    key: <base64 private key>            # chmod 600 the file!
    peers:
      - keys: {public: <base64>, shared: <base64>}
        allowed-ips: [10.9.0.2/32]
        endpoint: 203.0.113.5:51820
        keepalive: 25
```

**VXLAN** (since 0.105): `id` (VNI), `link`, `port` (set `4789` for IANA),
`mac-learning`, `ageing`, `limit`, `arp-proxy`, `port-range`, etc.

## 9. dummy-devices, virtual-ethernets

```yaml
dummy-devices:                # since 0.107
  dm0: {addresses: [192.168.0.123/24]}
virtual-ethernets:            # veth pair, since 0.107
  veth0: {peer: veth1}
  veth1: {peer: veth0}        # both ends must be defined, mutual peer
```

## 10. wifis, modems (brief — prefer NetworkManager)

```yaml
wifis:
  wlp0s1:
    access-points:
      "MySSID": {password: "..."}        # WPA3: auth: {key-management: sae}
```
AP keys: `password`, `mode` (`infrastructure`/`ap`/`adhoc`), `bssid`, `band`
(`2.4GHz`/`5GHz`), `channel`, `hidden`. networkd needs `wpasupplicant`; `mode: ap`
is NM-only.

`modems` (NetworkManager only): `apn`, `auto-config`, `device-id`, `network-id`,
`number`, `password`, `pin`, `sim-id`, `sim-operator-id`, `username` (all 0.99).

## 11. nm-devices (passthrough, "not recommended")

`networkmanager: {uuid, name, passthrough: {raw.nm.keys: ...}}` — raw NM keyfile
passthrough for connection types netplan can't model (e.g. VPN). Internal use only.
