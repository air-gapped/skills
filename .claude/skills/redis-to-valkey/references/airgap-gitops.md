# Air-gap delivery and GitOps rewiring

## Complete mirror list (Sentinel HA migration)

| Artifact | Source(s) | Notes |
|---|---|---|
| Valkey server image | `docker.io/valkey/valkey:<tag>` | the only runtime image for groundhog2k/CloudPirates/official charts; pin the tag explicitly in values |
| Exporter image (optional) | `docker.io/oliver006/redis_exporter`, **`ghcr.io/oliver006/redis_exporter`**, **`quay.io/oliver006/redis_exporter`** | pin `metrics.exporter.image.*` so the chart's own default tag drift doesn't change the mirror list |
| Chart | vendored `.tgz` in git (preferred) or mirrored Helm/OCI repo | see vendoring below; CloudPirates chart additionally needs its `common` library chart (OCI) for offline `helm dependency build` |
| RedisShake (if transferring data) | GitHub release tarball `redis-shake-vX.Y.Z-linux-<arch>.tar.gz` (single static Go binary) or image `ghcr.io/tair-opensource/redisshake` | binary for jump hosts; image for running the transfer as an in-cluster Job (often the only network position that reaches both ends) |
| rdb-cli (alternative) | build from `redis/librdb` source (no prebuilt binaries) | build on a matching-arch connected machine, carry the binary; or vendor the source tarball |

That's the whole surface: 1–2 images, 1 chart artifact, optionally 1 tool.
Compare against 5 vendor images for a Bitnami HA install.

## Chart vendoring (bootstrap-safe source)

Commit the chart tarball (or the unpacked chart) into the git repo the
GitOps controller already trusts:

```
helm repo add <name> <chart-repo-url> && helm pull <name>/valkey --version <X.Y.Z>
# commit valkey-X.Y.Z.tgz (and a default-values snapshot for diffing) to git
```

Why vendoring beats a mirrored chart registry for the bootstrap path: if
the migrated Redis/Valkey backs your **own container registry** (common:
registry session/cache stores), then that registry cannot be the source of
the chart or images needed to rebuild its own dependency — a circular
dependency that only shows up during disaster recovery. Git is the
bootstrap root; keep everything the registry's own stack needs in git or in
release artifacts stored outside the registry. For all *other* workloads,
a private OCI registry (`helm push chart.tgz oci://registry.internal/charts`)
is fine and more automatable.

## Argo CD source rewiring

Existing Bitnami apps commonly use the multi-source pattern (chart from
`charts.bitnami.com` + values from git via `$values`). The pattern survives
the migration — only the chart source line changes:

- **Classic Helm repo** (e.g. groundhog2k):
  `repoURL: https://groundhog2k.github.io/helm-charts/`, `chart: valkey`,
  `targetRevision: <X.Y.Z>` — plus the existing `ref: values` git source.
- **OCI registry**: `repoURL: registry.internal/charts` — **no `oci://`
  prefix** in Argo CD's repoURL (unlike the helm CLI); registry declared
  with `enableOCI: true` if it needs credentials.
- **Vendored in git**: point the source at the git repo `path:` holding the
  unpacked chart; valueFiles become plain relative paths (single-source) or
  keep `$values` (multi-source).

Release-name preservation: if the old app pinned `helm.releaseName`, choose
the new release name deliberately — resource names (services, secrets,
configmaps) derive from it, and client configs reference those DNS names.

## Bitnami endpoint risk model (as of 2026-07-18)

- `charts.bitnami.com` 302-redirects to `repo.broadcom.com/bitnami-files`
  and still serves the full index + old tarballs. **No announced sunset**,
  but Broadcom labels the legacy arrangement temporary.
- Only ~13 of 144 charts still receive updates — and those reference
  `docker.io/bitnami/*:latest` images only, because **versioned tags no
  longer exist on docker.io/bitnami** (moved to frozen
  `docker.io/bitnamilegacy`; version pins are a paid subscription).
- Therefore a pinned Bitnami app *syncs* fine and fails later at
  **image-pull on reschedule** once no node holds the tag in cache.
  A registry rewrite to `bitnamilegacy` is a stopgap (frozen, unpatched,
  no committed retention) — schedule the real migration.

## Update automation (Renovate) after the switch

- Charts consumed from classic Helm repos or OCI: standard helm managers
  work; in air-gapped setups point datasources at the internal mirror via
  `hostRules`/`registryAliases`.
- Vendored charts in git are invisible to Renovate by default — add a
  custom manager watching the committed `Chart.yaml`/tarball name, or
  accept a manual quarterly bump ritual.
- Silence is a signal: frozen upstreams (Bitnami pins) produce no update
  PRs at all — absence of PRs is indistinguishable from "up to date"
  unless you alert on artifact age.
