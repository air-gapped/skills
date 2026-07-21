# Sources — ubuntu-cloud-init

Authoritative references behind this skill's factual claims, with verification dates.
Re-probe with `skill-improver freshen ubuntu-cloud-init`. Claims verified against the
**canonical/cloud-init** source repo (authoritative implementation) + GitHub releases.

| Ref | URL / location | Pinned | Last verified | Verified claim |
|---|---|---|---|---|
| cloud-init repo | https://github.com/canonical/cloud-init | `main` | 2026-07-21 | Live (**pushed 2026-07-17**), not archived, default branch `main`. |
| Latest release | https://github.com/canonical/cloud-init/releases | `26.1` | 2026-07-21 | **Still `26.1`** (2026-02-28) — ~5 months, no new release despite active `main`. "26.04 LTS ≈ 26.1" holds. |
| netplan render target | `cloudinit/net/netplan.py` **L23** | `main` | 2026-07-21 | Re-read: `CLOUDINIT_NETPLAN_FILE = "/etc/netplan/50-cloud-init.yaml"`. Unchanged. |
| NoCloud `network-config` | `cloudinit/sources/DataSourceNoCloud.py` **L102** | `main` | 2026-07-21 | Re-read: `"optional": ["vendor-data", "network-config"]`. Unchanged. |
| Service rename (24.3) | `doc/rtd/reference/breaking_changes.rst` | `main` | 2026-07-21 | `cloud-init.service` → `cloud-init-network.service`. |
| `datasource_list` None (24.1) | `doc/rtd/reference/breaking_changes.rst` | `main` | 2026-07-21 | ds-identify no longer auto-appends `None` to a single-entry list. |
| ntp → ntpsec (26.1) | `ChangeLog` #6684 | `26.1` | 2026-07-21 | "migrate from ntp client package installed from ntp to ntpsec". |
| deb822 apt sources (23.4) | `cloudinit/config/cc_apt_configure.py` | `main` | 2026-07-21 | deb822 `sources_list` → `/etc/apt/sources.list.d/ubuntu.sources`. |
| cloud-init docs | https://cloudinit.readthedocs.io/en/latest/reference/datasources/nocloud.html | — | 2026-07-21 | Authoritative NoCloud reference; repo `doc/rtd/reference/` is the source. |
| **Breaking changes (full sweep)** | `doc/rtd/reference/breaking_changes.rst` | `main` | 2026-07-21 | **Read end-to-end this pass, not just the two entries previously cited.** The doc carries entries for 26.1, 25.3, **25.1.4**, 25.1, 24.4, 24.3, 24.1, 23.4, 23.2. Five were undocumented here; now summarised in SKILL.md § Upstream breaking changes. The doc's own caveat is worth repeating: *"These changes may not be present in all distributions … many operating system vendors patch out breaking changes"* — so confirm against the actual image. |
| **25.1.4 strict datasource identity** | `doc/rtd/reference/breaking_changes.rst` (25.1.4) | `main` | 2026-07-21 | `ds-identify` now requires strict identification via DMI / kernel cmdline / explicit `datasource_list:`; the old late-discovery mode (bring up networking, probe well-known link-local IPs) was removed to stop a local bad actor answering provisioning requests. Affects **Ec2 / OpenStack / AltCloud on non-x86** without DMI. If nothing is identified, **cloud-init stays disabled and configures nothing at boot**. Mitigations: `--config-drive true`, or pin `datasource_list:`. |

<!-- Grounding note: authored 2026-07-21 against a local checkout of canonical/cloud-init
@ main (26.1, June 2026). network-config v2 == netplan format (see ubuntu-netplan); the
installer path (autoinstall: key in NoCloud user-data) is owned by ubuntu-autoinstall.
Both siblings carry their own sources.md. The `99-disable-network-config.cfg` filename is
a documented convention, not a repo constant — the mechanism is `network: {config: disabled}`. -->


## 2026-07-21 freshen

Same shape as the sibling `ubuntu-autoinstall` pass: **`main` is active
(pushed 2026-07-17) while the latest release is ~5 months old (26.1,
2026-02-28)**. A release-tag check would have reported "nothing to do"; the
source and docs were re-read instead.

**Verified unchanged:** the netplan render target (`netplan.py` L23), the
NoCloud optional-seed list (`DataSourceNoCloud.py` L102), and the 26.1
ntp→ntpsec migration.

**Gap found and closed:** the skill cited only *two* entries from
`breaking_changes.rst` (24.3 service rename, 24.1 `datasource_list` None). The
doc actually carries nine, and **five were undocumented** — 26.1, 25.3, 25.1.4,
25.1, 24.4. The important one is **25.1.4 strict datasource identity**, which is
a security hardening that can leave cloud-init **silently disabled** on non-x86
Ec2/OpenStack/AltCloud images, and which strengthens the rationale for the
`datasource_list:` pin this skill already recommends for air-gapped use.

**Method note:** citing individual entries from a changelog-style doc leaves no
signal when new entries appear above them. Read the whole file and diff the
version headings (`grep -nE '^[0-9]+\.[0-9]+' breaking_changes.rst`) rather than
re-checking the two rows already quoted.
