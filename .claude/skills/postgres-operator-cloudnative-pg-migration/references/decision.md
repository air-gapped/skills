# Stay vs migrate: the evidence

Dated snapshot, verified 2026-07-24 from both repos at HEAD plus primary
statements. Use this to ground a recommendation; re-verify the volatile
rows (release dates, CNCF status) before quoting in a later year.

## Momentum (last 12 months, human/non-bot commits)

| Metric | Zalando postgres-operator | CloudNativePG |
|---|---|---|
| Human commits | 89 | 626 |
| Unique authors | 29 | 81 |
| Sustained (full-time-pace) contributors | 1 (Felix Kunde, 35% of commits) | 7 (all EDB) |
| Releases 2025 / 2026 YTD | 2 / **0** | ~monthly patch trains, 3 concurrent minors |
| Latest release | v1.15.1 (2025-12-18) | 1.30.0 + 1.29.2 + 1.28.4 (2026-06-29) |
| New issues opened 2026 YTD | 21 | 516 |
| Go LOC / test LOC | 40k / 15k | 205k / 97k |

Zalando human commits by year: 174 (2020) → 37 (2025) → 66 (2026 YTD —
a real rebound: PG18 prep, IRSA, informer refactor, but still no 2026
release; the "Q1 2026" PG18/Spilo-18 release is ~2 quarters late).
CNPG has held ~550–650 human commits/yr for five straight years. Note
CNPG's raw GitHub graphs are ~32–36% renovate-bot — the human-only gap
is still ~7×.

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
- Trust event: v1.15.0 (2025-10-21) shipped missing UI + logical-backup
  images; the fix (1.15.1) took ~2 months. At least one documented
  migration cites this as the trigger.

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

1. **Zalando is maintenance-mode, not dead.** Internal production use
   guarantees a maintenance floor; PG18 support is landing; the
   K8s-1.33 Endpoints deprecation is already addressed
   (`kubernetes_use_configmaps`). Staying is viable through ~2027.
2. **CNPG churn tax.** Each minor is supported only ~3 months past N+1
   (≈6-month life) → 2–4 operator upgrades/yr forever, and each operator
   upgrade by default **rolling-restarts every managed cluster**
   (instance-manager binary replacement; in-place update exists but is
   off by default and "breaks immutability"). Zalando asked ~1/yr.
3. **Plugin transition in flight.** In-tree Barman backup deprecated
   since 1.26; removal slipped 1.28→1.29→1.30→1.31. The plugin is
   pre-1.0 and already caused a silent backup-metrics regression
   (#8902). Conservative teams may prefer landing after 1.31 ships.
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
| Stay on Zalando + wait | Legitimate through ~2027. The gap widens; revisit at each k8s-components-checker survey. |

## Recommendation shape

Migrate deliberately: pilot on a low-stakes cluster, land the fleet over
quarters, keep the Zalando stack resurrectable until backup retention
expires (see backup-chain.md). No forcing event exists today; the case
is ecosystem trajectory, PG-version cadence, declarative surface, and
hiring familiarity.
