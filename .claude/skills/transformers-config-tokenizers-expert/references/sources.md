# Sources

Dated index of every external reference this skill cites. `Last verified:`
stamps track when the ref was last checked against live content.
`freshen` mode re-probes these and updates the stamp.

Rows marked `<!-- ignore-freshen -->` are intentionally frozen (historical
refs).

---

## Transformers (upstream source + spec)

| URL | Purpose | Last verified |
|---|---|---|
| https://github.com/huggingface/transformers/blob/main/src/transformers/tokenization_utils_base.py | PreTrainedTokenizerBase, SPECIAL_TOKENS_ATTRIBUTES, property accessors | 2026-04-21 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/tokenization_utils_tokenizers.py | TokenizersBackend + passthrough | 2026-04-21 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/tokenization_python.py | PythonBackend | 2026-04-21 |
| https://github.com/huggingface/transformers/blob/v5.1.0/src/transformers/tokenization_mistral_common.py | MistralCommonBackend | 2026-04-21 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/utils/chat_template_utils.py | Jinja env, globals, render_jinja_template | 2026-04-21 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/generation/configuration_utils.py | GenerationConfig, eos_token_id Union[int, list[int]] | 2026-04-21 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/utils/hub.py | CHAT_TEMPLATE_FILE constants | 2026-04-21 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/models/auto/tokenization_auto.py | AutoTokenizer dispatcher | 2026-04-21 |
| https://github.com/huggingface/transformers/blob/main/MIGRATION_GUIDE_V5.md | v4→v5 consolidation notes | 2026-04-21 |
| https://github.com/huggingface/transformers/releases/tag/v5.0.0 | v5.0.0 GA notes | 2026-04-21 |
| https://huggingface.co/blog/tokenizers | Transformers v5 tokenizer blog | 2026-04-21 |

## Transformers issues + PRs

| URL | Purpose | Last verified |
|---|---|---|
| https://github.com/huggingface/transformers/issues/38182 | Gemma-3 IT EOS mismatch | 2026-04-21 |
| https://github.com/huggingface/transformers/issues/41870 | GemmaTokenizerFast SP inconsistency | 2026-04-21 |
| https://github.com/huggingface/transformers/issues/42914 | chat_template.jinja not cached offline | 2026-04-21 |
| https://github.com/huggingface/transformers/issues/43066 | DeepSeek-R1-Distill decoder shape regression | 2026-04-21 |
| https://github.com/huggingface/transformers/pull/43104 | v5 decoder doc clarification | 2026-04-21 |
| https://github.com/huggingface/transformers/issues/45205 | Gemma-4 chat_template not auto-loaded | 2026-04-21 |
| https://github.com/huggingface/transformers/issues/45356 | Kimi-K2.5 `</think>` decode regression 5.3→5.4 | 2026-04-21 |
| https://github.com/huggingface/transformers/pull/45359 | Fix for #45356 | 2026-04-21 |

## vLLM

| URL | Purpose | Last verified |
|---|---|---|
| https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/cli_args.py | --chat-template, --trust-request-chat-template, --default-chat-template-kwargs | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/chat_completion/serving.py | OpenAIServingChat init, request flow | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/engine/serving.py | trust_request_chat_template enforcement, kwargs merge | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/renderers/hf.py | safe_apply_chat_template, resolve_chat_template_kwargs allowlist | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/sampling_params.py | update_from_generation_config stop-token merge | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/v1/engine/input_processor.py | generation_config EOS merge call site | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/v1/engine/detokenizer.py | Fast/slow incremental detokenizer | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/tokenizers/detokenizer_utils.py | detokenize_incrementally word-boundary logic | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/tokenizers/registry.py | tokenizer_mode auto-detect (mistral/hf) | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/tokenizers/mistral.py | MistralTokenizer + Tekkenizer | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/serve/render/serving.py | adjust_request call site | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/abstract_tool_parser.py | Tool parser adjust_request contract | 2026-04-21 |
| https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/serve/tokenize/serving.py | /tokenize, /detokenize | 2026-04-21 |
| https://github.com/vllm-project/vllm/pull/27622 | chat_template_kwargs allowlist fix (v0.11.1) | 2026-04-21 |
| https://github.com/vllm-project/vllm/issues/25401 | tokenizer-mode mistral silently ignores --chat-template | 2026-04-21 |
| https://github.com/vllm-project/vllm/releases/tag/v0.11.1 | Shipped PR #27622 | 2026-04-21 |

## sglang

