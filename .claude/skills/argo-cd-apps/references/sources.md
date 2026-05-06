# Sources — Argo CD application authoring

Dated index of authoritative URLs and the local clone the skill cites. Freshen
Mode reads this file, probes each row, and stamps `Last verified` (and
`Pinned` where applicable). The oldest `Last verified:` caps Dim 9 of the
quality rubric.

## Convention

Each row has `Source`, `URL`, `What it contains`, `Last verified` (YYYY-MM-DD),
`Pinned` (version, git ref, or commit SHA — optional). Rows the author wants
freshen to skip get `<!-- ignore-freshen -->` at the end.

## Most recent freshen pass: 2026-05-06

The skill was authored on 2026-05-06 against a fresh local clone of
`argoproj/argo-cd` at commit `4d02fc2f5` (2026-05-05). All sources were
verified at authoring time; no entries are stale.

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
| Upgrading 3.3 → 3.4 | https://argo-cd.readthedocs.io/en/stable/operator-manual/upgrading/3.3-3.4/ | Breaking changes in v3.4 (RC) | 2026-05-06 | v3.3.9 |

## GitHub

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| argoproj/argo-cd | https://github.com/argoproj/argo-cd | Source repo | 2026-05-06 | main @ 4d02fc2f5 |
| Releases | https://github.com/argoproj/argo-cd/releases | Canonical changelog (the in-repo `CHANGELOG.md` is stale, last entry v2.4.8 from 2022) | 2026-05-06 | v3.3.9 |
| Security advisories | https://github.com/argoproj/argo-cd/security/advisories | CVE-2026-42880 (`IncludeMutationWebhook=true` Secret leak), CVE-2025-55190, CVE-2024-31990 | 2026-05-06 | — |
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
