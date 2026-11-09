# External references — verification audit

Freshened: 2026-10-18 — every row, URL, PR/issue state and source anchor probed at the v0.32.0 tag (latest release, 2026-10-18), plus HF model IDs via the Hub API. Moved: `auto` audio decode order is torchcodec-first (#58364), per-request mm kwargs gated (#58830), MRV1 not removed at v0.32.0, MRV2 token-wise pooling no longer encoder-only (#50931, v0.28.0), Qwen3 reranker template path, STT/OCR class names, two wrong HF IDs.

2026-09-22 pass: **two placements were wrong**, both the same way: the release published *after* the PR merged while not containing it, because its branch was already cut. That is exactly what makes "merged before X, so it is in X" feel safe. One of the two had reached operator-facing guidance in `stt.md` as a version floor one release too low.

Latest vLLM is **v0.33.0** (published 2026-11-02); see the 2026-11-09 section.
Rows further down that name an earlier tag are point-in-time and remain
correct for what they assert unless a note says superseded.

Log of external citations probed during skill freshen passes. Each row
records when the reference was last verified and its classification:

- **fresh** — still valid, matches claim in skill.
- **version-drift** — reference moved forward but claim still holds with
  minor gloss (e.g. "scheduled" → "landed").
- **deprecation** — replaced by newer API; skill updated to reflect.
- **new-feature** — added since previous freshen; incorporated.
- **broken** — 404 / moved / unreachable; skill updated with replacement
  or "unverifiable" note.
- **unverifiable** — reachable but couldn't confirm the claim.

## 2026-11-09 freshen (v0.32.0 → v0.33.0)

Source anchors read from `vllm-project/vllm` at the `v0.33.0` tag and diffed
against `v0.32.0`. Release notes walked: v0.33.0. Issue tracker swept for
issues opened since 2026-10-18.

| Ref | URL | Classification | Notes |
|---|---|---|---|
| vLLM v0.33.0 (latest) | <https://github.com/vllm-project/vllm/releases/tag/v0.33.0rc3> | version-drift | Published 2026-11-02. The GitHub Release object is titled `v0.33.0` but attached to the tag `v0.33.0rc3`; the annotated tag `v0.33.0` points at the same commit (`4ba787ec99`), PyPI has `0.33.0` (uploaded 2026-11-02), the release assets are `vllm-0.33.0-*.whl`, and `docs.vllm.ai/en/stable` renders v0.33.0. `releases/tags/v0.33.0` returns 404 — list releases, do not look one up by tag. No v0.32.1 release (only a `v0.32.1rc0` tag). |
| Source anchors at v0.33.0 | `vllm-project/vllm` at `v0.33.0` | version-drift | Moved since v0.32.0: `vllm/config/model.py` `_RUNNER_CONVERTS` 123→124, `_get_runner_type`…`_get_convert_type` 1294-1369→1307-1382, runner validation 690-725→704-738, `is_matryoshka` 2066-2073→2084-2091; `vllm/entrypoints/pooling/utils.py` `enable_scoring_api` 232→220; `vllm/pooling_params.py` matryoshka bound 164-193→235 onward; `vllm/entrypoints/launchers/cli_args.py` moved to `vllm/entrypoints/common/cli_args.py` (`trust_request_mm_kwargs` still `:99`, `enable_flash_late_interaction` `:382`); `vllm/entrypoints/pooling/scoring/io_processor.py` 974→1056 lines. Unchanged: `vllm/tasks.py`, `vllm/config/scheduler.py:20`, `vllm/config/pooler.py`, pooling `api_router.py` files, `factories.py:38-109`, `jina.py:44-96`, `deepseek_ocr.py`, `deepseek_ocr2.py`, `dots_ocr.py` (770 lines), `vllm/multimodal/parse.py:603`, the whole `vllm/entrypoints/speech_to_text/` tree and `vllm/config/speech_to_text.py`. Still absent: `--task` in `arg_utils.py`, `task` in `ModelConfig`. GUNDAM constants unchanged in `vllm/transformers_utils/processors/deepseek_ocr.py:21-23`. Applied to runner-flags.md, reranking.md, embedding.md, SKILL.md. |
| MRV1 still present at v0.33.0 | v0.33.0 `vllm/config/vllm.py:731` `use_v2_model_runner`, `:3053` `_get_v2_model_runner_unsupported_features` | version-drift | `VLLM_USE_V2_MODEL_RUNNER=0` still returns V1. Fallback list at v0.33.0: PP + `external_launcher`, speculative `suffix` / `custom_class`, EAGLE parallel drafting, heterogeneous vocab, DBO subsets, no Triton. `medusa` / `mlp_speculator` dropped from the list because <https://github.com/vllm-project/vllm/pull/61701> (merged 2026-10-15, v0.33.0 notes "Breaking changes") removed both methods; `MedusaModel` is gone from `registry.py`. Pooling task set `_SUPPORTED_TASKS` unchanged (`pooling_runner.py:20`). Applied to runner-flags.md §11, SKILL.md. |
| PR #56497 — MRV2 custom logits processors | <https://github.com/vllm-project/vllm/pull/56497> | **broken (recipe)** | Merged 2026-09-19; first tag with the change is v0.31.0 (tag contents, not dates: v0.30.0 `vllm/config/vllm.py:2876` still appends "custom logits processors" to the V2-unsupported list; v0.31.0 has `vllm/v1/worker/gpu/sample/logits_processor/loader.py` and no such entry). The V2 loader raises `ValueError` for any class that is not a V2 `LogitsProcessor` (`loader.py:92,128`), and `NGramPerReqLogitsProcessor` subclasses the V1 `AdapterLogitsProcessor` at v0.31.0, v0.32.0 and v0.33.0 (`deepseek_ocr.py:140`). Field report of the exact error on v0.32.0: issue #62848 (side note). V2 port #57618 closed unmerged; native n-gram masking #57540 open. Applied to SKILL.md OCR section + version gates, ocr.md §3. |
| Issue #62848 — DeepEncoder `LOG2E` Triton compile failure | <https://github.com/vllm-project/vllm/issues/62848> | **broken (open)** | OPEN, opened 2026-10-21 against `vllm/vllm-openai:v0.32.0` (Triton 3.7.1); independently reproduced in the thread 2026-10-29. `vllm/model_executor/models/deepencoder.py:26,93,124` reads the plain-float `vllm.triton_utils.LOG2E` inside a `@triton.jit` kernel at v0.30.0, v0.31.0, v0.32.0 and v0.33.0 (kernel added by #55629, first tag v0.30.0); the first failing release is not established upstream. `TRITON_ALLOW_NON_CONSTEXPR_GLOBALS=1` is Triton's own switch (`triton-lang/triton` at `v3.7.0`, `python/triton/compiler/code_generator.py`) and is what the reproducers in #61946 and #64075 run with. Applied to ocr.md §6, SKILL.md version gates. |
| DeepSeek-OCR recipe — current location and request shape | <https://recipes.vllm.ai/deepseek-ai/DeepSeek-OCR> (JSON: `/deepseek-ai/DeepSeek-OCR.json`); `vllm-project/vllm` at `v0.33.0` `recipes/models/deepseek-ai/DeepSeek-OCR.yaml` | **broken (content) / moved** | The old page <https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-OCR.html> is still 200 but now carries a banner: current recipes live at recipes.vllm.ai and the Markdown guides are "kept as a historical reference". `recipes/` exists at v0.33.0, not at v0.32.0; recipe `date_updated: 2026-04-17`. Both pages give the online request as `extra_body={"skip_special_tokens": False, "vllm_xargs": {"ngram_size": 30, "window_size": 90, "whitelist_token_ids": [128821, 128822]}}` and offline `SamplingParams(extra_args=...)`; `vllm_xargs` becomes `extra_args` at `vllm/entrypoints/openai/chat_completion/protocol.py:783`, and `new_req_logits_processor` returns `None` when `ngram_size` is absent (`deepseek_ocr.py:180-189`). The skill's §4 example sent neither and used a prompt that is not one of the model's. The in-repo recipe's serve line is `--logits-processors … --mm-processor-cache-gb 0` (no `--no-enable-prefix-caching`; its tips still say to disable prefix caching, and offline it sets `enable_prefix_caching=False`); the old page keeps all three flags. Prompts from `deepseek-ai/DeepSeek-OCR` at `2ac6d64a` `DeepSeek-OCR-master/DeepSeek-OCR-vllm/config.py:27-37`. Applied to SKILL.md OCR section, ocr.md §3/§4/§8. |
| DeepSeek-OCR throughput figures | <https://github.com/deepseek-ai/DeepSeek-OCR> README; <https://arxiv.org/abs/2510.18234> | fresh | README: "pdf: concurrency ~2500tokens/s(an A100-40G)". Paper abstract (submitted 2025-10-21): "200k+ pages per day (a single A100-40G)". Neither figure is on the vLLM recipe pages. Supports SKILL.md OCR section and ocr.md §3. |
| PR #61226 — per-request media budgets | <https://github.com/vllm-project/vllm/pull/61226> | **deprecation / breaking** | Merged 2026-10-13; in v0.33.0, not v0.32.0 (in `git log v0.32.0..v0.33.0`; v0.33.0 notes "Security"). `vllm/envs.py:1053-1058`: `VLLM_MAX_MEDIA_REQUEST_DECODE_BYTES` default 715827880, `VLLM_MAX_MEDIA_REQUEST_DOWNLOAD_SIZE_MB` default 256; `<= 0` disables (`vllm/multimodal/media/base.py`, `vllm/connections.py:76-78`). Images charged `w * h * 4` (`vllm/multimodal/media/image.py:93`); audio reserves then settles decoded bytes. Scope per the PR: chat completions, messages and responses through the Python multimodal tracker; the Rust frontend and offline helpers are outside. Documented in `docs/usage/security.md`. Applied to ocr.md §5, SKILL.md version gates. |
| Issue #64541 / PR #64543 — dots.ocr wrong output at TP > 1 | <https://github.com/vllm-project/vllm/issues/64541> | **broken (unreleased fix)** | Issue closed 2026-11-08 by PR #64543 "Fix dots_ocr vision tower QKV split for TP > 1" (merged 2026-11-08, commit `b65f945008`, not an ancestor of v0.33.0). Reported on 0.30.0; the PR confirms on Ascend 910B3 and on CUDA (2× A800), and names `dots.mocr` as carrying the same defect. Workaround from the issue's control runs: `--mm-encoder-tp-mode data` (flag present at v0.33.0, `vllm/config/multimodal.py:385`, default `weights`). Applied to ocr.md §6. |
| v0.33.0 OCR roster — #61651, #63095, #61458 | <https://github.com/vllm-project/vllm/pull/61651> | new-feature | `registry.py` diff v0.32.0→v0.33.0 adds `RadioMBartPrefixForCausalLM` (`nemotron_parse3_5`), `ParseAuxMTPModel`, `MiniCPMOcrForConditionalGeneration` (`minicpm_ocr`). Model IDs from `tests/models/registry.py` and `docs/models/supported_models.md` at v0.33.0; `nvidia/Nemotron-3.5-Parse`, `openbmb/MiniCPM-OCR-1.0`, `PaddlePaddle/PaddleOCR-VL` all 200 on the Hub API. "Parse 3.5 MTP" is in `_get_v1_model_runner_unsupported_features` (`vllm/config/vllm.py`). `enable_thinking: false` note from the #63095 body. #61458 (merged 2026-10-14) reports 34–85% more PaddleOCR-VL throughput on H100; #61838 adds `compile_mm_encoder` for it. Applied to ocr.md §2. |
| PR #61772 / #60164 / #63051 — token embeddings and late chunking on `/v1/embeddings` | <https://github.com/vllm-project/vllm/pull/61772> | new-feature | #61772 merged 2026-10-22 (online), #60164 merged 2026-10-13 (offline `LateChunkingParams`), #63051 merged 2026-10-22 (chunk-size bound); all in `git log v0.32.0..v0.33.0`. Behaviour and limits read from `docs/models/pooling_models/token_embed.md` at v0.33.0 ("Online late chunking"); the v0.32.0 page has no late-chunking section and lists only the Pooling API for token vectors. Applied to embedding.md §1. |
| PR #62859 — chunked embeddings dropped multimodal inputs | <https://github.com/vllm-project/vllm/pull/62859> | **broken / correctness** | Merged 2026-10-21; in `git log v0.32.0..v0.33.0`. `maybe_pre_process_chunked()` rebuilt inputs with `tokens_input()`, discarding multimodal payloads even when the input fit one chunk; now the whole batch is validated first and multimodal requests get HTTP 400. PR validated on `google/siglip-base-patch16-224` through `/v2/embed` and `/v1/embeddings`. Applied to embedding.md §7, SKILL.md version gates. |
| Issue #64845 / #60977 — EmbeddingGemma 2 rejects `dimensions` | <https://github.com/vllm-project/vllm/issues/64845> | **broken (unreleased fix)** | #64845 closed 2026-11-06 by PR #64885 (sets `matryoshka_dimensions = [128, 256, 512, 768]` in the model's config hook); #60977 closed 2026-11-06 by PR #60978 (`embedding_size` falls back to `embedding_dim`, 768, before `hidden_size`, 512). Both merged 2026-11-06, after the v0.33.0 tag. At v0.33.0 `EmbeddingGemma2ModelConfig` sets no matryoshka field and `ModelConfig.embedding_size` (`vllm/config/model.py:2137`) has no `embedding_dim` fallback. Workaround and the `[1, 512]` rejection of 768 are from the #64845 reproduction table. Applied to embedding.md §4. |
| v0.33.0 pooling roster — #62201, #62237 | <https://github.com/vllm-project/vllm/pull/62237> | new-feature | `registry.py` diff v0.32.0→v0.33.0 adds `Lfm2BidirectionalModel` (`lfm2`) and `ColUltraVBertForRetrieval` (`colultravbert`), plus the alias `ModernVBertModel` → `ColModernVBertForRetrieval`. #62201 merged 2026-10-26 (body: encoder-only attention, CLS pooling); #62237 merged 2026-10-19. ColUltraVBERT prompts from `docs/models/pooling_models/specific_models.md` at v0.33.0. `LiquidAI/LFM2.5-Embedding-350M` and `athrael-soju/ColUltraVBERT` 200 on the Hub API. Applied to embedding.md §4, reranking.md §2. |
| PR #62783 — JinaVL score token lost under truncation | <https://github.com/vllm-project/vllm/pull/62783> | **broken / correctness** | Merged 2026-10-22; in `git log v0.32.0..v0.33.0`. `CrossEncoderIOProcessor` appended the score token (id 100) before post-tokenization truncation, so right-side truncation removed it. PR table (`jinaai/jina-reranker-m0`, `truncate_prompt_tokens=28`): reference 0.9831 / 0.8146, before 0.9857 / 0.9563, after 0.9830 / 0.8142; with `-1` on 672-token templates the irrelevant document scored 0.9980 against 0.9380 for the relevant one. Adds `reserve_tokens` in `vllm/entrypoints/pooling/utils.py:241`. No change for other cross-encoders. Applied to reranking.md §2, SKILL.md version gates. |
| LLM-based rerankers need a score template and overrides | `vllm-project/vllm` at `v0.33.0` `docs/models/pooling_models/scoring.md:44-96`, `examples/pooling/score/template/`, `tests/models/registry.py:789,806` | **broken (content)** | reranking.md §2 listed `BAAI/bge-reranker-v2-gemma`, `mixedbread-ai/mxbai-rerank-large-v2` and `nvidia/llama-nemotron-rerank-1b-v2` as plain `--runner pooling`. Upstream's table assigns each a score template (`bge-reranker-v2-gemma.jinja`, `mxbai_rerank_v2.jinja`, `nemotron-rerank.jinja`) and its notes give the `--hf-overrides` needed to load the official gemma and mxbai checkpoints; the registry test entry for the nemotron reranker sets `trust_remote_code=True`. Same rows at v0.32.0 (the only diff in that range is a LoRA tick). Only BERT / RoBERTa / XLM-RoBERTa / ModernBERT / mGTE rows carry "N/A" for the template. Applied to reranking.md §2, SKILL.md pitfall 3. |

## 2026-10-18 freshen (v0.30.0 → v0.32.0)

Full pass: every row below re-probed (45 GitHub/docs/blog URLs 200 via bare
curl; 80 issue/PR numbers in one GraphQL query — 74 PRs MERGED, issues #32588
and #47172 OPEN, #9255/#15216/#48443/#48831 CLOSED as the rows say; first
release of every merged PR re-derived by `git merge-base --is-ancestor`
against v0.18.0…v0.32.0; source anchors read with `git show v0.32.0:<path>`).
Release notes walked: v0.31.0 (2026-10-05), v0.32.0 (2026-10-18).

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| vLLM v0.32.0 (latest) | <https://github.com/vllm-project/vllm/releases/tag/v0.32.0> | 2026-10-18 | version-drift | Published 2026-10-18. All source probes in this pass at the `v0.32.0` tag. v0.31.0 published 2026-10-05. |
| PR #58830 — per-request mm kwargs gated | <https://github.com/vllm-project/vllm/pull/58830> | 2026-10-18 | **deprecation / breaking** | v0.31.0. `BaseFrontendArgs.trust_request_mm_kwargs` default False (`vllm/entrypoints/launchers/cli_args.py:99`); enforced in online rendering and pooling/scoring `_init_ctx`. Server-level `--mm-processor-kwargs`/`--media-io-kwargs` and offline `LLM` unchanged. Applied to SKILL.md v0.31/v0.32 section, stt.md §6. |
| PR #58364 — torchcodec-first `auto` audio decode | <https://github.com/vllm-project/vllm/pull/58364> | 2026-10-18 | **new-default** | v0.32.0 (tag ancestry). Diff flips `vllm/multimodal/media/audio.py` `auto` from soundfile → torchcodec → PyAV to torchcodec → soundfile → PyAV; only ImportError (and soundfile format-detection failure) defers. Also trims Vorbis tail padding on FFmpeg < 5. `torchcodec >= 0.14` is in `requirements/cuda.txt`, `cpu.txt`, `xpu.txt` (not `rocm.txt`) at both v0.30.0 and v0.32.0. Supersedes the order in the #51826 row. Applied to SKILL.md STT cheat-sheet, stt.md §6. |
| PR #57498 — chunked long-text embedding normalization | <https://github.com/vllm-project/vllm/pull/57498> | 2026-10-18 | **broken / correctness** | v0.31.0. Multi-chunk aggregates under `enable_chunked_processing` were averages of normalized chunks without re-normalization (PR repro: norm 0.707). Applied to embedding.md §7, SKILL.md. |
| PR #57666 — reranker tokenization with `max_tokens_per_doc` | <https://github.com/vllm-project/vllm/pull/57666> | 2026-10-18 | **broken / correctness** | v0.31.0. For non-separator rerankers a positive, non-binding limit changed the prompt and score; separator-based rerankers unchanged. Applied to reranking.md §3, SKILL.md. |
| PR #57347 — JinaVL label config | <https://github.com/vllm-project/vllm/pull/57347> | 2026-10-18 | broken (fixed) | v0.31.0. Text config kept `num_labels=2`, so jina-reranker-m0 weights failed to load. Applied to reranking.md §2. |
| PR #57769 / #56912 — Whisper / Qwen2-Audio > 30 s | <https://github.com/vllm-project/vllm/pull/57769> | 2026-10-18 | broken (fixed) | v0.31.0. Regression from #53275 (v0.29.0, `truncation=False` to the HF processor). Offline `LLM.generate`/chat-path clips > 30 s killed the engine; `/v1/audio/*` unaffected (server chunks). Applied to stt.md §9. |
| PR #40337 — flash-maxsim kernel | <https://github.com/vllm-project/vllm/pull/40337> | 2026-10-18 | new-feature | v0.32.0. Engine-side fused late-interaction scorer; `--no-enable-flash-late-interaction` (frontend `cli_args.py`) is mirrored into `PoolerConfig.enable_flash_late_interaction` (`vllm/config/pooler.py:66`). Corrects reranking.md's "env flag" wording. |
| PR #60254 / #60289 — EmbeddingGemma 2 | <https://github.com/vllm-project/vllm/pull/60254> | 2026-10-18 | new-feature | v0.32.0. `EmbeddingGemma2Model` in registry; `google/embeddinggemma-2` 200 on the Hub API. Serve line and `--limit-mm-per-prompt` encoder skipping from the PR body. Applied to embedding.md §4. |
| PR #60415 — zerank-2 template | <https://github.com/vllm-project/vllm/pull/60415> | 2026-10-18 | new-feature | v0.32.0. `examples/pooling/score/template/zerank2.jinja`; serve line from `docs/models/pooling_models/scoring.md:95`. Applied to reranking.md §2. |
| PR #59827 — Nemotron 3.5 ASR | <https://github.com/vllm-project/vllm/pull/59827> | 2026-10-18 | new-feature (out-of-tree) | v0.32.0. The release note reads as in-tree support; the merged diff only adds `Nemotron3_5AsrForRNNT` to `_OOT_SUPPORTED_MODELS` in `registry.py`, pointing at <https://github.com/Sohaib-Ahmed21/vllm-nemotron-asr-plugin> (200). Applied to stt.md §3. |
| PR #59417 — DeepSeek-OCR zero-sum pixels | <https://github.com/vllm-project/vllm/pull/59417> | 2026-10-18 | broken (fixed) | v0.32.0. Zero-sum normalized pixel tensor returned `None` from `embed_multimodal` and killed EngineCore; OCR-1, OCR-2, Unlimited-OCR. Applied to ocr.md §6. |
| PR #60022 — raster-format allowlist | <https://github.com/vllm-project/vllm/pull/60022> | 2026-10-18 | deprecation | v0.32.0. `ALLOWED_IMAGE_FORMATS` in `vllm/multimodal/image.py`; EPS/WMF denied. Applied to ocr.md §5. |
| PR #50931 — MRV2 decoder token-wise pooling | <https://github.com/vllm-project/vllm/pull/50931> | 2026-10-18 | **version-drift (stale claim)** | First ships v0.28.0. Removed `_get_enabled_tasks` and the encoder-only restriction; the skill still described v0.27.x behaviour. At v0.32.0 `_SUPPORTED_TASKS` = embed, classify, token_embed, token_classify, embed&token_classify (no `plugin`). Applied to runner-flags.md §11, embedding.md §4. |
| MRV1 still present at v0.32.0 | v0.32.0 `vllm/config/vllm.py` `use_v2_model_runner` | 2026-10-18 | version-drift | Skill said removal targeted v0.32 and "nowhere to fall back to"; `VLLM_USE_V2_MODEL_RUNNER=0` still returns V1 at v0.32.0, and the unsupported-feature fallback list (`_get_v2_model_runner_unsupported_features`) no longer names SP, elastic EP or custom logits processors. Applied to runner-flags.md §11, SKILL.md. |
| Qwen3 reranker template path | v0.32.0 `examples/pooling/score/template/qwen3_reranker.jinja` | 2026-10-18 | **broken** | `examples/templates/qwen3_reranker.jinja` exists at none of v0.20.0, v0.27.0, v0.30.0, v0.32.0. Upstream's own startup warning (#56017, `io_processor.py:461-475`) names the `examples/pooling/score/template/` path. Applied to SKILL.md, reranking.md. |
| STT roster class names | v0.32.0 `vllm/model_executor/models/registry.py`, files referencing `SupportsTranscription` | 2026-10-18 | broken | Implementers: cohere_asr, fireredasr2, funasr, gemma3n_mm, glmasr, granite_speech, kimi_audio, moss_transcribe_diarize, qwen3_asr, qwen3_omni_moe_thinker, voxtral, whisper. Qwen2-Audio, Ultravox, MiniCPM-O are not implementers (chat only). Class fixes: `CohereAsrForConditionalGeneration`, `KimiAudioForConditionalGeneration`, `Qwen3ASRForConditionalGeneration`; GLM-ASR, Granite Speech added. Applied to stt.md §3. |
| OCR roster class names | v0.32.0 `registry.py` | 2026-10-18 | broken | `GlmOcrForConditionalGeneration` (not `GlmOcrForCausalLM`), `GlmOcrMTP`, `NemotronParseForConditionalGeneration`, `QianfanOCRForConditionalGeneration`, `UnlimitedOCRForCausalLM`, `LightOnOCRForConditionalGeneration`. Anchors: `deepseek_ocr.py:362`, `deepseek_ocr2.py:234`, `dots_ocr.py` 770 lines. GUNDAM constants `BASE_SIZE=1024`/`IMAGE_SIZE=640`/`CROP_MODE=True` in `vllm/transformers_utils/processors/deepseek_ocr.py:21-23`. Applied to ocr.md. |
| `SequencePoolingType` / `TokenPoolingType` split | v0.32.0 `vllm/config/pooler.py:16-20` | 2026-10-18 | broken (content) | Found 2026-09-22 but not applied then; embedding.md §2 still listed ALL/STEP as sequence types. Applied now. |
| Matryoshka bound | v0.32.0 `vllm/pooling_params.py:164-193` | 2026-10-18 | fresh (precision) | Bound is `ModelConfig.embedding_size` (since v0.24.0), which falls back to `hidden_size`; raises `VLLMValidationError`. Applied to embedding.md §3, SKILL.md wording. |
| HF model IDs | `https://huggingface.co/api/models/<id>` | 2026-10-18 | broken (2) | 40 IDs probed. `mxbai/mxbai-rerank-large-v2` and `jinaai/jina-embeddings-v5` return 401 (no such repo) → `mixedbread-ai/mxbai-rerank-large-v2`, `jinaai/jina-embeddings-v5-text-small`. `rednote-hilab/dots.ocr` 307-redirects to `dots-studio/dots.ocr` (left as is; resolves). Applied to reranking.md §2, embedding.md §6. |
| Red Hat STT posts, DeepSeek-OCR recipe, pooling docs | (URLs in stt.md, ocr.md, SKILL.md) | 2026-10-18 | fresh / one claim removed | All 200. Recipe page contains the three flags plus `ngram_size=30`, `window_size=90`, `128821`. 2025-06-10 post names `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.0.0`; 2026-03-06 post names `RedHatAI/whisper-large-v3-turbo-FP8-dynamic`. Neither contains the "real-time factor ≫1 on a single L40S" claim → removed from stt.md §8. |
| Smaller precision fixes | — | 2026-10-18 | version-drift | MOSS-Transcribe-Diarize first ships v0.26.0 (SKILL.md and stt.md said v0.25.0, contradicting the #47729 row); MRV2 pooling PRs #49331/#48791/#50293/#50574/#50661 all first ship v0.27.0; #33686/#36818 ship v0.18.0, not v0.20.0; mean-pool `index_add` (#38559) is v0.20.0, not "v0.16+"; `parse.py` `audio_resample_method` default now at line 603. |
| Out of scope — v0.31/v0.32 items not applied | release notes | 2026-10-18 | not applicable | LoRA for VoyageQwen3/RoBERTa/BERT embedders (#57708, #58884, #61033) and seq-cls `modules_to_save`/per-adapter `num_labels` (#53555, #57766); chunked-embedding padding cap (#56505); BERT raw-logit heads (#57664); generative-scoring cancellation / `cache_salt` (#57729, #58788, #60841); chunked `/v1/embeddings` `cache_salt` (#47696); pooling mm-cache-miss crash (#58975); Qwen3-ASR EAGLE3 / processor parity (#52824, #57146); Voxtral realtime OOM (#45022); Nemotron Parse tied `lm_head` (#60272); CPU W4A16 Whisper (#58268); `IOProcessor.output_to_response` removal (#60923). Recorded so a future pass does not re-research them. |

## 2026-09-23 release-note fold-in (v0.29.0 → v0.30.0)

Scoped pass: worked the v0.30.0 release notes for items on this skill's
surface (pooling/rerank/STT/OCR), not a full re-verification of every
existing claim (that pass ran 2026-09-22, see the freshen note above).

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| vLLM v0.30.0 | <https://github.com/vllm-project/vllm/releases/tag/v0.30.0> | 2026-09-23 | new-feature | Tag date 2026-09-21. All source probes in this pass were made against the `v0.30.0` tag. |
| PR #51826 / #55642 — torchcodec audio backend | <https://github.com/vllm-project/vllm/pull/51826> | 2026-09-23 | new-feature | `AUDIO_BACKENDS = ("auto","soundfile","pyav","torchcodec")` in `vllm/multimodal/media/audio.py`. `auto` tried soundfile, then torchcodec, then pyav at v0.30.0 — **superseded by #58364 (v0.32.0): torchcodec first**. Select via `--media-io-kwargs '{"audio":{"audio_backend":"torchcodec"}}'`. Applied to SKILL.md STT cheat-sheet + v0.30.0 section, stt.md §6. |
| PR #52598 — torchaudio default resampler | <https://github.com/vllm-project/vllm/pull/52598> | 2026-09-23 | deprecation / new-default | `MultiModalDataParser.__init__`'s `audio_resample_method` default is `"torchaudio"` at v0.30.0 (`vllm/multimodal/parse.py:609` at v0.30.0, `:603` at v0.32.0), was `"pyav"`. torchaudio is already a standard dependency (`requirements/cuda.txt`, `cpu.txt`, `rocm.txt`, `xpu.txt`). Applied to SKILL.md + stt.md §6. |
| PR #54241 / #54918 — media_io_kwargs in mm cache hash, scoped by modality | <https://github.com/vllm-project/vllm/pull/54241> | 2026-09-23 | **broken / correctness** | Before: `media_io_kwargs` (e.g. `audio_backend`) was not part of the multimodal cache hash and hash kwargs were shared across modalities, so switching backend/kwargs between requests could reuse a stale cached decode. Applied to SKILL.md v0.30.0 section, stt.md §6. |
| PR #56017 — Qwen3 reranker missing-template warning | <https://github.com/vllm-project/vllm/pull/56017> | 2026-09-23 | new-feature (diagnostic) | `CrossEncoderIOProcessor` now `logger.warning`s naming the model id and `qwen3_reranker.jinja` when `is_original_qwen3_reranker=true` and no chat template is configured, instead of failing silently into random-looking scores. Applied to SKILL.md pitfall 5, reranking.md §2. |
| Out of scope for this skill — video-only v0.30.0 items | release notes "Multimodal"/"Correctness"/"Security" bullets | 2026-09-23 | not applicable | Request-controlled video sampling caps for `GLMGAVideoBackend` (#54935) and Qwen-VL (#56729); pruned sliding-window tiles for Gemma 4 video prompts (#53147); empty video URLs with multimodal UUIDs (#54220); base64 video validation (#54323); `VLLM_MM_HASHER_ALGORITHM` removal (#55353, replaced by `MultiModalConfig.mm_hasher_algorithm` / `--mm-hasher-algorithm`, confirmed absent from `vllm/envs.py` at v0.30.0 and present at v0.29.0). None touch pooling/rerank/STT/OCR; the hasher env var belongs to `vllm-configuration`'s catalog. Recorded here so a future pass does not re-research the same "in scope?" question. |

## 2026-08-11 freshen (rebaseline v0.25.1 → v0.27.0)

Two minors of drift (v0.26.0 published 2026-07-27, v0.27.0 published
2026-08-10). Unlike the last two passes, this one found a **correctness**
regression rather than a validation tightening — and one long-stale claim the
release notes could never have surfaced, because the change predates the
skill's own previous baseline.

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| vLLM v0.27.0 | <https://github.com/vllm-project/vllm/releases/tag/v0.27.0> | 2026-08-11 | new-feature | Published 2026-08-10. **All source probes in this pass were made against the `v0.27.0` tag.** |
| vLLM v0.27.1 (latest) | <https://github.com/vllm-project/vllm/releases/tag/v0.27.1> | 2026-08-11 | fresh | Published 2026-08-11 10:47Z, mid-pass. Patch release with exactly one change — "Support quantized DSpark Markov heads" (#50424) — which touches no pooling, rerank, STT or OCR surface, so the v0.27.0 probes above stand. The `v0.27.1` container images were pushed 10:24-10:42Z, *before* the 10:47Z release — image availability, not the PyPI wheel, gates this stack. Not restamped onto individual claims, because it was not probed. |
| vLLM v0.26.0 | <https://github.com/vllm-project/vllm/releases/tag/v0.26.0> | 2026-08-11 | new-feature | Published 2026-07-27. |
| PR #48901 — wrong pooling scores under chunked prefill + `torch.compile` | <https://github.com/vllm-project/vllm/pull/48901> | 2026-08-11 | **broken / correctness** | Merged 2026-07-17, v0.26.0. Fixes #48831. LAST-pooling models (PR names `Qwen/Qwen3-Reranker-0.6B`) returned wrong scores when a query+doc pair was chunk-prefilled, *only* under `torch.compile`. Repro: ~0.83 unchunked → ~0.01–0.36 chunked, varying run-to-run. `--enforce-eager` always correct; offline batch path happened not to chunk. Buffer-lifetime race in the compiled forward — cosine ~0.47 vs eager, no NaN/zeros, so the wrong value is *plausible*. **Invalidates past results, not just future ones.** Applied to SKILL.md pitfall 5 + new baseline section, reranking.md §2, embedding.md §7. |
| `--task` flag absent from the CLI | v0.27.0 `vllm/engine/arg_utils.py`, `vllm/config/model.py`, `docs/models/pooling_models/README.md` | 2026-08-11 | **deprecation → removed** | Source probe, not a release note. No `task` field in `ModelConfig` and no `--task` in `arg_utils.py` at v0.22.0, v0.25.1 **or** v0.27.0; the pooling doc documents only `--runner`/`--convert`. The skill had claimed since v0.20.0 that `--task` "still works with a warning" — that was already stale at its own previous baseline. Applied to SKILL.md mental model + pitfall 1, runner-flags.md §1/§3/§7. |
| `score` / `encode` pooling task names | v0.27.0 `vllm/tasks.py` | 2026-08-11 | **deprecation → removed** | `check_removed_pooling_task` raises `VLLMValidationError` naming the replacement (`classify`; `token_embed`/`token_classify`). Previously described as "deprecated". Applied to runner-flags.md §3/§7. |
| MRV2 pooling series — #49331, #48791, #50293, #50574, #50661 | <https://github.com/vllm-project/vllm/pull/50661> | 2026-08-11 | new-feature | All five first ship v0.27.0 (tag ancestry, 2026-10-18). #50661 completes encoder-only pooling for every in-tree task. Before it, BGE-M3 **failed to start** on V2 (`get_pooling_task()` ranks `embed&token_classify` first, then the runner rejected it). Applied to runner-flags.md §11. |
| PR #48290 — enable MRV2 for pooling by default | <https://github.com/vllm-project/vllm/pull/48290> | 2026-09-15 | **MERGED 2026-08-19** | Merge `08afae27`. Ancestry in-clone: **not** in v0.28.0, **is** in v0.29.0 — it landed after the v0.28.0 cut and no v0.28.1 was released, so v0.29.0 (2026-09-09) is the first release where pooling defaults to MRV2. Through v0.28.0 the earlier reading holds: `_is_default_v2_model_runner_model` returns False for `runner_type != "generate"` and `VLLM_USE_V2_MODEL_RUNNER` defaults to `None`. |
| MRV2 token-task restriction | v0.27.0 `vllm/v1/worker/gpu/pool/pooling_runner.py:65-78` | 2026-08-11 | new-feature | **Superseded: removed by #50931 (v0.28.0), see the 2026-10-18 row.** `_get_enabled_tasks` subtracts `token_embed`/`token_classify` unless `attn_type == "encoder_only"`. Startup error names the escape hatch `VLLM_USE_V2_MODEL_RUNNER=0`. |
| STT entrypoint package moved | v0.27.0 `vllm/entrypoints/speech_to_text/` | 2026-08-11 | **broken (source anchors)** | `vllm/entrypoints/openai/speech_to_text/` returns 404 at v0.27.0. New layout: `base/`, `transcription/`, `translation/`, `realtime/`, `factories.py`. Every anchor in stt.md §2/§11 pointed at the dead path. Applied. |
| PR #48543 — `diarized_json` | <https://github.com/vllm-project/vllm/pull/48543> | 2026-08-11 | new-feature | Merged 2026-07-29, v0.27.0, closes #48443. Transcriptions only (translations unchanged, matching the OpenAI contract). Model-gated, fail-closed parser; `json`/`text`/`verbose_json` paths untouched. Applied to stt.md §2 + roster row. |
| PR #41131 — cumulative STT chunk timestamps | <https://github.com/vllm-project/vllm/pull/41131> | 2026-08-11 | **broken (fixed)** | Merged 2026-07-27, v0.27.0 (tag-ancestry confirmed). **Issue #32588 is still OPEN** — the code shipped but the issue was never closed or linked, so its open state is not evidence the bug survives. `split_audio` searches a 1 s window before the nominal 30 s cut, but offsets assumed an exact 30 s; error accumulated ~1 s/chunk (~5 s over 10 chunks). Text was always right — only timestamps drifted. `TranscriptionSegment.seek` is now `int`. Applied to stt.md §6. |
| PR #45839 — translation-API sampling params | <https://github.com/vllm-project/vllm/pull/45839> | 2026-08-11 | new-feature | Merged 2026-07-21, v0.27.0. Adds `top_p`, `top_k`, `min_p`, frequency/repetition/presence penalties and `vllm_xargs` to `/v1/audio/translations`; defaults neutral. Applied to stt.md §5. |
| PR #49403 — MOSS-TD max audio duration | <https://github.com/vllm-project/vllm/pull/49403> | 2026-08-11 | **broken (fixed)** | Merged 2026-07-25, v0.27.0. MOSS-TD treated Whisper's 30 s chunk as the whole-item maximum, reporting ~375 `max_tokens_per_mm_item`, so encoder cache fell back to `max_num_batched_tokens` and longer audio was **rejected at request time**. Now sized from MOSS-TD's real 90-minute ceiling (67,500 audio embedding tokens). Applied to stt.md roster row. |
| PR #50688 — jina-embeddings-v5-text-nano | <https://github.com/vllm-project/vllm/pull/50688> | 2026-08-11 | new-feature | Merged 2026-08-03, v0.27.0. Same `JinaEmbeddingsV5Model` architecture, dispatched on `is_decoder`: `-small` = Qwen3 decoder, `-nano` = bidirectional EuroBERT encoder with `EncoderOnlyAttention`. Applied to embedding.md §4. |
| New pooling architectures in v0.26.0 | v0.27.0 `vllm/model_executor/models/registry.py` | 2026-08-11 | new-feature | Confirmed registered: `BertForMaskedLM` (#48463), `RobertaForTokenClassification` / `XLMRobertaForTokenClassification` (#47991); LongCat-Flash-Lite n-gram embedding (#47857) from the release notes. Recorded in embedding.md footer. |
| DeepSeek-OCR recipe constants | v0.27.0 `vllm/model_executor/models/deepseek_ocr.py` | 2026-08-11 | version-drift | `NGramPerReqLogitsProcessor` still present, and `mm_processor_cache_gb` still in `vllm/config/model.py` — all three recipe flags valid. But the class reads `whitelist_token_ids`/`ngram_size`/`window_size` from per-request `extra_args` (lines 140-195); it does not hard-code them, so "enforces" overstated it. GUNDAM sizes are imported constants (`BASE_SIZE`/`IMAGE_SIZE`/`CROP_MODE`) and were not re-read upstream. Applied to ocr.md §3. |

**Ecosystem removals, none on this skill's surface:** TeleChat (#47989),
Persimmon and Fuyu (#48096) in v0.26.0; Plamo2 (#49729) and Ouro (#49786) in
v0.27.0. Also `max_num_partial_prefills` / `max_long_partial_prefills` removed
in v0.27.0 (#49244) — belongs to the scheduler surface, recorded here only
because an image bump surfaces it.

**Still not probed:** HuggingFace model cards, the Red Hat Whisper/RHAIIS blog,
the `docs.vllm.ai` pooling doc tree, and the DeepSeek-OCR recipes page — all
listed under "Non-probed references" below and unchanged in status.

## 2026-07-21 freshen (rebaseline v0.21.0 → v0.25.1)

Four minors of drift. Probed every release body v0.22.0 → v0.25.1 for the
pooling / embedding / rerank / STT / OCR surface, then read the PRs behind
each hit. **The runner surface did not move** — no `--runner` / `--convert` /
`PoolerConfig` change since v0.20.0 — but two request-validation tightenings
in v0.24.0 convert previously-successful requests into errors.

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| vLLM v0.25.1 (latest) | <https://github.com/vllm-project/vllm/releases/tag/v0.25.1> | 2026-07-21 | new-feature | Published 2026-07-14. New baseline. Patch release, 19-line body, nothing on this skill's surface. |
| vLLM v0.22.0 → v0.25.0 | <https://github.com/vllm-project/vllm/releases> | 2026-07-21 | new-feature | v0.22.0 (2026-05-29), v0.23.0 (2026-06-15), v0.24.0 (2026-06-29), v0.25.0 (2026-07-11). |
| PR #46313 — matryoshka upper bound | <https://github.com/vllm-project/vllm/pull/46313> | 2026-07-21 | **deprecation / breaking** | Merged 2026-06-22, v0.24.0. `PoolingParams._set_default_parameters` checked only `dimensions >= 1` for MRL models lacking an explicit list, then sliced `[..., :d]` — oversized values **silently returned a `hidden_size`-length vector**. Now raises. Mirrors sglang `_validate_for_matryoshka_dim`. Applied to SKILL.md + embedding.md §3. |
| PR #46119 — rerank `top_n` validation | <https://github.com/vllm-project/vllm/pull/46119> | 2026-07-21 | **deprecation / breaking** | Merged 2026-06-22, v0.24.0. `top_n=-1` was silently treated as `0`. `top_n=0` still means "all"; oversized values still accepted. Applied to reranking.md. |
| PR #45173 — `/v1/embeddings` messages + `chat_template_kwargs` | <https://github.com/vllm-project/vllm/pull/45173> | 2026-07-21 | new-feature | Merged 2026-06-15, v0.24.0. Message-shaped input to `/v1/embeddings` was previously **rejected at validation**, and `chat_template_kwargs` never reached the renderer; only the top-level messages extension worked. This is now the supported path for instruction-style embedders. Applied to embedding.md §1. |
| PR #43260 — truncation side | <https://github.com/vllm-project/vllm/pull/43260> | 2026-07-21 | **unverifiable → refuted** | Merged 2026-05-22, v0.22.0. The release note reads "truncation side for OpenAI endpoints", which invites the assumption that `/v1/embeddings` gained `truncation_side`. The PR body scopes it to `/v1/completions` and `/v1/chat/completions` only. **Superseded 2026-10-18:** pooling requests already carried `truncation_side` before #43260 (`PoolingBasicRequestMixin`, present at v0.21.0 and v0.32.0), so `/v1/embeddings`, `/score` and `/rerank` do accept it; the SKILL.md "not applicable" line was removed and the field documented in embedding.md §1. |
| PR #42370 / #42274 — STT entrypoint + test consolidation | <https://github.com/vllm-project/vllm/pull/42370> | 2026-07-21 | fresh | Merged 2026-05-12 / 2026-05-11, v0.22.0. Internal refactor following #41907. No endpoint or request-body change — `/v1/audio/transcriptions` and `/v1/audio/translations` are untouched. |
| PR #46564 — Unlimited OCR | <https://github.com/vllm-project/vllm/pull/46564> | 2026-07-21 | new-feature | Merged 2026-06-28, v0.25.0. `baidu/Unlimited-OCR`, benchmarked on OmniDocBench; Triton R-SWA backend in #47102. Added to ocr.md §2. |
| PR #47729 — MOSS-Transcribe-Diarize | <https://github.com/vllm-project/vllm/pull/47729> | 2026-09-15 | new-feature | Merged 2026-07-08; **first ships in v0.26.0**, not v0.25.0 — the merge commit is not an ancestor of v0.25.0 (published 2026-07-11, three days later). Tag-ancestry verified. `OpenMOSS-Team/MOSS-Transcribe-Diarize` — long-form transcription with timestamped speaker labels; Whisper-style encoder into a Qwen3 causal decoder. First diarizing model in the roster. Added to stt.md. |
| PR #47071 — pooled Whisper sliding-window KV sizing | <https://github.com/vllm-project/vllm/pull/47071> | 2026-07-21 | fresh (bugfix) | Merged 2026-07-01, v0.25.0. Voxtral Realtime's causal Whisper encoder expressed `SlidingWindowSpec.sliding_window` in encoder-token units while the pool used `block_pool_size` tokens per block, so the KV manager over-reserved encoder blocks by ~`block_pool_size`×. Memory-sizing fix only. |
| PR #46762 — realtime embeddings on MRv2 | <https://github.com/vllm-project/vllm/pull/46762> | 2026-07-21 | new-feature | Merged 2026-06-27, v0.25.0. Realtime models (Voxtral) need embeddings during decode too. |

**Ecosystem removals noted, none on this skill's surface:** PagedAttention
removed entirely in v0.25.0 (#47361); Transformers v4 support deprecated in
v0.24.0 (#45161); model families removed across v0.24.0/v0.25.0 (ERNIE,
Xverse, Dots1, Bamba, Mono-InternVL, Baichuan, Aquila, Grok, Tarsier/Tarsier2,
AyaVision/MusicFlamingo, Mantis). No pooling, rerank, STT or OCR model was
removed — recorded in SKILL.md because an operator bumping the image for an
unrelated reason can still be stranded.

**Still not probed this pass:** the HuggingFace model cards, the Red Hat
Whisper/RHAIIS blog, and the `docs.vllm.ai` pooling doc tree (all listed under
"Non-probed references" below and unchanged in status).

## 2026-05-28 freshen (rebaseline v0.20.0 → v0.21.0)

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| vLLM v0.21.0 release notes (latest) | <https://github.com/vllm-project/vllm/releases/tag/v0.21.0> | 2026-05-28 | new-feature | Published 2026-05-15. Current baseline. No runner/`--convert`/`PoolerConfig` breaking change vs v0.20.0; pooling deltas perf-only (#41163 AllPool +51%, #41433 GPU↔CPU sync elimination). New OCR arch Qianfan-OCR (#40136). |
| vLLM v0.20.0 release tag (date correction) | <https://github.com/vllm-project/vllm/releases/tag/v0.20.0> | 2026-05-28 | version-drift | `published_at` is 2026-04-27 (not 2026-04-23 as previously stated). Corrected across SKILL.md + 4 reference files. |
| vLLM v0.20.1 / v0.20.2 patch releases | <https://github.com/vllm-project/vllm/releases> | 2026-05-28 | new-feature | v0.20.1 (2026-05-04), v0.20.2 (2026-05-10) — patch releases between v0.20.0 and v0.21.0; no pooling/STT/OCR surface change. |
| PR #41163 — AllPool.forward +51% | <https://github.com/vllm-project/vllm/pull/41163> | 2026-05-28 | new-feature | Pooling perf win, shipped v0.21.0. Token-wise / `ALL` pooling (ColBERT, Jina-v4 multi-vector). |
| PR #41433 — pooling GPU↔CPU sync elimination | <https://github.com/vllm-project/vllm/pull/41433> | 2026-05-28 | new-feature | Pooling perf win, shipped v0.21.0. |
| PR #40136 — Qianfan-OCR | <https://github.com/vllm-project/vllm/pull/40136> | 2026-05-28 | new-feature | New OCR architecture, shipped v0.21.0. Added to ocr.md §2 roster. |

Note: probes for the v0.21.0 rebaseline were performed during the recon
stage of this freshen pass (gh api against vllm-project/vllm releases,
2026-05-28). Internal-contradiction fixes applied this pass
(`max_tokens_per_doc` "late 2025" → v0.20.0/#38827; async-scheduling
"2026-01" → 2026-04-12; logit rename "late 2025" → v0.20.0/#39530) were
verified against the skill's own dated rows below, not online.

## 2026-04-24 freshen (against vLLM v0.20.0 released 2026-04-27)

| Ref | URL | Last verified | Classification | Notes |
|---|---|---|---|---|
| PR #38800 — jina-reranker-v3 | <https://github.com/vllm-project/vllm/pull/38800> | 2026-08-18 | fresh | Merged 2026-04-10; shipped v0.20.0 (Model Support section). |
| PR #38827 — `max_tokens_per_doc` in `/rerank` | <https://github.com/vllm-project/vllm/pull/38827> | 2026-08-18 | fresh | Merged 2026-04-13; shipped v0.20.0 (API section). |
| PR #34539 — Generative Scoring | <https://github.com/vllm-project/vllm/pull/34539> | 2026-08-18 | fresh | Merged 2026-03-31; shipped v0.20.0. Still flagged experimental in skill. |
| PR #39116 — ASR multi-chunk spacing fix | <https://github.com/vllm-project/vllm/pull/39116> | 2026-09-15 | version-drift | Merged 2026-04-09; **ships in v0.20.0 only** — `git tag --contains` on the merge commit. v0.19.1 published 2026-04-18, *after* the merge, and does not contain it: its branch was already cut. The floor here has now been wrong twice in the same direction ("v0.18+", then "≥v0.19.1"), both times by reasoning from dates. Corrected floor: **≥v0.20.0**. |
| PR #39592 — async scheduling OFF for pooling | <https://github.com/vllm-project/vllm/pull/39592> | 2026-08-18 | deprecation / new-default | Merged 2026-04-12; shipped v0.20.0. **Breaking** per release notes. Skill now calls this out as a landed default. |
| PR #39530 — `logit_bias/scale` → `logit_mean/sigma` | <https://github.com/vllm-project/vllm/pull/39530> | 2026-08-18 | deprecation | Merged 2026-04-13; shipped v0.20.0. **Breaking** rename; old names still accepted with warning. Skill now describes as landed. |
| Issue #15216 — Whisper OOM on 24 GB | <https://github.com/vllm-project/vllm/issues/15216> | 2026-08-18 | fresh | CLOSED, last updated 2025-10-20; referenced vLLM 0.8.0. Workaround (RedHatAI quants) still valid. |
| vLLM v0.20.0 release notes | <https://github.com/vllm-project/vllm/releases/tag/v0.20.0> | 2026-08-18 | fresh | Authoritative source for this freshen. Confirmed 5 of 6 PRs above plus Jina Embeddings v5 (PR #39575), redundant-sync pooling perf (+3.7%, PR #39113), and the `cprofile`/V0 deprecations. |

## Derived updates applied

- SKILL.md "Scheduled deprecations to plan for (v0.20)" → rewritten as
  "Landed in v0.20.0 (released 2026-04-27)" with breaking-change callouts
  and two new perf wins (#38559 mean-pool +5.9%, #39113 redundant-sync
  +3.7%).
- references/runner-flags.md §3 retitled "landed in v0.20.0"; §10 PR
  dates corrected (PRs merged 2026-03 through 2026-04, not 2025-11/12 or
  2026-01/02 as previously labelled). Added #39113.
- references/reranking.md §8 updated with merge dates + breaking-change
  note on #39530.
- references/stt.md §6 updated: #39116 is in v0.19.1 + v0.20.0 (not v0.18+). **Superseded 2026-09-15: it is v0.20.0 only — see the row above.**
- references/embedding.md §4 Jina v5 marked as landed via PR #39575 in
  v0.20.0.
- references/ocr.md: DeepSeek-OCR recipe unchanged; no v0.20.0 landing
  touches this flow.
- scripts/probe-endpoint.sh: unchanged — endpoints and probe semantics
  did not move in v0.20.0.

## Release history with no operator action (moved out of SKILL.md 2026-10-18)

Not re-probed when moved; numbers as last verified in the pass that added them.

- v0.21.0–v0.25.0 internals: #42267 offline pooling API split into
  `PoolingOfflineMixin`; #44593 proper pooling exceptions; #44410
  LoRA-adapter-name pooling fix; #44612 ASR CPU preprocessing 2.5× faster;
  #44999 / #45210 ColBERT `AutoWeightsLoader` plus query/document
  io-processor; #45640 Cohere `/v2/embed` input-exclusivity validation;
  #46762 realtime embeddings under MRV2; #47071 / #47437 pooled-Whisper
  sliding-window KV sizing.
- Architectures added: LLaVA-OneVision-2 (#44785).
- Removals off this surface: PagedAttention (#47361, v0.25.0); Transformers v4
  deprecated (#45161, v0.24.0); ERNIE, Xverse, Dots1, Bamba, Mono-InternVL
  (v0.24.0); Baichuan, Aquila, Grok, Tarsier/Tarsier2, AyaVision/MusicFlamingo,
  Mantis (v0.25.0); TeleChat (#47989), Persimmon and Fuyu (#48096) (v0.26.0);
  Plamo2 (#49729), Ouro (#49786), `max_num_partial_prefills` /
  `max_long_partial_prefills` (#49244) (v0.27.0).

## Previously non-probed references

Probed 2026-10-18 (see the 2026-10-18 rows above): Red Hat STT posts, the
DeepSeek-OCR recipes page, the `docs.vllm.ai` pooling docs, and every HF
model ID the skill names.

Next freshen triggers: v0.33+ release, MRV1 removal, new Jina embeddings
major, or a new native-multimodal reranker shipping. The runner surface stays
quiet while request validation and pooling correctness move underneath it:
grep release bodies for `pooling|rerank|embedding|matryoshka|top_n`, not just
for runner flags.
