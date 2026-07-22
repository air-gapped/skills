# Known product: Open WebUI — chat-API abuse (worked example)

*Dated log, verified 2026-06-29 (base guide) + 2026-07-22 (LiteLLM re-verify). Product-specific; the generic Traefik mechanics live in the sibling reference files. Re-verify against the running Open WebUI / LiteLLM / Traefik versions before applying — env-var names and LiteLLM keys drift.*

A full-stack instance of the generic pattern: a scarce GPU-backed chat service, abused by authorized users driving it programmatically instead of via the browser, starving everyone else. It's the canonical case for why **classification fails and per-identity capping wins**.

## The abuse mechanism (why disabling the OpenAI API doesn't help)

Open WebUI's own browser frontend sends every chat to the **internal** endpoint `POST /api/chat/completions` using the **session JWT** stored in plaintext in `localStorage.token`. A user copies that token from DevTools and replays the exact same endpoint from a script/CLI/coding-agent. The server cannot tell script from browser: same endpoint, same `Authorization: Bearer`, no CSRF, no origin check, **no websocket required to send a chat**. Turning off the "OpenAI-compatible API" toggle does nothing — that's a *different* endpoint. Maintainers consider this by-design (OWUI issues #21152, #20842); there is **no built-in chat rate limit** (the only limiter guards the sign-in form: 15 req / 180 s).

Verified live (2026-07-22) against a real instance: a bare `curl` with the lifted JWT — no browser, no UI fields, `User-Agent: curl` — gets a full 200 completion, and the same JWT reaches admin endpoints (`/api/v1/users/`, `/configs/export`). So a lifted *admin* session is full API-level compromise, not just GPU abuse.

## Layer map (which generic control goes where)

| Layer | Control | Generic ref |
|---|---|---|
| Traefik ingress | `InFlightReq` (concurrency) + `RateLimit` (rate), keyed on `Authorization` or a decoded `X-User-Id`, **scoped to `/api/chat/completions`** via a separate Ingress; `Buffering` req-body cap; existing `IPAllowList` perimeter | `middleware-primitives.md`, `deployment.md`, `identity-keying.md` |
| Open WebUI app | shrink replay window (`JWT_EXPIRES_IN` 4w→8h–1d, `OAUTH_MAX_SESSIONS_PER_USER` 10→2-3); `ENABLE_OAUTH_BACKCHANNEL_LOGOUT`+Redis for real revocation; reduce per-turn fan-out; a native **inlet Filter** that caps per-user rate/concurrency seeing the real `__user__["id"]` (covers browser AND replay, since both traverse the pipeline) | app config (below) |
| LiteLLM backend | global/per-model `max_parallel_requests` + `rpm`/`tpm`; per-user attribution via forwarded headers | below |
| Keycloak (IdP) | short session lifespans; **suspend user** = the hard stop | — |
| Detection | OWUI `audit.log` (identity+UA+IP) ⋈ Traefik access log (429/413) ⋈ LiteLLM logs (tokens/cost) | `detection-and-response.md` |

## The fan-out multiplier (sizes every concurrency cap)

One chat turn fires **4-5 concurrent** `/api/chat/completions` calls: main stream + title + tags + follow-up + (optional) autocomplete generation. So `InFlightReq.amount` must budget for legitimate fan-out — start at 8+, watch for false 429s, then tighten. Cutting the fan-out itself is app config: `ENABLE_TITLE_GENERATION`, `ENABLE_TAGS_GENERATION`, `ENABLE_FOLLOW_UP_GENERATION`, `ENABLE_AUTOCOMPLETE_GENERATION` (default off — keep off), and route the rest to a cheap `TASK_MODEL`.

## The "humans burst" objection — resolved by path scoping

A human dragging the mouse across the chat list fires hundreds of GETs on `/api/v1/chats/*` in seconds — which is exactly why the limit is scoped to **`POST /api/chat/completions` only** (the scoped-Ingress pattern). The cheap list GETs stay unthrottled; only the expensive completion path is capped. The burst never touches the rate limit.

## LiteLLM per-user attribution (verified 2026-07-22, v1.92.1)

Two-sided, no per-user provisioning needed:

1. **Open WebUI side:** `ENABLE_FORWARD_USER_INFO_HEADERS=True` → OWUI attaches `X-OpenWebUI-User-{Id,Email,Name,Role}` to every upstream call on the chat path (`routers/openai.py:include_user_info_headers`; header names default in `env.py` `FORWARD_USER_INFO_HEADER_USER_*`). Identity goes as **HTTP headers**, not the body `user` field. `user.id` is an OWUI-internal **uuid4** (NOT the OIDC `sub`), so prefer `X-OpenWebUI-User-Email` for legible records.
2. **LiteLLM side (required, else nothing shows):** set `general_settings.user_header_name: "X-OpenWebUI-User-Email"`. The email then populates the **End User** column in Request Logs + `LiteLLM_SpendLogs.end_user`, aggregated into `LiteLLM_EndUserTable` (keyed by email). *This attributes; it does not enforce until a per-end-user budget is added.*

> **Ledger correction:** the base guide (2026-06-29) reported the `user_header_mappings → end_user` path as broken with OWUI (LiteLLM #12893, #14667) and recommended `extra_spend_tag_headers` (spend *tags*) instead. Re-verified 2026-07-22 on **LiteLLM v1.92.1**: `user_header_name: X-OpenWebUI-User-Email` DID populate the `end_user` column. Either fixed since, or `user_header_name` (deprecated) works where `user_header_mappings` (newer) didn't. Prefer `user_header_name` on v1.92.1+; keep spend-tag headers as the fallback if the column stays empty on the running version.
>
> **Update 2026-07-22 (source read of litellm main):** `user_header_name` is formally deprecated in `litellm/proxy/_types.py` and only accepts a single string (non-string raises `TypeError`). A `user_header_mappings` entry with `litellm_user_role: customer` converges on the SAME `end_user_id` code path (`auth_utils.py:get_end_user_id_from_request_body` — mappings checked first, `user_header_name` as fallback), so on current versions the mappings form is the forward-compatible spelling and supports multiple headers (first present wins). `litellm_user_role: internal_user` is a different field (`user_id`, the internal-user column) — do not use it for OWUI end-user attribution.

Note at the LiteLLM layer the `User-Agent` is always OWUI's own client (`python`), never the end-user's — so browser-vs-script detection **cannot** happen at LiteLLM; it must be at Traefik (in front of OWUI) or in the OWUI audit log.

## Audit log — the identity+client detection feed

`AUDIT_LOG_LEVEL=METADATA` logs one JSON object per request with `user{id,email,role,name}`, `verb`, `request_uri`, `source_ip`, and the **real client `user_agent`** — the one place browser-vs-script is visible per user. For a **stateless pod** (no PVC, chart with no sidecar), the default file sink (`/data/audit.log`) is lost on pod moves; set `ENABLE_AUDIT_STDOUT=True` + `LOG_FORMAT=json` (+ optional `ENABLE_AUDIT_LOGS_FILE=False`) to stream it to stdout for the cluster log pipeline. This OWUI env detail is documented in the `open-webui-api` skill (`references/events-scim.md`).

Analysis (run against the log store or a pulled file) — **use `jq` for path counts, never a log-folding tool** (it over-folds distinct endpoints):

```bash
A=audit.log   # or: kubectl -n <ns> exec <pod> -- cat /data/audit.log > audit.log
# top talkers on completions
jq -r 'select(.request_uri|endswith("/api/chat/completions")) | .user.email' $A | sort | uniq -c | sort -rn | head
# non-browser clients hitting chat = JWT replayed from a script
jq -r 'select(.request_uri|endswith("/api/chat/completions")) | "\(.user.email)\t\(.user_agent)"' $A \
  | grep -ivE 'Mozilla|Chrome|Safari|Firefox|Edg' | sort | uniq -c | sort -rn
# peak per-user-per-minute (concurrency/hammering proxy)
jq -r 'select(.request_uri|endswith("/api/chat/completions")) | "\(.user.email) \((.timestamp/60|floor))"' $A | sort | uniq -c | sort -rn | head
```
Abuser fingerprint: high count + double-digit per-minute buckets + non-browser UA + flat 24h activity. A real user trips none.

## Fork-level (only if in-app blocking of the replay is mandatory)

The only thing that makes the replayed JWT *useless* outside the browser: **reject JWT bearer on external API paths**, accept the session JWT only via an `httponly` cookie (browser), forcing programmatic clients onto governable API keys (community patch, OWUI #21152). Optionally **require an active socket.io session** to send a chat (browser always holds one; most scripts don't). Both are OWUI fork patches to maintain across upgrades — last resort.

## Instance facts that shaped the above (example cluster, 2026)

Traefik **v3.7.1** DaemonSet; Cilium L2 + `externalTrafficPolicy: Local` → **single Traefik counting pod** (in-memory `InFlightReq`/`RateLimit` effectively global — see `deployment.md`). Existing `ipwhitelist-limited` middleware already restricts source ranges (abusers are *inside* the trusted CIDRs — the whole reason IP limiting can't solve it). OWUI → LiteLLM (Enterprise, v1.92.1) → vLLM. Traefik Hub CRDs present but **unlicensed** → no native Coraza WAF available.
