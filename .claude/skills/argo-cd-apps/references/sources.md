# Sources — Argo CD application authoring

Dated index of authoritative URLs and the local clone the skill cites. Freshen
Mode reads this file, probes each row, and stamps `Last verified` (and
`Pinned` where applicable). The oldest `Last verified:` caps Dim 9 of the
quality rubric.

## Convention

Each row has `Source`, `URL`, `What it contains`, `Last verified` (YYYY-MM-DD),
`Pinned` (version, git ref, or commit SHA — optional). Rows the author wants
freshen to skip get `<!-- ignore-freshen -->` at the end.

## Most recent freshen pass: 2026-07-21

Re-probed releases, security advisories, and the shipped upgrade docs via `gh`.

- **Releases moved:** latest stable **v3.4.5** (2026-07-09, was v3.4.3);
  maintenance **v3.3.12** (2026-06-18, was v3.3.11); v3.2.12 and v3.1.16 also
  active. **v3.5 entered RC** — v3.5.0-rc1 (2026-06-16), v3.5.0-rc2
  (2026-07-01), not GA.
- **Security: no change.** `gh api repos/argoproj/argo-cd/security-advisories`
  returns nothing newer than the two 2026-05-13 entries already recorded
  (CVE-2026-45737 / GHSA-rg3g-4rw9-gqrp medium, CVE-2026-45738 /
  GHSA-h98r-wv3h-fr38 high). The advisory rows are current as written.
- **v3.5 breaking changes captured** from
  `docs/operator-manual/upgrading/3.4-3.5.md` read at tag **v3.5.0-rc2** — a
  release artifact rather than `main`, which is what the 2026-05-06 authoring
  pass had. Headline: **Helm upgraded to 4.2.0**, so plain-HTTP OCI registries
  now need `--insecure-oci-force-http`, OCI *dependency* repos must be
  registered explicitly (transparent under Helm v3), and setting both
  `--insecure-skip-server-verification` and `--insecure-oci-force-http` makes
  Helm v4 silently drop `--plain-http` with **no workaround**. Also React 19 for
  UI extensions, an `EventList` gRPC type change, impersonation extended to all
  server operations, and SSH `known_hosts` now read from
  `argocd-ssh-known-hosts-cm` for credential-less repos.
- **Resolved a recorded ambiguity.** The "Note on conflicting sources" entry
  said to treat impersonation-on-server-operations as 3.4 "unless GA notes say
  otherwise". Checked both shipped docs: `3.3-3.4.md` at v3.4.5 does not mention
  impersonation at all; `3.4-3.5.md` at v3.5.0-rc2 documents it with an RBAC
  table. **It is a 3.5 change.**
- **Method note:** enumerate `gh release list`, don't read `releases/latest` —
  GitHub marks latest by recency, so a patch on an older line can outrank a
  newer minor.

## Prior freshen pass: 2026-05-29

The skill was authored on 2026-05-06 against a fresh local clone of
`argoproj/argo-cd` at commit `4d02fc2f5` (2026-05-05). Freshen pass on
2026-05-29 re-probed releases and security advisories via `gh`: v3.4 has
GA'd (latest stable **v3.4.3**, 2026-05-28; v3.3 maintenance latest
**v3.3.11**), CVE-2026-42880 patched in **v3.3.9 / v3.2.11**
(GHSA-3v3m-wc6v-x4x3, advisory 2026-05-01, NOT the previously recorded
v3.3.8), and two new advisories landed 2026-05-13 (CVE-2026-45737 medium /
GHSA-rg3g-4rw9-gqrp, CVE-2026-45738 high / GHSA-h98r-wv3h-fr38). Rows
re-confirmed online this pass carry `Last verified: 2026-05-29`; rows not
re-probed (readthedocs doc pages, adjacent skills) keep their 2026-05-06
stamp.

## Local clone (primary source of truth)

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| argoproj/argo-cd | https://github.com/argoproj/argo-cd | Full Argo CD source + docs/ tree (user-guide, operator-manual, applicationset/) — primary source for every cited file path in references/. Cited paths are relative to repo root (e.g. `docs/user-guide/best_practices.md`); access via local clone or `gh api repos/argoproj/argo-cd/contents/<path>`. | 2026-05-06 | main @ 4d02fc2f5 (2026-05-05) |

