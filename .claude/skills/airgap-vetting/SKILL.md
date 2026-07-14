---
name: airgap-vetting
description: >-
  Vet an open-source product for air-gap readiness BEFORE adoption. Answers
  eight questions — telemetry, does-opt-out-actually-work, proxy-in-disguise
  over a hosted API, runtime downloads, custom-CA support, feature-level
  content egress / offline degradation, day-two sustainment (feed mirroring,
  staleness), and a 4-grade verdict (air-gap-native / possible-with-mirror /
  proxy-in-disguise / no-go). Two-pass: static grep of source + container
  image (bundled fingerprint tables work offline), then an optional dynamic
  harness (--network=none, egress deny+log, mitmproxy CA injection, faketime).
  Writes AIRGAP-VETTING.json + .md. Use for any "should we adopt X?" question
  in a disconnected environment, not just when the user says "air gap".
when_to_use: >-
  Use when the user asks to vet, audit, or evaluate a tool for air-gapped,
  offline, disconnected, or restricted-egress use: "does X work
  offline", "can we run X air-gapped", "will X phone home", "does X send
  telemetry", "is X really open source or a wrapper around their cloud",
  "what does X download at runtime", "can X use our internal CA", "check X
  before we adopt it", "is X self-hostable for real", "what breaks if X
  can't reach the internet", "how do we keep X updated offline". Also on
  symptoms: a tool hangs or crashes without internet, a security
  review needs an egress inventory, or an adoption decision needs an
  offline-readiness verdict. This is an adoption/offline-readiness vet — not
  CI/CD pipeline hardening and not source-code vulnerability scanning.
argument-hint: "<product|repo-path|image-ref> [--dynamic] [--repo PATH] [--image REF] [--stakes low|high]"
---

# airgap-vetting

Rapidly vet a candidate OSS product for air-gap readiness before adoption.
Answers eight questions and assigns one of four grades. The organizing
insight from the research behind this skill: **"documents an offline flag" ≠
"works offline"** — several tools fall back to downloading even with their
own offline flag set, and the decisive distinction (*air-gap-native* vs
*proxy-in-disguise*) is only provable by denying egress **after** activation
and watching whether the product keeps working.

Invoke with `/airgap-vetting <target> [--dynamic] [--repo PATH] [--image REF]
[--stakes low|high]`.

**Arguments** (parse from `$ARGUMENTS`):
- target (first positional, required): a product name (`meilisearch`), a
  local source checkout, a git URL, or a container image ref. Resolve
  whatever else is needed in Phase 0.
- `--dynamic`: run the Phase-2 dynamic harness (requires Docker and, for
  the deny+log step, root/iptables on a **disposable** host or VM). Without
  it the vet is static-only and the verdict says so.
- `--repo PATH` / `--image REF`: explicit source checkout / image when the
  positional target is ambiguous.
- `--stakes low|high` (default `low`): `high` mandates the dynamic pass for
  any candidate that survives static (refuse to emit a final grade without
  it); `low` allows a static-only provisional grade.

**The eight questions:**

| # | Question | Reference |
|---|----------|-----------|
| 1 | Sends telemetry to the internet? | `references/telemetry.md` |
| 2 | Can telemetry be turned off — and does off mean off? | `references/telemetry.md` |
| 3 | Actually a proxy over a hosted API? | `references/downloads-and-proxy.md` |
| 4 | Requires internet at runtime for downloads? | `references/downloads-and-proxy.md` |
| 5 | Supports custom CA / private TLS trust? | `references/ca-trust.md` |
| 6 | Ships user *content* out / degrades offline? | `references/content-egress.md` |
| 7 | Can it be kept alive offline (day-two)? | `references/sustainment.md` |
| 8 | Overall verdict grade | rubric below |

Two cross-cutting sub-check clusters feed several questions:
time/revocation/offline signature verification (`references/verification-time.md`)
and identity/inbound/connectivity-probes (tail of `references/content-egress.md`).

Read each reference file at its question — they carry the exact hostnames,
env vars, grep patterns, and known counter-examples. Do not answer a
question from general knowledge when the reference has a table for it: the
tables encode verified, sourced fingerprints, including several cases where
docs and behavior disagree.

---

## Phase 0: Scope the target

1. **Check prior art.** Read `references/known-products.md`. If the
   candidate (or its direct dependency) already has a row, say so up front
   — the row may answer the whole request, or at least pin expectations.
2. **Resolve the target.** Get a local source checkout (clone if needed;
   prefer an existing clone under `~/projects/github.com/<org>/<repo>`) and,
   when a container distribution exists, the image ref. Record versions:
   git tag/commit and image tag@digest. **The verdict is version-specific**
   — pin what was actually vetted.
3. **Identify the deployment shape** (CLI, server, K8s chart/operator,
   desktop app). This decides which static checks apply (Helm image
   enumeration only for charts; browser-console check only for web UIs).
4. **Locate the docs' own air-gap story.** Search the repo/docs for pages
   titled "air-gap", "offline", "disconnected", "self-hosted". Their
   existence is a green flag (Q8) and their claims become hypotheses for
   the static pass to check — never conclusions.

