# improvement-backlog.md

Ceiling findings from skill-improver runs.

## Resolved — 2026-09-15 (rancher-logging: the pending respin shipped everywhere)

- **`rancher.24` has shipped on all five lines**, where at sift it existed only as
  an rc on 2.14: 2.11 → `106.0.8`, 2.12 → `107.0.6`, 2.13 → `108.0.5`,
  2.14 → `109.0.1`, all `+up4.10.0-rancher.24`.
- **The 2.15 chart line is released, not an rc** — `110.0.0+up4.10.0-rancher.24`.
  That closes a loop opened earlier in this same pass: Rancher **2.15 was added to
  the registry today** as a new community minor, and its logging chart being real
  is what makes a 2.15 survey answerable at all.
- **Its kube gate was deliberately not re-derived** and is marked so. Reading it
  is a sift; enumerating assets is a release check. Same discipline as the other
  components verified in this pass.
- **Upstream base is still 4.10.0 on every line** — the freeze the sift predicted
  continues, and the per-line kube gates are untouched.
- Worth restating why exact strings matter here: the `+…` build metadata is
  **invisible to Helm's version comparison**, so two artifacts on a line can
  differ only in a field Helm ignores. The file already warned about that on the
  2.12 line; this refresh is precisely that field moving on all five.

## Resolved — 2026-09-15 (the recommended Postgres-operator patch had a write loop)

