# autoinstall examples

## Minimal valid config

Only `version` is schema-required, but `identity` is required at runtime (unless
`user-data:` is present). The password hash below is `ubuntu`.

```yaml
#cloud-config
autoinstall:
  version: 1
  identity:
    hostname: ubuntu-server
    username: ubuntu
    password: "$6$exDY1mhS4KUYCE/2$zmn9ToZwTKLhCw.b4/b.ZRTIZM30JZ4QrOQ2aOXJ8yk96xpcCof0kxKwuX1kqLG/ygbJ1f8wxED22bTL4F46P0"
```

The on-media `autoinstall.yaml` form may drop the `#cloud-config` line and the
`autoinstall:` wrapper (but then **no other top-level keys** may be present).

## Complete air-gapped server install

Local apt mirror + proxy + `geoip: false` + static netplan network + LVM-on-LUKS +
ssh key auth + a `late-commands` tweak + first-boot `user-data`.

```yaml
#cloud-config
autoinstall:
  version: 1

  refresh-installer:
    update: false                      # no snap-store self-update

  proxy: http://proxy.internal:3128

  apt:
    geoip: false                       # no geoip.ubuntu.com lookup
    preserve_sources_list: false
    mirror-selection:
      primary:
        - uri: "http://mirror.internal/ubuntu"
          arches: [amd64]
    fallback: abort                    # don't silently fall back to ISO-offline
    disable_components: [multiverse]

  network:                             # netplan v2 — see the ubuntu-netplan skill
    version: 2
    ethernets:
      enp1s0:
        dhcp4: false
        addresses: [10.0.10.20/24]
        routes:
          - to: default
            via: 10.0.10.1
        nameservers:
          addresses: [10.0.10.2]
          search: [corp.internal]

  storage:
    layout:
      name: lvm
      password: SuperSecretLUKSPassphrase
      sizing-policy: all

  identity:
    realname: "Deploy"
    hostname: app-01
    username: deploy
    password: "$6$exDY1mhS4KUYCE/2$zmn9ToZwTKLhCw.b4/b.ZRTIZM30JZ4QrOQ2aOXJ8yk96xpcCof0kxKwuX1kqLG/ygbJ1f8wxED22bTL4F46P0"

  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
      - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...replace... deploy@bastion

  packages:
    - vim
    - htop
  updates: security

  late-commands:
    # runs in the installer env; target is mounted at /target
    - curtin in-target -- systemctl disable systemd-networkd-wait-online.service
    - echo "deployed $(date)" > /target/etc/deploy-stamp

  user-data:                           # cloud-config for the INSTALLED system (first boot)
    # see the ubuntu-cloud-init skill
    ca_certs:
      trusted:
        - |
          -----BEGIN CERTIFICATE-----
          <CORP-ROOT-CA>
          -----END CERTIFICATE-----
    ntp:
      enabled: true
      servers: [ntp.corp.internal]
      pools: []
```

## Matching `meta-data` (for a NoCloud HTTP or volume seed)

```yaml
instance-id: app-01-install-001
```

## Serving it for an unattended boot

```bash
mkdir seed && cd seed
cp autoinstall.yaml user-data          # the file above
printf 'instance-id: app-01-install-001\n' > meta-data
touch network-config                   # empty: avoids cloud-init >=24.3 seed retry
python3 -m http.server 8000
# then boot the installer with:
#   autoinstall ds=nocloud-net;s=http://<this-host>:8000/
# (quote the whole append line; ';' is a shell/GRUB metachar)
```
