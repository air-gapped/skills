# Loading Traefik plugins with no internet (air-gapped) + catalog maturity

Traefik plugins normally fetch from `plugins.traefik.io` at startup. In an air-gapped cluster they must be vendored locally. This is well-trodden and needs no sidecar or registry mirror — but the two plugin runtimes differ, and the difference matters.

## Two plugin mechanisms

- **Yaegi-interpreted Go** (since Traefik 2.3): plugin *source* is interpreted at runtime. No compile step, but constrained by Yaegi's Go subset (see gotchas).
- **WASM (`http.wasm`, Traefik 3.0+ only):** a precompiled `.wasm` module runs in a WASM runtime. Bypasses Yaegi entirely — the robust choice for anything non-trivial, but **not available on 2.x**.

## `experimental.localPlugins` — the offline path (zero network calls)

`experimental.plugins` (catalog mode) always reaches the CDN at startup and is unusable air-gapped. `experimental.localPlugins` reads pure local filesystem — **no fallback, telemetry, or version-check network call** (verified in Traefik source: the HTTP downloader object is only constructed when catalog `plugins` is configured; local mode never instantiates it).

```yaml
# Static config (Helm values / traefik.yml). Same field shape 2.x and 3.x.
experimental:
  localPlugins:
    myplugin:
      moduleName: github.com/org/repo    # NO version/hash field in local mode
```

**Directory layout** — the source lives under `./plugins-local/src/<module-path>/`, relative to Traefik's working directory (baked into the image or mounted as a volume):
```
./plugins-local/
  └── src/github.com/<org>/<plugin>/
      ├── *.go                 # (Yaegi) source
      ├── go.mod / go.sum
      ├── vendor/              # (Yaegi) any non-stdlib deps MUST be vendored here
      ├── plugin.wasm          # (WASM) the precompiled module instead of .go
      └── .traefik.yml         # REQUIRED even in local mode (displayName, type, import, testData)
```

- `.traefik.yml` is **not** skipped in local mode — startup hard-fails if `displayName`/`summary`/`testData` (and, for Yaegi, `import`) are missing/mismatched.
- **How to obtain the source for transfer:** there is no `traefik plugin download` CLI. On an internet-connected machine either `git clone` the plugin repo into the layout above (the officially documented method), or fetch the catalog archive `plugins.traefik.io/public/download/<module>/<version>` (a versioned zip), then carry it across the air gap.
- **WASM artifact:** plugins that ship a prebuilt `.wasm` as a GitHub Release zip asset are the easiest — download once, carry over, no build. Otherwise compile with TinyGo yourself.

## Yaegi gotchas (why WASM is safer for non-trivial plugins offline)

- Curated stdlib subset only (`yaegi/stdlib`) — uncommon packages fail with "package not found".
- No cgo, no assembly, no `//go:embed`, no compiler directives.
- Third-party imports resolve only if **vendored** under the plugin's own tree.
- `unsafe`/`syscall` excluded by default (they run inside Traefik's trust boundary).
- Practical implication: anything beyond header-mangling is more robust as a **precompiled WASM** module (TinyGo, outside Traefik) — but that requires Traefik 3.x.

## Catalog maturity census (as of 2026-07; re-verify before adopting)

No editorial "verified" tier exists — any repo with a valid `.traefik.yml` auto-indexes. All plugin middlewares work identically via file provider **and** the Kubernetes `Middleware` CRD's `plugin:` stanza.

| Plugin | Purpose | Verdict |
|---|---|---|
| `maxlerebourg/crowdsec-bouncer-traefik-plugin` | CrowdSec LAPI bouncer (IP reputation/behavior) | production-ready, actively maintained |
| `PascalMinder/geoblock` / `nscuro/traefik-plugin-geoblock` | country allow/deny (offline IP2Location data — air-gap friendly) | active; but for pure intranet-CIDR use, built-in `IPAllowList` is the right tool, no plugin |
| `traefik-plugins/traefik-jwt-plugin` (and "JWT Headers" variants) | decode JWT claim → header (enables per-user keying) | usable; the composition piece for `identity-keying.md` |
| `jcchavezs/coraza-http-wasm-traefik` | WASM WAF (OWASP CRS body/path inspection) | usable via localPlugins; maintainers disclaim production-grade perf; native Coraza is Hub-only |
| bot-UA blocklist plugins (e.g. `holysoles/bot-wrangler`) | block known AI/scraper UAs | cheap defense-in-depth; same spoofability caveat as any UA check |
| JA3/JA4 fingerprint plugin | — | **does not exist** — platform gap, not a maintenance gap |

## Known air-gap trap (catalog mode only)

`experimental.plugins` (catalog) makes a blocking call to `plugins.traefik.io` on **every restart**, and a transient failure can disable all plugin middlewares even with a cached archive (traefik/traefik #13005, a v3.5.3+ regression). `localPlugins` is immune — it never calls out. One more reason air-gapped deployments must use `localPlugins`, not catalog mode with a mirror.
