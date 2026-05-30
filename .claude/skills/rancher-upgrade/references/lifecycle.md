# lifecycle.md — community release model, EOL, and version grounding

**Grounded via `gh` + endoflife.date + suse.com/lifecycle: 2026-05-30.** Ceiling at sift:
Rancher community `v2.14.2`. Re-ground at use time (House Rule #8) — releases move.

## Community vs Prime — the only reliable discriminator

Rancher's GitHub releases carry **both** community and Prime builds, so "is there a GitHub
release?" does NOT tell you whether a patch is community-supported. The reliable signal is the
**first line of the GitHub release-notes body**:

| First line | Meaning |
|------------|---------|
| `"This is a Community version release"` | Community cadence — supported for community users. (Currently only the **2.14.x** line.) |
| `"This is a Community and Prime version release"` | Patch on the then-newest minor; serves both. |
| `"This is a Prime version release"` | Prime-cadence patch on an older minor; full notes still on GitHub but **not** community-supported. |
| `"Please refer to our Prime Documentation…"` (stub, no notes) | Prime-only; community gets nothing here. (Currently **2.11.14 / 2.12.10 / 2.13.6**.) |

**Cutover trigger:** when a new minor GAs, the previously-newest minor's *subsequent* patches flip
from Community → Prime labeling. So at any moment, **only the current stable minor is on community
cadence**; older still-supported minors get Prime-cadence patches. An operator upgrading an older
minor air-gapped must verify the specific patch actually ships a community-consumable chart/image
(the `rancher-latest` server-charts repo tracks the current stable minor; older minors live in
`rancher-stable` / per-version) — `UNVERIFIED` in general, check per version.

To classify a patch: `gh api repos/rancher/rancher/releases/tags/<tag> --jq '.body' | head -1`.

## Cadence & lifecycle

- **Minor cadence ≈ every 4 months (Mar / Jul / Nov).** Grounded GA dates: 2.11.0 = 2025-03-31,
  2.12.0 = 2025-07-31, 2.13.0 = 2025-11-25, 2.14.0 = 2026-03-26.
- **Patches are monthly and in lockstep across all active minors** (one batch, same day). There is
  **no separate "Prime patch cadence" offset** — the apparent Apr/Aug/Dec pattern is just the
  `.0`→`.1` stabilization gap (SUSE counts the support clock from the stabilized ~`.1` GA, ~1 month
  after the GitHub `.0`).
- **Support window ≈ 18 months** = ~12 months full support + ~6 months limited (critical-security
  only), for 2.9 onward.

**EOL dates (suse.com/lifecycle + endoflife.date agree, GA+18mo):**

| Minor | Community GA (.0) | EOL |
|-------|-------------------|-----|
| 2.11 | 2025-03-31 | **2026-10-24** |
| 2.12 | 2025-07-31 | **2027-02-28** |
| 2.13 | 2025-11-25 | **2027-06-17** |
| 2.14 | 2026-03-26 | **2027-10-10** |

Latest patch per minor at sift (grounded): 2.11.14, 2.12.10, 2.13.6 (Prime-stub), **2.14.2**
(community). Always re-derive — see Grounding.

## Grounding (House Rule #8) — repo map + anti-confirmation method

`gh` must run with **valid auth** from the operator's workstation. Anonymous = 60 req/hr and
exhausts almost instantly on an enumeration sweep — confirm `gh auth status` shows a logged-in
account and `gh api rate_limit --jq '.resources.core'` shows a 5000 limit BEFORE sweeping. (Run
`gh` centrally, not fanned across many subagents — they share one rate-limit bucket.)

Anti-confirmation: **anchor on `releases/latest`, enumerate-and-derive, never name a candidate
version in the query** (existence/list/per-tag queries get rubber-stamped — plausible fakes return
200).

```bash
# the ceiling (no candidate version in the command)
gh api repos/rancher/rancher/releases/latest --jq '.tag_name'
# real latest patch of a minor — enumerate, then take the max yourself (paginate for older minors)
gh api 'repos/rancher/rancher/releases?per_page=100' \
  --jq '.[]|select(.prerelease|not)|.tag_name' | grep -E '^v2\.13\.' | sort -V | tail -1
```

Component → release source (community):

| Component | Source |
|-----------|--------|
| Rancher | `rancher/rancher` (releases + issues) |
| Charts (Fleet, Turtles, provisioning-capi, rancher-backup, …) | `rancher/charts` — `assets/<chart>/` per `release-v2.X` branch |
| KDM | `rancher/kontainer-driver-metadata` (`release-v2.X` branch `data/data.json`) + live `releases.rancher.com/kontainer-driver-metadata/release-v2.X/data.json` |
| Rancher Turtles | `rancher/turtles` |
| Fleet | `rancher/fleet` |
| backup-restore-operator | `rancher/backup-restore-operator` |
| CAPRKE2 | `rancher/cluster-api-provider-rke2` |
| Community Helm chart index | `releases.rancher.com/server-charts/latest/index.yaml` (current stable); `.../stable/` for older |

**Chart-version prefix is NOT a reliable Rancher-minor map** — it drifts and differs per chart
family. Use the chart's `catalog.cattle.io/rancher-version` annotation (the authoritative gate) and
the `+up<appversion>` suffix. (Observed: the feature charts — fleet/turtles/capi/backup — use the
106/107/108/109 prefix base for 2.11/2.12/2.13/2.14, but don't rely on that across families.)

EOL cross-check: `gh api https://endoflife.date/api/v1/products/rancher/` (or WebFetch
endoflife.date/rancher).
