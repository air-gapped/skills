# Exemplars and anti-exemplars

Real templates to study. Reading them is the fastest way to internalize
what good chat-template Jinja looks like. This reference points at
specific files; always read the current version on HuggingFace or GitHub
— templates are updated frequently and some of these point at specific
issues or commits.

---

## Table of contents

1. Exemplars — chat templates worth reading verbatim
2. Exemplars — generic heavy-Jinja projects
3. Registries and catalogs
4. Anti-exemplars — the hall of shame
5. How to find the canonical template for any HF model

---

## 1. Exemplars — chat templates worth reading verbatim

### vLLM's hand-curated tool templates

**Repo**: `vllm-project/vllm/examples/` on GitHub
**Files**: `tool_chat_template_*.jinja` (about a dozen)

These exist because the upstream HF-shipped templates for these models were
buggy. Each one is a specific fix written by the vLLM maintainers, often
with a PR that documents what was broken. The single best collection of
hand-written chat-template Jinja in the open-source ecosystem.

Notable ones:
- `tool_chat_template_hermes.jinja` — Hermes/Nous tool format
- `tool_chat_template_mistral_parallel.jinja` — Mistral parallel tool calls
- `tool_chat_template_llama3.1_json.jinja` — Llama 3.1 JSON-wrapped tool calls
- `tool_chat_template_granite.jinja` — IBM Granite
- `tool_chat_template_deepseekv3.jinja` — DeepSeek V3

Reading approach: pick one, read it top to bottom, identify every pattern
from `authoring-patterns.md` that appears. The patterns are universal; the
delimiters and JSON format are model-specific.

### Qwen3 (HuggingFace)

**Path**: `huggingface.co/Qwen/Qwen3-8B/blob/main/tokenizer_config.json`
(the `chat_template` field)

Qwen3's template is widely cited as the cleanest modern chat template.
What to study:

- **Defensive `is string` content guard** — the idiom that would have
  prevented the GLM-5.1 bug.
- **Tool-call arguments string/dict branch** — handles both shapes
  correctly: `{{ tool_call.function.arguments if tool_call.function.arguments is string else tool_call.function.arguments | tojson }}`.
