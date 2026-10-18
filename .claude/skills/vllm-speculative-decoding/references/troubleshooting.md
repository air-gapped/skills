# Troubleshooting spec-dec

Load when an operator reports "spec-dec isn't paying off," "AL is low," "it
used to work and now doesn't," or "this worked in benchmarks but not prod."

## Decision tree for low-throughput spec-dec

Start with the two numbers:
- AL (mean acceptance length) — from
  `1 + rate(num_accepted_tokens_total)/rate(num_drafts_total)`
- Accepted tok/s — from `rate(num_accepted_tokens_total)`

Four regimes:

### 1. AL low (<2.0), BS small

The drafter is guessing badly. Causes, in order of likelihood:

1. **Tokenizer mismatch.** Verify drafter and target share a tokenizer — *or*
   that you are deliberately on **TLI** (v0.25.0+, PR #38174), which supports
   different-but-overlapping vocabularies by design. If TLI is not in use, a
   mismatch is a bug. For
   EAGLE-3, the checkpoint is tied to a specific target tokenizer — swapping
   target (e.g., an instruction-tuned variant with added chat tokens) without
   swapping checkpoint breaks it.
2. **Domain mismatch.** Stock EAGLE-3 checkpoints are chat-tuned. Production
   traffic that's code-heavy, SQL-heavy, JSON-heavy, or agentic drops AL 30%
   or more. Measure AL on a representative workload sample before deployment.
3. **Temperature drift.** Sampling with high temperature (>0.9) lowers AL
   mechanically — at high temp the target's next-token distribution is
   flatter, so the drafter's argmax less often matches target's sampled token.
   Not a bug; an inherent property.
4. **Quantization mismatch.** INT4 drafter + FP8 target usually survives;
   INT4 drafter + BF16 target or vice-versa is worse. Match where possible.
5. **Corrupt checkpoint.** Re-download and re-hash. Seen occasionally with
   partial HF cache transfers.
6. **Wrong method for model.** Model ships MTP heads but EAGLE-3 is running
   instead — the MTP path is better. Check `vllm/config/speculative.py`:
   method auto-detection in `SpeculativeConfig.__post_init__` (L1326-1366 at
   v0.32.0) and the per-arch `model_type` remap in `hf_config_override`
   (L661-1073).

### 2. AL OK (>2.5), throughput not improving

Spec-dec is accepting tokens but wall-clock isn't budging.

1. **BS too high.** The prototypical "spec-dec hurts at scale" regime. Target
   is compute-bound, drafter overhead is no longer hidden. Lower BS, or gate
   spec-dec to the low-concurrency tier.
2. **Async scheduling off.** Default since v0.14.0; can be disabled
   explicitly. Re-enable. Zero-bubble variant in v0.19.0 is further gain.
3. **`enforce_eager: true`.** Kills CUDA graphs. No spec-dec path forces it
   (the old DeepSeek-V3.2 MTP forcing is gone by v0.30.0) — remove it.
4. **Drafter CUDA graph cache miss storm.** Logs show repeated graph capture.
   Raise `--max-num-seqs` batching headroom, or set
   `-cc.cudagraph_mode=PIECEWISE` if full-graph capture is unstable.
5. **Draft TP != Target TP.** Would have failed at engine start on
   `draft_model` (hard error in `v1/spec_decode/draft_model.py::_raise_if_draft_tp_mismatch`),
   but `mlp_speculator` forces draft TP=1 when `draft_tensor_parallel_size` is
   unset. On an 8-way target the TP=1 drafter becomes a serial bottleneck.
6. **Verification bottleneck on the target** — rare, but if the target's
   sampler is unusually slow (e.g., structured output with a complex
   grammar), verification dominates. Test without structured outputs.

### 3. AL good, throughput good, but P99 latency regressed

Wall-clock gain on average, but tail worse.

1. **Stale tree-speculation config.** Tree attention was removed in v0.21.0
   (#42121); a leftover `speculative_token_tree` key is now rejected by config
   validation (extra fields forbidden). Delete it — chain drafting is the only mode.
2. **Drafter graph capture on the critical path.** First N requests after
   restart pay the graph-compile cost. Send warm-up traffic before
   production cutover (`vllm serve` has no warm-up-requests flag).
3. **Rejection tail on position-k tokens.** High k amplifies tail. Drop
   `num_speculative_tokens`.
4. **Chunked-prefill interaction with EAGLE edge case** (historical, fixed in
   v0.11.1 #26263). Upgrade if pinned to an older build.
5. **LoRA + EAGLE without the CUDA-graph specialisation** (pre-v0.11.1
   #28318). Upgrade.

### 4. AL zero, no spec-dec happening

Metrics show `num_drafts_total` stuck at 0 despite `--speculative-config`
passed.

1. **Config validation silently disabled spec-dec.** Check engine start log
   for `SpeculativeConfig` warnings. Pre-v0.14.0 some unsupported param
   combinations silently turned spec-dec off; v0.14.0 (PR #31982) changed
   this to hard-error. Upgrade.
2. **Method detection failed.** Local checkpoint dir renamed to drop the
   `"eagle3"` / `"dflash"` substring → auto-detection fails. Set `method:`
   explicitly.
3. **Attention backend mismatch.** DFlash requires `flash_attn`; on Triton,
   DFlash silently can't schedule. Log should reveal this.
4. **Plugin missing.** `method: "suffix"` without `pip install
   arctic-inference` fails clearly at engine start. Check base-image build.

## Silent regressions after upgrade

Map symptom → likely cause:

| Symptom | Upgrade that likely caused it | Recourse |
|---|---|---|
| Engine hard-fails on startup where it used to succeed | v0.14.0 unsupported-params-now-error (PR #31982) | Remove the offending sampling param or update the config |
| AL dropped after upgrade | Stale checkpoint vs method renames (#25232 unified MTP aliases) | Switch to `method: "mtp"`; old names still work but log deprecation |
| "Multimodal not supported" error that didn't fire before | Strict MM / drafter compatibility checks in v0.15+ | Disable MM on drafter or use a MM-capable variant |
| Throughput dropped after v0.16 | Default changes to `parallel_drafting` or unified parallel drafting (#32887) | Re-benchmark with explicit `parallel_drafting: true/false` to find best |
| Multimodal target + Llama 4 / Mistral Large 3 EAGLE drafter fails in the first draft prefill (startup profile run) | v0.28.0–v0.31.x regression (#50417), fixed v0.32.0 (#57633) | Upgrade to v0.32.0 |
| ModelOpt NVFP4 DeepSeek-V4/V4.1 + DSpark/MTP: AL exactly 1.00, no error; only hint is `w1_weight_scale_2 must match w3_weight_scale_2` after draft load | Ignored MTP/DSpark experts not kept on MXFP4 — fixed v0.32.0 (#59655) | Upgrade to v0.32.0, or use the non-NVFP4 checkpoint |
| `draft_model` + `use_heterogeneous_vocab: true` dies with a device-side assert | v0.31.x put TLI on MRV2, which has no vocab mapping; fixed v0.32.0 (#59541) | Upgrade, or `VLLM_USE_V2_MODEL_RUNNER=0` |
| Pipeline-parallel spec-dec broken | PP + spec-dec only on MRV2 (v0.17+ #33960). If on V1 engine runner, PP disables spec-dec | Switch to MRV2 or disable PP |

## Interpreting engine log lines

On startup:
```
INFO ... SpeculativeConfig(method='eagle3', model='yuhuili/EAGLE3-LLaMA3.1-Instruct-8B', num_speculative_tokens=3, ...)
```
If absent, spec-dec wasn't enabled. Check the flag parsing.

During serve (every `log-stats-interval`):
```
SpecDecoding metrics: Mean acceptance length: 2.73, Accepted throughput: 12.40 tokens/s,
Drafted throughput: 15.10 tokens/s, Accepted: 744 tokens, Drafted: 906 tokens,
Per-position acceptance rate: 0.890, 0.760, 0.610, Avg Draft acceptance rate: 82.1%
```
AL 2.73 on k=3 chain is healthy for EAGLE-3 on chat. Mentally reconstruct
`positions_accepted / drafts` from the per-position list — 0.890, 0.760, 0.610
averages to 0.75, which matches `AL - 1 = 1.73` (the `+1` is the bonus
target token that always gets accepted).

## When to disable spec-dec

Not every workload benefits. Consider disabling (or gating to a replica
subset) when:

- Prefill-dominated SLO (long prompts, short outputs)
- Single-token endpoints (classification, yes/no tool routing)
- Embedding / reward scoring (no autoregressive decode)
- Sustained BS ≥ 32 on all traffic with no low-concurrency tier
- Reproducibility-critical evals (logprob stability not guaranteed with
  spec-dec)

## When the bug is not yours

Spec-dec has shipped a flurry of bugfixes through v0.19. On a build older
than v0.18.x, upgrade is usually the answer to an unexpected bug before
deeper debugging. See SKILL.md "Critical version gates" for
the minimum-version-per-feature table.

If a new bug appears on the latest release, reproduce with
`examples/features/speculative_decoding/spec_decode_offline.py` (the canonical minimal repro the
maintainers trust) and file against `vllm-project/vllm` with that script.
