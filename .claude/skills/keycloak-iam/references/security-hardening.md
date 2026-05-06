# Keycloak security hardening

For Keycloak 26.6.x. Source-of-truth for behavior: `docs/documentation/server_admin/topics/threat/*.adoc`, `docs/documentation/server_admin/topics/clients/client-policies.adoc`, and the realm settings UI.

## TOC
1. [Realm-level password policies](#password-policies)
2. [Brute-force detection](#brute-force)
3. [Session and token lifespans](#sessions)
4. [Authentication flows](#flows)
5. [Client-level security](#clients)
6. [Token security (signing, rotation, DPoP)](#tokens)
7. [Client policies and security profiles (FAPI, OAuth 2.1)](#client-policies)
8. [Fine-Grained Admin Permissions v2](#fgap)
9. [Redirect URI / SSRF / open-redirect surface](#ssrf)
10. [CSP, X-Frame-Options, Security Defenses](#csp)
11. [TLS hardening and FIPS](#tls)
12. [Recent CVEs (26.4 → 26.6.1)](#cves)

---

## <a id="password-policies"></a>1. Realm-level password policies

Set under **Realm Settings → Authentication → Policies → Password Policy**.

| Policy                       | Recommended baseline                                                                                |
|------------------------------|-----------------------------------------------------------------------------------------------------|
| Hashing Algorithm            | `argon2` (default since 24.x; ~5 iterations). On FIPS, `pbkdf2-sha512` with 210k iterations.        |
| Length                       | ≥ 12 (NIST SP 800-63B current guidance).                                                            |
| Digits / Lowercase / Uppercase / Special | Set when compliance requires it; NIST 800-63B explicitly does NOT, and discourages forced rotation. |
| Not Username / Not Email     | On.                                                                                                  |
| Password History             | ≥ 5 when rotation is required; otherwise leave off.                                                  |
| Password Blacklist           | Drop OWASP / SecLists common-passwords file in `data/password-blacklists/`. **26.6+ auto-reloads it on change** — no restart needed. Configure check interval via `--spi-password-policy--password-blacklist--check-interval-seconds`. |
| Regex Pattern                | Use sparingly — over-strict regex frustrates users and causes weaker passwords overall.              |
| Maximum Authentication Age   | For sensitive operations (password change, MFA changes), force re-auth within N seconds.            |

Don't increase hash iterations beyond defaults without measuring CPU impact at peak login load — high iteration counts at scale can swamp CPU.

---

## <a id="brute-force"></a>2. Brute-force detection

**Realm Settings → Security Defenses → Brute Force Detection**. Off by default — turn it on.

Three modes:

- **Permanent Lockout**: account stays disabled until admin re-enables.
- **Temporary Lockout**: account locked for an exponentially increasing window after each batch of failures.
- **Mixed**: temporary lockouts up to N times, then permanent.

Sensible production defaults for "Temporary":

| Setting                          | Value     |
|----------------------------------|-----------|
| Max Login Failures               | 30        |
| Quick Login Check Milliseconds   | 1000      |
| Minimum Quick Login Wait         | 60s       |
| Wait Increment Seconds           | 60s       |
| Max Wait                         | 900s      |
| Failure Reset Time               | 12h       |

26.x split brute-force tracking into separate counters for password, OTP, and recovery codes. Previously a successful password attempt would reset the OTP failure counter — now it doesn't, so credential-stuffing attempts on the OTP field don't get cheap reset.

The lockout response is intentionally generic ("Invalid username or password") to avoid enumerating which usernames are locked.

---

## <a id="sessions"></a>3. Session and token lifespans

**Realm Settings → Sessions** and **→ Tokens**:

| Setting                              | Recommended                  |
|--------------------------------------|------------------------------|
| SSO Session Idle                     | 30 min                       |
| SSO Session Max                      | 10 hours                     |
| Access Token Lifespan                | 1–5 min                      |
| Access Token Lifespan For Implicit Flow | Don't use implicit; if you must, ≤ 5 min |
| Refresh Token Lifespan               | 30 min – 24 hours, depending on app |
| Offline Session Idle                 | 30 days                      |
| Offline Session Max Limited          | enable; cap at e.g. 60 days  |

Short access-token TTLs are the easy lever. Refresh-token rotation (per-client setting) limits replay damage if a refresh token is stolen.

26.6.1 fixed a subtle bug (`#47776`) where the session-type of an offline_access refresh token was incorrectly tracked when scope was requested without offline_access — this affected offline session lifecycle. Make sure to upgrade.

---

## <a id="flows"></a>4. Authentication flows

**Authentication → Flows**. The built-in Browser, Direct Grant, Reset Credentials, and Registration flows can't be edited directly — clone them, then assign the clone to the realm.

Things to know:

- **Conditional sub-flows** are how step-up (LoA / ACR) works. Mark a sub-flow `Conditional`, add a `Condition - Level Of Authentication` execution to gate it.
- **Identity-first login** (separate username and password screens) is now the default. CVE-2026-4633 fixed user enumeration via small response-time differences on this flow — upgrade to 26.6.1.
- **Required actions** (Configure OTP, Verify Email, Update Profile, …) are independent of flows — they fire on next login regardless of which flow handled auth.
- **Step-up authentication for SAML** is preview in 26.6 (`step-up-authentication-saml` feature). For OIDC it's been GA for several releases.

When customizing flows, **clone first**, edit the clone, and only switch the realm to use it after testing. The "default" assignments are how the realm picks them.

---

## <a id="clients"></a>5. Client-level security

| Topic                          | Production guidance                                                                                |
|--------------------------------|----------------------------------------------------------------------------------------------------|
| Public vs Confidential         | Confidential where possible. Public is for SPAs and native apps where no secret can be stored.    |
| Client Authenticator           | `private_key_jwt` (signed JWT with client's private key) > `client_secret_jwt` > `client_secret_basic/post`. |
| Federated Client Authentication| Now GA (26.6). Use external OIDC issuer or K8s service-account JWT instead of a client secret. Eliminates secret rotation. |
| PKCE                           | Mandatory for public clients. Set `pkce.code.challenge.method = S256` in client attributes.        |
| Bearer-only                    | Deprecated. Use confidential client + service-account roles instead.                                |
| Standard Flow / Implicit Flow / Direct Access Grants / Service Accounts | Disable each one not in use.                          |
| DPoP                           | Enable for SPAs and mobile (`Require DPoP bound tokens` in client → Advanced). Token theft becomes useless without the bound key. |
| mTLS for direct grants         | If you have a hardware-bound device flow, use mTLS authenticator instead of secrets.               |
| Valid redirect URIs / web origins | Exact URLs, no `*` wildcards beyond paths. Wildcards in scheme/host are SSRF bait.              |

**Token Exchange** (RFC 8693, GA in 26.5+) is powerful but a foot-gun: enable per-client only when you specifically need cross-client / cross-realm exchange. The default of "off everywhere" is correct for most realms.

---

## <a id="tokens"></a>6. Token security

**Realm Settings → Keys**: the realm's signing keys.

| Key consideration              | Guidance                                                                                  |
|--------------------------------|-------------------------------------------------------------------------------------------|
| Algorithms                     | RS256 / PS256 / ES256 / EdDSA. ES256/EdDSA are smaller and faster.                       |
| Rotation                       | Keycloak auto-rotates. Old keys remain in JWKS for validation until their `exp`.          |
| RSA key size                   | 2048 minimum, 4096 if you need belt-and-suspenders. ECC (ES256) is preferred for new realms in 26.5+. |
| Encrypted ID tokens            | Enable per-client if ID tokens carry PII you don't want in browser history.                |
| Audience claims                | Always set explicit audience. Default `aud` of `account` is a smell.                       |

Refresh-token rotation is per-client (Advanced → Revoke refresh token → On). Each refresh returns a new refresh token; the old one is invalidated. If two requests race to refresh, only the first wins — the loser gets a `400`.

---

## <a id="client-policies"></a>7. Client policies and security profiles

**Realm Settings → Client Policies**. Two parts:

- **Profiles**: a bundle of *executors* (concrete enforcement: PKCE required, signed request object required, redirect URI scheme HTTPS, …)
- **Policies**: a bundle of *conditions* (which clients does the policy apply to: by client role, scope, attribute, IP CIDR, …) plus a list of profiles to enforce.

Built-in **global profiles** (don't edit; reference from your policies):

| Profile                            | When to use                                                                            |
|------------------------------------|----------------------------------------------------------------------------------------|
| `oauth2-1`                         | New OAuth 2.1 deployments (PKCE, no implicit, no ROPC, refresh-token rotation).        |
| `fapi-1-baseline`                  | Open Banking baseline (TLS, PAR, signed request).                                      |
| `fapi-1-advanced`                  | Open Banking advanced (mTLS, hybrid flow + ID-token signature).                        |
| `fapi-2-security-profile`          | FAPI 2.0 (DPoP mandatory).                                                             |
| `fapi-2-message-signing`           | FAPI 2.0 + signed request/response messages.                                           |
| `fapi-ciba`                        | Decoupled / out-of-band auth.                                                          |
| `cdr-baseline`                     | Australian Consumer Data Right.                                                        |

Apply to a subset of clients via a Policy with a **client-roles** condition (so you can mark `fapi` as a role on the relevant clients).

The full list of executors lives in the source under `services/src/main/java/org/keycloak/services/clientpolicy/executor/`.

---

## <a id="fgap"></a>8. Fine-Grained Admin Permissions v2

Enable `admin-fine-grained-authz:v2` (build-time). Then under **Realm Settings → Admin Permissions** (only visible when feature is on).

FGAP v2 lets you grant a delegated admin scoped permissions on Users, Groups, Clients, Roles, Organizations. It's the right answer for "I want this team to manage *their* clients only" — scope a permission to a subset of resources via a policy.

26.6 adds the `manage-membership-of-members` scope on Groups: when you grant a delegated admin `manage-membership` on Group A and `manage-membership-of-members` on Group B, they can move users between A and B but not into other groups. Useful for tiered org structures.

Notes:
- Server-level realm-admin and master-realm admin **bypass FGAP entirely** — audit who has those.
- Permissions don't transit: `manage` does NOT imply `view`. Grant both if you need both.
- FGAP v1 still works but is deprecated; new realms should default to v2.

---

## <a id="ssrf"></a>9. Redirect URI / SSRF / open-redirect surface

The most-exploited surface in any IdP. Rules:

1. **Valid Redirect URIs** must be exact paths under exact origins. `https://app.example.com/callback` good; `https://app.example.com/*` acceptable (path wildcard); `https://*.example.com/*` is bad (subdomain wildcard — registers any subdomain takeover as a redirect target).
2. **Valid Post Logout Redirect URIs** is a separate list and matters as much. Don't leave blank — Keycloak will refuse the post-logout redirect (correct, but apps break).
3. **Web Origins** controls CORS; tighter than redirect URIs.
4. The **Secure Client URIs** executor (in client policies) rejects `http://` (non-loopback), wildcards, IP-literal hosts. Apply it to all production clients.

### CVE-2026-4366 (fixed in 26.6.1)

SSRF via HTTP redirect handling — Keycloak's HTTP client followed redirects without re-validating against the configured allowlist. Affected the parts of the server that fetch external URLs (IdP discovery, JWKS, user-info, theme remote resources). Fix re-applies allowlist on every redirect hop. **No user-side action beyond upgrading**, but if you've customized any IdP discovery / JWKS URL resolution, retest.

### CVE-2026-4633 (fixed in 26.6.1)

User enumeration via identity-first login — small timing differences in the response let an attacker probe whether a username exists. Fix introduces constant-time path handling. **Action**: upgrade; review your login flow if you cloned the built-in identity-first flow before 26.6.1.

---

## <a id="csp"></a>10. CSP, X-Frame-Options, Security Defenses

**Realm Settings → Security Defenses → Headers**:

| Header                       | Default                                                          | Hardened                                                  |
|------------------------------|------------------------------------------------------------------|------------------------------------------------------------|
| X-Frame-Options              | `SAMEORIGIN`                                                     | `DENY` if you don't need to embed Keycloak in iframes.    |
| Content-Security-Policy      | `frame-src 'self'; frame-ancestors 'self'; object-src 'none';`   | Tighten `frame-ancestors` to a fixed list; consider `default-src 'none'` with explicit allowlists. |
| Content-Security-Policy-Report-Only | empty                                                     | Use first to find what your app needs before enforcing.    |
| X-Content-Type-Options       | `nosniff`                                                        | Keep.                                                      |
| Referrer-Policy              | `no-referrer`                                                    | Keep.                                                      |
| Strict-Transport-Security    | `max-age=31536000; includeSubDomains` (when via HTTPS)           | Add `preload` if your domain is HSTS-preloaded.            |

Don't set CSP `unsafe-inline` for scripts — the admin console / account console don't need it. If a custom theme breaks under strict CSP, fix the theme; don't loosen the policy.

---

## <a id="tls"></a>11. TLS hardening and FIPS

| Knob                              | Recommended                                          |
|-----------------------------------|------------------------------------------------------|
| `--https-protocols`               | `TLSv1.3` (drop 1.2 for new deployments where clients allow). |
| `--https-cipher-suites`           | Leave default; Keycloak inherits modern JDK defaults. Override only for compliance. |
| `--https-client-auth`             | `none` for the public listener; `required` on a separate listener if you need mTLS for direct-grant. |
| Certificate rotation              | Cert-manager + reload via `--https-certificates-reload-period=1h` (default). |

### FIPS

`fips:` mode (build-time `--features=fips`) puts Keycloak on a FIPS-validated Bouncy Castle JCA. Constraints:

- The container image stays on JDK 21 because Bouncy Castle FIPS is certified there, not on 25 yet.
- Argon2 is not FIPS — falls back to PBKDF2-SHA512.
- Some algorithms (Ed25519 in some configs) are unavailable.

Read `docs/guides/server/fips.adoc` for the full list before flipping the switch.

---

## <a id="cves"></a>12. Recent CVEs (26.4 → 26.6.1)

Always check `gh api repos/keycloak/keycloak/security-advisories` for the canonical list. The table below is a snapshot as of May 2026. **High-severity items in bold.**

| CVE              | Severity | Affected     | Fixed in   | One-liner                                                                                |
|------------------|----------|--------------|------------|------------------------------------------------------------------------------------------|
| **CVE-2026-4366** | High    | <26.6.1     | 26.6.1     | Blind SSRF via HTTP redirect handling (in core HTTP client used for IdP discovery/JWKS). |
| CVE-2026-4633     | Medium  | <26.6.1     | 26.6.1     | User enumeration via identity-first login (timing).                                       |
| **CVE-2026-3429** | High    | <26.5.4     | 26.5.4     | LoA validation skipped on credential delete when client overrides flow.                   |
| CVE-2026-0707     | High    | <26.5.4 (subset) | 26.5.4 | Authorization Bearer token validation gap.                                                 |
| CVE-2025-66021    | Medium  | <26.5.0     | 26.5.0     | OWASP HTML Sanitizer XXE.                                                                  |
| CVE-2024-47072    | Medium  | <26.5.0     | 26.5.0     | XStream DoS (stack overflow on crafted input).                                             |
| CVE-2024-11734    | Medium  | <26.4.x     | 26.4.x     | DoS via unbounded string concat in security headers.                                       |
| CVE-2024-10270    | Medium  | <26.4.x     | 26.4.x     | DoS via unbounded recursion in token processing.                                           |
| CVE-2023-3597     | High    | older        | 26.4.x+    | Secondary-factor bypass when LoA not enforced.                                             |
| CVE-2023-6291     | Medium  | older        | 26.4.x+    | Redirect URI bypass.                                                                       |

For deployments stuck on 26.4.x/26.5.x for compatibility reasons, Red Hat backports security fixes to the RHBK LTS line (26.0 has long-term support). Upgrade, but if you can't, RHBK is the bridge.

When asked "is version X vulnerable to Y," **always cross-check** with `gh api repos/keycloak/keycloak/security-advisories` and the `gh release view <tag>` body — this table is a starting point, not the source of truth.
