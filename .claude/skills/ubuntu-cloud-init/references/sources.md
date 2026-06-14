# Sources — ubuntu-cloud-init

Authoritative references behind this skill's factual claims, with verification dates.
Re-probe with `skill-improver freshen ubuntu-cloud-init`. Claims verified against the
**canonical/cloud-init** source repo (authoritative implementation) + GitHub releases.

| Ref | URL / location | Pinned | Last verified | Verified claim |
|---|---|---|---|---|
| cloud-init repo | https://github.com/canonical/cloud-init | `main` | 2026-06-14 | Live (pushed 2026-06-12), not archived, default branch `main`. |
| Latest release | https://github.com/canonical/cloud-init/releases | `26.1` | 2026-06-14 | `26.1` is latest (2026-02-28) → "26.04 LTS ≈ 26.1"; `ChangeLog` top = 26.1. |
| netplan render target | `cloudinit/net/netplan.py` | `main` | 2026-06-14 | `CLOUDINIT_NETPLAN_FILE = "/etc/netplan/50-cloud-init.yaml"`. |
| NoCloud `network-config` | `cloudinit/sources/DataSourceNoCloud.py` | `main` | 2026-06-14 | `"optional": ["vendor-data", "network-config"]` — network-config is an optional seed file. |
| Service rename (24.3) | `doc/rtd/reference/breaking_changes.rst` | `main` | 2026-06-14 | `cloud-init.service` → `cloud-init-network.service`. |
| `datasource_list` None (24.1) | `doc/rtd/reference/breaking_changes.rst` | `main` | 2026-06-14 | ds-identify no longer auto-appends `None` to a single-entry list. |
| ntp → ntpsec (26.1) | `ChangeLog` #6684 | `26.1` | 2026-06-14 | "migrate from ntp client package installed from ntp to ntpsec". |
| deb822 apt sources (23.4) | `cloudinit/config/cc_apt_configure.py` | `main` | 2026-06-14 | deb822 `sources_list` → `/etc/apt/sources.list.d/ubuntu.sources`. |
| cloud-init docs | https://cloudinit.readthedocs.io/en/latest/reference/datasources/nocloud.html | — | 2026-06-14 | Authoritative NoCloud reference; repo `doc/rtd/reference/` is the source. |

<!-- Grounding note: authored 2026-06-14 against a local checkout of canonical/cloud-init
@ main (26.1, June 2026). network-config v2 == netplan format (see ubuntu-netplan); the
installer path (autoinstall: key in NoCloud user-data) is owned by ubuntu-autoinstall.
Both siblings carry their own sources.md. The `99-disable-network-config.cfg` filename is
a documented convention, not a repo constant — the mechanism is `network: {config: disabled}`. -->
