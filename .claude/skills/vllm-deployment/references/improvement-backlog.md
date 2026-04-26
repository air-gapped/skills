# vllm-deployment — improvement backlog

## Open

### Trigger probe (`probe-trigger.py`) returned all-zero rates — measurement broken (Dim 1)

- file: `~/.claude/skills/skill-improver/scripts/probe-trigger.py`
- evidence: 2026-04-25 trigger-mode run reported `trigger_rate: 0.00` for every query in both directions (should-trigger AND should-NOT-trigger). Both baseline + iter-1 produced identical zero-zero results across 18 queries. Either `claude -p` headless mode does not auto-invoke skills the way the probe assumes, or the synthetic slash-command isn't being registered as an auto-loadable skill in -p mode.
- impact: trigger mode falls back to manual A/B per skill-improver `references/trigger-patterns.md` §"Fallback when claude -p is not available". This skill's frontmatter was rewritten judgment-based (using documented user-failed phrasings from the 2026-04-25 model-preflight session as gold should-trigger queries) rather than via measurement loop.
- not skill-improver's job: probe is a skill-improver tool, not part of vllm-deployment.
- carry forward to skill-improver itself: investigate why `claude -p` + synthetic slash-command produces no skill invocation. Likely needs SDK-level inspection of how -p mode handles `.claude/commands/` registration vs auto-loadable skill listing.

### Eval set quality — needs more user-mined phrasings (Dim 1)

- file: `~/.claude/skills/vllm-deployment/references/trigger-evals.json`
- evidence: 2026-04-25 user pushback "these are such generic and boring sentences I would never use - I am much more a specialist". Initial eval was overly generic. Replaced mid-run with specialist-vocab eval, but only 18 queries — needs broader mining from this user's actual session transcripts across multiple model-preflight sessions.
- impact: even when probe works, low-quality eval = low-signal hill climb.
- action: next trigger-mode run should mine 2026-04-* session transcripts for actual user phrasings about deploy/manifest/cache/probe/HF_TOKEN/MoE/EP-DP/cold-boot.

### Sibling skill cross-cluster collision risk (Dim 1, T6 finding)

- evidence: "MTP1 working on Qwen3.6 — how do I add the spec-decode flag without restarting" — could fire vllm-deployment ("without restarting" = pod restart context) OR vllm-speculative-decoding (MTP). Marked should_trigger=false in eval but ambiguous in practice.
- impact: as vllm-deployment description gets pushier on operator-vocab, may steal triggers from sibling vllm-* skills (vllm-performance-tuning, vllm-speculative-decoding, vllm-caching, vllm-quantization).
- action: cross-cluster trigger-mode batch run after probe is fixed; check for over-trigger steal across all 14 vllm-* skills in one pass.

### Body still feature-list shaped — body inversion deferred (Dim 2)

- file: SKILL.md body
- evidence: body opens with "This skill is a pointer map…" + decision-guide table that's vendor-named (production-stack, llm-d, AIBrix). Body rewrite to lead with operator workflow ("audit → cache mount → HF_TOKEN → probes → serve_args → spec-decode → bench") deferred — out of scope for trigger mode.
- impact: post-trigger, when skill IS loaded, body still requires operator to know vendor names to navigate.
- action: separate `improve` mode iteration on body structure once trigger reliability confirmed.

## Resolved this pass

- 2026-04-25: rewrote `description` to lead with "Use this skill when…" + operator-vocabulary triggers (lab cluster perf, /root/.cache cache, HF_TOKEN, ep2 dp2, MoE, --enforce-eager, cold-boot, configmap mount, manifest review). Front-loads the 3 user-failed queries from this session as documented triggers. Description: 1014 chars (10 headroom from 1024 cap). when_to_use: 440 chars. Combined: 1454 chars (82 headroom from 1536 listing cap). Vendor keyword tail removed from when_to_use — already in description; saves cap budget.
- 2026-04-25: created persistent `references/trigger-evals.json` with 18 queries (12 train + 6 test) sourced from session transcript user-failed queries plus specialist-vocab paraphrases plus sibling-skill adversarials. Verda + spec-decode + quant + scout + jinja queries marked should_trigger=false to test scope discipline.
