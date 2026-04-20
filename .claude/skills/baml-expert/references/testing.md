# BAML Testing — full reference

## Contents
- [Test block shape](#test-block-shape)
- [Jinja context inside tests](#jinja-context-inside-tests) — `this`, `_.result`, `_.checks`, `_.latency_ms`
- [Arg literals](#arg-literals) — primitives, strings, lists, classes, media
- [Feeding args from a template_string](#feeding-args-from-a-template_string)
- [TypeBuilder inside tests](#typebuilder-inside-tests) — `@@dynamic` runtime extension
- [Soft vs hard assertions](#soft-vs-hard-assertions) — `@@check` vs `@@assert`
- [Running tests](#running-tests) — baml-cli test flags + exit codes
- [CI integration](#ci-integration) — GitHub Actions example, rate-limit tips
- [Streaming tests](#streaming-tests), [Human eval](#human-eval), [VSCode playground](#vscode-playground)
- [When tests flake](#when-tests-flake) — temperature 0, structural asserts, pinned models

BAML tests live in `.baml` files alongside the functions they cover. They are first-class, runnable via CLI and the VSCode playground, and they are the canonical way to catch regressions when prompts or schemas change. Use them as the primary verification step — they run against real LLMs, and the assertion language is rich enough to express most real invariants.

## Test block shape

```baml
test <TestName> {
  functions [<Fn1>, <Fn2>, ...]     // all must share the same signature
  args {
    <param_name> <value>
    <param_name> { ... }            // nested class literal
  }
  type_builder { ... }              // optional; inject into @@dynamic types
  @@check(<name>, {{ <jinja> }})    // soft — surfaces in report but doesn't fail
  @@assert({{ <jinja> }})           // hard — fails the test
  // multiple of each allowed
}
```

`functions [...]` runs the test against every listed function. Useful when you have a baseline function and a refactor running side by side, or an `@@dynamic` variant.

## Jinja context inside tests

| Variable | Meaning |
|---|---|
| `this` | The return value. Same as `_.result` for ergonomic field access (`this.name`). |
| `_.result` | Return value (alias). |
| `_.checks.<name>` | Bool — whether the named `@@check` passed. |
| `_.latency_ms` | Wall-clock latency of the LLM call. |

Example combining them:

```baml
@@check(nonempty_name, {{ this.name|length > 0 }})
@@check(has_skills, {{ this.skills|length > 0 }})
@@assert({{ _.checks.nonempty_name and _.checks.has_skills and _.latency_ms < 30000 }})
```

## Arg literals

```baml
args {
  // primitives
  age 42
  name "John"
  active true
  score 3.14

  // strings (block literal with #"..."#)
  resume_text #"
    Multi-line
    text block
  "#

  // lists
  tags ["python", "rust"]

  // nested class / map
  user { name "J"  age 30 }
  scores { "alice" 95  "bob" 87 }

  // enum
  level "SENIOR"

  // media — inside baml_src only
  doc { file "../fixtures/cv.pdf" }           // relative to the .baml file
  img { url "https://example.com/a.png" }
  voice { base64 "iVBORw..."  media_type "audio/wav" }
}
```

**Media files must live under `baml_src/`**. External paths fail to resolve. If the fixture is huge, keep a separate `baml_src/fixtures/` subfolder and `.gitignore` what shouldn't be committed. Git LFS once fixtures exceed ~500 MiB.

## Feeding args from a `template_string`

When the same test-input text is reused across many tests, factor it out:

```baml
template_string LongResume() #"
  John Doe...
  (many lines)
"#

test A { functions [Extract] args { resume_text: LongResume() } }
test B { functions [Classify] args { resume_text: LongResume() } }
```

Template strings work as argument expressions since they return strings — parameterize them if you want variations.

## TypeBuilder inside tests

When a class/enum is `@@dynamic`, tests can add fields or enum values at runtime:

```baml
class Experience { title string  company string }

class Resume {
  name string
  skills string[]
  @@dynamic
}

test WithExperience {
  functions [Extract]
  args { resume_text #"..."# }
  type_builder {
    class Experience { title string  company string }
    dynamic class Resume {
      experience Experience[]          // added at runtime
    }
  }
  @@assert({{ this.experience|length > 0 }})
}
```

The `dynamic class X { ... }` syntax extends the base `X`. `dynamic enum Y { ADD_THIS }` adds enum values.

## Soft vs hard assertions

- `@@assert({{ ... }})` — test fails if the expression is false. Use for invariants that must hold.
- `@@check(name, {{ ... }})` — check result is captured in the report and available as `_.checks.name`, but doesn't fail. Use when you want the information without the failure (e.g. to decide a complex mandatory assertion from multiple checks).

Typical pattern: many `@@check` for observable properties, one `@@assert` that composes them into a pass/fail rule.

## Running tests

```bash
baml-cli test                                    # all tests
baml-cli test -i '<Fn>::<Test>'                  # specific test (glob allowed)
baml-cli test -i 'Extract*::Basic*'              # glob
baml-cli test -x 'Extract::Slow*'                # exclude
baml-cli test --list                             # list without running
baml-cli test --parallel 8                       // default 10
baml-cli test --pass-if-no-tests                 // CI-friendly when no tests match a filter
baml-cli test --require-human-eval               // exit code 2 unless human confirms outputs
baml-cli test --dotenv-path .env.test            // override .env location
baml-cli test --no-dotenv                        // don't load .env at all
baml-cli test --from path/to/baml_src            // if not in cwd
```

**Exit codes**: 0 pass, 1 fail, 2 human-eval-required, 3 cancelled (Ctrl-C), 4 no tests found (without `--pass-if-no-tests`).

## CI integration

Minimal GitHub Actions job:

```yaml
- run: pip install baml-py
- run: baml-cli generate --no-version-check
- run: baml-cli test --parallel 4 --dotenv-path .env.ci
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

Budget tip: mark expensive model calls behind a `@@skip` (BAML's own), or segment into a separate test file that only runs nightly (e.g. via `baml-cli test --from baml_src_nightly` if you physically split).

Watch for rate limits — `--parallel 10` across many providers will trip Anthropic faster than OpenAI. Start at `--parallel 3` and increase.

## Streaming tests

Tests run the non-streaming path by default. For streaming-specific invariants (ordering, intermediate states), write a Python unit test that subscribes to `b.stream.Fn(...)` and asserts on the partial sequence.

## Human eval

`@@human_eval` on a test marks the result for manual inspection; combined with `--require-human-eval` it gates CI on reviewer approval. Useful for subjective outputs (copy quality, tone) that don't map to assertions.

## VSCode playground

With the Boundary extension (VSCode or Cursor), every function and test has a CodeLens "Open Playground" button. The playground panel shows:
- The exact prompt rendered with `{{ ctx.output_format }}` expanded.
- The raw cURL — full HTTP request that goes to the provider.
- Test runner with parallel toggle.
- Prompt history for A/B comparisons.

Env vars used by the playground live in VSCode local storage only (never committed, never sent anywhere). Set them via the "BAML" sidebar.

## When tests flake

LLM calls are non-deterministic. Common tactics:
- Set `temperature 0` in the client used by tests.
- Use `@@check` to surface variance and an `@@assert` that allows a wider range than the typical output.
- Use SAP's permissiveness — don't assert on `_.result == "exact string"`; assert on structural properties (length, field presence, enum value membership).
- Pin model versions explicitly (`"gpt-4o-mini-2024-07-18"` rather than `"gpt-4o-mini"`).
- If a test depends on external state (dates, prices), make the state part of the input.
