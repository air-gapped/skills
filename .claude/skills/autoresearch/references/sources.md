# Sources — Autoresearch Ecosystem

Freshened: 2026-08-20

URLs backing the autoresearch skill's ecosystem reference. Freshen Mode reads
this file, probes each row, and stamps `Last verified` / `Pinned` fields.
Dim 9 of the quality rubric caps Domain Accuracy based on oldest `Last verified`.

## Convention

Columns: `Source`, `URL`, `What it contains`, `Last verified` (YYYY-MM-DD),
`Pinned` (version or git ref, optional). Mark rows to skip with
`<!-- ignore-freshen -->` at the end.

## Most recent freshen pass: 2026-08-20

Discovery pass — "what does the landscape look like in August 2026", plus a full
re-probe of every row. All 22 previously-tracked rows verified live; no dead
links.

### Notable findings (freshen pass 2026-08-20)

- **STORM has a successor by lineage, and it is not a replacement.**
  `stanford-oval/DataSTORM` (created 2026-08-06, pushed 2026-08-19, 1 star) is
  built on STORM's `knowledge_storm/` package by the same lab and implements
  arXiv:2604.06474 — but it reframes deep research over **structured databases**,
  not general prose topics. Stanford OVAL has still never declared STORM
  end-of-life; the repo is dormant (last push 2025-09-30, v1.1.0 from
  2025-01-23) but **not archived**. Mode 2's premise is unchanged: the pattern
  is what it borrows, and the pattern has not rotted.
- **deer-flow no longer belongs on the STORM-alternatives list.** Its v2.0.0
  (2026-06-25) is a ground-up rewrite into a general persistent-agent harness;
  the STORM-shaped report pipeline survives only on the frozen `main-1.x`
  branch. The repo is extremely active (80k stars, pushed daily) — which is
  exactly why a liveness probe could not have caught this. **Scope drift, not
  link drift**: the second time in three passes that the failure was semantic.
- **Verification is the mechanism upgrade of 2026.** Four independent papers
  (2601.15808, 2607.21461, 2605.29861, 2602.13855) converge on making
  verification a separate stage rather than folding it into synthesis, with a
  rubric-guided verifier measured 12-48% F1 over LLM-as-judge. Mode 2 had no
  such stage. Added as step 5, "Audit", with the checklist in
  `deep-research.md` §"Audit Pass".
- **Greedy hill climbing survives contact with 2026's evidence — conditionally.**
  2603.27415 defends it directly; 2605.13874 and 2607.02807 show population and
  swarm methods beating single-path greedy on long runs; 2605.17373 reconciles
  them — density of remaining improvements decides, and *strategy switching on
  stagnation* beat every fixed strategy. Mode 1's plateau rule now widens the
  search rather than only rotating category.
- **The confidence cliff is real and cheap to fix.** 2607.27687 measures a
  judge's selective accuracy collapsing 82.8% -> 56.9% as kept changes
  accumulate, restored to 83.5% by comparing candidates before execution against
  similar past attempts. HYPOTHESIZE now sketches 2-3 candidates against
  results.tsv instead of committing to the first.
- **Reward hacking has a base rate now:** 16% of environments across five
  benchmarks were hackable from the task description alone (2606.08960), and
  2607.24300 names the verifier-deployment gap — self-scored improvement staying
  near-perfect while real performance degrades. Both are independent support for
  the anomaly check and the read-only truth layer.
- **DSPy's flagship optimizer moved** from MIPROv2 to GEPA. Content drift behind
  a live URL — the row said "MIPROv2, state of the art", which is no longer how
  DSPy positions it.
- **SkyPilot's blog domain rebranded** `blog.skypilot.co` -> `skypilot.ai/blog`.
  Old URL 301s, content unchanged.
- **Shopify Liquid PR #2056 is still open, not merged** (93 commits, 53% faster
  parse+render). The measured win is real; upstream acceptance is not, and the
  row now says so.
- **karpathy/autoresearch remains dormant** (no push since 2026-03-26; 91,968 ->
  94,232 stars). No fork has become a de-facto successor — the highest-activity
  one has 327 stars. Papers now cite "the AutoResearch baseline" as a fixed
  reference point for greedy single-path search rather than a moving target.
