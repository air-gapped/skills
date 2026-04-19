# Writing a custom `--tool-parser-plugin` (navigation)

Goal: ship as a plugin, not an upstream PR — unless the format is broadly useful.

## Read these first (in order)

1. `vllm/tool_parsers/abstract_tool_parser.py` — `ToolParser` base class + `ToolParserManager`. Everything needed to subclass is here.
2. `vllm/tool_parsers/utils.py` — helpers (`partial_json_loads`, `find_common_prefix`, `make_valid_python`, `compute_tool_delta`, `handle_single_tool`, `partial_tag_overlap`).
3. One existing parser closest to the target format:
   - JSON-in-tags → `vllm/tool_parsers/hermes_tool_parser.py`
   - JSON array in one sentinel → `vllm/tool_parsers/jamba_tool_parser.py`
   - Pythonic `[fn(a=1)]` → `vllm/tool_parsers/pythonic_tool_parser.py`
   - XML grammar → `vllm/tool_parsers/qwen3xml_tool_parser.py` (expat, cleanest streaming)
   - Harmony/channel-based → `vllm/tool_parsers/openai_tool_parser.py`
4. `vllm/entrypoints/openai/chat_completion/serving.py` — the streaming loop. Grep `extract_tool_calls_streaming` to see how the parser gets called.
5. `vllm/entrypoints/openai/api_server.py` — grep `import_tool_parser` to see how `--tool-parser-plugin` loads the file.
6. `tests/tool_parsers/common_tests.py` + `tests/tool_parsers/test_<name>_tool_parser.py` — the executable spec. Reviewers expect this harness.
7. `AGENTS.md` at repo root — duplicate-work policy, PR-description requirements.

## Minimum skeleton

```python
from vllm.entrypoints.openai.protocol import (
    ChatCompletionRequest, DeltaMessage,
    ExtractedToolCallInformation, FunctionCall, ToolCall,
)
from vllm.tool_parsers.abstract_tool_parser import ToolParser, ToolParserManager


@ToolParserManager.register_module(["your_name"])
class YourParser(ToolParser):
    # Base class inits: prev_tool_call_arr, current_tool_id=-1,
    # current_tool_name_sent=False, streamed_args_for_tool=[].

    def adjust_request(self, request):
        # Flip if sentinels are special tokens.
        # request.skip_special_tokens = False
        return super().adjust_request(request)

    def extract_tool_calls(self, model_output, request):
        ...  # non-streaming, stateless
        return ExtractedToolCallInformation(
            tools_called=bool(...), tool_calls=[...], content=None,
        )

    def extract_tool_calls_streaming(
        self, previous_text, current_text, delta_text,
        previous_token_ids, current_token_ids, delta_token_ids, request,
    ):
        ...  # stateful; update self.prev_tool_call_arr + self.streamed_args_for_tool
        # Returns None | DeltaMessage(content=...) | DeltaMessage(tool_calls=[...])
```

Launch:

```bash
vllm serve <model> --enable-auto-tool-choice \
  --tool-call-parser your_name \
  --tool-parser-plugin /abs/path/to/your_parser.py \
  --chat-template /abs/path/to/your_template.jinja
```

## Checklist before shipping

- [ ] Respects `current_text == previous_text + delta_text` invariant.
- [ ] Handles multi-token deltas (scheduler may coalesce).
- [ ] `prev_tool_call_arr[i]["arguments"]` reflects full accumulated args at stream end.
- [ ] `streamed_args_for_tool[i]` appended on every arg flush.
- [ ] `adjust_request` sets `skip_special_tokens=False` if sentinels are special tokens.
- [ ] `supports_required_and_named = False` if the output shape breaks guided JSON.
- [ ] Test file added at `tests/tool_parsers/test_<name>_tool_parser.py` using `common_tests.py` harness.
- [ ] Reference Jinja at `examples/tool_chat_template_<name>.jinja` if upstreaming.
- [ ] Aligned with `parse_delta` refactor (RFC #11522) if working against recent main.

## Before upstreaming

```bash
# Duplicate-work checks per AGENTS.md
gh pr list --repo vllm-project/vllm --state open --search "<relevant-keywords>"
gh issue list --repo vllm-project/vllm --search "<relevant-keywords>"
gh search issues --repo vllm-project/vllm "tool parser <shape>" --state open
```

If the format is single-consumer (internal fine-tune), stay a plugin. The plugin path is a first-class supported extension — no fork needed.

## When NOT to write a plugin

Check first:
- Is this actually a chat-template problem? (Verify via `/v1/completions` raw-bytes inspection.)
- Does an existing parser accept a superset of the target format? (`xlam` accepts multiple, `hermes` is generic JSON-in-tags.)
- Can the fine-tune trainer emit a shape that matches an existing parser?

Most "we need a custom parser" questions are chat-template or shape-selection problems.
