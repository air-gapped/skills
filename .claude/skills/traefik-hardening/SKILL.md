---
name: traefik-hardening
description: |-
  Harden a Traefik 2.x/3.x reverse proxy against abusive or unwanted traffic — per-identity rate + concurrency limiting, IP allowlisting, request-body buffering, middleware chaining, keying limits on a JWT claim/header instead of raw source IP, air-gapped plugin loading (localPlugins/WASM), and detection/response via access logs. Built on the principle that a proxy usually CANNOT reliably tell a "bad" client from a "good" one (User-Agent and even TLS/JA3 fingerprints are spoofable; real humans burst while abusive scripts crawl) — so cap per-identity resource use regardless of client type rather than trying to classify. Covers the 2.x→3.x middleware deltas (IPWhiteList→IPAllowList, Redis-backed distributed RateLimit, status-based Retry), the single-leader-counting trap, and where Traefik's job ends and the app/backend must take over.
when_to_use: |-
  Use whenever someone is fending off API abuse, request floods, scraping/bot traffic, one user starving shared capacity (GPU/DB/API), or session-cookie/token replay behind Traefik — even when they don't say "Traefik". Trigger phrases: "rate limit at the ingress", "limit requests per user", "block bots at the proxy", "stop one user hogging the API", "cap concurrent streams", "IngressRoute rate limiting", "traefik middleware chain", "IPAllowList"/"IPWhiteList", "InFlightReq", "ForwardAuth", "CrowdSec bouncer". Symptoms: "one user is DoSing our chat", "429s not firing", "rate limit says 30 but it's per second", "middleware annotation not applying", "cross-namespace middleware". Do NOT trigger for pure routing/TLS-cert/service-discovery setup with no abuse angle, or cloud-WAF products (Cloudflare/AWS WAF) unless Traefik is in the path. Also: "JA3 fingerprint at ingress", "load a traefik plugin offline / air-gapped", Kubernetes Ingress/IngressRoute middleware, RKE2's bundled Traefik, and choosing where to cap when one identity starves a shared resource (Traefik vs app vs backend).
---

# Traefik hardening — capping abusive traffic at the ingress

Harden a Traefik reverse proxy (standalone or Kubernetes ingress, 2.x or 3.x) against traffic that is *authorized but abusive* — a real user replaying their session token from a script, one client opening 50 parallel streams, request floods, scrapers — the cases a login wall doesn't stop.

## The one idea to internalize first

**A proxy usually cannot reliably tell a "bad" client from a "good" one — so don't try to classify; cap per-identity resource use regardless of client type.**

Every instinct to *detect* the abuser fails on inspection:
- **User-Agent** is one line to spoof (`curl -A "Mozilla/…"`).
- **TLS fingerprint (JA3/JA4)** genuinely separates a browser stack from `python-requests` — but **Traefik cannot see it** (the plugin API never receives the ClientHello; see `references/detection-and-response.md`), and `curl-impersonate` defeats it anyway.
- **Request rate** doesn't cleanly separate: a human dragging their mouse across a chat list fires hundreds of cheap GETs in seconds, while an agentic script doing long-context calls may crawl. Rate ≠ client type.

So the durable controls are the ones that apply **per identity, regardless of client**: cap how much of the scarce resource any one identity may consume, on the *expensive* paths only. Detection (§ below) then exists to decide *whom to throttle or ban*, not to gate requests in real time.

## Decision flow