- **Explicit `add_generation_prompt`** at the tail.
- **`enable_thinking` support** — per-turn reasoning toggle.
- **Reasoning extraction** from content (parses out `<think>...</think>`
  if the field isn't set separately).

Minor weakness: system-message-not-first handling is implicit, not guarded
with `raise_exception`.

### Gemma-4 (HuggingFace, circa 2026)

**Path**: `huggingface.co/google/gemma-4-*/blob/main/chat_template.jinja`

Current gold standard for defensive chat-template authoring.
What to study:

- **Three-branch content coercion** with catch-all — handles string, list,
  and unexpected shapes.
- **Namespace-based forward-scan** for tool responses to resolve
  `tool_call_id → function_name`.
- **Dual-field reasoning support** — handles both `reasoning` and
  `reasoning_content`.
- **Parallel tool-call emission** — multiple `<tool_call>` blocks in a
  single assistant turn.

This is what every new template should be measured against in 2026.

### Llama-3.3-Instruct (HuggingFace)

**Path**: `huggingface.co/meta-llama/Llama-3.3-70B-Instruct/blob/main/tokenizer_config.json`

Simpler than Qwen3 or Gemma-4 — string content only, no multimodal coercion.
Good as a starting point for a template that doesn't need multimodal
support. What to study:

- **Clean `add_generation_prompt` handling**.
- **Empty `tool_calls` via truthiness** — `{% if message.tool_calls %}`
  correctly skips when the list is empty.
- **`namespace()` usage** for turn-state tracking.

---

## 2. Exemplars — generic heavy-Jinja projects

Not chat-template specific, but the patterns generalize. Study these when
writing any Jinja, not just chat templates.

### ansible/ansible

The most Jinja-intensive project in the Python ecosystem.

- `lib/ansible/plugins/filter/core.py` — ~100 custom filters with
  docstrings. The canonical example of filter plugin registration.
- `lib/ansible/plugins/test/core.py` — parallel for tests.
- `lib/ansible/template/__init__.py` — their `AnsibleEnvironment`, a
  subclass of `SandboxedEnvironment` with project-specific rules.
  Directly analogous to what transformers does with
  `ImmutableSandboxedEnvironment` for chat templates.

### home-assistant/core

- `homeassistant/helpers/template.py` — async-safe template rendering,
  unique in the Python ecosystem.
- Docs at <https://www.home-assistant.io/docs/configuration/templating/> —
  the most readable user-facing Jinja documentation any project ships.

### saltstack/salt

- `salt/utils/jinja.py` — `SerializerExtension`, LazyLoader integration.
  Shows how to thread project objects into the Jinja global namespace.
- `doc/topics/jinja/index.rst` — their best-practices guide.

### dbt-labs/dbt-core

- `core/dbt/clients/jinja.py` — AST-level introspection via
  `MacroGenerator` and `statically_parse_ref`. The best example of Jinja
  introspection in the ecosystem — useful as a reference when building a
  linter.
- `core/dbt/context/` — injecting project objects into the render context.

### pallets/jinja (the reference implementation)

- `src/jinja2/sandbox.py` — the actual `SandboxedEnvironment` and
  `ImmutableSandboxedEnvironment` source. Read for the exact details of
  what's blocked and why.
- `src/jinja2/ext.py` — built-in extensions including `loopcontrols`.
- `docs/templates.rst` — language reference.

### cookiecutter/cookiecutter

- `cookiecutter/environment.py` — the cleanest minimal `Environment`
  subclass in the ecosystem. Good teaching example for anyone
  configuring their own Jinja env.

---

## 3. Registries and catalogs

### unslothai/unsloth

**Repo**: `https://github.com/unslothai/unsloth`
**File**: `unsloth/chat_templates.py`

The `CHAT_TEMPLATES` dict maps model family to a tuple
`(template_str, stop_token, pad_token, system_allowed)`. The canonical
"chat templates as first-class Python objects" pattern.

The unsloth organization on HuggingFace (`huggingface.co/unsloth/`) hosts
fixed versions of broken lab templates — `unsloth/Qwen3-32B`,
`unsloth/gemma-3-27b-it`, etc. Diffing unsloth's template against the
upstream lab's version is the fastest way to see what they fixed.

### chujiezheng/chat_templates

**Repo**: `https://github.com/chujiezheng/chat_templates`

Academic-style catalog. One `.jinja` per model family under
`chat_templates/`, paired with `generation_configs/`. Good for side-by-side
comparison across families, not authoritative on correctness.

### axolotl-ai-cloud/axolotl

**Repo**: `https://github.com/axolotl-ai-cloud/axolotl`
**Files**:
- `src/axolotl/utils/chat_templates.py` — training-time registry
- `src/axolotl/prompt_strategies/chat_template.py` — loss-masking
  interactions

Relevant for any case that touches assistant-turn boundaries for
training loss.

---

## 4. Anti-exemplars — the hall of shame

Broken chat templates shipped by major labs. Read these as "what NOT to do"
and as motivation for the defensive patterns.

When studying an anti-exemplar, use the git-history view on the HF repo
to get the **original broken version**, not the current patched one.
Pattern: `https://huggingface.co/{org}/{model}/commits/main/chat_template.jinja`.

### GLM-5.1 (original)

**Bug**: content-format bifurcation. Template's tool-result branch iterated
over `message.content` assuming each element had `.name`, silently emitted
nothing when content was a string. Empty `<tools>\n</tools>` block.

**What to look for**: the `{% for part in message.content %}` loop that
doesn't guard on `is mapping` or check the `type` field.

### Kimi K2 (original, pre-July 2025)

**Bug**: multiple.

1. Unguarded `tool_call['id']` — crashed on callers that omitted `id`.
2. `add_generation_prompt` read via `kwargs`, invisible to vLLM AST
   analysis — tool-calling accuracy collapsed.
3. Multi-turn tool calls didn't forward-scan correctly; the second tool
   result in a turn got dropped.

**What to look for**: all three patterns — missing `get()` defaults,
`kwargs.add_generation_prompt`, missing `namespace()` for forward-scanning.

### QwQ-32B (original)

**Bug**: `pad_token == eos_token`. Training loss masked EOS. Model
generated infinitely at inference time. Compounded by a template-level
turn-ending mismatch.

**What to look for**: the tokenizer config had `pad_token: <|im_end|>`
and `eos_token: <|im_end|>` both pointing at the same ID. Not strictly a
Jinja bug but surfaces in template behavior.

### Phi-4 (original)

**Bug**: hardcoded assistant primer. The template always emitted
`<|im_start|>assistant\n` at the tail regardless of `add_generation_prompt`.
Training runs produced subtly misaligned models.

**What to look for**: any template that emits the primer unconditionally
or inside the message loop.

### DeepSeek-V3 (original)

**Bug**: crashed on `message.content = None` in the tool-calling path —
`'dict object' has no attribute 'content'` (actually, the reverse — the
template assumed `content` was always defined and a string).

**What to look for**: direct `{{ message.content }}` without `is none`
or `is defined` guards.

### Llama-2-Chat and Gemma-2-IT

**Bug**: double BOS. Template had `{{ bos_token }}` at the top AND
`tokenizer_config.json` had `add_bos_token: true`. Every conversation
started with `<BOS><BOS>...`.

**What to look for**: `{{ bos_token }}` without having checked
`add_bos_token` in the tokenizer config.

---

## 5. How to find the canonical template for any HF model

Templates live in `tokenizer_config.json` as the `chat_template` field
(sometimes a `.jinja` file is also committed separately as
`chat_template.jinja`).

URL patterns:

- **Current template**:
  `https://huggingface.co/{org}/{model}/raw/main/tokenizer_config.json`
  (fetch, then read the `chat_template` field)
- **Standalone template file** (when committed):
  `https://huggingface.co/{org}/{model}/raw/main/chat_template.jinja`
- **Commit history** (to find the original broken version):
  `https://huggingface.co/{org}/{model}/commits/main/tokenizer_config.json`
- **Specific commit**:
  `https://huggingface.co/{org}/{model}/raw/{commit_sha}/tokenizer_config.json`

For comparing a lab's template to unsloth's patched version:

- Lab: `huggingface.co/Qwen/Qwen3-32B/raw/main/tokenizer_config.json`
- Fixed: `huggingface.co/unsloth/Qwen3-32B/raw/main/tokenizer_config.json`

Diff the two JSON files' `chat_template` strings to see exactly what was
patched.

---

## See also

- `references/chat-template/authoring-patterns.md` — the positive patterns
  these exemplars embody
- `references/chat-template/seven-failure-categories.md` — the negative
  patterns the anti-exemplars violated
