# Phase 2 — Dynamic Verification Harness

**Contents:** Step 1 isolation (`--network=none`) · 2 deny+log · 3 passive
enumeration · 4 MITM CA-injection (Q5+Q1) · 5 post-activation egress-deny
(Q3 tie-breaker) · 6 browser console (Q6) · 7 stale-feed (Q7) · 8 faketime ·
destination interpretation.

Static grep is necessary but insufficient: transit-domain telemetry,
offline-flag fallback downloads, and runtime-computed image names all
defeat static analysis. The harness is ground truth. Run it on a
**disposable host or VM** — the deny+log step rewrites firewall rules, and
the candidate runs with real privileges.

Capture every step in **two windows**: first-run (fresh volume, 2–5 min —
install/license/startup telemetry, including events sent *before* opt-out
can apply) AND steady-state (10–30 min — timer-based heartbeats a 30-second
capture misses).

## Step 1 — Isolation: does it work with zero network? (Q4)

```
docker run --rm --network=none <image> <cmd>
# non-container: unshare -n <cmd>   or   systemd-run -p PrivateNetwork=yes <cmd>
```

Interpretation: clean fast start = no blocking net dependency; 30–120 s
hang = synchronous phone-home hitting a socket timeout; crash referencing a
URL/resolver = hard dependency.

## Step 2 — Deny + log every attempted destination

**Critical Docker nuance: bridged-container egress traverses FORWARD /
`DOCKER-USER`, NOT `OUTPUT`** — logging OUTPUT silently captures nothing
for containers.

```
iptables -I DOCKER-USER -j LOG --log-prefix "CANDIDATE-EGRESS: " --log-level 4
iptables -A DOCKER-USER -j REJECT   # REJECT (not DROP): tool fails fast, not hangs
```

## Step 3 — Passive enumeration

Fastest signal is DNS (names resolve before connect):

```
tshark -i any -Y 'dns.flags.response==0' -T fields -e dns.qry.name
```

Process-attributed alternatives: `picosnitch` (per-executable SQLite
ledger, eBPF+fanotify), Tetragon (`connect` events bound to the exact
binary), `egress-auditor` (auto-generates allow-rules from observed
egress), `opensnitch` (interactive). Low-tech fallback:
`strace -f -e trace=network -yy`.

**Kubernetes charts**: kind + Cilium/Hubble default-deny egress;
`hubble observe --verdict DROPPED` lists every destination the chart
wanted. Default-deny blocks DNS, so
`hubble observe --type l7 --protocol dns` doubles as the resolution
inventory.

## Step 4 — Active MITM (settles Q5 AND inventories Q1 in one test)

Run `mitmdump` and point the tool at mitmproxy's generated CA
(`~/.mitmproxy/mitmproxy-ca-cert.pem`) via the ecosystem-appropriate env
var (`references/ca-trust.md` table):

- Traffic appears + decrypts cleanly → honors proxy env vars AND a custom
  CA → **passes Q5**, and the decrypted stream is the full phone-home
  inventory (hostnames + request bodies) for Q1.
- No traffic despite `HTTPS_PROXY` set → ignores proxy config (portability
  red flag); use `--mode transparent` + iptables REDIRECT to capture
  anyway.
- Connection *still fails after correct CA injection* ("certificate verify
  failed" on the handshake) → **certificate pinning** → un-mirrorable →
  air-gap blocker (Q5 hard-fail).

## Step 5 — Post-activation egress-deny (the Q3 tie-breaker; MANDATED)

Activate/license/log-in the product while connected, then apply a
permanent egress-deny (step 2 rules without removal) and exercise core
functionality for the steady-state window.

- Keeps working → not a proxy; the earlier egress was
  telemetry/update-class.
- Degrades to read-only, nags, or shuts down (the continuous-license-ping
  pattern) → **proxy-in-disguise**, regardless of what the marketing page
  says.

This is the only reliable way to draw the `possible-with-mirror` vs
`proxy-in-disguise` boundary. Do not skip it when Q3 is in play.

## Step 6 — Browser console under deny (Q6, web UIs only)

With egress denied, load the web UI and read the browser console/network
tab: failed requests to `fonts.googleapis.com`/`unpkg.com`/
`cdn.jsdelivr.net`/analytics hosts reveal CDN-asset and client-side
telemetry dependencies the backend capture misses. Broken layout = the UI
itself isn't air-gap-clean.

## Step 7 — Stale-feed run (Q7, security/feed tools only)

Give the tool a deliberately old feed (restore a weeks-old DB snapshot, or
block the update endpoint and let it age) and run a scan:

- Refuses to run and names the age limit → fail-closed, best.
- Warns loudly, proceeds → acceptable, document the warning string.
- Scans silently and reports green → silent-stale; caps grade at
  `possible-with-mirror` with explicit warning.

## Step 8 — Time skew (`faketime`) — TUF/license/cert expiry

```
faketime '+30 days'   <startup-or-verify-path>
faketime '+13 months' <startup-or-verify-path>
```

Failures expose TUF metadata expiry (~7-day sigstore window), license
expiry behavior, cert notAfter, JWT exp — without touching the system
clock. Caveat: LD_PRELOAD doesn't reliably hook statically-linked Go
binaries — for Go tools, skew a disposable container/VM clock instead
(`docker run --cap-add SYS_TIME` + `date -s`, or a VM snapshot).

## Destination interpretation heuristics

| Class | Hosts | Reading |
|---|---|---|
| Telemetry (red flag) | `api.segment.io`, `*.amplitude.com`, `*.mixpanel.com`, `sentry.io`, `*.google-analytics.com`, `*.datadoghq.com` | Q1 evidence |
| Expected for a container tool | `registry-1.docker.io`, `*.ghcr.io`, `quay.io` | mirrorable; goes on the mirror list |
| Grey (auto-updater — disable) | `github.com`, `api.github.com` | Q2 separate-channel check |
| Bad for air-gap (should be vendored) | `*.pypi.org`, `registry.npmjs.org` | Q4 runtime-download evidence |
| Probe (behavior fork?) | `connectivity-check.*`, raw `8.8.8.8`/`1.1.1.1` | Q4 red flag if behavior forks on it |

No turnkey orchestrator exists that runs isolation → deny+log → mitmproxy
in sequence and diffs the destination sets — assemble the steps manually
and record each step's destination set in the working state so the report
can show first-run vs steady-state vs feature-exercise deltas.
