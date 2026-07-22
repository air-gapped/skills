# Deployment mechanics — chaining, scoping, and the counting trap

How to attach a middleware chain in Kubernetes, scope limits to only the expensive paths, and reason about whether in-memory counters are actually accurate.

## Scope limits to the expensive path only (the scoped-Ingress pattern)

Never attach rate/concurrency limits to the whole app — cheap high-frequency paths (list/poll GETs, static assets) would trip the limit while the expensive path stays open, and normal users would hit 429s from ordinary UI activity. Middleware annotations on a plain `Ingress` apply to **all** routers that Ingress creates, so isolate the expensive paths in a **separate, higher-priority Ingress**. Traefik gives the longer/more-specific path rule higher priority, so those paths hit the limited router while everything else keeps using the existing unthrottled Ingress.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-expensive-limited
  namespace: apps
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
    # executed left→right; format: <namespace>-<name>@kubernetescrd, comma-separated
    traefik.ingress.kubernetes.io/router.middlewares: >-
      apps-intranet-only@kubernetescrd,apps-chat-inflight@kubernetescrd,apps-chat-ratelimit@kubernetescrd
spec:
  ingressClassName: traefik
  rules:
    - host: app.example
      http:
        paths:
          - { path: /api/expensive, pathType: Prefix, backend: { service: { name: app, port: { number: 80 } } } }
  tls:
    - { hosts: [app.example], secretName: app-tls }   # reuse the existing cert
```

## CRD chain vs annotation chain (and a security asymmetry)

- **CRD path** (`IngressRoute` referencing a `Middleware`/`chain`): the idiomatic 2026 approach; the `chain` type gives a named, reusable ordered bundle. Cross-namespace `Middleware` references are **rejected unless** `providers.kubernetesCRD.allowCrossNamespace: true` (Helm default `false`).
- **Annotation path** (plain `Ingress` + `router.middlewares`): the value embeds the namespace as a string (`<ns>-<name>@kubernetescrd`) and is **not gated by `allowCrossNamespace`** — a plain Ingress can pull a middleware from any namespace with no provider-level guardrail, while the "safer-looking" CRD path fails closed. Audit `Ingress` annotations for embedded cross-namespace refs.

Order is execution order in both forms, and a later middleware sees earlier ones' header mutations — so a claim→header decode must precede the limits that key on that header.

## The counting trap — in-memory counters: global or per-pod?

`InFlightReq` and non-Redis `RateLimit` count **per Traefik pod**. Whether that's accurate depends entirely on how ingress traffic is distributed:

- **Single-leader (accurate):** if one node receives all ingress traffic — e.g. a LoadBalancer VIP announced from a single node (L2/ARP) with `externalTrafficPolicy: Local` — all requests land on that node's Traefik pod, so the in-memory counter *is* effectively global. This is common with Cilium L2 / MetalLB L2. Caveat: on leader failover the counters reset on the new pod (a brief, benign window).
- **Fan-out (inaccurate):** if `externalTrafficPolicy: Cluster`, or an external LB round-robins across nodes, each Traefik pod counts independently — a limit of N per pod becomes N×(pods) in practice. Then either use **Redis-backed `RateLimit`** (v3.4+), divide limits by receiving-pod count (crude), or move the cap to the app/backend (`InFlightReq` has no distributed backend at all).

Check it: `kubectl -n <traefik-ns> get svc traefik -o jsonpath='{.spec.externalTrafficPolicy}'` → `Local` = single-leader-friendly. Confirm which node holds the VIP if using L2 (`kubectl get leases -A | grep -i l2announce` for Cilium).

## Helm chart notes

- The proxy (app) version and the Helm chart version move on **separate tracks**; a chart major can rename/restructure values (e.g. consolidating `service.type`/`loadBalancerSourceRanges` into a generic `service.spec` passthrough) independently of the Traefik version. Re-diff `helm show values` against local overrides on every chart-major bump.
- `providers.kubernetesCRD.enabled` is on by default (CRD middlewares available). `allowCrossNamespace` is off by default (see asymmetry above).
- Static config (entrypoints `forwardedHeaders.trustedIPs`, `experimental.localPlugins`, access-log fields) lives in Helm values, not in CRDs — a plugin or trusted-IP change is a chart upgrade + pod roll, not a `kubectl apply` of a CRD.

## Verify the limits actually fire

Confirm enforcement before trusting it — replay a token against the scoped path and watch for 429/413:

```bash
TOKEN="<a real session token>"; URL="https://app.example/api/expensive"; BODY='{"k":"v"}'
# Concurrency: 50 parallel requests — expect a wall of 429 once InFlightReq.amount is hit
for i in $(seq 1 50); do
  curl -sk -H "Authorization: Bearer $TOKEN" -d "$BODY" "$URL" -o /dev/null -w "%{http_code}\n" &
done; wait | sort | uniq -c
# Rate: 200 quick requests — expect 429s once RateLimit average+burst is exceeded
for i in $(seq 1 200); do curl -sk -H "Authorization: Bearer $TOKEN" -d "$BODY" "$URL" -o /dev/null -w "%{http_code} "; done; echo
```

Two checks that separate "working" from "false-tripping":
- **Fairness:** while the flood runs, time a single request from a *different* token — its latency should stay normal (the cap is per-identity, not global).
- **No false positives:** exercise a normal multi-step user action (which legitimately fans out several concurrent calls) — it must not trip the concurrency cap. If it does, raise `amount` or cut the fan-out at the app.

Enforcement metric to alert on: a per-router surge in `traefik_router_requests_total{code="429"}` (filter to the scoped router so ordinary 429s elsewhere don't drown it).

## Where the proxy layer ends

State this explicitly in any plan. Traefik can cap concurrency/rate per identity and shed load, but it cannot:
- share concurrency state across a fan-out without Redis (and `InFlightReq` never can) → app/backend,
- revoke a session or suspend a user → identity provider,
- reduce the *work per request* (e.g. an app firing 5 concurrent backend calls per user action) → app config,
- cryptographically validate a session it doesn't own → app, or a `ForwardAuth` callback to the app.

A proxy-only hardening plan is incomplete; name the app/backend/IdP pieces alongside the Traefik ones.