## Official documentation

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| Argo CD docs (stable) | https://argo-cd.readthedocs.io/en/stable/ | User guide, operator manual, upgrading guides — same content as local clone's docs/ tree | 2026-05-06 | v3.3.9 |
| Application spec | https://argo-cd.readthedocs.io/en/stable/operator-manual/application.yaml | Canonical Application CR YAML — every spec field with comments | 2026-05-06 | v3.3.9 |
| ApplicationSet spec | https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset.yaml | Canonical ApplicationSet CR YAML | 2026-05-06 | v3.3.9 |
| AppProject spec | https://argo-cd.readthedocs.io/en/stable/operator-manual/project.yaml | Canonical AppProject CR YAML | 2026-05-06 | v3.3.9 |
| Best practices | https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices.md | Argo's own 5-reason config-vs-source repo split, immutable-revision rule, replicas/HPA pattern | 2026-05-06 | v3.3.9 |
| Sync options | https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options.md | Every `syncPolicy.syncOptions` value | 2026-05-06 | v3.3.9 |
| Sync waves | https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves.md | Wave annotation, phase ordering | 2026-05-06 | v3.3.9 |
| Resource hooks | https://argo-cd.readthedocs.io/en/stable/user-guide/resource_hooks.md | All 7 hook types, all 3 delete policies | 2026-05-06 | v3.3.9 |
| Cluster bootstrapping | https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping.md | App-of-apps pattern; line 7 explicitly recommends ApplicationSets first | 2026-05-06 | v3.3.9 |
| ApplicationSet generators | https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Git.md | Git generator (and siblings: List, Cluster, Matrix, Merge, SCMProvider, PullRequest, ClusterDecisionResource, Plugin) | 2026-05-06 | v3.3.9 |
| Progressive Sync | https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Progressive-Syncs.md | RollingSync strategy, formal Beta in v3.3 | 2026-05-06 | v3.3.9 |
| Source Hydrator | https://argo-cd.readthedocs.io/en/stable/user-guide/source-hydrator.md | DRY/HYDRATED source flow — Alpha as of v3.4 | 2026-05-06 | v3.3.9 |
| AppProject specification | https://argo-cd.readthedocs.io/en/stable/operator-manual/project-specification.md | AppProject field-level reference | 2026-05-06 | v3.3.9 |
| Sync impersonation | https://argo-cd.readthedocs.io/en/stable/operator-manual/app-sync-using-impersonation.md | `destinationServiceAccounts` — Beta in v3.4 | 2026-05-06 | v3.3.9 |
| Application in any namespace | https://argo-cd.readthedocs.io/en/stable/operator-manual/app-any-namespace.md | Tenant-namespace Applications | 2026-05-06 | v3.3.9 |
| Feature maturity | https://argo-cd.readthedocs.io/en/stable/operator-manual/feature-maturity.md | Alpha / Beta / Stable status per feature | 2026-05-06 | v3.3.9 |
| Upgrading 3.2 → 3.3 | https://argo-cd.readthedocs.io/en/stable/operator-manual/upgrading/3.2-3.3/ | Breaking changes in v3.3 | 2026-05-06 | v3.3.9 |
| Upgrading 3.3 → 3.4 | https://argo-cd.readthedocs.io/en/stable/operator-manual/upgrading/3.3-3.4/ | Breaking changes in v3.4 (now GA). Confirmed 2026-07-21 at tag v3.4.5: **does not mention impersonation** | 2026-07-21 | v3.4.5 |
| Upgrading 3.4 → 3.5 | https://github.com/argoproj/argo-cd/blob/v3.5.0-rc2/docs/operator-manual/upgrading/3.4-3.5.md | Breaking changes in v3.5 (RC). Helm 4.2.0 + plain-HTTP OCI, React 19 UI extensions, `EventList` gRPC type, impersonation on all server operations, SSH known_hosts from ConfigMap | 2026-07-21 | v3.5.0-rc2 |

## GitHub

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| argoproj/argo-cd | https://github.com/argoproj/argo-cd | Source repo | 2026-05-29 | main @ 4d02fc2f5 |
| Releases | https://github.com/argoproj/argo-cd/releases | Canonical changelog (the in-repo `CHANGELOG.md` is stale, last entry v2.4.8 from 2022). Latest stable **v3.4.5** (2026-07-09); v3.3 maintenance **v3.3.12** (2026-06-18); v3.2.12, v3.1.16 active. **v3.5.0-rc2** (2026-07-01) in RC, not GA | 2026-07-21 | v3.4.5 |
| Security advisories | https://github.com/argoproj/argo-cd/security/advisories | CVE-2026-42880 Secret leak patched v3.3.9/v3.2.11 (GHSA-3v3m-wc6v-x4x3, 2026-05-01); CVE-2026-45737 medium SSD Secret extraction (GHSA-rg3g-4rw9-gqrp, 2026-05-13); CVE-2026-45738 high stored XSS dev→admin (GHSA-h98r-wv3h-fr38, 2026-05-13); CVE-2025-55190; CVE-2024-31990. **Re-probed 2026-07-21: no new advisories since 2026-05-13** | 2026-07-21 | — |
| gitops-engine | https://github.com/argoproj/gitops-engine | Sync engine library — `pkg/sync/sync_tasks.go` carries the canonical kind-ordering for sync waves | 2026-05-06 | — |

## Blog & community

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| blog.argoproj.io | https://blog.argoproj.io/ | Official Argo project blog with release announcements (note: WebFetch hit TLS cert chain errors during research; access via WebSearch site: queries works) | 2026-05-06 | — |

## Adjacent skills referenced

| Source | What it contains | Last verified |
|--------|------------------|---------------|
| `helm` skill | Helm chart authoring (Helm 4 SSA, OCI digest, helpers) — this skill assumes Helm authoring competence | 2026-05-06 |
| `kubefwd` skill | Bulk Kubernetes service port-forwarding for Argo CD UI/API access | 2026-05-06 |
| `gh-cli` skill | GitHub CLI for fetching argo-cd releases, security advisories, PRs (canonical changelog source) | 2026-05-06 |

## Search queries for future research

When freshening Argo CD specifics, these queries are productive:

```
gh release view <tag> --repo argoproj/argo-cd --json body
gh api repos/argoproj/argo-cd/security-advisories
site:blog.argoproj.io argo cd <year>
site:argo-cd.readthedocs.io <feature>
"argo cd" "<feature>" beta promotion
```
