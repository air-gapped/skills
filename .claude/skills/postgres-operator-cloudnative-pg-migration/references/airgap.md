# Air-gap mirroring and registry configuration

Verified 2026-07-24. CNPG publishes everything on ghcr.io; no
telemetry/phone-home exists anywhere in operator or docs (grep-verified)
— nothing to disable.

## Mirror list

Images (pin by digest after cosign verification at the mirror boundary):

| Image | Purpose | Notes |
|---|---|---|
| `ghcr.io/cloudnative-pg/cloudnative-pg:<ver>` | operator | Helm `image.repository` |
| `ghcr.io/cloudnative-pg/postgresql:<maj.min>-standard-<distro>` | operand | prefer `standard` over `minimal`: adds PGAudit, pgvector, pg_failover_slots, **all locales** (keeps en_US.UTF-8 available — Wall 1), JIT. `system` images deprecated. Distro = bookworm (glibc 2.36) or trixie (2.41) — **pick one and stay on it**: pg_upgrade refuses to cross image OS generations |
| `ghcr.io/cloudnative-pg/pgbouncer:<ver>` | Pooler CR | ≥1.19 required (auth_dbname) |
| `ghcr.io/cloudnative-pg/plugin-barman-cloud:v0.13.0` | backup plugin Deployment | |
| `ghcr.io/cloudnative-pg/plugin-barman-cloud-sidecar:v0.13.0` | backup sidecar in every PG pod | reference hidden base64-encoded in the release manifest Secret — easy to miss |
| `ghcr.io/cloudnative-pg/postgis:<ver>` (optional) | PostGIS operand | official |
| custom operand image (optional) | TimescaleDB / other Spilo-bundled extensions | no official timescaledb image; `timescale/timescaledb-ha` incompatible (wrong PGDATA, custom entrypoint); build on the CNPG base |

Helm charts (vendor tarballs or mirror the OCI/classic repo):
`cloudnative-pg/charts` → `cloudnative-pg` (operator) and
`plugin-barman-cloud` (chart 0.7.0 / appVersion v0.13.0).

Tools: `kubectl-cnpg` plugin binary (single Go binary from
cloudnative-pg releases; version-match the operator minor) — needed for
`publication/subscription create`, `sync-sequences`, `promote`,
`status`, `backup`.

Optionally the Grafana dashboard JSON from
`cloudnative-pg/grafana-dashboards`.

## Registry configuration

- Helm: `image.repository`, `imagePullSecrets`.
- Operator ConfigMap (`cnpg-controller-manager-config`, Helm
  `config.data`):
  - `POSTGRES_IMAGE_NAME` — fleet default operand image (the internal mirror).
  - `PGBOUNCER_IMAGE_NAME` — fleet default pooler image.
  - `PULL_SECRET_NAME` — operator copies this secret into every cluster
    namespace as `<cluster>-pull` and wires it into pods.
- Or per-fleet `ClusterImageCatalog` / per-namespace `ImageCatalog`
  CRDs mapping PG majors → mirrored digests; Clusters then use
  `imageCatalogRef` and image bumps become catalog edits (auto-rollout).
  Pooler images similarly via `pgbouncer.imageCatalogRef` (≥1.30).

## Signature verification offline

Operator/operand images are cosign-signed keylessly (GitHub OIDC) with
SBOM + provenance attestations. Keyless verification needs
Rekor/Fulcio — do it **at the mirroring boundary** (internet-side):

```bash
cosign verify ghcr.io/cloudnative-pg/cloudnative-pg@sha256:<digest> \
  --certificate-identity-regexp='^https://github.com/cloudnative-pg/' \
  --certificate-oidc-issuer='https://token.actions.githubusercontent.com'
```

then rely on digest pinning inside the gap.

## Support-window planning (affects mirror cadence)

CNPG ships a new minor ~quarterly; each minor is supported until 3
months after N+1 (≈6-month life). Skipping minors on upgrade is
discouraged ("sequential order"). Budget: 2–4 operator image + chart
refreshes per year, each triggering a rolling restart of all clusters
(unless `ENABLE_INSTANCE_MANAGER_INPLACE_UPDATES` is accepted). K8s
window at anchor time: CNPG 1.30.x officially supports K8s 1.34–1.36
(tested-not-supported down to ~1.30) — check the RKE2 fleet minor
against `supported_releases.md` each hop. Also re-check at each hop that
a plugin-barman-cloud release built against the new CNPG minor exists.

## Spilo-side freeze (decommission phase)

Keep mirrored until backup retention expires (see backup-chain.md):
the exact Zalando operator image, Spilo image, and logical-backup image
versions the retired clusters ran — resurrection is the only way to
read the frozen WAL-G archive. Zalando images are ghcr.io-only since
1.15.x (`registry.opensource.zalan.do` is dead — old mirror configs may
still point there).
