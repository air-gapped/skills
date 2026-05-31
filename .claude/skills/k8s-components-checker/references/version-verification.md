# version-verification.md — ground version claims; never invent releases

The registry's **k8s support windows** (minor-level floors/ceilings) are durable
methodology and are the registry's job to carry. **Specific version numbers** —
"latest patch", "newest minor", "CVE fixed in vX.Y.Z" — are volatile and are the
#1 source of fabrication: sifting release notes into prose invites
plausible-but-nonexistent patch numbers. A real example this skill produced: a
verdict cited **Argo CD `v3.2.10` / `v3.2.12`** and "CVE-2026-42880 fixed in
3.2.10" — the 3.2 line actually ended at **v3.2.6**, unpatched (pure
fabrication). The **opposite** error happened too: Harbor `## 2.15` was *struck*
as "not released" because `releases/latest` was `v2.14.4` — but `v2.15.0` /
`v2.15.1` are real, *higher* releases; `releases/latest` is **recency, not
rank**. Two different failure modes, two different defenses — see § Three
orthogonal failure modes.

This file is the protocol that stops both the survey and `freshen` from asserting
a release they have not grounded.

## The rule (non-negotiable — House Rule #8)

Never state a specific release/patch number as fact unless one of:

- **(a) Cluster-reported** — it is the version `kubectl`/`helm` reports as
  installed (ground truth; needs no external check); or
- **(b) Grounded** — it has been confirmed against a freshly fetched release
  listing using the *anti-confirmation* method below; or
- **(c) Marked UNVERIFIED** — written as
  `vX.Y.Z (registry-asserted, sifted <date>; UNVERIFIED — confirm vs releases when online)`.

Always separate the two kinds of claim in a verdict:

| Claim kind | Source | Treatment |
|---|---|---|
| k8s support window / minor floor / "supports 1.32–1.34" | registry compat file | cite the compat file; durable |
| latest patch, "newest minor", "CVE fixed in vX.Y.Z", a recommended **target** patch | release listing | **must be grounded or marked UNVERIFIED** |

If you cannot ground a specific patch and cannot mark it unverified honestly,
state the **minor** (`bump to a supported 1.20.x`) instead of inventing a patch.

## When online (internet + `gh` available): grounding is MANDATORY

If the operator's workstation has internet and `gh` is authenticated, you MUST
ground every specific version the verdict will cite (the recommended target, any
"fixed-in" patch, any "latest" claim). This is not optional when the tools are
present — the air-gap design is a floor, not a ceiling.

### Three orthogonal failure modes — ground against all three

Version grounding fails in three independent ways. Defending against one does
**not** cover the others; a version is grounded only when all three are clear.

| # | Failure mode | Looks like | Defense |
|---|---|---|---|
| 1 | **Fabrication** | a version that does not exist (`v3.2.10`, `v9.9.9`) asserted as real | derive from a no-candidate enumeration; a fake 404s on `gh release view <tag>` |
| 2 | **`releases/latest` ≠ highest version** | `releases/latest` points at an *older* minor's patch while a higher minor exists | never treat it as a ceiling; enumerate + reason per minor line |
| 3 | **Edition** | a real, older **Prime/EE** patch passes as community | release-notes edition discriminator (next subsection) |

#### 1 — Don't let a named candidate bias you (fabrication)

A query that names your guess confirms your guess. Ask the listing *what exists*,
never *whether your candidate exists*.

- **Never put a candidate version in the command** (`releases/tags/v3.2.10`,
  `| grep v3.2.10`). Only absurd fakes (`v9.9.9`) reliably 404; a plausible one you
  name biases your reading of the output.
- Fetch the full non-prerelease tag list with **no version named** — GitHub
  returns the repo's real tags (it does not invent releases), so **this
  enumeration is the authority for what exists:**
  ```bash
  gh api 'repos/<org>/<repo>/releases?per_page=100' --jq '[.[]|select(.prerelease|not)|.tag_name]|.[]'
  ```
- A tag absent from that list — or one that 404s on `gh release view <tag> --repo
  <org>/<repo>` — is fabricated → strike it. A real release returns a body +
  `published_at` + assets.

#### 2 — `releases/latest` is recency, not rank (the one this skill got wrong)

`gh api .../releases/latest` returns the **most-recently-published**
non-prerelease/non-draft release — **or whatever the maintainer manually flagged
"Latest."** It is **NOT the highest semantic version.** Any project that keeps
more than one line alive at once (an LTS/maintenance minor *plus* the current
minor, or several stable branches patched together) publishes **out of order**: a
back-ported fix lands on an *older* minor *after* a newer minor shipped — or a fix
**isn't needed in the higher line, so that line gets no matching patch.** Either
way `releases/latest` can point at the old line's fresh patch while a
genuinely-higher minor sits "below" it by date.

