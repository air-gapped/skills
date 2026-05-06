---
name: keycloak-iam
description: Operate, configure, deploy, secure, and integrate with Keycloak (open-source IAM) — the modern Quarkus distribution (24.x–26.6.x), the Keycloak Operator with `Keycloak` and `KeycloakRealmImport` CRDs, and realm/client/identity-provider configuration.
when_to_use: Use whenever the user mentions Keycloak, Red Hat build of Keycloak (RHBK), `kc.sh`, `kcadm.sh`, `keycloak.conf`, `KC_*` / `KCRAW_*` env vars, the Keycloak Operator, a `Keycloak` or `KeycloakRealmImport` custom resource, or asks about server tuning (hostname / proxy / db / cache flags, `--optimized` builds), Kubernetes deployment (HA topology, probes, zero-downtime upgrades), security hardening (FGAP v2, client policies, FAPI, DPoP, JWT-Authz-Grant, federated client auth, redirect URI safety, CVEs), OIDC/SAML/IdP brokering with Keycloak as the IdP, LDAP/AD federation, themes / custom SPIs, or operations (Prometheus metrics, OTLP tracing, realm export/import, backup, upgrade matrix). Triggers on IAM/SSO/realm questions in a Keycloak context even when "Keycloak" isn't repeated in every message of a long thread.
---

# Keycloak IAM — operator's reference skill

This skill covers running, configuring, deploying, and integrating with **Keycloak**, the open-source identity & access management server. It targets the modern **Quarkus-based** distribution (24.x → 26.6.x as of May 2026; the legacy WildFly distribution was removed years ago). Information is current as of **Keycloak 26.6.1** (released April 2026).

The Red Hat build of Keycloak (RHBK) is downstream of upstream Keycloak with longer support windows and the same surface area; advice here applies to both unless explicitly noted.

## How to use this skill

Keycloak is a large product. Don't try to load everything — route to one or two reference files based on what the user is asking, then go deep.

```
references/
├── server-config.md         → CLI/env vars, kc.sh, kcadm.sh, hostname, db, cache,
│                              TLS/proxy, logging, features, bootstrap-admin, KCRAW_
├── k8s-deployment.md        → Operator install, Keycloak CR, KeycloakRealmImport,
│                              raw manifests, HA topology, probes, autoscaling
├── security-hardening.md    → Realm policies, brute force, FGAP v2, client policies
│                              (FAPI/OAuth 2.1), DPoP, redirect URI safety, recent CVEs
├── integration.md           → OIDC/SAML flows, IdP brokering, LDAP/AD federation,
│                              themes, SPIs, admin clients (Java/JS/kcadm/Terraform)
├── observability.md         → Metrics, OTLP tracing, structured logging, health
│                              probes, troubleshooting recipes
└── upgrade-and-backup.md    → Upgrade matrix, zero-downtime patches, realm
                               export/import, DB backup, disaster recovery
```

**Routing cheatsheet:**

| User question                                                              | Read first                            |
|----------------------------------------------------------------------------|---------------------------------------|
| "How do I set the hostname / proxy / DB?"                                  | `server-config.md`                    |
| "Why is my login redirecting in a loop?"                                   | `server-config.md` (hostname/proxy)   |
| "How do I deploy Keycloak on Kubernetes?" / "Operator vs raw manifests"    | `k8s-deployment.md`                   |
| "Show me a Keycloak CR" / "What goes in `spec.*`?"                         | `k8s-deployment.md` + `assets/examples/` |
| "How do I do zero-downtime upgrades?"                                      | `k8s-deployment.md` + `upgrade-and-backup.md` |
| "Harden my realm" / "FAPI / OAuth 2.1 / DPoP / FGAP"                       | `security-hardening.md`               |
| "Recent CVEs?" / "Is 26.x.y vulnerable?"                                   | `security-hardening.md` §CVE table    |
| "Wire my SPA / mobile app / service to Keycloak"                           | `integration.md`                      |
| "Configure SAML / OIDC IdP / LDAP / social login"                          | `integration.md`                      |
| "Custom theme / authenticator / event listener / mapper"                   | `integration.md` §SPIs / §Themes      |
| "What metrics / Grafana dashboard / Prometheus / OTLP"                     | `observability.md`                    |
| "Realm export gotchas" / "How do I back up?" / "Liquibase migration stuck" | `upgrade-and-backup.md`               |