1. **Name the scarce resource and the expensive path(s).** GPU inference, a heavy DB query, an LLM completion endpoint. Scope every limit to those paths only — never throttle the whole app, or cheap list/poll GETs get caught and real users trip limits while the expensive path stays open. In Kubernetes this means a **separate, higher-priority Ingress/IngressRoute** owning just the expensive paths (`references/deployment.md`).
2. **Pick the identity key**, cheapest-to-most-accurate: source IP (blunt — shared NAT/egress makes it collateral-heavy) → a request header/cookie value → a **verified JWT claim** (best: the one thing an attacker can't forge without invalidating their token). Traefik's `sourceCriterion` keys on IP, a *header*, or host — **not a cookie directly**; keying per-user means decoding the token's claim into a header first (`references/identity-keying.md`).
3. **Cap concurrency first, then rate.** `InFlightReq` (concurrent requests per key) is *the* lever against resource starvation — a streaming response counts as one in-flight request for its whole duration, so `amount` literally bounds how many generations one identity runs at once. `RateLimit` (requests per period) handles floods. Budget for legitimate fan-out (one user action can fire several concurrent backend calls).
4. **Check the topology.** In-memory counters (`InFlightReq`, non-Redis `RateLimit`) are per-Traefik-pod. If one node receives all ingress traffic (single LoadBalancer leader, `externalTrafficPolicy: Local` + L2), counters are effectively global and accurate. If traffic fans across replicas, use **Redis-backed `RateLimit`** (v3.4+) or push the cap into the app/backend — `InFlightReq` has no Redis backend.
5. **Add the perimeter:** `IPAllowList` for intranet CIDRs (blunt but cheap), `Buffering` to cap request-body size against amplification. Never cap the *response* body on a streaming path — it breaks SSE.
6. **Wire detection for response, not gating:** access logs + `429`/`413` metrics identify who to act on; the hard stop is banning/suspending them at the identity provider. Triangulate proxy logs (status codes) + app audit (identity + client) + backend (cost/tokens) — each covers the others' blind spots.
7. **Know where Traefik stops.** Per-user concurrency across a fan-out LB, cryptographic session validation, and reshaping app behavior (e.g. reducing a chat's fan-out) live in the **app or backend**, not the proxy. A hardening plan that's proxy-only is incomplete; say so.

## Middleware quick map (details: `references/middleware-primitives.md`)

| Middleware | Buys | Key gotcha |
|---|---|---|
| `InFlightReq` | per-identity **concurrency** cap (streaming = 1 slot for its duration) | no Redis backend → per-pod; accurate only single-leader |
| `RateLimit` | per-identity **request rate** (± Redis in v3.4+) | **default `period` is 1s** — omit it and "30" means 30/sec |
| `IPAllowList` (v3; was `IPWhiteList` in v2) | perimeter CIDR gate | blunt behind shared NAT; set `ipStrategy.depth` if behind another proxy |
| `Buffering` | request-body size cap (413) | **never** set `maxResponseBodyBytes` on a streaming/SSE path |
| `ForwardAuth` | delegate an allow/deny to a sidecar | one real round-trip **per request**, no caching; `maxBodySize` unbounded by default in v3 |
| `Chain` | compose the above in order | later middleware sees earlier ones' header mutations; reject-cheap-first |

## Identity keying (details: `references/identity-keying.md`)

`Authorization`-keyed limits are **per token** — a user with N sessions gets N buckets. To key on the actual user, decode a JWT claim (e.g. `sub`/`id`) into a header with a JWT plugin, then point `sourceCriterion.requestHeaderName` at that header. This is safe even if the plugin only *decodes* (doesn't verify): a forged claim just lands in a different bucket, and the tampered token fails the app's own signature check → 401, so no expensive work happens. Only validly-signed tokens (carrying the real, unforgeable claim) ever reach the backend, and they share that user's bucket.

## What Traefik genuinely cannot do (say this out loud)

- **See TLS/JA3/JA4 fingerprints** — declined at the plugin layer upstream (traefik/traefik #8627, #12421). Needs a TLS-terminating layer *in front* (nginx+JA4 module, HAProxy, a CDN) that hands Traefik a header.
- **Native WAF (Coraza) in open-source** — that's Traefik **Hub** (commercial). OSS gets the community `coraza-http-wasm` plugin, which its own maintainers flag as not production-grade.
- **Per-user concurrency across a fan-out LB** — `InFlightReq` is per-pod with no Redis; move that cap to the app or backend.
- **Reliably distinguish browser from script** — header/UA checks are a *speed bump* (trivially spoofed), never a control. Use them to raise the cost of casual abuse and to generate intent evidence on an intranet, not as a gate.

## Reference routing

| Task | Read |
|---|---|
| Exact middleware config (file + Kubernetes CRD), 2.x↔3.x field deltas, per-middleware gotchas | `references/middleware-primitives.md` |
| Per-user vs per-token keying, JWT-claim→header plugins, forwarded-identity headers | `references/identity-keying.md` |
| Browser-vs-script signals (Sec-Fetch/UA/JA3/HTTP2), CrowdSec fit, log triangulation & response runbook | `references/detection-and-response.md` |
| Loading plugins with no internet (localPlugins Yaegi vs WASM), plugin-catalog maturity, CRD-vs-annotation chaining, single-leader counting, scoped-Ingress pattern | `references/air-gapped-plugins.md`, `references/deployment.md` |
| A full worked example on a real product | `references/known-products/open-webui-api-abuse.md` (dated) |

## Load-bearing gotchas (keep visible while working)

Beyond the per-middleware traps in the quick map above:

- **Disabling one auth path ≠ blocking another.** Turning off API keys doesn't stop session-JWT replay — different code path in most apps.
- **`period`/keying/topology interact.** A per-header limit without a claim→header decode is per-*token*, not per-user; pair with short token lifetimes or add the JWT plugin.
- **Cross-namespace middleware refs** need Traefik `allowCrossNamespace` for the CRD path — but the plain-Ingress annotation path bypasses that flag entirely (a security asymmetry worth auditing). See `references/deployment.md`.

## How to use this skill

Lead with the mental model, then walk the decision flow for the specific deployment: identify the scarce resource + expensive path, choose the identity key, layer concurrency + rate caps scoped to that path, verify the topology assumption, and name explicitly which parts must live in the app/backend rather than Traefik. Pull exact config from the reference files. When the target is a specific product, check `references/known-products/` for a dated worked example before re-deriving — but keep product specifics out of the generic reference files.
