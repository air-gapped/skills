# Gemma 4 31B chat template — drift, pins, re-vet procedure

Load when choosing or updating the `--chat-template` for a Gemma 4 31B deploy,
or when a quant's bundled template is in question. SKILL.md fact #3 carries the
rule; this file carries the evidence and the procedure.

## Rule

Serve Google's canonical template via `--chat-template`, pinned to a vetted
revision. Never serve the template bundled in `cyankiwi/gemma-4-31B-it-AWQ-4bit`.
`RedHatAI/gemma-4-31B-it-speculator.eagle3` ships no `chat_template.jinja`; it
inherits the base model's.

| Item | Value |
|---|---|
| Vetted canonical revision | google `68abe480` (2026-07-15) |
| Its sha256 / size | `ae53464b…8de4c6d4` / 18683 B |
| Later commits on `main` | `842da379` only — adds `response_template` to `tokenizer_config.json`, template unchanged |
| cyankiwi bundled template | `94899c0f…25bff413` / 16934 B — byte-identical to the 2026-04-30 canonical, 114 diff lines behind |

## What the frozen cyankiwi template loses

The current canonical file opens with Google's header *"Published: 2026-07-09 —
Fixed tool-calling loops, turn closures, and thinking content-ordering."*
Serving the frozen copy silently drops:

| Lost behaviour | Effect of the frozen copy |
|---|---|
| `preserve_thinking` kwarg | absent — thinking content past the last user turn on tool-call messages cannot be kept |
| `continues_into_next` turn closure | emits duplicate `<|turn>model` markers on model→assistant continuations |
| `<|channel>thought` re-open after `tool_response` (thinking on) | missing — see SKILL.md pitfall "Thinking + tool use" |
| `argument is none` → `null` | falls into the string branch |
| `messages and messages[0]` guards | no guard against an empty message list |

## Revision-pin hazard

Both cyankiwi repos (`gemma-4-31B-it-AWQ-4bit`, `gemma-4-31B-it-qat-AWQ-INT4`)
squashed their git history on 2026-07-21. Every pre-squash revision SHA returns
404, so an older `--revision` pin crash-loops on a cold boot with an empty HF
cache. Re-pin to the current HEADs — `6f1b616c` (AWQ-4bit), `e0814036`
(qat-AWQ-INT4). Config, tokenizer and template files are byte-identical across
the squash; re-pinning needs no re-audit.

## Re-vet procedure

Run before each adoption and periodically; a hash change on `main` is a re-vet
trigger, never an auto-adopt (template changes alter parser-facing behaviour).

```bash
d=$(mktemp -d)
curl -sSL -o "$d/g4.jinja" https://huggingface.co/google/gemma-4-31B-it/raw/main/chat_template.jinja
curl -sSL -o "$d/cy.jinja" https://huggingface.co/cyankiwi/gemma-4-31B-it-AWQ-4bit/raw/main/chat_template.jinja
head -7 "$d/g4.jinja"                          # read the in-file Published: date first
sha256sum "$d/g4.jinja" "$d/cy.jinja"          # compare with the table above
diff "$d/g4.jinja" "$d/cy.jinja" | grep -c '^[<>]'
```

- Hash matches `ae53464b…` → no action.
- Hash differs → diff against the vetted revision, re-run the tool-calling and
  thinking + tools probes (SKILL.md pitfalls), then re-pin.
- Read HF repo commit titles (`/api/models/<repo>/commits/main`), not
  `lastModified` — a README-only commit moves the timestamp.

## Hash chain (drift rate, not a pin)

| Pulled | sha256 | Bytes |
|---|---|---|
| 2026-04-30 | `94899c0f…25bff413` | 16934 |
| 2026-05-28 | `36e3a42e…bead3f0` | 17466 |
| 2026-07-21 | `ae53464b…8de4c6d4` | 18683 |
| 2026-08-11 → 2026-10-18 | `ae53464b…8de4c6d4` | 18683 (held) |

## Candidate local edits and upstream PRs

- Do NOT strip the `\n` before `<channel|>` in a local candidate — Google
  measured 7%+ tool-calling regressions without it
  ([#135](https://huggingface.co/google/gemma-4-31B-it/discussions/135)).
- Unmerged template PRs to review before the next adoption:
  [#137](https://huggingface.co/google/gemma-4-31B-it/discussions/137) (keep
  tool-call reasoning across later user turns — prefix-cache win on agent loops),
  [#140](https://huggingface.co/google/gemma-4-31B-it/discussions/140)
  (multimodal placeholders emitted outside the tool_response block), #147, #148.
