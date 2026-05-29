# Improvement backlog — lmcache-mp

## Open

- **Re-run verify-bundling.sh against a v0.21.0 / lmcache 0.4.5 image** (Dim 9) —
  `scripts/verify-bundling.sh` + the bundling table in `SKILL.md` ("Image bundling"
  section, ~lines 53-67) and `references/sources.md`. The freshen pass updated the
  version anchors to vLLM v0.21.0 + LMCache v0.4.5 but could NOT execute the script
  in this environment (Bash output channel was unavailable mid-pass). The bundled
  versions for the v0.21 image (lmcache, nixl, mooncake) remain unverified; only the
  v0.19.1 floor table is evidence-backed. Run the script and replace/extend the
  bundling table when an environment with working Bash + Docker is available.

- **Version-compat matrix triplication** (Dim 6) — `SKILL.md` version-gate table
  (~line 45), `SKILL.md` pitfall #3 ParallelStrategy table (~line 157), and
  `references/troubleshooting.md` version-compatibility matrix (~line 57). The same
  vLLM↔lmcache pin appears in three places. Not applied in one iteration: each copy
  is load-bearing in its own context (the pitfall table sits next to the ImportError
  it explains; the version-gate is the first-check reference; troubleshooting is the
  triage entry point). Collapsing to one + pointers would trade a small Dim 6 gain
  for a Dim 4 (actionability) loss from indirection, so the net metric does not
  improve. Revisit only if a future restructure consolidates the version surface.

## Resolved this pass

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
