# version-verification.md — ground version claims; never invent releases

The registry's **k8s support windows** (minor-level floors/ceilings) are durable
methodology and are the registry's job to carry. **Specific version numbers** —
"latest patch", "newest minor", "CVE fixed in vX.Y.Z" — are volatile and are the
#1 source of fabrication: sifting release notes into prose invites
plausible-but-nonexistent patch numbers. A real example this skill produced: a
verdict cited **Argo CD `v3.2.10` / `v3.2.12`** and "CVE-2026-42880 fixed in
3.2.10" — the 3.2 line actually ended at **v3.2.6**, unpatched. Harbor `## 2.15`
was written as the newest line while `releases/latest` was `v2.14.4`.

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

### Anti-confirmation discipline (this is the part that actually matters)

Existence/list queries get **rubber-stamped**. Observed in practice: list and
membership endpoints, and even per-tag lookups, will echo a plausible-but-fake
version back as real (`v3.2.10`, `v2.15.0` returned 200), and the *list output is
contaminated by version strings present elsewhere in the same command*. Only
*absurd* fakes (`v9.9.9`, `v2.99.0`) reliably 404. So:

1. **Never name a candidate version in the query.** Do NOT run
   `gh ... releases/tags/v3.2.10` or `... | grep v3.2.10`. A leading query is a
   confirmed query.
2. **Anchor on the authoritative scalar.** Fetch latest with the version absent
   from the command:
   ```bash
   gh api repos/<org>/<repo>/releases/latest --jq '.tag_name'
   ```
   This is the real ceiling. **Reject any cited version greater than it** (a
   published release cannot be newer than `latest`). Harbor `2.15.0 > 2.14.4` →
   reject the 2.15 claim.
3. **Enumerate, then derive the max yourself** — don't ask whether a patch
   exists, list the minor and pick the top:
   ```bash
   gh api 'repos/<org>/<repo>/releases?per_page=100' \
     --jq '[.[] | select(.prerelease|not) | .tag_name] | .[]' \
     | grep -E '^v?1\.20\.' | sort -V | tail -1     # the REAL latest 1.20 patch
   ```
   Cite that derived value, not one from memory. **The enumeration can be
   contaminated too** — the list endpoint echoes version strings present anywhere
   in your command *or session context* (observed: harbor's list returned
   `v2.15.0`/`v2.15.1` right after they'd been discussed, while `releases/latest`
   stayed `v2.14.4`). So re-apply step 2 to the enumeration output: **discard any
   enumerated tag newer than `releases/latest`.** If the enumerated max exceeds
   `releases/latest`, the list is contaminated — trust the scalar. `releases/latest`
   is the only signal that holds consistent.
4. **Cross-check consistency.** A "fixed-in vX.Y.Z" or "latest vA.B.C" that
   exceeds `releases/latest`, or names a patch the enumeration doesn't produce as
   the max-or-below of its minor, is fabricated → strike it.
5. **EOL** via endoflife.date (also a network call; online only):
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
older minor's later patches flip to **Prime-only**. So `releases/latest` (the current minor's
top patch) is community and grounds fine — but the "latest community patch" of an **older**
minor is **not** its top tag, and `sort -V | tail -1` returns a **Prime** patch.

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
