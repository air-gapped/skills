# Gemma 4 31B — unmeasured mechanisms and open bench questions

Load when explaining the TP=1-vs-TP=2 curve against another model, or when
planning a follow-up bench. Nothing here is a measured attribution; do not
present it as one.

## Why Gemma 4 31B AWQ has a different TP curve than gemma-3-27B-fp8

An existing prod running gemma-3-27B-fp8 may favour TP=2 over TP=1 or
TP=4 on H100/H200 — that experience is correct for that model. Gemma 4
31B AWQ-4bit shows a different curve (TP=1 wins on short-ctx per-H100
efficiency). The four reasons below are plausible mechanisms, not
measured attributions — confirming each needs a one-variable-at-a-time
bench (see "Bench questions not yet measured" below).

1. **AWQ-4bit weights are smaller than fp8** (4 bits vs 8 bits, ~16 GB vs
   ~27 GB). Less benefit from TP weight-splitting since weights already
   fit comfortably on one H100 with KV headroom.
2. **TRITON_ATTN backend has different TP scaling than FLASH_ATTN**.
   gemma-3 uses FLASH_ATTN (homogeneous head_dim); Gemma 4 ran TRITON_ATTN
   on the 0.20.0 audit — different per-rank communication characteristics.
3. **EAGLE3 spec-dec compute scales asymmetrically with TP**. The drafter
   weights are also sharded across TP ranks; for a small drafter (4.5 GB
   BF16 split across 2 cards) the per-rank compute is small, but the
   draft-verify cycle adds extra all-reduces that hurt at TP=2.
4. **31B vs 27B**: 31B has more layers + hidden dim → larger weight
   bytes per token; HBM bandwidth saturation knee shifts with weight
   size.

## Bench questions not yet measured

The following questions need a follow-up bench:

1. **`num_speculative_tokens=2` vs 3 on real-text**. At higher real
   acceptance (50-80%) k=3 may pay off but at low acceptance k=2 might
   win. Untested on Gemma 4.
2. **No-spec-dec baseline**. Operator brief was EAGLE3-only; if real
   acceptance drops below ~30% on prod traffic, no-spec might be
   competitive on aggregate throughput at high concurrency.
3. **Which WNA16 kernel ran.** The cyankiwi quant is compressed-tensors;
   read the `Using <Kernel> for CompressedTensorsWNA16` startup line. On
   SM90, v0.32.0 ranks Humming ahead of Marlin (#56997; order Machete →
   Humming → Marlin), so the kernel can differ from the 0.20.0 audit's.
4. **TP=4 hypothetical**. Would need a 4-H100 SKU. The bandwidth-bound
   knee should shift again, but TP communication overhead grows
   non-linearly past TP=2.
5. **Real-text long-context**. The 16K/1K random benchmark is
   conservative; ShareGPT-long or NuminaMath would give more realistic
   acceptance + throughput.
