# Sources — ubuntu-netplan

Authoritative references behind this skill's factual claims, with verification dates.
Re-probe with `skill-improver freshen ubuntu-netplan`. Claims verified against the
**canonical/netplan** source repo (authoritative implementation) + GitHub releases.

| Ref | URL / location | Pinned | Last verified | Verified claim |
|---|---|---|---|---|
| netplan repo | https://github.com/canonical/netplan | `main` | 2026-06-14 | Live (pushed 2026-06-10), not archived, default branch `main`. |
| Latest release | https://github.com/canonical/netplan/releases | `1.2.1` | 2026-06-14 | `1.2.1` is latest (2026-01-27) → "26.04 tracks 1.2.x". |
| Release tags | https://github.com/canonical/netplan/tags | — | 2026-06-14 | `1.0`, `1.0.1` (2024-07-04, in the 24.04 window → "24.04 ships ~1.0.x"), `1.1` (2024-08-14, *after* 24.04), `1.1.1`, `1.1.2`, `1.2`, `1.2.1` all exist. |
| YAML version | `src/parse.c` | `main` | 2026-06-14 | `NETPLAN_VERSION_MIN=2`, `NETPLAN_VERSION_MAX=3` with `< MIN \|\| >= MAX` reject → only `network.version: 2` accepted. |
| `ra-overrides` / `advertised-mss` gating | `doc/netplan-yaml.md` | `main` | 2026-06-14 | Both marked "since 1.1" → present on 26.04 (1.2.x), NOT on 24.04 (1.0.x). |
| `netplan try` timeout | `netplan_cli/cli/commands/try_command.py` | `main` | 2026-06-14 | `DEFAULT_INPUT_TIMEOUT = 120`. |
| `hairpin` / `port-mac-learning` | `doc/netplan-yaml.md` | `main` | 2026-06-14 | Bridge-port props "since 1.0" → available on both 24.04 and 26.04. |
| netplan docs | https://netplan.readthedocs.io/en/stable/netplan-yaml/ | — | 2026-06-14 | Authoritative YAML reference; repo `doc/netplan-yaml.md` (~2200 lines) is the source. |

<!-- Grounding note: authored 2026-06-14 against a local checkout of canonical/netplan
@ main (June 2026, post-1.2.1). netplan v2 is the shared substrate: cloud-init
network-config v2 and autoinstall network: blocks are netplan format — see the
ubuntu-cloud-init and ubuntu-autoinstall sibling skills (each has its own sources.md). -->
