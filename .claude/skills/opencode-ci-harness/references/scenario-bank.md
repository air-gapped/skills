# Scenario bank

Run tiers in order; stop at the first failure; record its break class.

## Workdir scaffold

```bash
W=$(mktemp -d /tmp/oc-scenarios-XXXXXX)
mkdir -p "$W/src" "$W/tests" "$W/data"
cat > "$W/src/main.py" <<'EOF'
def hello(): print("hello")
if __name__ == "__main__": hello()
EOF
cat > "$W/src/utils.py" <<'EOF'
def add(a,b): return a+b
def mul(a,b): return a*b
EOF
cat > "$W/src/api.py" <<'EOF'
def fetch(url): return f"fetched:{url}"
EOF
cat > "$W/src/db.py" <<'EOF'
def save(row): return f"saved:{row}"
EOF
cat > "$W/src/log.py" <<'EOF'
def info(msg): print(f"[INFO] {msg}")
EOF
cat > "$W/tests/test_utils.py" <<'EOF'
from src.utils import add, mul
def test_add(): assert add(1,2) == 3
def test_mul(): assert mul(2,3) == 6
EOF
cat > "$W/README.md" <<'EOF'
# Test project
Five Python modules under src/. Tests under tests/. Start at main.py.
EOF
cat > "$W/data/config.json" <<'EOF'
{"db":{"host":"localhost","port":5432,"retries":[1,2,5]},"features":{"ocr":true,"ner":false}}
EOF
export W
```

## Runner

```bash
H=${CLAUDE_SKILL_DIR}/scripts
# Endpoint:          TARGET=(--model "$MODEL" --base-url "$BASE_URL" --api-key "$API_KEY")
# Stored credential: TARGET=(--credential INTEGRATION --model "INTEGRATION/MODEL_ID")
run_tier() {
  local tier="$1" prompt="$2" timeout="${3:-600}"
  bash "$H/isolated-run.sh" "${TARGET[@]}" --workdir "$W" --max-turns 12 \
    --timeout "$timeout" --prompt "$prompt" > "$W/$tier.ndjson" 2> "$W/$tier.stderr"
  echo "$tier exit=$? tools=$(jq -r 'select(.type=="tool_use") | .part.tool' "$W/$tier.ndjson" | paste -sd,)" \
       "errors=$(jq -c 'select(.type=="error")' "$W/$tier.ndjson" | wc -l)"
}
```

Assertions: `bash $H/assert-tool-sequence.sh <fn> "$W/<tier>.ndjson" ...`.

## Tiers

### 0 — Smoke

Prompt: `List the Python files in the workdir. Read each one. For each, report the first line in one sentence.`

- Pass: ≥ 1 `glob`; ≥ 5 distinct `read` paths; no `error`; final text names every file.
- Break: no `tool_use` at all → wiring/parser broken; stop.

### 1 — Parallel reads

Prompt: `Read every .py file under src/ in PARALLEL (single turn). Then state the number of functions defined across all of them.`

- Pass: ≥ 4 of the 5 `src/*.py` reads between the same two `step_start` events; final count 6 (±1).
- Break: one read per step → no parallel tool_calls (template or model); `tool_use` missing while text shows calls → parser misses the array form; same file read twice → model loses parallel state.

### 2 — Chained state

Prompt: `Read README.md. Identify which file the README says to start at. Read ONLY that file. Do not read any other file.`

- Pass: exactly 2 `read` calls, second is `src/main.py`, in separate steps.
- Break: reads everything up front → tool_result not used for planning; never reads main.py → tool_result not rendered or truncated.

### 3 — Nested quoting in args

Run with `--allow-shell`. Prompt: ``Use bash to run `cat data/config.json | jq '.db.retries'`. Then write a short summary of the retry policy.``

- Pass: one `shell` call whose `command` contains `jq '.db.retries'` verbatim; final text contains `[1,2,5]` or 1, 2, 5.
- Break: unbalanced quotes → `repr()` instead of `tojson`; empty `command` → parser dropped the argument; `\\\"` → double serialization.

### 4 — Irrelevance

Prompt: `What is 1337 * 42? Answer with just the number.`

- Pass: zero `tool_use`; final text `56154`.
- Break: any tool call → model tool discipline (not a parser bug).

### 5 — Error recovery

Prompt: `Read the file src/thispaththatdoesnotexist.py. If it does not exist, list the actual files in src/ and state which ones DO exist.`

- Pass: first `read` has `state.status=="error"` or a not-found output; a follow-up `glob`/`read`/`shell`; final text lists ≥ 3 real files.
- Break: run stops after the tool error → error path broken; claims content for the missing file → model confabulation.

### 6 — Long context

Setup:

```bash
python3 -c 'import random; random.seed(0); print("\n".join(
  f"line {i}: " + " ".join(random.choices(
    ["alpha","beta","gamma","delta","epsilon","zeta"], k=8))
  for i in range(3500)))' > "$W/data/big.txt"
```

Prompt: `Read data/big.txt. Count the number of lines containing the word "gamma". Report the count.`

- Pass: no `error`; a later `step_finish` shows `tokens.input` ≥ 30000 (or the read output is complete); count is plausible (`grep -c gamma "$W/data/big.txt"` is ground truth).
- Break: count far off → engine or read truncated input; parser crash → long-context streaming bug.

### 7 — Shell quoting

Run with `--allow-shell`.

Prompt: `Use bash to run: echo 'quotes: "double" and '"'"'single'"'"'' and then echo the result of `date +%s`.`

- Pass: `command` keeps both quote kinds; output contains `"double"` and `'single'`; a 10-digit timestamp.
- Break: corrupted `command` → template escaping mismatch.

### 8 — JSON-in-JSON

Prompt: `Read data/config.json. Report the value of features.ocr as a boolean. Do not read any other file.`

- Pass: one `read` of `data/config.json`; final text `true`; no further calls.
- Break: file replayed as text → output re-parsed; `false` → model misread (do not route to the parser).

### 9 — Denied tool

The runner denies every tool except `read`, `glob`, `grep`, `list` (plus `shell` with `--allow-shell`).

Prompt: `Write "hello" to a new file called /tmp/should_fail.txt. Then tell me whether the write succeeded.`

- Pass: model reports the denial or checks the outcome before claiming success. If it used `shell` to write, verify the file exists and delete it.
- Break: claims success without evidence → model honesty signal, not a parser bug.
