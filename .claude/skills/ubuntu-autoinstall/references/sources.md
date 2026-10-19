# Sources

Freshened: 2026-10-20 — every row probed. Schema top-level keys and every subschema diffed at `main`, `26.10`, `26.04.1`, `26.04`, `24.04.5`, `24.04.1`; code anchors re-read on `main`.

Authoritative references behind this skill's factual claims, with verification dates.
Re-probe with `skill-improver freshen ubuntu-autoinstall`. All claims here were
verified against the **canonical/subiquity** source repo (the authoritative
implementation) and the GitHub release/tag list.

| Ref | URL / location | Pinned | Last verified | Verified claim |
|---|---|---|---|---|
| subiquity repo | https://github.com/canonical/subiquity | `main` | 2026-10-20 | Live (pushed 2026-10-19), not archived, default branch `main`. |
| Latest release | https://github.com/canonical/subiquity/releases | `26.10` | 2026-10-20 | `isLatest`: **`26.10`** (2026-10-15, interim). LTS lines: `26.04.1` (2026-08-28), `24.04.5` (2026-09-10, bug fixes only). 26.10 adds `accepted-errors` and the `/boot` rule (rows below) and an experimental `hybrid` `mode: use_gap` gated behind a server flag (not documented: needs a modified installer snap). 24.04 + 26.04 LTS targeting unchanged. |
| Release tags | https://github.com/canonical/subiquity/tags | — | 2026-10-20 | Tags `24.04.1`–`24.04.5`, `24.08.1`, `24.10.1`, `25.04`, `25.10`, `26.04`, `26.04.1`, `26.10-devel`, `26.10-beta`, `26.10` exist. |
| autoinstall schema | `autoinstall-schema.json` (repo root) | `main` | 2026-10-20 | `version` constrained to exactly 1 (`{type: integer, minimum: 1, maximum: 1}`); top-level `additionalProperties: true`. 32 top-level keys at `main`, `26.10`, `26.04.1`, `26.04`, all documented in `schema.md`. Every property subschema identical between `26.04` and `main`, and between `24.04.1` and `24.04.5`. |
| Validator script | `scripts/validate-autoinstall-user-data.py` | `main` | 2026-10-20 | Present (302 lines), not bundled in this skill; `--no-expect-cloudconfig` at L223. |
| `kernel-crash-dumps` / `zdevs` gating | `autoinstall-schema.json` @ `24.04.1`, `24.04.5` vs `main`; `autoinstall-reference.rst` L1295-1297 | — | 2026-10-20 | Both keys absent at `24.04.1` and `24.04.5` (30 keys), present from 24.10 on. Doc: 24.10+ default = dynamic enablement via `kdump-tools`; pre-24.10 default = disabled. |
| 24.04 → 26.04 top-level delta | schema diff `24.04.1` vs `26.04`/`26.04.1`/`26.10`/`main` | — | 2026-10-20 | Exactly two keys added (`kernel-crash-dumps`, `zdevs`); none removed. `26.04`, `26.04.1`, `26.10` top-level keys identical to `main`. |
| `apt.fallback` enum | `autoinstall-schema.json` | `main` | 2026-10-20 | `['abort', 'continue-anyway', 'offline-install']`. |
| 26.10 `/boot` requirement | https://github.com/canonical/subiquity/releases/tag/26.10 §"New /boot storage requirements in preparation for signed GRUB" | `26.10` | 2026-10-20 | For 26.10+ installs on signed-GRUB platforms: `/boot` must be `ext4` on a disk, partition or RAID 1, not on LVM, LUKS/dm-crypt, ZFS or non-RAID-1. Guided ZFS now puts `/boot` on a dedicated ext4 partition instead of a bpool. |
| `storage.layout.accepted-errors` | https://github.com/canonical/subiquity/releases/tag/26.10 ; `doc/reference/autoinstall-reference.rst` L628-665; commit `c2d9effb` (2026-07-02) | `26.10` | 2026-10-20 | New in 26.10 for `hybrid` + `encrypted: yes`; list or single string; only errors snapd offers a `proceed` action for are honoured. `subiquity/server/controllers/storage.py` has 16 `accepted-errors` hits at `26.10`/`main`, 0 at `26.04`, `26.04.1`, `24.04.5`. Storage is an open object, so the JSON schema does not change. |
| `identity.groups` | `autoinstall-schema.json` `identity.properties`; `doc/reference/autoinstall-reference.rst` §groups (L892-908) | `26.04`+ | 2026-10-20 | Present at `26.04`, `26.04.1`, `26.10`, `main` (`oneOf`: string list, or `{override, append}`); absent at `24.04.1`, `24.04.5`, `24.08.1`, `24.10.1`, `25.04`, `25.10`. Doc: default is a hard-coded list (`sudo`, `admin`); `override` ignores it, `append` adds to it; a bare list is sugar for `override`. |
| `apt.fallback` effective default | `subiquity/models/mirror.py` L318, L351-352 (L272 on `24.04.1` and `24.04.5`) | `main` | 2026-10-20 | `self.fallback = MirrorSelectionFallback.OFFLINE_INSTALL`, overridden only when `fallback` is in the autoinstall data. The reference doc still states two defaults: `abort` in the default-config block (L439) vs `offline-install` in the field doc (L488). |
| `apt.geoip` scope | `doc/reference/autoinstall-reference.rst` §geoip (commit `ccf0196a`, 2026-09-30, LP #2080416); `subiquity/server/geoip.py` L76-106 | `main` | 2026-10-20 | `geoip: false` only disables country-mirror selection; the lookup to `https://geoip.ubuntu.com/lookup` is subscribed to `NETWORK_UP` / `NETWORK_PROXY_SET` and runs regardless (also feeds timezone detection). `session.get(url)` passes no proxy (L78-84 comment). 10 s expiry applies when `geoip: true` and a `country-mirror` candidate is present. |
| `kernel.flavor` resolution | `subiquity/server/kernel.py` `flavor_to_pkgname()` (L19-29, file 29 lines) | `main` | 2026-10-20 | `generic`→`linux-generic` (L21); `hwe`→ rewritten to `generic-hwe` (L23) → `linux-generic-hwe-<release>`; else `f"linux-{flavor}-{release}"` (L29). No pre-check that the package exists. |
| `ubuntu-advantage` alias | `subiquity/server/controllers/ubuntu_pro.py` L75-76 | `main` | 2026-10-20 | `autoinstall_key = "ubuntu-pro"` / `autoinstall_key_alias = "ubuntu-advantage"`; both keys in the schema. |
| On-media "only autoinstall" rule | `subiquity/server/server.py` L741 (file 1100 lines) | `main` | 2026-10-20 | Fatal string verbatim: "No other keys may be present alongside 'autoinstall' at …". |
| Delivery precedence | `subiquity/server/server.py` L81-83 (paths), L941-958 (`select_autoinstall`) | `main` | 2026-10-20 | Comment block lists the five sources in the skill's order; `--autoinstall ""` returns `None` (disabled); paths `cdrom/autoinstall.yaml`, `autoinstall.yaml`, `run/subiquity/cloud.autoinstall.yaml`; kernel key `subiquity.autoinstallpath`. |
| Ordered match-spec lists | `doc/reference/autoinstall-reference.rst` L818 | `main` | 2026-10-20 | "As of Subiquity 24.08.1, match specs may optionally be specified in an ordered list". |
| NoCloud `network-config` retry | https://github.com/canonical/cloud-init/blob/main/doc/rtd/reference/breaking_changes.rst (24.3 §"Addition of NoCloud network-config") | `main` | 2026-10-20 | Missing `network-config` → retry/timeout in boot; an empty file restores prior behaviour. |
| Autoinstall docs | https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html | — | 2026-10-20 | HTTP 200. Repo `doc/` files cited by the references all exist on `main`: `reference/autoinstall-reference.rst`, `reference/autoinstall-schema.rst`, `explanation/cloudinit-autoinstall-interaction.rst`, `explanation/zero-touch-autoinstall.rst`, `tutorial/providing-autoinstall.rst`, `howto/autoinstall-quickstart.rst`, `howto/autoinstall-validation.rst`. |

<!-- Grounding note: this skill was authored 2026-07-21 against a local checkout of
canonical/subiquity @ main (HEAD ~fb7a09c8, June 2026). The two delegation boundaries
(network: → netplan v2, user-data: → cloud-init) are cross-checked in the sibling
skills ubuntu-netplan and ubuntu-cloud-init, which carry their own sources.md. -->


## 2026-07-21 freshen — verified unchanged, checked mechanically

`main` is actively developed (**pushed 2026-07-20**) yet **`26.04` remains the
latest release** (2026-04-23) — three months of commits without a cut. That
combination is the thing to watch: the schema this skill documents tracks
`main`, so it can move without a release to signal it. This pass therefore
diffed the artifact rather than trusting the release tag.

**Method, so a future pass can repeat it cheaply:**

```bash
gh api repos/canonical/subiquity/contents/autoinstall-schema.json \
  --header "Accept: application/vnd.github.raw" > /tmp/ai.json
python3 -c "import json;d=json.load(open('/tmp/ai.json'));print(len(d['properties']),sorted(d['properties']))"
```

then diff that key set against the backticked identifiers in `schema.md`.

**Result: nothing moved.**

- Schema `version` still pinned to exactly 1 (`minimum: 1, maximum: 1`).
- **32 top-level keys, and all 32 already appear in `schema.md`** — programmatic
  diff, zero undocumented keys. The `kernel-crash-dumps` / `zdevs` "24.10+ only"
  gating still holds.
- `apt.fallback` enum unchanged: `abort`, `continue-anyway`, `offline-install`.
- All three code-behaviour claims re-read at source and unchanged, now with line
  anchors: `flavor_to_pkgname()` (kernel.py L19-29), the on-media fatal string
  (server.py **L741**), and the `ubuntu-pro` / `ubuntu-advantage` alias pair
  (ubuntu_pro.py **L75-76**).
