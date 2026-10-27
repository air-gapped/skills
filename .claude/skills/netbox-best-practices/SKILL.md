---
name: netbox-best-practices
description: >-
  NetBox 4.2-4.7 deployment and upgrade knowledge the official netboxlabs/skills marketplace does not cover — deploying or upgrading NetBox on Kubernetes with the netbox-community helm chart (netbox-chart), external PostgreSQL/valkey wiring, API token bootstrap on 4.5+ (nbt_ v2 tokens), plugin installation in the official image, version-migration planning across 4.2-4.7, module type profiles, front/rear port (patch panel) API changes, and OIDC/SSO group-to-role mapping. Gap-filler only: for general NetBox data modeling, IPAM design, Diode, validation, or turning an auth backend on in the first place, prefer the official netbox-administration skill.
when_to_use: >-
  Trigger on "netbox helm", "netbox chart", "netbox kubernetes", "netbox upgrade", "netbox plugin install", "netbox api token bootstrap", "netbox 4.x breaking changes", "netbox oidc/sso group mapping", "netbox sso hardening", "netbox keycloak", OIDC via the helm chart (extraConfig wiring), or seeding/automation that must survive a NetBox version bump.
---

# NetBox Best Practices (helm + version deltas)

This skill COMPLEMENTS the official `netboxlabs/skills` marketplace
(`/plugin marketplace add netboxlabs/skills`). For data modeling, IPAM design,
API patterns, Diode ingestion, or validation, consult those skills first —
they are maintained upstream and authoritative. This skill covers four areas
they do not (as of 2026-06):

1. **netbox-chart (helm) deployment gotchas** → `references/helm-chart-gotchas.md`
2. **NetBox 4.2→4.7 version-delta cheat sheet** → `references/version-deltas.md`
3. **Modeling gaps**: module type profiles (4.3+), port-mapping rework (4.5) → `references/modeling-gaps.md`
4. **SSO/OIDC group→role mapping + hardening** → `references/sso-hardening.md`

Evidence labels used throughout: `[source]` = verified against chart/NetBox
source code (file:line cited); `[docs]` =
official docs/release notes (4.2–4.6: adversarially verified, 3-vote panel).

## Upgrading to 4.7 — gates [docs + live 2026-10-27]

From the 4.7.0–4.7.3 release notes, plus one live 4.6.10 → 4.7.3 hop.

