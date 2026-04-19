# NVIDIA ModelOpt — PTQ + speculative-decoding training

Canonical repo: [NVIDIA/TensorRT-Model-Optimizer](https://github.com/NVIDIA/TensorRT-Model-Optimizer). Local: `<home>/projects/github.com/NVIDIA/Model-Optimizer`.

Produces vLLM-loadable checkpoints via `--quantization modelopt` / `modelopt_fp4` / `modelopt_mxfp8` / `modelopt_mixed`. Also produces TRT-LLM engines (not our concern).

## Two distinct product lines in the same repo

1. **`modelopt/torch/quantization/`** — PTQ (NVFP4, FP8, MXFP8, INT4). Exports HF-format checkpoint.
2. **`modelopt/torch/speculative/`** — trains EAGLE-3 / dflash / Medusa drafter heads (llm-compressor does NOT do this). Exports HF-format drafter checkpoint vLLM loads via `--speculative-config`.

## Part 1 — Quantization (PTQ)

### NVFP4 recipe (the Blackwell flagship)

Example: `examples/llm_ptq/hf_ptq.py`.

```bash
python examples/llm_ptq/hf_ptq.py \
    --model_name_or_path meta-llama/Llama-3.1-70B-Instruct \
    --quant_cfg NVFP4_DEFAULT_CFG \
    --batch_size 1 \
    --calib_size 512 \
    --export_dir export/llama-3.1-70b-nvfp4
```

Output:

```
export/llama-3.1-70b-nvfp4/
├── config.json                   # includes quantization_config.quant_algo = "NVFP4"
├── model-00001-of-N.safetensors
├── hf_quant_config.json          # ModelOpt-specific metadata
├── tokenizer.*
```

vLLM: `vllm serve export/llama-3.1-70b-nvfp4 --quantization modelopt_fp4`.

### Named PTQ configs

Source: `modelopt/torch/quantization/config.py`.

| Config | Export algo | Blocks | Use |
|---|---|---|---|
| `NVFP4_DEFAULT_CFG` | NVFP4 | 16 elements, E4M3 scales | Blackwell primary |
| `NVFP4_MLP_ONLY_CFG` | NVFP4 | — | Attention stays BF16 (accuracy-critical) |
| `NVFP4_KV_CACHE_CFG` | NVFP4 + FP8 KV | — | Long-context Blackwell |
| `FP8_DEFAULT_CFG` | FP8 | per-tensor static | Hopper default |
| `FP8_PER_CHANNEL_PER_TOKEN_CFG` | FP8 | per-channel W + per-token A dynamic | Compressed-tensors-flavor |
| `FP8_PB_WO_CFG` | FP8 per-block weight-only | 128×128 | MoE-friendly |
| `MXFP8_DEFAULT_CFG` | MXFP8 | 32 elements, E8M0 scales | Ada+ MoE |
| `INT4_AWQ_CFG` | INT4 AWQ | — | Legacy W4A16 |
| `INT8_SMOOTHQUANT_CFG` | INT8 W8A8 + SmoothQuant | — | Cross-hardware |
| `MIXED_PRECISION_CFG` | Per-layer mix | — | Experimental |

### Calibration time benchmarks

- Llama 8B FP8 on H100: ~45 s
- Llama 70B NVFP4 on 8×H100: ~3.5 min
- DeepSeek 671B NVFP4 on 8×H200: ~12–15 min

### vLLM loading matrix

| ModelOpt export | vLLM flag | Min SM | Loader file |
|---|---|---|---|
| FP8 (any flavor) | `--quantization modelopt` | 89 | `modelopt.py:362` (`ModelOptFp8Config`) |
| NVFP4 | `--quantization modelopt_fp4` | 75 emulated / 100 native | `modelopt.py:1000` (`ModelOptNvFp4Config`) |
| MXFP8 | `--quantization modelopt_mxfp8` | 89 | `modelopt.py:1492` (`ModelOptMxFp8Config`) |
| Mixed precision | `--quantization modelopt_mixed` | 89 | `modelopt.py:2021` (`ModelOptMixedPrecisionConfig`) |

### Export path

`modelopt.torch.export.export_hf_checkpoint()` is the unified entry; writes compressed-tensors-aligned `quantization_config` into `config.json` plus a `hf_quant_config.json`. Shared loader across vLLM, TRT-LLM, SGLang.

### NVFP4 vs MXFP4

| | NVFP4 | MXFP4 |
|---|---|---|
| Block size | 16 elements | 32 elements |
| Scale format | E4M3 | E8M0 |
| Target hardware | Blackwell native | Broader (Ada / Hopper / Blackwell) |
| vLLM flag | `--quantization modelopt_fp4` or compressed-tensors NVFP4 | `--quantization mxfp4` / `gpt_oss_mxfp4` |
| Shipped in | ModelOpt PTQ, llm-compressor 0.10+ | GPT-OSS vendor ships; ModelOpt MXFP4 PTQ |
| Best for | Datacenter Blackwell inference | Legacy-GPU training compat + GPT-OSS |

### Selective quantisation to preserve accuracy

```python
from modelopt.torch.quantization import NVFP4_MLP_ONLY_CFG
# quantises only MLP blocks; attention stays BF16
```

Strongly recommended for smaller models (< 14B) where stock NVFP4 loses 3–5 % on hard evals.

### Known quantization-side issues

- [vLLM #38980](https://github.com/vllm-project/vllm/issues/38980) — ModelOpt NVFP4 Qwen3-30B-A3B export missing `_double_scale` key on DGX Spark.
- [vLLM #39764](https://github.com/vllm-project/vllm/issues/39764) — uninitialised `PerTensorScaleParameter` in fused-QKV NVFP4 exports.
- [vLLM #37854](https://github.com/vllm-project/vllm/issues/37854) — Nemotron-3 NVFP4 with `quant_algo MIXED_PRECISION` rejected by NGC vLLM 26.02 allow-list.
- [vLLM #38912](https://github.com/vllm-project/vllm/issues/38912) — Gemma 4 MoE NVFP4 `expert_params_mapping` misses scale suffixes.
- [vLLM #31628](https://github.com/vllm-project/vllm/issues/31628) — ModelOpt Llama-4 DP/EP FlashInfer Cutlass broken.
- [vLLM #31624](https://github.com/vllm-project/vllm/issues/31624) — ModelOpt Llama-4 loads > 5 min.
- [vLLM #40291](https://github.com/vllm-project/vllm/issues/40291) — Gemma 4 NVFP4 OOM on RTX 5090.

Active RFC: [vLLM #40182](https://github.com/vllm-project/vllm/issues/40182) — unified ModelOpt quantization.

## Part 2 — Speculative decoding training

`modelopt/torch/speculative/{eagle,dflash,medusa,plugins}/`. Examples: `examples/speculative_decoding/`. Recipes: `modelopt_recipes/general/speculative_decoding/{eagle3,dflash}.yaml`.

**Critical constraint**: training requires **BF16 target model**. Cannot train draft heads on top of already-NVFP4 / FP8 target (gradients don't flow through quantised weights). Order:

```
1. Train drafter on BF16 target       (this section)
2. Export drafter HF dir              (scripts/export_hf_checkpoint.py)
3. PTQ target to NVFP4/FP8            (Part 1 above)
4. (Optional) PTQ drafter separately
5. Serve both                         (see vLLM command below)
```

### EAGLE-3 training

Simplified one-liner (Llama-3.2-1B):

```bash
cd examples/speculative_decoding
bash train_eagle3_and_export.sh --base_model meta-llama/Llama-3.2-1B-Instruct
```

Full distributed (8B+):

```bash
./launch_train.sh \
    --config ../../modelopt_recipes/general/speculative_decoding/eagle3.yaml \
    --num_nodes 1 \
    model.model_name_or_path=meta-llama/Llama-3.1-8B \
    data.data_path=input_conversations/train.jsonl \
    training.output_dir=ckpts/llama-3.1-8b-eagle3
```

Recipe YAML key fields (`modelopt_recipes/general/speculative_decoding/eagle3.yaml`):

```yaml
training:
  mode: eagle3
  num_train_epochs: 1
  per_device_train_batch_size: 1
  learning_rate: 1.0e-4
  training_seq_len: 2048

eagle:
  eagle_decoder_type: llama           # or qwen, deepseek
  eagle_ttt_steps: 3                  # test-time training steps
  eagle_self_logit_distillation: true
  eagle_freeze_base_model: true
  eagle_architecture_config:
    num_hidden_layers: 1              # drafter depth
    intermediate_size: 14336
    num_attention_heads: 32
    num_key_value_heads: 8
```

#### Hidden-state collection (offline training)

```bash
python collect_hidden_states/compute_hidden_states_hf.py \
    --model meta-llama/Llama-3.1-70B \
    --input-file input_conversations/train.jsonl \
    --output-dir /data/hidden_states_70b \
    --dp-world-size 8 --dp-rank $SLURM_PROCID
```

Extracts layers `[2, N/2, N-3]` concatenated. Output: 5–10 TB per 200K samples for 70B. Then train offline:

```bash
./launch_train.sh \
    --config ../../modelopt_recipes/general/speculative_decoding/eagle3.yaml \
    model.model_name_or_path=meta-llama/Llama-3.1-70B \
    data.offline_data_path=/data/hidden_states_70b \
    training.output_dir=ckpts/llama-3.1-70b-eagle3-offline
```

#### Aux-hidden-state layer IDs

ModelOpt auto-sets `eagle_aux_hidden_state_layer_ids` in exported `config.json` — vLLM requires these. Formula in `modelopt/torch/speculative/plugins/transformers.py:529-536`:

```python
num_layers = self._base_llm_config.num_hidden_layers
self.eagle_config.eagle_aux_hidden_state_layer_ids = list(set([
    1, max(0, num_layers // 2 - 1), max(0, num_layers - 4),
]))
```

vLLM supported target families for EAGLE-3 aux-hidden-state path (from `vllm/config/speculative.py:818-833`): `llama, qwen, minicpm, gpt_oss, hunyuan_vl, hunyuan_v1_dense, afmoe, nemotron_h, deepseek_v2, deepseek_v3, kimi_k2, kimi_k25, minimax_m2, gemma4`.

#### Training times (indicative)

| Target | Mode | GPUs | Time |
|---|---|---|---|
| Llama-3.2-1B | Online | 8×H100 | ~4 h (1 ep, 200K UltraChat) |
| Llama-3.1-8B | Offline | 8×H100 | ~6 h (+5 TB storage) |
| Qwen3-8B | Online | 8×H100 | ~5 h |
| DeepSeek-V3 | Online | 16×H100 | ~12 h |

#### Export + deploy

```bash
python scripts/export_hf_checkpoint.py \
    --model_path ckpts/llama-3.1-8b-eagle3 \
    --export_path export/llama-3.1-8b-eagle3

# serve with BF16 target
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --speculative-config '{"method":"eagle3","model":"export/llama-3.1-8b-eagle3"}'

# or with quantized target
vllm serve export/llama-3.1-8b-nvfp4 \
    --quantization modelopt_fp4 \
    --speculative-config '{"method":"eagle3","model":"export/llama-3.1-8b-eagle3"}'
```

#### Evaluate (acceptance rate)

```bash
python scripts/ar_validate.py --model_path ckpts/llama-3.1-8b-eagle3
```

Typical AL 2.5–3.5 at k=3 on MT-Bench.

### dflash training (Blackwell-oriented)

```bash
uv run launch.py --yaml examples/Qwen/Qwen3-8B/hf_online_dflash.yaml --yes
```

Or direct:

```bash
./launch_train.sh \
    --config ../../modelopt_recipes/general/speculative_decoding/dflash.yaml \
    model.model_name_or_path=Qwen/Qwen3-8B \
    data.data_path=input_conversations/train.jsonl \
    training.output_dir=ckpts/qwen3-8b-dflash
```

Recipe YAML key fields:

```yaml
training:
  mode: dflash
  num_train_epochs: 10
  training_seq_len: 4096
  answer_only_loss: true

dflash:
  dflash_block_size: 8              # parallel prediction window
  dflash_num_anchors: 512           # random anchor samples per seq
  dflash_loss_decay_factor: 4.0
  dflash_self_logit_distillation: true
  dflash_architecture_config:
    num_hidden_layers: 5
```

Deploy: `vllm serve Qwen/Qwen3-8B-Instruct --speculative-config '{"method":"dflash","model":"export/qwen3-8b-dflash","num_speculative_tokens":7}'`.

Benchmark (Qwen3-8B H100 TP=8, MT-Bench): ModelOpt dflash bs=8 → 2.8× vs baseline, beats z-lab bs=16 (2.4×).

Open gaps: no offline training, MLA (Kimi-K2, DeepSeek-V3) KV injection not validated, Docker example missing.

### Medusa / MTP

- **Medusa** — ModelOpt loads + exports (`modelopt/torch/speculative/medusa/`) but **does not train** post-hoc. Use for converting legacy Medusa checkpoints.
- **MTP** — not trainable post-hoc. MTP heads must be part of pretraining. Use pretrained MTP from DeepSeek V3/V3.2, GLM-4.5/4.6 MoE, Qwen3-Next — served with `--speculative-config '{"method":"mtp","num_speculative_tokens":1}'`.

### Quantization-aware drafter training — **unsupported**

No QAT hooks in `modelopt/torch/speculative/`. No example in `examples/chained_optimizations/` combining PTQ + spec-dec (that dir is BERT only).

**Workaround**: train drafter BF16 → PTQ drafter separately via `hf_ptq.py` with `NVFP4_MLP_ONLY_CFG`:

```bash
python examples/llm_ptq/hf_ptq.py \
    --model_name_or_path export/llama-3.1-8b-eagle3 \
    --quant_cfg NVFP4_MLP_ONLY_CFG \
    --export_dir export/llama-3.1-8b-eagle3-nvfp4
```

Drafter PTQ has minimal accuracy cost (small model, learned features).

### Runtime tuning (acceptance rate, method selection)

Not this skill. See `vllm-speculative-decoding` skill for AL metrics, method selection per target family, composability with chunked prefill / PP / LoRA, and AL-vs-batch-size decision points.

## External references

- ModelOpt docs: [nvidia.github.io/TensorRT-Model-Optimizer](https://nvidia.github.io/TensorRT-Model-Optimizer/)
- Pre-trained HF collection: [huggingface.co/collections/nvidia/speculative-decoding-modules](https://huggingface.co/collections/nvidia/speculative-decoding-modules)
- SafeAILab canonical EAGLE: [github.com/SafeAILab/EAGLE](https://github.com/SafeAILab/EAGLE) — ModelOpt's EAGLE-3 is adapted from this (utils.py line 1 attribution)
- Red Hat speculators: `huggingface.co/RedHatAI/*-speculator.eagle3`
- Example README: `<home>/projects/github.com/NVIDIA/Model-Optimizer/examples/speculative_decoding/README.md`
- dflash doc: `examples/speculative_decoding/doc/dflash.md`
