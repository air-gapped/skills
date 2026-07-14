# Known-Products Log

Grades from prior vets and the research behind this skill. Check here
FIRST (Phase 0) — a row may answer the whole request. The ONLY home for
product-specific findings (pattern files stay product-agnostic); rows are
dated and **version-specific** — re-vet on major version changes. Basis:
`research` = sourced research report, not a full 8-question vet; `vetted`
= actual skill run. Append new rows at the bottom (same columns as
`./AIRGAP-KNOWN-PRODUCTS.md` in run working directories).

| Product | As of | Grade | Decisive evidence | Basis |
|---|---|---|---|---|
| Coder | 2026-07 | air-gap-native | local signed license, zero callbacks; air-gap doc publishes full hostname mirror/disable list; offline docs bundle | research |
| Ollama | 2026-07 | air-gap-native (provisional) | no usage telemetry; only explicit `ollama pull` + desktop update check | research |
| Meilisearch | 2026-07 | possible-with-mirror | transit-domain telemetry (`telemetry.meilisearch.com`→Segment→Amplitude); value-vs-presence opt-out bug #1983; "Launched" event before opt-out visible | research |
| Trivy | 2026-07 | possible-with-mirror | DB as OCI artifact + `--db-repository` (good); silent-stale with `--skip-db-update` (schema-only validation) — pair with external age check | research |
| Grype | 2026-07 | possible-with-mirror | `GRYPE_DB_UPDATE_URL` + `grype db import`; fail-closed at 5 days (`MaxAllowedBuiltAge`) — best-in-class staleness handling; v6 moved to `latest.json` (v5 `listing.json` mirrors insufficient) | research |
| ClamAV | 2026-07 | possible-with-mirror | official mirror tool `cvdupdate`; warns >7 days, fail-open | research |
| osv-scanner | 2026-07 | possible-with-mirror | public `all.zip` feeds + `--offline`; no documented staleness warning (silent-stale risk) | research |
| Elastic stack | 2026-07 | possible-with-mirror | exemplary air-gap docs w/ feature-degradation table; but lockstep-pinned EPR image, EMS/GeoIP default-on callbacks, kill switches with documented breakage (kibana#30202/#152389) | research |
| GitLab self-managed | 2026-07 | possible-with-mirror | Offline Cloud License (approval-gated, ~30-day grace); Duo default-on→`cloud.gitlab.com` when licensed but Duo Self-Hosted path exists; mandatory version stops multiply gap crossings; gravatar on by default (+#26008 setting-ignored reports) | research |
| Mattermost | 2026-07 | possible-with-mirror | dedicated air-gap doc (disable link previews); Agents plugin off-by-default w/ BYO-LLM | research |
| GitHub CLI (gh) | 2026-07 | possible-with-mirror | telemetry on by default since v2.91.0 (2026-04-22); honors DO_NOT_TRACK | research |
| Semgrep | 2026-07 | possible-with-mirror | local rules run offline; registry `p/...` rulesets never cached + send project URL (#3147) — sustainment = vendor a semgrep-rules clone | research |
| Renovate | 2026-07 | possible-with-mirror | no feed artifact; queries registries live — requires standing Artifactory/Nexus mirror via `hostRules` | research |
| Sourcegraph | 2026-07 | proxy-in-disguise | continuous license ping to sourcegraph.com; **shuts instance down** without "Allow air gapped" license tag; air-gap is a negotiated tier | research |
| LangSmith | 2026-07 | proxy-in-disguise | repo topology `*-sdk` only; platform closed; self-host is Enterprise-tier | research |
| Cursor | 2026-07 | proxy-in-disguise | own docs: BYOK requests "routed through our backend" | research |
| Warp | 2026-07 | proxy-in-disguise | login requirement lifted Dec 2024 but full offline still unsupported (#5640) — login-optional ≠ offline-capable | research |
| Postman | 2026-07 | proxy-in-disguise | offline Scratch Pad removed Sept 2023; cloud sign-in required for full app | research |
| Docker Desktop | 2026-07 | proxy-in-disguise | org-enforced cloud sign-in (vendor-documented) | research |
| Plex | 2026-07 | proxy-in-disguise | LAN access authenticates against plex.tv unless exemption pre-configured while online | research |
| Tailscale | 2026-07 | proxy-in-disguise | control plane (`login.tailscale.com`) closed; Headscale is the self-hosted escape hatch (separate product to vet) | research |
| Docker Content Trust | 2026-07 | no-go | retired; `notary.docker.io` shuts down 2026-12-08 — do not build air-gap verification on it | research |
| LangSmith self-hosted (chart 0.16.0-rc.12 / app 0.16.13rc1) | 2026-07-14 | proxy-in-disguise (provisional, static-only) | sharper than the research row: self-host is a REAL local platform (traces local, 10 mirrorable images, global registry override, custom CA) — but billing telemetry to `beacon.langchain.com` "cannot be disabled" and zero-egress is a negotiated offline Enterprise license (no offline flag in public chart); with that license, re-vet toward possible-with-mirror | vetted |
| Meilisearch v1.50.0 (fff2ef5a4) | 2026-07-14 | possible-with-mirror (provisional, static-only) | default-on telemetry to transit domain `telemetry.meilisearch.com` (Segment), first-run "Launched" before opt-out notice, `MEILI_NO_ANALYTICS=true` verified off-means-off (#1983 fixed); zero mandatory egress otherwise; ureq/webpki compiled-in roots block private-CA HTTPS on embedder/webhook/HF paths; personalization hardcodes `api.cohere.ai` (opt-in); EE=BUSL-1.1 legal-only, no enforcement | vetted |