- **"Use 2.0.1, never 2.0.0" is superseded: require ≥ 2.0.2** (2026-08-20).
- **The reason is a compound, not a newer number.** §2.0.0 already documents that
  `password_encryption` defaults to **scram-sha-256**. v2.0.2 fixes "skip
  `ALTER ROLE` when the stored SCRAM verifier already matches the password"
  (#3171). Together: on 2.0.0/2.0.1 that default makes the operator re-issue
  `ALTER ROLE` for managed roles **every sync cycle, indefinitely** — a
  steady-state write loop against every managed database, not a one-off
  migration cost. Neither fact says that alone, which is why it was worth writing
  at the recommendation rather than leaving it in a changelog.
- **2.0.1 was not "the release where the CRD is correct".** v2.0.2 also fixes
  `sidecars` schema validation in the OperatorConfiguration CRD (#3160) — a
  *different* field from the type mismatch 2.0.1 fixed, so a GitOps diff/apply
  loop could still bite.
- Also recorded: the Helm chart gained `strategy: Recreate` (#3164) to smooth the
  **v1.x → v2.x** hop, and the only breaking change (#3156, `/v2` Go module path)
  affects library consumers, not deployments.
- **The durable instruction:** this operator's pattern now reads three deep —
  1.15.0 broken images, 2.0.0 broken CRD, 2.0.1 write loop plus a second CRD gap.
  The entry says not to treat the newest patch on this line as safe by default,
  which is the opposite of the usual take-the-latest-patch advice.
- **GitLab release-verified in the same pass**: chart tags `v10.3.2` / `v10.2.6` /
  `v10.1.8` (2026-09-10), all still inside the documented 10.x / GitLab-19.x row,
  so the row and floors are unchanged. The chart→app mapping was **not**
  re-derived; the entry now says to read `appVersion` from the chart at survey
  time rather than trusting the July figure. Note `gh` does not apply to
  gitlab.com — the tags came from the GitLab API.

## Resolved — 2026-09-15 (patch-level release-verify: RKE2, Rook, Tetragon, KEDA)

- **No new minors**, so every k8s window and in-scope set is unchanged and no
  verdict flips. Only the latest-patch figures moved — which is what a currency
  question reads.
- **RKE2 drifted on all four tracked minors**: 1.36 → `v1.36.4+rke2r1`,
  1.35 → `v1.35.8+rke2r1`, 1.34 → `v1.34.11+rke2r1` (all 2026-08-28),
  1.33 → `v1.33.13+rke2r2` (2026-08-04).
- **The 1.33 move is the one worth keeping.** It is `+rke2r1` → `+rke2r2` — a
  **second RKE2 build of the same Kubernetes patch**, with `1.33.13` unchanged.
  A currency check comparing only the k8s portion of the tag calls such a node
  current while a newer build exists. The entry now says to compare the whole
  tag, suffix included.
- **Tetragon** → `v1.7.1` (2026-08-25), still no 1.8. **Rook** → `1.20.7`
  (2026-09-02). **KEDA** → `2.20.2` (2026-07-31) — which also matches what the
  standalone `keda` skill already says, so the two are now consistent.
- All four marked *patch contents not sifted*, and `Last sifted` untouched
  throughout. That separation is what makes a cheap, frequent currency refresh
  possible without implying anyone re-read a support matrix.

## Resolved — 2026-09-15 (Cilium 1.20 GA'd after the sift; the file said not to use it)

- **Cilium's "1.20 is still pre-release only … do not treat it as available" is
  now a wrong instruction.** `v1.20.0` GA'd **2026-07-29** — eight days after the
  2026-07-21 sift — and `v1.20.1` followed 2026-08-18.
- **The scope shift is the part that is easy to miss.** The in-scope rule is
  "current stable + prior 2", so a new stable minor does not add a row, it
  **rotates** the set: 1.20 / 1.19 / 1.18, with **1.17 dropping out**. A 1.17
  verdict flips from supported to out-of-window without anyone editing a table.
- 1.20 has **no section**, so its k8s range is marked not recorded. Not inferred —
  the per-minor sections are the thing a verdict reads.
- **A pre-release note is a statement about a date written in the present tense.**
  `v1.20.0-pre.4, 2026-07-03` was accurate when written and misleading within the
  month. Worth a standing habit: pre-release notes are the shortest-lived claims
  in this registry and should be the first thing a release-verify re-reads.
- **OpenEBS umbrella moved twice past the newest recorded pin** — v4.6.0
  (2026-08-26), v4.6.1 (2026-09-10) against sections stopping at 4.5.0 / 4.5.1.
  The LocalPV-LVM version each pins is **deliberately not filled in**: that
  mapping *is* this file's structure, and guessing it from the umbrella number
  would produce a row indistinguishable from the grounded ones.
- **Checked, accurate, unchanged:** Harbor — it already records 2.15 with the note
  that `releases/latest` returns v2.14.4 by recency rather than rank, which is the
  exact trap a naive latest-version check falls into. Recorded so it is not
  re-opened.

## Resolved — 2026-09-15 (registry release-verify: one EOL flip, one new minor)

- **Kyverno 1.18 is EOL as of 2026-08-20**, when 1.19.0 shipped (1.19.1 followed
  2026-09-10). The file's support rule is mechanical — "when `x.(y+1)` ships,
  `x.y` is EOL" — so the sifted line "1.18 supported (no 1.19 yet)", correct on
  2026-07-21, now returns the **opposite** of the right verdict. A 1.18 cluster
  that passed then is on an EOL minor now.
  - This is the argument for release-verifying mechanically-derived statuses
    separately from sifting matrices: no reading was required to know the answer
    flipped, only a release date.
  - 1.19's own k8s range is **deliberately not recorded** — that would be a sift.
- **ECK 3.5.0 shipped 2026-08-04**, one minor above the newest section (3.4).
  Ranges marked *not recorded*, and a 3.5 deployment marked **unverified rather
  than unsupported**. Not filled in from inference because this file's header
  already flags some rows as reconstructed and some floors as inferred, so an
  invented 3.5 row would be indistinguishable from the grounded ones.
- **`Last sifted` deliberately untouched on both.** Only `Last release-verified`
  moved. The two stamps answer different questions and the registry's value
  depends on not conflating them.
- **Checked, accurate, unchanged:** cert-manager — its in-scope set (1.21 current,
  1.20 current, 1.19 EOL) matches upstream, despite a patch-level string that
  looked four minors stale to a regex. Recorded so the next pass does not re-open it.
- Method note: a crude "latest version" regex across the registry produced several
  false alarms of exactly that shape, because most files state *per-minor* latest
  patches rather than an overall latest. Read the in-scope set, not the first
  version-looking string.

## Resolved — 2026-09-15 (Traefik: eight documented lines, exactly one supported)

- **The file documented 3.0–3.7 and 2.11 as if a survey could land on any of them.** Upstream's
  support table says only **3.7** still has active *or* security support. 3.6's security window
  ended **2026-08-16**; 3.5 and below have none; 2.11's ended **2026-09-07**.
- **The dates interlock with the advisories, which is what makes this a verdict and not a support
  argument.** GHSA-5w68-77r2-r64c (critical — complete authentication bypass in the `digestAuth`
  middleware) published **2026-08-21**, five days *after* 3.6 left security support, with affected
  range `>= v3.0.0, <= v3.7.10`. The 3.6 line's final release is **v3.6.25** (2026-07-31), inside
  that range. **No 3.6.x will ever be patched for it.** CVE-2026-88007 (critical, 2026-09-07) then
  raised the 3.x ceiling to `<= v3.7.12`, moving the floor to **v3.7.13**.
- **A survey now has exactly one answer: v3.7.13+.** "Upgrade to the latest patch of the minor you
  are on" is wrong here for every minor except 3.7 — the usual advice produces a still-vulnerable,
  unsupported build.
- **The 2.11 section was wrong in the direction that strands an operator.** It read "latest patch
  v2.11.46 … security ENDED 2026-02-01". The line kept shipping security releases for another
  seven months through **v2.11.57** (2026-09-04), and upstream gives the end as **2026-09-07**.
  The old text told a 2.11 operator no patch existed when eleven more had shipped, including the
  ones clearing both 2026 criticals. 2.11.57 is not currently exposed — but the window has now
  closed, so the next advisory against it has no fix.
- **The file carried no advisory floors at all** despite Traefik publishing **30 advisories in
  2026**, 16 of them in the seven weeks after the previous sift. A verdict shortcut with the floor
  and the support table now sits at the top, with an instruction to re-derive every pass.
- Upstream's support rule changed at v3.6: each minor now gets 6 months from GA so several overlap,
  where previously a minor's support ended the moment the next shipped. Worth knowing before
  reading the older rows as though the current rule produced them.

## Resolved — 2026-09-15 (a "correction" had deleted six real releases and inverted the verdict)

- **Retracted the 2026-05-30 operator correction in `compat/argo-cd.md`.** It claimed the 3.2 line
  ended at **v3.2.6**, never received the CVE-2026-42880 backport, and that `v3.2.10` / `v3.2.12`
  **do not exist**. All three are false. The line runs to **v3.2.12** (2026-05-13); v3.2.7–v3.2.12
  are real published stable releases; the CVE fixes landed in **v3.2.11** and **v3.2.12**.
- **The verdict it produced was wrong in the operationally expensive direction** — "a 3.2.x cluster
  handling Secrets is permanently exposed, the only path is bump to 3.4.x". A 3.2 cluster already
  on v3.2.12 is exposed to neither CVE. The correction turned schedulable maintenance into an
  incident, and pointed at a destination chosen for the wrong reason.
- **Shape to distrust: a correction that removes releases.** Enumerate the tags before deleting
  one. A single `gh api releases --paginate` would have refuted it at the time.
- **The real reason to leave 3.2 is EOL, and it is derivable rather than looked up.** Argo CD
  supports exactly the newest three minors: **minor N reaches EOL the day minor N+3 GAs.** Three
  independent confirmations — 3.0 EOL 2026-02-02 = v3.3.0 GA, 3.1 EOL 2026-05-06 = v3.4.1 GA,
  3.2 EOL 2026-08-04 = v3.5.0 GA — and v3.2.12's own notes carry the banner. Minors land ~every
  3 months, so **3.3 EOLs when 3.6 GAs, ~2026-11**: a 3.3 landing is temporary by construction.
- **Two more floors were wrong in the unsafe direction.** §3.3 said CVE-2026-42880 was "patched
  3.3.8", but the advisory's range is `3.2.0 - 3.3.8`, so 3.3.8 is *affected*; and §3.4 gave
  "≥ 3.4.0", which is not a usable floor because **there is no `v3.4.0` tag**. With
  CVE-2026-45737's incomplete-fix follow-up the per-line floors are **3.4.2 / 3.3.10 / 3.2.12**.
- **3.5 added** (GA 2026-08-04, latest v3.5.3 2026-09-14), with its k8s floor explicitly marked
  not-re-derived rather than guessed from the 3.4 row.
- Latest-patch figures refreshed: 3.4 → v3.4.9, 3.3 → v3.3.14 (were v3.4.5 / v3.3.12).

## Resolved — 2026-09-15 (Rancher 2.15 added to the registry)

- **The registry stopped at 2.14 while 2.15 had been out for six weeks.** v2.15.0
  (2026-07-30) and v2.15.1 (2026-08-28) both self-declare Community, so this is the
  current community minor and the only one still receiving community patches.
- **k8s axis 1.34–1.36** (adds 1.36 #54303, removes 1.33 #55306). Only 1.34 and 1.35
  overlap with 2.14's 1.33–1.35, so a management cluster on 1.33 has to move k8s
  before Rancher rather than after — the narrow overlap is the part a verdict needs.
- **No cert-manager number recorded, deliberately.** 2.14's #52922 made the supported
  window follow the k8s window instead of a fixed version, and the `v1.13.1` string on
  the doc site is reused verbatim across several Rancher doc versions, so it is not a
  2.15 statement. Derive from k8s instead of copying it.
- **No minimum source version is stated** for the hop to 2.15. Recorded as an absence,
  not as permission to skip minors.
- **v2.15.1 is the security batch**; the same batch carries CVE-2026-75036 against
  **Fleet**, which lives in the `rancher/fleet` advisory feed. A Rancher-only sweep
  misses it — worth knowing for any tooling that maps one skill to one repo.
- **Four open hazards recorded, all verified still open or unshipped on 2026-09-15:**
  #57078 (upgrade to 2.15.1 stranding downstream clusters, rollback-and-restore
  required), #57050 (ClusterRole reconciliation loop on GlobalRole inheritance,
  milestoned **v2.15.2** so it is in no shipped release), #57196 (downstream stuck
  Unavailable after credential regeneration), #57240 (default-registry ignored on the
  Docker install — air-gap relevant).
- **2.15.0 is explicitly not a landing point.** Two release-blocker regressions fixed
  between 2.15.0 and 2.15.1 — OIDC-provisioned users unassignable (#56392) and the
  `--no-cacerts` crashloop (#56522) — appear nowhere in the published notes. The
  release notes on this line run thinner than the tracker, which is the same
  read-the-tracker-too pattern the registry already applies elsewhere.

## Resolved — 2026-09-15 (the 2.12 community ceiling was one patch too high)

- **`v2.12.4` is a Prime release that the registry scored as community.** It carries inline
  `# Release v2.12.4` notes but its body reads "This is a **Prime** version release" — format 2,
  the exact under-detection the 2.11-line caveat already described. Community ceiling for 2.12 is
  **v2.12.3** (2025-10-22).
- **Cause: the fix was scoped to the line that exposed it.** The 2.12 value was derived 2026-05-30
  with the first-line-only test. Format 2 was discovered 2026-06-02 on the 2.11 line, the caveat
  was written as a *2.11-line* caveat, and 2.12 was never re-derived against the better test. Three
  later verifies re-ran the discriminator on "the newest few tags" and never revisited it.
- Corrected in three places that each carried the value independently: the §2.12 heading, the
  header's release-verified stamp, and `version-verification.md`'s derived-ceilings block.
- **The caveat is now stated for every line, not just 2.11**, with a one-pass command that
  classifies all tags at once. Rule added: re-derive every line whenever the discriminator itself
  changes.
- **The Prime flip has an exact trigger, so ceilings need not be re-tested per sift.** A minor gets
  community patches only while it is the newest minor; the first patch on or after the next minor's
  GA is Prime and stays Prime. Confirmed on all 50 stable tags of 2.11–2.15: `v2.11.4` flipped on
  2.12.0's GA date, `v2.12.4` one day before 2.13.0's, `v2.13.4` on 2.14.0's, `v2.14.4` on 2.15.0's.
  A ceiling moves only when a new minor GAs.
- **2.15 is a new community minor** — v2.15.0 (2026-07-30) and v2.15.1 (2026-08-28) both
  self-declare Community. Recorded in the header; its own `## 2.15` compat block is still to be
  sifted from the release notes.

## Resolved — 2026-09-15 (Harvester advisory floors)

- **The registry named two vulnerable releases as upgrade targets.**
  `compat/harvester.md` described the community path as
  `1.5.x → 1.6.1 → 1.7.1 → …`. `1.6.1` is inside **both** Harvester advisories
  and `1.7.1` inside the second, so a verdict built on that sentence recommends
  a vulnerable landing point. Replaced with latest-patch-per-minor plus the
  floors themselves.
- **CVE-2025-62877 (CRITICAL)** — the interactive installer **exposes the OS
  default SSH login password**, affecting `1.5.0–1.5.2` and `1.6.0–1.6.1`.
  Recorded with the consequence that matters for a verdict: this is an
  *installer* exposure, so a node built by an affected installer stays exposed
  after the version moves. Remediation is credential rotation, not the hop.
- **CVE-2025-71261 (HIGH)** — registration-client MITM/DoS, affecting `< 1.8`,
  `<= 1.7.1`, `<= 1.6.1`, `<= 1.5.2`. A floor **per minor**, the same shape as
  the Rancher advisories handled earlier in this pass.
- `first_patched_version` null on both, so the floors come from
  `vulnerable_version_range`. Latest stables at this check: 1.8.2 (2026-08-06),
  1.7.3 (2026-08-07).
- Same correction applied to the `harvester-upgrade` skill, whose
  patch-skipping example named the same `1.5.2 → 1.6.1` pair. Two skills, one
  wrong pair of numbers, found once — which is the argument for keeping the
  compat registry and the upgrade runbook consistent rather than independently
  maintained.

## Open

### Per-version "fixed-in vX.Y.Z" / CVE-patch claims not release-grounded (Dim 9) (new 2026-05-30)

- Every `compat/*.md` carrying "fixed in" / "patched in" lines (keda
  CVE-2025-68476→2.18.3, cert-manager CVE-2025-617xx, argo CVE-2026-42880, ceph
  data-loss point releases). The release-grounding pass confirmed version
  *existence* via `releases/latest`, but the gh release-**body** endpoint is
  confirmatory/contaminated here, so a patch's *changelog contents* can't be
  trusted from it. Action: author verifies the "fixed-in" patches against real
  changelogs on a trusted network, then stamp `Last release-verified:`.

### GitLab not gh-groundable (new 2026-05-30)

- `compat/gitlab.md`. Chart at `gitlab.com/gitlab-org/charts/gitlab`; `gh` does
  not apply. Ground via the GitLab API / `glab` / `helm search`, else mark
  versions `UNVERIFIED`.

### ES 8.8 / 8.14 exact end-of-maintenance dates UNVERIFIED (new 2026-06-02)

- `compat/eck.md` § "Which ECK minors manage Elasticsearch 8.8 / 8.14 / 8.17?".
  ES **8.17 EOL = 2025-08-05** is verified (endoflife.date). **8.8.x and 8.14.x**
  have rolled off endoflife.date's per-minor table (long superseded), so their
  exact end-of-maintenance day is derived from Elastic's "two-newest-8.x-minors"
  policy + successor-minor GA dates, not a fetched per-minor EOL. Only "EOL well
  before 2026" is certain. Both are flagged UNVERIFIED in the table.
- Action: if an exact 8.8/8.14 EOL date is ever needed for a verdict, fetch
  Elastic's archived support-matrix snapshot (web.archive.org of
  elastic.co/support/eol at the relevant date) — not groundable via `gh`.

## Resolved — 2026-09-15 (NVIDIA GPU Operator)

- **The item asked for a 26.3.2 sift; by the time it ran there was a whole new
  minor.** 26.3.2 is now two releases back — **26.3.3** (2026-06-25) and
  **26.7.0** (2026-08-21) both shipped. Sifted from the NVIDIA release-notes
  page, because the GitHub release body for 26.7.0 is nothing but a link to it.
  That thin-body shape is worth remembering: `gh release view` looks empty here
  and the content lives entirely off-GitHub.
- **26.7.0 changes a host requirement, not an operator setting**: minimum
  supported **containerd moves from 1.8 to 2.0**. The operator cannot satisfy
  that from inside the cluster, so it gates the hop at the node level. Also adds
  Kubernetes 1.37.
- **26.3.3 fixed a regression that silently broke RDMA and NCCL.**
  `MOFED_ENABLED` and `GDS_ENABLED` were defaulting on for the device-plugin
  operand, injecting every ibverbs device node on the host into GPU workload
  containers. Now inferred from the kernel modules actually loaded per node
  (PR #2525). Anything on 26.3.0–26.3.2 running multi-node NCCL wants this.

## Resolved — 2026-09-15 (Mimir chart axis)

- **The chart-vs-app axis item was already done; what was stale was the
  window.** The entry asked to ground Mimir via `Chart.yaml` at chart-release
  tags rather than `releases/latest`. That had already been applied on
  2026-07-21 — the file carries `kubeVersion` per chart and both floor jumps.
  What it did not have was **chart 6.2.0** (appVersion **3.2.0**), read from
  `Chart.yaml` at tag `mimir-distributed-6.2.0`. Added, along with the in-scope
  window moving to 6.2 + prior two.
- **6.2.0 is not a floor event**: `kubeVersion` stays `^1.32.0-0`, so 1.32 gates
  the whole 6.1/6.2 line. Recorded explicitly, because "a new minor" and "a new
  floor" have been the same thing twice running in this chart and assuming it a
  third time would be wrong.
- Carried the operator-visible default change from its CHANGELOG:
  `querier.max_concurrent` default reduced to **8** (#15984), which lowers query
  concurrency for anyone who never set it, plus the `kedaAutoscaling.fallback`
  `ScaledObject` template fix (#15793).

## Resolved — 2026-09-15

### Ceph patch drift and its unverified evidence — both closed

Both Ceph items above are closed together, because the second one (the
House Rule #8 re-flag: "the drift is UNVERIFIED, not merely un-applied — do
NOT bump on the tags evidence") named exactly the right fix, and that fix
has now been done. The prose release notes were read in full rather than the
tag list:

- **Tentacle latest is 20.2.4** (2026-08-19), not 20.2.1. Intervening:
  20.2.2 (2026-06-16), 20.2.3 (2026-08-05). 20.2.4 is a **security release**
  for CVE-2025-30156, CVE-2026-39944, CVE-2026-50152, CVE-2026-54330.
- **Squid latest is 19.2.6** (2026-08-19), not 19.2.3. Intervening: 19.2.4
  (2026-06-01), 19.2.5 (2026-07-14). 19.2.6 carries the same four-CVE hotfix.
- **Reef is unchanged at 18.2.8** and the series is now **archived** upstream.
- **No new known-bad point release** in either window. The skipped list is
  still exactly 18.2.5 / 18.2.6 / 19.2.0 / 19.2.1, and the notes' own warning
  text for each is now quoted in `compat/ceph.md` so a future pass can see
  what the flag rests on.
- **EOL dates replaced with upstream's own estimates**: Tentacle 2027-06-01
  (was a ~2027-11 cadence guess), Squid **2026-10-31** — weeks away, which
  makes Squid a migration source rather than a destination.

One durable trap found and recorded in the file: **`docs.ceph.com/en/tentacle/releases/`
is stale.** It lists only Squid and Reef as active, shows Squid at 19.2.2 and
Reef at 18.2.6, and never mentions Tentacle at all. `/en/latest/`, `/en/squid/`
and `/en/reef/` serve identical current content. Reading the release index
from the branch you are asking about is the natural move and it silently
returns old data.

Also noted, unresolved and left as an upstream inconsistency rather than
guessed at: the releases index gives Reef's end-of-life as 2025-03-20, while
Reef's own page dates its final release 18.2.8 at 2026-03-20, a year later.
Both figures are quoted verbatim; the docs do not explain the gap.

## Resolved — 2026-07-21 (freshen, operator-requested; driver = a live Mimir 5.7.0/2.16.0 air-gapped fleet)

All 19 compat files re-probed and restamped. Findings applied:

- **mimir** — added **chart 6.1.0 / app 3.1.2** (2026-07-16). k8s floor jumps
  again, `^1.29` → **`^1.32`** — second floor move in two minors, so a fleet
  below k8s 1.32 can reach 6.0.x but not 6.1.0. `kafka.extraEnv` removed →
  `kafka.env`. **Default registry is now `docker.io` and the image tag defaults
  to `Chart.AppVersion`** — air-gap image lists must be regenerated, not diffed.
  Added the 5.7 → 5.8 → 6.0 → 6.1 ladder, the one-minor-at-a-time app policy,
  and a warning about the chart-vs-app version-number collision (Grafana's
  "chart 2.x → 3.0" migration guide is from 2022 and unrelated to app 3.0).
  5.7.0 explicitly retained below the tracked window as a live fleet version.
- **cert-manager** — **1.21.0 GA'd 2026-07-08**, so 1.19 is now EOL and the
  k8s floor moves to **1.33**. Recorded three chart-breaking changes (default
  `tokenrequest` RBAC removed; metrics `servicemonitor`/`podmonitor` values
  removed against an `additionalProperties: false` schema, so leftovers fail
  the upgrade; `cert-manager-edit` RBAC narrowed per GHSA-8rvj-mm4h-c258) plus
  two known issues, including a **controller crash-loop** on
  `renewal.policy: Disabled` (#9031).
- **keda** — registry was two minors behind. Added **2.20.0 / 2.20.1** with the
  `events.k8s.io` RBAC action required *before* upgrading, the four scaler
  metadata removals that 2.19 only warned about, and the new CRD validation
  markers that can reject previously-accepted ScaledObjects.
- **rook** — added **1.20** (new minor, 2026-06-02; latest 1.20.2). Ceph CSI
  operator is now mandatory and CSI settings are gone from the operator
  ConfigMap and `rook-ceph` chart; unused CRUSH rules are deleted by default.
  1.18 marked as fallen out of the current+prior-2 window.
- **openebs** — added **LocalPV-LVM 1.9.0/1.9.1** (umbrella 4.5.0/4.5.1) with
  the thin-pool `GetCapacity` fix that changes scheduling maths.
- **rancher** — edition discriminator re-run: **v2.14.3 is Community** (new
  2.14 ceiling); v2.13.7 / v2.12.11 / v2.11.15 are all Prime-docs redirects, so
  those three ceilings are unchanged. The "older minor's top tag is Prime"
  pattern held exactly.
- **harvester** — community patches **1.8.1** (2026-06-29) and **1.7.2**
  (2026-07-07) recorded; noted that 1.7.2 post-dates 1.8.1, so `sort -V` across
  tags does not yield the newest release. 1.9.0-rc2 flagged as not-released.
- **Patch-level restamps:** cilium 1.19.6/1.18.12/1.17.18; rke2
  1.36.2/1.35.6/1.34.9/1.33.13; argo-cd 3.4.5/3.3.12; kyverno 1.18.2; traefik
  3.7.8; harbor 2.15.2 (security fix + Redis→Valkey cache backend); eck 3.4.1;
  gpu-operator 26.3.3.
- **Re-probed, no change (recorded as such rather than silently restamped):**
  tetragon 1.7.0 still latest; zalando postgres-operator v1.15.1 unchanged for
  7 months; gitlab still chart 10.x / app 19.x; ceph k8s axis unchanged by Rook
  1.20; cilium 1.20 is still pre-release only.

**Not applied (stays Open):** the Ceph patch-level drift above — same reason as
2026-05-28, it needs a multi-fetch prose sift of docs.ceph.com release notes to
extract new known-bad point releases, which is not an atomic header edit.

## Resolved — 2026-05-28 (first pass)

### freshen — 2026-06-02 (floor-override pass, operator-directed migration sources)

Operator-requested floor overrides applied (operator runs / migrates clusters off
versions below the rolling-default floor; registry extended **downward** rather than
abstaining). All version numbers grounded via no-candidate enumeration + per-minor
`sort -V` (House Rule #8). Five compat files backfilled, `components.md` floor cells +
headers + `sources.md` rows updated atomically:

- **Harbor floor 2.13 → 2.11.** §2.12 (chart 1.16.x, app v2.12.4, k8s **1.29–1.31**
  — matrix verified exact at chart tag v1.16.4) + §2.11 (chart 1.15.x, app v2.11.2,
  k8s **1.23–1.25** — verified exact at v1.15.2; bundled **PostgreSQL 14→15** one-way
  DB bump is the load-bearing 2.11 hazard). k8s floors read from harbor-helm
  `.github/workflows/integration.yaml` (README only states generic "1.20+").
- **Rancher floor 2.12 → 2.11.** §2.11 (k8s **1.30–1.32**; community ceiling **v2.11.3**
  = the operator's stated migration source, confirmed community). Forward-migration
  framing: what a 2.11 operator must clear before the 2.12 hop (re-import pre-2.11
  direct-`provisioning.cattle.io` clusters, RKE1 sweep, k8s ≥1.31, OIDC AuthConfig
  backup, aggregation-layer requirement origin).
- **ECK floor 3.2.0 → 2.16.** §3.1.0 (k8s 1.29–1.33), §3.0.0 (k8s 1.28–1.32; the
  **2.x→3.0 operator-major hop** — adds Stack 9.0, removes 6.x, 9.0 staged through
  8.18), §2.16.1 (k8s 1.27–1.32, last line managing Stack 6.x). Added the **ES 8.8 /
  8.14 / 8.17** cross-cutting table: all 8.x → every tracked ECK minor (2.16.1→3.4)
  manages them; constraint is ES-side EOL (all three EOL).
- **OpenEBS → refocused to LocalPV-LVM only** (operator-directed, same session).
  Backfilled the umbrella to 4.0, then **re-scoped the file to the LVM engine alone**,
  re-keyed by LocalPV-LVM version (§1.8.0 → §1.5.1) and dropped Mayastor / LocalPV-ZFS /
  LocalPV-Hostpath / LocalPV-Rawfile / cStor / Jiva entirely. Floor = **LVM 1.5** (engine
  umbrella 4.0.1 pins). LVM versions/dates grounded from `openebs/lvm-localpv`; umbrella→LVM
  pin map from umbrella `Chart.yaml` `dependencies:`. `components.md` row → "OpenEBS
  (LocalPV-LVM only) | 1.5"; `cluster-survey.md` detection narrowed (`local.openebs.io`
  CRDs + `lvm-localpv` chart = tracked; other engines → untracked/abstain); `sources.md`
  row → lvm-localpv. Registry count unchanged (19 — OpenEBS is one component, scoped to LVM).
- **Traefik floor 3.5.0 → 2.11.** §3.4–§3.0 ladder + §2.11. §3.0.0 = the **v2→v3
  migration landing** (`traefik.containo.us`→`traefik.io` CRD-group flip, v3 rule
  syntax); §2.11 (v2.11.46, fully EOL) = migration SOURCE → `✗ blocker`. Gateway API
  version grounded per minor (3.0→v1.0.0 … 3.4→v1.2.1) from each tag's `go.mod`.
  Support-window table extended continuous 3.7→2.11.

### freshen methodology hardening — 2026-06-02 (Rancher edition discriminator, third format)

- **Recurrence fix.** The documented edition discriminator (`version-verification.md`
  § Edition discrimination) tested only the release-notes **first line** for the
  Prime-docs redirect and treated its absence as community. Grounding the 2.11 line
  exposed a **third format the first-line test under-detects**: v2.11.4–v2.11.8
  self-declare `"This is a Prime version release"` in the body while keeping an inline
  `# Release vX.Y.Z` first line — so the first-line test wrongly passes them as
  community (it would have returned v2.11.8; `sort -V | tail -1` returns v2.11.14).
  The robust discriminator greps the body for the `"This is a … version release"`
  **self-declaration line**. Fixed in `version-verification.md` (new "Three Rancher
  release-note formats" table + self-declaration-grep bash + verified 2.11 evidence),
  `compat/rancher.md` (§ Community vs Prime 2.11-line caveat + §2.11 edition note),
  and the `sources.md` Rancher row note. Verified-true via independent body enumeration
  of all 15 v2.11.x tags (2026-06-02).



### improve — 2026-05-30 (field upgrade lessons merged: RKE2 1.32 → 1.33)

Merged a field-validated 1.32 → 1.33 upgrade-gotchas briefing into the compat
data — extracting only durable **compat-registry / survey-verdict** signal (the
skill is methodology, "NOT for executing upgrades"), dropping the per-node runbook
and host/hardware-specific firmware noise. Each lesson landed where the skill
consumes it; provenance tagged inline (`field-validated 2026-05-30`):

- **`compat/rke2.md` § 1.33 — etcd 3.5 → 3.6, the headline 1.32→1.33 risk.**
  Grounded vs RKE2 release notes that the 3.6 bump first ships at **v1.33.11**
  (1.33.10 = etcd `v3.5.26-k3s1`, 1.33.11 = `v3.6.7-k3s1`), not at 1.33.0. Added
  the hard **≥ 3.5.26** all-members prereq (zombie-member fix; 1.33.10 already
  satisfies it), mixed-window discipline + storage-version auto-promote, leader-last
  reboot, post-convergence rollback narrowing. Added the benign rke2-server
  restart-storm / transient-NotReady note (rke2#5614, etcd#16287/#19635) with the
  real readiness signal: **OOM on low-RAM swap-off masters**. Refined the § 1.32 /
  § 1.31 cross-minor etcd lines to the grounded 1.33.11.
- **`compat/nvidia-gpu-operator.md` — host-driver/loaded-`.ko` mismatch** after an
  OS package upgrade (rc 18 / `NVML_ERROR_LIB_RM_VERSION_MISMATCH`), device-plugin
  crashloop until reboot, not flagged by `reboot-required`; rc 18 vs rc 9/12
  distinction; assert on `nvidia-smi == 0`; skip non-NVIDIA hosts.
- **`compat/cilium.md` + `compat/tetragon.md`** — kernel **6.17** BPF verifier
  `WARN_ONCE` (`verifier.c:2752`, `cilium-agent`, tc/`cls_bpf`): cosmetic, dataplane
  fine. Cross-ref pair: **not Tetragon** (kprobe/fentry, no `cls_bpf`); a Tetragon
  trigger of the same path is masked because Cilium loads first — validates the
  Tetragon kernel-axis model.
- **`compat/rook.md` — node drain/reboot during a rolling upgrade** (cross-version):
  OSD/mon/mgr on shared master+worker nodes; gate on CephCluster HEALTH_OK + CSI
  unmount; degraded/backfill recovery window; **trap — never gate on Rook PDBs by
  name** (created/deleted dynamically; per-failure-domain `rook-ceph-osd` PDBs).
- **`cluster-survey.md` Phase 1 — server-version display lag** in a partially-upgraded
  control plane: trust per-node `kubectl get nodes` VERSION, not `kubectl version`.

### improve — 2026-05-30 (Tetragon component added; registry 18 → 19)

- **Operator-directed content gap closed:** the registry was missing **Tetragon**
  (`cilium/tetragon`, Cilium's eBPF runtime-security/observability sibling). Added
  end-to-end per the `components.md` "Adding a component" procedure + cross-file
  wiring:
  - NEW `references/compat/tetragon.md` — multi-axis, `release_notes`. The
    load-bearing **kernel axis** (min 4.19; arm64 ≥ 5.10; BTF required;
    `CONFIG_BPF_KPROBE_OVERRIDE` for enforcement; `CONFIG_BPF_LSM` ≥ 5.7 for the
    LSM sensor; ring-buffer default ≥ 5.11; cgroup v1 ≥ 6.11 extra configs) +
    loose k8s axis (no published matrix, chart sets no `kubeVersion:`, chart ==
    app version). Per-minor breaking signal sifted for 1.7 / 1.6 / 1.5.
  - `components.md` — count 18 → 19; new multi-axis stanza under "No published
    matrix"; Cilium-sibling-not-Cilium note.
  - `cluster-survey.md` — detection wired: shares the `cilium.io` CRD group with
    Cilium, so keyed on the `tracingpolicies.cilium.io` CRD + `tetragon` chart /
    DaemonSet; merge note routes Tetragon's kernel axis to the Phase 1
    `KERNEL-VERSION` column; "18 → 19 registry entries".
  - `sources.md` — Tetragon row (FAQ kernel-floor source + chart source + probe).
  - `version-verification.md` — `cilium/tetragon` added to the repo map (kernel
    floor not `gh`-groundable — from `tetragon.io/docs/installation/faq/`).
  - `SKILL.md` — description count + component list (+"Tetragon"); combined
    description+when_to_use = 1496 chars (under the 1536 Dim 1 cap, 40 margin);
    "19-entry registry". `report-format.md` — three "of 18" → "of 19".
- **All versions release-grounded (House Rule #8):** anchored on
  `gh api repos/cilium/tetragon/releases/latest` → `v1.7.0`; minors enumerated +
  `sort -V` (1.7.0 / 1.6.1 / 1.5.0, none newer than `latest`); Chart.yaml read at
  the `v1.7.0`/`v1.6.0`/`v1.5.0` tags (chart == app, no `kubeVersion:`); CRD
  apiVersion (`cilium.io/v1alpha1`, TracingPolicy/TracingPolicyNamespaced/PodInfo)
  confirmed against `pkg/k8s/apis/cilium.io/client/crds/v1alpha1/`. No CVE-patch
  / "fixed-in" claims authored (the body endpoint is contaminated), so nothing
  added to Open.

### freshen — 2026-05-30 (release-grounding pass, House Rule #8)

- **argo-cd fabrication removed** (this session): struck invented `v3.2.10` /
  `v3.2.12` + "CVE fixed in 3.2.10"; the 3.2 line ended at `v3.2.6` (unpatched);
  grounded latest `v3.4.3`. The 2026-05-28 `gh release view`-based pass did NOT
  catch this (it bumped only the 3.4 / 3.3 headers).
- **harbor fabrication flagged**: `§ 2.15` is not a published release
  (`releases/latest` = `v2.14.4`); banner + UNVERIFIED marker added; line is 2.14.x.
- **nvidia version-drift applied**: real latest `v26.3.2` over documented
  `§ 26.3.1` (existence grounded; content sift in Open).
- **15 gh-backed components release-grounded** via `releases/latest`; 12
  confirmed fresh + nvidia existence. See `sources.md` § 2026-05-30.
- **Methodology hardened (recurrence fix):** House Rule #8 + new
  `references/version-verification.md` (anchor on `releases/latest`,
  enumerate-and-derive, never ask "does vX exist?"); wired into SKILL.md,
  cluster-survey.md (Phase 4b), tooling.md, compat/README.md. Root cause: prior
  runs verified via `gh release list` / `gh release view` / `gh api tags` — the
  confirmatory endpoints that let the fabrications through.

### Improve + freshen run — 2026-05-28 (cap-lift + patch-drift pass)

- **Dim 1 trigger-truncation Open item RESOLVED (Pattern 1.4/6.1).** Trimmed
  the air-gap/freshen maintenance prose from `description` (no trigger phrase
  lost): combined `description` + `when_to_use` 1562 → 1486 chars, now under
  the 1536 listing cap with margin. The late-listed load-bearing triggers
  ("Mimir Chart kubeVersion", "ECK against k8s 1.NN", apiserver
  deprecated-API metric) are no longer at truncation risk. Dim 1 7 → 8.
  Supersedes the prior plan to route this to `trigger` mode — a pure deletion
  fit in one improve iteration.
- **Dim 6 survey-step de-duplication (Pattern 6.1, Boris cap-lift).** Collapsed
  the 5-step Survey workflow's procedural steps 2–5 (which duplicated
  `cluster-survey.md` Phases 2–5 verbatim) into a single goal + tool-pointer
  line, keeping the unique change-set taxonomy (step 1) intact. Fixed the
  dangling `Survey workflow § 1` cross-reference in the Verdict format to
  `§ Survey workflow`. SKILL.md 193 → 181 lines. Dim 6 8 → 9.
- **Four in-minor patch-drift findings bumped (Dim 9 freshen).** Verified each
  new patch's release notes carry no new breaking section before stamping:
  - `compat/argo-cd.md`: 3.4 latest v3.4.2 → **v3.4.3** (2026-05-28); 3.3
    latest v3.3.10 → **v3.3.11** (2026-05-28). Both pure bug-fix + dep bump
    (UI CVE-2026-41240).
  - `compat/rancher.md`: 2.14 latest community v2.14.1 → **v2.14.2**
    (2026-05-28). No new breaking item (2.14.2 restates the 2.14.0/2.14.1
    CAAPF-disable + embedded-CAPI-removed signals; floor 1.33–1.35 unchanged).
  - `compat/kyverno.md`: 1.18.0 header now notes **latest patch 1.18.1**
    (2026-05-18). No breaking/migration heading in 1.18.1.
  - `compat/traefik.md`: 3.7.0 header now notes **latest patch 3.7.1**
    (2026-05-11, **CVE-2026-44774** fix). Additive `CrossProviderNamespaces`
    option; Gateway API stays v1.5.1; no removed feature.

### Freshen run — 2026-05-28 (floor-override pass, operator-driven)

Operator-requested floor overrides applied (running versions in the lab cluster
were below the rolling-default floor; freshen extended the registry to cover
them rather than abstaining):

- **RKE2 floor 1.34 → 1.31.** `compat/rke2.md` backfilled with 1.33 / 1.32 /
  1.31 per-minor sections. Key signal captured: snapshot-controller
  v1beta1→v1beta2 break lands at 1.32; etcd 3.5→3.6 lands at 1.33; Traefik
  v2→v3 chart bump lands at 1.32; Cilium 1.18.x is the ceiling for 1.31;
  upstream k8s 1.31 EOL October 2025. Section headers cite latest community
  `+rke2r1` patches (1.32.13+rke2r1, 1.31.14+rke2r1) per house rule #1;
  Prime-only `+rke2r2` rebuilds noted as installable-if-needed context.
- **Harvester floor 1.6.0 → 1.5.0.** `compat/harvester.md` backfilled with
  1.5.0 section: bundled stack (embedded RKE2 v1.32.3+rke2r1, KubeVirt v1.4.0,
  Longhorn v1.8.1, SLE Micro 5.5), management plane (Rancher v2.11.0,
  harvester-ui-extension v1.5.0), community EOL 2025-10-16 (when 1.6.1 Prime
  shipped) AND past SUSE Prime EOM 2025-12-30 → double-EOL warning. RKE1 EOL
  the headline cross-cutting story; no in-place replatforming path.
- **cert-manager floor 1.18 → 1.17.** `compat/cert-manager.md` backfilled
  with 1.17 section: k8s 1.29–1.33 floor, latest patch 1.17.4, upstream EOL
  2025-10-07, RSA hash + structured-log breaking signals, additive
  `keystores.password` CRD note, `ValidateCAA` deprecation hand-off, 1.16→1.17
  floor jump 1.25 → 1.29.
- **Argo CD floor 3.2 → 3.0.** `compat/argo-cd.md` backfilled with v3.1 +
  v3.0 sections: v3.1 k8s 1.31–1.34 (EOL 2026-05-06 at v3.1.16, CVE-2026-42880
  patched in v3.1.15, OCI Beta, SSA migration opt-in landed here); v3.0 k8s
  1.29–1.32 (EOL 2026-02-02 at v3.0.23, seven default flips with PR cites,
  CVE-2026-42880 patched in v3.0.22, ksonnet removal, default JSON logging).
- All four `components.md` cells + per-compat-file headers updated atomically.

### Freshen run — 2026-05-28 (earlier pass)

- **All 18 sources.md rows stamped `Last verified: 2026-05-28`.** 17 fresh
  (latest upstream tag at or within the compat file's "current + prior 2"
  range), 1 in-minor patch drift (Ceph — see Open above). Dim 9 staleness
  cap should lift on the next score: oldest dated row 0 days, no cap.
- **All 18 `min_tracked_version` cells in `components.md` populated from
  per-compat-file headers.** Replaces the `_set by freshen_` literals with
  semver values: RKE2 1.34, Cilium 1.17, cert-manager 1.18, Kyverno 1.16,
  KEDA 2.17, Argo CD 3.2, Harbor 2.13, Traefik 3.5.0, Rook 1.17, Ceph 18.2,
  OpenEBS 4.2, GitLab 8.11, NVIDIA GPU Operator 25.3, Rancher 2.12,
  Harvester 1.6.0, ECK 3.2.0, Zalando 1.13.0, Mimir 5.7. This **resolves**
  the previous Open item "Format drift between compat/README.md template and
  components.md placeholders" — components.md now carries real semvers, the
  README template still uses `<semver>` (which is correct for a template).
- Updated `sources.md` header — replaced "Stamps are intentionally absent on
  the initial structure pass" claim (no longer true) with a cadence note.

### Improve run — 2026-05-28 (prior pass)

- House rule 7 (air-gap) trimmed — Pattern 6.1.
- Verdict format `✓ ready` example collapsed 2→1 — Pattern 6.3.
- Survey workflow step 5 Harvester example removed — Pattern 6.1.
- Added `allowed-tools` frontmatter — Pattern 9.3.
- Two discards (apiserver caveats, source-disagreement decision tree) — both
  Pattern 6.1 violations.

## Run log

### freshen — 2026-06-02 (floor-override pass, operator-directed)

- Input: operator named five migration-source floors to cover — harbor 2.11.1+,
  rancher 2.11.3, eck 2.16.1+, openebs 4.0.1, traefik 2.11.2+ — plus a research ask:
  "which ECK minors support Elasticsearch 8.8 / 8.14 / 8.17?".
- Grounding (House Rule #8): enumerated all five repos' non-prerelease tags with
  **no candidate named**; derived per-minor-line ceilings via `sort -V`. Traefik
  required `--paginate` (2.11 still gets frequent security patches → older 3.0.x
  patches fell past the first 100 results; 3.0 returned empty until paginated).
  Confirmed ceilings: Harbor app v2.12.4 / v2.11.2 (chart v1.16.4 / v1.15.2),
  ECK v3.1.0 / v3.0.0 / v2.16.1, OpenEBS umbrella v4.1.3 / v4.0.1, Traefik
  v3.4.5 / v3.3.7 / v3.2.5 / v3.1.7 / v3.0.4 / v2.11.46. Rancher 2.11 community
  ceiling **v2.11.3** derived by edition discriminator (independently re-verified).
- Sift: 5 parallel research subagents (opus), one per compat file (distinct files,
  no parallel-edit conflict), each handed the pre-grounded version numbers so they
  sifted **prose only** — no version-fabrication surface. Each grounded content
  against authoritative non-`gh-body` sources (harbor-helm integration matrices +
  Chart.yaml at tags; openebs umbrella Chart.yaml dependencies; ECK versioned
  supported-versions pages + supported_versions.go + client-go inference; Traefik
  migrate/v3.md + deprecation/releases.md + per-tag go.mod; Rancher rendered release
  pages + body edition-discriminator). 13 new sections total.
- Driver verification: independently re-ran the Rancher 2.11 edition enumeration
  (exposed the third release-note format); confirmed the two Harbor k8s matrices
  exact at the chart tags; confirmed ECK 3.1.0 date. Header floors cross-checked
  against components.md (all match). No stale floor references elsewhere.
- Methodology recurrence-fix applied (edition discriminator third format) — see
  Resolved. No blind score (freshen is verification-based, not score-based).
- One new Open item: ES 8.8/8.14 exact EOL dates UNVERIFIED (rolled off
  endoflife.date; 8.17 EOL 2025-08-05 verified).
- **Follow-on operator directive (same session): OpenEBS refocused to LocalPV-LVM
  only.** After the umbrella backfill, the operator scoped OpenEBS to the LVM engine.
  `compat/openebs.md` re-keyed by LocalPV-LVM version (§1.8.0 → §1.5.1, floor LVM 1.5),
  all other engines dropped; LVM versions/dates re-grounded from `openebs/lvm-localpv`
  (two tag schemes — `vX.Y.Z` + `lvm-localpv-X.Y.Z`); umbrella→LVM pin map kept as
  context. Wiring updated: components.md row, cluster-survey.md detection (2 rows),
  sources.md row, version-verification.md repo map. See Resolved this pass.

### improve — 2026-05-30 (field upgrade lessons merge)

- Input: `/tmp/rke2-1.32-to-1.33-upgrade-gotchas.md` (first-hand validated 1.32→1.33
  briefing). Scanned for hostnames/IPs/secrets — none present; kept merged content
  generic and stripped cluster-/hardware-specific framing (node counts, HP ProLiant /
  Matrox firmware-quirk noise list, the per-node runbook).
- Triage: 5 of ~13 gotchas were durable compat/survey signal → merged into rke2 /
  nvidia / cilium / tetragon / rook / cluster-survey. The rest (stage-without-restart
  tactic, crictl-preload retries, apt-timing, worker-reboot ease, per-node procedure,
  host firmware noise) are execution-runbook / host-specific → intentionally NOT
  merged (skill is "NOT for executing upgrades").
- Grounded the one load-bearing patch claim (House Rule #8): enumerated rke2 1.33
  tags, read packaged-etcd in the 1.33.10/.11 bodies → 3.6 transition confirmed at
  1.33.11. No fabricated versions; provenance tagged `field-validated 2026-05-30`.
- 6 files edited, no new files. No blind score (field-content merge, not a rubric
  hill-climb).

### improve — 2026-05-30 (Tetragon addition)

- Research: anchored `cilium/tetragon` on `releases/latest` (`v1.7.0`), enumerated
  non-prerelease tags (clean — no candidate version named in any query), read the
  in-repo FAQ at the `v1.7.0` tag for the kernel floor (ground truth, not memory),
  Chart.yaml at 3 tags, CRD manifests for the apiVersion. `gh release view` 401'd
  on v1.6.0/v1.5.0 (transient); bodies read via the tags endpoint instead (content
  sift of already-enumerated tags, not an existence check).
- Mutations: 1 new compat file + 6 wired files (components, cluster-survey,
  sources, version-verification, SKILL, report-format). One logical change (a new
  component), so not split into rubric iterations — the user gave an explicit
  content directive and the registry's own "Adding a component" procedure spans
  these files. Self-consistency check: every "18"-count surface updated to 19;
  historical run-log "18" entries left intact (they correctly record past passes).
- No blind score (content addition against a real gap, not a rubric hill-climb).
  Skill remains at its prior ~90/100 self-score; Dim 1 margin preserved (1496/1536).

### freshen — 2026-05-30 (release-grounding pass)

- Probe: `releases/latest` scalar for 17 gh repos (clean — no candidate version
  named). 15 returned a version; ceph 404 (no `/latest`); gitlab N/A (not
  GitHub); mimir returned the app tag, not the chart `kubeVersion`.
- Findings: 12 fresh · 2 fabrications (argo-cd, harbor) · 1 drift applied
  (nvidia `v26.3.2`) · 3 not-gh-groundable (ceph / gitlab / mimir → Open) · 1
  claim class (per-version "fixed-in" CVE patches) not body-groundable → Open.
- Key methodology finding: gh release-**body**, **list**, and **tags** endpoints
  are confirmatory/contaminated in this environment (rubber-stamp plausible
  fakes; echo in-context version strings). Only `releases/latest` is
  trustworthy. The prior 2026-05-28 freshen relied on the contaminated
  endpoints — root cause of the surviving fabrications. Fixed via House Rule #8
  + `references/version-verification.md`.
- No blind score (freshen is verification-based, not score-based).

### improve + freshen — 2026-05-28 (cap-lift + patch-drift pass)

- Baseline self: 87/100. Lowest dims: Trigger Precision (7), Simplicity (8).
- 3 keeps, 0 discards. Dim 1 7 → 8 (trim under 1536 cap), Dim 6 8 → 9
  (survey-step de-dup), Dim 9 held at 9 (four patch bumps applied; Ceph
  illustrative-patch drift remains the sole carried drift).
- Freshen: 14 refs probed by recon, 11 current, 4 in-minor patch-drift all
  re-confirmed online this pass via `gh release list` + `gh release view`
  (argo-cd v3.4.3/v3.3.11, rancher v2.14.2, kyverno v1.18.1, traefik v3.7.1)
  and applied as header-marker bumps after verifying no new breaking section.
- Ceph 20.3.0 / 19.3.0 re-confirmed present via tags but NOT bumped — needs a
  docs.ceph.com regression-audit WebFetch (multi-step, non-`gh`); stays Open.
- Final self: 90/100.

### freshen — 2026-05-28 (floor-override pass, operator-driven)

- Floor overrides applied per operator instruction: RKE2 1.31, Harvester
  1.5.0, cert-manager 1.17, Argo CD 3.0.
- Backfill: 7 new per-minor sections written across 4 compat files (RKE2 +3,
  Harvester +1, cert-manager +1, Argo CD +2) via 4 parallel subagents.
- Post-pass fixup: RKE2 1.32 / 1.31 section headers corrected to cite latest
  community `+rke2r1` patch per house rule #1 (subagent had labeled latest
  `+rke2r2` patches as the headline; demoted to contextual note since
  Prime-only labels apply to those rebuilds).
- All probed sources reachable.

### freshen — 2026-05-28 (earlier pass)

- Probe budget: 20 (used 18 + 2 follow-ups for Mimir / GitLab / Ceph
  edge-cases).
- Classifications: 17 fresh, 1 version-drift (Ceph, in-minor, low-risk, not
  auto-applied).
- Mutations applied: stamp 18 dates on sources.md, populate 18
  min_tracked_version cells in components.md, refresh sources.md header.
- All probed sources reachable (no broken / 4xx).
- Rate-limit headroom on completion: 5000/5000 (no gh rate-limit pressure
  this pass).

### improve — 2026-05-28 (prior pass)

- Baseline self: 83/100. Baseline blind: 89/100.
- Final self: 84/100. Final blind: 85/100.
- 6 iterations: 4 keeps + 2 discards.
- Expected score after freshen (Dim 9 cap lift): self → ~86, blind → ~88-89.