**When in doubt about a CLI flag**, the source of truth is `https://www.keycloak.org/server/all-config` (full option index). When in doubt about a CR field, the source of truth is the CRD YAML in `keycloak-k8s-resources` at the version tag (see §"Authoritative sources" below).

## Version map (May 2026)

Latest stable: **Keycloak 26.6.1** (released 2026-04-15). Two CVEs were fixed in 26.6.1 — `CVE-2026-4366` (SSRF via HTTP redirect) and `CVE-2026-4633` (user enumeration via identity-first login) — operators on 26.6.0 should upgrade. See `security-hardening.md` for the full CVE table.

Notable changes through the 26.x line:

| Version  | Key changes (operator-relevant)                                                                |
|----------|------------------------------------------------------------------------------------------------|
| 26.6.x   | Workflows, JWT Authorization Grant, Federated client auth, **Zero-downtime patch updates**, KCRAW_ env prefix, automatic K8s truststore, graceful HTTP shutdown, configurable Service name/port in Operator, organization groups, sensitive-info redaction in HTTP access logs |
| 26.5.x   | Token Exchange Standard (RFC 8693) GA, declarative-user-profile GA, FIPS via Bouncy Castle, ECC keys default for new realms, Java 25 added (server image still on JDK 21 for FIPS) |
| 26.4.x   | hostname-v2 GA + `hostname-v1` removed, Quarkus 3.20 LTS, `--proxy-headers` (replaces `--proxy edge|reencrypt`) |
| 26.3.x   | Organizations GA, Account Console v3 GA, Admin UI on PatternFly React, FGAP v2 preview |
| 26.2.x   | OIDC client policies v2, persistent user sessions GA |
| 26.0.0   | `KEYCLOAK_ADMIN` removed → `KC_BOOTSTRAP_ADMIN_*`, persistent user sessions on by default, hostname-v2 by default |

Always cross-check with the release-notes body via `gh release view <tag> --repo keycloak/keycloak --json body --jq '.body'`. Do not rely solely on this table — bump the date and verify.

## Authoritative sources

When the user asks about something specific, prefer these sources over generic recall. Cited paths are relative to repo root — access via a local clone, or fetch via `gh api repos/<owner>/<repo>/contents/<path>`.

- **Upstream source** (`keycloak/keycloak`)
  - CLI option mappers: `quarkus/runtime/src/main/java/org/keycloak/quarkus/runtime/configuration/mappers/*PropertyMappers.java`
  - Option definitions (descriptions, defaults): `quarkus/config-api/src/main/java/org/keycloak/config/*Options.java`
  - Operator Java code + CRD generators: `operator/src/main/java/org/keycloak/operator/`
  - Themes (login/email/account/admin): `themes/src/main/resources/theme/` + `js/apps/{account-ui,admin-ui}/`
  - asciidoc guides operators rarely think to read: `docs/guides/server/*.adoc`, `docs/guides/operator/*.adoc`, `docs/guides/high-availability/*.adoc`

- **Operator install manifests** (`keycloak/keycloak-k8s-resources`)
  - Each Keycloak version has a git tag (e.g. `26.6.1`) with three files under `kubernetes/`:
    - `keycloaks.k8s.keycloak.org-v1.yml` — the `Keycloak` CRD
    - `keycloakrealmimports.k8s.keycloak.org-v1.yml` — the `KeycloakRealmImport` CRD
    - `kubernetes.yml` — Operator Deployment + RBAC + ServiceAccount
  - The repo's `main` branch has only the README + LICENSE; the actual manifests live in tags. Use `git checkout <tag>` against a clone, or `gh api repos/keycloak/keycloak-k8s-resources/contents/kubernetes?ref=<tag>` to fetch raw. (Do NOT assume the repo is stale just because `main` looks empty.)

