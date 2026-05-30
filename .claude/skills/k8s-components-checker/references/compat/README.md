# compat/ — per-component compatibility signal

One file per registry component. Each file carries **sifted** highlights from
whatever authoritative source the component publishes:

- Vendor support matrix pages (Cilium, cert-manager, Argo CD, NVIDIA GPU Operator, ECK)
- Official documentation (Harbor, GitLab, OpenEBS, Kyverno, KEDA)
- GitHub release notes (Traefik, Zalando, RKE2, Rancher)
- Wiki pages with per-version compatibility tables (Harvester)
- Helm `Chart.yaml` `kubeVersion:` constraints at release tags (Grafana Mimir)
- Cross-references from another component's release notes (Ceph from Rook)

The `truth_source_type` field in `references/components.md` says where the
*primary* signal lives. Freshen probes all sources listed in
`references/sources.md` for the component and reconciles findings — if the
matrix page says one thing and a recent release note contradicts it, the file
calls out the discrepancy with both citations rather than silently picking one.

These files are **read at use time** during a survey. They are **maintained at
freshen time** by `skill-improver freshen`.

## File shape

```markdown
# <component-name> — compat (sifted from <primary source type>)

- **Primary source:** <URL>
- **Secondary sources:** <URLs, if any>
- **Truth source type:** `published_matrix` | `release_notes` | `chart_metadata`
- **Axis type:** `single` | `multi`
- **min_tracked_version:** <semver>     # default = current + prior 2 minors; operator override sticks
- **Last sifted:** YYYY-MM-DD            # stamped by `skill-improver freshen`
- **Last release-verified:** YYYY-MM-DD  # when version numbers were grounded vs `gh` releases (House Rule #8); omit while numbers are UNVERIFIED

## <version 1.X.0>

- **k8s floor:** <range, e.g. `1.27 – 1.31`>
- **Breaking:** <one-liner per breaking change; cite source if non-obvious>
- **CRD migrations:** <CRD version bumps that require conversion or manual steps>
- **Upgrade ordering:** <"must upgrade X before this"; "must upgrade this before Y">
- **Deprecations:** <APIs/flags/CRDs deprecated, with removal version if announced>
- **Cross-component:** <e.g. for Rook: "supports Ceph 18.2.x, 19.x"; for Ceph: "requires Rook ≥ 1.14">
- **Notable:** <anything else that would change a compat verdict>

## <version 1.Y.0>
...
```

Order versions newest → oldest. Trim entries below `min_tracked_version`.

## Sifting discipline

Include only what affects a compat verdict. Exclude:

- Feature additions that don't move the k8s floor and don't deprecate anything.
- Bug fixes that don't change observable behavior.
- Refactors, doc updates, internal cleanups.
- Performance improvements without API/floor changes.

If a section has no signal for a version, omit it. An empty `## <version>`
block is acceptable — the version is tracked, nothing relevant changed. Do not
fabricate signal to fill sections.

## Version grounding — no invented releases

Specific version numbers are the #1 fabrication risk in these files. Sifting
release notes into prose invites plausible-but-nonexistent patches — this skill
once wrote Argo CD `v3.2.10` / `v3.2.12` and "CVE fixed in 3.2.10" (the 3.2 line
ended at `v3.2.6`), and Harbor `## 2.15` while `releases/latest` was `v2.14.4`.

Rules (full protocol: `references/version-verification.md`, House Rule #8):

- Distinguish **support windows** (k8s minor floors — durable, the registry's
  job) from **version specifics** (latest patch, newest minor, "CVE fixed in
  vX.Y.Z" — volatile, must be release-grounded).
- Only write a version number that appears in a **freshly fetched, uncontaminated**
  release listing. Derive "latest patch of minor X" by enumeration
  (`… | sort -V | tail -1`), never by extrapolation.
- **Never name a candidate version in a verification query** — existence / list /
  per-tag queries get rubber-stamped (plausible fakes return 200; the list echoes
  back versions named in the command). Anchor on `releases/latest`; reject newer.
- Ground every "fixed-in vX.Y.Z" against that release's own notes
  (`gh release view <tag>`). If you cannot ground it, **omit the claim**.
- Stamp `Last release-verified:` when numbers were checked against `gh`; leave it
  off (and mark the numbers `UNVERIFIED`) when they were not.

## Multi-source reconciliation

When a component publishes both a matrix page and release notes (most do):

1. The matrix establishes the k8s-version support window.
2. Release notes refine with breaking-change, CRD-migration, deprecation, and
   ordering signal that the matrix omits.
3. If they disagree on a k8s minor: call out the discrepancy in the file with
   both citations. Do not silently pick one.

For `chart_metadata` components: `Chart.yaml`'s `kubeVersion:` is canonical for
the chart-version → k8s-version axis; release notes of the underlying app are
secondary for app-level breaking changes.

## Citation

When a verdict references a finding from one of these files, the source line
points at the exact `## <version>` block:

```
source: references/compat/cilium.md § 1.17.0
```

That citation is the contract — the line must exist, with the named signal.

## Maintenance

Files are touched by:

- `skill-improver freshen <skill>` — probes all sources, updates `Last sifted`,
  adds new versions, trims rows below `min_tracked_version`. Respects per-row
  operator overrides. **Must ground every version number against real releases
  (`references/version-verification.md`): enumerate-and-derive, never extrapolate
  a patch line, and never write a release it hasn't confirmed.**
- The operator, by hand, when adding a `min_tracked_version` override or when
  documenting a finding that freshen missed.

Do not hand-edit during a survey. Surveys are read-only against this directory.
