# OCR / document parsing — operator reference

Load when the question is about DeepSeek-OCR, dots-OCR, GLM-OCR,
Nemotron-Parse, LightOnOCR, or serving any VLM for document-image
extraction.

## 1. Mental model

OCR in vLLM is not a separate runner or endpoint. It's a **multimodal
generate** workload served through `/v1/chat/completions`, with the model
doing the heavy lifting. The "OCR" models below are VLMs whose training
biases them hard toward transcription of document images.

```
--runner generate            # implicit; don't set it
# NO /v1/ocr endpoint exists — use /v1/chat/completions with image inputs
```

## 2. The dedicated OCR-purpose models

| Model | vLLM class | File | Notes |
|---|---|---|---|
| `deepseek-ai/DeepSeek-OCR` | `DeepseekOCRForCausalLM` | `vllm/model_executor/models/deepseek_ocr.py:358` | 3B, the reference OCR model since Oct 2025 |
| `deepseek-ai/DeepSeek-OCR-2` | `DeepseekOCR2ForCausalLM` | `deepseek_ocr2.py:240` | v2, wider layout support |
| `THUDM/glm-ocr-*` | `GlmOcrForCausalLM` | `glm_ocr.py` | `model_type=glm_ocr` inside glm4_1v family |
| `glm-ocr-mtp-*` | `GlmOcrForCausalLM` (MTP head) | `glm_ocr_mtp.py` | multi-token prediction variant |
| `rednote-hilab/dots.ocr` (family) | `DotsOCRForCausalLM` | `dots_ocr.py` | dense layout + table handling |
| `nvidia/Nemotron-Parse-*` | VLM path | `nemotron_*` | layout parsing + structure |
| `Lighton/Ocr-*` | `LightOnOCR*` | `lightonocr.py` | lightweight |

Plus: any general VLM (Qwen2.5-VL, InternVL, GLM-4.1V, MiniCPM-V) handles
OCR reasonably well via chat completion — just not as efficiently or
accurately as the purpose-built models on dense document images.

## 3. DeepSeek-OCR — canonical recipe

From <https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-OCR.html>:

```bash
vllm serve deepseek-ai/DeepSeek-OCR \
  --logits-processors vllm.model_executor.models.deepseek_ocr:NGramPerReqLogitsProcessor \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0
```

Three non-obvious flags, none optional:

1. **`--logits-processors ...NGramPerReqLogitsProcessor`** — enforces
   table-token whitelist (`{128821, 128822}`) with `ngram_size=30`,
   `window_size=90`. Without it, dense tables regress badly.
2. **`--no-enable-prefix-caching`** — OCR requests don't share prefixes;
   the cache is pure bookkeeping overhead.
3. **`--mm-processor-cache-gb 0`** — multimodal processor caching targets
   repeated images (which OCR doesn't do) and wastes RAM.

**Mode is hard-coded to GUNDAM** (base=1024, image=640, crop=True). The
upstream repo's Tiny/Small/Base/Large modes are not yet switchable via env
vars in vLLM; follow the upstream tracker if a deployment needs a different
resolution profile.

Published throughput: ~2500 tok/s on a single A100-40 GB, ~200 k pages/day.

## 4. Request format

Standard OpenAI chat-completions with images:

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")

r = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-OCR",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url",
             "image_url": {"url": "data:image/png;base64," + b64}},
            {"type": "text", "text": "Transcribe this document to markdown."},
        ],
    }],
    max_tokens=4096,
    temperature=0,
)
print(r.choices[0].message.content)
```

Prompt conventions per model:

| Model | Prompt style | Output |
|---|---|---|
| DeepSeek-OCR | `"Transcribe this document to markdown."` | markdown (tables as \| \| \|) |
| DeepSeek-OCR | `"<image>\n<\|grounding\|>Convert to markdown."` | with bounding boxes |
| dots.ocr | `"请识别图像内容"` | raw text (model is Chinese-first) |
| GLM-OCR | standard VLM prompt | varies |
| Nemotron-Parse | structure-aware prompt per model card | JSON / structured |

Check the model card for exact prompt tokens. Prompts matter more for OCR
than for general chat — the model was trained on specific instruction
templates.

## 5. Image-input specifics

- **Base64 data URLs** work out of the box. Large images (>1 MB base64)
  add request-parsing cost; prefer URL references for scanned documents
  when possible.
- **Multi-page documents** — split client-side into one image per page.
  vLLM handles one image per message cleanly; some VLMs accept multiple
  images per message (see per-model docs for limit).
- **Image resolution** — server does resizing per model's
  `MultiModalConfig`. For DeepSeek-OCR, the GUNDAM mode crops + tiles
  up to 1024 px base, 640 px per crop. A 300 DPI letter-size page
  (~2550×3300) gets tiled into ~12 crops.
- **Batching** — vLLM batches multiple OCR requests in a single engine
  step. Throughput scales roughly linearly with batch up to the encoder
  bottleneck (~8 concurrent images on A100).

## 6. Known sharp edges

1. **`--enable-prefix-caching` left on** — doesn't crash, but costs memory
   and the cache never helps. Always disable for OCR traffic.
2. **General VLMs as "OCR"** — works for short text on images (signs,
   screenshots) but degrades fast on dense documents, tables, and handwriting.
   If OCR is the primary workload, use a purpose-built model.
3. **Nemotron-Parse JSON schema** — the model card spells out the schema.
   Free-form prompts produce less structured output; stick to the
   documented instruction templates.
4. **Tensor parallelism** — works on the purpose-built OCR models but
   rarely worth it below 7B. These models are already encoder-bottlenecked
   on single-GPU setups.
5. **GLM-OCR model_type quirk** — it's `glm_ocr` inside the `glm4_1v`
   family. If auto-detection picks the plain `glm4_1v` class, the model
   runs but without OCR-specific preprocessing; pin via
   `--hf-overrides '{"model_type": "glm_ocr"}'` if needed.

## 7. Pairing OCR + a language model

Common pattern: use a fast OCR model (DeepSeek-OCR) to extract text, then
feed text to a general LLM for reasoning. Two approaches:

- **Two-serve**: deploy DeepSeek-OCR on one vLLM port, a general LLM on
  another. Client orchestrates.
- **One-serve**: use a strong general VLM (Qwen2.5-VL-72B, InternVL3-78B)
  that does OCR + reasoning in a single chat turn. Lower latency, higher
  cost per token.

Pick based on throughput vs latency requirements. OCR-then-LLM is cheaper
per page; single-VLM is lower-latency for interactive use.

## 8. Source anchors

- `vllm/model_executor/models/deepseek_ocr.py:358-` — `DeepseekOCRForCausalLM`,
  `NGramPerReqLogitsProcessor`
- `vllm/model_executor/models/deepseek_ocr2.py:240-` — v2
- `vllm/model_executor/models/glm_ocr.py`, `glm_ocr_mtp.py`
- `vllm/model_executor/models/dots_ocr.py` — 793 LOC
- `vllm/model_executor/models/lightonocr.py`
- `vllm/multimodal/parse.py` — image-input parsing
- Recipe: <https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-OCR.html>

## 9. Related skills

- `vllm-nvidia-hardware` — VLM HBM sizing; multi-image VLMs eat memory fast
  on long documents.
- `vllm-caching` — KV offload isn't useful for OCR (no prefix reuse), so
  most of that skill's advice doesn't apply; this is the one place where
  turning KV features off is correct.
