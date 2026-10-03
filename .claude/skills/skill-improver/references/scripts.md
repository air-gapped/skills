# Scripts

Every executable in `scripts/`. Pick by the "when" column; `Read` a script's docstring for flags.

## Per-run and fleet tools

| Script | What it does | When | Reading output / caveat |
|---|---|---|---|
| `scan-skills.sh` | Finds all SKILL.md in profile and project scopes | Locate skills | Paths sorted by modification time |
| `staleness-report.py` | No-probe fleet readout per skill: `sources.md` `Freshened:` stamp (legacy: oldest row `Last verified:`), age, dated-row coverage, implied Dim 9 staleness cap, last improvement pass (from `improvement-backlog.md`), trigger/outcome evals present, count of items under `## Open` (fleet total in footer) | `ages`; ranking for `freshen --all` | Stalest first. `--json` for machine output |
| `advisory-lag.py` | Ranks skills by security advisories their upstream published since the skill's `Freshened:` stamp (legacy: oldest row date); picks the GitHub repo each `sources.md` references most | Freshen priority | Critical-first; rows with unseen CRITICAL marked. A lead, not a verdict: repo attribution is crude on multi-product skills. Failed call or no feed is skipped, not zero; empty feeds print `no repo feed` with a pointer to the package-keyed endpoint, and the footer counts them separately (an empty repo feed can mean missing token scope) |
| `read-x-post.py` | Reads an `x.com` / `twitter.com` post as text for a freshen probe (`WebFetch` returns 402; bare `curl` works). Handles the 278-char `og:description` cap and the `Show more` truncation by pulling the full `NoteTweet` text from the `<script>` payload | Freshen rows citing X | Prints `[notes \| expanded \| unexpanded]` to stderr; non-zero `unexpanded` = escalate that row to the browser. Profile URLs return ~7 recent posts. See freshen-patterns §2.4 |
| `frontmatter-lengths.py` | Exact `name` / `description` / `when_to_use` char counts for one SKILL.md, combined total vs the 1,536-char listing cap, any `description` breach of the 1,024-char hard max | Blind scorer calls it for Dim 1 and Dim 9; never estimate lengths | Exact counts |
| `eval-evidence.py` | The blind scorer's only channel into a target's `evals/` (which holds prior blind totals and verdicts, so reading it directly un-blinds the pass). Prints case count, every `delta_*` measurement with source path, and the implied Dim 10 cap | Negative-Transfer Gate input | Delta is derived from the `with_skill`/`without_skill` arms, never the stored `delta.pass_rate`; a missing arm yields no delta |
| `outcome-eval.py` | Runs the skill's `evals/evals.json` through `claude plugin eval` with and without the skill (throwaway plugin under `mktemp -d`). `--against <git-ref\|dir>` adds the other version (skill arm only) and prints all three side by side. `--runs`, `--case GLOB`, `--model`, `--judge-model`, `--max-cost-usd`, `--selfcheck` | Measure whether the skill helps on its tasks | Score = fraction of assertions passed. Errored runs are NO SCORE: excluded, never counted as 0. Prompts get "Use the <name> skill for this." unless `--natural`. `--write-benchmark` writes `evals/benchmark.plugin-eval.json` (`with_skill`/`without_skill` pass rates) that `eval-evidence.py` reads for Dim 10 |
| `probe-trigger.py` | Trigger-mode measurement: spawns `claude -p` against a synthetic slash-command, parses stream-json for `Skill`/`Read` `tool_use` events, computes per-query trigger rate. Stratified train/test split, runs-per-query, threshold, parallelism | `trigger` mode | Per-query trigger rate |
| `scaffold-probe.py` | Classifies each numbered item as scaffold, criterion, or branch | Find candidate bloat, then judge fit (quality-rubric §"Procedural steps") | Advisory only; sets no score |
| `induced-cost-probe.py` | Cost of *obeying* the skill: pinned effort over cheap modes, unconditional read-everything, uncapped fan-out, over-obedience phrasing. `--refs` includes references; `--selftest` checks patterns still separate mention from use | Dim 6 | Caps Dim 6 at 6 (quality-rubric §"Induced cost") |
| `knowledge-floor.py` | Floor-mode probe: extracts checkable claims (cached to `<skill>/references/knowledge-claims.json`), asks a bare `claude -p` (empty project, every tool denied = parametric recall), buckets answers KNOWS / UNKNOWN / CONFLICTS. `--models`/`--efforts` sweep the matrix | Floor Mode | Each call reports `total_cost_usd`. Every cell records `resolved_model` (full ids); compare across releases on that field, never on the alias. See Floor Mode |
| `floor-fleet.py` | Fleet driver for Floor Mode: runs `knowledge-floor.py` per SKILL.md under a root, writes each result as it lands (resumable; `--redo` forces). `--report` re-prints leaderboard without probing; `--merge <dir,...>` folds later passes over the same claim sets into one table | Fleet Floor pass | Ranked by share of claims the strongest probed model already knows; merge columns weakest-to-strongest |
| `overlap-scan.py` | Embeds every skill twice (SkillEvaluator Tier 2): `name: description` (queries competing = trigger problem) and whole SKILL.md (duplicated material = Dim 10 problem); output is the cross-tab | Dim 10 fleet overlap | **Rank, do not threshold**: scores are z-scores against the fleet's own distribution (0.95/0.90/0.75 bands do not apply; a `--full-body --threshold 0.75` run aborts on the 1000-match cap). Lexical-overlap column flags the register artifact (long documents score high for being long). Config env-only via `--env-file`; hardcode no host. `--from-catalogs` re-scores offline |
| `dedup-fleet.py` | Fleet driver for intra-skill dedup (Pattern 6.1): runs `context-optimization-check` per skill, writes each result as it lands | Fleet duplication ranking | Ranks by duplicate **share**, not count; shares over <5 clusters print `n/a`. Names families with repetition in 3+ members (fix shared material once). Cache `${XDG_CACHE_HOME:-~/.cache}/skillevaluator/dedup/` keyed by content hash + chat model + embedding model + endpoint; unchanged skills skipped. Skills over the pairwise budget (~221 chunks at 1024 dims) report SKIPPED. Unmatched cache exits 2 (nothing measured). Needs both provider roles; `--env-file` |
| `run-cost.py` | Token/cost accounting from a session transcript; dedups on `requestId`; reads `<session>/subagents/agent-*.jsonl` so scorers and probe fleets are costed by `agentType` and task. Also timing: per-model p50 latency, output tok/s, in-model vs wall time (= effective concurrency) | Cost or timing of a run | `--json`, `--list` (enumerate sessions), `--since` (one phase). Rates in `scripts/model-rates.json` (refreshed from `sources.md` `Model pricing` row): list rates, read dollars as relative sizing, not an invoice |
| `check-advisory-floors.py` | Checks every "CVE-X is fixed in vY" claim in a skill against the advisory | Fleet check; `freshen` and `advisory-lag.py` do not verify claims already made | Flags floors too low (named version still in the affected range) and fix credited to the wrong line (version outside every affected range) |
| `check-expiring-claims.py` | Lists skill claims dated in the future (statements that expire on a known day) | Fleet check | Flags relative phrases ("roughly three months out") as well as dates; a correct date beside a rotted description is a defect |
| `check-issue-states.py` | Flags prose whose issue/PR state contradicts the tracker | Fleet check | Reports three classes, each a defect: A text says open + tracker CLOSED/MERGED; B text says merged + tracker CLOSED (unmerged); C text says unmerged + tracker MERGED |
| `check-links.py` | Checks external links a skill cites, targeting documentation hosts and GitHub `blob`/`tree` paths (the two classes that rot) | Whole-tree sweep (the gate only checks staged skills) | Dead link = fix or replace the citation |
| `check-shell-fences.py` | Every ```` ```bash ````/```` ```sh ```` fence: pass 1 `bash -n`; pass 2 line-continuation regex (`cmd \   # note` does not continue the line; `bash -n` misses it) | Fleet check | Any finding is a copy-paste break |
| `check-yaml-fences.py` | Parses every YAML fence | Fleet check | Parse failure = broken manifest (e.g. unquoted `[` `]` in a flow mapping) |
| `check-tables.py` | Finds markdown table rows whose cell count differs from the header | Fleet check | Renderers drop cells past the header's column count, losing the last (payload) column |
| `batch-workflow.js` | `Workflow`-tool driver for batch improve + freshen (recon, apply, blind pipeline, median-of-3 final blind). Skill list from `args` | Batch Mode: `Workflow({scriptPath: "${CLAUDE_SKILL_DIR}/scripts/batch-workflow.js", args: [...]})`; see `SKILL.md` §"Batch" | |

