# Improvement backlog — lmcache-mp

## Open

- **Validate the hybrid-model claim on real hardware** (Dim 9, new 2026-07-21) —
  `SKILL.md` "Hybrid model status" section. The 2026-07-21 freshen pass inverted this
  skill's central guidance from "MP does NOT support hybrid models" to "supported",
  on the strength of two pieces of evidence: upstream's published recipe page
  (`docs/source/mp/hybrid_models.rst` at tag v0.5.1) and a source-level check that
  `LMCacheMPConnector` subclasses `SupportsHMA`
  (`lmcache/integration/vllm/lmcache_mp_connector.py:512`). **No local run backs it.**
  Complicating the picture: tracker #2845 is still open, and #3106 shows an active
  2026-07-17 report of a multi-object-group `Size mismatch` on DeepSeek-V4-Pro. Not
  applicable in one edit — needs a GPU session serving a Mamba/GDN hybrid (Qwen3.5)
  through an MP server end-to-end, including the unified-block-size `N` derivation
  and an A/B of `--separate-object-groups`. Until then the section is upstream-doc
  authority, not lab-verified.

- **Re-run verify-bundling.sh against a v0.25.1 / lmcache 0.5.1 image** (Dim 9) —
  `scripts/verify-bundling.sh` + the bundling table in `SKILL.md` ("Image bundling"
  section, ~lines 53-67) and `references/sources.md`. The freshen pass updated the
  version anchors to vLLM v0.21.0 + LMCache v0.4.5 but could NOT execute the script
  in this environment. Carried forward and re-scoped on 2026-07-21: the anchors are
  now vLLM v0.25.1 + LMCache v0.5.1, and the gap is five vLLM minors wide. Only the
  v0.19.1 floor table is evidence-backed. Run the script and replace/extend the
  bundling table when an environment with working Bash + Docker is available; expect
  nixl 1.3.0 (vLLM's exact pin) and lmcache ≥ 0.5.x.

- **Version-compat matrix triplication** (Dim 6) — `SKILL.md` version-gate table
  (~line 45), `SKILL.md` pitfall #3 ParallelStrategy table (~line 157), and
  `references/troubleshooting.md` version-compatibility matrix (~line 57). The same
  vLLM↔lmcache pin appears in three places. Not applied in one iteration: each copy
  is load-bearing in its own context (the pitfall table sits next to the ImportError
  it explains; the version-gate is the first-check reference; troubleshooting is the
  triage entry point). Collapsing to one + pointers would trade a small Dim 6 gain
  for a Dim 4 (actionability) loss from indirection, so the net metric does not
  improve. Revisit only if a future restructure consolidates the version surface.

## Resolved this pass (2026-07-21)

Freshen pass — evidence via `gh release view`, `gh issue view`, and `git show <tag>:<path>`
against local LMCache and vLLM clones:

- **Inverted the skill's central claim (Dim 9).** "LMCache MP does NOT support hybrid
  models" → supported as of the 0.5 line, with the upstream validated-model table
  (Gemma 3/4, gpt-oss, Qwen3.5/3.6 GDN, DeepSeek-V4-Flash, GLM 5.1/5.2, MiniMax-M3),
  the unified-block-size `N` derivation procedure, and `--separate-object-groups`.
  Propagated to the frontmatter `description`, troubleshooting matrix, and the
  #2845 entry (reframed as bookkeeping lag, not a blocker). Flagged for lab
  validation under Open.
- **Reframed pitfall #1 (Dim 4/9).** `--disable-hybrid-kv-cache-manager` is no longer
  a requirement but a symptom that the external lmcache import failed and vLLM fell
  back to its repo-local connector. Removed the flag from the quick-start, both
  deployment recipes, and the decision tree.
- **Version drift.** vLLM v0.21.0 → **v0.25.1**, LMCache v0.4.5 → **v0.5.1**, operator
  **v0.1.1 → v0.5.0** (numbering jumped; RC v0.5.1rc1 exists — noted as an RC).
  Added the v0.23.0 HMA-by-default gate row and the 0.5.0 rename list
  (`MPCacheEngine`→`MPCacheServer`, `GPUKVFormat`→`EngineKVFormat`, …), which
  invalidates old greps.
- **New capabilities documented**: operator webhook auto-injecting the `LMCacheEngine`
  connection into vLLM pods, `hostNetwork` CRD field, optional privileged DaemonSet;
  L2-adapter additions (Aerospike, Valkey per-key TTL, TurboQuant serde, runtime
  adapter registration, Device-DAX L1 overflow, AMD `hipFile` GDS L1,
  `disk_io_threads`).
- **Bug states**: vLLM #40040 open (2026-07-17); LMCache #2942 open but stale-flagged
  2026-06-29 — recorded as "stale ≠ fixed"; #3106 open and active.

## Resolved earlier (2026-05-28)

- Bumped version anchors to current stable vLLM v0.21.0 + LMCache v0.4.5 across the
  version-gate table, pitfall #3 matrix, and troubleshooting matrix; kept v0.19.1 as
  the verified-floor bundling example (Dim 9).
- Added the LMCache K8s Operator (`operator-v0.1.1`) pointer to the Kubernetes
  section and External references; kept hand-rolled YAML as the manual alternative
  (Dim 5).
- Refreshed the hybrid-model PR wording in SKILL.md and troubleshooting.md:
  LMCache#2879 closed-unmerged (2026-05-21), vLLM#38261 still open, Qwen3.5/3.6
  hybrids still unsupported per #2845 (2026-05-22); kept the do-not-recommend
  conclusion (Dim 9).
- Added the reconnect-after-LMCache-restart note (LMCache 0.4.5 / #3208) to the
  troubleshooting reachability row, correcting the orphaned-pods assumption (Dim 5).
- Added one-line entries for the v0.4.5 `raw_block` and RESP/Redis-Valkey L2 adapters
  to `references/l2-storage.md` (Dim 5).
- Trimmed the frontmatter `description` (~1100 → ~740 chars) and tightened
  `when_to_use`, bringing combined description+when_to_use under the 1536-char listing
  cap so the defer-to clauses (vllm-caching / nvidia-nixl / sglang-hicache) survive
  truncation (Dim 1).
- Prepended a table of contents to `references/deployment.md` and
  `references/l2-storage.md` (both >100 lines) for partial-read navigation (Dim 2).
- Rebuilt `references/sources.md` with a dated per-URL verification table stamped
  2026-05-28; noted that the v0.21/0.4.5 bundling table was not re-captured (Dim 9).
