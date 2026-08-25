# Stay vs migrate: the evidence

Dated snapshot, verified 2026-07-24 from both repos at HEAD plus primary
statements; release-state rows re-verified 2026-07-29 (Zalando v2.0.0/
v2.0.1 landed 2026-07-27/29) and again 2026-08-25 (Zalando v2.0.2;
release-defect record; CNPG release cadence). Use this to ground a
recommendation; re-verify the volatile rows (release dates, CNCF status)
before quoting in a later year.

## Momentum (last 12 months, human/non-bot commits)

| Metric | Zalando postgres-operator | CloudNativePG |
|---|---|---|
| Human commits | 89 | 626 |
| Unique authors | 29 | 81 |
| Sustained (full-time-pace) contributors | 1 (Felix Kunde, 35% of commits) | 7 (all EDB) |
| Releases 2025 / 2026 YTD | 2 / 2 (v2.0.0 + v2.0.1, both 2026-07) | ~monthly patch trains, 3 concurrent minors |
| Latest release | v2.0.2 (2026-08-20) | 1.30.0 + 1.29.2 + 1.28.4 (2026-06-29) |
| New issues opened 2026 YTD | 21 | 516 |
| Go LOC / test LOC | 40k / 15k | 205k / 97k |

Zalando human commits by year: 174 (2020) → 37 (2025) → 66+ (2026 YTD —
a real rebound that delivered **v2.0.0 (2026-07-27)**: PG18 support,
PG13 dropped, `kubernetes_use_configmaps` default-on, scram-sha-256
default, IRSA, informer refactor. The "Q1 2026" PG18 release landed ~2
quarters late, as a major).
CNPG has held ~550–650 human commits/yr for five straight years. Note
CNPG's raw GitHub graphs are ~32–36% renovate-bot — the human-only gap
is still ~7×.

CNPG cadence check, 2026-08-25: the 1.30.0/1.29.2/1.28.4 train is ~8
weeks old against a historical 5–7 week interval (2026-02-05, 04-01,
05-08, 06-29). Development is plainly alive — ~30 commits in the last 30
days, most recent 2026-08-24. Read that as a release gap at the edge of
normal, not a slowdown signal; re-check before quoting a cadence.

## On-the-record statements

