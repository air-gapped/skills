# Sources — ubuntu-netplan

Authoritative references behind this skill's factual claims, with verification dates.
Re-probe with `skill-improver freshen ubuntu-netplan`. Claims verified against the
**canonical/netplan** source repo (authoritative implementation) + GitHub releases.

| Ref | URL / location | Pinned | Last verified | Verified claim |
|---|---|---|---|---|
| netplan repo | https://github.com/canonical/netplan | `main` | 2026-07-21 | Live (**pushed 2026-07-20**), not archived, default branch `main`. |
| Latest release | https://github.com/canonical/netplan/releases | `1.2.2` | 2026-07-21 | **`1.2.2` is latest (2026-07-20)**, up from 1.2.1. **Bug fixes only** — SR-IOV udev ordering before the apply service (#569), terminal `BlockingIOError` handling (#572), CI/doc chores. **No new YAML surface, no breaking change.** "26.04 tracks 1.2.x" unchanged. |
| Release tags | https://github.com/canonical/netplan/tags | — | 2026-07-21 | `1.0`, `1.0.1` (2024-07-04, in the 24.04 window → "24.04 ships ~1.0.x"), `1.1` (2024-08-14, *after* 24.04), `1.1.1`, `1.1.2`, `1.2`, `1.2.1` all exist. |
| YAML version | `src/parse.c` **L38-39**, reject at **L3155** | `main` | 2026-07-21 | Re-read: `NETPLAN_VERSION_MIN 2` / `NETPLAN_VERSION_MAX 3`, rejecting `< MIN \|\| >= MAX` → only `network.version: 2` accepted. Unchanged. |
| `ra-overrides` / `advertised-mss` gating | `doc/netplan-yaml.md` **L406, L709, L845** | `main` | 2026-07-21 | Both still marked "since 1.1" → present on 26.04 (1.2.x), NOT on 24.04 (1.0.x). **These are the only three `since 1.1` markers in the file** — see the sweep below. |
| `netplan try` timeout | `netplan_cli/cli/commands/try_command.py` **L36** | `main` | 2026-07-21 | Re-read: `DEFAULT_INPUT_TIMEOUT = 120` (also the `--timeout` default at L75). Unchanged. |
| `hairpin` / `port-mac-learning` | `doc/netplan-yaml.md` | `main` | 2026-07-21 | Bridge-port props "since 1.0" → available on both 24.04 and 26.04. |
| netplan docs | https://netplan.readthedocs.io/en/stable/netplan-yaml/ | — | 2026-07-21 | Authoritative YAML reference; repo `doc/netplan-yaml.md` (~2200 lines) is the source. |

<!-- Grounding note: authored 2026-07-21 against a local checkout of canonical/netplan
@ main (June 2026, post-1.2.1). netplan v2 is the shared substrate: cloud-init
network-config v2 and autoinstall network: blocks are netplan format — see the
ubuntu-cloud-init and ubuntu-autoinstall sibling skills (each has its own sources.md). -->


## 2026-07-21 freshen — full `since`-marker sweep

Applying the lesson from the sibling `ubuntu-cloud-init` pass: **re-checking the
markers already cited says nothing about markers that appeared since.** So this
pass swept every version marker in `doc/netplan-yaml.md` (2199 lines) rather
than only the two features previously quoted:

```bash
gh api repos/canonical/netplan/contents/doc/netplan-yaml.md \
  --header "Accept: application/vnd.github.raw" \
  | grep -oiE 'since (netplan )?[0-9]+\.[0-9]+(\.[0-9]+)?' \
  | sed 's/netplan //' | sort | uniq -c | sort -k2 -V
```

**Result — the markers top out at `since 1.1`:**

| Marker | Count |
|---|---|
| 0.98 – 0.107 | 100 total across ten 0.x versions |
| **1.1** | **3** — and that is the newest |

No `since 1.2` or later exists anywhere in the file. The three `1.1` entries are
exactly `ra-overrides` (twice — it appears under two sections, L406 and L709)
and `advertised-mss` (L845), which is precisely what this skill already
documents. **So the 24.04-vs-26.04 feature gating is complete as written**, and
1.2 / 1.2.1 / 1.2.2 added no YAML surface at all.

**Verified unchanged with line anchors:** the version constants
(`parse.c` L38-39, reject L3155) and the `netplan try` timeout
(`try_command.py` L36).
