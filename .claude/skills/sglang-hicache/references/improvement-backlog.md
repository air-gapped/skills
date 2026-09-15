# Improvement Backlog — sglang-hicache

Prior skill-improver runs and ceiling findings.

## Resolved — 2026-09-15 (hicache-doctor.sh shipped)

- **Shipped `scripts/hicache-doctor.sh`.** The entry deferred it as
  "author-judgment-dependent on which log sources to scan (systemd / docker /
  kubectl)" and said to "skip until the operator workflow is more concrete".
  That is a judgement, and the answer is just *all three*: the script
  auto-detects in the order an operator is most likely on, and `--systemd` /
  `--docker` / `--kubectl` / `--file` / `--stdin` override it.
- **Grounded in the real strings, not a guessed grep.** All three rewrite sites
  in `arg_groups/hicache_hook.py` were read at upstream `main` on 2026-09-15:
  "Kernel io backend does not support page first direct layout, switching to
  direct io backend", "Page first layout is not supported with direct IO
  backend, switching to page first direct layout", and the templated
  "switching to {layout} layout for {io_backend} io backend". **`switching to`
  is the invariant across all three**, so that is what the script matches —
  a pattern built from the specific messages would rot on the next rewrite rule.
- **Prints the resolved configuration as well as the rewrites**, because the
  rewrite line alone does not tell an operator what they ended up running.
- **Says what a clean result does and does not mean.** "No rewrites found" is
  reported as weak evidence — it covers the log window read, and both
  `journalctl -n 5000` and `docker logs` can have rolled past startup. Silent
  success here would be the same failure the script exists to catch.
- Exit 1 when a rewrite fired, so it drops into a post-deploy gate unchanged.
- The one-liner previously inlined in pitfall #3 stays; it is the zero-install
  version. This is the multi-source one the entry said was the remaining value.

## Resolved — 2026-09-15 (unguarded SWA fallthrough re-verified at v0.5.19)