- Zalando maintainer FxKu (issue #2921, 2025-06-12): project "in a
  little idle state… modernizing them was not encouraged by the
  management because 'it works'… we still use Spilo and the Postgres
  Operator in production, so we will keep maintaining them to e.g.
  support new Postgres versions." Team manages "1000s of database
  clusters". Patroni is "the most important asset anyway".
- Spilo maintainer (zalando/spilo#1131, June 2025): alive "for the time
  being"; Zalando runs an internal Spilo fork; last GitHub Release
  March 2023 (newer Spilo exists as image tags only, e.g. 4.1-p1
  2026-02).
- **Release-testing gap: three consecutive releases shipped with a defect
  a user hits immediately** (verified 2026-08-25):

  | release | defect | time to fix |
  |---|---|---|
  | v1.15.0 (2025-10-21) | published without UI and logical-backup images | ~2 months (v1.15.1) |
  | v2.0.0 (2026-07-27) | generated CRD rejected by the apiserver; operator fatals on startup | 2 days (v2.0.1) |
  | v2.0.1 (2026-07-29) | its own new `scram-sha-256` default triggers an infinite per-sync `ALTER ROLE` loop (#3170) | 3 weeks (v2.0.2) |

  At least one documented migration cites v1.15.0 as its trigger. Do not
  read v2.0.0 -> v2.0.1's two-day turnaround as reassurance on its own:
  **the fast fix shipped another defect**, and that one was self-inflicted —
  the release changed a default to `scram-sha-256` without the code path
  that makes scram idempotent. Three for three is a release-testing gap,
  not bad luck.

  **Counterweight — do not overread it.** Every one of these is an
  *upgrade-path* defect; none touches steady state, and fleets run for
  years on v1.14.0 without incident. With no forcing function (no
  Endpoints removal is planned — see the sibling skill
  `postgres-operator-best-practices`), the rational response to "the
  upgrade path is rough" is at minimum "do not upgrade right now", which
  is not the same as "migrate operators".

## CNPG standing

- CNCF Sandbox 2025-01-15; Incubation application cncf/toc#1961 filed
  2025-11-12, still open (watch for maintainer-diversity conditions —
  all 5 maintainers are EDB employees; governance is vendor-neutral on
  paper only, so far).
- 9,029 stars vs Zalando 5,208 (crossed during 2024–25); 132M+ image
  pulls; KubeCon NA 2025 + EU 2026 talks (incl. GEICO); IBM Instana
  replaced its embedded Zalando operator with CNPG and publishes an
  official migration runbook; pgEdge integrates with CNPG.
- 2023 Timescale survey: CNPG 27.6% (1st), Zalando 7.9%. Caveat:
  EDB-published; no neutral 2025/26 survey exists.

## The skeptic's case (why NOT to rush)

1. **Zalando is maintenance-mode, not dead — and v2 proves the floor
   holds.** Internal production use guarantees maintenance; v2.0.0
   (2026-07-27) delivered PG18 support (PG14–18 bundled) and flipped
   `kubernetes_use_configmaps` on by default, closing the K8s-1.33
   Endpoints deprecation without operator action. Staying is viable
   well past the previously-estimated ~2027 horizon. Note v2 breaking
   changes for stayers: PG13 dropped, scram-sha-256 default (forces a
   rolling update), kubectl-pg plugin dropped, deprecated manifest
   fields removed (`useLoadBalancer`, `replicaLoadBalancer`,
   `init_containers`). **Deploy v2.0.2, not v2.0.0 or v2.0.1 — both are
   defective** (see the release-testing row above); the v2 upgrade is a
   staged operation, not a chart bump. Sibling skill
   `postgres-operator-best-practices` carries the path.
2. **CNPG churn tax.** Each minor is supported only ~3 months past N+1
   (≈6-month life) → 2–4 operator upgrades/yr forever, and each operator
   upgrade by default **rolling-restarts every managed cluster**
   (instance-manager binary replacement; in-place update exists but is
   off by default and "breaks immutability"). Zalando asked ~1/yr.
3. **Plugin transition in flight.** In-tree Barman backup deprecated
   since 1.26; removal slipped 1.28→1.29→1.30→1.31. The plugin is
   pre-1.0 and already caused a silent backup-metrics regression
   (#8902). Conservative teams may prefer landing after 1.31 ships —
   **note that condition is still unmet as of 2026-08-25: latest is
   1.30.0 and 1.31 is unreleased**, so "wait for 1.31" is currently a
   wait of unknown length, not a scheduled one.
4. **Feature losses.** Teams API / OAuth credential automation,
   credential rotation, operator UI, preparedDatabases automation,
   arbitrary sidecars, logical-backup cron, upgrade maintenance windows.
5. **HA semantics.** Patroni's failsafe is strictly more conservative
   under partial partition (see pitfalls.md §HA). Mitigated but not
   eliminated by CNPG 1.27/1.28/1.30 work.
6. Practitioner sentiment was still split as late as Aug 2025 (one org
   chose Zalando over CNPG for perceived stability; others "wish we had
   switched earlier").

## Alternatives (assessed and set aside)

| Option | Verdict |
|---|---|
| Crunchy PGO | Active, Apache-2.0 code — but production images gated behind Crunchy's Developer Program terms; documented pull-revocation incident (#3601). Supply-chain risk for community users. |
| StackGres | Active, feature-rich, AGPL, ~1.4k stars — viable but small community. |
| Percona PG Operator | v3.0 (May 2026), fully-open images, optional paid support — cleanest commercial-backed alternative, smaller ecosystem than CNPG. |
| EDB Postgres for Kubernetes | Commercial CNPG with longer support windows — escape hatch if the 6-month community window is the only blocker. |
| Stay on Zalando + wait | Legitimate — v2 (2026-07) reset the release clock and covers PG14–18. The momentum gap still widens; revisit at each k8s-components-checker survey. |

## Recommendation shape

Migrate deliberately: pilot on a low-stakes cluster, land the fleet over
quarters, keep the Zalando stack resurrectable until backup retention
expires (see backup-chain.md). No forcing event exists today; the case
is ecosystem trajectory, PG-version cadence, declarative surface, and
hiring familiarity.
