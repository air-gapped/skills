# Sources

Freshened: 2026-10-27 — every row probed; all 71 URLs resolve after repointing two vLLM files that moved, and vLLM v0.32.0's transformers floor now clears the three tokenizer-path fixes.

Dated index of every external reference this skill cites. The header stamp
is authoritative; per-row `Last verified` dates are legacy.

The stale-bot trap this file documents was reproduced on a second issue (#41870, closed `COMPLETED` by `github-actions[bot]` with no fix), confirming it is general transformers bot behaviour rather than a one-off — treat `COMPLETED` in that repo as no evidence of a fix without checking the closer.

Rows marked `<!-- ignore-freshen -->` are intentionally frozen (historical
refs).

---

## Transformers (upstream source + spec)

| URL | Purpose | Last verified |
|---|---|---|
| https://github.com/huggingface/transformers/blob/main/src/transformers/tokenization_utils_base.py | PreTrainedTokenizerBase, SPECIAL_TOKENS_ATTRIBUTES, property accessors | 2026-09-15 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/tokenization_utils_tokenizers.py | TokenizersBackend + passthrough | 2026-09-15 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/tokenization_python.py | PythonBackend | 2026-09-15 |
| https://github.com/huggingface/transformers/blob/v5.1.0/src/transformers/tokenization_mistral_common.py | MistralCommonBackend | 2026-09-15 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/utils/chat_template_utils.py | Jinja env, globals, render_jinja_template | 2026-09-15 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/generation/configuration_utils.py | GenerationConfig, eos_token_id Union[int, list[int]] | 2026-09-15 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/utils/hub.py | CHAT_TEMPLATE_FILE constants | 2026-09-15 |
| https://github.com/huggingface/transformers/blob/main/src/transformers/models/auto/tokenization_auto.py | AutoTokenizer dispatcher | 2026-09-15 |
| https://github.com/huggingface/transformers/blob/main/MIGRATION_GUIDE_V5.md | v4→v5 consolidation notes | 2026-09-15 |
| https://github.com/huggingface/transformers/releases/tag/v5.0.0 | v5.0.0 GA notes | 2026-09-15 |
| https://github.com/huggingface/transformers/releases | Release cadence + latest version: **v5.21.0, 2026-10-26** (GitHub tag `v5.21`, PyPI `5.21.0`), via v5.18.0 (09-30), v5.19.0 (10-06), v5.20.0-v5.20.2 (10-15 to 10-19). Breaking-change sections of 5.18.0-5.21.0 carry no tokenizer, chat-template, special-token or EOS item (5.20.1/5.20.2 patch notes not read). Tokenizer-adjacent non-breaking fixes in 5.18/5.19 (#48708 special ids, #49082 config EOS ids, #48641/#49116 hub tokenizer class) not yet reflected in the skill. | 2026-10-27 |
| https://github.com/huggingface/tokenizers/tags | `tokenizers` (Rust) latest: **v0.23.3** (2026-10-09, isLatest; PyPI 0.23.3). Still no v0.24; a **v1.0.0** pre-release line exists (rc.3, 2026-10-19). vLLM v0.32.0 requires `tokenizers >= 0.23.2`. | 2026-10-27 |
| https://huggingface.co/blog/tokenizers | Transformers v5 tokenizer blog | 2026-09-15 |

## Transformers issues + PRs

| URL | Purpose | Last verified | Notes |
|---|---|---|---|
| https://github.com/huggingface/transformers/issues/38182 | Gemma-3 IT EOS mismatch | 2026-09-15 | — |
| https://github.com/huggingface/transformers/issues/41870 | GemmaTokenizerFast SP inconsistency | 2026-09-15 | — |
| https://github.com/huggingface/transformers/issues/42914 | chat_template.jinja not cached offline | 2026-09-15 | — |
| https://github.com/huggingface/transformers/issues/43066 | DeepSeek-R1-Distill decoder shape regression | 2026-09-15 | — |
| https://github.com/huggingface/transformers/pull/43104 | v5 decoder doc clarification | 2026-10-27 | **CLOSED unmerged** 2026-10-20 by a maintainer (diff larger than the fix needed; asked for a one-line PR instead). No replacement merged. |
| https://github.com/huggingface/transformers/issues/45205 | Gemma-4 chat_template not auto-loaded | 2026-09-15 | **Shows CLOSED 2026-06-10 with `stateReason: COMPLETED` — but the closing comment is the stale bot** ("automatically marked as stale because it has not had recent activity"). **No fix landed; the gotcha stands.** See the stale-bot warning below. |
| https://github.com/huggingface/transformers/issues/45356 | Kimi-K2.5 `</think>` decode regression 5.3→5.4 | 2026-09-15 | — |
| https://github.com/huggingface/transformers/pull/45359 | Fix for #45356 | 2026-09-15 | MERGED 2026-04-13 |

## vLLM

| URL | Purpose | Last verified |
|---|---|---|
| https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/common/cli_args.py | --chat-template, --trust-request-chat-template, --default-chat-template-kwargs (moved from `entrypoints/launchers/` by #62390, after v0.32.0; v0.32.0 still has the launchers path) | 2026-10-27 |
| https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/chat_completion/serving.py | OpenAIServingChat init, request flow | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/renderers/online_renderer.py | trust_request_chat_template enforcement (`validate_chat_template`); `ChatTemplateConfig` lives in `vllm/renderers/chat_utils/chat_template.py`. `entrypoints/chat_utils.py` moved to `renderers/chat_utils.py` in #60522 (v0.32.0) and was split into a package on `main` after it | 2026-10-27 |
| https://github.com/vllm-project/vllm/blob/main/vllm/renderers/hf.py | safe_apply_chat_template, resolve_chat_template_kwargs allowlist | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/sampling_params.py | update_from_generation_config stop-token merge | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/v1/engine/input_processor.py | generation_config EOS merge call site | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/v1/engine/detokenizer.py | Fast/slow incremental detokenizer | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/tokenizers/detokenizer_utils.py | detokenize_incrementally word-boundary logic | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/tokenizers/registry.py | tokenizer_mode auto-detect (mistral/hf) | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/tokenizers/mistral.py | MistralTokenizer + Tekkenizer | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/parser/abstract_parser.py | adjust_request call site (moved from serve/render/serving.py; scale-out consolidation #44512) | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/abstract_tool_parser.py | Tool parser adjust_request contract | 2026-09-15 |
| https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/serve/tokenize/serving.py | /tokenize, /detokenize | 2026-09-15 |
| https://github.com/vllm-project/vllm/pull/27622 | chat_template_kwargs allowlist fix (v0.11.1) | 2026-09-15 |
| https://github.com/vllm-project/vllm/issues/25401 | tokenizer-mode mistral silently ignores --chat-template | 2026-09-15 |
| https://github.com/vllm-project/vllm/releases/tag/v0.11.1 | Shipped PR #27622 | 2026-09-15 |
| https://github.com/vllm-project/vllm/releases | Latest **v0.32.0, 2026-10-18** (isLatest), via v0.30.0 (09-22) and v0.31.0 (10-05). transformers requirement per tag read from `requirements/common.txt` and `requirements/test/*.txt` in the local clone: v0.29.0 `>=5.10.4` (test 5.15.0), v0.30.0 `>=5.10.4` (test 5.16.1), v0.31.0 `>=5.10.4,<5.18.0` (test 5.17.0, cap #59614), v0.32.0 `>=5.16.1,<5.20.0` (test 5.19.0, floor #57387/#59762), main `>=5.16.1,<5.21.0` (test 5.20.2). v0.32.0 also fixed GHSA-4hhp-h66f-j5j7 (chat-template render timeout, #50300). Chat-template/CLI paths re-read at main 2026-10-27; other engine-knobs.md line numbers are from an older tree. | 2026-10-27 |

## sglang

| URL | Purpose | Last verified |
|---|---|---|
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/entrypoints/openai/serving_chat.py | Kwargs dict-update, skip_special_tokens overrides, delta slicing | 2026-09-15 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/managers/detokenizer_manager.py | DetokenizerManager subprocess, DecodeStatus | 2026-09-15 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/sampling/sampling_params.py | skip_special_tokens per-request | 2026-09-15 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/configs/model_config.py | _get_hf_eos_token_id union | 2026-09-15 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/speculative/spec_info.py | SpeculativeAlgorithm enum (no MTP entry) | 2026-09-15 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/parser/reasoning_parser.py | Registered reasoning parsers | 2026-09-15 |
| https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/parser/conversation.py | FastChat conversation-template registry | 2026-09-15 |
| https://github.com/sgl-project/sglang/issues/22510 | Streaming word-fragment report (red herring) | 2026-09-15 |
| https://github.com/sgl-project/sglang/pull/22549 | Fix: serving_chat.py double-slice | 2026-09-15 |
| https://github.com/sgl-project/sglang/commit/9e7dfcc151e4ba79457851019458567eabfc2764 | Merge commit | 2026-09-15 |

## HuggingFace model repos

| URL | Purpose | Last verified |
|---|---|---|
| https://huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/tokenization_kimi.py | TikTokenTokenizer custom class | 2026-09-15 |
| https://huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/tokenizer_config.json | Kimi auto_map, EOS `[EOS]` | 2026-09-15 |
| https://huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/generation_config.json | eos_token_id 163586 | 2026-09-15 |
| https://huggingface.co/moonshotai/Kimi-K2-Instruct/discussions/31 | EOS ambiguity | 2026-09-15 |
| https://huggingface.co/moonshotai/Kimi-K2.5/discussions/7 | Slow tokenizer note | 2026-09-15 |
| https://huggingface.co/moonshotai/Kimi-K2.6/blob/main/tokenizer_config.json | Half-fix EOS split-brain | 2026-09-15 |
| https://huggingface.co/google/gemma-4-E4B/blob/main/tokenizer_config.json | GemmaTokenizer + Gemma4Processor (`processor_class` read 2026-10-27, same in 26B-A4B-it; class ships from transformers v5.5.0) | 2026-09-15 |
| https://huggingface.co/google/gemma-4-E4B/blob/main/generation_config.json | eos_token_id 1 | 2026-09-15 |
| https://huggingface.co/google/gemma-4-26B-A4B-it/blob/main/generation_config.json | eos_token_id [1, 106, 50] | 2026-09-15 |
| https://huggingface.co/zai-org/GLM-5.1/blob/main/tokenizer_config.json | TokenizersBackend + list extra_special_tokens | 2026-09-15 |
| https://huggingface.co/zai-org/GLM-5.1/blob/main/generation_config.json | Three-ID EOS [154820, 154827, 154829] | 2026-09-15 |
| https://huggingface.co/zai-org/GLM-5.1-FP8/blob/main/tokenizer_config.json | FP8 variant config | 2026-09-15 |
| https://huggingface.co/zai-org/GLM-4.6/blob/main/tokenizer_config.json | PreTrainedTokenizer + dict extra_special_tokens | 2026-09-15 |
| https://huggingface.co/Qwen/Qwen3-0.6B/blob/main/tokenizer_config.json | `<\|im_end\|>` dual role | 2026-09-15 |
| https://huggingface.co/Qwen/Qwen3.5-35B-A3B-Base/blob/main/tokenizer_config.json | Base flips EOS to `<\|endoftext\|>` | 2026-09-15 |
| https://huggingface.co/deepseek-ai/DeepSeek-V3/blob/main/tokenizer_config.json | LlamaTokenizerFast, no added_tokens_decoder | 2026-09-15 |
| https://huggingface.co/deepseek-ai/DeepSeek-V3/raw/main/tokenizer.json | 7.85 MB LFS added_tokens | 2026-09-15 |
| https://huggingface.co/deepseek-ai/DeepSeek-R1/blob/main/tokenizer_config.json | `<think>` only in chat_template | 2026-09-15 |
| https://huggingface.co/microsoft/phi-4/blob/main/tokenizer_config.json | Inverted BOS/EOS | 2026-09-15 |
| https://huggingface.co/mistralai/Mistral-Small-24B-Instruct-2501/blob/main/tokenizer_config.json | LlamaTokenizer + [INST] wrappers | 2026-09-15 |
| https://huggingface.co/nvidia/nemotron-colembed-vl-4b-v2/commit/e707da79538edf17c86abd24d42d603eaec9b3cb | extra_special_tokens list-vs-dict fix | 2026-09-15 |

## Other

| URL | Purpose | Last verified |
|---|---|---|
| https://github.com/QwenLM/Qwen3/issues/927 | config.json vs tokenizer_config EOS drift | 2026-09-15 |
| https://kaitchup.substack.com/p/qwen3-when-im_end-suddenly-becomes | Qwen3 base-vs-instruct EOS flip | 2026-09-15 |

---

## Freshen trap: `CLOSED` + `COMPLETED` can mean *stale bot*

`huggingface/transformers` runs an inactivity bot that closes issues **and the
GitHub API reports `stateReason: COMPLETED`** for them. #45205 (Gemma-4
`chat_template` not auto-loaded) is closed by exactly this route with no fix
merged — a freshen that trusted `state` + `stateReason` would delete a live
gotcha from four files.

The same behaviour was observed in `sgl-project/sglang` on the same day, so treat
it as the default assumption, not a quirk. Always read the closing comment:

```bash
gh issue view <N> -R <owner>/<repo> \
  --json state,closedAt,stateReason,comments \
  --jq '"\(.state) \(.stateReason)\n\(.comments[-1].body[0:200])"'
```

A real fix names a PR or a release. A stale close says "no recent activity".

