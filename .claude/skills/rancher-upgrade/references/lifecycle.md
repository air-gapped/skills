# lifecycle.md — community release model, EOL, and version grounding

**Grounded via `gh` + endoflife.date + suse.com/lifecycle: 2026-05-30.** Ceiling at sift:
Rancher community `v2.14.3` (2026-06-29, re-verified 2026-07-25). Re-ground at use time (House Rule #3) — releases move.

**Contents:** [Community vs Prime](#community-vs-prime--the-only-reliable-discriminator) ·
[Cadence & lifecycle / EOL](#cadence--lifecycle) · [Grounding — repo map + anti-confirmation
method](#grounding-house-rule-3--repo-map--anti-confirmation-method)

## Community vs Prime — the only reliable discriminator

Rancher's GitHub releases carry **both** community and Prime builds, so "is there a GitHub
release?" does NOT establish whether a patch is community-supported. The reliable signal is a
**classifier sentence in the GitHub release-notes body**:

| Body contains | Meaning |
|------------|---------|
| `"This is a Community version release"` | Community cadence — supported for community users. (Currently only the **2.14.x** line.) |
| `"This is a Community and Prime version release"` | Patch on the then-newest minor; serves both. |
| `"This is a Prime version release"` | Prime-cadence patch on an older minor; full notes still on GitHub but **not** community-supported. |
| `"Please refer to our Prime Documentation…"` (stub, no notes) | Prime-only; community gets nothing here. (Currently **2.11.15 / 2.12.11 / 2.13.7**.) |

⚠ **Do NOT read this off `head -1`.** Verified 2026-07-25: the classifier sentence is *not*
the first line on a community release. Community bodies open with a `# Release vX.Y.Z`
markdown heading and carry the sentence at **body line 3** (patch) or **line 12** (a `.0`
minor); only the Prime *stub* form is genuinely line 1. A `head -1` classifier therefore
matches **none** of the first three rows and silently mis-classifies every community patch.
Grep the whole body instead.

**Cutover trigger:** when a new minor GAs, the previously-newest minor's *subsequent* patches flip
from Community → Prime labeling. So at any moment, **only the current stable minor is on community
cadence**; older still-supported minors get Prime-cadence patches. An operator upgrading an older
minor air-gapped must verify the specific patch actually ships a community-consumable chart/image
(the `rancher-latest` server-charts repo tracks the current stable minor; older minors live in
`rancher-stable` / per-version) — `UNVERIFIED` in general, check per version.

To classify a patch:

```bash
gh api repos/rancher/rancher/releases/tags/<tag> --jq '.body' \
  | grep -iEm1 'this is a (community and prime|community|prime) version release|refer to our \[?Prime Documentation'
```

No match at all = an unrecognized notes format; read the body before assuming community.

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

EOL table re-verified 2026-07-21 against endoflife.date — all four dates unchanged.

Latest patch per minor, re-grounded 2026-07-25 (unchanged): **2.11.15, 2.12.11, 2.13.7, 2.14.3** —
all four lines were patched on the same day, **2026-06-29**. Always re-derive — see Grounding.

⚠ **v2.15 is at RC and its release plumbing is already live (grounded 2026-07-25).** The prior pass
(2026-07-21) recorded 2.15 as *alpha*; it moved that same day. Observed now: `v2.15.0-rc1`
(2026-07-21) through `v2.15.0-rc3` (2026-07-24), plus **`release-v2.15` branches in both
`rancher/kontainer-driver-metadata` and `rancher/charts`**, and a live
`releases.rancher.com/kontainer-driver-metadata/release-v2.15/data.json` serving 200. On the
Mar/Jul/Nov cadence, 2.15 GA is **due now** — but it is still a prerelease, so:

- **Do NOT plan a hop onto 2.15**; `releases/latest` remains v2.14.3 and no community classifier
  sentence exists for an RC. 2.14 is the correct target today.
- **Do factor it into look-ahead (House Rule #4).** A fleet landing on 2.14 should expect a 2.15 hop
  shortly after GA — say so in the plan rather than presenting 2.14 as a terminal state.
- **Re-run the ceiling probe before writing any plan.** This line is the fastest-moving fact in the
  skill; between GA and this stamp the correct target changes.

⚠ **2.11 goes EOL 2026-10-24 — roughly three months out.** 2.11 is this skill's
upgrade *floor*, so an operator arriving on 2.11 has a short runway: they are
starting a one-minor-at-a-time ladder (2.11→2.12→2.13→2.14) from a version
that leaves support before that ladder is likely to finish. Factor that into
look-ahead targeting (House Rule: pick the version covering the *next* hop) —
and note **2.10 is already EOL (2026-06-19)**, so anyone below the floor is
unsupported today.

## Grounding (House Rule #3) — repo map + anti-confirmation method

`gh` must run with **valid auth** from the operator's workstation. Anonymous = 60 req/hr and
exhausts almost instantly on an enumeration sweep — confirm `gh auth status` shows a logged-in
account and `gh api rate_limit --jq '.resources.core'` shows a 5000 limit BEFORE sweeping. (Run
`gh` centrally, not fanned across many subagents — they share one rate-limit bucket.)

Anti-confirmation: **anchor on `releases/latest`, enumerate-and-derive, never name a candidate
version in the query** (existence/list/per-tag queries get rubber-stamped — plausible fakes return
200).

**`isPrerelease` is not trustworthy across the Rancher org — check the tag string too.**
Verified 2026-07-21: `rancher/turtles` publishes release-candidate tags with
`isPrerelease=false` — `v0.25.6-rc.1` and `v0.26.4-rc.2` both pass an
`isPrerelease==false` filter. A sweep that trusts the flag will report an RC as
the stable version. Filter on **both**:

```bash
gh release list -R rancher/turtles --limit 40 \
  --json tagName,publishedAt,isPrerelease \
  --jq '.[] | select(.isPrerelease==false) | select(.tagName|test("-(rc|alpha|beta)")|not)
        | "\(.tagName)\t\(.publishedAt[0:10])"'
```

**And do not read component versions off the component repo at all** — not because stable tags are
missing, but because the component repo answers *"what exists"*, not *"what ships with 2.14"*. The
authoritative binding of component → Rancher minor is the **`rancher/charts` `release-v2.X`
branch**, which is what § chart-version lookup already prescribes.

> **Why the wording changed — a caution about snapshot claims.** The 2026-07-21 pass recorded that
> the top of the release list for `rancher/fleet`, `rancher/backup-restore-operator` and
> `rancher/turtles` was *entirely* RC tags with "no stable tag in the recent window to find".
> Re-probed 2026-07-25, **that had already reversed in four days**: Fleet cut stable
> `v0.12.18 / v0.13.14 / v0.14.9 / v0.15.5` on 2026-07-22 (all four lines at once, mapping cleanly
> onto 2.11/2.12/2.13/2.14) and Turtles cut `v0.26.4` / `v0.25.6` / `v0.27.0` on 2026-07-21–22. Only
> BRO still tops out on RCs (`v11.0.0-rc.6`; newest stable `v10.0.7`). Treat "repo X currently has no
> stable release" as a *reading of one moment*, never as a durable property — the release-plumbing
> state around a pending minor flips within days.

**Fastest exact answer to "which component version is in *this patch*": the release's own
`rancher-mirror-to-rancher-org.sh` asset.** It is a flat `docker pull` list of the precise image
tags that patch ships — one fetch, no branch archaeology, and it is the release artifact itself
rather than an inference from a chart branch:

```bash
# no candidate version named; <tag> comes from the ceiling/enumeration probes above
curl -sL https://github.com/rancher/rancher/releases/download/<tag>/rancher-mirror-to-rancher-org.sh \
  | grep -E 'rancher/(fleet|backup-restore-operator|cluster-api-controller|turtles):' | sort -u
```

Grounded 2026-07-25 on **v2.14.3** → `fleet:v0.15.4`, `backup-restore-operator:v10.0.5`,
`turtles:v0.26.3`, `cluster-api-controller:v1.12.7`. Note **every one of those sits *below* the
newest stable tag in its own repo** (Fleet `v0.15.5`, BRO `v10.0.7`, Turtles `v0.26.4`) — a concrete
demonstration of why the component repo cannot answer this question. Use the `rancher/charts`
`release-v2.X` branch for the
**chart**-level binding and its `rancher-version` annotation; use this asset for the **image** tags
actually deployed.

```bash
# the ceiling (no candidate version in the command)
gh api repos/rancher/rancher/releases/latest --jq '.tag_name'
# real latest patch of a minor — enumerate, then derive the max locally (paginate for older minors)
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
