# Autoresearch Ecosystem & Prior Art

*Last updated: 2026-06-09. See `results/autoresearch-evolution-research-2026-04-06.md`
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

## Curated Lists

- [alvinreal/awesome-autoresearch](https://github.com/alvinreal/awesome-autoresearch) —
  60+ projects organized by category
- [WecoAI/awesome-autoresearch](https://github.com/WecoAI/awesome-autoresearch) —
  Includes optimization traces showing what agents actually tried

## Production Results

- [SkyPilot: Scaling Autoresearch](https://blog.skypilot.co/scaling-autoresearch/) —
  16 GPUs, 910 experiments, $300. Agent autonomously developed two-tier H100/H200 strategy.
- [Shopify Liquid PR #2056](https://github.com/Shopify/liquid/pull/2056) — 93 commits,
  53% faster rendering, 61% fewer allocations from autoresearch.
- [PJ Hoberman: 60 Experiments](https://blog.pjhoberman.com/autoresearch-60-experiments-production-search) —
  Production search optimization. Mapped the ceiling. Co-optimization pitfalls.
