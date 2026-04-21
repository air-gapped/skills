---
name: transformers-config-tokenizers-expert
description: >-
  Preflight reference for HuggingFace snapshots — what vLLM, sglang, and
  transformers.generate see at runtime. Covers config-file precedence
  (tokenizer.json, tokenizer_config.json, generation_config.json,
  chat_template.jinja), transformers v5 tokenizer-class taxonomy
  (TokenizersBackend, PythonBackend, MistralCommonBackend, TikTokenTokenizer),
  special-token discovery (all_special_ids, added_tokens_decoder,
  extra_special_tokens, backend_tokenizer.get_added_tokens_decoder),
  chat-template Jinja contract (ImmutableSandboxedEnvironment, loopcontrols,
  raise_exception, strftime_now, tojson, add_generation_prompt), and engine
  knobs (skip_special_tokens, trust_request_chat_template,
  chat_template_kwargs allowlist, adjust_request, incremental detokenizer,
  EOS merge). Ships verified 2026 hall-of-shame for Kimi-K2.6, GLM-5.1,
  Gemma-4, Qwen3, DeepSeek-V3, plus drop-in Python for resolving markers to
  IDs, detecting turn-primer-as-EOS leaks, and cross-referencing
  tokenizer.json vs tokenizer_config.json.
when_to_use: >-
  Use proactively on preflight questions about HuggingFace models at
  runtime. Trigger on: loading a tokenizer, debugging vLLM/sglang
  emitting turn-role markers, EOS drift between generation_config.json
  and tokenizer_config.json, `apply_chat_template` dropping kwargs,
  `AttributeError 'list' object has no attribute 'keys'` on
  `extra_special_tokens`, turn primers leaking on stream, or
  `Cannot use chat template functions`. Apply even when phrasing omits
  these exact words.
---

# Transformers config + tokenizers expert

Target: engineers writing a preflight tool (or a vLLM/sglang operator)
that must decide, before handing a HuggingFace snapshot to an inference
engine, *which* files win, *which* tokens are structural, and *which*
class will actually instantiate.

Almost every major 2026 release has shipped with drift between
`tokenizer_config.json`, `generation_config.json`, `config.json`, and
the Rust-backed tokenizer state. The skill exists so a preflight tool
can answer that drift authoritatively — not guess.

---

## Stance

- **Cite, don't paraphrase.** Every load-bearing claim has a file:line
  or URL citation in `references/`. Point at the source.
- **Version-gate.** Transformers v5 (GA 2026-01-26) renamed the
  tokenizer classes and changed serialization shapes. Pre-5.0 and
  post-5.0 diverge — check `transformers.__version__` before claiming.
- **Rust is truth.** For any model with `tokenizer.json`, the
  authoritative added-token state is
  `tokenizer.backend_tokenizer.get_added_tokens_decoder()`. Python-side
  `all_special_ids` / `special_tokens_map` / `added_tokens_decoder` are
  views; treat them as such.
- **Engines disagree.** vLLM and sglang both union-merge
  `generation_config.eos_token_id`, but apply it through different
  pipelines (see `engine-knobs.md`). Predict per engine, not in the
  abstract.

---

## Triage: symptom → layer → reference

Use this table first. Deep dives live in `references/`.

