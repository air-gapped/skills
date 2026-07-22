# Keying limits on identity, not just source IP

The accuracy of every per-identity cap depends on *what it is keyed on*. Ranked cheapest → most accurate: source IP → a request header/cookie value → a **verified JWT claim**. This file covers how to key on the actual user rather than an IP or a single token.

## Why source IP is usually wrong

- Many users behind one corporate NAT/egress share an IP → an IP limit is collateral-heavy (throttles innocents) and blunt (the abuser hides in the crowd).
- A single user on many devices spans several IPs → an IP limit under-counts them.
- Behind another proxy/LB, Traefik only sees the real client IP if the entrypoint trusts the forwarding hop: `entryPoints.<name>.forwardedHeaders.trustedIPs: ["<lb-cidr>"]`. Without it, XFF/Forwarded are stripped (secure default) and `ipStrategy.depth` degrades to `RemoteAddr` (the LB's IP) — so *all* traffic keys to one bucket. Set `trustedIPs` before trusting any depth-based IP strategy.

## `sourceCriterion` reads a header, not a cookie

`RateLimit`/`InFlightReq` `sourceCriterion` supports `ipStrategy`, `requestHeaderName`, or `requestHost` — there is **no native cookie-value criterion**. Two consequences:

- Keying on `Authorization: Bearer <token>` gives one bucket **per token**. A user with N active sessions gets N buckets — a trivial bypass by re-logging in. Pair with short token lifetimes + a low max-sessions cap, or key on the user (below).
- To key on a **cookie** (e.g. a session cookie), first copy the cookie value into a header (a small Headers step or plugin), then point `requestHeaderName` at that header.

## Per-user keying: decode a JWT claim into a header

If the token is a JWT, decode its stable user claim (`sub`, `id`, `email`) into a request header with a JWT plugin, then key the limit on that header. Now every session of one user shares **one** bucket.

```yaml
# 1) Install the plugin in Traefik STATIC config (Helm values / traefik.yml)
experimental:
  plugins:
    jwtHeaders:
      moduleName: github.com/traefik-plugins/traefik-jwt-plugin   # a real plugin; pick the one whose claim-injection fits
      version: v<latest>   # pin an exact tag from the repo's Releases page — never leave floating
```
```yaml
# 2) Middleware: decode + inject the claim as a header
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata: { name: jwt-userid, namespace: apps }
spec:
  plugin:
    jwtHeaders:
      forwardHeaders:
        X-User-Id: "sub"        # or the app's user-id claim
      # secret/JWKS config per the plugin's README (HS256 shared secret or RS256 JWKS URL)
```
```yaml
# 3) Chain jwt-userid BEFORE the limits, and key the limits on X-User-Id
spec:
  chain:
    middlewares:
      - name: jwt-userid
      - name: chat-inflight     # sourceCriterion.requestHeaderName: X-User-Id
      - name: chat-ratelimit    # sourceCriterion.requestHeaderName: X-User-Id
```

### Why this is safe even if the plugin only decodes (doesn't verify the signature)

A common worry: "if the plugin doesn't verify the signature, can't an attacker forge a claim to land in someone else's / an empty bucket?" It doesn't matter for enforcement:

- A forged claim produces a **different bucket** — but that tampered token then fails the *application's own* signature check (HS256 with the app secret, or RS256 against the IdP) → 401, so no expensive backend work happens.
- Only **validly-signed** tokens — carrying the real, unforgeable claim — ever reach the backend, and they all share that user's bucket.

So decode-only keying is sufficient for rate/concurrency enforcement. Verifying in the plugin too (shared secret / JWKS) is belt-and-suspenders and lets Traefik reject bad tokens earlier, but the security of the *limit* doesn't depend on it.

## Forwarded-identity headers (attribution downstream)

Separately from keying at Traefik, many apps can forward the authenticated user identity to the *backend* as headers, so a downstream gateway can attribute or cap per user without re-parsing the session. This is an **application feature**, not a Traefik one — the app injects e.g. `X-<App>-User-Id/-Email` on its upstream calls, and the backend (e.g. an LLM gateway) reads a configured header as the "end user" for spend/quota. Traefik's role is only to pass those headers through untouched. See `references/known-products/` for a concrete instance.

Signed variant: some apps can emit a short-lived **signed JWT** asserting the identity (`X-…-User-Jwt`) so the backend can *cryptographically* trust "who" — preferable to plain headers when the backend enforces budgets, since plain forwarded headers are only as trustworthy as the network path.

## Rule of thumb

- Quick + good-enough on a single-leader topology: key on `Authorization` + short token TTL + low max-sessions.
- Accurate across multi-login and multi-device: decode the user claim → header, key on that.
- Cross-pod accuracy: the above **plus** Redis-backed `RateLimit`, or move the cap to the app/backend (Traefik `InFlightReq` can't share state across pods).
