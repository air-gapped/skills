# Q1 + Q2 — Telemetry Fingerprints & Opt-Out Semantics

**Contents:** Fingerprints (Q1) — SDK packages · hostnames & key shapes ·
OpenTelemetry · Scarf's three mechanisms · update checkers · container-image
angle. Opt-out semantics (Q2) — catalog grep · `DO_NOT_TRACK` is advisory ·
the six pitfalls.

## Fingerprints (Q1)

Detection needs BOTH layers — SDK-package grep AND hostname grep — because
each misses what the other catches: a product running a *self-hosted*
analytics backend (its own PostHog/Plausible/umami instance) has no SaaS
hostname to match, while *transit-domain* telemetry (a vendor-owned
subdomain like `telemetry.<product>.com` that forwards to a SaaS analytics
pipeline) hides the SaaS host behind the vendor's own DNS.

### Layer 1 — SDK packages per ecosystem

| Vendor | npm | Python | Go | Java | Rust |
|---|---|---|---|---|---|
| Sentry | `@sentry/*` | `sentry-sdk`, `sentry_sdk.init(` | `github.com/getsentry/sentry-go` | `io.sentry:sentry` | `sentry` crate |
| PostHog | `posthog-js`, `posthog-node` | `posthog` | — | — | — |
| Segment | `analytics-node`, grep `writeKey` | `analytics-python` | `analytics-go` | — | — |
| Humbug (embedded telemetry SDK, several Python tools) | — | `humbug`, opt-out `BUGGER_OFF` | — | — | — |

### Layer 2 — hostnames & key shapes

```
# Error/crash reporting
o[0-9]+\.ingest(\.(us|us2|de|eu))?\.sentry\.io
https://[a-f0-9]{32}@o[0-9]+\.ingest        # Sentry DSN — single most reliable
                                            # fingerprint; survives import aliasing
notify\.bugsnag\.com | sessions\.bugsnag\.com

# Product analytics
api\.segment\.io/v1/(track|identify|batch) | cdn\.segment\.com   # + grep writeKey
api2\.amplitude\.com/2/httpapi
api\.mixpanel\.com/track
[a-z0-9-]+\.dataplane\.rudderstack\.com     # + grep dataPlaneUrl
www\.google-analytics\.com/mp/collect       # keys G-[A-Z0-9]{10} / UA-[0-9]+-[0-9]+
(us|eu)\.i\.posthog\.com | app\.posthog\.com  # key shape phc_[A-Za-z0-9]+
browser-intake-.*datadoghq\.(com|eu)        # + clientToken:'pub...'
plausible\.io/api/event
data-website-id                             # umami
```

### OpenTelemetry as an exfil channel

OTel is neutral; the discriminator is the endpoint literal —
`localhost:4317/4318` is benign plumbing, a hardcoded public hostname in
`otlptracehttp.WithEndpoint("...")` or a baked `OTEL_EXPORTER_OTLP_ENDPOINT`
is phone-home.

### Scarf — three distinct mechanisms, easy to miss

1. `scarf-js` / `@scarf/scarf` in package.json **dependencies** (not
   devDeps): `postInstall` reports OS/arch at every consumer `npm install`;
   opt-out `SCARF_ANALYTICS=false`.
2. **Scarf Gateway** — a vendor-branded registry/download host that CNAMEs
   to `gateway.scarf.sh`: the source is clean, the *distribution channel*
   phones home. Detect: `dig CNAME <registry-host>`.
3. **Scarf pixel** `static.scarf.sh/a.png?x-pxid=` in READMEs — fires when
   docs are viewed (matters for air-gapped doc mirrors).

### Update checkers phone home even with "no analytics"

Update checking is its own telemetry channel, usually independent of the
analytics setting. Grep for the embedded checker libraries and endpoints:

- HashiCorp Checkpoint: `checkpoint-api.hashicorp.com/v1/check/<product>` —
  and vendors sometimes rehost Checkpoint under their own domain, so grep
  the `checkpoint` package import, not just the hostname.
- npm `update-notifier` → `registry.npmjs.org` on CLI startup.
- Go self-update `rhysd/go-github-selfupdate` → `api.github.com/.../releases`.
- `electron-updater`.

### Container-image angle

