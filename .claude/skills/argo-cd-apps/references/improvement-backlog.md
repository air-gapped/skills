# Improvement Backlog — argo-cd-apps

Carries open ceiling findings across skill-improver runs. Each entry: title,
affected dim, file:line pointer (or file-set), why it couldn't be applied in
one iteration this run, enough context for a future loop to act on.

## Resolved — 2026-09-15 (four carried items: one shipped, two closed on evidence, one re-stated)

- **Item 4 (no `scripts/` directory) — DONE.** Shipped
  `scripts/check-serversidediff-exposure.py`. The entry called it "author work",
  which is effort, not an absent thing, so it never qualified as a blocker. What
  it asked for was also too narrow: checking only for
  `IncludeMutationWebhook=true` passes a cluster exposed to CVE-2026-45737,
  which needs no annotation. The shipped script does both — text scan plus a
  per-line version floor — and refuses to print a pass for a clean manifest scan
  when no `--version` was given.
  - Scans as **text** rather than parsed YAML deliberately: the annotation must
    be caught inside Helm templates, kustomize patches and ApplicationSet
    `template:` blocks, none of which parse standalone.
  - `--selfcheck` asserts all six per-line boundaries plus the 3.4-specific case
    where CVE-2026-42880 never applied, so the floors cannot silently rot.
  - Exit 1 on exposure, so it drops into CI unchanged.
- **Item 3 (`paths:` frontmatter) — CLOSED, decided against, on evidence.** The
  entry deferred to "author judgment". The docs settle it without a judgement
  call: `paths` is real and supported, and it means *"when set, Claude loads the
  skill automatically **only** when working with files matching the patterns"*
  (code.claude.com/docs/en/skills.md, frontmatter reference, read 2026-09-15).
  This skill's `when_to_use` is explicitly conversational — "even if they don't
  say 'Argo CD' explicitly" — so `paths` would silence the exact trigger the
  description is built around. The suggestion and the skill's trigger design
  contradict each other; adding it would trade a real recall loss for a
  frontmatter-completeness point. **Do not add it.** Reopen only if the skill is
  ever narrowed to file-editing work.
  - Fleet context: **0 of 70 skills** here use `paths`. That is now a deliberate
    position rather than an oversight.
- **Item 2 (second-person sweep of `references/`) — DROPPED, not deferred.** Its
  blocker was that "cost-benefit is marginal" — a judgement, and judgements do
  not belong in Open. Making it: ~1% density across 5326 lines, in reading-flow
  contexts rather than instructional voice, in `references/`, which costs nothing
  until something reads it. Not worth the churn. A future pass may re-open it
  with a reason; carrying it unresolved for four months was the failure.
- **Item 1 (relocate canonical YAML) — KEPT, blocker re-stated.** It read as
  blocked on being a three-edit multi-file restructure. That is effort and does
  not qualify. The real blocker is that the inline placement is a *deliberate*
  author choice for fast reach, so overriding it needs the blind A/B comparator
  — a paid run nobody has authorised. Now recorded that way, with what unblocks it.

## Resolved — 2026-09-15 (the stated remediation was inside the follow-up advisory)

- **The skill told operators to reach v3.3.9 / v3.2.11. Both are affected by
  CVE-2026-45737.** That advisory says it outright — "the original fix for
  GHSA-3v3m-wc6v-x4x3 is incomplete" — and lists `3.2.0 – 3.2.11`, `3.3.9` and
  `3.4.1` as affected. Real floor: **v3.4.2 / v3.3.10 / v3.2.12**, confirmed by
  the `fix(gitops-engine): apply HideSecretData to server-side diff results`
  commit in the v3.3.10 and v3.4.2 release notes.
- **The second CVE is not a narrower rerun of the first, and the old mitigation
  does not cover it.** CVE-2026-42880 needs `IncludeMutationWebhook=true`;
  CVE-2026-45737 needs no compare-option at all. The first fix masked top-level
  Secret data but not the copy inside
  `kubectl.kubernetes.io/last-applied-configuration`, which any Secret
  previously written by client-side apply still carries — `HideSecretData`
  rewrote only the `live` object while server-side dry-run returns the
  annotation on `predictedLive` too. So "strip the annotation" closes the
  critical and leaves the medium open, and a cluster that never set the
  annotation was still exposed.