#### Eval-corpus maintenance (fleet-wide, not per-run)

Use only when the corpus itself is the problem (a `delta_pass_rate` that cannot resolve a change, or untrustworthy grading), not during a normal `improve` or `freshen` run.

| Script | What it does | Caveat |
|---|---|---|
| `normalize-evals.py` | Collapses every skill's `evals.json` onto one schema and stamps provenance | A stale eval set defends the stale skill |
| `backfill-assertions.py` | Writes discrete outcome assertions for cases graded only against prose `expected_output` | Enforces outcome assertions over text-recall ones ("expert parallelism is set correctly for a 2-node MoE deployment", not "mentions `--enable-expert-parallel`") |
| `grow-evals.py` | Adds cases until a skill can resolve a change; floor of 8 (one flip = 12.5 points) | New cases complement existing prompts, not repeat them |
| `regrade.py` | Re-buckets stored floor-mode answers with a stricter grader, no re-probing | Keeps `CONFLICTS` free of agree-with-different-detail and hedged answers |
| `bucket-evals.py` | Labels every trigger-eval query by bucket (negatives definitional; three positive buckets classified by the chat model, one batched call per skill), reports fleet balance | Target `contextual` 20%. Fails closed: any UNLABELLED left exits 1 |

## Deterministic safety gate

Use NVIDIA's own command, not a wrapper. `--policy` is the way to declare "this finding does not apply to us":

```bash
skillevaluator validate <skills-dir> --type skill --external \
  --policy .claude/skillevaluator-policy.yaml --no-dedup -c
```

Catches what no rubric dimension can: tag-block smuggling payloads (CRITICAL; report decodes them), leaked home paths, schema breaks that stop a skill loading. Needs the binary and its scanners, no API key. One skill ~0.3s; 68 skills ~4m40s, so the pre-commit hook (`scripts/skillevaluator-gate.sh`) scopes to staged skills. Docs: [ci-integration](https://docs.nvidia.com/skills/skillevaluator/ci-integration), [installation](https://docs.nvidia.com/skills/skillevaluator/installation).
