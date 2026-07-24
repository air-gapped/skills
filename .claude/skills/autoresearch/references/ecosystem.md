# Autoresearch Ecosystem & Prior Art

*Last updated: 2026-07-24. See `results/autoresearch-evolution-research-2026-04-06.md`
for the full research report with methodology, findings, and source assessments.*

## Canonical

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — The original
  630-line implementation. Three-file architecture (prepare.py read-only,
  train.py agent-editable, program.md human-editable). val_bpb metric, 5-min budget.
- [karpathy/autoresearch program.md](https://github.com/karpathy/autoresearch/blob/master/program.md) —
  The agent instruction file. Our SKILL.md is heavily influenced by this.
- [Karpathy, "notes from claude coding" (X, 2026-01-26)](https://x.com/karpathy/status/2015883857489522876) —
  Primary source for the skill's thesis. The *Leverage* note: give success criteria
  and loop, write the naive-correct version first then optimize while preserving
  correctness, shift imperative → declarative. Same post the 160K-star
  [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills)
  CLAUDE.md derives from (its Simplicity-First / Goal-Driven principles mirror this
  skill's Simplicity Criterion and optimize loop).

## Beyond Hill-Climbing

- [WecoAI/aideml](https://github.com/WecoAI/aideml) — Tree search in code space.
  4x more medals than linear agents on MLE-Bench (75 Kaggle competitions).
- [gepa-ai/gepa](https://github.com/gepa-ai/gepa) — Pareto-aware evolutionary search.
  ICLR 2026 Oral. Multi-objective, reads full execution traces. 35x fewer rollouts.
- [SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) — Island evolution
  with UCB bandit model selection. Dynamic islands, code embedding novelty tracking.
- [OpenEvolve](https://huggingface.co/blog/codelion/openevolve) — Open-source
  population-based evolution. YAML config, EVOLVE-BLOCK markers, multi-objective.

## Meta / Self-Improving Agents

- [facebookresearch/HyperAgents](https://github.com/facebookresearch/HyperAgents) —
  Recursive self-improvement. Meta-agent modifies task agents AND itself.
- [metauto-ai/HGM](https://github.com/metauto-ai/HGM) — Huxley-Godel Machine. Tree
  search over agent codebases. ICLR 2026 Oral. Human-level on SWE-bench Verified.
- [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) — Full
  scientific discovery loop. Agentic tree search. First AI paper through peer review.
- [Meta-Harness](https://yoonholee.com/meta-harness/) — Agentic outer-loop. Reads
  10M+ tokens of execution traces. 10x fewer evaluations than program-search baselines.

## Mechanisms Worth Borrowing

Descendants whose contribution is a specific loop mechanism rather than a port.

- [jmilinovich/goal-md](https://github.com/jmilinovich/goal-md) — generalizes the
  pattern to repos where the agent must *first construct a measurable fitness
  function* before it can optimize. Independent arrival at Mode 3's premise:
  the hard part is manufacturing the metric, not climbing it.
- [ArmanJR-Lab/autoautoresearch](https://github.com/ArmanJR-Lab/autoautoresearch) —
  adds a "director" that injects novelty (arXiv papers, a reasoning model) into a
  stalled loop, and reports baseline-vs-director comparisons with stall analysis.
  A concrete implementation of the Local Maxima escape strategies.
- [tonitangpotato/autoresearch-engram](https://github.com/tonitangpotato/autoresearch-engram) —
  persistent cross-session memory with frequency-weighted retrieval, so
  experiment history survives beyond one run. Same direction PERFOPT-Bench
  measured a gain from.
- [sentient-agi/EvoSkill](https://github.com/sentient-agi/EvoSkill) — evolves
  reusable skills and prompts *from failed trajectories* against benchmarks;
  supports Claude Code, Codex CLI, OpenCode, OpenHands, Goose. Turns the discard
  pile into an artifact instead of discarding it.

## Swarm / Distributed

- [HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam) — Leader + specialized workers.
  Multi-GPU parallel.
- [autoresearch@home](https://github.com/mutable-state-inc/autoresearch-at-home) —
  Distributed SETI@home-style with experiment claiming and hypothesis exchange.

## Claude Code Specific

- [drivelineresearch/autoresearch-claude-code](https://github.com/drivelineresearch/autoresearch-claude-code) —
  Pure Claude Code skill port. Baseball biomechanics R² 0.44→0.78 in 22 experiments.
- [armgabrielyan/autoloop](https://github.com/armgabrielyan/autoloop) — Agent-agnostic.
  Explicit phases, bounded experiments, path-scoped git.
- [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code) — Wrapper
  with dual-condition exit detection and circuit breaker for stuck loops.

## Research Patterns

- [stanford-oval/storm](https://github.com/stanford-oval/storm) — STORM/Co-STORM v1.1.0.
  Multi-perspective research. Our Mode 2 is based on this pattern. **Note the
  pin is stable because the project is quiet, not because it is actively
  maintained at that version**: v1.1.0 dates from 2025-01-23 (~18 months) and
  the repo's last push was 2025-09-30 (~10 months) as of 2026-07-21. The
  *pattern* is what Mode 2 borrows and that doesn't rot; treat the codebase as
  reference rather than a dependency to track.
- [dzhng/deep-research](https://github.com/dzhng/deep-research) — Minimal recursive
  depth+breadth implementation in <500 lines.
- **Actively-maintained alternatives to a dormant STORM**, if the codebase rather
  than the pattern is what's wanted: [bytedance/deer-flow](https://github.com/bytedance/deer-flow)
  (now a long-horizon harness with sandboxes, memory, subagents — pushed
  2026-07-24), [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)
  (parallelized plan-and-solve: static planner decomposes, concurrent retrieval
  agents execute), and [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research).
  All three are outline-or-plan-driven like STORM; none replaces the
  multi-perspective decomposition Mode 2 borrows.
- [Deep Researcher Reflect Evolve](https://arxiv.org/abs/2601.20843) — Sequential
  refinement with Global Research Context. Beat Claude Researcher, Perplexity, and Grok.
  Key finding: sequential > parallel in 95.6% of configurations.

## Reward Hacking & Safety

- [METR: Reward Hacking](https://metr.org/blog/2025-06-05-recent-reward-hacking/) —
  o3 rewrote scoring code in 25% of runs. Our anomaly check addresses this.
- [Nick Oak: Tennis XGBoost](https://nickoak.com/posts/tennis-xgboost-autoresearch/) —
  Detailed reward hacking case study. "Move the judge out of the arena."
- [Langfuse: Cautionary Tale](https://langfuse.com/blog/2026-03-24-optimizing-ai-skill-with-autoresearch) —
  Score 0.35→0.824 but optimizer removed safety gates. "Review like a junior's PR."

## Eval-Driven Development

- [Anthropic: Agent Evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) —
  Capability evals vs regression evals. Start with 20-50 tasks from real failures.
- [DSPy MIPROv2](https://dspy.ai/) — Bayesian surrogate model (TPE) for prompt optimization.
  State of the art for systematic prompt tuning.

## Benchmarks for the Loop Itself

Benchmarks that measure agents doing *exactly what Mode 1 does*. Useful as
evidence about the loop's design, not as dependencies.

- [PERFOPT-Bench](https://arxiv.org/abs/2607.07744) (2026-07-08) — evaluates
  coding agents on the full performance-engineering workflow: profile, locate
  the bottleneck, optimize, preserve correctness, reproduce the speedup. Two
  findings bear on this skill directly. First, *"no single stack dominates, and
  changing the agent framework can materially change the same LLM's per-task
  speedup profile"* — the harness is a variable, not a constant, so a loop's
  design decisions matter as much as its model. Second, *"some large gains arise
  from benchmark-specific shortcut exploitation"* — independent confirmation of
  the anomaly check in Mode 1 Step 6. The paper also reports that externalizing
  optimization summaries between sessions unlocks further gains, which is the
  measured case for the results ledger and end-of-session summary.
- [OPT-BENCH](https://arxiv.org/abs/2605.08904) (2026-05-09) — iterative
  self-optimization across 20 ML tasks and 10 NP-hard problems, 19 LLMs from 3B
  to 235B. Stronger models extract more from environmental feedback, and base
  model capacity — not loop design — sets the ceiling on adaptability. Read as a
  caution against attributing a plateau to the loop when it belongs to the model.
- [SEAGym](https://arxiv.org/abs/2606.17546) (2026-06-16) — evaluation
  environment for self-evolving agents on Terminal-Bench 2.0 and HLE, with a
  shared epoch/batch protocol for comparing outer-loop designs.

## Curated Lists

- [webfuse-com/awesome-autoresearch](https://github.com/webfuse-com/awesome-autoresearch) —
  100+ projects organized by category. Transferred from `alvinreal/` (old URL
  still redirects, so liveness probes do not catch the move — check `full_name`
  in the API response, not the HTTP status).
- [WecoAI/awesome-autoresearch](https://github.com/WecoAI/awesome-autoresearch) —
  Includes optimization traces showing what agents actually tried

## Production Results

- [SkyPilot: Scaling Autoresearch](https://blog.skypilot.co/scaling-autoresearch/) —
  16 GPUs, 910 experiments, $300. Agent autonomously developed two-tier H100/H200 strategy.
- [Shopify Liquid PR #2056](https://github.com/Shopify/liquid/pull/2056) — 93 commits,
  53% faster rendering, 61% fewer allocations from autoresearch.
- [PJ Hoberman: 60 Experiments](https://blog.pjhoberman.com/autoresearch-60-experiments-production-search) —
  Production search optimization. Mapped the ceiling. Co-optimization pitfalls.