- **Two smaller drifts, both cosmetic so far.** `WecoAI/aideml` is now described
  by its own repo as "the research Weco grew out of" — repositioned as the OSS
  root of a commercial product rather than a standalone artifact; the tree-search
  and MLE-Bench claims are unaffected. `SakanaAI/AI-Scientist-v2` has not been
  pushed since 2025-12-19, the quietest row in the file after STORM itself.
- **The Karpathy X row was verifiable this time.** X returns HTTP 402 to a
  direct fetch, but the post was read through an alternate reader and all three
  elements of the *Leverage* note the row claims are present verbatim. Worth
  recording as method: an X row is not unverifiable, it is unverifiable *by
  WebFetch*.
- **Explicitly not settled**, and not to be cited as if it were: no 2026 work
  revises STORM's guidance on the optimal *number* of perspectives, and nothing
  benchmarks parallel-perspective decomposition head-to-head against sequential
  refinement on the same tasks.

### Prior pass: 2026-07-24

Discovery-oriented pass — the question was "what has appeared beyond Karpathy and
STORM", not "are the links alive". Probed the curated lists for new entries, the
arXiv benchmark literature, and the Mode 2 alternatives.

### Notable findings (freshen pass 2026-07-24)

- **First real drift in four passes — and liveness probes could not see it.**
  `alvinreal/awesome-autoresearch` was transferred to
  **`webfuse-com/awesome-autoresearch`**. GitHub redirects the old URL, so
  `archived=false` + HTTP 200 both pass while the canonical owner is wrong. This
  is exactly the failure the 2026-07-21 method note predicted. **Probe
  `full_name` in the API response, not the HTTP status.** The list has also grown
  from ~60 to 100+ entries.
- **Three benchmarks now measure what Mode 1 does** — none existed in the skill
  before. PERFOPT-Bench (2026-07-08) is the important one: it finds that the
  *harness*, not just the model, changes per-task speedup, that large gains are
  frequently shortcut exploitation (independent support for the anomaly check),
  and that carrying summaries across sessions unlocks further gains.
- **STORM's dormancy now has live competition.** `bytedance/deer-flow` (pushed on
  the probe date), `gpt-researcher`, and `langchain-ai/open_deep_research` are all
  active. STORM last pushed 2025-09-30. The *pattern* Mode 2 borrows still holds;
  the codebase is the part that has been overtaken.
- **Four descendants contribute mechanisms rather than ports** — `goal-md`
  (construct the fitness function first), `autoautoresearch` (novelty injection to
  escape stalls), `autoresearch-engram` (cross-session memory), `EvoSkill`
  (evolve skills from failed trajectories). Recorded under "Mechanisms Worth
  Borrowing" rather than scattered into the port lists.
- **The practice has an event circuit now:** Ralphthon@ICML 2026 (Seoul,
  2026-07-05) was the fifth such hackathon after San Francisco, Singapore, and
  Busan, themed "Can AI automate research?". Context for the
  dormant-repo/spreading-practice split, not a correctness claim.
- **karpathy/autoresearch:** still dormant (no push since 2026-03-26), stars
  91,664 → 91,968. The plateau in star growth is itself new — the six-week
  surge reported on 2026-07-21 has flattened.

### Prior pass: 2026-07-21

Probed all 16 ecosystem repos via `gh api` (pushed_at / archived / stars), the
tracked Shopify Liquid PR, and every non-GitHub URL by HTTP status.

### Notable findings (freshen pass 2026-07-21)

- **No drift, deprecations, or broken links — again.** All **16** repos alive
  and unarchived; all **9** non-GitHub URLs return **200** (including
  pjhoberman.com, which rate-limited a curl on the prior pass). Shopify Liquid
  **PR #2056 still OPEN** (last updated 2026-04-13 — three months quiet);
  claims unchanged. Third consecutive clean pass.
- **Two dormancy signals worth recording — the ecosystem is not uniformly
  active:**
  - **stanford-oval/storm** — v1.1.0 is from **2025-01-23 (~18 months)** and the
    repo last pushed **2025-09-30 (~10 months)**. The v1.1.0 pin has been
    "stable" across three passes, but that is quietness, not maintenance.
    Annotated in `ecosystem.md`: Mode 2 borrows the *pattern*, which doesn't
    rot — treat the codebase as reference, not a tracked dependency.
  - **SakanaAI/AI-Scientist-v2** — last push **2025-12-19 (~7 months)**.
