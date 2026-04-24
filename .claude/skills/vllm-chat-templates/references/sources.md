# Source verification log

Tracks external references cited by this skill and their last-verified dates.
Lift Dim 9 staleness cap by keeping this table current: when adding a new
issue/PR/URL to the skill, probe it and add a row here.

Probe pattern: `gh pr view <N> --repo vllm-project/vllm --json state,mergedAt,title,closedAt,stateReason`

## Last sweep: 2026-04-24

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| vLLM PR #27622 | https://github.com/vllm-project/vllm/pull/27622 | 2026-04-24 | MERGED 2025-10-28 | Whitelists HF standard chat-template kwargs (`add_generation_prompt`, `continue_final_message`, `enable_thinking`, etc.) through `**kwargs`. Required for Kimi-K2 fix. Shipped in v0.11.1+. |
| vLLM issue #25401 | https://github.com/vllm-project/vllm/issues/25401 | 2026-04-24 | CLOSED/COMPLETED 2025-10-09 | Mistral `--tokenizer-mode mistral` silently dropping `--chat-template` — **fixed upstream**. Warning-or-error behavior now present in recent vLLM. Verify on your version before assuming silent drop. |
| vLLM issue #28804 | https://github.com/vllm-project/vllm/issues/28804 | 2026-04-24 | CLOSED/NOT_PLANNED 2026-03-23 | DeepSeek V3.1 multi-turn whitespace accumulation. Not accepted upstream as a planned fix. Treat as won't-fix; apply client-side mitigation (strip leading whitespace) rather than expecting a vLLM-side fix. |
| vLLM issue #22578 | https://github.com/vllm-project/vllm/issues/22578 | 2026-04-24 | CLOSED/NOT_PLANNED 2026-01-23 | gpt-oss `/v1/chat/completions` tool calling. Closed as not-planned — `/v1/responses` (Harmony) is the supported path for gpt-oss tool calling and will remain so. |
| vLLM issue #23015 | https://github.com/vllm-project/vllm/issues/23015 | 2026-04-24 | CLOSED/NOT_PLANNED 2026-04-20 | gpt-oss template "appears hard-coded". Closed as not-planned — operator-supplied `--chat-template` is intentionally overridden for gpt-oss when the harmony path is used. Use `/v1/responses`. |
| vLLM issue #39392 | https://github.com/vllm-project/vllm/issues/39392 | 2026-04-24 | OPEN | Gemma-4 `<pad>` tokens under concurrent load. Still open as of sweep. `--max-num-seqs 1` workaround remains current. |
| vLLM issue #38855 | https://github.com/vllm-project/vllm/issues/38855 | 2026-04-24 | OPEN | Gemma-4 reasoning parser / `skip_special_tokens` stripping. Still open. `extra_body={"skip_special_tokens": false}` workaround remains current. |
| vLLM issue #39614 | https://github.com/vllm-project/vllm/issues/39614 | 2026-04-24 | OPEN | GLM-5.1-FP8 `--chat-template-content-format auto` misroutes tool result. Still open. Workaround: set content-format to `openai` or `string` explicitly. |

## Not re-probed this sweep (budget exhausted, prior-state assumed)

These refs were cataloged but not re-probed — verify on next sweep. Most are
either (a) historical bug references whose workarounds are baked into the
skill even if the issue is since closed, or (b) model-card discussions that
rarely flip state.

- vLLM #12999, #13978, #14682, #14734, #14884, #15403, #16292, #16463, #16482,
  #16510, #18090, #18141, #18819, #19513, #19545, #20341, #20611, #21711,
  #22403, #22718, #33654, #37909, #39043, #39611
- HuggingFace discussions: DeepSeek-R1 #144, gpt-oss-20b #160 / #218,
  gpt-oss-120b #69, Llama-4-Scout #78, Pixtral #22, Mistral-Small-3.1 #49,
  gemma-4-31B #28
- vLLM blog: https://vllm.ai/blog/Kimi-K2-Accuracy (Oct 2025)
- HF blog: https://huggingface.co/blog/qwen-3-chat-template-deep-dive
- discuss.vllm.ai threads: DeepSeek-V3 tool_choice, Llama4-Maverick LangGraph
- MoonshotAI/Kimi-K2 #41 (Kimi-K2 upstream repo)
- ms-swift #5836 (ModelScope downstream harness)

## vLLM source paths cited (subject to code-drift)

These paths are cited inline in SKILL.md with line-number ranges. Line numbers
drift on every vLLM release; treat the range as illustrative, not canonical.
Do **not** re-probe unless a user reports "that line has unrelated code".

- `vllm/renderers/hf.py` — `resolve_chat_template()`, kwarg allowlist
- `vllm/renderers/params.py` — `ChatParams` dataclass
- `vllm/entrypoints/chat_utils.py` — multimodal placeholder injection, ChatTemplateResolutionError
- `vllm/entrypoints/openai/serving_chat.py` — parser instantiation
- `vllm/reasoning/__init__.py` — registered reasoning parsers
- `vllm/transformers_utils/chat_templates/registry.py` — bundled fallback lookup
- `examples/tool_chat_template_*.jinja` (27 files)