- **The real instance (the bug this section fixes):** Harbor `releases/latest =
  v2.14.4`, yet `v2.15.0` / `v2.15.1` are real, released minors — `v2.14.4` is just
  a later patch on the still-maintained 2.14 line; **2.15 is the newer feature
  line.** A prior grounding "rejected 2.15 as contamination because it exceeded
  `releases/latest`" — that rejection rule **was the error.** (RKE2 is the same
  shape: `1.32.x … 1.36.x` all take `+rke2rN` patches on one day; a late 1.34 CVE
  patch would make `releases/latest` a 1.34 tag with 1.36 long out.)
- **The rule:** **never use `releases/latest` as a version ceiling, and never
  reject a higher enumerated minor on its strength.** It tells you only *which line
  is most-recently / actively patched* (useful — that's the maintained line). To
  find what is newest, **enumerate and reason per minor line:**
  ```bash
  # every minor LINE that exists (highest = newest feature line, regardless of dates):
  gh api 'repos/<org>/<repo>/releases?per_page=100' --jq '[.[]|select(.prerelease|not)|.tag_name]|.[]' \
    | sed -E 's/^v?([0-9]+\.[0-9]+).*/\1/' | sort -uV
  # ceiling patch of one line (e.g. 2.15):
  gh api 'repos/<org>/<repo>/releases?per_page=100' --jq '[.[]|select(.prerelease|not)|.tag_name]|.[]' \
    | grep -E '^v?2\.15\.' | sort -V | tail -1
  ```
- The **highest minor in the enumeration is the newest line**, whether or not
  `releases/latest` agrees. If a surprising tag's reality is in doubt, confirm it
  **directly** (`gh release view <tag>` → metadata vs 404) — do **not** adjudicate
  it against `releases/latest`. Publish-date order tells you *which lines are
  maintained*, never *which version is higher*.

#### 3 — Consistency cross-check, then EOL

A "fixed-in vX.Y.Z" or "latest vA.B.C" that the no-candidate enumeration does not
produce (as a real tag at or below its line's ceiling) is fabricated → strike it.
**Do not** strike a version merely for exceeding `releases/latest` — that is
failure mode 2, not fabrication.

EOL via endoflife.date (also a network call; online only):
```bash
gh api https://endoflife.date/api/v1/products/<product>/ 2>/dev/null   # or curl
```

### Edition discrimination (community vs Prime/EE) — what anti-confirmation does NOT catch

Anti-confirmation proves a release **exists** and is **not newer than `latest`**. It does
**not** prove the release is the **edition the registry tracks** (House Rule #1: community
only). A real, older, **Prime/enterprise** patch passes every existence check — it exists, it
is below `latest` — and gets rubber-stamped as community. This is a **separate axis** from
fabrication and needs its own grounding step. *(Real miss: `compat/rancher.md` carried "2.12
latest community: v2.12.6" through a freshen on 2026-05-30. v2.12.6 is **Prime-only**. The
freshen anchored on `releases/latest` = v2.14.2, found 2.12.6 real and below latest, and left
it. Nothing checked edition.)*

Applies to any vendor with an OSS-vs-paid split that publishes **both** editions to one feed:

| Vendor | Both editions on one feed? | Discriminator |
|---|---|---|
| **Rancher** (community vs SUSE **Prime**) | yes — `rancher/rancher` GitHub releases carry both; `prerelease` flag does NOT separate them | **release-notes first line**. Prime-only ⟺ body redirects to `"Please refer to our Prime Documentation …"`. Community = `"… This is a Community version release …"` **or** inline notes (`# Release vX.Y.Z`). **Test for the Prime marker; treat its absence as community** (a positive "community version release" grep misses the older inline-notes format). |
| **GitLab** (CE vs EE) | tags shared | operator runs the EE binary as CE — treat as CE per House Rule #1; edition is not version-distinguished, so no per-tag check needed. |

**The pattern anti-confirmation misses (Rancher):** once a newer community minor ships, the
older minor's later patches flip to **Prime-only**. So `releases/latest` (here v2.14.2, a
current-minor patch) is community and grounds fine — but the "latest community patch" of an
**older** minor is **not** its top tag, and `sort -V | tail -1` returns a **Prime** patch.
(Note this is failure mode 2's cousin: the *highest* tag of an older line is not the answer —
there because of edition, in §2 because of recency. Enumerate and reason per line either way.)

Derive "latest community patch of minor X" by filtering on the discriminator, newest-first,
stopping at the first non-Prime release — never by version order alone:

```bash
# latest COMMUNITY patch of a Rancher minor (e.g. 2.12): stop at first tag NOT redirecting to Prime docs
for t in $(gh api 'repos/rancher/rancher/releases?per_page=100' \
            --jq '[.[]|select(.prerelease|not)|.tag_name]|.[]' | grep -E '^v2\.12\.' | sort -rV); do
  gh api repos/rancher/rancher/releases/tags/$t --jq '.body' | head -1 \
    | grep -qi 'prime documentation' || { echo "latest community 2.12: $t"; break; }
done
```

Verified 2026-05-30: 2.12 → **v2.12.4** (v2.12.5+ Prime), 2.13 → **v2.13.3** (v2.13.4+ Prime),
2.14 → **v2.14.2** (current minor). `sort -V | tail -1` on 2.12 returns **v2.12.10 — a Prime
patch**; that is the exact rubber-stamp this step prevents.

### Chart vs app version

For Helm-installed components the operator picks the **chart** version, but the
compat verdict often cites the **app** version. Ground BOTH against their own
repos:

- Argo CD: app = `argoproj/argo-cd`, chart = `argoproj/argo-helm` (`argo-cd-*` tags)
- Harbor: app = `goharbor/harbor`, chart = `goharbor/harbor-helm`
- Grafana Mimir: `grafana/mimir` — `chart_metadata`; verify the chart's
  `Chart.yaml` `kubeVersion:` at the chart-release tag, not just the app version.

## Component → release source (for `gh`)

| Component | Release source |
|---|---|
| RKE2 | `rancher/rke2` |
| Rancher | `rancher/rancher` — **community/Prime share one feed; apply § Edition discrimination, do NOT `sort -V | tail -1`** |
| Cilium | `cilium/cilium` |
| Tetragon | `cilium/tetragon` (chart == app version; no `kubeVersion:`; kernel floor from `tetragon.io/docs/installation/faq/`, not `gh`) |
| cert-manager | `cert-manager/cert-manager` |
| Kyverno | `kyverno/kyverno` |
| KEDA | `kedacore/keda` |
| Argo CD | `argoproj/argo-cd` (app) · `argoproj/argo-helm` (chart) |
| Harbor | `goharbor/harbor` (app) · `goharbor/harbor-helm` (chart) |
| Traefik | `traefik/traefik` |
| Rook | `rook/rook` |
| Ceph | `ceph/ceph` (k8s axis is transitive via Rook — see `compat/ceph.md`) |
| OpenEBS | `openebs/openebs` (+ engines: `openebs/mayastor`, `openebs/lvm-localpv`, `openebs/zfs-localpv`, `openebs/dynamic-localpv-provisioner`) |
| NVIDIA GPU Operator | `NVIDIA/gpu-operator` |
| ECK | `elastic/cloud-on-k8s` |
| Zalando postgres-operator | `zalando/postgres-operator` |
| Harvester | `harvester/harvester` |
| Grafana Mimir | `grafana/mimir` (chart `Chart.yaml`) |
| **GitLab** | **NOT GitHub** — chart at `gitlab.com/gitlab-org/charts/gitlab`. `gh` does not apply; use the GitLab API / `glab` / `helm search repo`, else mark UNVERIFIED. |

## When air-gapped (no internet): mark, don't invent

State support windows from the registry as normal (cite the compat file). For
any specific patch / "fixed-in" / "latest" you would otherwise cite, append
`(registry-asserted, sifted <date>; UNVERIFIED — confirm vs releases when
online)`, or drop to the **minor** level. Never present an ungrounded patch
number as established fact. Recommend `skill-improver freshen k8s-components-checker`
from an internet-accessible client.

## At freshen time (writing the compat files)

Same protocol, applied to authoring:

- Only write version numbers that appear in a **freshly fetched, uncontaminated**
  release listing (step 2–3 above). Never extrapolate a patch line ("…so 3.2.10
  probably exists").
- Derive each "latest patch of minor X" by enumeration + `sort -V | tail -1`.
- Ground every "fixed-in vX.Y.Z" against that release's own notes
  (`gh release view <tag> --repo <r>`); if you cannot, **omit the claim** rather
  than guess.
- Stamp `Last sifted: <date>` only after grounding. Add `Last release-verified:
  <date>` when versions were checked against `gh`.
