# llm-compressor — producing vLLM-loadable checkpoints

[vllm-project/llm-compressor](https://github.com/vllm-project/llm-compressor). Outputs compressed-tensors format vLLM loads with `--quantization compressed-tensors`.

Docs: [llm-compressor docs](https://docs.vllm.ai/projects/llm-compressor/en/latest/). Current release: **v0.10.0** (NVFP4/MXFP4, DDP GPTQ, disk offloading, per-head KV).

## Modifier classes (what you compose into recipes)

| Modifier | File | Use |
|---|---|---|
| `QuantizationModifier` | `src/llmcompressor/modifiers/quantization/quantization/base.py:16-50` | Simple PTQ, data-free (FP8_DYNAMIC, FP8_BLOCK, W8A16, NVFP4A16) |
| `GPTQModifier` | `src/llmcompressor/modifiers/gptq/base.py:42-116` | Hessian-based PTQ (W4A16, W8A8, W4A4 with calibration) |
| `AWQModifier` | `src/llmcompressor/modifiers/awq/base.py:57-82` | Activation-aware INT4 (fewer calibration samples than GPTQ) |
| `SmoothQuantModifier` | `src/llmcompressor/modifiers/transform/smoothquant/base.py:60-100` | Activation smoothing before W8A8 GPTQ |

## Standard oneshot template

Every llm-compressor script follows:

```python
from llmcompressor import oneshot
from llmcompressor.modifiers.quantization import QuantizationModifier
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset

MODEL_ID = "meta-llama/Llama-3.1-70B-Instruct"
model = AutoModelForCausalLM.from_pretrained(MODEL_ID, dtype="auto")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

# Load calibration if needed
ds = load_dataset("HuggingFaceH4/ultrachat_200k", split="train_sft[:512]")

recipe = QuantizationModifier(targets="Linear", scheme="FP8_DYNAMIC", ignore=["lm_head"])

oneshot(model=model, recipe=recipe, dataset=ds,
        max_seq_length=2048, num_calibration_samples=512)

SAVE_DIR = MODEL_ID.split("/")[-1] + "-FP8-Dynamic"
model.save_pretrained(SAVE_DIR, save_compressed=True)
tokenizer.save_pretrained(SAVE_DIR)
```

vLLM loads it: `vllm serve ./Llama-3.1-70B-Instruct-FP8-Dynamic` — no flag needed when `quantization_config` is in `config.json`.

## Recipes — full catalog

### FP8 Dynamic (recommended Hopper default)

```python
recipe = QuantizationModifier(targets="Linear", scheme="FP8_DYNAMIC", ignore=["lm_head"])
```

- **Calibration**: none (data-free)
- **Hardware**: SM89+ (Ada, Hopper, Blackwell)
- **Time on H100, 70B**: ~15 min (init only)
- **Output name**: `*-FP8-Dynamic`
- **Example**: `examples/quantization_w8a8_fp8/llama3_example.py`

### FP8 Block (per-128×128 tile scaling)

```python
recipe = QuantizationModifier(targets="Linear", scheme="FP8_BLOCK", ignore=["lm_head"])
```

- **Calibration**: none
- **Time on H100, 70B**: ~15 min
- **Output name**: `*-FP8-Block`
- **Accuracy**: slightly better than dynamic, modest compute overhead
- **Example**: `examples/quantization_w8a8_fp8/fp8_block_example.py`
- **Caveat on Gemma 4**: **do not use** ([#39407](https://github.com/vllm-project/vllm/issues/39407) — double-applied absorbed scales)

### W8A8 INT8 (requires SmoothQuant)

```python
from llmcompressor.modifiers.gptq import GPTQModifier
from llmcompressor.modifiers.transform.smoothquant import SmoothQuantModifier

recipe = [
    SmoothQuantModifier(smoothing_strength=0.8),
    GPTQModifier(targets="Linear", scheme="W8A8", ignore=["lm_head"]),
]
```

- **Calibration**: 512 ultrachat samples, seq 2048
- **Time on H100, 70B**: ~45 min
- **Output name**: `*-W8A8-Dynamic-Per-Token`
- **Tuning**: `smoothing_strength` 0.5–1.0; drop to 0.5 if activations NaN
- **Example**: `examples/quantization_w8a8_int8/llama3_example.py`

### W4A16 GPTQ

```python
recipe = GPTQModifier(
    targets="Linear",
    scheme="W4A16",
    ignore=["lm_head"],
    block_size=128,
    dampening_frac=0.01,
    actorder="static",
)
```

- **Calibration**: 512 samples
- **Time on H100, 70B**: ~60 min
- **Memory peak**: ~2× model size (Hessian same size as weights)
- **OOM fix**: `offload_hessians=True` (+2× time, -30 % GPU peak) or sequential pipeline
- **Output name**: `*-W4A16-G128`
- **Example**: `examples/quantization_w4a16/llama3_example.py`
- **DDP variant**: `llama3_ddp_example.py` (v0.10+)

### W4A16 AWQ

```python
from llmcompressor.modifiers.awq import AWQModifier

recipe = [
    AWQModifier(
        targets=["Linear"],
        scheme="W4A16_ASYM",
        ignore=["lm_head"],
        duo_scaling="both",  # or "weight" / "activation"
    ),
]
```

- **Calibration**: 256 samples (fewer than GPTQ)
- **Time on H100, 70B**: ~40 min
- **Output name**: `*-awq-asym`
- **Mappings**: auto for Llama/Qwen/Mistral. Custom via `AWQMapping` list.
- **Accuracy edge**: ~1–2 % over GPTQ on small cal sets
- **Example**: `examples/awq/llama_example.py`

### NVFP4 A16 (weight-only FP4)

```python
recipe = QuantizationModifier(targets="Linear", scheme="NVFP4A16", ignore=["lm_head"])
```

- **Calibration**: 20 samples (!)
- **Time on B200, 70B**: ~12 min
- **Hardware**: Blackwell native, Hopper via emulation (weight-only)
- **Output name**: `*-NVFP4A16`
- **Example**: `examples/quantization_w4a16_fp4/nvfp4/llama3_example.py`

### NVFP4 (W4A4)

```python
recipe = QuantizationModifier(targets="Linear", scheme="NVFP4", ignore=["lm_head"])
```

- **Calibration**: 20 samples
- **Time on H100, 70B**: ~15 min
- **Blackwell native**: full W4A4. Hopper: falls back to weight-only.
- **Compression**: ~8× vs FP16
- **Example**: `examples/quantization_w4a4_fp4/llama3_example.py`

### MXFP4 A16 (Microsoft format)

```python
recipe = GPTQModifier(targets="Linear", scheme="MXFP4A16", ignore=["lm_head"])
```

- **Calibration**: 512 samples
- **Time on H100, 70B**: ~70 min
- **Hardware**: Ada, Hopper (needs vLLM ≥ 0.14.0)
- **Output name**: `*-MXFP4A16-GPTQ`
- **Example**: `examples/quantization_w4a16_fp4/mxfp4/llama3_example.py`

### W8A16 (weight-only INT8)

```python
recipe = QuantizationModifier(targets="Linear", scheme="W8A16", ignore=["lm_head"])
```

- **Calibration**: none (RTN)
- **Time on H100, 70B**: ~10 min
- 2× weight compression (vs 3.7× for W4A16) but lower quantization noise.

### KV-cache FP8

```python
recipe = QuantizationModifier(
    targets="Linear",
    scheme="FP8_DYNAMIC",
    ignore=["lm_head"],
    kv_cache_scheme={
        "num_bits": 8, "type": "float", "strategy": "tensor",
        "dynamic": False, "symmetric": True,
    },
)
```

- **Calibration**: 512 samples
- **Time on H100, 70B**: ~35 min
- vLLM flag: `--kv-cache-dtype fp8`
- **Caveat**: per-head KV is experimental; stick to `strategy: tensor` for MLA
- **Example**: `examples/quantization_kv_cache/llama3_fp8_kv_example.py`

## Output directory layout

All schemes produce:

```
Model-Name-SCHEME/
├── config.json                          # model config + quantization_config
├── model-00001-of-N.safetensors
├── model.safetensors.index.json
├── tokenizer.json
├── tokenizer.model                      # if SPM
├── tokenizer_config.json
├── special_tokens_map.json
└── generation_config.json
```

vLLM reads `quantization_config` automatically — no `--quantization` flag required when it's in `config.json`. For clarity, pass `--quantization compressed-tensors` anyway.

## Pipeline modes

| Mode | Use for | Memory / time tradeoff |
|---|---|---|
| Oneshot (default) | < 100B on single node | Fast, 1–2× model size peak |
| Sequential (`pipeline="sequential"`) | 70B+ with limited GPU memory | Layer-by-layer onload/offload, adds ~30 % time, cuts peak ~40 % |
| Model-free PTQ | Safetensors-only (no HF class definition — e.g. Kimi-K2, Mistral-Large-3 675B) | No model load, direct tensor transform |

Sequential:

```python
oneshot(model=model, recipe=recipe, dataset=ds,
        pipeline="sequential", sequential_offload_device="/tmp/offload")
```

Model-free:

```python
from llmcompressor.entrypoints.model_free import model_free_ptq

model_free_ptq(
    model_stub="unsloth/Kimi-K2-Thinking-BF16",
    scheme="FP8_BLOCK",
    save_directory="./Kimi-K2-Thinking-FP8-BLOCK",
)
```

Examples: `examples/model_free_ptq/`.

## Version gates (llm-compressor releases)

| Feature | Version | Status |
|---|---|---|
| FP8_DYNAMIC | 0.7.0 | Stable |
| W4A16 GPTQ | 0.7.0 | Stable |
| AWQ | 0.7.1 | Stable |
| SmoothQuant | 0.7.1 | Stable |
| FP8_BLOCK | 0.8.1 | Stable |
| KV cache FP8 | 0.8.0 | Stable |
| Model-free PTQ | 0.9.0 | Stable |
| DDP GPTQ | 0.10.0 | Stable |
| NVFP4 (W4A4, W4A16) | 0.10.0 | Stable |
| MXFP4 | 0.10.0 | Stable |
| Per-head KV | 0.10.0 | Experimental |
| 2:4 sparsity | — | Deprecated (vLLM PR #36799) |

## Known issues & operator gotchas

1. **OOM during GPTQ calibration (70B+)** — `offload_hessians=True`, or `pipeline="sequential"`.
2. **Calibration dataset mismatch** → perplexity degraded. Use ultrachat or your fine-tuning data with chat template applied. `add_special_tokens=False`.
3. **vLLM fails to load compressed checkpoint** — vLLM < 0.5.5 or compressed-tensors < 0.5.0. Upgrade both.
4. **Group-size divisibility** — `hidden_size % group_size == 0` required. Use 32/64/128/256.
5. **`add_bos_token` sensitivity** — quantized models need explicit BOS handling in eval: `--model_args ...,add_bos_token=True`.
6. **SmoothQuant NaN** — reduce `smoothing_strength` from 0.8 → 0.5.
7. **AWQ mapping missing for custom arch** — use generic smoothing (loss ~0.5 %) or contribute mappings.
8. **MXFP4 / NVFP4 on Hopper** = silent weight-only fallback (activations stay FP16). Expected.
9. **Tokenizer not pushed to HF Hub** — `tokenizer.save_pretrained()` saves locally; push separately.
10. **Disk-offloaded weights** — enable explicit sequential pipeline; `model.to(device)` can skip offloaded layers.

## llm-compressor does NOT:

- Train EAGLE / dflash / Medusa drafters (confirmed — no speculative-decoding code in repo). Use ModelOpt.
- Produce TRT-LLM engines.
- Support per-head INT8 KV (FP8 per-head experimental only).

## External

- README: [`vllm-project/llm-compressor/README.md`](https://github.com/vllm-project/llm-compressor/blob/main/README.md)
- Compression schemes doc: `docs/guides/compression_schemes.md`
- Memory guide: `docs/guides/memory.md`
- Sequential onloading: `docs/guides/big_models_and_distributed/sequential_onloading.md`
- vLLM recipes: [docs.vllm.ai/projects/recipes](https://docs.vllm.ai/projects/recipes/en/latest/index.html)
