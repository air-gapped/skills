# Sources — ubuntu-autoinstall

Authoritative references behind this skill's factual claims, with verification dates.
Re-probe with `skill-improver freshen ubuntu-autoinstall`. All claims here were
verified against the **canonical/subiquity** source repo (the authoritative
implementation) and the GitHub release/tag list.

| Ref | URL / location | Pinned | Last verified | Verified claim |
|---|---|---|---|---|
| subiquity repo | https://github.com/canonical/subiquity | `main` | 2026-06-14 | Live (pushed 2026-06-12), not archived, default branch `main`. |
| Latest release | https://github.com/canonical/subiquity/releases | `26.04` | 2026-06-14 | `26.04` is the latest release (published 2026-04-23) → 26.04 LTS shipped; confirms the 24.04 + 26.04 LTS targeting. |
| Release tags | https://github.com/canonical/subiquity/tags | — | 2026-06-14 | Tags `24.04.1`–`24.04.4.1`, `24.10.1`, `25.04`, `25.10`, `26.04`, `26.10-devel` all exist. |
| autoinstall schema | `autoinstall-schema.json` (repo root) | `main` | 2026-06-14 | Present; regenerated via `make schema`. Schema `version` is `1`. |
| Validator script | `scripts/validate-autoinstall-user-data.py` | `main` | 2026-06-14 | Present in the repo's `scripts/` (NOT bundled in this skill) — basis for the Dim 8 provenance note. |
| `kernel-crash-dumps` / `zdevs` gating | `autoinstall-schema.json` @ `24.04.1` vs `main` | — | 2026-06-14 | Top-level keys `kernel-crash-dumps` and `zdevs` present in `main`, **absent in `24.04.1`** → "24.10+ only". |
| 24.04 → 26.04 top-level delta | schema diff `24.04.1` vs `26.04`/`main` | — | 2026-06-14 | Exactly two keys added (`kernel-crash-dumps`, `zdevs`); none removed. `26.04` top-level keys **identical to `main`**. |
| `apt.fallback` enum | `autoinstall-schema.json` | `main` | 2026-06-14 | Enum = `abort`, `continue-anyway`, `offline-install`. |
| `kernel.flavor` resolution | `subiquity/server/kernel.py`, `controllers/kernel.py` | `main` | 2026-06-14 | `generic`→`linux-generic`; `hwe`→`linux-generic-hwe-<release>`; else `linux-<flavor>-<release>` (`<release>` from `lsb_release`); empty `kernel:`→`flavor: generic`. No pre-check that the package exists. |
| `ubuntu-advantage` alias | `subiquity/server/controllers/ubuntu_pro.py` | `main` | 2026-06-14 | `autoinstall_key_alias = "ubuntu-advantage"` → alias of `ubuntu-pro`; both keys in schema. |
| On-media "only autoinstall" rule | `subiquity/server/server.py` | `main` | 2026-06-14 | Fatal: "No other keys may be present alongside 'autoinstall'." |
| Autoinstall docs | https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html | — | 2026-06-14 | Reference docs live in the repo `doc/` tree (`autoinstall-reference.rst`, `autoinstall-schema.rst`, `cloudinit-autoinstall-interaction.rst`). |

<!-- Grounding note: this skill was authored 2026-06-14 against a local checkout of
canonical/subiquity @ main (HEAD ~fb7a09c8, June 2026). The two delegation boundaries
(network: → netplan v2, user-data: → cloud-init) are cross-checked in the sibling
skills ubuntu-netplan and ubuntu-cloud-init, which carry their own sources.md. -->