- **The footgun stands, and it is wider than the three archs recorded.** Exactly
  one architecture has a guard keyed on hierarchical cache: `Step3p5ForCausalLM`,
  which under `if cfg.enable_hierarchical_cache` sets `swa_full_tokens_ratio = 1.0`
  and `disable_hybrid_swa_memory = True` in
  `python/sglang/srt/arg_groups/overrides.py`. All 21 other members of the
  hybrid-SWA set are unguarded. UnifiedTree-by-default (#27759) did not add guards.
- **The detection set grew from 8 architectures to 22**, so the blast radius grew
  with it: Llama-4, gpt-oss, Granite-SWA (×2), DeepSeek-V4 (×3), MiMo-V2 (×3),
  Step3p7, Gemma-4 (×3), Laguna, Mellum, MuseGlimmer (×2), Inkling (×2),
  UnlimitedOCR.
- **Gemma-3 is safe and Gemma-4 is not**, which is the likeliest operator mistake
  on the page. `gemma2_gemma3.py`, `exaone.py` and `olmo2.py` set
  `disable_hybrid_swa_memory = True` **unconditionally**, so those archs never
  enter the path — not comparable to a hicache-conditional guard.
- **Inkling cannot take the documented mitigation at all**: `models/inkling.py`
  asserts `not disable_hybrid_swa_memory`.
- **Mechanism located:** `arg_groups/hicache_hook.py`, the dedicated
  hierarchical-cache argument hook, contains no SWA handling whatsoever.
- **Citations repaired.** `model_config.py:1503-1515` and
  `server_args.py:1948-2030` are both dead — detection is now
  `is_hybrid_swa_model()` and the arg plumbing moved wholesale into
  `python/sglang/srt/arg_groups/`. Named functions rather than line ranges this
  time, since the refactor is what invalidated them.
- **Why this was not really blocked:** the entry said resolving it meant
  "re-reading the current scheduler routing and the guard list" — that is source
  reading against a local clone, i.e. work, not an absent thing. What *is* absent
  is the paired quality eval on Gemma-4 or gpt-oss with hicache on, and the
  `HiRadixCache`-doesn't-model-SWA half is still carried from the earlier pass
  unverified. The scope of this check is stated in both files rather than implied.

## Resolved — 2026-09-15 (freshen to v0.5.19)

- **The "unguarded SWA fallthrough" footgun is resolved for the three
  architectures the skill named, and the skill was telling operators to work
  around a problem they no longer have.** `cli-flags.md` said Llama4, GptOss and
  Gemma4 do NOT get SWA-aware handling and that the operator must pass
  `--disable-hybrid-swa-memory` or avoid hicache on them. Verified in source at
  tag **v0.5.19**: `is_hybrid_swa_model()`'s `hybrid_swa_archs` allowlist in
  `configs/model_config.py` contains `Llama4ForConditionalGeneration`,
  `GptOssForCausalLM` (via `SWA_SINK_ARCHS`) and all three `Gemma4*` entries.
  PR #27759 made hybrid models route through `UnifiedRadixCache` by default in
  v0.5.13, and **v0.5.19 made the unified tree the default for every model**.
- **The failure class narrowed rather than disappeared, and the rewrite says
  so.** The guard is an allowlist plus one opt-in (`hf_text_config.is_hybrid_swa`).
  A genuinely-SWA architecture in neither returns a plain `False` with no
  assertion, and its SWA layers are still cached as full attention. That is now
  framed as the thing to check for a new, custom or vendor-forked architecture.
- **The skill cited a symbol that no longer exists.** `_handle_hicache()` was
  removed from `server_args.py` by PR #38047 (merged 2026-09-06, after v0.5.19);
  the fields moved to `arg_groups/fields/memory.py` and the logic to
  `arg_groups/hicache_hook.py::handle_hicache()`, with the two rewrite rules
  named `resolve_layout_io_compatibility()` and
  `resolve_storage_layout_compatibility()`. Three call sites updated, and the
  line-range citations replaced with an instruction to grep the symbol.
- **`--hicache-storage-backend` had grown from 8 values to 11** at v0.5.19
  (`sim`, `shm` and `mori` beyond the documented set), with `npu_memcache` on
  `main` after the tag.
- **Two flag renames ship with no deprecated alias**, so an existing launch
  command fails outright: `--enable-deepep-waterfill` → `--enable-waterfill` and
  `--optimistic-prefill-retries` → `--optimistic-prefill-attempts`, both v0.5.16.
- **v0.5.18 moved every compiled-kernel cache under `SGLANG_CACHE_DIR`**, which
  costs one recompile on first boot and invalidates a mounted cache volume's
  path — recorded with the migration paths.
- Two open HiCache correctness bugs added (#39147 file-backend prefix
  intersection on hybrid pools; #39444 `write_through` eviction before backup
  completes), both narrow enough to plan around.

### Checked and still CORRECT — do not close these

- **The two stale-bot issues remain genuinely unfixed.** #21880 (file backend
  slow in containers) and #22757 (GLM5/DSA L3 crash on H20) were both closed by
  the inactivity bot, and #22757's candidate fix **PR #22120 was closed
  unmerged**. GitHub reports `stateReason: COMPLETED` for both, which does not
  distinguish a fix from an autoclose. The skill's decision to keep recording
  them as live risks was right and stays.

## Open


### Recipes for `simm` / `eic` / `dynamic` backends (carried 2026-05-29)

- **Dim:** 5
- **Where:** `references/recipes.md` would need 3 new recipe sections.
- **Why ceiling-bound:** these backends are listed in `references/storage-backends.md` but have no worked recipe — niche but documented. Adding sample configs requires probing the AIBrix / Volcengine / Scitix doc sites for proprietary env-var sets that may not be public. Defer until an operator request surfaces.
- **Score impact if resolved:** Dim 5 9→10 (~+1 total).


### Two stale-bot closures recorded as live risks (new 2026-07-21)

- **Dim:** 9
- **Where:** `SKILL.md` "Open bugs" (the stale-bot sub-table) and the corresponding
  `sources.md` rows for #21880 (`file` backend slow in containers) and #22757
  (GLM5/DSA L3 segfault on H20).