| Symptom | Layer | Open |
|---|---|---|
| `tokenizer.eos_token_id` disagrees with `generation_config.eos_token_id` | Config drift | `config-files.md#eos-drift` |
| Engine stops on token X, template emits token Y | Config drift | `config-files.md#eos-drift` + `engine-knobs.md#stop-token-merge` |
| `AutoTokenizer.from_pretrained` wants `trust_remote_code=True` | Class selection | `tokenizer-classes.md#tiktoken-path` |
| `KeyError: 'TokenizersBackend'` on import | Version gate | `tokenizer-classes.md#version-aliases` |
| `AttributeError: 'list' object has no attribute 'keys'` on `extra_special_tokens` | Cross-version serialization | `precedence-rules.md#extra-special-tokens-shape` |
| `all_special_ids` misses DeepSeek `<｜place▁holder…｜>` tokens | Discovery precedence | `precedence-rules.md#backend-fallback` |
| `added_tokens_decoder` absent from `tokenizer_config.json` | v5 consolidation | `config-files.md#v5-consolidation` |
| `Cannot use chat template functions because tokenizer.chat_template is not set` | Template file not wired | `chat-template-contract.md#gemma-4-issue-45205` |
| `chat_template_kwargs` silently dropped at request time | Allowlist filter | `engine-knobs.md#chat-template-kwargs-allowlist` |
| `enable_thinking=false` has no effect | Allowlist filter (pre-v0.11.1) | `engine-knobs.md#pr-27622` |
| Tool-call arguments render as `"None"` instead of `null` | Template scalar bug | `hall-of-shame.md#gemma-4-ap-45` |
| Turn primers (`<\|user\|>`, `<\|observation\|>`) leak into output | EOS list contains turn markers (GLM-5.1) | `hall-of-shame.md#glm-5-1-three-id-eos` |
| Streaming chunks arrive as word fragments | sglang `serving_chat.py` double-slice (#22549) OR vLLM `skip_special_tokens=False` | `engine-knobs.md#incremental-detokenizer` |
| `apply_chat_template` crashes with `UndefinedError` on `tc.arguments.items()` | Arguments arrived as JSON string, not dict | `hall-of-shame.md#glm-5-1-ap-45` |
| Kimi emits `[EOS]` but engine expects `<\|im_end\|>` (or vice versa) | Kimi EOS split-brain | `hall-of-shame.md#kimi-k2-6-half-fix` |

---

## The precedence cheat sheet (memorize)

Five sources exist for "is this token structural?" They disagree.
Reach for them in this order when writing preflight code:

1. **`tokenizer.backend_tokenizer.get_added_tokens_decoder()`** — Rust
   truth. `dict[int, AddedToken]`. Every added token, with `special`
   flag, `lstrip/rstrip/normalized` attrs. Source:
   `tokenization_utils_tokenizers.py:488-495` (v5), passthrough.
   Only available for `TokenizersBackend`.
2. **`tokenizer.added_tokens_decoder`** — Python mirror. For
   `TokenizersBackend` it's a passthrough to #1. For
   `PythonBackend` it's deserialized from
   `tokenizer_config.json["added_tokens_decoder"]`.
3. **`tokenizer.all_special_tokens` / `all_special_ids`** — the narrow
   union of SEVEN named role slots (`SPECIAL_TOKENS_ATTRIBUTES` at
   `tokenization_utils_base.py:1040-1047`) + `extra_special_tokens`.
   **Does not include** any added token registered with
   `special=False`. This is why DeepSeek's reserved-token slabs and
   GLM-5.1's `<\|user\|>`-as-turn-primer are invisible.
4. **`tokenizer.special_tokens_map`** — only the seven role slots as
   `dict[str, str]`. No extras, no added_tokens. Legacy shape.
5. **`tokenizer.extra_special_tokens`** — list internally
   (`self._extra_special_tokens = []` at `tokenization_utils_base.py:1074`).
   v5.0.0rc0 *serialized* this as a list into `tokenizer_config.json`,
   crashing `<5.0` readers that call `.keys()`. GLM-5.1 ships
   extra_special_tokens as a **list**; GLM-4.6 ships it as `{}` (dict).
   See `precedence-rules.md#extra-special-tokens-shape`.

**Preflight rule of thumb.** For any structural question beyond "is
this a named role slot", go to #1. If #1 is unavailable (no
`tokenizer.json`, i.e. Kimi via TikTokenTokenizer), fall through to
#2 from `tokenizer_config.json["added_tokens_decoder"]`, and
cross-ref against `generation_config.json`.

Full table with file:line per backend: `references/precedence-rules.md`.

---

## Config-file precedence (memorize)

For the "which EOS wins" question:

