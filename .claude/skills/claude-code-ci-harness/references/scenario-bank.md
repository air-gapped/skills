# Scenario Bank

Start with the smallest useful scenario and stop at the first failure.

Create the workdir with `scripts/make-fixtures.sh DIR` and pass it as
`--workdir DIR`. Every file named below comes from that script.

## Smoke

Prompt:

```text
List the files in the working directory. Do not modify anything. Then give a one-sentence summary.
```

Expected: `Glob` or `Read`, followed by a successful `result` event.

## Chained state

Prompt:

```text
Find the largest text-like file in the working directory, read it, and summarize its first paragraph. Do not modify anything.
```

Expected: a discovery tool call followed by a read call and a successful result.

## Error recovery

Prompt:

```text
Try to read missing-file-for-ci.txt. After the expected error, explain what happened and stop. Do not modify anything.
```

Expected: a tool error is returned to the model, the model produces a recovery
response, and the process terminates without a hang.

## Escalation

Keep the same prompt and workdir when comparing endpoints.

### Parallel intent

```text
Read fixture-a.txt and fixture-b.txt in the same turn. Do not modify anything.
```

Expected: two `Read` tool calls in one assistant message, then a successful
result. Assert with `--expect-tools Read,Read --min-parallel 2`; the tool
sequence alone also passes two sequential reads.

### Nested JSON arguments

```text
Call Glob with pattern "references/*.md" and then Read on the file whose name
sorts first. Report the path you chose.
```

Expected: exact tool sequence `Glob,Read`; the `Read` input path matches a
real file from the glob result.

### Shell-safe strings

```text
Read the file named "fixture with spaces.txt". Do not modify anything.
```

Expected: one `Read` call whose path argument preserves the spaces exactly.

### Long context

Preload the workdir with a large file, then:

```text
Read large-fixture.txt and answer: what is the last line? Do not modify anything.
```

Expected: the answer `LAST-LINE-MARKER-7f3a`, with no tool-call format
degradation at depth.