- **karpathy/autoresearch: dormant repo, still-climbing adoption.** No pushes
  since **2026-03-26** (~4 months), yet stars went **85,764 → 91,664** in the
  six weeks since the last pass. Worth separating explicitly, since this
  skill's whole methodology derives from that repo: the *source* is static
  while the *practice* is spreading. Dormancy here is not a deprecation signal.
  (Consistent with backlog B2 — star counts stay out of the body; recorded here
  as a trend observation only.)
- **Most active:** `gepa-ai/gepa` (pushed **2026-07-21**, i.e. the probe date),
  `frankbria/ralph-claude-code` (2026-07-18, now 9.5k stars),
  `SakanaAI/ShinkaEvolve` (07-17), `alvinreal/awesome-autoresearch` (07-16),
  `WecoAI/aideml` (07-15).

### Prior pass: 2026-06-09

Probed via `gh api` (repo liveness, archived flag, pushed_at) and batch HTTP
status checks on all non-GitHub rows older than 30 days.

### Notable findings (freshen pass 2026-06-09)

- **No drift, deprecations, or broken links.** All 9 probed repos alive and
  unarchived; all 10 probed URLs return 200 (pjhoberman.com rate-limited curl
  with 429 but confirmed alive via WebFetch). Shopify Liquid PR #2056 still
  OPEN, claims unchanged.
- **karpathy/autoresearch:** no pushes since 2026-03-26 — dormant but healthy.
  Stars drifted again 83,919 → **85,764**; still not mutated in sources.md
  (not a correctness claim), but the standalone star-count sentences in
  `ecosystem.md` were deleted this pass (backlog B2) — they rot every pass
  and carry no correctness weight.
- **Not re-probed** (stamped 2026-05-28, 12 days old): Karpathy X post
  (browser-only), stanford-oval/storm (v1.1.0 pin), dzhng/deep-research,
  gepa, aideml, ShinkaEvolve, HGM, alvinreal/awesome-autoresearch.

### Prior pass: 2026-05-28

Probed via `gh api` (releases, trees, commits) and the Chrome browser agent
(x.com, which `gh`/`WebFetch` cannot reach).

### Notable findings (freshen pass 2026-05-28)

- **No version drift, deprecations, or broken links.** Every probed repo is
  alive and unarchived; no pinned version contradicted.
- **karpathy/autoresearch:** three-file architecture verified in the live
  tree (`prepare.py`, `train.py`, `program.md` all present). No commits
  since the last pass; healthy. Star count drifted 74,359 → **83,919** —
  still not mutated (not a correctness claim).
- **stanford-oval/storm:** latest release still **v1.1.0** (2025-01-23).
  v1.1.0 pin remains correct.
- **NEW primary source — Karpathy's Jan 2026 "notes from claude coding" X
  post.** Added below under Canonical. Its *Leverage* paragraph is the
  author's own articulation of this skill's thesis: "give it success
  criteria and watch it go," write the naive-correct version first then
  optimize while preserving correctness, shift imperative → declarative to
  loop longer. Also the source the 160K-star `andrej-karpathy-skills`
  repo derives from. Verified live via browser 2026-05-28.
- **Ecosystem repos spot-checked alive:** gepa-ai/gepa (pushed 2026-05-28,
  very active), WecoAI/aideml, SakanaAI/ShinkaEvolve, metauto-ai/HGM,
  dzhng/deep-research (~19K stars), alvinreal/awesome-autoresearch.

### Prior pass: 2026-04-19

Initial sources.md generated by `freshen autoresearch`. Refs extracted from
`references/ecosystem.md`. No drift/deprecations; all URLs alive.

## Canonical

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| karpathy/autoresearch | https://github.com/karpathy/autoresearch | Original 630-line autoresearch implementation; three-file architecture (prepare.py / train.py / program.md), nanochat val_bpb metric | 2026-08-20 | master |
| karpathy/autoresearch program.md | https://github.com/karpathy/autoresearch/blob/master/program.md | Agent instruction file; heavily influenced this skill's SKILL.md | 2026-08-20 | master |
| Karpathy: "notes from claude coding" (X) | https://x.com/karpathy/status/2015883857489522876 | Primary source for the skill's thesis — *Leverage*: give success criteria and loop; naive-correct first then optimize; imperative→declarative. Source the `andrej-karpathy-skills` repo derives from | 2026-08-20 | 2026-01-26 |

