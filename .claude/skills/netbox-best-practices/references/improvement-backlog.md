# Improvement backlog — netbox-best-practices

## Resolved — 2026-09-15 (live build: 4.6.10 hop + Keycloak SSO on noffe)

The helm SSO design (§9 + `sso-hardening.md`) went from `[source]` to
`[live]` in one evening: chart 8.3.37/4.6.5 → 8.3.66/4.6.10, then Keycloak
26.7.2 login via the generic `OpenIdConnectAuth`, mounted pipeline module,
`readers` default group. What the build corrected or added:

- **§9.2 `/auth` claim was too strong.** A Keycloak that keeps the legacy
  prefix on purpose (operator `spec.hostname` with `/auth`) has
  `/auth/realms/<realm>` as its issuer; the rule is now "copy the discovery
  `issuer`", not "Quarkus has no `/auth`".
- **Fifth 4.7 gate.** 4.7.0 breaks the SSO login button (#23112) and its
  `pg_dump` loses cascade triggers (#23130); 4.7.1 fixes both, no chart pins
  it yet. Recorded in `SKILL.md` and `version-deltas.md`; 8.3.66 named as the
  last 4.6 chart.
- **Worked example** appended to `sso-hardening.md`: Keycloak client JSON +
  groups mapper, complete values, the smaller flags-only pipeline variant,
  the read-only-group script, and what the redirect/pod look like when right.
- **§9.1/9.3/9.5/9.6** gained the live mount paths, a compile + stub
  self-check for the module, the from-outside verification recipe, the
  "feed Django code on stdin" observation (`shell -c` output did not come
  back through `kubectl exec` on the 4.6.10 image), and the two-revision
  pattern (hop, then SSO).

- **`is_staff` does not exist on NetBox 4.x** — both the skill's original
  `map_groups` snippet and the first live module set it; the first real
  login 500ed with `ValueError: … non-concrete fields: is_staff`. Corrected
  in both examples; the stub self-check cannot catch this class of error.

Still open from this build: the first real IdP login by a human was pending
when this was written — the promote/demote path is stub-tested and the
redirect verified, not yet exercised with a live Keycloak session.

## Resolved — 2026-07-21 (freshen)

**The skill's own refresh trigger did not fire — and that is the finding.**
NetBox is still **4.6.x** (v4.6.5, 2026-07-14) and the chart is still **8.x**
(8.3.37, 2026-07-15). No new minor, no chart major, so every `version-deltas.md`
claim and the v1-token-removal-at-**v5.0** schedule stand unchanged.

- **Version-lookup trap documented.** `netbox-community/netbox-chart` publishes
  **two products into one release stream** — `netbox-<chart>` and
  `netbox-operator-<chart>`. As of 2026-07-21 `isLatest` is
  **`netbox-operator-1.2.128`**, so `gh release view -R
  netbox-community/netbox-chart` returns an *operator* version, not a chart
  version. Recorded the Helm-index query as the correct lookup, since it
  separates the two entries and carries `appVersion`.
  (Fourth distinct shape of this failure found in one freshen run — after
  date-ranked `latest`, RC tags flagged non-prerelease, and parallel-minor
  patching. "How do I find the newest version" is a per-repo question.)
- **`[live]` labels re-scoped, not re-stamped.** They were verified once on
  chart 8.3.14 / v4.6.2 (2026-06-12) and have **not** been re-run; upstream has
  since moved 23 chart patches and 3 NetBox patches. The header now reads
  "observed on 4.6.2" rather than leaving currency implied. Re-running them
  needs the production install, not a public probe — deliberately not faked.
- **Pinned versions annotated** in `SKILL.md`, `helm-chart-gotchas.md` and
  `sources.md` with the upstream delta plus the explicit "no delta invalidated"
  conclusion, so a future reader can tell *checked-and-unchanged* from
  *not-checked*.


## Open

- **NetBox 4.7.0 is outside the covered range** (Dim 9, new 2026-09-15). The skill
  states 4.2–4.6 and its deltas stop there; 4.7.0 published 2026-09-02, verified
  against the release feed. SKILL.md now says so rather than implying 4.6.x is still
  the head of the line, but the version-delta sheet, the chart pairing and the
  source-verified auth claims have not been re-read against 4.7.
  **What it needs:** a freshen pass over the 4.7 release notes and the chart's 4.7
  pairing — the work is real research, not a range edit, and writing "4.2–4.7" without
  it would claim coverage that does not exist.


- **HA/replicas/media-persistence coverage** (Dim 5) — netbox-chart replicas >1
  requires RWX media storage (or S3-style media backend); chart issues track
  upgrade-path and securityContext recurrences. Needs researched, verified
  content (chart issues sweep + a live multi-replica test) — not a
  single-iteration mutation. Source candidates: netbox-community/netbox-chart
  issues; deep-research run 2026-06-12 flagged this as its open question.
- **No eval set → Dim 10 capped at 8** (Negative-Transfer Gate). Both blind
  passes on 2026-08-20 named this as the only route past the cap. Blocked on a
  measurement, not on writing: needs `evals/evals.json` plus a with/without
  `benchmark.json` producing a real `delta_pass_rate`. Note `knowledge-claims.json`
  does NOT qualify — it is claim extraction, not a KNOWS/UNKNOWN/CONFLICTS floor
  probe.

## Resolved this pass — 2026-08-20

- **`when_to_use` field split** (Dim 1 + Dim 9) — RESOLVED. The June note called
  this "cosmetic today, do it next description edit" at 866 chars. It stopped
  being cosmetic: `description` had drifted to **1,070 chars, past the 1,024
  spec hard max**, hard-capping Dim 9 at 3. Split into `description` 654 +
  `when_to_use` 351 (combined 1,005, inside the 1,536 listing cap). Self Dim 9
  3→9, Dim 1 6→8. Both blind scorers independently named this the single
  highest-impact fix, each having measured the length with
  `skill-improver/scripts/frontmatter-lengths.py` rather than estimating it.
  Lesson worth carrying: a "cosmetic" frontmatter item can silently cross a
  hard cap as the field grows — it is worth re-measuring, not re-reading.
- **Intro said "three areas" and listed four** (Dim 8 8→9). Kept under the
  noise-zone rule: a bare +1 with no simplification, re-checked cold on the
  affected dimension, where it reproduced.
- **Second-person prose in references** (Dim 3, the final blind's lowest at 7
  and its own recommended next fix) — 21 instances across `sso-hardening.md`
  (12) and `helm-chart-gotchas.md` (9) converted to imperative. Now 0 in both.
- **PKCE-off-by-default duplicated near-verbatim** (Dim 6) across
  `helm-chart-gotchas.md` and `sso-hardening.md` — merged to one source of
  truth in `sso-hardening.md`, with the helm file carrying the two settings a
  chart operator needs plus a pointer. helm-chart-gotchas.md 400 → 394 lines.
- **`[live]` labels pinned to chart 8.3.14 / NetBox v4.6.2** while upstream is
  chart 8.3.57 / v4.6.8 — NOT resolved, and NOT filed as a blocker either: it
  is a `freshen` job, which is a different mode with its own evidence
  requirement, and `sources.md` already flags it as the next freshen target.

**Pass record (2026-08-20, commit d7da2e5).** 2 iterations, 2 keeps, 0
discards. Self 73 → 83 cold; blind 78 → 86. Anomaly gate fired on iteration 1
(+8 ≥ +5): cold rescore of all ten dims gave 83 against delta-math 82, inside
the 2-point tolerance, so the delta stood. Scorer was Sonnet 5 (pinned in the
`blind-scorer` agent frontmatter as of 2026-08-20). **Stopped on operator
scope, not on a rubric stop condition** — no ceiling was mapped and zero
discards were logged, so this pass has NOT established that the skill is near
its ceiling.

## Resolved this pass — 2026-06-12## Resolved this pass — 2026-06-12

- sources.md created, all rows stamped 2026-06-12 (Dim 9 cap 6 → 9).
- Token section deduplicated against official netbox-labs:netbox-api-integration,
  then made runnable again per final blind feedback (curl + credential assembly).
- Overbroad description catch-all ("any NetBox deployment/bootstrap/CI
  question") narrowed.
- Second-person occurrences → 0; ToC added to helm-chart-gotchas.md.
- Cross-skill deferral given an internal fallback (version-deltas.md §4.5).
- Scores: self baseline 78 → blind baseline 83 → blind final **91/100**
  (no self-vs-blind dimension gap ≥2 at baseline; final issues all addressed
  or backlogged).
