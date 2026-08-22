# Scripts

Every executable in `scripts/`, what it measures, and the failure it exists
to prevent. SKILL.md links here rather than inlining the catalogue — the
same progressive disclosure this skill's Pattern 2.1 prescribes, applied to
itself after the pre-commit gate flagged SKILL.md at 10,051 tokens against
the 5,000 guidance.

- **`scripts/scan-skills.sh`** — Find all SKILL.md files in profile and project scopes. Outputs paths sorted by modification time.
- **`scripts/dedup-fleet.py`** — Fleet driver for intra-skill dedup, and the
  measurement behind Pattern 6.1. Runs `context-optimization-check` per skill,
  writing each result as it lands so a killed pass keeps what finished, and
  ranks skills by **duplicate share**, not count — 1 duplicate among 22 clusters
  is noise, 4 among 7 is structural, and sorting by count buries the second
  behind large skills that are mostly fine. Shares over fewer than 5 clusters
  print `n/a` rather than a number, because 1-of-2 is two clusters, not "50%
  duplicated". It also names **name families with repetition in 3+ members** —
  measured `vllm-*` at 13 skills and 29 duplicate clusters, a third of all
  duplication in the fleet, which is shared material to fix once rather than
  thirteen separate jobs. Results
  cache in `${XDG_CACHE_HOME:-~/.cache}/skillevaluator/dedup/`, never in the
  repo, keyed by the skill's content hash **and** the chat model, embedding
  model and endpoint that produced the verdicts: a verdict is only valid for
  the pipeline that made it, and the same `bge-m3` scores differently across
  gateways. Unchanged skills are skipped (a 68-skill re-report is 0.07s against
  7m19s cold). Skills over the tool's pairwise-work budget (~221 chunks at 1024 dims) are
  reported SKIPPED
  with the reason rather than failing. An unmatched cache exits 2 saying nothing
  was measured, rather than printing a clean fleet. Config via `--env-file`;
  needs both provider roles.
- **`scripts/eval-evidence.py`** — The blind scorer's only channel into a
  target's `evals/`. That directory is not neutral input: it accumulates prior
  blind totals, kept/discarded records, and regression verdicts, so reading it
  un-blinds the pass exactly as `improvement-backlog.md` does. But it cannot be
  excluded outright — the Negative-Transfer Gate needs `delta_pass_rate` out of
  it. This prints the case count, every `delta_*` measurement with its source
  path, and the Dim 10 cap they imply, and nothing else. The delta is **derived**
  from the `with_skill`/`without_skill` arms, never read from the stored
  `delta.pass_rate` — which the official aggregator writes as a 2-decimal string,
  orders by dict insertion, and defaults a missing arm to 0 — turning an
  absent baseline into a maximally positive result. A missing arm now
  yields no delta at all rather than a flattering one.
- **`scripts/overlap-scan.py`** — Fleet-wide overlap measurement, and the
  empirical input Dim 10 has been missing. Embeds every skill twice via
  SkillEvaluator Tier 2 — `name: description` alone, then the whole SKILL.md —
  because the two answer different questions: description similarity means the
  skills compete for the same **queries** (a trigger problem), body similarity
  means they may duplicate **material** (a Dim 10 problem). The cross-tab of the
  two is the output. **Rank, do not threshold**: upstream's 0.95/0.90/0.75 bands
  come from another model and corpus, and measured here on 68 skills with bge-m3
  the *median* body pair scored 0.789 — above `SIMILAR` — so a
  `--full-body --threshold 0.75` run aborts on the 1000-match cap. It saves
  vectors once and scores locally as z-scores against the fleet's own
  distribution. A lexical-overlap column guards the known artifact: pooling a
  long document measures *register* as much as subject (measured
  `corr(body, lexical) = 0.515`), so two unrelated 400-line operator guides
  score high for both being 400-line operator guides. Endpoint config is env-only
  (`--env-file`); no host is hardcoded and none should be added. `--from-catalogs`
  re-scores offline with no API calls.