- **Online docs**: `https://www.keycloak.org/`
  - `/server/all-config` — every CLI option, every default
  - `/server/configuration` — concept overview, build-time vs runtime
  - `/operator/installation`, `/operator/basic-deployment`, `/operator/advanced-configuration`, `/operator/realm`, `/operator/keycloak-cr`, `/operator/rolling-updates`
  - `/high-availability/` — multi-cluster, external Infinispan, CloudNativePG recipe
  - `/securing-apps/` — OIDC layers, SAML, DPoP, JWT-Authz-Grant, MCP authorization server (CIMD)
  - `/docs/<version>/server_admin/` and `/docs/<version>/server_development/` — admin and SPI guides

- **gh CLI** (per the user's `gh-cli-preferred` rule):
  - Release notes: `gh release view <tag> --repo keycloak/keycloak --json body --jq '.body'`
  - Issues: `gh issue view <N> --repo keycloak/keycloak`
  - Search: `gh search issues --repo keycloak/keycloak "<query>"`
  - Security advisories: `gh api repos/keycloak/keycloak/security-advisories`

When the user references a specific behavior, *check the source clone or CRD YAML before answering* — option names, defaults, and JSON field names get renamed across releases (e.g. `--proxy edge|reencrypt|passthrough` → `--proxy-headers xforwarded|forwarded` in 26.4; `KEYCLOAK_ADMIN` → `KC_BOOTSTRAP_ADMIN_*` in 26.0; the `hostname-v2` rewrite). Stale answers are worse than "let me check."

## Production guardrails (the checklist that matters)

These are the things that bite operators most. Don't suggest a Keycloak deployment that violates them without a stated reason.

1. **Run `kc.sh build` before `start --optimized`** in a custom image, or set `spec.startOptimized: true` only after baking the build. Otherwise startup pays the auto-build cost on every pod start.
2. **`--hostname` must be a real, externally-resolvable URL** in production, with `--hostname-strict=true` (default). Do not run with `hostname-strict=false` outside of dev — it lets clients dictate the issuer.
3. **`--proxy-headers=xforwarded|forwarded` is required** when behind any reverse proxy that does TLS termination or rewrites the Host header. Pair with `--proxy-trusted-addresses` to a CIDR that covers the proxy. Without this, login redirects loop.
4. **Use `--db postgres` (or another supported vendor)**. The default `dev-file` H2 is **not** for production and silently disables clustering. Postgres is the only DB that gets tested under load by upstream.
5. **Use a real container image registry / pin a tag** (`quay.io/keycloak/keycloak:26.6.1`), never `latest`. The `nightly` tag is for CI only.
6. **Probes go to the management port (default 9000)**: `/health/started`, `/health/live`, `/health/ready` — not the main HTTP port. As of 26.6, probes return UP during DB migrations so Liquibase can finish without K8s killing the pod.
7. **HPA on Keycloak is a trap.** Sessions live in clustered Infinispan caches; scaling out and back in churns the cache. Run a fixed number of replicas (≥3 for HA) with a `PodDisruptionBudget`, not an HPA.
8. **Realm exports are NOT backups.** They omit secrets, federated users, and event history. The Postgres database is the source of truth — back that up with WAL archiving (CloudNativePG, Crunchy, RDS automated backups).
9. **Bootstrap admin is temporary.** `KC_BOOTSTRAP_ADMIN_USERNAME`/`PASSWORD` exists only to create the first real admin via `kcadm.sh`, then should be removed. The bootstrap admin auto-expires after 120 minutes.
10. **Pin Keycloak ↔ Operator versions together.** The operator at tag `26.6.1` is meant to manage Keycloak `26.6.1`. Mixing major.minor versions across the operator/server boundary is unsupported and often breaks the CRD schema.

## Quickstart: the smallest production-shaped Keycloak

When the user says "just stand one up so I can play," **don't** point them at `kc.sh start-dev` if they care about production fidelity — show them this instead. It's a Keycloak CR + Postgres + Ingress, no extra moving parts:

```yaml
# 1. Install the operator (do this once per cluster)
# kubectl apply -f https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/26.6.1/kubernetes/keycloaks.k8s.keycloak.org-v1.yml
# kubectl apply -f https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/26.6.1/kubernetes/keycloakrealmimports.k8s.keycloak.org-v1.yml
# kubectl apply -f https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/26.6.1/kubernetes/kubernetes.yml

# 2. Create a TLS secret (cert-manager / hand-roll / etc.)
# 3. Create DB credentials secret (keys: username, password)
# 4. Deploy Keycloak
apiVersion: k8s.keycloak.org/v2alpha1
kind: Keycloak
metadata:
  name: keycloak
  namespace: iam
spec:
  instances: 2
  image: quay.io/keycloak/keycloak:26.6.1
  startOptimized: false           # set true when the image is pre-baked with `kc.sh build`
  hostname:
    hostname: https://auth.example.com
    strict: true
  proxy:
    headers: xforwarded
  http:
    tlsSecret: keycloak-tls       # remove and use ingress for edge termination
  db:
    vendor: postgres
    host: postgres-rw.iam.svc
    database: keycloak
    usernameSecret: { name: keycloak-db, key: username }
    passwordSecret: { name: keycloak-db, key: password }
  bootstrapAdmin:
    user:
      secret: keycloak-bootstrap-admin   # keys: username, password
  update:
    strategy: Auto                # zero-downtime patch updates (26.6+)
  features:
    enabled: ["organizations", "admin-fine-grained-authz:v2"]
```

See `assets/examples/` for fuller examples (with HA tuning, `KeycloakRealmImport`, raw-manifest deployment without the operator, network policies).

## Common operator pitfalls

- **`hostname-strict=false` "fixes" my login** → No, it papers over a proxy/headers misconfig. Set `--proxy-headers` correctly instead.
- **"Why is my custom theme not appearing?"** → The theme must be baked into a custom image and `kc.sh build` re-run; dropping a theme jar into a stock image at runtime no longer works. Themes are packaged into the optimized server jar.
- **"Operator pod logs are flooded with warnings"** → On 26.6.0 exactly, that's `#47872`. Upgrade to 26.6.1.
- **"Realm import keeps failing on existing realm"** → `KeycloakRealmImport` is *create-or-replace*; it won't merge. Use `kcadm.sh` for incremental edits, or accept the realm-as-config GitOps trade-off.
- **"My JS admin client is broken on 26.6.0"** → 26.6.0 shipped a broken `@keycloak/keycloak-admin-client` package. Use 26.6.1.
- **"Liquibase changelock stuck"** → A previous migration crashed mid-flight. `DELETE FROM DATABASECHANGELOGLOCK WHERE ID=1` (after confirming no other instance is migrating). See `observability.md` §troubleshooting for the safe procedure.
- **"I'm getting `KC_*` substitution surprises with `$` in passwords"** → Use the new `KCRAW_*` prefix (26.6+) instead of `KC_*` for any value that contains `$`.

## Style

- When citing options, give the **exact** flag *and* the env var: ``--proxy-headers / `KC_PROXY_HEADERS` ``. Operators copy-paste; getting it half right costs them an hour.
- Prefer linking to the source file or release-notes URL the user can verify, over restating from memory. Releases between 26.0 and 26.6 renamed flags and removed others; "I'm pretty sure" is wrong about half the time.
- When the user is on a pre-26 version, surface the upgrade urgency *briefly* (a one-liner pointing at the upgrade guide). Don't lecture.
- The user is sophisticated — skip the "Keycloak is an open-source IAM solution from Red Hat" preamble. Get to the answer.
