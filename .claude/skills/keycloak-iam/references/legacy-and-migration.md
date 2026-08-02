# Keycloak legacy versions (16.x–23.x) and migration verification

Two jobs: (1) operate/identify old Keycloak instances — including the WildFly
("-legacy") distribution — and (2) verify that a realm migrated across versions
still carries the same effective configuration.

Source of truth for per-version breaking changes: upstream
`docs/documentation/upgrading/topics/changes/changes-<version>.adoc` — one file
per release, 16.0.0 through current, in `keycloak/keycloak`. This file distills
the operator-relevant subset; fetch the adoc when you need the full text:
`gh api repos/keycloak/keycloak/contents/docs/documentation/upgrading/topics/changes --jq '.[].name'`.

## TOC
1. [Identifying an unknown Keycloak](#identify)
2. [WildFly vs Quarkus operational map](#distributions)
3. [Upgrade ladder: what breaks at each version](#ladder)
4. [Migration verification: comparing realm/client config across versions](#compare)
5. [Automation against legacy versions](#automation)

---

## <a id="identify"></a>1. Identifying an unknown Keycloak

Fastest, works on any version — ask kcadm inside the pod/container:

```bash
# Try both paths; prints e.g. "Keycloak - Version 19.0.3"
kubectl exec <pod> -- sh -c \
  'for p in /opt/keycloak/bin /opt/jboss/keycloak/bin; do
     [ -x $p/kcadm.sh ] && $p/kcadm.sh help 2>&1 | grep -m1 Version && break; done'
```

Indirect tells when you only have network/browser access:

| Observation                                   | Conclusion                                  |
|-----------------------------------------------|---------------------------------------------|
| URLs contain `/auth/`                          | WildFly distribution, or Quarkus with `--http-relative-path=/auth` (common on migrated installs) |
| No `/auth` prefix                              | Quarkus 17+                                 |
| Old dense AngularJS admin console              | ≤ 20 (stock ≤ 18; new console default in 19)|
| New PatternFly/React admin console             | ≥ 19 (or an 18 opted into `keycloak.v2`)    |
| New console, no fallback theme available       | ≥ 21 (old console removed)                  |
| kcadm at `/opt/jboss/keycloak/bin/`            | WildFly distribution (any version)          |
| kcadm at `/opt/keycloak/bin/`                  | Quarkus distribution                        |
| Image tag ends in `-legacy`                    | WildFly build (17.x–19.x published both)    |

The WildFly line ended at **19.0.3-legacy** (late 2022) — any `-legacy` image
found in the field is unpatched since then; treat migration as urgent but
don't lecture.

---

## <a id="distributions"></a>2. WildFly vs Quarkus operational map

| Concern            | WildFly (≤19 `-legacy`)                          | Quarkus (17+)                                  |
|--------------------|--------------------------------------------------|------------------------------------------------|
| Install root       | `/opt/jboss/keycloak/`                           | `/opt/keycloak/`                               |
| Context path       | `/auth` always                                   | none (restore: `--http-relative-path=/auth`)   |
| Config             | `standalone.xml`, `standalone-ha.xml`, jboss-cli | `conf/keycloak.conf`, CLI args, `KC_*` env vars |
| Custom providers   | `standalone/deployments/` (hot deploy, EAR/WAR)  | `providers/` jar + `kc.sh build` (no hot deploy) |
| Initial admin      | `KEYCLOAK_USER`/`KEYCLOAK_PASSWORD` (container) or `add-user-keycloak.sh` | 17–25: `KEYCLOAK_ADMIN`/`KEYCLOAK_ADMIN_PASSWORD`; 26+: `KC_BOOTSTRAP_ADMIN_USERNAME`/`KC_BOOTSTRAP_ADMIN_PASSWORD` |
| Health/metrics     | `/auth/realms/master` + WildFly management :9990 | 17–18: `/q/health`; 19+: `/health`, `/metrics`; 25+: management port 9000 |
| K8s operator       | `keycloak.org/v1alpha1` (separate Client/User/Realm CRDs, Deployment) | `k8s.keycloak.org/v2alpha1` (StatefulSet, `KeycloakRealmImport`) |
| Proxy config       | `PROXY_ADDRESS_FORWARDING=true`                  | `--proxy` (≤23) → `--proxy-headers` (24+)      |

Current upstream docs retro-apply modern env-var names to old guides — when
reading `migrating-to-quarkus` on `main`, remember the bootstrap-admin vars
were `KEYCLOAK_ADMIN`/`KEYCLOAK_ADMIN_PASSWORD` until 26.0 renamed them.

There is no automated config migration WildFly→Quarkus: re-express
`standalone.xml` intent as `keycloak.conf`/CLI options, move providers to
`providers/`, and replace the old operator's CRs with a fresh `Keycloak` CR +
`KeycloakRealmImport`. The old and new operators can coexist during cutover
(use fully-qualified CRD names).

---

## <a id="ladder"></a>3. Upgrade ladder: what breaks at each version

The DB schema migrates automatically (Liquibase) on first boot of the newer
version — multi-hop jumps are supported, but each version below has changes
you must pre-check. Back up the DB before every hop; Liquibase changes are
one-way.

### 16 → 17 (the distribution switch)
- Quarkus becomes the default distribution; everything in §2 applies.
- `keycloak.properties` → `keycloak.conf`; per-feature keys → `--features`; `h2-mem`/`h2-file` → `dev-mem`/`dev-file`.
- Liquibase 3.5.5 → 4.6.2: custom Liquibase extensions re-register via `ServiceLoader`.
- Client-policy JSON: client-scopes condition field `"scope"` → `"scopes"`.

### 18
- OIDC logout: `redirect_uri` param dead → `post_logout_redirect_uri` + `id_token_hint`.
- `upload-scripts` removed: realms with REST-uploaded scripts (script mappers/authenticators/JS policies) **block** — convert to deployed script-provider jars before upgrading.
- `metrics-enabled` no longer implies health: set `health-enabled=true` too.
- New realm-default `acr` client scope — added to *new* clients only; existing clients silently lose the automatic `acr` claim (attach manually if step-up auth matters).

### 19
- `/q/health` & `/q/metrics` → 404; probes move to `/health*`, `/metrics` (readiness DB check requires metrics enabled as well).
- New admin console default; custom admin themes must extend `keycloak.v2`.
- `--auto-build` deprecated; `--optimized` introduced for prebaked images.
- New operator switches Deployment → StatefulSet: delete + recreate the Keycloak CR (no in-place migration).
- 19.0.2: UserInfo endpoint requires `openid` scope (403 otherwise) and returns RFC 6750 challenges instead of JSON error bodies.

### 20
- Operator CR schema breaks wholesale: `serverConfiguration` → `additionalOptions`, `disableDefaultIngress` → `ingress.enabled: false`, new `http`/`hostname` blocks, `INSECURE-DISABLE` removed. Hand-migrate the CR.
- H2 1.x files unreadable by H2 2.x (dev only).

### 21
- All metric names change (SmallRye → Micrometer): every dashboard/alert breaks.
- SAML SHA1 signatures fail on Java 17 unless the JDK security policy is relaxed.
- Old admin console removed; `curl` removed from the container image.
- 21.0.0–21.0.1 write user attribute `TERMS_AND_CONDITIONS` (uppercase); 21.0.2 reverts to `terms_and_conditions` — check both in exports.
- 21.1.0: service-account default mapper claim `clientId` → `client_id`.

### 22
- Jakarta EE namespace switch: every custom provider needs recompilation (`javax.*` → `jakarta.*`).
- Built-in `http challenge` flow + `basic-auth`/`no-cookie-redirect` authenticators removed — migration **blocks** if any realm/broker/client-override uses them; audit first.
- `export`/`import` commands now auto-build: add `--optimized` in scripts.
- Proxy mode `passthrough` stops parsing forwarding headers.

### 23
- `kc.sh` drops shell-eval: double-escaped args and single-string invocations (`kc.sh "start --x"`) break, including in Dockerfiles.
- `RegistrationProfile` form action removed from every realm's registration flow.
- Valid redirect URIs: exact case-sensitive matching (23.0.2) — case-variant redirect entries needed.
- `partial-export` REST/kcadm now requires `manage-realm` (was `view-realm`).
- Admin-console translations un-namespaced (DB-stored overrides must drop prefixes).

### 24
- User profile always-on: default validators appear, *User Profile Enabled* switch becomes *Unmanaged attributes* (ON→OFF, OFF→ON mapping).
- New `hmac-generated-hs512` key component in every realm; migrated realms keep the old HS256 component alongside until manually removed.
- Password hashing defaults jump to pbkdf2-sha512 @ 210k iterations: ~5× CPU per password login, one-off re-hash load after upgrade. Pin old algorithm in password policy if capacity-constrained.
- `--proxy` deprecated → `--proxy-headers` (+ `--http-enabled true` for former `edge`).
- Admin User API becomes full-replace (24.0.4): omitting writable attributes on update **deletes** them — audit automation before this hop.
- Infinispan cache metrics renamed to labeled form (dashboards again).

### 25
- Hostname v2 default: `hostname-url`, `hostname-path`, `hostname-port`, `hostname-strict-backchannel` removed (→ single full-URL `hostname`, `hostname-backchannel-dynamic`); escape hatch `--features=hostname:v1` (gone in 26).
- `/health` + `/metrics` move to the management port (9000): probes and scrape configs again.
- Default password hashing → Argon2 (re-hash burst on next logins); default GC → G1GC.
- `persistent-user-sessions` (preview): enabling it **at the 25 hop** is the only way live sessions survive 26's cache-format switch — this is a one-shot decision.
- New `basic` client scope auto-added to the realm AND all existing OIDC clients — the single largest export diff of the whole range; `session_state` claim dropped from tokens, `nonce` only in ID token.

### 26.0
- Infinispan marshalling → Protostream: **all caches cleared** on upgrade; sessions survive only if persisted on 25 first.
- `KEYCLOAK_ADMIN`/`KEYCLOAK_ADMIN_PASSWORD` → `KC_BOOTSTRAP_ADMIN_USERNAME`/`KC_BOOTSTRAP_ADMIN_PASSWORD`; `--proxy` and `hostname:v1` removed outright.
- `start --optimized` without a prior matching build now **fails startup** (was a warning).
- `GET /admin/realms/{realm}` stops returning `identityProviders` (realm *exports* still include them — don't confuse the two when comparing).
- Realm-level LDAP `connectionPooling*` settings silently ignored (system properties only).

### 26.1 – 26.3
- 26.1: new realm client scope `service_account` takes over the `client_id`/`clientHost`/`clientAddress` mappers from clients' dedicated scopes.
- 26.2: standard Token Exchange + FGAP v2 enabled by default; embedded-cache mTLS on by default (service meshes must allow pod-to-pod mTLS); Operator creates NetworkPolicies; `X-Forwarded-Host` loses request-port fallback.
- 26.3: SPI option format gains double-dash separators (`spi-x--y--z`); only master-realm `admin` can assign admin roles (relaxed again in 26.4.3); brute-force-locked users now report `enabled=true` via Admin API — check attack-detection endpoint instead.

### 26.4 – 26.5
- 26.4: client-session cache key changed — **no mixed-version cluster** during the hop; SAML-encrypting clients gain explicit encryption-algorithm attributes during migration; PostgreSQL gets `targetServerType=primary` automatically.
- 26.5: realm/client create/update/**import** now fails validation when client session idle/max exceed realm SSO settings — a previously-valid old export can refuse to import (fix the values before migrating); new authz-enabled clients no longer get Default Resource/Policy/Permission; PostgreSQL 13 support removed; `session_state`/`sid` no longer UUID-shaped.

### 26.6
- `OFFLINE_CLIENT_SESSION` gains `REALM_ID`, backfilled by copy (~7500 rows/s on PG) — **requires downtime**, no mixed-version operation.
- 26.6.0's migration wrongly injected the `Organization` sub-flow into *custom* browser flows (fixed in 26.6.1; remove manually after upgrading through it).
- Operator CRDs gain `v2beta1`; token introspection validates `aud` (26.6.2); redirect-URI wildcards no longer match into hostnames (26.6.3); admin roles granted via protocol mappers no longer grant Admin API access (26.6.5).

### 26.7
- Silent export rewrites during migration: `is.dynamic.scope` → `is.parameterized.scope` (+ new required `parameterized.scope.type`), realm `displayName` promoted to a column (>255 chars truncated), *Configure OTP*/*Update password* required actions reordered in existing realms, LDAP binary mappers pinned to explicit `base64`, WebAuthn `RequireResidentKey` realm attributes renamed to `ResidentKey` variants.
- Identity Provider `alias` becomes immutable via Admin API (400 on update).

---

## <a id="compare"></a>4. Migration verification: comparing realm/client config across versions

Goal: prove a migrated realm (old instance → new instance, any hop) still has
the same *effective* settings, separating three diff classes: (a) instance
noise (UUIDs, ordering), (b) expected version-migration changes, (c) real
drift/loss — only (c) is a problem.

### Step 1 — export both sides identically

```bash
# Either side, any version 17+ (WildFly: /opt/jboss/keycloak/bin, add /auth):
kcadm.sh create "realms/<realm>/partial-export?exportClients=true&exportGroupsAndRoles=true" \
  -o > realm-export.json
```

Gotchas that produce silently-wrong exports:
- The export options are **query parameters**, not body fields — `-s exportClients=true` is silently ignored and you get a realm with no clients. Put them in the URL.
- On 23+ `partial-export` needs `manage-realm` permission (plus `view-clients` / `query-groups` for the respective sections); a view-only service account gets a realm-only export or 403.
- `kc.sh export --realm <r>` (Quarkus) / `standalone.sh -Dkeycloak.migration.action=export` (WildFly) are the offline alternatives; they additionally include components/keys. Compare like with like — same export method on both sides.
- Realm exports omit user passwords/secrets by design either way; this recipe compares *configuration*, not credentials.
- If the migration itself goes via export/import: on 26.5+ the import **fails validation** when any client's session idle/max exceeds the realm SSO settings — values that were legal when exported. Fix them in the source realm (or the export) first.

### Step 2 — normalize and diff

Use `assets/compare/kc-normalize.jq` (strips `id`/`containerId`, volatile
attributes; sorts every named-object array):

```bash
jq -S -f kc-normalize.jq old-export.json > old.norm.json
jq -S -f kc-normalize.jq new-export.json > new.norm.json
diff old.norm.json new.norm.json
```

Verified behavior: regenerated UUIDs and reordered arrays diff to empty;
a single flipped boolean (e.g. one client's `serviceAccountsEnabled`)
surfaces as exactly one diff hunk.

### Step 3 — interpret remaining diffs against the expected-changes allowlist

Every hop crossed contributes expected diffs. From the ladder above, the ones
that appear in realm exports:

| Hop crosses | Expected diff in export                                                        |
|-------------|--------------------------------------------------------------------------------|
| →17         | client-policy `"scope"` → `"scopes"`                                           |
| →18         | new `acr` default client scope (realm level; NOT on pre-existing clients)      |
| →19.0.2     | inline-script SAML mappers replaced by deployed-script references              |
| →21.0.x     | user attribute `terms_and_conditions` casing flip-flop (21.0.0/21.0.1 exports) |
| →21.1       | service-account mapper claim `clientId` → `client_id`                          |
| →22         | `http challenge` flow gone (blocked if referenced)                             |
| →22.0.2     | legacy LinkedIn IdP present but dead without `--features linkedin-oauth`       |
| →23         | `RegistrationProfile` execution gone from registration flow; localization keys un-namespaced |
| →24         | user-profile config appears; `hmac-generated-hs512` component added, old `hmac-generated` retained; `verify-profile` required-action state differs fresh-vs-migrated |
| →25         | `basic` client scope on realm AND every existing OIDC client (with `Subject (sub)`/`auth_time` mappers) |
| →26.0       | IdP config attrs `kc.org`/`hideOnLoginPage` become first-class `organizationId`/`hideOnLogin` fields |
| →26.1       | `service_account` client scope appears; `client_id`/`clientHost`/`clientAddress` mappers move off per-client scopes |
| →26.2       | `admin-permissions` client appears if FGAP v2 gets enabled for the realm       |
| →26.3       | fresh-realm browser flow differs (Conditional 2FA, WebAuthn/Recovery executions) — migrated realms keep the old flow |
| →26.4       | SAML-encrypting clients gain explicit encryption-algorithm attributes          |
| →26.5       | new authz-enabled clients lack Default Resource/Policy/Permission; IdP boolean config values may be null/absent |
| →26.6.x     | `Organization` sub-flow in built-in browser flow (and wrongly in custom flows if upgraded through 26.6.0) |
| →26.7       | `is.dynamic.scope`→`is.parameterized.scope` (+`parameterized.scope.type`); realm `displayName` truncated at 255; *Configure OTP*/*Update password* priorities reordered; LDAP binary mappers pinned `base64`; WebAuthn `ResidentKey` attribute renames |

Anything NOT in the allowlist for the hops crossed = investigate: it is either
drift that predates the migration (also valuable to find) or a setting the
migration dropped.

### Practical notes
- Diff realm-by-realm; don't concatenate.
- A fresh realm created on the new version is NOT a valid comparison baseline
  for a migrated realm — new-realm defaults differ from migrated state by
  design (e.g. `verify-profile`, ECC keys on 26.5+ realms).
- For continuous enforcement after verification, hand the normalized export to
  `keycloak-config-cli` (adorsys) as the desired state — it applies
  export-format files idempotently; it is an importer, not a differ.

---

## <a id="automation"></a>5. Automation against legacy versions

- `kcadm.sh` and the service-account + `client_credentials` pattern work
  unchanged back to 17 (and on the WildFly 18/19 `-legacy` builds) — only the
  path and the `/auth` base URL differ (§2).
- Match kcadm version to server version by running it from the server's own
  pod/image; there is no published compatibility matrix and the Admin REST API
  is unversioned.
- kcadm option parsing changed over the years (exit code 2 for usage errors,
  no shell-eval since 23) — don't assume a script tested on 19 parses
  identically on 26.
- Watch the permission escalations when reusing scoped service accounts across
  versions (e.g. `partial-export` view→manage in 23, §4).
