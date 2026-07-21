---
name: netbox-best-practices
description: NetBox 4.2-4.6 deployment and upgrade knowledge that the official netboxlabs/skills marketplace does NOT cover - use for deploying or upgrading NetBox on Kubernetes with the netbox-community helm chart (netbox-chart), external PostgreSQL/valkey wiring, API token bootstrap on 4.5+ (nbt_ v2 tokens), plugin installation in the official image, version-migration planning between NetBox 4.2 and 4.6, module type profiles, and front/rear port (patch panel) API changes. Trigger on "netbox helm", "netbox chart", "netbox kubernetes", "netbox upgrade", "netbox plugin install", "netbox api token bootstrap", "netbox 4.x breaking changes", "netbox oidc/sso group mapping" or "netbox sso hardening", or seeding/automation that must survive a NetBox version bump. For general NetBox data modeling, IPAM design, Diode, or validation questions - and for turning on an auth backend in the first place - prefer the official netboxlabs/skills marketplace skills (netbox-administration); this skill only covers the gaps.
---

# NetBox Best Practices (helm + version deltas)

This skill COMPLEMENTS the official `netboxlabs/skills` marketplace
(`/plugin marketplace add netboxlabs/skills`). For data modeling, IPAM design,
API patterns, Diode ingestion, or validation, consult those skills first —
they are maintained upstream and authoritative. This skill covers three areas
they do not (as of 2026-06):

1. **netbox-chart (helm) deployment gotchas** → `references/helm-chart-gotchas.md`
2. **NetBox 4.2→4.6 version-delta cheat sheet** → `references/version-deltas.md`
3. **Modeling gaps**: module type profiles (4.3+), port-mapping rework (4.5) → `references/modeling-gaps.md`
4. **SSO/OIDC group→role mapping + hardening** → `references/sso-hardening.md`

Evidence labels used throughout: `[source]` = verified against chart/NetBox
source code (file:line cited); `[live]` = verified on a production install of
chart 8.3.14 / NetBox v4.6.2 — upstream is now chart 8.3.37 / v4.6.5 (2026-07-21), still 4.6.x and still chart 8.x, so no delta invalidated; `[docs]` = official docs/release notes,
adversarially verified (3-vote panel).

## The five rules that prevent the worst failures

1. **Never commit rendered helm templates.** With `superuser.password`,
   `secretKey`, and `apiTokenPeppers` left empty, every OFFLINE render
   regenerates them (`lookup` returns nothing without a live cluster), so
   `helm template` output contains fresh random secret material every time.
   Gitignore `template-*.yaml`. During a real `helm upgrade` the chart
   preserves existing values via `lookup`. [source: templates/_helpers.tpl]

2. **Name external Postgres clusters differently from the helm release.**
   A Zalando/CNPG cluster named like the release fullname creates a Service
   with the same name the chart wants to own → `helm install` fails with
   "invalid ownership metadata". Convention: `<release>-postgres-cluster`. [live]

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
takes several minutes before the pod goes Ready; that is normal. [live]

## When upgrading NetBox or writing automation against it

Read `references/version-deltas.md` — it lists what changed in each minor
release 4.2→4.6 with dates and PR numbers, plus two "anti-facts" (plausible
claims that are FALSE) to avoid repeating common misinformation.

## When wiring SSO/OIDC (after the official skill gets it turned on)

Read `references/sso-hardening.md`. The official `netbox-administration` skill
covers enabling each backend; this file covers the gap it leaves: that the
`REMOTE_AUTH_SUPERUSER_GROUPS`/`_STAFF`/group-sync settings work ONLY with the
header/proxy backend — native OIDC/SAML ignores them and needs a custom
`SOCIAL_AUTH_PIPELINE` function to map IdP groups to NetBox roles — plus the
break-glass / header-spoofing / SSO≠API-token hardening rules. [source-verified
against netbox 4.6 authentication code]