- **The wrong floor had propagated into three more places**, each of which would
  have re-asserted it: the knowledge claim ("patched in v3.3.9 and v3.2.11"),
  and two eval assertions — one asserting "3.3.9 or later" as the expected
  floor, the other stating "CVE-2026-42880 patched in 3.3.8+", where 3.3.8 is
  inside the critical's own range. A skill that grades itself against a stale
  floor will keep scoring the stale answer correct.
- **CVE-2026-45738** (high, 2026-05-13) recorded alongside: stored XSS in
  application link annotations escalating an Application editor to admin.
  Affects `< 3.0.0` only, so every 3.x is clear — it matters only when advising
  someone still on 2.x.
- Third instance this pass of one defect class: a skill naming a remediation
  target that a later advisory lists as affected. The other two were
  `harvester-upgrade` and the Harvester entry in the components registry.

## Resolved — 2026-07-21 (freshen)

- **Rebased the version picture.** Latest stable v3.4.3 → **v3.4.5**
  (2026-07-09); maintenance v3.3.11 → **v3.3.12** (2026-06-18); v3.2.12 and
  v3.1.16 also active.
- **Documented v3.5 while it is still in RC** (rc1 2026-06-16, rc2 2026-07-01),
  read from `docs/operator-manual/upgrading/3.4-3.5.md` **at tag v3.5.0-rc2** —
  a release artifact, whereas the 2026-05-06 authoring pass only had the
  in-development version on `main`. Documented ahead of GA deliberately: the
  headline is a **Helm 4.2.0 upgrade that breaks plain-HTTP OCI registries**,
  which is a planning problem, not an upgrade-day problem. Specifically:
  dependency repos on plain-HTTP OCI now need explicit registration where Helm
  v3 handled them transparently, and combining
  `--insecure-skip-server-verification` with `--insecure-oci-force-http` makes
  Helm v4 silently drop `--plain-http` with **no workaround upstream**. Also
  captured React 19 for UI extensions, the `EventList` gRPC type change (CLI
  unaffected, REST unaffected, generated gRPC/OpenAPI clients affected),
  impersonation extending to all server operations with a required-verbs table,
  and SSH `known_hosts` moving to `argocd-ssh-known-hosts-cm` for
  credential-less repos.
- **Closed a recorded ambiguity in "Note on conflicting sources".** It said to
  treat impersonation-on-server-operations as a 3.4 change "unless GA notes say
  otherwise", reasoning from PR merge dates. Resolved by reading the *shipped
  docs* instead: `3.3-3.4.md` at tag **v3.4.5** does not mention impersonation
  at all, while `3.4-3.5.md` at **v3.5.0-rc2** documents it with a full RBAC
  table. It is a **3.5** change. Also corrected the arithmetic in that note —
  PR #26898 (2026-04-02) landed *after* v3.4.0-rc1 (2026-03-16), not four weeks
  before it. Reasoning from merge dates was the error; the release artifact is
  the authority.
- **Security advisories re-probed: genuinely no change.** Nothing newer than the
  two 2026-05-13 entries. Recorded as a verified non-event rather than left
  ambiguous.
- **Added a method note** to the currency section: enumerate
  `gh release list -R argoproj/argo-cd --limit 25` and reason per minor line;
  do not read `releases/latest`, which GitHub marks by recency, so a patch on an
  older line can outrank a newer minor.

**Not attempted:** both structural Open items below (SKILL.md YAML relocation,
second-person leakage) — unchanged reasoning, and this pass's budget went to the
v3.5 material.

## Resolved — 2026-09-15 (freshen: v3.4/v3.5 re-baseline)

The skill targeted "v3.4.x latest v3.4.5" and called v3.5 an RC. v3.5.0 shipped
2026-08-04 and both lines are now at .9 / .3 (2026-09-14). Re-baselined, and
three upgrade hazards recorded that a version bump alone would have hidden:

