# Keycloak: integrating apps and extending the server

For Keycloak 26.6.x. Source-of-truth for SPIs: `services/src/main/java/org/keycloak/...` in the upstream clone, plus the Server Developer Guide.

## TOC
1. [OIDC integration patterns](#oidc)
2. [SAML integration](#saml)
3. [Identity brokering (Keycloak as the front door for external IdPs)](#brokering)
4. [User federation: LDAP / AD / custom stores](#federation)
5. [Themes (login, account, admin, email)](#themes)
6. [Custom providers / SPIs](#spis)
7. [Admin REST clients (Java, JS, kcadm, Terraform)](#admin-clients)
8. [Workflows](#workflows)
9. [Multi-tenancy: realm-per-tenant vs Organizations](#multitenancy)
10. [MCP authorization server (CIMD)](#mcp)

---

## <a id="oidc"></a>1. OIDC integration patterns

Endpoints (per realm):
- Discovery: `/realms/{realm}/.well-known/openid-configuration`
- Auth: `/realms/{realm}/protocol/openid-connect/auth`
- Token: `/realms/{realm}/protocol/openid-connect/token`
- Userinfo: `/realms/{realm}/protocol/openid-connect/userinfo`
- Logout: `/realms/{realm}/protocol/openid-connect/logout`
- JWKS: `/realms/{realm}/protocol/openid-connect/certs`
- Token introspection: `/realms/{realm}/protocol/openid-connect/token/introspect`
- Token revocation: `/realms/{realm}/protocol/openid-connect/revoke`
- PAR: `/realms/{realm}/protocol/openid-connect/ext/par/request`
- Backchannel logout: `/realms/{realm}/protocol/openid-connect/k_logout`

### Picking the right flow

| App type                       | Flow                                           | Notes                                                                |
|--------------------------------|------------------------------------------------|----------------------------------------------------------------------|
| SPA (React/Vue/Angular)         | Authorization Code + PKCE (S256)               | Public client. No client secret. Use silent renewal via iframe or refresh token. |
| Mobile (iOS/Android)            | Authorization Code + PKCE                       | System browser / `ASWebAuthenticationSession`, NOT WebView.          |
| CLI / desktop                   | Authorization Code + PKCE + loopback redirect   | RFC 8252.                                                             |
| Server-side web app             | Authorization Code (confidential client)        | Optional PKCE adds defense-in-depth.                                 |
| Service-to-service              | Client Credentials                              | `private_key_jwt` > `client_secret`. Or **federated client auth** (26.6 GA) for K8s SAs. |
| Internal-to-internal token swap | Token Exchange (RFC 8693)                       | Enable per-client only when needed.                                   |
| Sender-constrained tokens       | DPoP                                            | Mobile/SPA where token theft is the threat.                           |
| Implicit flow                   | Don't.                                          | Removed from OAuth 2.1.                                               |
| ROPC / Direct Grants            | Don't, for human users.                         | OK for legacy migration / IoT device flows narrowly.                  |
| Device Authorization Grant      | When the device has no browser                  | TVs, CLI without loopback.                                            |

### Federated client authentication (GA in 26.6)

Lets the client authenticate using a JWT issued by an external trusted issuer instead of a Keycloak-managed secret. Two main use cases:
- **Kubernetes service accounts**: pod presents its projected SA token; Keycloak validates against the cluster's OIDC issuer.
- **Cross-issuer trust**: client app already authenticated to AWS/Google; their token serves as the "I am app X" proof.

Configure on the client → Credentials → Client Authenticator → "Federated JWT". Add an Identity Provider trusted to issue the assertion JWT. SPIFFE / SPIRE-issued JWTs work via the SPIFFE variant (preview).

This eliminates client-secret rotation entirely. Use it.

### DPoP (RFC 9449)

Per-client toggle: Advanced → "Use DPoP-bound tokens". When enabled, the access and refresh tokens are bound to the client's ephemeral key pair. The client signs a `DPoP` proof header on every API call, proving possession of the key. A stolen token without the key is useless.

Apps must use a DPoP-aware client library. The Java `keycloak-admin-client` ships with a DPoP filter; for JS the `oidc-client-ts` library has DPoP support.

---

## <a id="saml"></a>2. SAML integration

Endpoints (per realm):
- SSO: `/realms/{realm}/protocol/saml`
- Descriptor (metadata): `/realms/{realm}/protocol/saml/descriptor`

When SAML is the right answer:
- B2B with enterprise IdPs that haven't switched to OIDC (Okta, ADFS, PingFederate)
- Government / regulated environments mandating SAML (FedRAMP profiles, eIDAS)
- Existing app stack already SAML

Per-client SAML config knobs that matter:
- **Force POST Binding** — yes, unless the client genuinely needs Redirect.
- **Sign Documents / Assertions** — yes.
- **Encrypt Assertions** — yes if the client supports it (most do).
- **Client Signature Required** — require the client to sign AuthnRequests.
- **Force Name ID Format** — pin to `email` or `persistent` to avoid surprises across deployments.
- **IDP Initiated SSO URL Name** — leave blank unless the client demands IdP-initiated.

Don't enable both SAML and OIDC for the same logical app — pick one. SAML signing keys live under Realm Settings → Keys (same store as OIDC signing keys).

Step-up authentication for SAML is preview in 26.6 (`step-up-authentication-saml`). Use SAML `<RequestedAuthnContext>` to demand specific LoA.

---

## <a id="brokering"></a>3. Identity brokering

Realm → Identity Providers. Built-in IdP types:

| Type                | When to use                                             |
|---------------------|---------------------------------------------------------|
| OIDC v1.0           | Generic OIDC IdP                                        |
| Keycloak OIDC       | Other Keycloak realm — pre-fills metadata               |
| SAML v2.0           | SAML IdP — paste metadata XML or URL                    |
| Google / GitHub / Microsoft / Apple / GitLab / Facebook / Twitter / Bitbucket / Stack Overflow / Instagram / LinkedIn / OpenShift v3+v4 / PayPal | Social login presets |

Hardening checklist for any external IdP:
- "Trust Email" only when you trust the IdP's email verification.
- "Sync Mode" → `IMPORT` for one-shot creation; `FORCE` to overwrite local user attributes from IdP on every login (treat IdP as source of truth).
- Token Storage: store only what your app needs from the external IdP — extra tokens are extra attack surface.
- Redirect URIs in the external IdP must point at `/realms/{realm}/broker/{alias}/endpoint` — exact, not wildcard.
- For SAML brokers, validate the IdP signing cert is current and rotate alerts are in place.

### Identity Brokering APIs V2 (preview in 26.6)

Replaces the legacy "internal-to-external" Token Exchange path for retrieving tokens originally issued by the external IdP. New endpoint: `POST /realms/{realm}/broker/{alias}/token`. Apps that need to call the IdP's API on the user's behalf use this; v1 still works but is on its way out.

---

## <a id="federation"></a>4. User federation: LDAP / AD / custom stores

Realm → User Federation → Add provider.

LDAP/AD provider:
- **Edit Mode**: `READ_ONLY` (LDAP is master) / `WRITABLE` (Keycloak writes back) / `UNSYNCED` (local-only after import).
- **Import Users**: lazy import on first login (default) vs full sync on schedule.
- **Sync Settings**: full and changed-only sync schedules; bigger directories should set "Periodic Changed Users Sync" only.
- **Vendor**: pick `Active Directory` for AD-specific quirks (sAMAccountName, userAccountControl, password change semantics).
- **Trust Email** → match your sourcing reality.
- **Connection Pooling** → on for production.
- **Read Timeout / Connection Timeout** → set to bound failure modes.

26.6 added support for the LDAP server's `pwdChangedTime` attribute (standard in AD/eDirectory/OpenLDAP+ppolicy): when the LDAP-side policy says "password must change," Keycloak now sets a required-action `update-password` instead of letting the user in unchallenged. Enable via Advanced → "Enable LDAP password policy".

For non-LDAP backends (CRM, NoSQL, proprietary stores), implement the `UserStorageProvider` SPI. Capability interfaces let you opt into `UserLookupProvider` (login-only) up to `UserQueryMethodsProvider` + `UserRegistrationProvider` (full admin-console support).

---

## <a id="themes"></a>5. Themes

Theme types, their templates, and what they look like:

| Theme type | What it skins                          | Template engine                |
|------------|----------------------------------------|--------------------------------|
| `login`    | Login, register, password reset, 2FA  | FreeMarker (.ftl)              |
| `account`  | Account Console v3 (self-service)     | React / Vite (PatternFly)      |
| `admin`    | Admin Console                          | React / Vite (PatternFly)      |
| `email`    | Email templates (verify, reset)        | FreeMarker                     |
| `welcome`  | Welcome page (only seen pre-bootstrap)| FreeMarker                     |

Layout under `themes/src/main/resources/theme/`:
- `base/` — never customize directly; the no-op fallback.
- `keycloak/` and `keycloak.v2/` — the default themes.
- Your custom theme inherits via `theme.properties: parent=keycloak`.

Dev mode (turn off all caching during iteration):
```
--spi-theme--static-max-age=-1 --spi-theme--cache-themes=false --spi-theme--cache-templates=false
```

Production: bake the custom theme into your image as a JAR in `providers/`, then `kc.sh build` it in.

For the React UIs (account, admin), the source lives in `js/apps/account-ui/` and `js/apps/admin-ui/`. Vite dev server (`npm run dev`) connects to a running Keycloak for fast iteration.

---

## <a id="spis"></a>6. Custom providers / SPIs

The Server Developer Guide is the authoritative source. Most-extended SPIs:

| SPI                              | What it lets you do                                                            |
|----------------------------------|--------------------------------------------------------------------------------|
| `EventListenerProvider`          | React to user/admin events — Kafka, webhook, SIEM forwarding.                  |
| `Authenticator`                  | A custom auth step (custom 2FA, IP-based gating, CAPTCHA).                     |
| `RequiredActionProvider`         | A custom required action (accept ToS, complete profile).                       |
| `UserStorageProvider`            | Federate users from a non-LDAP store.                                          |
| `OIDCProtocolMapper` / `SAMLProtocolMapper` | Custom claim/attribute in tokens/assertions.                       |
| `ClientPolicyConditionProvider`  | Custom condition for client policies.                                          |
| `ClientPolicyExecutorProvider`   | Custom enforcement step.                                                       |
| `BruteForceProtector`            | Replace the brute-force tracker (e.g., to use a distributed cache).           |
| `RealmResourceProvider`          | A custom REST endpoint under `/realms/{realm}/<your-path>`.                   |
| `ThemeProvider`                  | Programmatic theme.                                                            |
| `KeyProvider`                    | Custom key source (HSM, KMS).                                                  |
| `TokenExchangeProvider`          | Custom token exchange logic.                                                   |

Packaging:
1. Implement `MyProviderFactory implements XProviderFactory<X>`.
2. Service file: `META-INF/services/org.keycloak.events.EventListenerProviderFactory` (or whichever SPI's factory).
3. Single fat-jar in `providers/`.
4. `kc.sh build` to register it.

Hot-reload: most SPIs require a build + restart. Themes, however, reload at runtime if you turn off the theme caches.

---

## <a id="admin-clients"></a>7. Admin REST clients

| Client                            | When to use                                                            |
|-----------------------------------|------------------------------------------------------------------------|
| `kcadm.sh`                        | Manual ops, scripts, ad-hoc.                                           |
| Java: `org.keycloak:keycloak-admin-client` (Maven) | Java apps that need to manage Keycloak.              |
| JS: `@keycloak/keycloak-admin-client` (npm) | Node.js / TS scripts. (Was broken in 26.6.0; **fixed in 26.6.1**.) |
| Terraform: `keycloak/keycloak` (the upstream-blessed registry namespace; `mrparkers/keycloak-orchestrator` is the legacy fork) | GitOps realm-as-code. |
| Operator `KeycloakRealmImport` CR | Kubernetes-native realm-as-code (create-or-replace).                   |
| Pulumi / Crossplane               | If you're already invested in those toolchains.                        |

For machine access, **don't reuse the `admin-cli` client** — it's a built-in public client in master and meant for human admin login. Create a dedicated confidential client per CI pipeline / per script, assign the `realm-management` roles you need (`view-realm`, `manage-users`, etc.), and use that.

```bash
# Service account auth pattern
kcadm.sh config credentials --server https://auth.example.com \
  --realm master --client my-cicd-client --client-secret '<...>'
```

For the Java SDK, `KeycloakBuilder.builder().grantType("client_credentials")` is the same shape.

---

## <a id="workflows"></a>8. Workflows

GA in 26.6. Realm-level YAML-defined automation triggered by events or schedules.

```yaml
# Workflow YAML (managed via admin REST or admin UI)
name: deactivate-stale-users
trigger: SCHEDULE      # or USER_CREATED, LOGIN_ERROR, ...
schedule: "0 0 3 * * *"
steps:
  - type: SetUserAttribute
    config:
      attribute: lastEvaluated
      value: "{{ now() }}"
  - type: HttpRequest
    config:
      url: https://hr.example.com/users/{{ user.id }}/active
      method: GET
  - type: ConditionalDisable
    config:
      condition: "response.body.active == false"
```

Use cases:
- Time-based account lifecycle (deactivate stale accounts, prompt MFA enrollment after N days)
- React to events without writing a Java EventListener
- Cleanup tasks (delete expired tokens, purge old sessions, prune disabled users after N days)

Step types in 26.6 source under `services/src/main/java/org/keycloak/models/workflow/`. For complex business logic, keep using a custom EventListener — workflows are for declarative, low-code orchestration.

---

## <a id="multitenancy"></a>9. Multi-tenancy: realm-per-tenant vs Organizations

| Pattern             | Strengths                                                            | Weaknesses                                                              |
|---------------------|----------------------------------------------------------------------|-------------------------------------------------------------------------|
| Realm-per-tenant    | Maximum isolation; per-tenant customization; clear blast radius     | Operational overhead grows linearly with tenants; cache memory per realm |
| Organizations (GA in 26.3+) | Single realm, multiple tenants share infra; per-org IdP/branding     | Less isolation; per-org customization more constrained                    |

26.6 added **organization groups** — group hierarchies scoped to an Organization, with mappers that auto-place federated users into the right org-group based on IdP claims. Significantly closes the gap with realm-per-tenant for most B2B SaaS scenarios.

Decision rule of thumb: ≤ 50 tenants and they're meaningfully different → realms. ≥ 50 tenants or they're variations of the same product → Organizations.

---

## <a id="mcp"></a>10. MCP authorization server (CIMD)

Keycloak can act as an OAuth 2.1 authorization server for Model Context Protocol servers. The required parts (RFC 8414 metadata, RFC 7591 dynamic client registration, OAuth 2.1) are GA. **OAuth Client ID Metadata Document (CIMD)** — the spec MCP versions 2025-06-18+ require — is **experimental** in 26.6 (`--features=cimd`).

What CIMD does: lets MCP clients identify themselves with a URL (`client_id=https://vscode.dev/mcp-client`) instead of pre-registering. Keycloak fetches metadata from the URL and validates.

Not all MCP versions are fully supported — RFC 8707 Resource Indicators (required by MCP 2025-06-18+) is not yet in Keycloak. Workaround: use scopes to encode resource targets, register specific clients ahead of time. Track via `gh search issues --repo keycloak/keycloak "RFC 8707"`.

Reference: `https://www.keycloak.org/securing-apps/mcp-authz-server`.