`strings` / `strings -e l` on binaries → hostname regexes + `phc_...` +
Sentry-DSN shape + `writeKey`; `docker inspect` ENV for `SENTRY_DSN`,
`SEGMENT_WRITE_KEY`, etc.; entrypoint scripts for `curl|wget` to
non-localhost / `anonymous-statistics` / uuid-then-POST; resolve the
image's registry-host CNAME for `gateway.scarf.sh`. A vendor *baking in*
`DO_NOT_TRACK=1` or `SCARF_ANALYTICS=false` is itself an admission that
telemetry exists.

---

## Opt-out semantics (Q2) — does "off" mean off?

**Grep for kill-switch-shaped tokens — substrings, not exact names.** The
*presence* of opt-out handling in a codebase is itself evidence telemetry
exists. Detection needs recall, not a catalog: extract uppercase
env-var-shaped tokens and match telemetry-adjacent substrings —

```
grep -rhoEI --exclude-dir=.git '[A-Z][A-Z0-9_]{4,}' <src-dir> \
| grep -E 'TELEMETRY|ANALYTIC|TRACKING|DO_NOT_TRACK|OPT_?OUT|OPT_IN|USAGE_(DATA|STATS?)|CRASH_?REPORT|DIAGNOSTIC|METRICS|CHECKPOINT|PHONE_?HOME|INSIGHT' \
| sort | uniq -c | sort -rn
```

(`-I` skips binaries; `OPT_IN` keeps its underscore so bash's `OPTIND`
doesn't flood the output. A near-empty result on a large codebase is a
meaningful green flag, not a failed grep — re-run without the second stage
to confirm tokens were extracted.)

False positives are cheap — every hit gets its polarity verified in source
regardless (pitfall 3). Two blind spots this closes differently:

- **Opt-outs that aren't env vars** — also grep the *config-parser* key
  space for lowercase `telemetry`, `analytics`, `usage_stats`,
  `crash_report`, `error_report` (the schema below has targets
  {env|exec|file|registry} for a reason).
- **SDK-named oddballs with no such substring** (e.g. Humbug's
  `BUGGER_OFF`) — these are caught by the Layer-1 SDK-package grep, not by
  name-guessing: once the SDK import is found, its opt-out mechanism comes
  from that SDK's docs/source.

Schema model (from `beatcracker/toptout`, frozen 2023-02 but structurally
excellent): each mechanism has traits {usage_data, update_check,
error_report}, a target {env|exec|file|registry|noop}, a scope
{machine|user|process}, and opt_out/opt_in values where `opt_in: null`
means "the variable must not exist".

**`DO_NOT_TRACK` is advisory — never assume it works.** Spec at
`donottrack.sh` (consoledonottrack.com lapsed to unrelated content,
verified 2026-07-14). Adoption is inconsistent and several prominent
projects have explicitly refused it (closed-unmerged PRs). It is
process-env-scoped only — it cannot stop install-time telemetry. Verify
honoring in the candidate's source, never from an adopter list.

### The six pitfalls — check each explicitly

1. **Opt-out by default** — assume telemetry ships enabled. Also check
   release notes/changelogs for telemetry added silently between versions.
2. **Phones home before opt-out can apply** — installers and first-run
   code often send an event before the operator ever sees the opt-out
   notice. Dynamic test: capture from before first run, not after.
3. **Value-vs-presence bugs** — code may test only whether the variable
   *exists*, so `VAR=false` behaves like `VAR=true` (or vice versa).
   Polarity is wildly inconsistent across tools: `=1` disables telemetry
   in some and *enables* it in others, and some require specific strings.
   Verify the exact comparison the code makes, in source, not docs.
4. **Reduce-not-eliminate** — tiered "telemetry level" settings where only
   the lowest tier stops usage data; plugins/extensions are often
   explicitly out of scope and need their own per-plugin audit.
5. **Update-check is a separate channel** with its own kill switch — one
   product can require two or more variables to go fully quiet.
6. **Destination drift** — the opt-out variable stays stable across
   versions while the backend destination moves. Vet the variable, but
   re-vet destinations across versions.

**Output for Q2:** each kill switch cited as
`ENV_VAR=value (polarity verified in source at file:line)`. A kill switch
whose polarity was not verified in source is reported as `unverified`.
