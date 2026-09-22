# Sources — traefik-hardening

Freshened: 2026-09-22 — every row probed. The patch floor, the advisory count, the critical GHSAs and the RateLimit/InFlightReq field behaviour all reproduce. A new high-severity advisory (GHSA-v67p-phpq-fc8x, 2026-09-07) falls inside the already-counted range.

Dated index of the primary sources behind this skill's claims. `freshen` mode reads and re-stamps the `Last verified` column. Traefik version claims track the release line current at the last verified date; re-probe on `freshen`.

Traefik ships security advisories faster than its docs change — **48** in 2026 (re-counted 2026-09-15 over the full advisory list), 16 of them in the seven weeks after the doc rows below were last checked. The earlier figure of 30 was right when written — the point it supports has only got stronger. **Re-probe the advisory row on every pass even when nothing else looks stale**; several of those advisories are auth bypasses in the middlewares this skill configures, so a row-date that only tracks documentation will not move when the thing that matters does.

**Freshened: 2026-09-15 — every row probed, and every row holds.** Patch floor re-confirmed at v3.7.13 / v2.11.57 (both 2026-09-04) and the advisory counts re-derived from the full list. Three absence claims re-tested and still true: InFlightReq still has no Redis backend, there is still no OSS-native Coraza (it is Hub-only), and none of the four tracked plugins is archived. **#8627's `stateReason` reads `COMPLETED` but the maintainer's closing comment declines the request** — the row's own caveat about not trusting that field is correct and stays.

| Claim / area | Source | Last verified |
|---|---|---|
| Security advisories + patch floor — latest stable v3.7.13, legacy v2.11.57; the two 2026 criticals are the `digestAuth` complete authentication bypass (no CVE assigned) and CVE-2026-88007 HTTP/3 backend NTLM reuse | https://github.com/traefik/traefik/security/advisories | 2026-09-15 |
| RateLimit fields (`average`/`period` default 1s/`burst`/`sourceCriterion`) + `redis` backend (v3.4+) | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/ratelimit/ | 2026-09-15 |
| InFlightReq fields (`amount`/`sourceCriterion`, no Redis backend) | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/inflightreq/ | 2026-09-15 |
| IPAllowList (v3) fields (`sourceRange`/`ipStrategy`/`rejectStatusCode`); `IPWhiteList`→`IPAllowList` rename at v3.0 | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/ipallowlist/ + migrate/v3 | 2026-09-15 |
| Buffering (`maxRequestBodyBytes`→413; do not cap response on SSE) | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/buffering/ | 2026-09-15 |
| ForwardAuth (per-request, no caching; v3 `maxBodySize` default -1 unbounded) | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/forwardauth/ | 2026-09-15 |
| Retry v2→v3 delta (network-only → HTTP `status`, non-idempotent opt-in) | https://github.com/traefik/traefik/releases (3.7 line) | 2026-09-15 |
| JA3/JA4 not exposed to plugin API (declined/open) | https://github.com/traefik/traefik/issues/8627 · https://github.com/traefik/traefik/issues/12421 | 2026-09-15 |
| Catalog-mode plugin startup network call regression (localPlugins immune) | https://github.com/traefik/traefik/issues/13005 | 2026-09-15 |
| `localPlugins` layout + `.traefik.yml` required; zero network calls (source-verified) | https://doc.traefik.io/traefik/reference/install-configuration/experimental/plugins/ + traefik/traefik `pkg/plugins/` | 2026-09-15 |
| Plugin maturity: crowdsec-bouncer, geoblock, jwt-plugin, coraza-http-wasm | github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin · PascalMinder/geoblock · traefik-plugins/traefik-jwt-plugin · jcchavezs/coraza-http-wasm-traefik | 2026-09-15 |
| `allowCrossNamespace` default false (CRD path); annotation path bypasses it | https://github.com/traefik/traefik-helm-chart `values.yaml` + doc.traefik.io kubernetes/crd | 2026-09-15 |
| Native Coraza WAF is Traefik Hub (commercial), not OSS | https://doc.traefik.io/traefik/ (Hub WAF pages) | 2026-09-15 |
| known-products: Open WebUI JWT-replay mechanism, forwarded-identity headers, audit schema | open-webui/open-webui source: `routers/openai.py`, `env.py`, `utils/logger.py`; OWUI issues #21152, #20842 | 2026-09-15 |
| known-products: LiteLLM `user_header_name`→`end_user` works on v1.92.1 (corrects prior #12893/#14667 report) | live verify on LiteLLM v1.92.1 + BerriAI/litellm `litellm/proxy/` source | 2026-09-15 |
| known-products: `user_header_name` deprecated; `user_header_mappings` (role `customer`) feeds same `end_user_id` path, checked before the deprecated fallback | BerriAI/litellm main source: `proxy/_types.py`, `proxy/auth/auth_utils.py:get_end_user_id_from_request_body`, `proxy/litellm_pre_call_utils.py` | 2026-09-15 |
