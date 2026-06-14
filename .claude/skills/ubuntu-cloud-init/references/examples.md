# cloud-init examples (air-gapped first boot)

## Minimal `#cloud-config`

```yaml
#cloud-config
hostname: server01
```

## Realistic air-gapped first-boot config

`/var/lib/cloud/seed/nocloud/user-data`:

```yaml
#cloud-config
hostname: app01
fqdn: app01.corp.internal
ssh_pwauth: false

users:
  - default
  - name: deploy
    groups: [sudo]
    sudo: "ALL=(ALL) NOPASSWD:ALL"
    lock_passwd: true
    ssh_authorized_keys:
      - ssh-ed25519 AAAAC3Nza... deploy@corp

ca_certs:
  trusted:
    - |
      -----BEGIN CERTIFICATE-----
      <CORP-ROOT-CA>
      -----END CERTIFICATE-----

apt:
  preserve_sources_list: false
  primary:
    - arches: [default]
      uri: http://mirror.corp.internal/ubuntu
  security:
    - arches: [default]
      uri: http://mirror.corp.internal/ubuntu
  conf: |
    Acquire::http::Proxy "http://apt-cache.corp.internal:3142";

package_update: true
package_upgrade: false
packages:
  - nginx
  - chrony

ntp:
  enabled: true
  ntp_client: chrony
  servers: [ntp.corp.internal]
  pools: []

write_files:
  - path: /etc/myapp/app.conf
    owner: root:root
    permissions: '0640'
    content: |
      backend = db.corp.internal:5432

runcmd:
  - [systemctl, enable, --now, nginx]
```

`/var/lib/cloud/seed/nocloud/meta-data`:

```yaml
instance-id: app01-2026-06-14-01      # bump to force a re-run
local-hostname: app01
```

`/var/lib/cloud/seed/nocloud/network-config` (empty file, or netplan v2 — present to
avoid the 24.3 HTTP-seed retry/timeout). A real one, in netplan v2 (see the
**ubuntu-netplan** skill):

```yaml
version: 2
ethernets:
  enp1s0:
    addresses: [10.0.10.20/24]
    routes: [{to: default, via: 10.0.10.1}]
    nameservers:
      addresses: [10.0.10.2]
      search: [corp.internal]
```

Build the seed ISO:

```bash
genisoimage -output seed.iso -volid cidata -joliet -rock \
  user-data meta-data network-config
# attach seed.iso as a second drive; cloud-init finds it by the CIDATA label
```

## MIME multipart (cloud-config + a script)

Build it with the helper (don't hand-assemble the boundaries):

```bash
cloud-init devel make-mime \
  -a config.yaml:cloud-config \
  -a bootstrap.sh:x-shellscript > user-data
```

The produced `user-data` is a standard MIME document — ship it as the NoCloud
`user-data` file unchanged:

```
Content-Type: multipart/mixed; boundary="===============1234567890=="
MIME-Version: 1.0

--===============1234567890==
Content-Type: text/cloud-config; charset="utf-8"

#cloud-config
packages: [nginx]

--===============1234567890==
Content-Type: text/x-shellscript; charset="utf-8"

#!/bin/sh
echo bootstrapped >> /var/log/firstboot.log

--===============1234567890==--
```

Per-frequency script subtypes exist too: `x-shellscript-per-boot`,
`x-shellscript-per-instance`, `x-shellscript-per-once`.

## Jinja-templated user-data

`## template: jinja` MUST be line 1; the real header (`#cloud-config` here) on line 2.
Variables are instance-data keys (`cloud-init query --all` lists them):

```yaml
## template: jinja
#cloud-config
hostname: host-{{ v1.instance_id }}
runcmd:
  - echo "booted on {{ v1.cloud_name }} as {{ v1.instance_id }}" > /etc/provisioned
```

## Pin the datasource (air-gapped) — `/etc/cloud/cloud.cfg.d/99-datasource.cfg`

```yaml
datasource_list: [ NoCloud ]
```

## Site-wide vendor-data (overridden by per-host user-data)

`/var/lib/cloud/seed/nocloud/vendor-data`:

```yaml
#cloud-config
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
apt:
  preserve_sources_list: false
  primary:
    - arches: [default]
      uri: http://mirror.corp.internal/ubuntu
```