| Consumer | Reads | Wins |
|---|---|---|
| `model.generate()` (transformers) | `generation_config.eos_token_id` | Primary; `config.json` only fills unset fields |
| `apply_chat_template` | `tokenizer.eos_token` (from `tokenizer_config.json`) when template says `{{ eos_token }}` | Render only; not enforcement |
| vLLM stop-matching | Unions `generation_config.eos_token_id` list into `stop_token_ids` at `sampling_params.py:540-560` | Union |
| sglang stop-matching | Unions `hf_config.eos_token_id` and `hf_generation_config.eos_token_id` at `model_config.py:580-598` | Union |

**Consequence:** a single-int `eos_token` in `tokenizer_config.json`
paired with a three-ID list in `generation_config.json` is fine for
engines (they union) but ambiguous for any tool that only reads the
tokenizer. Preflight must read both and diff.

Full catalogue per file: `references/config-files.md`.

---

## Tokenizer-class cross-reference (2026)

Which class actually instantiates for major lab repos. Verified
against each repo's `tokenizer_config.json`.

| Lab / repo | `tokenizer_class` | Backend | Files shipped | Trust remote code? |
|---|---|---|---|---|
| moonshotai/Kimi-K2-Instruct, K2.6 | `TikTokenTokenizer` (custom, `auto_map`) | `PythonBackend` (slow) | `tiktoken.model`, NO `tokenizer.json` | **Yes** + `pip install tiktoken` |
| google/gemma-4-E4B, 26B-A4B-it | `GemmaTokenizer` + `Gemma3Processor` | `TokenizersBackend` | `tokenizer.json` (LFS), sep `chat_template.jinja` (issue #45205) | No |
| zai-org/GLM-5.1, GLM-5.1-FP8 | `TokenizersBackend` (explicit) | `TokenizersBackend` | `tokenizer.json`, no `special_tokens_map.json` | No; **transformers ≥5.0 required** |
| zai-org/GLM-4.6 | `PreTrainedTokenizer` | `PythonBackend` (alias) | `tokenizer.json` + dict `extra_special_tokens` | No |
| Qwen/Qwen3-0.6B | default | `TokenizersBackend` | Full set | No |
| Qwen/Qwen3.5-35B-A3B-Base | default | `TokenizersBackend` | Base flips EOS to `<\|endoftext\|>` vs `<\|im_end\|>` on Instruct | No |
| deepseek-ai/DeepSeek-V3 | `LlamaTokenizerFast` | `TokenizersBackend` | `tokenizer.json` (7.85 MB LFS); `added_tokens_decoder` NOT in `tokenizer_config.json` | No |
| deepseek-ai/DeepSeek-R1 | `LlamaTokenizerFast` | `TokenizersBackend` | `<think>`/`</think>` only in `chat_template.jinja`, NOT in `added_tokens_decoder` | No |
| microsoft/phi-4 | `GPT2Tokenizer` | `TokenizersBackend` | EOS is `<\|im_end\|>`; BOS is `<\|endoftext\|>` (inverted vs Qwen-Base) | No |
| mistralai/Mistral-Small-24B-Instruct-2501 | `LlamaTokenizer` | `MistralCommonBackend` if `tekken.json` present, else fast | `[INST]`/`[/INST]` at ids 3/4 | No |

Full taxonomy + `auto_map` mechanics: `references/tokenizer-classes.md`.

---

## Chat-template Jinja rendering contract

Environment built at `transformers/utils/chat_template_utils.py:234`:

```python
jinja_env = ImmutableSandboxedEnvironment(
    trim_blocks=True, lstrip_blocks=True,
    extensions=[AssistantTracker, jinja2.ext.loopcontrols]
)
jinja_env.filters["tojson"] = tojson                     # ensure_ascii=False default
jinja_env.globals["raise_exception"] = raise_exception   # throws TemplateError
jinja_env.globals["strftime_now"] = strftime_now         # LOCAL TZ, not UTC
```

Four gotchas operators hit:

1. **`tojson` defaults to `ensure_ascii=False`** — stdlib Jinja's
   default is `True`. Templates that dump CJK/emoji tool schemas rely
   on this override. A preflight tool that renders in a naive Jinja
   env will produce HTML-escaped output the model never trained on.
2. **`strftime_now` uses local time.** Llama-3.1/3.2 templates inject
   a date header; the host's timezone determines the value. A
   container running in UTC produces different prompts than a laptop
   in Europe.
3. **`ImmutableSandboxedEnvironment` blocks mutation.** Templates
   cannot `.pop()` `messages` or write to passed objects. Workarounds
   copy into locals.
4. **`loopcontrols` enables `{% break %}` and `{% continue %}`.**
   Some templates depend on these; a stripped-down renderer missing
   the extension raises `TemplateSyntaxError`.

`add_generation_prompt` semantics, `continue_final_message`,
`apply_chat_template` resolution order, `AssistantTracker` offsets:
`references/chat-template-contract.md`.

---

## Engine knob precedence (vLLM + sglang)

Short form:

- **vLLM `chat_template_kwargs`**: CLI `--default-chat-template-kwargs`
  → `OpenAIServingChat.__init__` default → `_prepare_extra_chat_template_kwargs`
  merges with dict-union (request wins) → `safe_apply_chat_template` →
  `resolve_chat_template_kwargs` **allowlist** filter at
  `vllm/renderers/hf.py:352-377` → `tokenizer.apply_chat_template(**resolved)`.
  Allowlist fix PR #27622 shipped in **v0.11.1** (2025-11-18). Pre-v0.11.1
  silently dropped kwargs for tokenizers whose `apply_chat_template`
  uses `**kwargs` (Kimi K2).
- **sglang `chat_template_kwargs`**: literal dict update at
  `serving_chat.py:524-527`. **No allowlist.** Any key reaches
  `apply_chat_template`. Closer to pre-27622 vLLM.
- **vLLM `trust_request_chat_template`**: default `False`. Rejects
  per-request `chat_template` or `chat_template_kwargs` unless set
  True. Enforced at `engine/serving.py:415-425`.
- **sglang no equivalent**: request kwargs always accepted; only
  three sites hardcode overrides to `skip_special_tokens=False`
  (gpt-oss/gemma4 models, `request.tools` present, mistral
  reasoning_effort).
- **`adjust_request` (vLLM)**: runs at
  `render/serving.py:372-383`, reasoning parser first then tool
  parser. Can mutate `tools`, `stop`, `structured_outputs`,
  `response_format` before `to_sampling_params`.
- **sglang has no `adjust_request` analog.** The three hardcoded
  `skip_special_tokens=False` overrides at `serving_chat.py:306/315/397`
  are the equivalent.
- **Stop-token merge**:
  - vLLM: `update_from_generation_config` at `sampling_params.py:540-560`
    appends `generation_config.eos_token_id` list to `stop_token_ids`
    unless `ignore_eos=True`.
  - sglang: `model_config._get_hf_eos_token_id` at `model_config.py:580-598`
    unions `hf_config.eos_token_id` and `hf_generation_config.eos_token_id`
    into `Set[int]`.
- **Incremental detokenizer word boundaries**: vLLM has fast
  (`DecodeStream` from `tokenizers`) and slow (`detokenize_incrementally`
  with `prefix_offset`/`read_offset` diff + U+FFFD guard) paths at
  `vllm/v1/engine/detokenizer.py` and `vllm/tokenizers/detokenizer_utils.py:98-167`.
  sglang uses `DetokenizerManager` subprocess with four-offset
  `DecodeStatus` at `sglang/srt/managers/detokenizer_manager.py:57-63`.
  sglang #22510 was a **serving_chat.py double-slice bug** (fixed PR
  #22549, not the detokenizer — despite `skip_special_tokens=False`
  being a red herring in the initial report).

