# Sources — keycloak-iam

Authoritative external references the skill points at. `freshen` mode probes these and stamps `Last verified:` per row. Mark a row with `<!-- ignore-freshen -->` if the URL is intentionally pinned to a historical state.

## Documentation roots

| URL | Purpose | Last verified | Pinned |
|-----|---------|---------------|--------|
| https://www.keycloak.org/server/all-config | Full CLI option index | 2026-05-06 | — |
| https://www.keycloak.org/server/configuration | Configuration concept overview, build vs runtime | 2026-05-06 | — |
| https://www.keycloak.org/server/configuration-metrics | Metrics surface | 2026-05-06 | — |
| https://www.keycloak.org/server/health | Health endpoints + probe semantics | 2026-05-06 | — |
| https://www.keycloak.org/server/configuration-tracing | OTLP tracing options | 2026-05-06 | — |
| https://www.keycloak.org/server/logging | Structured logging, JSON output, redaction | 2026-05-06 | — |
| https://www.keycloak.org/server/importExport | `kc.sh export`/`import` modes | 2026-05-06 | — |
| https://www.keycloak.org/server/reverseproxy | Proxy headers, graceful shutdown, client cert lookup | 2026-05-06 | — |
| https://www.keycloak.org/docs/latest/upgrading/index.html | Migration changes per version | 2026-05-06 | — |
| https://www.keycloak.org/docs/latest/server_admin/ | Server admin guide (realms, clients, auth flows, FGAP, organizations, workflows) | 2026-05-06 | — |
| https://www.keycloak.org/docs/latest/server_development/ | SPI guide, theme structure, custom providers | 2026-05-06 | — |

## Operator + Kubernetes

| URL | Purpose | Last verified | Pinned |
|-----|---------|---------------|--------|
| https://www.keycloak.org/operator/installation | OLM and non-OLM install paths | 2026-05-06 | — |
| https://www.keycloak.org/operator/basic-deployment | Minimal `Keycloak` CR | 2026-05-06 | — |
| https://www.keycloak.org/operator/advanced-configuration | Full CR field reference (additionalOptions, podTemplate, scheduling) | 2026-05-06 | — |
| https://www.keycloak.org/operator/keycloak-cr | CR field-by-field reference | 2026-05-06 | — |
| https://www.keycloak.org/operator/realm | `KeycloakRealmImport` CR | 2026-05-06 | — |
| https://www.keycloak.org/operator/rolling-updates | Zero-downtime patch update strategy (26.6+) | 2026-05-06 | — |
| https://www.keycloak.org/high-availability/ | HA topology guide (single + multi-cluster) | 2026-05-06 | — |
| https://github.com/keycloak/keycloak-k8s-resources | Per-version-tag operator install manifests (CRDs + RBAC + Deployment); tags 26.6.1 and 26.6.2 both carry the 3 expected files | 2026-05-28 | — |

## Securing applications (developer surface)

| URL | Purpose | Last verified | Pinned |
|-----|---------|---------------|--------|
| https://www.keycloak.org/securing-apps/oidc-layers | OIDC integration patterns | 2026-05-06 | — |
| https://www.keycloak.org/securing-apps/dpop | DPoP-bound tokens (RFC 9449) | 2026-05-06 | — |
| https://www.keycloak.org/securing-apps/jwt-authorization-grant | RFC 7523 JWT-Authz-Grant (GA in 26.6) | 2026-05-06 | — |
| https://www.keycloak.org/securing-apps/mcp-authz-server | MCP authorization server (CIMD experimental) | 2026-05-06 | — |
| https://www.keycloak.org/securing-apps/token-exchange | RFC 8693 standard token exchange | 2026-05-06 | — |

## Source code + releases

| URL | Purpose | Last verified | Pinned |
|-----|---------|---------------|--------|
| https://github.com/keycloak/keycloak | Upstream source — option mappers, operator code, themes | 2026-05-28 | — |
| https://github.com/keycloak/keycloak/releases/tag/26.6.2 | Latest stable release notes (2026-05-19) — security-fix batch | 2026-05-28 | 26.6.2 |
| https://github.com/keycloak/keycloak/releases/tag/26.6.1 | 26.6.1 release notes (2026-04-15) | 2026-05-28 | 26.6.1 |
| https://github.com/keycloak/keycloak/releases/tag/26.6.0 | 26.6.0 release notes (highlights: Workflows, JWT-Authz-Grant, zero-downtime updates) | 2026-05-06 | 26.6.0 |
| https://github.com/keycloak/keycloak/security/advisories | Security advisories — canonical CVE list (probe before quoting any CVE ID) | 2026-05-28 | — |
| https://github.com/keycloak/keycloak-benchmark | Gatling-based load harness | 2026-05-06 | — |

## Specs referenced

<!-- ignore-freshen --> RFCs and standards don't drift; pinning is intentional.

| URL | Purpose | Pinned |
|-----|---------|--------|
| https://datatracker.ietf.org/doc/html/rfc7523 | JWT Bearer / Authorization Grant | RFC |
| https://datatracker.ietf.org/doc/html/rfc8693 | OAuth 2.0 Token Exchange | RFC |
| https://datatracker.ietf.org/doc/html/rfc9449 | DPoP | RFC |
| https://datatracker.ietf.org/doc/html/rfc7636 | PKCE | RFC |
| https://datatracker.ietf.org/doc/html/rfc8252 | OAuth 2.0 for Native Apps | RFC |
| https://datatracker.ietf.org/doc/html/rfc8414 | OAuth 2.0 Authorization Server Metadata | RFC |
| https://datatracker.ietf.org/doc/html/rfc8707 | OAuth 2.0 Resource Indicators | RFC |
| https://datatracker.ietf.org/doc/html/rfc7591 | OAuth 2.0 Dynamic Client Registration | RFC |
