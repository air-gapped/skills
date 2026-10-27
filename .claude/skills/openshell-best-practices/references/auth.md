# Authentication — users, automation, tokens (0.1.x)

Verified against `v0.1.6` (`docs/how-it-works/gateways/authentication.mdx`,
`docs/kubernetes/access-control.mdx`, `crates/openshell-cli/src/oidc_auth.rs`,
`crates/openshell-server/src/cli.rs`).

## Contents

- Pick a mode
- OIDC with Keycloak (client recipe)
- Interactive vs unattended login
- Tokens: lifetimes and the TUI
- mTLS and the local gateway
- Supervisor identity (not a user concern)

## Pick a mode

| Mode | Use when | Notes |
|---|---|---|
| OIDC | Any shared or remote gateway | Per-person identity, roles, workspaces. Recommended upstream |
| mTLS | Package-managed local gateway, or one operator over port-forward/passthrough | Default for RPM/deb/brew local gateways; enabled automatically when a client CA is configured and no OIDC issuer is set |
| Trusted proxy | An access proxy (Cloudflare Access, corporate SSO) already authenticates | `server.disableTls=true` + `allow_unauthenticated_users = true`; never expose such a gateway directly |

Since **0.1.6** a gateway with none of OIDC / mTLS user auth / operator auth / gateway JWT
refuses to start. `allow_unauthenticated_users = true` is the explicit dev-only opt-out.

## OIDC with Keycloak

Gateway side: `server.oidc.issuer` (exact `iss`, e.g. `https://kc.example.com/realms/x` — or
`/auth/realms/x` on legacy-path installs), `audience` (default `openshell-cli`),
`rolesClaim: realm_access.roles`, `adminRole` + `userRole` (both or neither). Issuer must be
HTTPS; JWKS redirects and cross-origin `jwks_uri` are rejected unless allowed.

Client — public, for the CLI and SDKs:

```json
{
  "clientId": "openshell-cli",
  "publicClient": true,
  "standardFlowEnabled": true,
  "directAccessGrantsEnabled": false,
  "redirectUris": ["http://127.0.0.1/callback"],
  "attributes": {
    "pkce.code.challenge.method": "S256",
    "oauth2.device.authorization.grant.enabled": "true"
  },
  "protocolMappers": [{
    "name": "audience openshell-cli",
    "protocol": "openid-connect",
    "protocolMapper": "oidc-audience-mapper",
    "config": {"included.client.audience": "openshell-cli", "access.token.claim": "true"}
  }]
}
```

- **Redirect**: the CLI binds `127.0.0.1:<random port>` and redirects to
  `http://127.0.0.1:<port>/callback`. Register it **without a port**: Keycloak retries
  loopback redirects with the default port (RFC 8252), so any port matches. No wildcard.
- **Audience mapper**: public clients don't put themselves in `aud` by default; without the
  mapper every call fails audience validation.
- **Device grant**: lets `OPENSHELL_NO_BROWSER=1` use the device flow on headless hosts.
- **Roles**: realm roles `openshell-admin` / `openshell-user`. A user without either can log
  in but every RPC is refused in RBAC mode. Platform Admin = `adminRole`; workspace roles are
  memberships stored by the gateway (`openshell workspace ...`).
- Entra ID: `rolesClaim: roles`; Okta: `groups` (ES256 keys work).

Register: `openshell gateway add https://gw.example.com --name prod --oidc-issuer <issuer> --oidc-client-id openshell-cli`
(opens the browser; `openshell gateway login <name>` re-authenticates; `gateway logout`
forces a fresh login prompt next time).

## Interactive vs unattended login

| | Person at a workstation | Unattended job (cron, CI, another server) |
|---|---|---|
| Flow | Authorization Code + PKCE, browser on loopback | Client credentials, no browser |
| IdP client | The public `openshell-cli` | A separate **confidential** client with a secret (service account enabled, standard flow off, same audience mapper) |
| Renewal | CLI refreshes from the refresh token before each command | CLI requests a new token itself |
| Identity | The person, with their roles | The client's service-account user, with only the role granted to it |
| CLI | `gateway add ... --oidc-client-id openshell-cli` | `gateway add ... --oidc-client-id <confidential-id>` and `OPENSHELL_OIDC_CLIENT_SECRET=...` |

Scripts a person starts on their own machine reuse that person's login; the confidential
client is only needed when nobody is present. SDKs (Python/TS/Go) also do client credentials
directly, holding the secret and token in memory. Known open bug: CLI client-credentials
logins stop working when the access token expires (#4287).

## Tokens: lifetimes and the TUI

Access tokens are short (Keycloak default 5 min) because the gateway validates JWTs offline
and cannot revoke one early; the refresh token carries the long login (SSO idle/max). The
CLI refreshes automatically. **The TUI (`openshell term`) does not**: the CLI hands it one
bearer value at launch (`EdgeAuthInterceptor` with a fixed header) and it never reloads or
refreshes — after the access-token lifetime every action fails with
`invalid token: ExpiredSignature`. Unreported upstream as of 0.1.6 (siblings: #4515 Go SDK
caches an edge token forever, #4514 Go SDK never uses the refresh token).

Workarounds: restart the TUI (starting it after a fresh `openshell gateway login` gives a
full token lifetime); or raise the access-token lifespan **for the CLI client only**
(Keycloak client attribute `access.token.lifespan`, e.g. `28800` = 8 h). The trade-off:
a leaked token and a revoked role both stay effective for that long. The gateway's switch-
gateway path inside the TUI reloads the token from disk but bails if it has expired.

## mTLS and the local gateway

Package installs (RPM/deb) register the local gateway as
`openshell gateway add https://127.0.0.1:17670 --local --name openshell`; the CLI copies the
client bundle into `~/.config/openshell/gateways/<name>/mtls/`. On Kubernetes the chart
generates `openshell-client-tls` for transport trust; it is **not** user authentication
there — configure OIDC or a trusted proxy (`access-control.mdx`). With OIDC set, mTLS user
auth is off unless `[openshell.gateway.mtls_auth]` enables it explicitly.

## Supervisor identity

Supervisors never use user tokens: on Kubernetes the driver validates each supervisor's
projected ServiceAccount token (TokenReview, pod UID, Sandbox ownerReference) and the
gateway mints a sandbox-scoped JWT. Nothing to configure for normal deployments.