---

## Phase 1: Static pass (always)

Work through Questions 1–7 in order. For each, record in working state:
`answer` (yes/no/partial/unknown), `evidence[]` (exact grep hit with
file:line, hostname, or doc URL), and `flags[]` (red/green signals for
grading). Every claim in the final report carries evidence — a verdict row
without a grep hit or citation is a guess, and guesses get `unknown`, not
`no`.

**Q1 — Telemetry.** Read `references/telemetry.md` §Fingerprints. Run BOTH
grep layers (SDK packages AND hostnames) over source and — if an image is
in scope — `strings` over its binaries, `docker inspect` ENV, entrypoint
scripts, and a CNAME check of the registry host (Scarf Gateway hides in the
*distribution channel*). One layer alone misses what the other catches.

**Q2 — Opt-out semantics.** Read `references/telemetry.md` §Opt-out. Grep
the candidate for kill-switch-shaped tokens (telemetry-adjacent substrings,
not an exact-name list) — the mere *presence* of opt-out handling is
evidence telemetry exists. Then check the
six pitfalls (opt-out-by-default, phones-home-before-opt-out,
value-vs-presence bugs, reduce-not-eliminate, separate update-check
channel, destination drift) against the code that actually reads the
variable. Verify polarity in source, not docs.

**Q3 — Proxy-in-disguise.** Read `references/downloads-and-proxy.md` §Proxy.
Repo topology, hardcoded base URLs, BYOK-routing docs, pricing-page
"self-hosted = Enterprise" tells, mandatory-login issues.

**Q4 — Runtime downloads.** Same file, §Downloads. Build-time vs runtime is
the organizing principle. For Helm charts, enumerate images from rendered
output (`helm template | grep -oE 'image: *"?[^"]+' | sort -u`), never
values.yaml alone. Runtime-computed image names are an automatic `no-go`.

**Q5 — Custom CA.** Read `references/ca-trust.md`. Identify the TLS stack
per ecosystem, check additive-vs-replacement semantics, and hunt the two
hard blockers (compiled-in `webpki-roots`, certificate pinning) plus the
anti-pattern of verification-off switches offered *instead of* a CA option.

**Q6 — Content egress & offline degradation.** Read
`references/content-egress.md`. Inventory features that send user content
(AI assist, gravatar, map tiles/GeoIP, link previews) with their kill
switches, plus CDN-loaded frontend assets. Also run the identity and
inbound sub-checks at the tail of that file. Output here is a per-feature
table: feature → destination → default on/off → kill switch → what's lost
offline.

**Q7 — Sustainment.** Read `references/sustainment.md`. How do upgrades and
content feeds (vuln DBs, rules, models) cross the gap, and what does the
product do when a feed is stale — fail-closed, warn, or silently report
green? Find the age-validation code (or its absence). Count the gap
crossings an upgrade path requires.

**Signature-verification and time sub-checks** (feed Q4/Q5/Q7): if the
product or its install path verifies signatures (cosign, Notation, GPG) or
carries an expiring license, read `references/verification-time.md` and run
its greps — provenance verification is itself a common hidden egress.

Static-pass greps run offline; only Phase 0 target resolution and optional
`gh` issue-searches need network. When vetting from inside a gap, skip the
`gh` checks and note them as not-run in the report.

---

## Gate: static → dynamic

Run the dynamic pass when **any** of:
- `--dynamic` was passed, or `--stakes high` and the candidate survived
  static;
- Q3 is unresolved (docs market "offline" but static found license-ping or
  activation endpoints) — the post-activation egress-deny test is the
  **mandated tie-breaker** between `possible-with-mirror` and
  `proxy-in-disguise`; do not guess this boundary statically;
- Q2 found opt-out flags whose actual behavior can't be confirmed in source
  (compiled binary, obfuscated build);
- Q5 hinges on runtime behavior (does the binary honor `HTTPS_PROXY` +
  custom CA?).

If the gate fires but `--dynamic` was not passed and stakes are `low`, emit
the static-only report with grade suffix `(provisional — dynamic pass not
run)` and list exactly which dynamic steps would settle which questions.

If stakes are `high` but the dynamic pass cannot run (no Docker, no
disposable host), do NOT emit a final grade — that is the whole point of
`high`. Report the static findings, set `grade_provisional: true` with the
grade left as the static best-guess, and state plainly that a final verdict
requires running the listed dynamic steps on a disposable host.

## Phase 2: Dynamic pass (gated)

Read `references/dynamic-harness.md` and run its ladder on a disposable
host/VM: (1) `--network=none` first-run, (2) iptables `DOCKER-USER`
deny+log with REJECT, (3) passive DNS/egress enumeration, (4) mitmproxy
with CA injection — this one test settles Q5 *and* inventories Q1
destinations, (5) post-activation egress-deny (the Q3 tie-breaker),
(6) browser-console check under deny for web UIs (Q6), (7) stale-feed run
for security tools (Q7), (8) `faketime` skew runs (+30 days, +13 months)
for time dependencies. Capture in two windows — first-run AND 10–30 min
steady-state; timer-based heartbeats don't show up in a 30-second capture.

