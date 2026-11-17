# Prompt optimization: `baml-cli optimize`, and where DSPy fits

Load when asked to improve a prompt's accuracy or cost, to run or script
`baml-cli optimize`, or to choose between BAML and DSPy.

## `baml-cli optimize` (v0, 0.215.0+, beta)

GEPA search over one function's prompt. The score is the function's own `test`
blocks, so the tests are the training data.

1. **Write tests first.** Every `@@assert` counts toward `accuracy`. A function
   with no runnable test aborts with `No tests found`. Use inputs shaped like
   real traffic; two tests optimize toward two tests.
2. **Commit.** A chosen candidate overwrites the `.baml` source.
3. **Run** from the directory that contains `baml_src/`:

   ```bash
   baml-cli optimize --beta -f ExtractSubject          # TUI: arrows select, Enter applies
   baml-cli optimize --beta -f ExtractSubject --no-ui --apply   # CI: no TUI, write the winner
   ```

4. **Review the diff, then `baml-cli test`.** The optimizer rewrites the prompt
   text and the `@description` / `@alias` of the classes and enums the function
   uses. It never renames, adds or removes a field, so call sites keep working.

### Flags

| Flag | Default | Does |
|---|---|---|
| `--beta` | — | Required. Without it the command prints a notice and exits 1 (`--view` is exempt) |
| `-f, --function <Name>` | all | Limit to a function; repeatable |
| `-t, --test <pattern>` | all | Same syntax as `baml-cli test -i` (`"Fn::*"`, `"::Name"`) |
| `--trials <n>` | 20 | Candidate prompts to try |
| `--max-evals <n>` | 50 | Test executions across all candidates. One cycle needs `2 × tests`; raise it for large suites |
| `--auto light\|medium\|heavy` | — | Preset budget: 6 / 12 / 18 candidates |
| `--weight k=v,k=v` | accuracy only | Objectives: `accuracy`, `tokens`, `prompt_tokens`, `completion_tokens`, `latency`, or the name of a `@@check` |
| `--apply` | off | Write the best candidate to source; without it results stay in `.baml_optimize/` |
| `--no-ui` | off | Text output only |
| `--parallel <n>` | 4 | Concurrent test executions |
| `--resume <run-dir>` | — | Continue `.baml_optimize/run_YYYYMMDD_HHMMSS` |
| `-v, --view` (`--run-dir <dir>`) | — | Browse a finished run |
| `--reset-gepa-prompts` | off | Rewrite the reflection prompts and client to the bundled defaults |

- **The flag is `--weight`.** The docs page also shows `--weights`; that
  spelling is rejected.
- **Custom objective:** name a soft check and weight it —
  `@@check(no_hallucination, {{ this.age == null }})` then
  `--weight accuracy=0.1,no_hallucination=0.9`. Give the same check name to
  several tests.
- **Shorter prompts:** `--weight accuracy=0.2,prompt_tokens=0.8` trades
  accuracy for input tokens (drops descriptions, abbreviates aliases).

### The reflection model

The model that proposes candidates is `client<llm> ReflectionModel` in
`.baml_optimize/gepa/baml_src/clients.baml` — by default provider `anthropic`,
so `ANTHROPIC_API_KEY` must be set. The file is created on the first run;
`--reset-gepa-prompts` creates it without starting a run.

To use another model or a local endpoint, edit that block (any v0 provider
works, e.g. `openai-generic` with `base_url`). In `gepa.baml` beside it, only
add text to the prompts of `ProposeImprovements`, `MergeVariants` and
`AnalyzeFailurePatterns`; changing or deleting its classes breaks the run.

`.baml_optimize/` sits beside `baml_src/` and is added to `.gitignore`
automatically.

### Limits

- One function at a time. A pipeline of several functions is not optimized as a
  whole.
- Every failure counts against the prompt, a provider 500 included. Re-run or
  raise `--max-evals` after a flaky run; do not trust a single low score.
- It does not find or use `template_string`s the function does not already call.
- It tunes instructions and schema text only: no few-shot example selection, no
  fine-tuning.

## DSPy

DSPy is a Python library that compiles a multi-step LLM program against a
metric. BAML is a typed-function DSL with generated clients. They overlap on
"structured output from a prompt" and on GEPA; the rest differs.

| Need | Use |
|---|---|
| Typed client in TypeScript, Go, Ruby, Rust, Elixir or over REST | BAML — DSPy is Python only |
| Partial structured objects while streaming | BAML — DSPy streams `str` fields only |
| Tolerant parsing of malformed output (SAP), `retry_policy`, `fallback`, `round-robin` | BAML |
| One function, improved against its own tests | BAML — `baml-cli optimize` |
| A pipeline of several LLM steps optimized together against an end-to-end metric | DSPy — `baml-cli optimize` is single-function |
| Few-shot examples selected from data (`BootstrapFewShot`, `MIPROv2`) | DSPy — BAML has no equivalent |
| Distilling the program into fine-tuned weights (`BootstrapFinetune`) | DSPy |
| A built-in tool-calling agent loop (`dspy.ReAct`) | DSPy — in BAML a tool is a returned class and the loop is your code |

In an existing BAML project, do not introduce DSPy for a single-function
accuracy problem: write tests and run `baml-cli optimize`.

### Using both

No bridge exists upstream in either direction. What works is plain Python:

- **BAML function inside a DSPy program.** Call `b.Fn(...)` from a
  `dspy.Module.forward`. DSPy optimizers tune `dspy.Predict` steps only, so
  the BAML step stays fixed while the steps around it are tuned.
- **Optimize in DSPy, ship in BAML.** Run the DSPy optimizer, copy the winning
  instruction text into the function's `prompt`, paste any selected demos in
  as literal examples, then run `baml-cli test`. The copy is manual and is
  repeated after every re-optimization.
- **`BAMLAdapter` is not BAML.** `from dspy.adapters.baml_adapter import
  BAMLAdapter`, then `dspy.configure(lm=lm, adapter=BAMLAdapter())`. It renders
  nested Pydantic output types in BAML's compact schema style and nothing
  more: no SAP (output is parsed with `json_repair`), no `baml-py`, no `.baml`
  files. `dspy.BAMLAdapter` as written in DSPy's adapter docs is not exported.

`dspy.GEPA` and `baml-cli optimize` are separate implementations of the same
algorithm. DSPy's takes a Python metric that can return textual feedback, a
`reflection_lm`, and exactly one budget argument (`auto`, `max_full_evals` or
`max_metric_calls`); it tunes the instructions of every predictor in the
program.
