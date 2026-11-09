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
| `deepseek-ai/DeepSeek-OCR` | `DeepseekOCRForCausalLM` | `vllm/model_executor/models/deepseek_ocr.py:362` | 3B, the reference OCR model since Oct 2025 |
| `deepseek-ai/DeepSeek-OCR-2` | `DeepseekOCR2ForCausalLM` | `deepseek_ocr2.py:234` | v2, wider layout support. TTFT optimisation in v0.27.0 (#49531) |
| `THUDM/glm-ocr-*` | `GlmOcrForConditionalGeneration` | `glm_ocr.py` | `model_type=glm_ocr` inside glm4_1v family |
| `glm-ocr-mtp-*` | `GlmOcrMTP` (arch `GlmOcrMTPModel`) | `glm_ocr_mtp.py` | multi-token prediction variant |
| `rednote-hilab/dots.ocr` (family) | `DotsOCRForCausalLM` | `dots_ocr.py` | dense layout + table handling |
| `nvidia/Nemotron-Parse-*` | `NemotronParseForConditionalGeneration` | `nemotron_parse.py` | layout parsing + structure |
| `Lighton/Ocr-*` | `LightOnOCRForConditionalGeneration` | `lightonocr.py` | lightweight |
| Qianfan-OCR | `QianfanOCRForConditionalGeneration` | `qianfan_ocr.py` | added v0.21.0 (#40136) |
| `baidu/Unlimited-OCR` | `UnlimitedOCRForCausalLM` | `unlimited_ocr.py` | added v0.25.0 (#46564); Triton R-SWA backend #47102. Benchmarked on OmniDocBench |
| `nvidia/Nemotron-3.5-Parse` | `RadioMBartPrefixForCausalLM` | `nemotron_parse3_5.py` | added v0.33.0 (#61651); `--trust-remote-code`. Its MTP draft (`ParseAuxMTPModel`) runs on Model Runner V2 only |
| `openbmb/MiniCPM-OCR-1.0` | `MiniCPMOcrForConditionalGeneration` | `minicpm_ocr.py` | added v0.33.0 (#63095). Send `chat_template_kwargs={"enable_thinking": false}` for plain transcription — otherwise the output opens with `<think>` |
| `PaddlePaddle/PaddleOCR-VL` | `PaddleOCRVLForConditionalGeneration` | `paddleocr_vl.py` | vision encoder batched across images from v0.33.0 (#61458) |

Plus: any general VLM (Qwen2.5-VL, InternVL, GLM-4.1V, MiniCPM-V) handles
OCR reasonably well via chat completion — just not as efficiently or
accurately as the purpose-built models on dense document images.

## 3. DeepSeek-OCR — canonical recipe

From <https://recipes.vllm.ai/deepseek-ai/DeepSeek-OCR> (source:
`recipes/models/deepseek-ai/DeepSeek-OCR.yaml` in the vLLM repo):

```bash
VLLM_USE_V2_MODEL_RUNNER=0 \
vllm serve deepseek-ai/DeepSeek-OCR \
  --logits-processors vllm.model_executor.models.deepseek_ocr:NGramPerReqLogitsProcessor \
  --no-enable-prefix-caching \
  --mm-processor-cache-gb 0
```

**Model Runner V1 is required for the logits processor.**
`NGramPerReqLogitsProcessor` subclasses the V1 `AdapterLogitsProcessor`. What
happens without `VLLM_USE_V2_MODEL_RUNNER=0`:

| Running version | Result |
|---|---|
| v0.28.x and below | V1 is the default — works |
| v0.29.x–v0.30.x | vLLM logs `Model Runner V2 does not yet support custom logits processors; using the V1 model runner instead.` — works |
| v0.31.0–v0.33.0 | startup fails: `ValueError: NGramPerReqLogitsProcessor is not a subclass of vllm.v1.worker.gpu.sample.logits_processor.LogitsProcessor` |

Same for `baidu/Unlimited-OCR`, which reuses this processor. No V2-interface
n-gram processor ships at v0.33.0, and MRV1 is announced for removal
(`references/runner-flags.md` §11): re-check on every upgrade. Dropping the
processor instead makes long pages loop.

Three non-obvious flags. Only the first changes output; the other two remove
overhead (the recipe's own serve line carries the first and third):

1. **`--logits-processors ...NGramPerReqLogitsProcessor`** — applies the
   table-token whitelist (`{128821, 128822}`) with `ngram_size=30`,
   `window_size=90`. Without it, dense tables regress badly. Note the class
   does not hard-code those numbers: it reads `whitelist_token_ids`,
   `ngram_size` and `window_size` from each request's `extra_args`
   (`deepseek_ocr.py:140-195`). A request without `ngram_size` gets **no
   processor at all** — every client must send the §4 request shape.
2. **`--no-enable-prefix-caching`** — OCR requests don't share prefixes;
   the cache is pure bookkeeping overhead. Keep this spelling: upstream docs
   from v0.33.0 write `--disable-prefix-caching`, which v0.32.x and older
   reject as an unknown argument; `--no-enable-…` parses on every version.
3. **`--mm-processor-cache-gb 0`** — multimodal processor caching targets
   repeated images (which OCR doesn't do) and wastes RAM.

**Mode is hard-coded to GUNDAM** (base=1024, image=640, crop=True). The
upstream repo's Tiny/Small/Base/Large modes are not yet switchable via env
vars in vLLM; follow the upstream tracker if a deployment needs a different
resolution profile.

Published throughput: ~2500 tok/s on a single A100-40 GB, ~200 k pages/day.

## 4. Request format

OpenAI chat-completions with images. For DeepSeek-OCR and Unlimited-OCR the
`extra_body` block is mandatory — it is what switches the logits processor on:

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
            {"type": "text", "text": "Free OCR."},
        ],
    }],
    max_tokens=4096,
    temperature=0,
    extra_body={
        "skip_special_tokens": False,
        "vllm_xargs": {                 # -> SamplingParams.extra_args
            "ngram_size": 30,
            "window_size": 90,
            "whitelist_token_ids": [128821, 128822],   # <td>, </td>
        },
    },
)
print(r.choices[0].message.content)
```

Offline (`LLM.generate`): prompt `"<image>\nFree OCR."` and
`SamplingParams(temperature=0.0, max_tokens=8192, skip_special_tokens=False,
extra_args=dict(ngram_size=30, window_size=90, whitelist_token_ids={128821, 128822}))`.

Prompt conventions per model:

| Model | Prompt style | Output |
|---|---|---|
| DeepSeek-OCR | `"Free OCR."` | plain text, no layout |
| DeepSeek-OCR | `"<\|grounding\|>Convert the document to markdown."` | markdown with layout boxes (tables as HTML `<td>`) |
| DeepSeek-OCR | `"<\|grounding\|>OCR this image."` / `"Parse the figure."` | non-document image / figure |
| dots.ocr | `"请识别图像内容"` | raw text (model is Chinese-first) |
| GLM-OCR | standard VLM prompt | varies |
| Nemotron-Parse | structure-aware prompt per model card | JSON / structured |

Check the model card for exact prompt tokens. Prompts matter more for OCR
than for general chat — the model was trained on specific instruction
templates. DeepSeek-OCR wants its short fixed prompts, not free-form
instructions; offline, prefix them with `<image>\n`.

## 5. Image-input specifics

- **Base64 data URLs** work out of the box. Large images (>1 MB base64)
  add request-parsing cost; prefer URL references for scanned documents
  when possible.
- **Raster formats only from v0.32.0** (#60022). Request images are opened
  against `ALLOWED_IMAGE_FORMATS`; EPS/PostScript and WMF are refused.
  Rasterize vector scans (PDF/EPS/WMF) to PNG client-side.
- **Multi-page documents** — split client-side into one image per page.
  vLLM handles one image per message cleanly; some VLMs accept multiple
  images per message (see per-model docs for limit).
- **Per-request media budget from v0.33.0** (#61226). Every image, audio
  clip and video frame in one chat request draws on one decoded-size budget,
  `VLLM_MAX_MEDIA_REQUEST_DECODE_BYTES` (default 715,827,880; an image costs
  width × height × 4 bytes, so ~179 MP in total — about 21 letter pages at
  300 DPI), and all URL downloads on `VLLM_MAX_MEDIA_REQUEST_DOWNLOAD_SIZE_MB`
  (default 256). Over either, the request fails with `Request decoded media
  exceeds VLLM_MAX_MEDIA_REQUEST_DECODE_BYTES` / `Request media downloads
  exceed …`. Send one page per request, or raise the variables (`0` disables
  a budget). The per-item limits (`VLLM_MAX_IMAGE_PIXELS`, 256 MB per
  download) still apply.
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
   on single-GPU setups. **Exception — dots.ocr / dots.mocr through v0.33.0:**
   with `--tensor-parallel-size` > 1 every region comes back as the same
   "does not contain any text … blurry image" sentence (vision-tower QKV split,
   #64541; fix merged after v0.33.0). Run TP=1 or add
   `--mm-encoder-tp-mode data`.
5. **GLM-OCR model_type quirk** — it's `glm_ocr` inside the `glm4_1v`
   family. If auto-detection picks the plain `glm4_1v` class, the model
   runs but without OCR-specific preprocessing; pin via
   `--hf-overrides '{"model_type": "glm_ocr"}'` if needed.
6. **EngineCore dies on a half-black / half-white page (DeepSeek-OCR, OCR-2,
   Unlimited-OCR, below v0.32.0).** A normalized pixel tensor summing to
   exactly zero was treated as "no image" and tripped the encoder-output
   check (#59417). Upgrade to ≥v0.32.0 for any public-facing OCR endpoint.
7. **Startup fails with `triton.compiler.errors.CompilationError … Cannot
   access global variable LOG2E from within @jit'ed function`, then `Engine
   core initialization failed`** (DeepSeek-OCR, DeepSeek-OCR-2, Unlimited-OCR —
   the shared DeepEncoder attention kernel). Reported on v0.32.0; the kernel
   code is identical in v0.30.0–v0.33.0 and the upstream issue (#62848) is
   open. Set `TRITON_ALLOW_NON_CONSTEXPR_GLOBALS=1` in the server environment.
   No attention backend and no `--enforce-eager` avoids it — the failing
   kernel is the vision encoder's.

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

## 8. Source anchors (line numbers at v0.33.0)

- `vllm/model_executor/models/deepseek_ocr.py:362-` — `DeepseekOCRForCausalLM`;
  `:140-195` — `NGramPerReqLogitsProcessor`
- `vllm/model_executor/models/deepseek_ocr2.py:234-` — v2
- `vllm/model_executor/models/glm_ocr.py`, `glm_ocr_mtp.py`
- `vllm/model_executor/models/dots_ocr.py` — 770 LOC
- `vllm/model_executor/models/lightonocr.py`
- `vllm/multimodal/parse.py` — image-input parsing
- Recipe: `recipes/models/deepseek-ai/DeepSeek-OCR.yaml`, rendered at
  <https://recipes.vllm.ai/deepseek-ai/DeepSeek-OCR>

## 9. Related skills

- `vllm-nvidia-hardware` — VLM HBM sizing; multi-image VLMs eat memory fast
  on long documents.
- `vllm-caching` — KV offload isn't useful for OCR (no prefix reuse), so
  most of that skill's advice doesn't apply; this is the one place where
  turning KV features off is correct.