Deep dive with file:line per knob: `references/engine-knobs.md`.

---

## Hall of shame (verified 2026)

Pre-loaded real incidents. Each entry in `references/hall-of-shame.md`
has the exact file(s), token IDs, and — where known — the bead ID or
commit SHA. Summary:

- **GLM-5.1** — three-ID EOS `[154820, 154827, 154829]` in
  `generation_config.json`. IDs 154827/154829 are
  `<|user|>` / `<|observation|>` turn primers. Engines unioning this
  list stop on turn boundaries; `skip_special_tokens=False` leaks
  them into output. `extra_special_tokens` as **list**, not dict.
  `TokenizersBackend` class name — fails import on transformers `<5.0`.
- **GLM-5.1-FP8 orphan-commit trap** — patch SHA `6ad52ee` not
  reachable from `refs/heads/main` (`a92f8155`). Users assume fix is
  live; it isn't. Verification requires checking `/refs` on HF API.
- **Gemma-4-26B-A4B-it** — multi-ID EOS `[1, 106, 50]`. `added_tokens_decoder`
  absent from `tokenizer_config.json` (lives in LFS `tokenizer.json`).
  Separate `chat_template.jinja` not auto-loaded by transformers 5.5.0
  (issue #45205). Scalar-null serialization bug in `format_argument`
  macro renders `None` not `null`.
- **Kimi-K2.6 half-fix** — `config.json` + `generation_config.json`
  flipped EOS to 163586 (`<|im_end|>`); `tokenizer_config.json` kept
  `[EOS]` (163585). vLLM reads tokenizer_config, sglang reads
  generation_config. Different engines stop on different tokens.
  No `tokenizer.json`; `tiktoken` package required.
- **Qwen3-0.6B** — `<|im_end|>` is simultaneously turn terminator AND
  EOS. Qwen3.5-**Base** flips EOS to `<|endoftext|>` — preflight
  hardcoding `<|im_end|>` emits runaway completions on base variants.
- **DeepSeek-V3** — added tokens live only in `tokenizer.json` (7.85
  MB LFS). `tokenizer_config.json` has no `added_tokens_decoder`.
  `<think>`/`</think>` on R1 live only in `chat_template.jinja`, not
  as added tokens.
- **Phi-4 inversion** — EOS `<|im_end|>`, BOS `<|endoftext|>`.
  Opposite of Qwen-Base. Don't regex on string.

Full incidents with citations: `references/hall-of-shame.md`.

---

## Drop-in snippets

`references/snippets.py` — copy-paste Python for preflight init-time
questions:

| Function | Answers |
|---|---|
| `discover_added_tokens(tokenizer, snapshot_dir=None)` | Every added token ID, walked Rust→Python→config→tokenizer.json |
| `resolve_marker_to_id(tokenizer, marker_str)` | ID(s) for `<\|im_end\|>` / `<\|endoftext\|>` / `<｜end▁of▁sentence｜>` etc. Length >1 = vocab collision |
| `is_turn_marker_eos(snapshot_dir)` | `[(eos_id, content, where_in_template)]` for EOS entries that the template emits as turn primers (leak-on-stream set) |
| `cross_ref_files(snapshot_dir)` | Drift findings: EOS mismatch, extra_special_tokens shape, special_tokens_map drift, template sidecar-vs-inline |
| `version_gate_tokenizer_class(cfg)` | Minimum transformers version (`TokenizersBackend` → `>=5.0`; `PreTrainedTokenizerFast` → `>=4.0` alias) |
| `build_chat_template_env()` | Minimal faithful `ImmutableSandboxedEnvironment` for offline render testing |
| `verify_commit_reachable(repo_id, sha)` | Guards against GLM-5.1-FP8-style orphan-commit traps via HF `/refs` |

---

## Reference map

- `references/config-files.md` — catalogue per file, drift matrix
- `references/tokenizer-classes.md` — v5 taxonomy, `auto_map`, aliases
- `references/precedence-rules.md` — five-source discovery w/ file:line
- `references/chat-template-contract.md` — Jinja env, globals, `add_generation_prompt`
- `references/engine-knobs.md` — vLLM + sglang tokenizer-adjacent flags
- `references/hall-of-shame.md` — verified 2026 incidents
- `references/snippets.py` — drop-in preflight Python
- `references/sources.md` — dated external references (freshen target)