---

## Phase 3: Grade (Question 8)

Assign exactly one grade. When evidence splits across grades, the worse
grade wins — the cost of over-promising air-gap readiness (a dead product
inside the gap) far exceeds the cost of extra mirroring work.

**air-gap-native** — complete published artifact enumeration (image list /
`relatedImages` / SBOM); digest-pinnable references; ONE global registry
override covering ALL images including init-containers and operator-pulled
ones; license validated locally via cryptographic signature with zero
callbacks ever; every outbound feature listed with a documented kill switch
or local-mirror path; custom-CA injection works; offline docs artifact;
installer completes with egress fully denied; content feeds published as
mirrorable artifacts (OCI/HTTPS) with override flags and **non-silent**
staleness handling; a published feature-degradation table.

**possible-with-mirror** — all artifacts enumerable and mirrorable
(possibly with effort); registry overrides exist but per-image rather than
global; offline license path exists but may be approval-gated; some
features degrade offline in a **documented** way; requires standing mirror
infrastructure and periodic content sync. Also the cap for: default-on
content-egress features that DO have a self-hosted path, and security feeds
that go silently stale (state the silent-stale warning explicitly in the
verdict).

**proxy-in-disguise** — vendor markets "offline/disconnected" but operation
requires allowlisted egress to specific endpoints: license-ping servers,
telemetry gateways, activation callbacks, update checks that gate
functionality, or login that requires the vendor's cloud with no offline
workaround. Works behind an HTTP proxy, dies behind a true gap. Decisive
objective test: does the product survive a permanent egress-deny applied
**after** activation? Note: air-gap sold only as a negotiated license tier
is a proxy-in-disguise trigger even when technically mirrorable.

**no-go** — hardcoded URLs with no override; image/artifact names computed
at runtime (defeats all mirroring); install scripts that fetch mid-run with
no offline flag; license enforcement that shuts the product down absent
connectivity with no offline tier; no way to enumerate what to mirror;
TLS certificate pinning or compiled-in-roots-only on endpoints that must be
mirrored.

---

## Phase 4: Output

### 4a. Write `./AIRGAP-VETTING.json`

```json
{
  "vetting_completed": true,
  "candidate": {
    "name": "...",
    "version": "git tag/commit and/or image@digest actually vetted",
    "source": "repo URL", "image": "ref or null",
    "deployment_shape": "cli|server|k8s-chart|k8s-operator|desktop"
  },
  "mode": "static-only|static+dynamic",
  "stakes": "low|high",
  "grade": "air-gap-native|possible-with-mirror|proxy-in-disguise|no-go",
  "grade_provisional": false,
  "questions": [
    {
      "id": 1,
      "question": "Sends telemetry to internet?",
      "answer": "yes|no|partial|unknown",
      "evidence": ["exact grep hit with file:line, hostname, or captured destination"],
      "flags": ["red: ...", "green: ..."],
      "kill_switches": ["ENV_VAR=value (polarity verified in source at file:line)"],
      "dynamic_confirmed": false
    }
  ],
  "egress_inventory": ["hostname — purpose — first-seen (static grep | dns capture | mitm)"],
  "mirror_list": ["everything that must cross the gap: images@digest, feeds, models, docs"],
  "sustainment": {
    "feeds": [{"feed": "...", "mechanism": "...", "staleness_behavior": "fail-closed|warn|silent"}],
    "upgrade_gap_crossings": "packages/artifacts per upgrade hop",
    "sync_cadence_required": "..."
  },
  "not_run": ["checks skipped and why"]
}
```

Every question appears exactly once, `unknown` answers stay `unknown`, and
`not_run` lists what a follow-up should do. Do not print this JSON to the
terminal; write to file only.

### 4b. Write `./AIRGAP-VETTING.md`

Reviewer-facing, in this order: title + one-line verdict; the grade with
its two or three decisive pieces of evidence; the eight-question table
(question | answer | strongest evidence); the per-feature content-egress
table (Q6); the mirror list; the sustainment summary; `Not run / next
steps`. Keep it under ~120 lines — the JSON carries the full detail.

### 4c. Append to the known-products log

Append one row to `./AIRGAP-KNOWN-PRODUCTS.md` in the working directory
(create with header if absent, same columns as
`references/known-products.md`). If the skill directory itself is writable
(in-repo development, not an installed plugin), ALSO append the row to
`references/known-products.md` so the skill compounds across runs.

### 4d. Terminal summary

Under ~10 lines: grade (+ provisional marker), the single most decisive
finding, count of red/green flags per question, where the reports were
written, and — if static-only — the one dynamic test most worth running.

---

## Maintenance

Smoke tests (expected grades for three known-products rows), design
rationale, composition with sibling skills, and provenance live in
`references/maintenance.md`. Re-verify the version-gated facts periodically
— cosign v2 vs v3 flags, DCT shutdown 2026-12-08, and the dated
known-products rows all drift.