- **An open Secret data-loss regression** (#29644, filed 2026-09-09).
  `RespectIgnoreDifferences=true` with a key-level `ignoreDifferences` rule on a
  Secret rendering `stringData` drops the whole `data` map on sync. Regression
  from #27136, cherry-picked into **both** 3.4 and 3.5, with a reporter unit
  test passing on v3.4.4 and failing on v3.5.2. Self-heal then re-applies the
  key-less manifest indefinitely. This is the reason the re-baseline is not just
  a number change.
- **Helm 4 rendering differences** (#29068) — v3.5 bundles Helm 4.2.x whose
  null coalescing changed, so charts can emit explicit `null` fields with no
  edit. Diff a render across the bump.
- **Two further open 3.5 regressions**: `valueFiles` globs stopped matching
  (#29069), in the release that advertised wildcard support; and `oci://` plus
  `manifest-generate-paths` flaps apps to Unknown (#29058).

Also recorded: the 3.4→3.5 breaking list (GnuPG → Source Integrity, impersonation
widened past sync, gRPC `EventList` type change, React 19 UI extensions,
`--repo-server-strict-tls` deprecation); the v3.4.1 ApplicationSet Cluster
Generator move to `argocd.argoproj.io/kubernetes-version` in `vMajor.Minor.Patch`
form; and corrected feature maturity — Source Hydrator and impersonation both
reached **Beta** in v3.5.0, Progressive Sync has been Beta since **v3.3.0**, and
none of them is GA.

Two things checked and found already correct, so left alone: the advisory list
already named CVE-2026-45737 and CVE-2026-45738 alongside CVE-2026-42880, and no
advisory has been published since 2026-05-13. There is also no `v3.4.0` tag —
that line starts at v3.4.1, which its own release notes state.


## Open

### 1. Inline canonical YAML in SKILL.md — relocate to references (carried 2026-05-29)

- **Blocked on:** a paid blind A/B run nobody has authorised. NOT on effort.
- **Dim 2** (Progressive Disclosure) / **Dim 6** (Simplicity). `SKILL.md`
  § Canonical Application and § Canonical ApplicationSet — ~98 body lines that
  load on every trigger.
- **The blocker is the measurement, not the edit.** The move is three edits
  across two files (`references/application.md:5` says the example is "not
  repeated here", so it must be moved and that pointer rewritten) — mechanical,
  and by itself no reason to defer. What is absent is evidence: the author
  *deliberately* chose fast reach, putting the highest-traffic authoring surface
  at the top of the body. Overriding a deliberate choice needs the blind A/B
  comparator, which costs money and is optional work under skill-improver's
  "state the spend before a fan-out" rule.
- **To unblock:** price a 3-comparator A/B (baseline vs lean variant), get a
  yes, run it. `REGRESSED` or `NO CHANGE` closes this permanently.
- Estimated lift if kept: Dim 2 8→9, Dim 6 7→8; SKILL.md ~350 → ~250 lines.
## Resolved this pass (2026-05-29 freshen + improve)

- **CVE-2026-42880 patched-version matrix was WRONG** — claimed patched `v3.3.8 / v3.2.10 / v3.1.15`; actual is `v3.3.9 / v3.2.11` per GHSA-3v3m-wc6v-x4x3 (advisory 2026-05-01), and v3.3.8 predates the advisory. Corrected in `SKILL.md` gotcha #1, `references/projects-rbac.md` §8, `references/version-changes.md` CVE-callouts. Security-critical: the old text would have left an operator on an unpatched build (iter 1).
- **Version-currency stale** — "v3.3.9 (latest stable) / v3.4 (RC)" corrected to "v3.4.x GA, latest stable v3.4.3 (2026-05-28); v3.3 maintenance latest v3.3.11" in `SKILL.md` intro + `references/version-changes.md` currency note + v3.4 section header (iter 2).
- **Two post-authoring CVEs missing** — added CVE-2026-45737 (medium, SSD Secret extraction via sensitive annotations, GHSA-rg3g-4rw9-gqrp, 2026-05-13) and CVE-2026-45738 (high, stored XSS dev→admin via Application link annotations, GHSA-h98r-wv3h-fr38, 2026-05-13) to `references/version-changes.md` CVE-callouts and `references/projects-rbac.md` §8 secrets section (iter 3).
- **Top-of-file ToC missing on the four reference files >100 lines** — added a verified `## Contents` block (anchors generated from `grep -n '^## '` headings) to `references/sync.md` (12 sections), `references/troubleshooting.md` (12 + appendix), `references/repo-layout.md` (12 + citation index), `references/applicationset.md` (7 sections). Satisfies the rubric reference-depth ToC rule for partial reads (iter 4, Dim 2).
- **sources.md restamped 2026-05-29** — freshen-pass header rewritten with the probe findings; Releases + Security-advisories + local-clone rows re-stamped `Last verified: 2026-05-29` with the v3.4.3 pin and the four CVEs (freshen).

## Prior run — Final scores (2026-05-06 run)

- Baseline self: 73 / blind: 77
- Final self: 85 / blind: 89
- Delta: +12 self, +12 blind
- 5 iterations, all kept (0 discards), 5 different categories (spec / content / style / portability / simplification)
- No 2+ gap dimensions on final blind check
