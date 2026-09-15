# Sources — gitlab-best-practices

Per-URL index backing this skill's factual claims. Freshen Mode probes every
row and rewrites the stamp below; rows it could not reach carry an inline
exception note instead.

**Freshened: 2026-08-29**

Chart and app versions enumerated unfiltered from the Helm repo index; the
required-stop list read from its machine-readable source; deployment-level
claims checked against a live install taken through a multi-hop 18.x → 19.x
campaign, and against the unpacked chart at 10.3.1. Claims tagged **[A]** in
the reference files were reported by a source but not independently
re-verified.

## Table of contents
- [Primary sources — verified directly](#primary-sources-verified-directly)
- [Agent-sourced — fetched but not independently re-verified (**[A]**)](#agent-sourced-fetched-but-not-independently-re-verified-a)
- [Issue states — probed via `glab api` 2026-08-29](#issue-states-probed-via-glab-api-2026-08-29)
- [Volatile facts to re-verify on every freshen](#volatile-facts-to-re-verify-on-every-freshen)
- [Method notes that changed an answer](#method-notes-that-changed-an-answer)
- [Claims that did not survive checking](#claims-that-did-not-survive-checking)
- [Known weak spots](#known-weak-spots)
- [Related skills](#related-skills)

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
| Live install | a multi-hop 18.x → 19.x campaign, chart 9.x → 10.x | default flips, render behaviour, verification sequence, Sidekiq HPA measurements, restore rehearsal |
| Unpacked chart | `helm pull gitlab/gitlab --version 10.3.1 --untar` | per-component PDBs and replica defaults; the `praefect` and `ai-gateway` subcharts; optional-subchart image sources |
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
| **gitaly#6934** | https://gitlab.com/gitlab-org/gitaly/-/issues/6934 | **open** (2025-09-29, 60 notes read in full). GitLab's own "No documented or publicly supported approach to ZDU in Cloud Hybrid"; `tableflip` removal and its Kubernetes incompatibility; unsolved Rails↔Gitaly rollout ordering; the sequencing argument |
| gitaly#4616 | https://gitlab.com/gitlab-org/gitaly/-/issues/4616 | **closed** decision record — **"Final decision: NO-GO"** on retiring Praefect's PostgreSQL ahead of Raft |
| gitaly#4436 | https://gitlab.com/gitlab-org/gitaly/-/issues/4436 | **closed** (2022) — the four Raft goals, unchanged in epic 8903 four years later |
| Epic 6127 note trail | https://gitlab.com/groups/gitlab-org/-/epics/6127 | 150+ notes read end to end: the 2023 "unsupported vs document the risks" argument; the 2023→2026 customer-commitment trail with tiers and seat counts; the reversed-recommendation quote; the FY26Q4 GA target that slipped |
| GitLab 18.11 release | https://docs.gitlab.com/releases/18/gitlab-18-11-released/ | GA date 2026-04-16, against the FY26Q4 (Dec 2025–Jan 2026) commitment |
| charts#3813, #5376 | https://gitlab.com/gitlab-org/charts/gitlab/-/issues/3813 | gitlab-exporter/Sentinel — **both closed at milestone 17.1**, not open |
| Duo Self-Hosted | https://docs.gitlab.com/administration/gitlab_duo_self_hosted/ | the Duo Enterprise add-on requirement, verbatim; version history to GA 17.9. **Repointed 2026-09-15** — the old `/administration/self_hosted_models/` path now 403s; same page, moved. |
| Duo add-ons | https://docs.gitlab.com/subscriptions/subscription-add-ons/ | tier table; Duo Core unavailable on an offline licence; Agent Platform Self-Hosted flat-fee ELA |
| Duo offline deployment | https://docs.gitlab.com/administration/gitlab_duo_self_hosted/offline_deployment/ | sales-gated offline licence; the three hosts not contacted; `vllm/vllm-openai` pinned v0.18.1+; side-load list |
| Install the AI Gateway | https://docs.gitlab.com/install/install_ai_gateway/ | `AIGW_*` / `DUO_WORKFLOW_*` env vars; 512 MB / 2 CPU / no GPU; the `customers.gitlab.com` 20-second timeout |
| AI Gateway source + licence | `gitlab-org/modelops/applied-ml/code-suggestions/ai-assist` | public repo, **GitLab EE licence** — source-available, not OSI open source |
| Configure LLM platforms | https://docs.gitlab.com/administration/gitlab_duo_self_hosted/supported_llm_serving_platforms/ | vLLM **v0.18.1+**; LiteLLM as the provider layer; validated provider list; the `/v1` URL suffix and `custom_openai/<id>` identifier format; `--disable-log-requests`. **Note the path moved** — the `self_hosted_models/` form 403s |
| Large-instance backups | `doc/administration/backup_restore/backup_large_reference_architectures.md` @ master | the split-by-data-class approach; `pg_dump` "not appropriate for databases over 100 GB"; "incremental repository backup is not supported by `backup-utility` with server-side repository backup". **Its `cron.extraArgs` recipe is defective** — `--skip repositories` there suppresses the repository backup entirely; proven against the `backup-utility` gate |
| `backup_gitlab.md` | `doc/administration/backup_restore/backup_gitlab.md` @ master | `COMPRESS_CMD` (default `gzip -c -1`); **"It is not possible to skip the tar creation when using object storage for backups"** |
| `object_storage_backup.rb` | `gitlab-org/build/CNG` → `gitlab-toolbox/scripts/lib/object_storage_backup.rb` @ master | the per-bucket `s3cmd ... sync` + `tar -I gzip` path; **`gzip` hardcoded**, no `COMPRESS_CMD` hook; `s3cmd` is the default `s3_tool`, `awscli` the alternative |
| `backup-utility` | `gitlab-org/build/CNG` → `gitlab-toolbox/scripts/bin/backup-utility` @ master | `--repositories-server-side`, `--s3tool` / `--s3tool-backup` / `--s3tool-data`; **no `--incremental`, no `PREVIOUS_BACKUP`** (verified by absence) |
| Gitaly backup sink | `gitlab-org/gitaly` → `internal/backup/sink.go` @ master | `endpoint` supported for third-party S3; `withS3DefaultChecksumCalculation` forces `request_checksum_calculation=when_required` whenever a custom endpoint is set — the **Object Lock** trap, named in the code comment |
| charts#3421 / #3338 / #5151 | https://gitlab.com/gitlab-org/charts/gitlab/-/issues/3421 | incremental (closed unimplemented); s3cmd 404 `NoSuchKey` on artifacts; large-backup guidance |
| gitlab#477791 | https://gitlab.com/gitlab-org/gitlab/-/issues/477791 | `gitlab-backup-cli` docs — `missed:` labels for every release 17.7 → 19.3 |
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

## Issue states — probed via `glab api` 2026-08-29

State drifts independently of the claim. Re-probe this table on every freshen;
the claims resting on these issues are cited in the reference files above.

| Issue | State | Note |
|---|---|---|
| `gitlab#594569` | **open** | paused background migrations after 18.10; no fix version |
| `gitlab#477791` | **open**, milestone 19.4 | backup-cli docs link; `missed:` 17.7 → 19.3 |
| `charts#4918` | **open** | mirror chart images to an external registry |
| `charts#5151` | **open** | best practice for very large backups |
| `gitaly#6934` | **open** | ZDU on Cloud Hybrid; rollout ordering; tableflip removal |
| `gitlab#388094` | closed 2023-09-18 | **closed on a triage ping, not by a fix** — see below |
| `gitlab#595725` | closed, milestone 19.0 | backports reached 18.9/18.10/18.11 — milestone ≠ fixed-in |
| `gitlab#597558` | closed, milestone 19.1 | the dropped-index pre-flight |
| `gitlab#241672` | closed | stale Sidekiq schema cache |
| `gitlab#587846` | closed | MCP server decoupled from Duo in 19.2 |
| `charts#1444` | closed | prepared statements / PgBouncer — no chart flag shipped |
| `charts#3021` | closed | migrations Job under Argo CD |
| `charts#3338` | closed 2024-01-29 | retitled to a docs task; the `404 NoSuchKey` crash is in the body |
| `charts#3421` | closed unimplemented | incremental backup in `backup-utility` |
| `charts#3813`, `#5376` | closed, milestone 17.1 | exporter/Sentinel — fixed, not a live limitation |
| `gitaly#4616` | closed | "Final decision: NO-GO" on retiring Praefect's PostgreSQL |
| `runner#4509` | closed | helper-image tagging asymmetry |

**Method rule — a closed issue is not a fixed bug.** `gitlab#388094` closed with
*"Thanks for the reminder. I will close this issue"* in reply to a triage bot
asking for a status update, and the last substantive comment says the safe
ordering exists in the **Operator** while leaving the chart case open. Read the
closing comment before downgrading a hazard on the strength of a `closed` badge;
housekeeping closes and fix closes look identical in the state field.

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
- **Whether upstream fixes the `cron.extraArgs` recipe** in
  `backup_large_reference_architectures.md` (it currently ships
  `--skip repositories` alongside `--repositories-server-side`), and whether
  `backup-utility` starts rejecting that flag pair instead of silently
  producing a repository-free backup.

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

- **[?] "Staff publicly objected to their own company's HA direction."** Not
  found in that form, and a first pass wrongly generalised that null result into
  "the reversal framing is unsupported." **It is supported** — the error was
  searching for internal dissent instead of for commitments to customers.
  Documented: a reversed recommendation stated by staff (*"architecture that
  GitLab had once blessed and has since changed our recommendation"*, 2023), a
  three-year unmet-requirement trail on epic 6127 ending in a **July 2026 lost
  deal**, a **published GA target that slipped** (FY26Q4 → 18.11 on 2026-04-16,
  standalone only), and a substantive engineering argument on `gitaly#6934` that
  the platform migration was sequenced ahead of the HA work. What is *not*
  evidenced is anyone stating that leadership was wrong to do it.
- **[?] "charts#3813 (gitlab-exporter ignores Sentinel) is open."** Closed at
  milestone 17.1, along with #5376. Secondary sources still describe it as live.
- **[?] "Upstream states the toolbox `backup-utility` *fails* with a large
  amount of data, and repositories must then be backed up from a Linux-package
  VM."** Attributed to `backup_large_reference_architectures.md`; **not present**
  there at master, raw or rendered, nor in the charts backup doc. Provenance
  traced: it is **2023-era doc text quoted inside a comment on charts#5151**
  (2023-12-05), since reworded or removed. **Do not restore it.** For a
  current line with similar force, that page does still say `pg_dump` is *"not
  appropriate for databases over 100 GB"*.

  **Method rule this produced — a quotation inside an issue comment is evidence
  about the past, not about the current page.** Issue threads preserve doc text
  as it read the day someone pasted it. Re-grep the live file before attributing
  any quote to it, even when the comment names the file.
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
  page as unfetchable.** **The same move caught the parent page too**: the
  `Duo Self-Hosted` row above was still on `/administration/self_hosted_models/`
  (403) and is repointed to `/administration/gitlab_duo_self_hosted/` (200,
  same title) as of 2026-09-15. When a docs section moves, fix every row that
  points into it, not just the one that failed.
- Whether `backup-utility --skip db` is *required* against operator-managed
  PostgreSQL is unresolved by any source found → `references/backup-restore.md`.
- Default replica literals for webservice/sidekiq/kas/shell resolve through a
  shared chart helper that was not traced to ground — confirm against a render
  before quoting a number.
- CE image publication for a specific 19.x tag was not confirmed; the registry
  API cannot sort tags reverse-chronologically.
- "Inference data never leaves the network" is GitLab's own documented
  assertion about software built from their source, not an audited fact.

## Related skills

- **`postgres-operator-best-practices`** — Zalando operator mechanics for the
  mandatory PG 17 move. Cited, not restated.
- **`helm`** — `references/values-porting.md` for the three-way merge this
  skill's per-hop method depends on.
- **`redis-to-valkey`** — migrating the Redis Sentinel dependency to Valkey.
- **`k8s-components-checker`** — compatibility verdicts and version-skew.
- **`airgap-vetting`** — vetting artifacts before they cross the gap.
