# Improvement backlog — vllm-speculative-decoding

Work-not-done log from skill-improver passes. `## Open` = issues attempted as a
hypothesis but not applicable in one atomic iteration. `## Resolved this pass` =
changes a metric actually registered.

## Resolved — 2026-07-21 (freshen, v0.21.0 -> v0.25.1)

Closed the audit the 2026-05-29 pass deferred ("Version-gate table caps at
v0.19 — audit v0.20/v0.21/v0.22 release notes for new spec-dec gates"). Six
minors, not three.

- **A cited construct moved out of its file — not another line-number drift.**
  The aux-hidden-states allowlist had been re-pinned twice (818-833 →
  895-909). At v0.25.1 there is **no list in `config/speculative.py` at all**:
  support is now the `SupportsEagle3` capability interface, checked by
  `supports_eagle3(model)` in `eagle3_utils.py`, with models declaring layers
  via `get_eagle3_aux_hidden_state_layers()`. The user-facing question changed
  shape — "is my model in the list" became "does the model class implement the
  interface". **When a line range drifts twice, check whether the construct
  still lives there rather than re-pinning a third time.**
- **The same-tokenizer rule is no longer unconditional.** TLI (#38174, merged
  2026-07-02, v0.25.0) implements Token-Level Intersection spec-dec for
  target/draft pairs with different but *overlapping* vocabularies. Scoped the
  rule in all three places it was stated flatly, with two caveats attached:
  vocabularies must actually overlap, and acceptance behaviour on mismatched
  pairs is uncharacterised here — measure it.
- **Enum 11 -> 13 methods:** `custom_class` (callable proposer, #39487,
  v0.22.0) and `dspark` (#46995, v0.25.0). `RejectionSampleMethod` also gained
  `block` (#46781). `MTPModelTypes` now 20 aliases. Frontmatter count updated.
- **Security item, a first for this skill:** #44744 (v0.24.0) fixes a **remote
  DoS via invalid recovered-token reinjection in speculative decoding**.
  Added to the version-gate table with an explicit "upgrade if reachable" note.
- **Version-gate table extended v0.19 -> v0.25.0** with twelve rows, including
  thinking-budget support (#34668), independent drafter attention backend
  (#39930), Dynamic SD (#32374, CUDA-graph-compatible via #45953), and DFlash's
  maturation well past its v0.19 debut (CPU #44029, backend selection #46770,
  FlashInfer #43081).

**Not re-probed:** the four original PRs (long-merged, gates unchanged),
ArcticInference, the yuhuili checkpoint, and the training-data recipe survey.

## Resolved — 2026-08-11 (freshen, v0.25.1 -> v0.27.1)

- **TLI was documented as a capability but never as a configuration.** The
  2026-07-21 pass correctly retired the unconditional same-tokenizer rule, but
  never named the flag. TLI is **opt-in**: `use_heterogeneous_vocab: true`
  inside `--speculative-config`. Without it,
  `verify_equal_vocab_size_if_draft_model()` still runs and rejects exactly the
  pair the feature exists to allow. It also carries two hard `ValueError`s —
  `method` must be `draft_model`, and `draft_sample_method` must be `greedy`.
  **All three facts were already true at v0.25.1.** *Lesson: a release note
  tells you a capability exists; only the config dataclass tells you how to
  spell it. Read the dataclass.* Fixed in SKILL.md pitfall 7, the version-gate
  row, and `methods.md`.
- **`kv_cache_dtype` inside `--speculative-config`** (#48787, v0.26.0) — the
  drafter can now hold a KV dtype independent of the target's; unset inherits.
  Found by diffing the whole `SpeculativeConfig` field set v0.25.1 -> v0.27.0,
  which showed it was the *only* field added. That diff is now in the
  re-verification recipe.
- **`sample_from_anchor`** (#48639, v0.27.0) — a **checkpoint** field, not a CLI
  flag, for DFlash and DSpark. Default `False` means a `block_size = N` drafter
  yields **N-1** speculative tokens. Explains a measured drafts-per-step one
  below the checkpoint card without it being a bug.
- **Quantized DSpark Markov heads** (#50424, **v0.27.1**, the release's sole
  change) — `DSparkMarkovHead.markov_w2` now forwards `quant_config`, so W4A16
  incl. `weight_scale_2` loads normally. The skill made **no** claim that the
  head must be unquantized, so nothing was retracted; the operator-facing
  consequence (on <= v0.27.0 the head loads unquantized whatever the checkpoint
  says, costing drafter VRAM) went into pitfall 8.
- `MTPModelTypes` 20 -> **22**: **Kimi K3** and **Inkling** now ship native MTP
  heads. Method-selection row 1 and `mtp.md`'s table updated — the latter had
  also been missing `mimo_v2_mtp`, `minimax_m3_mtp`, `bailing_hybrid_mtp`,
  `gemma4_mtp`, `hy_v3_mtp` from earlier releases.
- **Re-verified without change:** the `SupportsEagle3` capability interface is
  still the mechanism at v0.27.0 (no allowlist returned to
  `config/speculative.py`); base method count still **13**, so the frontmatter
  count stands.

**Process hazard hit this run:** a concurrent git operation in the parent
session reverted the working tree mid-pass and discarded applied edits. They
were re-applied via a script with per-edit exact-match assertions. Verify edits
are on disk before reporting when a freshen pass shares a session with anything
that commits.

**Not re-probed, declared rather than assumed:** ArcticInference (now three
passes stale — the `suffix` method depends on it being installable, so it is
first up next pass), the yuhuili checkpoint, the EAGLE 3.1 blog, the
training-data recipe survey, and the four long-merged original PRs.

## Open

- **Deduplicate the BS>=32 / domain-mismatch caveat** — Dim 6 (Simplicity).
  Files: SKILL.md "wins/loses" L17-32 (canonical home), references/eagle3.md
  "When EAGLE-3 fails to pay off" L137-149, references/dflash.md "When DFlash is
  the wrong choice" L77-84, references/troubleshooting.md. The general caveat
  recurs across four files. The per-method "when X fails" restatements in
  eagle3.md and dflash.md carry method-specific falloff data (DFlash falls off
  faster than vanilla EAGLE-3; EAGLE-3 chat-tuned AL ~3→~2), so they are not pure
  duplicates and cannot be deleted wholesale — the dedup should collapse the
  *generic* statement to SKILL.md and leave only the method-specific delta in the
  references, which is a multi-file restructure (>1 atomic edit). Could not be
  applied this pass: the tool channel returned empty for every Read of
  troubleshooting.md, so its exact text could not be confirmed and a blind Edit
  would risk corruption.

## Resolved this pass

- Fixed aux_hidden_states allowlist line-anchor drift 818-833 → 895-909 in
  references/eagle3.md L27 and references/dflash.md L41 (Dim 8 — matches
  SKILL.md/methods.md; sources.md row 15 had already claimed this fixed).
- Added EAGLE 3.1 note (vLLM blog 2026-05-26) to references/eagle3.md after the
  P-EAGLE section (Dim 9 / Dim 5 — captures newest in-scope EAGLE feature).
- Re-stamped sources.md "vLLM releases" row from stale "v0.20.0 one day ago" to
  v0.21.0 stable / v0.22.0rc as of 2026-05-29; added an EAGLE 3.1 blog row; both
  stamped Last verified 2026-05-29 (Dim 9).
- Trimmed two near-duplicate implicit triggers ("faster inference", "higher
  tok/s") from SKILL.md when_to_use — subsumed by retained "speed up decode" /
  "can we get more tokens/sec"; widens listing-cap headroom (Dim 1 / Dim 6).