## Beyond Hill-Climbing

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| WecoAI/aideml | https://github.com/WecoAI/aideml | Tree search in code space; 4x medals on MLE-Bench (arXiv:2502.13138). Now positioned as the OSS research root of the commercial Weco product — technical claim unaffected | 2026-08-20 | main |
| gepa-ai/gepa | https://github.com/gepa-ai/gepa | Pareto-aware evolutionary search (ICLR 2026 Oral) | 2026-08-20 | main |
| SakanaAI/ShinkaEvolve | https://github.com/SakanaAI/ShinkaEvolve | Island evolution with UCB bandit model selection | 2026-08-20 | main |
| OpenEvolve | https://huggingface.co/blog/codelion/openevolve | Open-source population-based evolution | 2026-08-20 | — |
| Greedy Is a Strong Default | https://arxiv.org/abs/2603.27415 | Greedy hill climbing with early stopping is a strong default; costlier strategies added little. Direct defence of Mode 1 | 2026-08-20 | 2026-03-28 |
| FML-bench | https://arxiv.org/abs/2605.17373 | Greedy vs tree search through search dynamics: density of improvements decides, and strategy-switching on stagnation beat all fixed strategies. Grounds the plateau rule | 2026-08-20 | 2026-05-17 |
| GEAR | https://arxiv.org/abs/2605.13874 | Genetic/population search sustains gains where single-path greedy settles into a local optimum | 2026-08-20 | 2026-05-08 |
| SwarmResearch | https://arxiv.org/abs/2607.02807 | A single long-running optimizer narrows onto one approach; coordinator + branch-isolated parallel agents won 13/15 tasks | 2026-08-20 | 2026-07-02 |

## Meta / Self-Improving Agents

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| facebookresearch/HyperAgents | https://github.com/facebookresearch/HyperAgents | Recursive self-improvement; meta-agent modifies task agents and itself | 2026-08-20 | main |
| metauto-ai/HGM | https://github.com/metauto-ai/HGM | Huxley-Godel Machine; ICLR 2026 Oral | 2026-08-20 | main |
| SakanaAI/AI-Scientist-v2 | https://github.com/SakanaAI/AI-Scientist-v2 | Full scientific discovery loop; agentic tree search. Going quiet — last push 2025-12-19 | 2026-08-20 | main |
| Meta-Harness | https://yoonholee.com/meta-harness/ | Agentic outer-loop reading execution traces | 2026-08-20 | — |

## Swarm / Distributed

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| HKUDS/ClawTeam | https://github.com/HKUDS/ClawTeam | Leader + specialized workers; multi-GPU parallel | 2026-08-20 | main |
| autoresearch-at-home | https://github.com/mutable-state-inc/autoresearch-at-home | Distributed SETI@home-style autoresearch | 2026-08-20 | main |

## Claude Code Specific

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| drivelineresearch/autoresearch-claude-code | https://github.com/drivelineresearch/autoresearch-claude-code | Pure Claude Code skill port | 2026-08-20 | main |
| armgabrielyan/autoloop | https://github.com/armgabrielyan/autoloop | Agent-agnostic bounded-experiment loop | 2026-08-20 | main |
| frankbria/ralph-claude-code | https://github.com/frankbria/ralph-claude-code | Wrapper with dual-condition exit + circuit breaker | 2026-08-20 | main |

