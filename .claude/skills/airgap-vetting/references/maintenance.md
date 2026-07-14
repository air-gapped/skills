# airgap-vetting — maintenance & provenance

Maintainer-facing notes kept off the invocation path. Not needed to run a
vet. Settled decisions (do-not-re-propose) live in
`references/improvement-backlog.md`.

## Testing this skill

Smoke test against known-products rows with expected outcomes:
- `meilisearch` (static-only) → transit-domain telemetry + verified opt-out
  → `possible-with-mirror`.
- `langsmith` → `*-sdk`-only repo topology → `proxy-in-disguise`.
- `coder` → local signed license, zero callbacks → `air-gap-native`.

## Design notes

- **Two passes, explicit gate** — static is cheap and catches most
  disqualifiers; dynamic is ground truth for what static cannot settle.
  Never present a static-only vet as final at high stakes.
- **Bundled data over live lookups** — the reference tables make the
  static pass air-gap-complete; verify every hit against the candidate's
  current source before citing it.
- **Product-agnostic pattern files** — mechanisms and pitfall classes
  only; product findings live solely in `known-products.md` (dated,
  expected to drift). Pattern knowledge ages slowly; product examples
  multiply freshen cost.
- **Freshen targets** — cosign v2→v3 verify flags, DCT shutdown
  2026-12-08, dated `known-products.md` rows.
- **Composition** — this is the "should we even adopt this?" front-end,
  upstream of pipeline-hardening, version-compat checking, and vuln
  review. Output follows the repo's `*.json` + `*.md` report convention.

## Provenance

Distilled from a two-round multi-agent research pass (2026-07-14, ~150
primary sources); every hostname, env var, flag, and issue number traces
to the dated per-URL index in `references/sources.md`.
