# netplan examples (server / on-prem)

All examples are `network: version 2`, `renderer: networkd` unless noted. Mirrors
the patterns in `canonical/netplan/examples/*.yaml` and the `doc/*-vm-host*.md`
how-tos.

## Static single NIC

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp6s0:
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []                 # fully static: no IPv4/IPv6 link-local
      addresses: [172.16.0.10/24]
      routes:
        - to: default
          via: 172.16.0.254
      nameservers:
        addresses: [172.16.0.254, 172.16.0.253]
        search: [example.local]
```

## Off-subnet / point-to-point gateway

```yaml
network:
  version: 2
  ethernets:
    enp1s0:
      addresses: [10.0.0.5/32]
      routes:
        - to: default
          via: 10.10.10.1
          on-link: true              # gateway not on our subnet
```

## Two NICs, two default routes (metric to disambiguate)

```yaml
network:
  version: 2
  ethernets:
    enp1s0:
      addresses: [10.0.10.5/24]
      routes: [{to: default, via: 10.0.10.1, metric: 100}]
    enp2s0:
      addresses: [10.0.20.5/24]
      routes: [{to: default, via: 10.0.20.1, metric: 200}]
```

For DHCP NICs use `dhcp4-overrides: {route-metric: 100}` instead.

## Bonded + VLAN + bridge virtualization host (4 NICs)

The canonical KVM/LXD host pattern: bond three NICs with LACP, carve out tagged
VLANs, and put IPs on bridges so guests can attach. (One NIC left free for VM
passthrough.)

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eno1: {dhcp4: false}             # reserved for passthrough
    eno2: {dhcp4: false}
    eno3: {dhcp4: false}
    eno4: {dhcp4: false}
  bonds:
    bond0:
      dhcp4: false
      interfaces: [eno2, eno3, eno4]
      parameters: {mode: 802.3ad, mii-monitor-interval: 1000}
  vlans:
    bond0-vlan40: {id: 40, link: bond0}
    bond0-vlan41: {id: 41, link: bond0}
  bridges:
    br0:                             # untagged management network
      interfaces: [bond0]
      dhcp4: false
      addresses: [192.168.150.10/24]
      routes: [{to: default, via: 192.168.150.254, metric: 100, on-link: true}]
      nameservers: {addresses: [192.168.150.2], search: []}
    br0-vlan40:
      interfaces: [bond0-vlan40]
      dhcp4: false
      addresses: [192.168.151.10/24]
      nameservers: {addresses: [192.168.150.2]}
    br0-vlan41:
      interfaces: [bond0-vlan41]
      dhcp4: false
      addresses: [192.168.152.10/24]
      nameservers: {addresses: [192.168.150.2]}
```

Stacking order: ethernets → bond → VLANs on the bond → bridges on bond/VLANs. The
bridges carry the IPs; libvirt then uses `<forward mode="bridge"/><bridge name="br0"/>`.

## Source/policy routing (two uplinks, reply on the same link)

```yaml
network:
  version: 2
  ethernets:
    enp1s0:
      addresses: [10.0.10.5/24]
      routes:
        - {to: default, via: 10.0.10.1, table: 101}
      routing-policy:
        - {from: 10.0.10.5, table: 101}
    enp2s0:
      addresses: [10.0.20.5/24]
      routes:
        - {to: default, via: 10.0.20.1, table: 102}
      routing-policy:
        - {from: 10.0.20.5, table: 102}
```

## Pin a predictable name by MAC (and set MTU safely)

Match by MAC — not interface name — whenever you also set `mtu`/`wakeonlan`/MAC,
because name-only matching races udev renaming on networkd.

```yaml
network:
  version: 2
  ethernets:
    lan0:
      match: {macaddress: "52:54:00:ab:cd:ef"}
      set-name: lan0
      mtu: 9000
      addresses: [10.0.10.5/24]
      routes: [{to: default, via: 10.0.10.1}]
```

## Single-NIC bridge (simple VM host)

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp1s0: {dhcp4: false}
  bridges:
    br0:
      interfaces: [enp1s0]
      addresses: [10.0.10.5/24]
      routes: [{to: default, via: 10.0.10.1}]
      nameservers: {addresses: [10.0.10.2]}
      parameters: {stp: true, forward-delay: 4}
```
