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
12. [Recent CVEs — pull the live list](#cves)

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

Offline-session lifecycle has had subtle bugs around how the session-type of an offline_access refresh token is tracked when scope is requested without offline_access. Stay on a current 26.6.x patch and confirm fixed-version claims against the release-notes body (`gh release view <tag> --repo keycloak/keycloak --json body`).

---

## <a id="flows"></a>4. Authentication flows

**Authentication → Flows**. The built-in Browser, Direct Grant, Reset Credentials, and Registration flows can't be edited directly — clone them, then assign the clone to the realm.

Things to know:

- **Conditional sub-flows** are how step-up (LoA / ACR) works. Mark a sub-flow `Conditional`, add a `Condition - Level Of Authentication` execution to gate it.
- **Identity-first login** (separate username and password screens) is now the default. This flow has historically been the surface for user-enumeration-via-timing findings; stay current and check the advisory feed (§CVE table) before asserting a given version is unaffected.
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

Redirect-URI validation bypass and SSRF-via-redirect classes recur across Keycloak releases (the HTTP client used for IdP discovery, JWKS, user-info, and theme remote resources is the usual surface). When advising on a specific version, pull the current advisory set with `gh api repos/keycloak/keycloak/security-advisories` rather than recalling CVE IDs — see the §CVE table below for how. Customised IdP-discovery / JWKS URL resolution should be retested after any redirect-handling fix.

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

## <a id="cves"></a>12. Recent CVEs — pull the live list, don't recall IDs

CVE identifiers and fixed-in versions are exactly the kind of detail that must never be quoted from memory: they get invented, mis-dated, or attributed to the wrong release. **The canonical source is the GitHub Security Advisory feed.** Run these before answering any "is version X vulnerable" / "what did version X fix" question:

```bash
# Full advisory feed (CVE id, severity, summary, fixed versions) — newest first
gh api repos/keycloak/keycloak/security-advisories \
  --jq '.[] | {cve: .cve_id, ghsa: .ghsa_id, sev: .severity, published: .published_at, summary: .summary}'

# What a specific release closed (the release body lists its Security fixes section)
gh release view 26.7.0 --repo keycloak/keycloak --json body --jq '.body'

# Confirm whether a given CVE applies and its patched range
gh api repos/keycloak/keycloak/security-advisories \
  --jq '.[] | select(.cve_id=="CVE-XXXX-YYYYY") | {sev: .severity, vulns: .vulnerabilities}'
```

Cross-check the `vulnerabilities[].patched_versions` field against the deployed version to decide if an upgrade is required. Map each advisory to the relevant hardening section above (redirect-URI / SSRF findings → §9; flow/timing findings → §4; token/session findings → §3 and §6) when advising on remediation.

**As of 2026-07-21, latest stable is 26.7.0 (2026-07-09).** The 26.6 line ran on
to 26.6.4 (2026-06-26); 26.6.2, 26.6.3 and 26.6.4 are all security batches.
Quote each version's CVE set from its own `gh release view <version>` body, not
from memory.

**The advisory feed will not tell you the fix version.** Every advisory probed
on 2026-07-21 had an empty `first_patched_version`, and eight advisories share a
`published_at` of 2026-06-26 while only one of them (CVE-2026-9099) appears in
that day's 26.6.4 notes. Disclosure date is not fix version — read the release
bodies of each candidate version to map a CVE to the release that closes it.

For deployments stuck on 26.4.x/26.5.x for compatibility reasons, Red Hat backports security fixes to the RHBK LTS line (26.0 has long-term support). Upgrade, but if you can't, RHBK is the bridge.
