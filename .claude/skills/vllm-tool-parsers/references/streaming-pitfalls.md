# Streaming pitfalls (navigation)

Cross-parser footguns. For each, the remedy is to **go read the cited file or run the cited command** — don't trust a paraphrase.

## The `prev_tool_call_arr` flush contract

**Read**: `vllm/entrypoints/openai/chat_completion/serving.py` — grep `prev_tool_call_arr` and `streamed_args_for_tool`.

Serving layer reads `prev_tool_call_arr[i]["arguments"]` at stream end and flushes anything not already in `streamed_args_for_tool[i]`. Implications for every custom parser:

- `prev_tool_call_arr[i]["arguments"]` must reflect full accumulated args at stream end.
- `streamed_args_for_tool[i]` must be appended on every arg flush (else tail doubles).
- `finish_reason="tool_calls"` fires iff `prev_tool_call_arr` non-empty. Hence the `= [{"arguments": {}}]` HACK several parsers carry.

## Top production footguns

1. **Full-width vs ASCII punctuation.** DeepSeek V3/V3.1/V3.2 and Step-3 use `｜` (U+FF5C) and `▁` (U+2581) — not ASCII `|` / `_`. Grep the Jinja template for bytes:
   ```bash
   python3 -c "import sys; b=open(sys.argv[1],'rb').read(); \
     print('U+FF5C:', b.count('｜'.encode())); print('U+2581:', b.count('▁'.encode())); \
     print('ASCII |:', b.count(b'|')); print('ASCII _:', b.count(b'_'))" <template>
   ```

2. **`skip_special_tokens=False` requirement.** Parsers whose sentinels are special tokens must override `adjust_request`. Check:
   ```bash
   grep -l "skip_special_tokens" vllm/tool_parsers/
   ```

3. **Sentinel-in-vocab check.** Jamba hard-fails at `vllm serve` if sentinels aren't in tokenizer vocab. Intentional — silences downstream bugs.

4. **Empty-args stalls.** DeepSeek V3/V3.1 need `"}` literally in `delta_text` to close. Different parsers handle `{}` differently. Read the specific parser's close-path.

5. **Parallel calls support varies.** Only some parsers handle multiple tool calls in streaming. Grep the parser file for `current_tool_id > 0` to see rejection behavior.

6. **Pythonic re-parse is O(n²).** `pythonic`/`llama4_pythonic`/`olmo3` re-`ast.parse` the whole buffer per delta. Long arg strings spike TTFT.

7. **Apostrophe bug in `compute_tool_delta`.** Naive `'`→`"` substitution. Strings containing `'` (e.g. `"it's"`) corrupt. Check `vllm/tool_parsers/utils.py` before relying on this helper.

8. **Non-streaming parsers.** `phi4_mini_json.extract_tool_calls_streaming` returns `None` unconditionally. `openai` raises `NotImplementedError` — Harmony streaming is hand-rolled in `chat_completion/serving.py`.

9. **Stream-interval > 1 regressions.** Several parsers have had fixes for `--stream-interval > 1`. If setting that flag, grep the merged PRs:
   ```bash
   gh search prs --repo vllm-project/vllm "stream-interval tool parser" --state merged --limit 20
   ```

10. **The `parse_delta` refactor.** RFC #11522 is removing the HACK pattern. PRs #39446 / #39728 / #38755. Check current state before writing a new parser.

## Reasoning-parser pairing

Several tool parsers gate on a reasoning-end sentinel. The canonical list is in `SKILL.md`. Verify by grepping:

```bash
grep -l "is_reasoning_end\|</think>\|</seed:think>" vllm/tool_parsers/
```

## Diagnostic flow

The canonical step-by-step playbook lives in `SKILL.md` ("Diagnostic playbook"). Don't duplicate it here — the streaming-specific footguns above feed steps 5–9 of that playbook (streaming support, `finish_reason`/`prev_tool_call_arr`, template-vs-parser isolation, version-vs-fix-PR checks).

## When to recommend vs not

- **Recommend reading the source** over copying guidance from this skill whenever the operator's question is about specific parser behavior.
- **Recommend upgrading** when a specific issue is referenced — verify its status first (`gh issue view N --repo vllm-project/vllm`).
- **Recommend the plugin path** over upstreaming for private / single-consumer formats (per `AGENTS.md` fail-closed policy).
