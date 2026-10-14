# Scenario authoring and debugging

## Feeding scenarios

| Shape | Command |
|---|---|
| One line | `isolated-run.sh ... --prompt "List *.py files, then read the largest."` |
| Multi-line | `isolated-run.sh ... <<'EOF'` … `EOF` (omit `--prompt`) |
| Templated | `envsubst < scenario.md \| isolated-run.sh ...` — `${VAR}` placeholders per matrix row |

## jq recipes (v2 transcript)

```bash
jq -r 'select(.type=="tool_use") | .part.tool' t.ndjson                       # tools in order
jq -c 'select(.type=="tool_use") | {tool:.part.tool, in:.part.state.input}' t.ndjson
jq -c 'select(.type=="tool_use" and .part.state.status=="error")' t.ndjson    # failed tool calls
jq -rs 'map(select(.type=="text")) | last | .part.text' t.ndjson              # final text
jq -c 'select(.type=="error") | .error' t.ndjson                              # errors
jq -s 'map(select(.type=="step_start")) | length' t.ndjson                    # turns
jq -s '[.[] | select(.type=="step_start" or .type=="tool_use") | .type]' t.ndjson  # parallel check: N tool_use between two step_start
jq -r 'select(.type=="tool_use") | .part.state.metadata.rawInput' t.ndjson    # arguments string as the engine returned it
```

## Session export (raw assistant parts)

The scratch home is deleted on exit; keep it to export:

```bash
OC_CI_KEEP=1 bash isolated-run.sh ... > t.ndjson 2> t.stderr   # stderr prints the kept path
T=/tmp/oc-ci-XXXXXX                                              # from stderr
SID=$(jq -r .sessionID t.ndjson | head -1)
( export OPENCODE_TEST_HOME=$T HOME=$T XDG_CONFIG_HOME=$T/config XDG_DATA_HOME=$T/data \
    XDG_CACHE_HOME=$T/cache XDG_STATE_HOME=$T/state TMPDIR=$T/tmp OPENCODE_CONFIG_PROJECT_DISABLE=1
  cd "$WORKDIR" && opencode session export "$SID" --standalone </dev/null ) > session.json
jq 'keys' session.json    # discover the shape before writing paths
rm -rf "$T"
```

## Failure rubric

| Observation | Class | Route |
|---|---|---|
| Correct tool name, empty or mangled `input` | Template / parser | Read `state.metadata.rawInput`: broken → engine parser argument extraction or template `tojson(arguments)`; intact but `input` wrong → opencode-side bug |
| No `tool_use`, raw text contains tool-call syntax | Parser format not recognized | Engine tool-call parser selection |
| No `tool_use`, tool schemas absent from the rendered prompt | Template drops `tools` | Chat template `tools` block |
| Tool result never consumed (model re-asks) | Template drops tool results in history | Chat template history loop |
| Engine `error` with parser traceback | Engine parser crash | Engine log |
| Wrong tool, wrong path, wrong number with correct tool outputs | Model behavior | Not a pipeline bug; confirm on a larger / BF16 variant |
| Tool call on a no-tool question (tier 4) | Model tool discipline | Not a parser bug |

Separate model from parser: same scenario, two models, same parser. One passes → model. Both fail and a different parser passes → parser.

## Engine-side capture

```bash
grep -iE 'tool_parser|Traceback|ValueError' engine.log
grep -E 'POST /v1/(chat/completions|responses|messages)' engine.log   # which API was hit
```

For request bodies enable the engine's request logging, or put mitmproxy between opencode and the engine.
