# Improvement backlog — traefik-hardening

## Open

- **Dim 1 — full trigger set won't fit the 1,536-char listing cutoff.** Combined `description`+`when_to_use` = ~1,934 chars. After the iter-11 reorder, the core positives + symptoms + the "Do NOT" guard land within 1,536, but the JA3/air-gap trigger *phrases* and the "choose where to cap" clause sit past it (their concepts are covered in `description`, which is fully within cutoff). iter-7 proved a trim-to-fit stays over 1,536 (1,564) while deleting symptom+intent coverage — net negative. Closing fully needs an author decision on which trigger phrases to sacrifice vs. accept tail-truncation. File: `SKILL.md:6`.
- **Dim 6 — single-leader / fan-out topology caveat repeats across 4 files.** Appears in `SKILL.md` (decision-flow step 4 + quick-map), `references/middleware-primitives.md` (InFlightReq), `references/deployment.md` (counting-trap section), and `references/known-products/open-webui-api-abuse.md`. Partly intentional (each file needs the caveat in its own context), but a canonical treatment in `deployment.md` + one-line pointers elsewhere would cut ~15 lines. Multi-file restructure; author call on whether the reinforcement earns its place.
- **Dim 9 — JWT plugin version/config left as `v<latest>` placeholder.** `references/identity-keying.md:27` intentionally does not pin a version (operator picks the plugin and pins at install). Making it concrete would require an online probe of the plugin's Releases (freshen-style), not a score-loop mutation — and hardcoding a number risks staleness. Run `freshen` if a pinned reference example is wanted.

## Resolved — 2026-09-15 (freshen to v3.7.13)

- **The skill was 16 security advisories behind, two of them critical.** Traefik
  published **30 advisories in 2026**, and 16 of those landed after this skill's
  2026-07-22 verification date. The two criticals are **GHSA-5w68-77r2-r64c**,
  a *complete authentication bypass in the `digestAuth` middleware*
  (2026-08-21), and **GHSA-qqjf-53cj-pwvv**, HTTP/3 backend NTLM connection
  reuse (2026-09-07). A new "patch first, tune second" section leads the skill,
  because several of this year's advisories are auth bypasses **in the very
  middlewares this skill configures** — tuning an unpatched build is wasted
  effort. The recurring classes are named: path normalization defeating
  route-scoped auth, TLS-option confusion bypassing mTLS, and Kubernetes
  cross-namespace reference checks failing open.
- **`aliasHeadersStrategy` (v3.7.12) is now documented as a control, not a
  default.** It deprecates `underscoreHeadersStrategy`, and the widening matters:
  underscores were one case, but HTTP permits thirteen other characters that can
  each alias a header a middleware trusts. That is the mechanism behind the
  ForwardAuth dot-form and BasicAuth/DigestAuth underscore spoofing advisories.
  Traefik logs a startup warning for every entry point that leaves it unset.
- **Two v3.7.13 breaking changes recorded**: `Upgrade: h2c` / `HTTP2-Settings`
  headers are no longer forwarded, and a rootless request target is rejected
  with 400 with no configuration option.

### Checked and found CORRECT — do not "fix" these

- **Redis-backed `RateLimit` at v3.4+ is real and open-source.** A doc-page
  fetch returned an empty shell and appeared to show zero Redis mentions, which
  would have suggested the feature was commercial-only. The source settles it:
  `pkg/middlewares/ratelimiter/redis_limiter.go` is present at tag **v3.4.0** and
  absent at **v3.3.0**, so the skill's version gate is exactly right. The
  near-miss is the lesson — an empty fetch is not evidence of absence.
- **`RateLimit` and `InFlightReq` remain per-instance in open-source Traefik.**
  The skill's single-leader-versus-fan-out caveat still holds; nothing in the
  2026-07-01 onward window changed it. Traefik Hub's "Distributed RateLimit" is
  a separate commercial middleware and is now called out by name so the two do
  not get conflated.

## Resolved this pass — 2026-07-22 (baseline 75/76 → 88)

- Dim 9 hard-fail: `description` was 1,671 chars (> 1,024 spec cap) → rebalanced to 842, triggers moved to `when_to_use` (iter 1).
- Dim 9 staleness: added `references/sources.md` with per-row `Last verified: 2026-07-22` stamps → cap lifted (iter 2).
- Dim 3: eliminated all second-person across SKILL.md + references, including 2 capitalized "You" a case-sensitive grep missed (iters 3, 4, 10).
- Dim 6: de-duplicated the period-default / streaming / per-pod gotchas (already in the quick-map) so Load-bearing = cross-cutting traps only (iter 5).
- Dim 4: added a "Verify the limits actually fire" section (curl concurrency/rate probes, fairness + false-positive checks, the 429-metric alert) — the skill previously had no validation step (iter 9).
- Dim 1: split description/when_to_use and reordered so symptoms + the "Do NOT" negative guard fall within the 1,536 listing cutoff (iters 1, 11).
- Discards (ceiling-mapping): iter 7 (trim when_to_use to fit 1,536 — stays over while losing coverage); iter 8 (remove "How to use" section — carried a unique product-quarantine instruction, wash/loss).