## Research Patterns

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| stanford-oval/storm | https://github.com/stanford-oval/storm | STORM/Co-STORM multi-perspective research. Dormant: last push 2025-09-30, v1.1.0 from 2025-01-23 | 2026-08-20 | v1.1.0 |
| dzhng/deep-research | https://github.com/dzhng/deep-research | Minimal recursive depth+breadth implementation | 2026-08-20 | main |
| bytedance/deer-flow | https://github.com/bytedance/deer-flow | **No longer a deep-research report generator.** v2.0.0 (2026-06-25) is a ground-up rewrite into a general persistent-agent harness; the STORM-shaped pipeline survives only on the frozen `main-1.x` branch | 2026-08-20 | v2.0.0 |
| assafelovic/gpt-researcher | https://github.com/assafelovic/gpt-researcher | Parallelized plan-and-solve: static planner decomposes, concurrent retrieval agents execute | 2026-08-20 | master |
| langchain-ai/open_deep_research | https://github.com/langchain-ai/open_deep_research | LangChain reference deep-research implementation | 2026-08-20 | main |
| Deep Researcher Reflect Evolve | https://arxiv.org/abs/2601.20843 | Sequential refinement with Global Research Context | 2026-08-20 | — |
| stanford-oval/DataSTORM | https://github.com/stanford-oval/DataSTORM | STORM successor by lineage (built on `knowledge_storm/`), scoped to structured-database research. Created 2026-08-06, 1 star — new, not established | 2026-08-20 | main |
| DataSTORM paper | https://arxiv.org/abs/2604.06474 | Tree search posing sub-questions answered by generated SQL; SOTA on InsightBench (+19.4% insight recall, +7.2% summary) | 2026-08-20 | 2026-04-07 |
| AREX | https://arxiv.org/abs/2607.21461 | Inner evidence-gathering loop + outer constraint-wise self-audit of the provisional answer. Grounds Mode 2's Audit step | 2026-08-20 | 2026-07-23 |
| Inference-Time Scaling of Verification | https://arxiv.org/abs/2601.15808 | Deep-research failure taxonomy (5 categories / 13 sub); rubric-guided DeepVerifier beats LLM-as-judge by 12-48% F1 | 2026-08-20 | 2026-01-22 |
| From Fluent to Verifiable | https://arxiv.org/abs/2602.13855 | Auditable Autonomous Research standard: provenance coverage/soundness, contradiction transparency, audit effort | 2026-08-20 | 2026-02-14 |
| Towards Verifiable Multimodal Deep Research (Ptah) | https://arxiv.org/abs/2605.29861 | Plan-research-write with a dedicated verifier agent as an acceptance gate. NB: "Ptah" is the system name, not the arXiv title | 2026-08-20 | 2026-05-28 |
| DR3-Eval | https://arxiv.org/abs/2604.14683 | Five scoring axes for deep-research reports: recall, factual accuracy, citation coverage, instruction following, depth | 2026-08-20 | 2026-04-16 |
| QUEST | https://arxiv.org/abs/2605.24218 | Open-weight 2B-35B deep-research agent models trained on synthetic rubric-tree-verified tasks. Model, not harness | 2026-08-20 | 2026-05-22 |
| EverMind-AI/Raven | https://github.com/EverMind-AI/Raven | Self-improving harness exposing a `deep_research` tool with cross-session memory. Fastest-growing new entrant; watch-only | 2026-08-20 | main |
| lajosdeme/mole | https://github.com/lajosdeme/mole | Deep research with an enforced step/token budget and quote-level verification | 2026-08-20 | main |
| LearningCircuit/local-deep-research | https://github.com/LearningCircuit/local-deep-research | Local-first deep research, 10+ search backends incl. arXiv/PubMed | 2026-08-20 | main |

## Reward Hacking & Safety

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| METR: Reward Hacking | https://metr.org/blog/2025-06-05-recent-reward-hacking/ | o3 rewrote scoring code in 25% of runs | 2026-08-20 | 2025-06-05 |
| Nick Oak: Tennis XGBoost | https://nickoak.com/posts/tennis-xgboost-autoresearch/ | Reward hacking case study | 2026-08-20 | — |
| Langfuse: Cautionary Tale | https://langfuse.com/blog/2026-03-24-optimizing-ai-skill-with-autoresearch | Score gained while safety gates removed | 2026-08-20 | 2026-03-24 |
| Adversarial Hacker-Fixer Loops | https://arxiv.org/abs/2606.08960 | 16% of environments across 5 benchmarks hackable from the task description alone; KernelBench attack success 62% -> 0% after verifier patching | 2026-08-20 | 2026-06-08 |
| Self-Authored Verification Is Unreliable | https://arxiv.org/abs/2607.24300 | Names the verifier-deployment gap: self-scored improvement stays high while real performance degrades. Proposes SEAL, a sealed external verifier | 2026-08-20 | 2026-07-27 |