| Gate | What it means for a Kubernetes install |
|---|---|
| **Target 4.7.2 or later** | 4.7.0 breaks the SSO button under a restrictive `form-action` CSP ([#23112](https://github.com/netbox-community/netbox/issues/23112)) and its `pg_dump` restores without the hierarchy cascade triggers ([#23130](https://github.com/netbox-community/netbox/issues/23130)). 4.7.0–4.7.1 write the plaintext of tokens created by background bulk API requests into job results, readable by anyone who can view jobs ([#23196](https://github.com/netbox-community/netbox/issues/23196)) — replace any token created that way. Chart pins: **8.3.66 = 4.6.10** (last 4.6), 8.3.67–8.3.77 = 4.7.0, 8.3.78–8.3.90 = 4.7.1, 8.3.91 = 4.7.2, **8.3.92+ = 4.7.3** (latest 8.3.97, 2026-10-27). 8.3.66 → 8.3.96 in one hop works. |
| **PostgreSQL 15+ required; 14 dropped** | The upgrade script **aborts** on 14 — 4.6 only warned, so a cluster that upgraded cleanly to 4.6 can hard-fail here. Check the external DB's major version before bumping the image tag. |
| **The `ltree` extension must be available** | Trusted: the migration creates it as the NetBox DB user, which needs `CREATE` on the database (owning it is enough) — no superuser. A managed DB that restricts extension creation blocks it. |
| **Redis 6.0+ required; 5.x dropped** | Applies to the external valkey/Redis wiring. Valkey is 7.x-derived and unaffected; a pinned legacy Redis 5 sidecar is not. |
| **Selection custom fields change shape on read** | REST *and* GraphQL now return `{"value": "...", "label": "..."}` instead of the bare value. Writes still accept the raw value. Any seeding or reconciliation script that reads a selection custom field back breaks silently — it gets a dict where it expected a string. |
| **The mptt → ltree migration locks hierarchical tables** | `ACCESS EXCLUSIVE` on each hierarchical table (reads block too) while it backfills; minutes on a large install. Plan a window. |

**After the 4.7 roll**, run the steps in `references/version-deltas.md` §4.7
"After the roll": config-context cache rebuild (the image entrypoint skips it),
`housekeeping` CronJob off, POST-based SSO check, hierarchy-path check. Before
moving or restoring a 4.7 database, read §4.7 "Moving or restoring".

## The five rules that prevent the worst failures

1. **Never commit rendered helm templates.** With `superuser.password`,
   `secretKey`, and `apiTokenPeppers` left empty, every OFFLINE render
   regenerates them (`lookup` returns nothing without a live cluster), so
   `helm template` output contains fresh random secret material every time.
   Gitignore `template-*.yaml`. During a real `helm upgrade` the chart
   preserves existing values via `lookup`. [source: templates/_helpers.tpl]

2. **Name external Postgres clusters differently from the helm release.**
   Zalando names a Service after the cluster CR, so a CR named like the
   release fullname makes `helm install` fail with "invalid ownership
   metadata". CloudNativePG suffixes its Services (`-rw`/`-ro`/`-r`)
   but names its ServiceAccount, Role and RoleBinding after the cluster, and
   the chart creates all three under the release name. Use `<release>-postgres-cluster` or `<release>-pg`.

3. **Don't trust the chart's superuser `api_token`.** The chart generates one
   and mounts it, but NetBox 4.6's entrypoint never seeds it (v2 peppered
   tokens can't be pre-seeded). Bootstrap real tokens via
   `POST /api/users/tokens/provision/`. Details + wire format in
   `references/helm-chart-gotchas.md#api-token-bootstrap`. [source+live]

4. **Plugins need a custom image.** `plugins:`/`pluginsConfig:` values are
   config-only (rendered into PLUGINS json); the official image ships zero
   plugin code. Build `FROM ghcr.io/netbox-community/netbox:<tag>` +
   `RUN /opt/netbox/venv/bin/pip install <plugin>`. [source: configmap.yaml]

5. **Check the version-delta sheet before writing API automation.** The REST
   API broke meaningfully at 4.3 (services), 4.5 (tokens, port mappings) —
   code that worked on 4.2 fails on 4.6 in non-obvious ways. See
   `references/version-deltas.md`.

## When deploying fresh

Read `references/helm-chart-gotchas.md` end-to-end first — it is ordered as a
pre-flight checklist (external DB, valkey sentinel wiring, secrets layout,
first-boot expectations, metrics). First boot runs all Django migrations and
takes several minutes before the pod goes Ready; that is normal.

## When upgrading NetBox or writing automation against it

Read `references/version-deltas.md` — it lists what changed in each minor
release 4.2→4.7 with dates and PR numbers, plus two "anti-facts" (plausible
claims that are FALSE) to avoid repeating common misinformation.

## When wiring SSO/OIDC (after the official skill gets it turned on)

Read `references/sso-hardening.md`. The official `netbox-administration` skill
covers enabling each backend; this file covers the gap it leaves: that the
`REMOTE_AUTH_SUPERUSER_GROUPS`/group-sync settings work ONLY with the
header/proxy backend — native OIDC/SAML ignores them and needs a custom
`SOCIAL_AUTH_PIPELINE` function to map IdP groups to NetBox roles — plus OIDC
backend gotchas (redirect URI shape, RS256-only default, PKCE off by default) and the
break-glass / header-spoofing / SSO≠API-token / associate_by_email hardening
rules. [source-verified against netbox 4.6 and 4.7.3 authentication code]

**Deploying SSO on the helm chart** (Keycloak etc.): start from the **worked
example at the end of `references/sso-hardening.md`** — the complete Keycloak
wiring that ran live on 2026-09-15 (client, mapper, values, pipeline module,
self-check, verification) — and read `references/helm-chart-gotchas.md` §9 — there are no dedicated OIDC chart
values (maintainers declined, netbox-community/netbox-chart#987); everything rides in `extraConfig`, custom
pipeline code must be volume-mounted as a `netbox.*` module, and the chart's
own `docs/auth.md` examples carry a dated KeycloakOAuth2 config (legacy /auth
URLs, pasted realm key) and a risky `associate_by_email` pipeline step.
