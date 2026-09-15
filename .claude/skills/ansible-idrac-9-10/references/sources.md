# Sources

Freshened: 2026-09-15 — every row probed. The collection is at **v10.0.3** (2026-06-23, Galaxy `highest_version` agrees) and the local clone still sits at v10.0.2; the module-behaviour claims are unchanged. Every cited issue and PR state was re-checked by `gh` (note #1054, the misleading-TLS-error report, has since closed as COMPLETED upstream).

**Exceptions — 2 rows, browser- or portal-only:** the iDRAC 10 Attribute Registry PDF (Dell support-portal search, no stable URL) and the internal Dell whitepaper (no URL). Dell manuals URLs need their `?guid=...` query parameter to resolve — a bare URL 404s because of SPA routing, which is not link rot. — ansible-idrac-9-10

Dated index of authoritative URLs and local artifacts. `freshen` mode
reads this file, probes each row, and stamps `Last verified` (and
`Pinned` where applicable).

## Convention

Each row has `Source`, `URL`, `What it contains`, `Last verified`
(YYYY-MM-DD), `Pinned` (optional). Rows marked
`<!-- ignore-freshen -->` are intentionally not refreshed.

## Most recent freshen pass: 2026-09-15

Skill authored 2026-05-17 against a fresh local clone of
`dell/dellemc-openmanage-ansible-modules` at commit `50215ac9`
(`Merge pull request #1098 from dell/dependabot/pip/pytest-9.0.3`),
collection version `10.0.2`. All sources verified at authoring time.

## Local clones and artifacts (primary sources of truth)

| Source | Path | What it contains | Last verified | Pinned |
|--------|------|------------------|---------------|--------|
| dell/dellemc-openmanage-ansible-modules | `~/projects/github.com/dell/dellemc-openmanage-ansible-modules` (typical local clone) | Full collection source — modules, module_utils, roles, docs, CHANGELOG. Cited paths in `references/*.md` are relative to repo root; access via local clone or `gh api repos/dell/dellemc-openmanage-ansible-modules/contents/<path>`. | 2026-09-15 | collections @ 50215ac9 (v10.0.2) |
| iDRAC 10 Attribute Registry PDF (1.30.xx) | Dell support portal (search "iDRAC10 Attribute Registry 1.30") | Official Dell registry, March 2026 / Rev A01. Source of truth for Chapter 2 (Deprecated), Chapter 3 (Reorganized), Chapter 4 (Changed). | 2026-09-15 | March 2026 / Rev A01 |
| Dell whitepaper "iDRAC Redfish BasicAuth change" | Internal — referenced from Dell KB 000437501 in the Official Documentation section below | Whitepaper covering BasicAuthState change + idrac_session pattern. Source of canonical session example in `auth-and-session.md`. | 2026-09-15 | — |

## Official Dell documentation

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| Dell KB 000437501 — iDRAC HTTP basic authentication changes | https://www.dell.com/support/kbdoc/en-us/000437501/idrac-http-basic-authentication-changes | The canonical reference on the `Enabled`/`Unadvertised`/`Disabled` tri-state, version cutovers (iDRAC 9 ≥ 7.30.10.50, iDRAC 10 ≥ 1.30.10.50). 14G systems cut over at 7.00.00.184. | 2026-09-15 | KB last modified 2026-07-17 |
| Dell KB 000305325 — iDRAC10 releases and release notes | https://www.dell.com/support/kbdoc/en-us/000305325/idrac10-versions-and-release-notes | Master tracking page for iDRAC 10 firmware versions. **The ceiling has moved past the `1.30.10.50` this row used to name** — read the page for the current figure rather than quoting one from here. Dell serves `curl` a block page, so this row is browser-verified only. | 2026-09-15 | — |
| Dell KB 000356005 — 17G recommended BIOS + iDRAC10 | https://www.dell.com/support/kbdoc/en-us/000356005/poweredge-recommended-bios-and-idrac10-upgrades-for-17th-gen | Per-platform recommended firmware versions for 17G servers. | 2026-09-15 | — |
| Dell KB 000348267 — iDRAC 10 platform support list | https://www.dell.com/support/kbdoc/en-us/000348267/poweredge-support-for-integrated-dell-remote-access-controller-10-idrac10 | Definitive list of which PowerEdge platforms ship with iDRAC 10. | 2026-09-15 | — |
| Dell KB 000132986 — Dell catalog endpoints | https://www.dell.com/support/kbdoc/en-us/000132986/dell-emc-catalog-links-for-poweredge-servers | downloads.dell.com catalog URIs for Dell Repository Manager / OpenManage Enterprise / idrac_firmware updates. Unchanged on 17G. | 2026-09-15 | — |
| Dell KB 000137343 — Identifying server generation | https://www.dell.com/support/kbdoc/en-us/000137343/how-to-identify-which-generation-your-dell-poweredge-server-belongs-to | How to determine generation from model number, dmidecode, racadm, OS files. | 2026-09-15 | — |
| Dell KB 000240160 — OSM → iDRAC 10 conversion | https://www.dell.com/support/kbdoc/en-us/000240160/conversion-from-open-server-manager-to-idrac10 | R670/R770 conversion path; explains the intermediate `bmc` manager-ID anomaly. | 2026-09-15 | — |
| iDRAC 10 Attribute Registry (HTML) | https://www.dell.com/support/manuals/en-us/poweredge-r770/idrac10_ar_guide_1.10.05.00/idrac-attributes | Web-rendered version of the registry (1.10.05.00). PDF version 1.30.xx is the local-clone source. | 2026-09-15 | 1.10.05.00 |
| Dell community — "iDRAC DCIM roadmap" (WS-MAN removal) | https://www.dell.com/community/en/conversations/systems-management-general/idrac-dcim-roadmap/647fa2b6f4ccf8a8de852b92 | Dell employee (ajay_shenoy, 2023-02-28): "WSMAN will be 'removed' in iDRAC10/17th Generation. You will not be able to use WSMAN and WMI." — plus "DCIM view classes will not be supported… use the Redfish equivalent properties in the OEM sections." Corroborates the Attribute-Registry-sourced WS-MAN claim in `troubleshooting.md` #13 with a second, on-the-record Dell source. Caveat: a forward-looking roadmap post, not a shipped-product statement; treat as strong-but-not-definitive. | 2026-09-15 | — |
| iDRAC 10 Security Configuration Guide — Redfish session login | https://www.dell.com/support/manuals/en-us/poweredge-r6715/idrac10_1.xx_scg/redfish-session-login-authentication | Dell's official documentation of the Redfish session-token flow. | 2026-09-15 | 1.xx |

## Ansible documentation

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| `dellemc.openmanage.idrac_session` | https://docs.ansible.com/ansible/latest/collections/dellemc/openmanage/idrac_session_module.html | Module reference — params, return values, examples. `version_added: 9.2.0`. | 2026-09-15 | latest |
| `dellemc.openmanage.idrac_attributes` | https://docs.ansible.com/projects/ansible/latest/collections/dellemc/openmanage/idrac_attributes_module.html | Module reference — `x_auth_token` `added_in: 9.3.0`, env fallback `IDRAC_X_AUTH_TOKEN`. | 2026-09-15 | latest |
| `dellemc.openmanage` collection (Galaxy) | https://galaxy.ansible.com/dellemc/openmanage | Galaxy listing — version, install command. Galaxy v3 API `highest_version` = 10.0.3. | 2026-09-15 | 10.0.3 |
| `ansible.builtin.uri` | https://docs.ansible.com/ansible/latest/collections/ansible/builtin/uri_module.html | Stock URI module — `force_basic_auth` parameter for the iDRAC 10 BasicAuth-Unadvertised fallback. | 2026-09-15 | latest |

## GitHub repo

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| dell/dellemc-openmanage-ansible-modules | https://github.com/dell/dellemc-openmanage-ansible-modules | Source repo for the collection. | 2026-09-15 | collections @ 50215ac9 |
| CHANGELOG.rst (collections branch) | https://github.com/dell/dellemc-openmanage-ansible-modules/blob/collections/CHANGELOG.rst | The authoritative version-by-version log of iDRAC 10 enablement (v9.2.0 idrac_session, v9.3.0 x_auth_token, v9.8–v10.0.0 per-module enablement, v10.0.1+ known issues). | 2026-09-15 | v10.0.2 |
| Releases | https://github.com/dell/dellemc-openmanage-ansible-modules/releases | Per-tag release notes. Latest tag v10.0.3 published 2026-06-23 (maintenance only: galaxy.yml build excludes, pytest bump, README — no module behavior change; minimum-version pins in this skill stay at 10.0.2). | 2026-09-15 | v10.0.2 |
| docs/README.md (collections branch) | https://github.com/dell/dellemc-openmanage-ansible-modules/blob/collections/docs/README.md | Per-module iDRAC 9 / iDRAC 10 support matrix. | 2026-09-15 | v10.0.2 |
| Open issue #1103 — `redfish_powerstate` `oem_reset_type` on iDRAC 10 | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1103 | Module gates the virtual AC power-cycle on an iDRAC 9 firmware string (`7.00.60`), so every iDRAC 10 (`1.xx`) box is *skipped*, not failed. Source of `troubleshooting.md` #17. Filed 2026-06-09, no maintainer response. | 2026-09-15 | — |
| Open issue #1102 — OIDC workload identity | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1102 | Feature request for OIDC/workload-identity auth (zero-trust / sovereign cloud). Out of scope for this skill today — logged so a future freshen notices if it ships. | 2026-09-15 | — |
| Open issue #1007 — easy way to get iDRAC generation | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1007 | Open feature request — the reason `troubleshooting.md` #11 has a workaround section. | 2026-09-15 | — |
| Issue #1054 — `idrac_user` writes fail on iDRAC 10 with misleading TLS error | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1054 | Source of `troubleshooting.md` #1. | 2026-09-15 | — |
| Issue #1038 — `idrac_network` fails on 17G (iDRAC 10) | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1038 | Co-cited with #1054 in `troubleshooting.md` #1 and SKILL.md ("things that break") for the `idrac_network` → `idrac_network_attributes` rename. CLOSED. | 2026-09-15 | — |
| Issue #1053 — `idrac_system_info` SystemBoardInletTemp→InletTemp rename | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1053 | Source of `troubleshooting.md` #2. | 2026-09-15 | — |
| Issue #947 — `idrac_user` privilege regression on iDRAC 10 | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/947 | Source of `troubleshooting.md` #3. | 2026-09-15 | — |
| Issue #959 — SCP not qualified for iDRAC 10 | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/959 | Source of `troubleshooting.md` #5. | 2026-09-15 | — |
| Issue #1058 — `idrac_os_deployment` rejects `/` in iso_image | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1058 | Source of `troubleshooting.md` #6. | 2026-09-15 | — |
| Issue #1008 — collection 10.0.0 dropped iDRAC 8 | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1008 | Source of `troubleshooting.md` #7. | 2026-09-15 | — |
| Issue #1046 — ansible-core 2.18+ TypeError on `_configure_auth` | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1046 | Source of `troubleshooting.md` #10. | 2026-09-15 | — |
| Issue #1101 — `idrac_system_info` missing VirtualDisk on iDRAC 10 | https://github.com/dell/dellemc-openmanage-ansible-modules/issues/1101 | Source of `troubleshooting.md` #8. | 2026-09-15 | — |
| PR #865 — `[Module][idrac_session] - 17G support` | https://github.com/dell/dellemc-openmanage-ansible-modules/pull/865 | Token-auth foundation for iDRAC 10. | 2026-09-15 | merged 2025-05-13 |
| PR #1069 — `idrac_user` / `custom_privilege` fix | https://github.com/dell/dellemc-openmanage-ansible-modules/pull/1069 | Fix for `custom_privilege:` bitmap collapse (`troubleshooting.md` #4). MERGED 2025-12-19, shipped in collection 10.0.2 (published 2026-04-01). | 2026-09-15 | merged 2025-12-19 |
| PR #1061 — sensor URI rename fix | https://github.com/dell/dellemc-openmanage-ansible-modules/pull/1061 | Iterate SensorCollection, only fetch listed sensors. | 2026-09-15 | merged 2025-11-12 |
| PR #1034 — defensive sensor check | https://github.com/dell/dellemc-openmanage-ansible-modules/pull/1034 | Companion to #1061. | 2026-09-15 | merged 2025-09-23 |
