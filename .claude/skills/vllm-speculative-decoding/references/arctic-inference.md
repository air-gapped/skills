# Arctic Inference (Snowflake) — plugin + suffix decoding

Load when deploying suffix decoding (already upstreamed, still requires the
Arctic pip package) or considering Arctic-only features (LSTM-Speculator,
SwiftKV, Shift Parallelism) behind the plugin.

## What it is

A **vLLM plugin**, not a fork. Monkey-patches vLLM in-process on import. No
separate runtime, no daemon. Install:

```bash
pip install arctic-inference
# or latest:
pip install "git+https://github.com/snowflakedb/ArcticInference.git#egg=arctic-inference[vllm]"
```

Air-gap friendly: pure Python + PyTorch, no phone-home, no cloud callouts at
runtime. The *speculator checkpoints* live on Hugging Face — mirror them for
air-gap cutover.

Repo: <https://github.com/snowflakedb/ArcticInference>

## Feature surface relevant to spec-dec

### Suffix Decoding — upstream, needs plugin

Suffix decoding was upstreamed via PR #25784 (v0.12, 2025-11-03) as
`method: "suffix"`. vLLM's proposer is a thin wrapper around Arctic's
`SuffixDecodingCache` (`vllm/v1/spec_decode/suffix_decoding.py:9-85`), so the
plugin is still required at runtime (lazy imported; engine throws if missing).

Paper: arXiv 2411.04975 (NeurIPS 2025). Project site:
<https://suffix-decoding.github.io/>.

**Killer workloads:**
- Code editing (each edit shares long common prefix with prior version)
- Agentic loops — self-reflection, self-consistency, SWE-Bench
- RL rollouts — same prompts re-evaluated thousands of times
- Benchmark harnesses — repeated evaluation of the same questions

Published numbers:
- **1.8–4.5× end-to-end on SWE-Bench**
- **5.3× on agentic SQL workloads**
- **2.8× over EAGLE-2/3 on agentic workloads**
  ([Snowflake blog](https://www.snowflake.com/en/engineering-blog/suffixdecoding-arctic-inference-vllm/))

**Anti-workload**: open-ended chat with no repetition. The suffix tree won't
find matches, AL collapses to ~1, tree maintenance is pure overhead.

### LSTM-Speculator — plugin-only, not upstream

Arctic's own drafter architecture. Snowflake's published comparison:
- Baseline MLP-Speculator: 13.7% accept rate
- Arctic LSTM-Speculator: **44.5%** accept rate
- 3.1× speedup over MLP-Speculator on their eval

Pretrained checkpoints:
- `Snowflake/Arctic-Text-Gen-Speculator-Llama-3.1-8B`
- `Snowflake/Arctic-Text-Gen-Speculator-Llama-3.1-70B`
- `Snowflake/Arctic-Text-Gen-Speculator-Llama-3.3-70B`
- `Snowflake/Arctic-Text-Gen-Speculator-Qwen2.5-32B`

To use: install plugin, point `--speculative-config` at the Snowflake
checkpoint. The plugin handles the LSTM method registration; no upstream
method enum added.

### SwiftKV — not spec-dec, adjacent

Reuses earlier-layer hidden states to skip later layers on prefix-overlap
tokens. Up to 50% prefill compute reduction, 2× throughput on long-prompt
enterprise workloads. Orthogonal to spec-dec but stacks.

### Shift Parallelism — not spec-dec

Dynamic TP/SP switching based on batch state. Paper arXiv 2507.11830. Claims
3.4× faster completion, 1.75× faster gen vs vanilla vLLM. Again orthogonal.

## Canonical invocation — suffix decoding

```bash
# Install the plugin
pip install arctic-inference

# Then just use the upstream method name
vllm serve <target> \
  --speculative-config '{"method":"suffix","num_speculative_tokens":32,"suffix_decoding_max_spec_factor":1.0,"suffix_decoding_min_token_prob":0.1}'
```

`num_speculative_tokens` acts as a ceiling; per-request speculation is dynamic
based on `suffix_decoding_max_spec_factor × prefix_match_length`.

## Air-gap checklist

1. Mirror the `arctic-inference` wheel to internal PyPI or install from a
   vendored tarball. The package itself has no runtime callouts.
2. For LSTM-Speculator checkpoints, mirror
   `Snowflake/Arctic-Text-Gen-Speculator-*` to internal HF mirror (or download
   to `HF_HOME` directly — see `vllm-configuration` skill).
3. Plugin imports on first `SpecDecodeProposer` instantiation — any missing
   dependency fails engine start with a clean error. Add the plugin to the
   base container image; don't rely on runtime install.

## When NOT to use Arctic Inference

- Workload is open-ended chat → suffix decoding won't help, LSTM- and
  MLP-speculators are beaten by EAGLE-3 / MTP on general traffic
- Target has no Snowflake speculator checkpoint → plain EAGLE-3 or a
  draft_model setup is easier
- Plugin monkey-patching is unacceptable in production → use the upstream
  `method: "suffix"` only (the plugin is still required but its surface
  area is bounded to suffix decoding alone)

## Troubleshooting

- `ImportError: arctic-inference is required for suffix decoding` — install
  `pip install arctic-inference`; the error is raised in
  `config/speculative.py:644-649` at engine start.
- Low AL on suffix method for a workload expected to benefit → inspect
  `suffix_decoding_max_cached_requests` (default 10000, but workloads with
  rare prompt repetition need it higher; 0 disables global cache entirely and
  falls back to prompt-only).
- Memory growth over time — the global suffix tree grows unboundedly if
  `max_cached_requests` is unset or too high. Tune based on real traffic.