- **Deterministic safety gate — use NVIDIA's own command, not a wrapper.**
  SkillEvaluator is designed as a merge gate
  ([ci-integration](https://docs.nvidia.com/skills/skillevaluator/ci-integration)),
  and its `--policy` overlay is the intended way to say "this finding does not
  apply to us" — declaratively, reviewed like code:

  ```bash
  skillevaluator validate <skills-dir> --type skill --external \
    --policy .claude/skillevaluator-policy.yaml --no-dedup -c
  ```

  Catches what no rubric dimension can: a tag-block smuggling payload is
  CRITICAL and the report decodes it verbatim, while the text renders as
  nothing in an editor. Also leaked home paths, and schema breaks that stop a
  skill loading. Needs the binary and its scanners, no API key —
  [installation](https://docs.nvidia.com/skills/skillevaluator/installation).
  One skill ~0.3s, 68 skills ~4m40s, which is why the pre-commit hook
  (`scripts/skillevaluator-gate.sh`) scopes to staged skills. An earlier
  `tier1-sweep.py` reimplemented the severity filtering in Python before this
  path was understood; the policy file replaced it.
- **`scripts/frontmatter-lengths.py`** — Exact `name` / `description` /
  `when_to_use` character counts for one SKILL.md, the combined total against
  the 1,536-char listing cap, and any `description` breach of the 1,024-char
  hard max. The blind scorer calls this for Dim 1 and Dim 9 instead of
  estimating: a scorer was measured reporting 1,120 chars for an 847-char field
  and hard-failing Dim 9 to 3 on the invented number (2026-08-20).
- **`scripts/staleness-report.py`** — Fleet-wide staleness readout, no probes/network: per skill, the `sources.md` `Freshened:` header stamp (or, on legacy files, the oldest per-row `Last verified:` date), its age, dated-row coverage, the Dim 9 staleness cap it implies, last improvement-pass date (from `improvement-backlog.md`), whether trigger/outcome evals exist, and the count of items still under that backlog's `## Open` heading (fleet total in the footer). Stalest first — this is the ranking `freshen --all` uses. `--json` for machine output.
- **`scripts/read-x-post.py`** — Reads an `x.com` / `twitter.com` post as text for a freshen probe. `WebFetch` returns `402` on every X URL because it identifies as `Claude-User`; bare `curl` is served the real page, so an X row is verifiable rather than an exception note. Handles the two truncations that make a naive tag-strip return a partial post that reads as complete: `og:description` is capped at 278 chars, and long posts render 278 chars plus a `Show more` button while shipping the full text in a `<script>` payload as `__typename:"NoteTweet"`. Prints `[notes | expanded | unexpanded]` to stderr — a non-zero `unexpanded` is the signal to escalate that row to the browser. Profile URLs work too, returning the ~7 most recent posts. See freshen-patterns §2.4.
- **`scripts/batch-workflow.js`** — Reusable `Workflow`-tool driver for batch improve + freshen (recon → apply → blind pipeline, median-of-3 final blind). Skill list comes from `args`. Invoke with `Workflow({scriptPath: "${CLAUDE_SKILL_DIR}/scripts/batch-workflow.js", args: [...]})`. See Batch Mode § Dynamic workflows.
- **`scripts/scaffold-probe.py`** — classifies each numbered item as scaffold, criterion, or branch. **Advisory only — it sets no score.** The step-count cap it once fed was withdrawn 2026-08-20: no source states a numeric threshold, Anthropic's degrees-of-freedom guidance recommends explicit steps for fragile or order-dependent work, and SkillLens measured surface format as non-predictive (p > 0.34). Use it to find candidate bloat, then judge fit (quality-rubric §"Procedural steps").
- **`scripts/induced-cost-probe.py`** — what the skill costs to *obey*, which no text dimension measures: pinned effort over cheap modes, unconditional read-everything, uncapped fan-out, over-obedience phrasing. `--refs` to include references, `--selftest` to check the patterns still separate mention from use. Caps Dim 6 at 6 (quality-rubric §"Induced cost").
- **`scripts/floor-fleet.py`** — Fleet driver for Floor Mode. Walks every SKILL.md under a root, runs `knowledge-floor.py` per skill, and writes each result the moment it lands so a multi-hour pass is resumable (`--redo` to force). `--report` re-prints the leaderboard without probing; `--merge <dir,...>` folds a later pass over the same claim sets (e.g. adding a cheaper tier) into one table, columns ordered weakest-to-strongest. Ranks by the share of claims the strongest probed model already knows.
- **`scripts/knowledge-floor.py`** — Floor-mode probe. Extracts checkable factual claims from a skill (cached to `<skill>/references/knowledge-claims.json`), then asks a **bare** `claude -p` — empty project so no skills resolve, every tool denied so the answer is parametric recall — and buckets each answer KNOWS / UNKNOWN / CONFLICTS against the skill's own claim. `--models`/`--efforts` sweep the matrix; each invocation reports its own `total_cost_usd`. See Floor Mode.
- **`scripts/run-cost.py`** — Token and cost accounting for a session, read from its transcript. The agent cannot see its own spend at runtime; the harness records every call's `usage`, so cost is recoverable after the fact. Deduplicates on `requestId` (one request writes one record per content block — summing records overcounts 2x+) and reads `<session>/subagents/agent-*.jsonl` so blind scorers and probe fleets are costed by `agentType` and task. `--json` for machine output, `--list` to enumerate sessions, `--since` to scope to one phase. Also derives **timing** from transcript timestamps — per-model p50 latency and output tokens/sec, plus in-model time against wall time, whose ratio is the effective concurrency a fan-out actually achieved. Throughput runs inverse to capability (haiku 70.7 tok/s → fable 30.2), so this is the column that prices a stronger model in seconds rather than dollars. Rates live in **`scripts/model-rates.json`** (dated; refreshed from the `Model pricing` row in `sources.md`). List API rates — read the dollars as relative sizing between runs, not as an invoice.
#### Eval-corpus maintenance (fleet-wide, not per-run)

These four operate on the *fleet's* `evals/` and floor results rather than on
one skill in one pass. Reach for them when the corpus itself is the problem —
a `delta_pass_rate` that cannot resolve a change, or graded output that is not
trustworthy — not during a normal `improve` or `freshen` run.

- **`scripts/normalize-evals.py`** — Collapses every skill's `evals.json` onto one schema and stamps provenance. An audit found 26 eval files carrying 11 distinct shapes and no record of what wrote them or when; 15 predated the current model by four generations. A stale eval set **defends the stale skill** — a case expecting a reminder an older model needed fails when that reminder is correctly deleted.
- **`scripts/backfill-assertions.py`** — Writes discrete outcome assertions for cases graded only against a prose `expected_output`, which is the subjective text comparison SkillLens measured at 46.4% (worse than chance). Enforces outcome assertions over text-recall ones ("expert parallelism is set correctly for a 2-node MoE deployment", not "mentions `--enable-expert-parallel`").
- **`scripts/grow-evals.py`** — Adds cases until a skill has enough to resolve a change. At the corpus median of 3 cases, one flip moves pass rate 33 points, so `delta_pass_rate` cannot separate "this edit hurt" from "one case is flaky". Floor of 8 (one flip = 12.5 points). New cases are generated to complement the existing prompts, not repeat them.
- **`scripts/regrade.py`** — Re-buckets stored floor-mode answers with a stricter grader, no re-probing. The first fleet pass inflated `CONFLICTS` by dumping agree-with-different-detail and hedged answers into it — the one bucket that can least afford noise, since overriding a confident wrong prior is the whole point of Floor Mode.

- **`scripts/bucket-evals.py`** — Labels every trigger-eval query by bucket and
  reports the fleet's balance. A true/false corpus says whether a query should
  fire, not what KIND it is, and the kinds fail differently: a description tuned
  on explicit phrasings passes by keyword match while missing every implicit or
  mid-task one, and an aggregate rate reads identically either way. Negatives are
  definitional; the three positive buckets are classified by the configured chat
  model, one batched call per skill. Measured on 14 corpora / 220 queries:
  `contextual` **9% against a 20% target, four corpora at zero**, negatives 45%.
  Fails closed — a labelling run that leaves anything UNLABELLED exits 1 rather
  than reporting shares over a partial corpus.
- **`scripts/probe-trigger.py`** — Trigger-mode measurement tool. Adapted from anthropics/skills `skill-creator/scripts/run_eval.py`. Spawns `claude -p` subprocesses against a synthetic slash-command and parses stream-json for `Skill`/`Read` `tool_use` events to compute per-query trigger rate. Supports stratified train/test split, configurable runs-per-query, threshold, and parallelism.