| URL | Purpose | Last verified |
|---|---|---|
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/entrypoints/openai/serving_chat.py | Kwargs dict-update, skip_special_tokens overrides, delta slicing | 2026-04-21 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/detokenizer_manager.py | DetokenizerManager subprocess, DecodeStatus | 2026-04-21 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/sampling/sampling_params.py | skip_special_tokens per-request | 2026-04-21 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/configs/model_config.py | _get_hf_eos_token_id union | 2026-04-21 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/speculative/spec_info.py | SpeculativeAlgorithm enum (no MTP entry) | 2026-04-21 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/parser/reasoning_parser.py | Registered reasoning parsers | 2026-04-21 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/parser/conversation.py | FastChat conversation-template registry | 2026-04-21 |
| https://github.com/sgl-project/sglang/issues/22510 | Streaming word-fragment report (red herring) | 2026-04-21 |
| https://github.com/sgl-project/sglang/pull/22549 | Fix: serving_chat.py double-slice | 2026-04-21 |
| https://github.com/sgl-project/sglang/commit/9e7dfcc151e4ba79457851019458567eabfc2764 | Merge commit | 2026-04-21 |

## HuggingFace model repos (verified 2026-04-21)

| URL | Purpose | Last verified |
|---|---|---|
| https://huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/tokenization_kimi.py | TikTokenTokenizer custom class | 2026-04-21 |
| https://huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/tokenizer_config.json | Kimi auto_map, EOS `[EOS]` | 2026-04-21 |
| https://huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/generation_config.json | eos_token_id 163586 | 2026-04-21 |
| https://huggingface.co/moonshotai/Kimi-K2-Instruct/discussions/31 | EOS ambiguity | 2026-04-21 |
| https://huggingface.co/moonshotai/Kimi-K2.5/discussions/7 | Slow tokenizer note | 2026-04-21 |
| https://huggingface.co/moonshotai/Kimi-K2.6/blob/main/tokenizer_config.json | Half-fix EOS split-brain | 2026-04-21 |
| https://huggingface.co/google/gemma-4-E4B/blob/main/tokenizer_config.json | GemmaTokenizer + Gemma3Processor | 2026-04-21 |
| https://huggingface.co/google/gemma-4-E4B/blob/main/generation_config.json | eos_token_id 1 | 2026-04-21 |
| https://huggingface.co/google/gemma-4-26B-A4B-it/blob/main/generation_config.json | eos_token_id [1, 106, 50] | 2026-04-21 |
| https://huggingface.co/zai-org/GLM-5.1/blob/main/tokenizer_config.json | TokenizersBackend + list extra_special_tokens | 2026-04-21 |
| https://huggingface.co/zai-org/GLM-5.1/blob/main/generation_config.json | Three-ID EOS [154820, 154827, 154829] | 2026-04-21 |
| https://huggingface.co/zai-org/GLM-5.1-FP8/blob/main/tokenizer_config.json | FP8 variant config | 2026-04-21 |
| https://huggingface.co/zai-org/GLM-4.6/blob/main/tokenizer_config.json | PreTrainedTokenizer + dict extra_special_tokens | 2026-04-21 |
| https://huggingface.co/Qwen/Qwen3-0.6B/blob/main/tokenizer_config.json | `<\|im_end\|>` dual role | 2026-04-21 |
| https://huggingface.co/Qwen/Qwen3.5-35B-A3B-Base/blob/main/tokenizer_config.json | Base flips EOS to `<\|endoftext\|>` | 2026-04-21 |
| https://huggingface.co/deepseek-ai/DeepSeek-V3/blob/main/tokenizer_config.json | LlamaTokenizerFast, no added_tokens_decoder | 2026-04-21 |
| https://huggingface.co/deepseek-ai/DeepSeek-V3/raw/main/tokenizer.json | 7.85 MB LFS added_tokens | 2026-04-21 |
| https://huggingface.co/deepseek-ai/DeepSeek-R1/blob/main/tokenizer_config.json | `<think>` only in chat_template | 2026-04-21 |
| https://huggingface.co/microsoft/phi-4/blob/main/tokenizer_config.json | Inverted BOS/EOS | 2026-04-21 |
| https://huggingface.co/mistralai/Mistral-Small-24B-Instruct-2501/blob/main/tokenizer_config.json | LlamaTokenizer + [INST] wrappers | 2026-04-21 |
| https://huggingface.co/nvidia/nemotron-colembed-vl-4b-v2/commit/e707da79538edf17c86abd24d42d603eaec9b3cb | extra_special_tokens list-vs-dict fix | 2026-04-21 |

## Other

| URL | Purpose | Last verified |
|---|---|---|
| https://github.com/QwenLM/Qwen3/issues/927 | config.json vs tokenizer_config EOS drift | 2026-04-21 |
| https://kaitchup.substack.com/p/qwen3-when-im_end-suddenly-becomes | Qwen3 base-vs-instruct EOS flip | 2026-04-21 |