## Benchmarks for the Loop Itself

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| PERFOPT-Bench | https://arxiv.org/abs/2607.07744 | Coding agents on the full profile→optimize→verify workflow. Harness choice changes the same LLM's speedup profile; large gains often come from shortcut exploitation; cross-session summary externalization unlocks further gains | 2026-08-20 | 2026-07-08 |
| OPT-BENCH | https://arxiv.org/abs/2605.08904 | Iterative self-optimization, 20 ML + 10 NP-hard tasks, 19 LLMs. Base model capacity limits adaptability | 2026-08-20 | 2026-05-09 |
| SEAGym | https://arxiv.org/abs/2606.17546 | Evaluation environment for self-evolving agents (Terminal-Bench 2.0, HLE); shared epoch/batch protocol | 2026-08-20 | 2026-06-16 |
| PAST-Bench | https://arxiv.org/abs/2608.04003 | Retained-experience gains are real but uneven across capabilities and models — validate carryover, don't assume it | 2026-08-20 | 2026-08-04 |
| Recursive Self-Improvement (survey) | https://arxiv.org/abs/2607.07663 | ~1,250-paper survey building a verification-reliability hierarchy; every loop's evaluator choice is a claim about substituting for human judgment | 2026-08-20 | 2026-07-08 |

## Mechanisms Worth Borrowing

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| jmilinovich/goal-md | https://github.com/jmilinovich/goal-md | GOAL.md pattern — agent constructs the fitness function before optimizing; independent arrival at Mode 3's premise | 2026-08-20 | main |
| ArmanJR-Lab/autoautoresearch | https://github.com/ArmanJR-Lab/autoautoresearch | "Director" injects arXiv/reasoning-model novelty into a stalled loop; baseline-vs-director stall analysis | 2026-08-20 | main |
| tonitangpotato/autoresearch-engram | https://github.com/tonitangpotato/autoresearch-engram | Persistent cross-session memory, frequency-weighted retrieval | 2026-08-20 | main |
| sentient-agi/EvoSkill | https://github.com/sentient-agi/EvoSkill | Evolves reusable skills from failed trajectories; Claude Code / Codex / OpenCode / OpenHands / Goose | 2026-08-20 | main |
| Rehearse | https://arxiv.org/abs/2607.27687 | Confidence cliff in autoresearch loops: judge selective accuracy 82.8% -> 56.9% as changes accumulate, restored to 83.5% by comparing candidates before execution. Grounds HYPOTHESIZE | 2026-08-20 | 2026-07-30 |

## Eval-Driven Development

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| Anthropic: Agent Evals | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | Capability vs regression evals (pub. 2026-01-09) | 2026-08-20 | 2026-01-09 |
| DSPy | https://dspy.ai/ | Programmatic prompt optimization. **GEPA is now the lead optimizer**; MIPROv2 (Bayesian surrogate/TPE) demoted to secondary | 2026-08-20 | — |

## Curated Lists

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| webfuse-com/awesome-autoresearch | https://github.com/webfuse-com/awesome-autoresearch | 100+ projects organized by category. Transferred from `alvinreal/` — old URL redirects, so probe `full_name`, not HTTP status | 2026-08-20 | main |
| WecoAI/awesome-autoresearch | https://github.com/WecoAI/awesome-autoresearch | Includes optimization traces | 2026-08-20 | main |

## Production Results

| Source | URL | What it contains | Last verified | Pinned |
|--------|-----|------------------|---------------|--------|
| SkyPilot: Scaling Autoresearch | https://skypilot.ai/blog/scaling-autoresearch/ | 16 GPUs, 910 experiments, $300. Domain rebranded from `blog.skypilot.co` | 2026-08-20 | — |
| Shopify Liquid PR #2056 | https://github.com/Shopify/liquid/pull/2056 | 93 commits, 53% faster parse+render, 61% fewer allocations. **Open, not merged** | 2026-08-20 | — |
| PJ Hoberman: 60 Experiments | https://blog.pjhoberman.com/autoresearch-60-experiments-production-search | Production search optimization | 2026-08-20 | — |
| Bennett: Weakest Not Shortest | https://arxiv.org/abs/2301.12987 | v4 2024: weakest (largest-extension) hypothesis maximises P(generalisation); MDL neither necessary nor sufficient. Grounds the Generality Criterion (SKILL.md Mode 1). | 2026-08-20 | v4 |

## Search Queries for Future Research

When checking for updates, these queries have been productive:

```
autoresearch Claude Code skill 2026
karpathy autoresearch latest
"ICLR 2026" agent autoresearch
reward hacking autoresearch
STORM multi-perspective research
```
