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
| https://github.com/keycloak/keycloak-k8s-resources | Per-version-tag operator install manifests (CRDs + RBAC + Deployment); tags now run to 26.7.0, and 26.6.3/26.6.4 exist too — the repo tracks server releases 1:1 | 2026-07-21 | — |

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
| https://github.com/keycloak/keycloak | Upstream source — option mappers, operator code, themes | 2026-07-21 | — |
| https://github.com/keycloak/keycloak/releases/tag/26.7.0 | **Latest stable** (2026-07-09) — new minor. Highlights: SCIM user provisioning (preview), multi-cluster HA without external caches (preview), OpenID Shared Signals Framework (experimental), Identity Brokering API V2, SAML step-up auth, HAProxy/Traefik proxy blueprints | 2026-07-21 | 26.7.0 |
| https://github.com/keycloak/keycloak/releases/tag/26.6.4 | 26.6.4 (2026-06-26) — terminal 26.6 patch as of this probe; security fix for CVE-2026-9099 (group-admin → realm-admin escalation, HIGH) | 2026-07-21 | 26.6.4 |
| https://github.com/keycloak/keycloak/releases/tag/26.6.3 | 26.6.3 (2026-06-04) — security batch (3 CVEs: lodash template injection in account/ui, SSRF via OIDC token endpoint, CORS reflection from unverified `azp`) | 2026-07-21 | 26.6.3 |
| https://github.com/keycloak/keycloak/releases/tag/26.6.2 | 26.6.2 release notes (2026-05-19) — security-fix batch | 2026-07-21 | 26.6.2 |
| https://github.com/keycloak/keycloak/releases/tag/26.6.1 | 26.6.1 release notes (2026-04-15) | 2026-05-28 | 26.6.1 |
| https://github.com/keycloak/keycloak/releases/tag/26.6.0 | 26.6.0 release notes (highlights: Workflows, JWT-Authz-Grant, zero-downtime updates) | 2026-05-06 | 26.6.0 |
| https://github.com/keycloak/keycloak/security/advisories | Security advisories — canonical CVE list (probe before quoting any CVE ID) | 2026-07-21 | — | 

**Advisory-feed caveat, observed 2026-07-21.** Eight advisories carry
`published_at: 2026-06-26`, but only one of them (CVE-2026-9099) is credited in
the 26.6.4 release notes published the same day. The feed's
`first_patched_version` is **empty on every one of them**, so the feed alone
cannot tell you which release closes a given CVE. Cross-read the release notes
of each candidate version — do not infer a fix version from the disclosure date.
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
