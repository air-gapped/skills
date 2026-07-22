# Sources — traefik-hardening

Dated index of the primary sources behind this skill's claims. `freshen` mode reads and re-stamps the `Last verified` column. Traefik version claims track the release line current at the last verified date; re-probe on `freshen`.

| Claim / area | Source | Last verified |
|---|---|---|
| RateLimit fields (`average`/`period` default 1s/`burst`/`sourceCriterion`) + `redis` backend (v3.4+) | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/ratelimit/ | 2026-07-22 |
| InFlightReq fields (`amount`/`sourceCriterion`, no Redis backend) | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/inflightreq/ | 2026-07-22 |
| IPAllowList (v3) fields (`sourceRange`/`ipStrategy`/`rejectStatusCode`); `IPWhiteList`→`IPAllowList` rename at v3.0 | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/ipallowlist/ + migrate/v3 | 2026-07-22 |
| Buffering (`maxRequestBodyBytes`→413; do not cap response on SSE) | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/buffering/ | 2026-07-22 |
| ForwardAuth (per-request, no caching; v3 `maxBodySize` default -1 unbounded) | https://doc.traefik.io/traefik/reference/routing-configuration/http/middlewares/forwardauth/ | 2026-07-22 |
| Retry v2→v3 delta (network-only → HTTP `status`, non-idempotent opt-in) | https://github.com/traefik/traefik/releases (3.7 line) | 2026-07-22 |
| JA3/JA4 not exposed to plugin API (declined/open) | https://github.com/traefik/traefik/issues/8627 · https://github.com/traefik/traefik/issues/12421 | 2026-07-22 |
| Catalog-mode plugin startup network call regression (localPlugins immune) | https://github.com/traefik/traefik/issues/13005 | 2026-07-22 |
| `localPlugins` layout + `.traefik.yml` required; zero network calls (source-verified) | https://doc.traefik.io/traefik/reference/install-configuration/experimental/plugins/ + traefik/traefik `pkg/plugins/` | 2026-07-22 |
| Plugin maturity: crowdsec-bouncer, geoblock, jwt-plugin, coraza-http-wasm | github.com/maxlerebourg/crowdsec-bouncer-traefik-plugin · PascalMinder/geoblock · traefik-plugins/traefik-jwt-plugin · jcchavezs/coraza-http-wasm-traefik | 2026-07-22 |
| `allowCrossNamespace` default false (CRD path); annotation path bypasses it | https://github.com/traefik/traefik-helm-chart `values.yaml` + doc.traefik.io kubernetes/crd | 2026-07-22 |
| Native Coraza WAF is Traefik Hub (commercial), not OSS | https://doc.traefik.io/traefik/ (Hub WAF pages) | 2026-07-22 |
| known-products: Open WebUI JWT-replay mechanism, forwarded-identity headers, audit schema | open-webui/open-webui source: `routers/openai.py`, `env.py`, `utils/logger.py`; OWUI issues #21152, #20842 | 2026-07-22 |
| known-products: LiteLLM `user_header_name`→`end_user` works on v1.92.1 (corrects prior #12893/#14667 report) | live verify on LiteLLM v1.92.1 + BerriAI/litellm `litellm/proxy/` source | 2026-07-22 |
| known-products: `user_header_name` deprecated; `user_header_mappings` (role `customer`) feeds same `end_user_id` path, checked before the deprecated fallback | BerriAI/litellm main source: `proxy/_types.py`, `proxy/auth/auth_utils.py:get_end_user_id_from_request_body`, `proxy/litellm_pre_call_utils.py` | 2026-07-22 |
