# Detection & response — signals, their honest limits, and the runbook

Detection at a proxy is for **deciding whom to throttle or ban** — not for gating requests in real time. Every "is this client bad?" signal below is spoofable or blind in some way; treat them as evidence, and let per-identity caps (not classification) do the actual enforcement.

## Browser-vs-script signals, ranked by real-world value

| Signal | Separates browser from default script? | Spoof cost | Can Traefik see it? |
|---|---|---|---|
| `Sec-Fetch-Site`/`-Mode`/`-Dest`/`-User` presence | **Yes** — set by browsers, not by JS; default `curl`/`requests`/`httpx`/`node fetch` send none | one line (`curl-impersonate`, adding headers) | Yes (Headers/plugin match) |
| `User-Agent` string | Weakly — tools announce themselves by default | one flag (`-A`) | Yes |
| TLS fingerprint (JA3/JA4) | **Yes** — browser TLS stack ≠ python/curl | moderate (`curl-impersonate`, `tls-client`) | **No** — see below |
| HTTP/2 fingerprint (frame/SETTINGS order) | Yes | moderate (same tools) | **No** — below plugin API |

**JA3/JA4 and HTTP/2 fingerprinting are real but invisible to Traefik.** The plugin API never receives the raw ClientHello or the HTTP/2 frame sequence — this was explicitly declined/left-open upstream (traefik/traefik #8627, #12421). Using them requires a TLS-terminating layer *in front of* Traefik (nginx with a JA4 module, HAProxy, Apache Traffic Server, a CDN) that computes the hash and passes it to Traefik as a header for a `ForwardAuth`/plugin to consume. There is **no JA3/JA4 plugin** in the Traefik catalog.

**The honest framing:** header/UA/fingerprint checks are a **speed bump**, not a control. On an open internet they stop only the laziest bots. On an **intranet with identifiable users** they have a different value: the casual `curl`/CLI user is stopped by default, and anyone who *spoofs* to get past it has converted "didn't know" into deliberate circumvention — which is an evidence/policy matter, not an engineering one. Deploy them as deterrence and to raise the cost of casual abuse; never rely on them as the boundary. Prefer allowlisting the one legitimate client shape (e.g. same-origin browser markers) over blocklisting an endless list of tool UAs.

## Where a header gate lives

A plain Ingress rule can't express "require header X". Options:
- **A plugin** (a "block if header missing" / bot-filter plugin), or
- **One IngressRoute** *just for this matcher* (fine even if IngressRoutes are avoided elsewhere): match the expensive path AND the *absence* of the browser marker, route to a 403 service. v3 rule syntax supports `!` negation, e.g. `Host(\`app\`) && PathPrefix(\`/expensive\`) && !HeaderRegexp(\`Sec-Fetch-Site\`, \`.+\`)`.

Combine with rate/in-flight caps; never ship it alone.

## CrowdSec bouncer — what it's for (and isn't)

`maxlerebourg/crowdsec-bouncer-traefik-plugin` (actively maintained) queries a CrowdSec LAPI per request and bans/captchas at the edge. Its detection is **IP-behavior + community reputation** (burst rates, credential-stuffing/scan signatures, shared blocklists). That fits an *external attacker* model. It does **not** fit "one legitimate internal user replaying their own valid session from a script on the same subnet" — no bad reputation, no anomalous IP. Deploy CrowdSec for perimeter/reputation defense; don't expect it to catch insider token-replay without writing custom scenarios keyed on something other than IP.

## WAF (request-body/path inspection)

- **Native Coraza WAF is Traefik Hub (commercial).** OSS Traefik does not ship it.
- OSS option: the community `jcchavezs/coraza-http-wasm-traefik` WASM plugin — real body/path inspection (OWASP CRS-style rules), but its maintainers explicitly disclaim production-grade performance. Load it via `localPlugins` for air-gap (see `air-gapped-plugins.md`); validate body-buffer limits against real payload sizes before relying on it.

## Access logs — capture the User-Agent WITHOUT leaking credentials

To see the real client UA/IP in Traefik's access log, keep headers **dropped by default** and allowlist only safe ones — flipping the default to `keep` would log `Authorization`/`Cookie` (i.e. write session tokens into the logs):

```yaml
# Helm values (traefik-helm-chart)
logs:
  access:
    enabled: true
    format: json
    fields:
      headers:
        defaultmode: drop          # keep as drop — do NOT set to keep
        names:
          User-Agent: keep
          Sec-Fetch-Site: keep
```

Traefik's access log goes to **stdout**, so a cluster log pipeline collects it regardless of pod moves — no sidecar/PVC needed.

## Triangulate three sources (each covers the others' blind spots)

| Source | Gives | Blind to |
|---|---|---|
| Proxy access log (Traefik) | status codes incl. **429/413** (enforcement hits), UA, IP, path | the app's *user identity* (only token/IP) |
| App audit log | frequency · client UA · **user identity** · IP | status/429, tokens, cost |
| Backend log (e.g. LLM gateway) | **tokens / cost** per user | pre-proxy or blocked traffic |

The proxy sees enforcement outcomes; the app sees *who*; the backend sees *how expensive*. All three together say "user X ran up cost Y and hit N 429s from a non-browser client."

## Response runbook (the hard stop is not at Traefik)

1. Identify from the triangulated logs: high count + concurrency spikes + non-browser client + flat 24h activity = abuser fingerprint; a real user trips none of these.
2. Graduated response: move them to a restricted tier (cheaper backend / lower caps) → temporary throttle bounded by token lifetime → **suspend/disable at the identity provider** (the real hard stop; Traefik can only shed load, not revoke identity).
3. Alert on the leading indicator: a per-route surge in `traefik_router_requests_total{code="429"}` (or `413`). Filter to the expensive router so normal 429s elsewhere don't drown it.

## Log-analysis gotcha

For counting **paths/endpoints**, use exact tools (`jq | sort | uniq -c`). Do **not** use a log-*folding* tool (e.g. `lessence`) to count paths — segment-normalizing folders collapse distinct endpoints under one template and destroy the counts. Use folding tools only for the messy free-text field (`user_agent`), where clustering is the point.