- **Why ceiling-bound:** both were closed by the inactivity bot (2026-06-18 and
  2026-06-14) with no linked fix — #22757 has an unconfirmed candidate PR (#22120),
  #21880's last substantive comment reproduced the problem. Closed-state alone is not
  evidence of a fix, so the skill now records them as live risks. Actually resolving
  them needs a measurement, not a probe: v0.5.15's CP-aware LRU eviction on the file
  backend (#26670) may have changed #21880's picture, and #22757 needs H20 hardware.
- **Score impact if resolved:** removes two hedged entries from the bug table.

## Resolved this pass (2026-07-21)

Freshen pass — evidence via `gh release view`, `gh issue view`, `gh pr view`, issue
timelines/comments, and the v0.5.15.post1 `server_args.py`:

- **Version drift (Dim 9).** v0.5.12.post1 → **v0.5.15.post1** (2026-07-14); three
  minors behind. Updated Versions, image tag, and sources.md.
- **The headline change: v0.5.13 #27759** — `HybridModel` (SWA/Mamba) launches HiCache
  via **UnifiedTree by default**. Added to Versions and to pitfall #4 as the leading
  bullet, with an explicit "re-benchmark after upgrade" warning since a config tuned
  on v0.5.11/v0.5.12 may take a different code path.
- **Flag surface (Dim 9).** `server_args.py` refactored to annotated dataclasses (old
  line-range citations dead). New choices documented: `write_through_selective`;
  io-backend default now `kernel`, plus `kernel_ascend`; mem-layout `page_first_kv_split`
  and `page_head`; storage-backend `mori`. Noted the adjacent `--enable-hisparse`
  subsystem so it isn't conflated with hicache.
- **Bug-state flips.** #19212 (`write_back` crash) closed **with a fix** 2026-05-24 via
  PRs #22592 + #23696 — pitfall #5 rewritten from "avoid" to "defensible experiment";
  #23429, #23457, #19737, #20529 also closed with fixes. #21880 and #22757 closed by
  the **stale bot** — split into their own table and kept as live risks. #22607 still
  open with its fix PR #22878 closed unmerged; **new #30760** (2026-07-10) reports the
  same prefetch `all_reduce` deadlock at TP=4 with no PP, which weakens the
  "`--pp-size 1` is sufficient" advice.
- **v0.5.14/v0.5.15 HiCache features** catalogued (int8 linear-attention checkpoint
  pool, hybrid-pool staged H2D kernel, asymmetric pool direct backend, MiMo-V2 HiCache,
  file-backend CP-aware LRU eviction, NIXL bucketed multi-dir layout + FILE cache
  cleaner, Mooncake group semantics, AMD UMBP tiered DRAM+SSD L3).
- **Cross-skill correction.** The skill's raison-d'être paragraph claimed vLLM
  tier-extension caching is "broken for the entire 2026 hybrid-attention lineup". That
  is no longer true (vLLM v0.21.0 native offload + HMA, v0.23.0 HMA-by-default,
  LMCache MP 0.5.x) and only the in-process `LMCacheConnectorV1` remains blocked.
  Corrected in SKILL.md, `hybrid-models.md`, and `migration-from-vllm-caching.md`,
  where the migration premise now carries a "upgrading vLLM is usually cheaper than
  migrating engines" caveat.

## Resolved earlier (2026-05-29)

Freshen (evidence: `gh release list` + `gh issue/pr view`, all probed 2026-05-29):

- **Domain Accuracy (Dim 9) — 6→8.** Version pin bumped v0.5.10.post1 → **v0.5.12.post1** (2026-05-26, isLatest; also v0.5.12, v0.5.11) across SKILL.md Versions + image tag and sources.md. The skill was 3 stable releases behind.
- **Dim 9 — SWA reclassification.** The load-bearing differentiator claim "SWA not yet available, wait for v0.5.11, PR #23391 still OPEN" was factually wrong. PR **#23391 merged 2026-05-06** (day-0 Gemma 4), issue **#23659 closed 2026-05-08** — both shipped in v0.5.11. Corrected in SKILL.md (description, Why-this-matters, pitfall #4, open-bug table → "Recently resolved" line), hybrid-models.md (arch-detection comment, support matrix SWA-proper row, mitigations, migration table, roadmap), troubleshooting.md (SWA fix), migration-from-vllm-caching.md (decision tree), storage-backends.md (mooncake/hf3fs rows).
- **Dim 9 — resolved-issue reclassification.** #16797 (Mooncake TTFT regression) **closed 2026-05-12**; #22572 / PR #23241 (3FS hybrid Mamba/DSA) **closed**, shipped v0.5.11. Updated in SKILL.md pitfall #7 + table, troubleshooting.md, storage-backends.md, sources.md.
- **Dim 9 — still-open confirmation.** Re-probed #22607 + #22878 (PP+HiCache) → **still OPEN**, did NOT make the v0.5.11/v0.5.12 cut; corrected the stale "until v0.5.11 lands" framing to "still open as of 2026-05-29" in SKILL.md pitfall #6 + table, troubleshooting.md, migration. Verified #23429/#23457/#21880/#19737/#22105/#20529/#22757 all still OPEN (no change). All re-probed sources.md rows stamped `Last verified: 2026-05-29`.

Improve loop (rubric-driven, keep/discard):

- **Simplicity (Dim 6) — 8→9.** Removed the two lowest-information duplicate rows (#22607, #19212) from the Open-bugs table; their root-cause-bearing prose lives in Critical pitfalls #6/#5. Replaced with a one-line cross-reference. No information lost.
- **Actionability (Dim 4) — 9→10.** Inlined the effective-layout verify command (`journalctl -u sglang | grep -iE 'switching to .* layout|...'`) into pitfall #3, turning the symptom-only auto-rewrite warning into a runnable step.
- **Trigger Precision (Dim 1) — kept-as-simplification.** Trimmed one redundant flag synonym (`storage-backend-extra-config`, already covered by the `--hicache-*` glob) from `when_to_use`; combined description+when_to_use 1488 → 1444 chars, buying headroom below the 1,536 listing cap so the tail defer-to-`vllm-caching`/`nvidia-nixl` clauses survive a shrunk dynamic budget. Equal trigger coverage, simpler.
- **Discard (logged).** Briefly added a "hybrid attention sglang cache" trigger phrase to `when_to_use`, then reverted — it duplicated the existing "sglang hybrid model caching" trigger and pushed back toward the char cap (opposite of the iteration goal).

## Resolved (2026-04-25)

- **Writing Style (Dim 3) — 8→10.** 2 second-person slips removed (iter 1): `references/cli-flags.md:64` and `references/troubleshooting.md:41`. Zero "you/your" remaining. Blind agent confirmed Dim 3 = 10/10.
- **Simplicity (Dim 6) — 8→9.** Consolidated SKILL.md "Why this matters" hybrid-attention duplication (iter 2). Net –7 lines.
- **Resource Quality (Dim 7) — 8→9.** Added `scripts/inspect-sglang-image.sh` (iter 3). Reads `lmsysorg/sglang:<tag>` Docker image config without pulling layers; reports CUDA, mooncake-transfer-engine / nixl-cu* / aibrix-kvcache / lmcache versions. Smoke-tested against `v0.5.10` — confirms mooncake + nixl-cu13 bundled, no aibrix or lmcache.
- **Domain Accuracy (Dim 9) — freshen findings.** Iter 4: PR #23391 (SWA support) and PR #22878 (Channel-B writing_check) re-classified as **OPEN** in SKILL.md, sources.md, troubleshooting.md, hybrid-models.md (skill had claimed merged 2026-04-24). Issue #23659 framing tightened — "fix path" now correctly says "v0.5.11 once PR #23391 merges (still OPEN as of 2026-04-25)". Mooncake-transfer-engine v0.3.10.post2 (released 2026-04-22) noted in sources.md Versions section.

### Score trajectory

| iter | self | blind | delta | status | description |
|------|------|-------|-------|--------|-------------|
| 0    | 88   | 92    | —     | baseline | first version drafted with rubric loaded upfront |
| 1    | 89   |       | +1    | keep   | 2 second-person → imperative |
| 2    | 90   | 95    | +1    | keep   | consolidate "Why this matters" hybrid-attention duplication |
| 3    | 91   |       | +1    | keep   | add `scripts/inspect-sglang-image.sh` (Docker image inspector) |
| 4    | 92   | **97** | +1   | keep   | freshen findings — PR #23391/#22878 re-classified OPEN, Mooncake post2 noted |

**Stop conditions met:** self 92/100, final blind **97/100**, no dim < 9 on blind. Run converged. Self-blind gap is +5 (blind higher) — no flagged dims, scores aligned. Remaining ceiling items (`hicache-doctor.sh`, niche-backend recipes) carried forward — author-judgment-dependent.

Blind trajectory 92 → 95 → 97 across iters 0/2/4 confirms each iteration produced a real, defensible gain measured by an independent agent.
