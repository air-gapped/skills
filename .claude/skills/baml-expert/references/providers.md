# Clients + providers — full reference

## Contents
- [Provider catalogue](#provider-catalogue) — first-class, OpenAI-compatible, strategy (fallback/round-robin), retry_policy
- [Common options](#common-options) — model, api_key, temperature, http timeouts, headers, allowed_role_metadata
- [Timeouts — MIN-wins composition](#timeouts--composition-is-min-wins)
- [Retry policies](#retry-policies) — constant_delay vs exponential_backoff, composition with fallback
- [Fallback / round-robin](#fallback--round-robin) — named + shorthand strategies, nesting
- [Provider-specific notes](#provider-specific-notes) — Anthropic (system/caching), OpenAI o1, Vertex+Anthropic, AWS Bedrock, Azure, openai-generic
- [Environment variables](#environment-variables) — lazy checking, .env loading
- [Runtime client override cheat sheet](#runtime-client-override-cheat-sheet) — baml_options["client"], with_options, ClientRegistry

Every `function` has a `client`. Either inline shorthand (`client "openai/gpt-5-mini"`) or a named `client<llm> Name { ... }` block. Named clients let you centralize retry, timeouts, load-balancing, and credentials.

## Provider catalogue

### First-class (dedicated adapters with per-model knowledge)

- **`openai`** — `/v1/chat/completions`. Default when no provider.
- **`openai-responses`** — `/v1/responses`. OpenAI's newer endpoint; recommended by OpenAI for new integrations. **Does NOT support `o1-mini`** (use `openai`). Supports reasoning models' server-side state.
- **`anthropic`** — Messages API. Auto-sets `anthropic-version: 2023-06-01`. Default support for `cache_control` metadata.
- **`google-ai`** — Gemini via `generativelanguage.googleapis.com`.
- **`vertex-ai`** — Google Vertex AI. **Also serves Anthropic models** since 0.85.0 (Anthropic-on-Vertex). With API key (Express Mode) `project_id` must be explicit.
- **`aws-bedrock`** — Converse API. Supports token caching (0.221.0+).
- **`azure`** — Azure OpenAI. Uses deployment name instead of model name.

### OpenAI-compatible

- **`openai-generic`** — base for any OpenAI-compatible endpoint. Thin wrappers for readability: `cerebras`, `groq`, `huggingface`, `keywordsai`, `llama-api`, `litellm`, `lmstudio`, `microsoft-foundry`, `ollama`, `openrouter`, `tinfoil`, `together`, `unify`, `vercel-ai-gateway`, `vllm`.

### Strategy (composite)

- **`fallback`** — try list in order, next on error.
- **`round-robin`** — rotate across list. `start` index selectable.

### Policy

- **`retry_policy <Name> { ... }`** — standalone; attach to any client via `retry_policy <Name>`.

## Common options

```baml
client<llm> Example {
  provider openai
  retry_policy MyRetry
  options {
    model "gpt-5-mini"
    api_key env.OPENAI_API_KEY
    temperature 0.1
    max_tokens 4000               // OR max_completion_tokens for o1 family
    top_p 0.95
    seed 42
    stop ["END"]
    base_url "..."                // overrides default endpoint
    headers {
      "x-custom" "value"
      "authorization" "Bearer ..."    // usually set via api_key
    }
    http {
      connect_timeout_ms 5000
      time_to_first_token_timeout_ms 15000
      idle_timeout_ms 30000
      request_timeout_ms 60000     // must be >= time_to_first_token_timeout_ms
      verify_ssl true
    }
    allowed_role_metadata ["cache_control"]   // opt-in to provider-specific role metadata
    default_role "user"                        // what `_.role()` defaults to when omitted
    proxy_url "http://..."
  }
}
```

### Timeouts — composition is MIN-wins

When a `fallback` or `round-robin` wraps child clients, and both have timeouts set, the **shorter** timeout wins for each call. This is often surprising: a "longer parent timeout" does NOT relax a strict child. To loosen, edit the child.

Runtime override (Python):

```python
from baml_py import ClientRegistry
cr = ClientRegistry()
cr.override("GPT5Mini", options={"http": {"request_timeout_ms": 120000}})
b.Fn(text, baml_options={"client_registry": cr})
```

### Retry policies

```baml
retry_policy ConstDelay {
  max_retries 3
  strategy { type constant_delay  delay_ms 500 }
}

retry_policy ExpBackoff {
  max_retries 5
  strategy {
    type exponential_backoff
    delay_ms 200
    multiplier 1.5
    max_delay_ms 10000
  }
}
```

- **On a `fallback` client**, retry applies AFTER the entire fallback chain fails. So `retry=3 + fallback=[A,B,C]` = up to 9 attempts.
- On a simple client, applies to that client only.

## Fallback / round-robin

```baml
client<llm> Main {
  provider fallback
  retry_policy ExpBackoff
  options {
    strategy [
      FastModel,                              // named
      "anthropic/claude-sonnet-4-20250514",   // shorthand allowed
      CheapBackup,
    ]
  }
}

client<llm> Balanced {
  provider round-robin
  options { strategy [A, B, C]  start 0 }
}
```

Mixing: a `fallback` can contain a `round-robin`, which can contain named clients. Nested composition is fully supported.

## Provider-specific notes

### Anthropic

- Only the **first `system` message** is used. Subsequent `system` roles get cast to `assistant`. Check raw cURL to verify layout.
- Prompt caching: add `{{ _.role("user", cache_control={"type": "ephemeral"}) }}` and whitelist `allowed_role_metadata ["cache_control"]` on the client. Cached tokens show in `Collector.last.usage.cached_input_tokens`.
- `anthropic-version` header auto-set; override via `options.headers` if needed.

### OpenAI / o1 family

- `o1`, `o1-mini`, `o1-preview` need `max_completion_tokens` instead of `max_tokens`. Set `max_tokens null` explicitly.
- `o1-mini` is NOT supported by `openai-responses` — use `openai` provider.
- Temperature is often hard-wired on reasoning models; setting it may error.

### Vertex + Anthropic

Vertex supports Anthropic models via a different model format (e.g. `claude-3-5-sonnet@20241022`). Configure provider `vertex-ai` but set `model` to the Vertex-formatted name. Credentials via ADC or explicit `credentials` file.

### AWS Bedrock

- Converse API — shared surface across Anthropic, Cohere, Mistral, Meta, AI21 on Bedrock.
- Caching: supported for Anthropic on Bedrock since 0.221.0; cached-token reporting may come back null for some models.
- Region and profile in `options`: `region "us-west-2"`, `aws_profile "myprofile"`.

### Azure OpenAI

- Use the deployment name, not the model name: `options { model "my-gpt-4o-deployment" }`.
- Set `base_url "https://<resource>.openai.azure.com"`.
- API version header: `options { headers { "api-version" "2024-10-21" } }`.

### OpenAI-compatible (`openai-generic`)

Pattern for any OpenAI-compatible endpoint:

```baml
client<llm> LocalVLLM {
  provider "openai-generic"
  options {
    base_url "http://localhost:8000/v1"
    api_key "EMPTY"                     // most local servers ignore
    model "meta-llama/Llama-3.1-70B-Instruct"
  }
}

client<llm> OpenRouter {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    api_key env.OPENROUTER_API_KEY
    model "anthropic/claude-sonnet-4-20250514"
    headers { "HTTP-Referer" "https://myapp.com"  "X-Title" "MyApp" }
  }
}
```

## Environment variables

Referenced via `env.NAME`. Checked LAZILY — missing env var only errors when the client is actually called. Set in a `.env` (auto-loaded by `baml-cli test`/`dev`/`serve` since 0.214.0) or pass `--dotenv-path`.

## Runtime client override cheat sheet

Simplest (since 0.216.0):
```python
b.Fn(x, baml_options={"client": "openai/gpt-4o-mini"})          # one-off
my_b = b.with_options(client="openai/gpt-4o-mini")               # reusable
```

`ClientRegistry` for richer runtime behavior (A/B test, per-tenant routing, add entirely new clients):
```python
from baml_py import ClientRegistry

cr = ClientRegistry()
cr.add_llm_client(name="Tenant42", provider="openai", options={
    "model": "gpt-5-mini",
    "api_key": tenant.key,
    "temperature": 0.0,
})
cr.set_primary("Tenant42")
b.Fn(x, baml_options={"client_registry": cr})
```

**Note**: `client` option overrides `client_registry` when both set. `ClientRegistry` imports from `baml_py`, not `baml_client`.
