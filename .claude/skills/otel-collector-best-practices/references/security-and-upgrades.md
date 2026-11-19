# Security, supply chain, upgrades

Checked 2026-10-04: GitHub security advisories for collector, contrib,
releases, operator and helm-charts; opentelemetry.io security docs; releases
repo at v0.162.0.

## Contents
- Advisories and upgrade floors
- Hardening
- Supply chain: distributions, signatures, SBOMs, ocb
- Config tooling
- Upgrade procedure
- Air-gapped sites

## Advisories and upgrade floors (2025-01 → 2026-10)

| Advisory | Component | Severity | Fixed in |
|---|---|---|---|
| GHSA-pjv4-3c63-699f / CVE-2026-42602 | `azureauthextension` server-side auth does not validate bearer tokens | high | **no fix listed** — do not use `azure_auth` on receivers; use `oidc` |
| GHSA-8hxm-mxr2-qf9h | Prometheus receiver dependency (resource exhaustion, info exposure) | high | Prometheus lib 0.311.3 (contrib pins newer from v0.152) |
| GHSA-j39g-cqwj-9xvf / CVE-2026-2303 | otelcol-contrib 0.154.0 mongo driver, only `mongodb` receiver with GSSAPI | medium | driver ≥ 2.4.2 (contrib v0.155 ships 2.7.0) |
| GHSA-4jvg-4jfx-fmhc / CVE-2026-47256 | `sentry` exporter path traversal | medium | contrib 0.154.0 |
| GHSA-w5cv-pw74-4rxc / CVE-2026-55701 | `github` receiver ignores `required_headers` | medium | contrib 0.151.0 |
| GHSA-cxh2-4639-vmc5 / CVE-2026-47701 | operator Target Allocator reads arbitrary files via ServiceMonitor `bearerTokenFile` | high | operator 0.152.0 |

Floors: **contrib ≥ 0.155.0**, **operator ≥ 0.152.0**. No 2025–2026
advisories for core, the releases repo or the Helm charts. Security fixes are
promised within 30 days of disclosure (5 business days for CVSS ≥ 9.0).

## Hardening

- Server components bind to `localhost` by default since v0.110.0 — bind
  deliberately, never `0.0.0.0` without need.
- TLS: `min_version` defaults to 1.2; mTLS with `client_ca_file` on the
  receiver, `ca_file`/`cert_file`/`key_file` on the exporter; avoid
  `insecure_skip_verify`.
- Authenticate server-like receivers (`bearertokenauth`, `basicauth`,
  `oidc`).
- Minimise components (custom `ocb` build); expose only needed ports.
- Run non-root where possible (the contrib image is `FROM scratch`,
  `USER 10001`). Exceptions: `file_log` with hostPath checkpoints, `journald`
  (root or `DAC_READ_SEARCH`).
- Secrets via `${env:VAR}` / `${file:path}`; secret fields are
  `configopaque` and redacted in printed config.
- `pprof` (1777) and `zpages` (55679) are debug tools — do not expose them.
- `memory_limiter`, queue sizing and `filter` double as DoS safeguards.

## Supply chain

- Distributions: `otelcol`, `otelcol-contrib`, `otelcol-k8s`,
  `otelcol-otlp`, `otelcol-ebpf-profiler`, `otelcol-prometheus`
  (experimental). Images on Docker Hub (`otel/…`) and GHCR
  (`ghcr.io/open-telemetry/opentelemetry-collector-releases/…`).
- Every binary, package, checksum and SBOM ships a cosign v3 bundle
  `<artifact>.sigstore.json` (mandatory since v0.158.0) and a Syft
  `<artifact>.sbom.json`.
- Verify an image (from the core README):

  ```bash
  cosign verify \
    --certificate-identity=https://github.com/open-telemetry/opentelemetry-collector-releases/.github/workflows/base-release.yaml@refs/tags/<RELEASE_TAG> \
    --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
    <IMAGE>
  ```

- Verify a binary: `cosign verify-blob --bundle <artifact>.sigstore.json <artifact>`
  (add the identity/issuer flags; the identity is the releasing workflow
  ref — inferred, not documented).
- `ocb` (OpenTelemetry Collector Builder), released as `cmd/builder/v<ver>`:
  a manifest with `dist:` and `receivers`/`processors`/`exporters`/
  `extensions`/`connectors`/`providers` lists of `gomod:` entries (plus
  `replaces:`). Component and `otelcol_version` must match on major.minor.
  Needs Go (≥ 1.26 from v0.160) and a module source. Start from a
  distribution's `manifest.yaml` in the releases repo and delete what you do
  not use.

## Config tooling

| Command | Use |
|---|---|
| `otelcol validate --config=…` | parse and validate without starting; run with the target binary/image and the env vars the config expands |
| `otelcol components` | list what this binary contains, with stability |
| `otelcol print-config --config=…` | final merged config (feature gate `otelcol.printInitialConfig`; secrets redacted unless `--mode=unredacted`) |
| several `--config` flags | merged in order; `--config="yaml:exporters::debug::verbosity: normal"` for one-off overrides |
| `--feature-gates=…` | enable (`name`) or disable (`-name`) gates |
| config providers | `file:`, `env:`, `yaml:`, `http:`, `https:`; may nest (`${file:exporters.yaml}`) |

OpAMP supervisor and extension are alpha.

## Upgrade procedure

1. List releases unfiltered (core and contrib, plus the chart if used) and
   read the breaking-changes and deprecations sections of **every** release
   between installed and target — two-week cadence means many hops.
2. Search the target's open issues (regressions, data loss, memory).
3. Render/validate the config with the new binary: `otelcol validate`, and on
   Helm `helm template` + diff. Watch for deprecated-alias warnings.
4. Check attribute and metric renames (see `processing.md` semconv table)
   against dashboards, alerts and saved queries.
5. Pin image tags (or digests); keep the previous artifact for rollback. An
   invalid config makes the collector fail at start, so a bad upgrade fails
   fast — make sure the rollout strategy stops on it.
6. After rollout, compare ingest rates and the self-monitoring drop metrics
   with the pre-upgrade baseline.

There is no LTS: only the latest release is supported; patch releases are
rare (crash, data loss, no workaround).

## Air-gapped sites

- Mirror the image(s) and keep the matching `.sigstore.json` bundles;
  whether image signatures survive a registry mirror copy is unverified —
  test it once.
- Offline signature checks need the Sigstore trusted root shipped in
  (`cosign verify-blob --bundle … --offline --trusted-root …`, flags not
  independently confirmed).
- `ocb` needs Go modules: mirror a module proxy, or run ocb outside and ship
  the binary. Vendoring via `GOFLAGS=-mod=vendor` is not documented by ocb.
- Mirror the Helm chart and set `image.repository` to the mirror; the k8s
  distro image is the only image the chart needs.
