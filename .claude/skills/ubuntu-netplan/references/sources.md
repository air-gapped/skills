# Sources

Freshened: 2026-10-20

Authoritative references behind this skill's factual claims. Re-probe with
`skill-improver freshen ubuntu-netplan`. Claims verified against the
**canonical/netplan** source repo (authoritative implementation), its GitHub
releases, and the Ubuntu archive (Launchpad).

| Ref | URL / location | Pinned | Verified claim |
|---|---|---|---|
| netplan repo | https://github.com/canonical/netplan | `main` | Live (pushed 2026-10-15), not archived, default branch `main`. Bugs are tracked on Launchpad, not GitHub issues. |
| Latest release | https://github.com/canonical/netplan/releases | `1.2.2` | **`1.2.2` is latest (2026-07-20)**, bug fixes only — no new YAML surface, no breaking change. Unfiltered release list: 1.2.2, 1.2.1, 1.2, 1.1.2, 1.1.1, 1.1, 1.0.1, 1.0, 0.107.1 … 0.99. |
| Release tags | https://github.com/canonical/netplan/tags | — | `1.0` (2024-02-29), `1.0.1` (2024-07-04), `1.1` (2024-08-14), `1.1.1` (2024-10-15), `1.1.2` (2025-01-21), `1.2` (2025-12-16), `1.2.1` (2026-01-27), `1.2.2` (2026-07-20). No tag above 1.2.2. |
| Ubuntu `netplan.io` packages | https://api.launchpad.net/1.0/ubuntu/+archive/primary?ws.op=getPublishedSources&source_name=netplan.io&exact_match=true | — | noble Release `1.0-2ubuntu1` (Security `1.0-2ubuntu1.2`); **noble-updates `1.1.2-8ubuntu1~24.04.3`** (2026-09-15; 1.1.x SRU'd since `1.1.1-1~ubuntu24.04.1`, 2025-01-08). resolute Release `1.2-1ubuntu5`, Updates `1.2-1ubuntu5.1`. → updated 24.04 has `ra-overrides`/`advertised-mss`; 26.04 is 1.2, not 1.2.2. |
| umask 0077 generate bug | https://bugs.launchpad.net/ubuntu/+source/netplan.io/+bug/2164636 ; fix https://github.com/canonical/netplan/pull/614 | — | Under `umask 0077`, `/run/systemd/network/10-netplan-*` are written `0600` instead of `0640`; networkd "Permission denied". Fix merged to `main` 2026-09-18 (after 1.2.2); LP tasks: netplan Fix Committed, netplan.io (Ubuntu) Triaged — not in any release or Ubuntu package yet. |
| YAML version | `src/parse.c` **L38-39**, reject at **L3191** (4048 lines) | `main` | `NETPLAN_VERSION_MIN 2` / `NETPLAN_VERSION_MAX 3`, rejecting `< MIN \|\| >= MAX` → only `network.version: 2` accepted. |
| `ra-overrides` / `advertised-mss` gating | `doc/netplan-yaml.md` **L418, L721, L857** (2211 lines) | `main` | The only three "since 1.1" markers. Full marker sweep (bold-tolerant one-liner below): newest is 1.1; `since 1.0` ×2 (`hairpin` L614, `port-mac-learning` L621); no 1.2+ marker. |
| `netplan try` timeout | `netplan_cli/cli/commands/try_command.py` **L36** | `main` | `DEFAULT_INPUT_TIMEOUT = 120` (also the `--timeout` default at L75). |
| `hairpin` / `port-mac-learning` | `doc/netplan-yaml.md` L614, L621 | `main` | Bridge-port props "since **1.0**" → available on both 24.04 and 26.04; `port-mac-learning` networkd-only. |
| CLI flags | `netplan_cli/cli/commands/{status,try_command,apply,info,migrate,sriov_rebind,ip}.py` | local clone `1.2.1-12-g12ff34c` | `status --all/--diff/--diff-only/--format`; `try --config-file/--timeout/--state`, SIGUSR1 accepts; `info --json/--yaml`; `migrate --dry-run`; `rebind`; `ip leases`. Feature flags include `sriov`, `eswitch-mode`, `infiniband`, `openvswitch`, `regdom`, `vrf`, `vxlan`, `virtual-ethernet`. |
| Schema details | `doc/netplan-yaml.md`, `doc/netplan-generate.md`, `doc/generator.md`, `src/parse.c` | local clone `1.2.1-12-g12ff34c` | stp default true; lacp-rate default slow; miimon no-suffix = ms; bridge times = s; `gratuitious-arp` alias; since-markers for activation-mode 0.103, ignore-carrier 0.104, vrf/vxlan/neigh-suppress 0.105, packets-per-member 0.106, dummy/veth 0.107, wireguard/address lifetime+label 0.100; file precedence + sequence concatenation; warn-only on open permissions (parse.c); `set` writes 0600; generator ignores parse errors at boot. |
| netplan docs | https://netplan.readthedocs.io/en/stable/netplan-yaml/ | — | 200; authoritative YAML reference rendered from repo `doc/netplan-yaml.md`. |

Marker sweep (markers are sometimes bolded — `since **1.0**` — so the pattern
tolerates `*`):

```bash
gh api repos/canonical/netplan/contents/doc/netplan-yaml.md \
  --header "Accept: application/vnd.github.raw" \
  | grep -oiE 'since[ *]*(netplan )?[0-9]+\.[0-9]+(\.[0-9]+)?' | tr -d '*' \
  | sed 's/netplan //I' | sort | uniq -c | sort -k3 -V
```

Watched, not applied (2026-10-20):

- `critical` accepting `KeepConfiguration=` scalars (`static`, `dynamic`,
  `dynamic-on-stop`; aliases `dhcp`, `dhcp-on-stop`) — merged to `main` in canonical/netplan#599 (2026-09-17), in
  no release yet.
- LP #2167907 — `dhcp4-overrides`/`dhcp-identifier: mac` reportedly ignored on
  systemd 259 because netplan emits a legacy `[DHCP]` section; fix PR
  canonical/netplan#617 open. Contested: a maintainer could not reproduce on
  resolute (2026-10-07). Not applied until the PR merges or the bug is confirmed.

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
