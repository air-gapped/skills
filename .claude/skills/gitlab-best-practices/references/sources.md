# Sources — gitlab-best-practices

Per-URL index backing this skill's factual claims. Freshen Mode probes every
row and rewrites the stamp below; rows it could not reach carry an inline
exception note instead.

**Freshened: 2026-08-29**

Chart and app versions enumerated unfiltered from the Helm repo index; the
required-stop list read from its machine-readable source; deployment-level
claims checked against a live RKE2 install carried from GitLab 18.7.0 to
19.3.1 across four hops on the same day. Claims tagged **[A]** in the
reference files were reported by a source but not independently re-verified.

## Primary sources — verified directly

| Ref | URL | Grounds |
|---|---|---|
| `config/upgrade_path.yml` | https://gitlab.com/gitlab-org/gitlab/-/raw/master/config/upgrade_path.yml | required stops, minor-level only; **no 19.0 entry**; the "x.2/x.5/x.8/x.11 from 17.5" comment. **Re-verified 2026-08-29** |
| Helm repo index | https://charts.gitlab.io/index.yaml | chart↔app mapping and the chart-major = app-major − 9 offset. **Pinned: chart 10.3.1 / app v19.3.1 latest, 2026-08-29** |
| `doc/install/requirements.md` | https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/install/requirements.md | PG min/max per GitLab major (19.x is 17.x/17.x); the required-extensions table incl. `amcheck` at 18.4 |
| GitLab 19 changes | https://docs.gitlab.com/update/versions/gitlab_19_changes/ | PG 17 mandatory "Affects: All installation methods"; Redis 6 removed; Spamcheck removed; registry `s3_v2`; NGINX → Gateway API |
| Chart 10.0 release notes | https://docs.gitlab.com/charts/releases/10_0/ | bundled PostgreSQL / Redis / MinIO removed; external deps become required |
| PostgreSQL extensions | https://docs.gitlab.com/administration/postgresql/extensions/ | defers to requirements.md — the page itself carries no table (a null result worth recording) |
| Registry S3 driver | `registry/storage/driver/s3-aws/s3.go` @ `v4.40.2-gitlab` | legacy `s3` name registered onto the v2 factory — `s3_v2` is not a breaking change |
| Live install | chart 9.7.0 → 10.3.1 / GitLab 18.7.0 → 19.3.1, RKE2 | default flips, render behaviour, verification sequence, Sidekiq HPA measurements, restore rehearsal |
| Gitaly on Kubernetes | `doc/administration/gitaly/kubernetes.md` @ master | GA at 18.11 standalone-only; the "single point of failure by design" quote; the SPoF mitigation set |
| Praefect index | `doc/administration/gitaly/praefect/_index.md` @ master | Gitaly Cluster on Kubernetes **beta**, introduced 19.1; snapshot backups unsupported for Cluster |
| Reference architectures | `doc/administration/reference_architectures/_index.md` @ master | Cloud Native Hybrid scope; 2,000-user floor; the zero-downtime "not supported" claim and its stale citation |
| Zero-downtime (Omnibus) | `doc/update/zero_downtime.md` @ master | scoped to the Linux package only |
| **Chart upgrade doc** | `charts/gitlab` → `doc/installation/upgrade.md` @ master | the chart's **own** zero-downtime procedure and required rollout settings — contradicts the reference architectures |
| Chart source @ master | `gitlab-org/charts/gitlab` (shallow clone) | per-component PDB templates and replica defaults; `edition: ee` default |
| Epic 8903 | https://gitlab.com/groups/gitlab-org/-/work_items/8903 | Raft goals: remove Praefect, remove Postgres. **Last status update 2024-06-18** |
| Epic 20405 | https://gitlab.com/groups/gitlab-org/-/work_items/20405 | "Make Gitaly Cluster a first-class solution"; open Praefect bugs; public weekly "No progress" notes at ~5 h/week |
| Epic 6127 | https://gitlab.com/groups/gitlab-org/-/epics/6127 | "Gitaly should run well in Kubernetes"; customer notes incl. a paused evaluation over Praefect-on-VMs |
| cloud-native#52 | https://gitlab.com/gitlab-org/cloud-native/-/work_items/52 | **closed**, and about the Operator — the stale citation the reference-architectures claim rests on |
| charts#3813, #5376 | https://gitlab.com/gitlab-org/charts/gitlab/-/issues/3813 | gitlab-exporter/Sentinel — **both closed at milestone 17.1**, not open |
| Duo Self-Hosted | https://docs.gitlab.com/administration/self_hosted_models/ | the Duo Enterprise add-on requirement, verbatim; version history to GA 17.9 |
| Duo add-ons | https://docs.gitlab.com/subscriptions/subscription-add-ons/ | tier table; Duo Core unavailable on an offline licence; Agent Platform Self-Hosted flat-fee ELA |
| Duo offline deployment | https://docs.gitlab.com/administration/gitlab_duo_self_hosted/offline_deployment/ | sales-gated offline licence; the three hosts not contacted; `vllm/vllm-openai` pinned v0.18.1+; side-load list |
| Install the AI Gateway | https://docs.gitlab.com/install/install_ai_gateway/ | `AIGW_*` / `DUO_WORKFLOW_*` env vars; 512 MB / 2 CPU / no GPU; the `customers.gitlab.com` 20-second timeout |
| AI Gateway source + licence | `gitlab-org/modelops/applied-ml/code-suggestions/ai-assist` | public repo, **GitLab EE licence** — source-available, not OSI open source |
| Configure LLM platforms | https://docs.gitlab.com/administration/gitlab_duo_self_hosted/supported_llm_serving_platforms/ | vLLM **v0.18.1+**; LiteLLM as the provider layer; validated provider list; the `/v1` URL suffix and `custom_openai/<id>` identifier format; `--disable-log-requests`. **Note the path moved** — the `self_hosted_models/` form 403s |
| MCP server | https://docs.gitlab.com/user/model_context_protocol/mcp_server/ | `Tier: Free, Premium, Ultimate` |
| gitlab#587846 | https://gitlab.com/gitlab-org/gitlab/-/work_items/587846 | MCP server decoupled from Duo and the cloud AI Gateway in **19.2**; the admin toggle path |
| Chart deployment doc | `charts/gitlab` → `doc/installation/deployment.md` @ master | `global.edition=ce` opt-in; EE is the default |

