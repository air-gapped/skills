# Autoresearch Ecosystem & Prior Art

*Last updated: 2026-08-20. Full research reports with methodology, findings, and
source assessments live in `results/` — `autoresearch-evolution-research-2026-04-06.md`
and `autoresearch-landscape-research-2026-08-20.md`. That directory is a local
archive and is gitignored, so it is empty in a fresh checkout.*

## Table of Contents
- [Canonical](#canonical): Karpathy's implementation · program.md · the thesis post
- [Beyond Hill-Climbing](#beyond-hill-climbing): tree search · evolutionary · does greedy hold up (2026 evidence, both directions)
- [Meta / Self-Improving Agents](#meta--self-improving-agents)
- [Mechanisms Worth Borrowing](#mechanisms-worth-borrowing): fitness-function-first · novelty injection · cross-session memory · skill evolution · the confidence cliff
- [Swarm / Distributed](#swarm--distributed)
- [Claude Code Specific](#claude-code-specific)
- [Research Patterns](#research-patterns): STORM and its live successors · verification as a separate stage (behind Mode 2's Audit step)
- [Reward Hacking & Safety](#reward-hacking--safety)
- [Eval-Driven Development](#eval-driven-development)
- [Benchmarks for the Loop Itself](#benchmarks-for-the-loop-itself): PERFOPT-Bench · OPT-BENCH · SEAGym · PAST-Bench
- [Curated Lists](#curated-lists)
- [Production Results](#production-results)

## Canonical

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — The original
  630-line implementation. Three-file architecture (prepare.py read-only,
  train.py agent-editable, program.md human-editable). nanochat val_bpb metric,
  5-min budget.
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

- [WecoAI/aideml](https://github.com/WecoAI/aideml) — Tree search in code space
  (arXiv:2502.13138). 4x more medals than linear agents on MLE-Bench (75 Kaggle
  competitions). Now positioned as the OSS research root of the commercial Weco
  product; the technical claim is unaffected.
- [gepa-ai/gepa](https://github.com/gepa-ai/gepa) — Pareto-aware evolutionary search.
  ICLR 2026 Oral. Multi-objective, reads full execution traces. 35x fewer rollouts.
- [SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) — Island evolution
  with UCB bandit model selection. Dynamic islands, code embedding novelty tracking.
- [OpenEvolve](https://huggingface.co/blog/codelion/openevolve) — Open-source
  population-based evolution. YAML config, EVOLVE-BLOCK markers, multi-objective.

### Does greedy actually hold up? (2026 evidence, both directions)

The honest answer is *it depends on the density of remaining improvements*, and
the strongest result says a loop should switch strategy rather than pick one.

- [Greedy Is a Strong Default: Agents as Iterative Optimizers](https://arxiv.org/abs/2603.27415)
  (Yitao Li, 2026-03-28) — greedy hill climbing with early stopping is a strong
  default; more sophisticated strategies added evaluation cost without
  meaningful benefit. The direct defence of Mode 1's core choice.
- [FML-bench](https://arxiv.org/abs/2605.17373) (Qiran Zou, 2026-05-17) — a
  controlled study of research-agent strategies through the lens of search
  dynamics. A simple greedy hill-climber nearly matches the best tree-search
  agent, **which strategy wins depends on whether improvement opportunities are
  dense or sparse**, and an agent that switches strategy on detecting stagnation
  beat every fixed-strategy agent tested. This is why Mode 1's plateau rule
  widens the search rather than only rotating hypothesis category.
- [GEAR: Genetic Autoresearch for Agentic Code Evolution](https://arxiv.org/abs/2605.13874)
  (Ahmadreza Jeddi, 2026-05-08) — population-based search (parent selection on
  productivity/novelty/coverage, plus mutation and crossover) sustains
  improvement over long runs where single-path greedy settles into one local
  optimum. The counter-case to the two above.
- [SwarmResearch](https://arxiv.org/abs/2607.02807) (Yuvraj Virk, 2026-07-02) —
  a single long-running optimizer narrows onto one high-level approach as
  context accumulates; a coordinator plus parallel search agents on separate git
  branches beat both single-agent and standard evolutionary search on 13/15
  tasks. Read alongside REFLECT (Mode 1 step 9), which exists to counteract the
  same narrowing inside one agent.

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
- [Rehearse](https://arxiv.org/abs/2607.27687) (Jiazhen Ji, 2026-07-30) — studies
  autoresearch-style loops directly and finds a **confidence cliff**: as kept
  changes accumulate, a judge's selective accuracy at predicting whether a
  proposed change will help collapses from 82.8% to 56.9%. Comparing candidates
  *before* execution against a focused memory of similar past attempts restores
  it to 83.5% and improves the final metric under a fixed budget. This is the
  mechanism behind Mode 1's HYPOTHESIZE step sketching 2-3 candidates and
  checking them against the nearest results.tsv rows rather than committing to
  the first idea — the correction is cheap because results.tsv is already the
  memory it needs.

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
  maintained at that version**: v1.1.0 dates from 2025-01-23 (~19 months) and
  the repo's last push was 2025-09-30 (~11 months) as of 2026-08-20. The
  *pattern* is what Mode 2 borrows and that doesn't rot; treat the codebase as
  reference rather than a dependency to track.
- [dzhng/deep-research](https://github.com/dzhng/deep-research) — Minimal recursive
  depth+breadth implementation in <500 lines.
- **Actively-maintained alternatives to a dormant STORM**, if the codebase rather
  than the pattern is what's wanted (all verified 2026-08-20):
  [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)
  (parallelized plan-and-solve: static planner decomposes, concurrent retrieval
  agents execute; v3.6.0 2026-07-18) and
  [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)
  (continuous off `main`, no tagged releases). Both are outline-or-plan-driven
  like STORM; neither replaces the multi-perspective decomposition Mode 2
  borrows.
  **[bytedance/deer-flow](https://github.com/bytedance/deer-flow) no longer
  belongs on that list.** Its v2.0.0 (2026-06-25) is a ground-up rewrite into a
  general persistent-agent harness — sandboxed sub-agents, memory, chat-bot
  channels, self-editing agent files. The STORM-shaped research-report pipeline
  it used to be now lives only on the frozen `main-1.x` branch. Very active, but
  no longer a comparable deep-research report generator.
- **STORM has a successor by lineage, not a replacement:**
  [stanford-oval/DataSTORM](https://github.com/stanford-oval/DataSTORM) (created
  2026-08-06, pushed 2026-08-19, and essentially unadopted at 1 star — new, not
  established) is built on STORM's `knowledge_storm/` codebase by
  the same lab, and is the implementation for arXiv:2604.06474. It reframes deep
  research over **structured databases** — tree search where each node poses a
  sub-question answered by generated SQL, branches scored for interestingness and
  expanded, findings reranked into a staged citation-traceable report. The paper
  reports SOTA on InsightBench (+19.4% insight recall, +7.2% summary). Scoped to
  database/EDA work, not general prose topics, so it is adjacent to Mode 2 rather
  than a drop-in. Note what this does *not* mean: Stanford OVAL has never declared
  STORM end-of-life, the repo is dormant but not archived, and the succession is
  inferred from code lineage and lab activity, not from any statement.
- **Newer entrants worth watching**, none adopted here:
  [EverMind-AI/Raven](https://github.com/EverMind-AI/Raven) (created 2026-05-21,
  fastest-growing new project in the space — self-improving harness exposing a
  `deep_research` tool with cross-session memory),
  [lajosdeme/mole](https://github.com/lajosdeme/mole) (created 2026-08-01 —
  enforced step/token budget plus quote-level verification, the two things Mode 2
  handles by convention rather than mechanism), and
  [LearningCircuit/local-deep-research](https://github.com/LearningCircuit/local-deep-research)
  (local-first, 10+ search backends including arXiv/PubMed).
- [Deep Researcher Reflect Evolve](https://arxiv.org/abs/2601.20843) — Sequential
  refinement with Global Research Context. Beat Claude Researcher, Perplexity, and Grok.
  Key finding: sequential > parallel in 95.6% of configurations.

### Verification as a separate stage (2026 evidence behind Mode 2's Audit step)

Four independent 2026 results converge on the same architectural point: in
deep research the failure is not fluency, it is claims that do not trace to
evidence — and catching that needs a stage of its own, not a more careful
writer.

- [Inference-Time Scaling of Verification](https://arxiv.org/abs/2601.15808)
  (Yuxuan Wan, 2026-01-22) — builds a failure taxonomy of five major categories
  and thirteen sub-categories, and shows a rubric-guided verifier
  ("DeepVerifier") beats vanilla agent-as-judge and LLM-judge baselines by
  **12-48% meta-evaluation F1**. The case for auditing against an explicit
  checklist rather than asking a model "is this good".
- [AREX](https://arxiv.org/abs/2607.21461) (Shuqi Lu, 2026-07-23) — alternates
  evidence gathering with provisional-answer construction, then audits the
  provisional answer constraint-by-constraint and launches targeted follow-up on
  what is unresolved. A sequential-refinement counterpart to STORM's
  parallel-perspective decomposition; Mode 2's Audit step borrows the outer loop
  without giving up the parallel first round.
- [Towards Verifiable Multimodal Deep Research](https://arxiv.org/abs/2605.29861)
  (Chenghao Zhang, 2026-05-28; the system is named Ptah inside the paper) —
  plan → research → write, with a dedicated verifier agent as an explicit
  acceptance gate on factual grounding and citation fidelity.
- [From Fluent to Verifiable](https://arxiv.org/abs/2602.13855) (Razeen A
  Rasheed, 2026-02-14) — proposes an Auditable Autonomous Research standard
  measured on provenance coverage, provenance soundness, **contradiction
  transparency**, and audit effort. Contradiction transparency is the one Mode 2
  most easily loses: merging is allowed to *note* a disagreement, never to
  quietly pick a winner. The report's Competing Perspectives section is where
  that obligation lands.
- [DR³-Eval](https://arxiv.org/abs/2604.14683) (Qianqian Xie, 2026-04-16) — five
  scoring axes for deep-research reports (Information Recall, Factual Accuracy,
  Citation Coverage, Instruction Following, Depth Quality). The nearest thing to
  an off-the-shelf rubric if Mode 2's output ever needs a number.

**Two things are NOT settled, and should not be cited as if they were.** No 2026
work found revises STORM's guidance on the optimal *number* of perspectives, and
no paper benchmarks parallel-perspective decomposition head-to-head against
sequential refinement on the same tasks. Examples exist on both sides; a
comparison does not.

- [OSU-NLP-Group/QUEST](https://github.com/OSU-NLP-Group/QUEST) /
  [arXiv:2605.24218](https://arxiv.org/abs/2605.24218) (Jian Xie, 2026-05-22) —
  open-weight 2B-35B models trained specifically as deep-research agents on
  fully synthetic rubric-tree-verified tasks. Relevant only if the underlying
  model, rather than the harness, is what gets swapped.

## Reward Hacking & Safety

- [METR: Reward Hacking](https://metr.org/blog/2025-06-05-recent-reward-hacking/) —
  o3 rewrote scoring code in 25% of runs. Our anomaly check addresses this.
- [Nick Oak: Tennis XGBoost](https://nickoak.com/posts/tennis-xgboost-autoresearch/) —
  Detailed reward hacking case study. "Move the judge out of the arena."
- [Langfuse: Cautionary Tale](https://langfuse.com/blog/2026-03-24-optimizing-ai-skill-with-autoresearch) —
  Score 0.35→0.824 but optimizer removed safety gates. "Review like a junior's PR."
- [Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops](https://arxiv.org/abs/2606.08960)
  (Ziqian Zhong, 2026-06-08) — 323 environments (16%) across five benchmarks were
  hackable by frontier models *from the task description alone*; a
  hacker/fixer/solver triad patching the verifier per discovered exploit cut
  KernelBench attack success from 62% to 0%. The base rate that justifies the
  anomaly check: reward hacking is not an exotic failure, it is one task in six.
- [Self-Authored Verification Is Unreliable in Heuristic Self-Improving Agents](https://arxiv.org/abs/2607.24300)
  (Diandian Guo, 2026-07-27) — names the **verifier-deployment gap**: self-scored
  improvement can stay near-perfect while real performance degrades, and weaker
  agents damage prior capability while still passing their own tests. Proposes
  SEAL, a sealed external verification layer the agent cannot edit. This is the
  measured argument for the Truth Layer being read-only by construction rather
  than by good intentions.

## Eval-Driven Development

- [Anthropic: Agent Evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) —
  Capability evals vs regression evals. Start with 20-50 tasks from real failures.
- [DSPy](https://dspy.ai/) — Programmatic prompt optimization. **GEPA** (reflective
  prompt evolution) is now the optimizer DSPy leads with; MIPROv2 (Bayesian
  surrogate over a TPE) is still shipped but no longer the headline. The
  surrogate-search idea is what this skill points at for pure parameter sweeps
  — the flagship label moved, the mechanism did not.

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
- [PAST-Bench](https://arxiv.org/abs/2608.04003) (Shuhan Xue, 2026-08-04) —
  benchmarks the foundations of recursive self-improvement in personal agents.
  Retained-experience gains are real but uneven across capabilities and models,
  so a session-carryover mechanism should be validated end-to-end rather than
  assumed to help.
- [Recursive Self-Improvement in AI](https://arxiv.org/abs/2607.07663) (Mingguang
  Chen, 2026-07-08) — survey of ~1,250 papers building a verification-reliability
  hierarchy. Its framing is worth internalizing: every self-improvement loop's
  choice of evaluator is an implicit claim about what may substitute for human
  judgment. That is the question Step 1's "Verifier" row is really asking.

## Curated Lists

- [webfuse-com/awesome-autoresearch](https://github.com/webfuse-com/awesome-autoresearch) —
  100+ projects organized by category. Transferred from `alvinreal/` (old URL
  still redirects, so liveness probes do not catch the move — check `full_name`
  in the API response, not the HTTP status).
- [WecoAI/awesome-autoresearch](https://github.com/WecoAI/awesome-autoresearch) —
  Includes optimization traces showing what agents actually tried

## Production Results

- [SkyPilot: Scaling Autoresearch](https://skypilot.ai/blog/scaling-autoresearch/) —
  16 GPUs, 910 experiments, $300. Agent autonomously developed two-tier H100/H200 strategy.
- [Shopify Liquid PR #2056](https://github.com/Shopify/liquid/pull/2056) — 93 commits,
  53% faster parse+render, 61% fewer allocations from autoresearch. **Still open,
  not merged** (verified 2026-08-20) — the measured win is real; upstream
  acceptance is a separate question and this row is not evidence of it.
- [PJ Hoberman: 60 Experiments](https://blog.pjhoberman.com/autoresearch-60-experiments-production-search) —
  Production search optimization. Mapped the ceiling. Co-optimization pitfalls.
