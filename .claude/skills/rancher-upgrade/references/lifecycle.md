# lifecycle.md — community release model, EOL, and version grounding

**Grounded via `gh` + endoflife.date + suse.com/lifecycle: 2026-05-30; ceiling table re-derived
2026-10-27.** Current community ceiling: `v2.15.2` (2026-09-23). Re-ground at use time (House Rule #3) — releases move.

**Contents:** [Community vs Prime](#community-vs-prime--the-only-reliable-discriminator) ·
[Cadence & lifecycle / EOL](#cadence--lifecycle) · **[Latest patch per minor — the community ceiling
is NOT the top tag](#latest-patch-per-minor--the-community-ceiling-is-not-the-top-tag)** ·
[Grounding — repo map + anti-confirmation method](#grounding-house-rule-3--repo-map--anti-confirmation-method)

## Community vs Prime — the only reliable discriminator

Rancher's GitHub releases carry **both** community and Prime builds, so "is there a GitHub
release?" does NOT establish whether a patch is community-supported. The reliable signal is a
**classifier sentence in the GitHub release-notes body**:

| Body contains | Meaning |
|------------|---------|
| `"This is a Community version release"` | Community cadence — supported for community users. Only the newest minor. |
| `"This is a Community and Prime version release"` | Patch on the then-newest minor; serves both. |
| `"This is a Prime version release"` | Prime-cadence patch on an older minor; full notes still on GitHub but **not** community-supported. |
| `"Please refer to our Prime Documentation…"` (stub, no notes) | Prime-only; community gets nothing here. |
| *(empty body, no assets)* | Unclassifiable by notes — treat as **not community**. Every older-minor tag of the 2026-09-23 batch took this form, and none is in the community chart index. |

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

Empty body = not community. Any other non-match = an unrecognized notes format; read the body before
assuming community. Settle doubt with the community chart index — a version absent from
`releases.rancher.com/server-charts/{latest,stable}/index.yaml` is not installable by `helm upgrade`.

## Cadence & lifecycle

- **Minor cadence ≈ every 4 months (Mar / Jul / Nov).** Grounded GA dates: 2.11.0 = 2025-03-31,
  2.12.0 = 2025-07-31, 2.13.0 = 2025-11-25, 2.14.0 = 2026-03-26, 2.15.0 = 2026-07-30.
- **Patches are monthly and in lockstep across all active minors** (one batch, same day). There is
  **no separate "Prime patch cadence" offset** — the apparent Apr/Aug/Dec pattern is just the
  `.0`→`.1` stabilization gap (SUSE counts the support clock from the stabilized ~`.1` GA, ~1 month
  after the GitHub `.0`).
- **Support window ≈ 18 months** from the stabilized GA = ~6 months maintenance (GA→EOM) + ~12
  months limited (EOM→EOL: critical-security fixes on request only), for 2.9 onward.

**EOL dates (suse.com/lifecycle + endoflife.date agree):**

| Minor | Community GA (.0) | EOL |
|-------|-------------------|-----|
| 2.11 | 2025-03-31 | **2026-10-24** (passed) |
| 2.12 | 2025-07-31 | **2027-02-28** |
| 2.13 | 2025-11-25 | **2027-06-17** |
| 2.14 | 2026-03-26 | **2027-10-10** |
| 2.15 | 2026-07-30 | **2028-02-27** |

Read EOL dates from endoflife.date or suse.com/lifecycle; never compute one. They are not
GA+18mo arithmetic (2.11 GA 2025-03-31 would give 2026-09-30, the published date is 2026-10-24),
because SUSE counts from the stabilized ~`.1` GA. A minor with no published date is unannounced.

> **Trap — endoflife.date's `latest` column is the PRIME tag, not the community ceiling.** It
> reports Prime-only patches for every minor but the newest (2.14.6 / 2.13.10 / … on 2026-10-04). It
> overshoots exactly the way `sort -V | tail -1` does, so use it for **dates only** and take
> ceilings from the edition discriminator below. Its `releaseDate` column is the stabilized
> date, not the GitHub `.0` — which is why it reads 2.14 as 2026-04-30 while the `.0` tag is
> 2026-03-26.

### Latest patch per minor — the **community** ceiling is NOT the top tag

⚠ **The single most dangerous version mistake in this skill's domain.** The ladder rule says "land on
the latest patch of the current minor before stepping". For every minor except the current one, the
newest *tag* is a non-community patch (Prime-only, or an empty-body tag) a community operator
cannot install:

| Minor | Newest tag (`sort -V \| tail -1`) | **Community ceiling** | Community ceiling released |
|---|---|---|---|
| 2.11 | v2.11.18 | **v2.11.3** | 2025-06-25 |
| 2.12 | v2.12.14 | **v2.12.3** | 2025-10-22 |
| 2.13 | v2.13.10 | **v2.13.3** | 2026-02-25 |
| 2.14 | v2.14.6 | **v2.14.3** | 2026-06-29 |
| 2.15 *(current)* | v2.15.2 | **v2.15.2** ✓ | 2026-09-23 |

Every non-current line stops at **`.3`** — that is the cutover: once the next minor GAs, the previous
line's subsequent patches flip to Prime. Only the current minor is fully community.

Confirmed by two independent sources: the release-notes edition markers, **and** the community Helm
chart index itself — `releases.rancher.com/server-charts/{latest,stable}/index.yaml` offer exactly
2.11.3 / 2.12.3 / 2.13.3 / 2.14.3 / 2.15.2 and nothing higher per line. The chart index is the
decisive test, because it is what `helm upgrade` actually pulls.

**Use these as the ladder targets. Always re-derive — see Grounding.**

⚠ **A pre-GA next minor is look-ahead only, never a target.** Its `release-v2.X` branches in
`rancher/charts` and KDM, a live KDM `data.json` and `-rc` tags all appear weeks before GA, and no
RC carries a community classifier sentence. Plan onto the current minor's community ceiling; say in
the plan that a hop to the next minor follows its GA (cadence above) instead of presenting the
current minor as terminal (House Rule #4). Re-run the ceiling probe before writing any plan — the
current-minor row above is the fastest-moving fact in this skill.

⛔ **2.11 is past EOL (2026-10-24), and community 2.11 has had no fix since v2.11.3 (2025-06-25).**
2.11 is this skill's upgrade *floor*: an operator arriving on it starts the one-minor-at-a-time
ladder (2.11→2.12→2.13→2.14→2.15) from an unsupported version that sits under every advisory floor
on the line. Treat it as urgent — chain the hops in as few windows as the gates allow (SKILL.md § 2) and
target the newest minor (House Rule #4). 2.10 and older (EOL 2026-06-19) are below the floor.

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
```

⛔ **Do NOT derive a per-minor target with `… | sort -V | tail -1`.** That returns the newest *tag*,
which for any non-current minor is a **Prime-only** patch (see the community-ceiling table above).
It is the highest-consequence trap in this skill: it silently produces an upgrade target the
community operator cannot install.

Two edition-aware derivations — prefer the first, it needs one request and no interpretation:

```bash
# BEST — the community chart index is what `helm upgrade` actually pulls, so it cannot disagree
curl -s https://releases.rancher.com/server-charts/latest/index.yaml \
  | grep -oE '^\s+version: 2\.13\.[0-9]+$' | awk '{print $2}' | sort -V | tail -1
# (the `$` anchor is load-bearing — without it, `2.15.0-rc3` is reported as `2.15.0`)

# CROSS-CHECK — edition markers on the release notes; Prime uses TWO forms, test for both
gh api repos/rancher/rancher/releases/tags/<tag> --jq '.body' \
  | grep -oiE 'This is a (Community and Prime|Community|Prime) version release|refer to our \[?Prime Documentation'
# "Prime version release" OR the Prime-docs redirect  -> Prime-only, NOT installable by community
```

**`k8s-components-checker` owns the full edition-discrimination protocol** —
`references/version-verification.md` § Edition discrimination, plus the per-patch 2.11 mapping in
`references/compat/rancher.md`. Cite it for the method; the table above is this skill's ladder-facing
consequence of it.

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