## Agent-sourced — fetched but not independently re-verified (**[A]**)

| Area | URLs |
|---|---|
| Upgrade paths, requirements | `docs.gitlab.com/update/upgrade_paths/`, `/install/requirements/` |
| External Redis | `docs.gitlab.com/charts/advanced/external-redis/` |
| Reference architectures, Gitaly on K8s, Operator | `/administration/reference_architectures/`, `/administration/gitaly/kubernetes/`, `/operator/` |
| PostgreSQL external upgrade | `/administration/postgresql/external_upgrade/` |
| Backup / restore | `/administration/backup_restore/backup_gitlab/`; chart repo `doc/backup-restore/backup.md`, `restore.md` |
| Offline deployments | `/user/application_security/offline_deployments/`, `/topics/offline/quick_start_guide/` |
| Issues | `gitlab-org/gitlab` #388094, #241672, #542995, #595725, #597558; epic #22099 |
| Charts issues | `gitlab-org/charts/gitlab` #1444, #3813, #3021, #4918, #6152 |
| Runner issues | `gitlab-org/gitlab-runner` #4509, #37448 |

## Volatile facts to re-verify on every freshen

- **Latest chart and app version.** Enumerate unfiltered from
  `charts.gitlab.io/index.yaml` or `helm search repo gitlab/gitlab --versions`.
  Never pattern-match on expected versions.
- **The required-stop list.** Re-read `upgrade_path.yml`; stops are appended as
  new minors ship, and a conditional stop has precedent (17.1).
- **The PG support window.** 19.x is 17-only today; PG 18 is opt-in from 19.3,
  default from 19.10, minimum at 20.0 — all three are future-dated claims.
- **Chart default flips** at every hop. The mechanical stock-values diff is the
  only reliable detector; a hand-built breaking-change list has already been
  measured missing one of five.
- **NGINX Ingress removal at GitLab 20.0**, and whether Gateway API becomes
  unavoidable before then.
- **`global.appConfig.knowledgeGraph` → `orbit`**, removal planned for 19.5.
- Issue states for every number above — several are open and may be fixed,
  documented, or closed as stale.
- **Gitaly Cluster (Praefect) on Kubernetes leaving beta.** Check epic 20405's
  status notes and whether `praefect/_index.md` still says beta. This is the
  single fact that would change the HA answer.
- **Whether the zero-downtime contradiction is reconciled** — reference
  architectures vs the chart's own `doc/installation/upgrade.md`.
- **The Duo tier table and add-on names.** GitLab has renamed and re-tiered
  these repeatedly; Non-Agentic Chat left Duo Core on 2026-05-21. Never answer
  a licensing question from memory.
- **The vLLM version pin** in the Duo Self-Hosted offline runbook (v0.18.1+ at
  time of writing) and the supported-model matrix.
- **MCP server availability and its admin toggle path** — free and
  Duo-decoupled since 19.2; verify it has not been re-gated.

## Method notes that changed an answer

- **Use `glab`, not web scraping, for gitlab.com.** The notes endpoint returns
  401 to unauthenticated fetchers and comments are JS-rendered. A scraped pass
  concluded a fix had no backport; `glab api .../related_merge_requests`
  returned three backport MRs and proved the opposite.
- **A milestone is not a fixed-in version.** Only backport MRs and their
  `target_branch` answer whether a fix reached the target.
- **The Support upgrade-path calculator is client-side JS** and was never
  executed — the YAML is the source.

## Claims that did not survive checking

Recorded so nobody re-derives them.

- **[?] "GitLab publicly walked back an HA promise, and staff objected."**
  Searched the trackers, the epics' full note threads, forums and aggregators —
  **no such statement was found**. What *is* documented is a stall: epic 20405
  reports "No progress" at ~5 contributor hours/week (2026-07-23, 2026-07-30)
  and a customer evaluation paused over Praefect-on-VMs. Use the stall framing;
  the reversal framing is unsupported.
- **[?] "charts#3813 (gitlab-exporter ignores Sentinel) is open."** Closed at
  milestone 17.1, along with #5376. Secondary sources still describe it as live.
- **[?] "19.0's `s3_v2` change breaks an `s3:` registry stanza."** The legacy
  name is registered onto the v2 factory; the stanza keeps working.
- **[?] "Chart 10.3.0's Gateway API CRD step is required for everyone."**
  Required only if Gateway API objects render.
- **[?] "The extensions docs page lists the required extensions."** It defers to
  `requirements.md`; grepping it for `amcheck` returns nothing.
- **[?] "19.0 is a required stop because it is a major."** No `19.0` entry
  exists in `upgrade_path.yml`.

## Known weak spots

- The GitLab 19.0 breaking-changes **blog post** returned HTTP 403 to every
  fetch; its content reached this skill only through search summaries. The
  *docs* equivalents were fetched directly and carry the verified claims.
- ~~The serving-platforms page 403s.~~ **Resolved 2026-08-29** — the page moved.
  `.../administration/self_hosted_models/supported_llm_serving_platforms/` 403s;
  `.../administration/gitlab_duo_self_hosted/supported_llm_serving_platforms/`
  returns 200 and is now the cited source. **A 403 on a GitLab docs URL is more
  often a stale path than a block — try the sibling path before recording the
  page as unfetchable.**
- Whether `backup-utility --skip db` is *required* against operator-managed
  PostgreSQL is unresolved by any source found → `references/backup-restore.md`.
- Default replica literals for webservice/sidekiq/kas/shell resolve through a
  shared chart helper that was not traced to ground — confirm against a render
  before quoting a number.
- CE image publication for a specific 19.x tag was not confirmed; the registry
  API cannot sort tags reverse-chronologically.
- "Inference data never leaves the network" is GitLab's own documented
  assertion about software you build from their source, not an audited fact.

## Related skills

- **`postgres-operator-best-practices`** — Zalando operator mechanics for the
  mandatory PG 17 move. Cited, not restated.
- **`helm`** — `references/values-porting.md` for the three-way merge this
  skill's per-hop method depends on.
- **`redis-to-valkey`** — migrating the Redis Sentinel dependency to Valkey.
- **`k8s-components-checker`** — compatibility verdicts and version-skew.
- **`airgap-vetting`** — vetting artifacts before they cross the gap.
