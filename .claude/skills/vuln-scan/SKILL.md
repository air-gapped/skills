---
name: vuln-scan
description: >-
  [2/4 defending-code] Static source-code vulnerability scan. Second step of
  the find-and-fix loop (/threat-model -> /vuln-scan -> /triage -> /patch),
  and the usual entry point when no threat model exists. Reads a target
  directory (and
  THREAT_MODEL.md if present), spawns parallel review subagents per focus
  area, and writes VULN-FINDINGS.json + .md for /triage to consume. Read-only
  — no building, running, or network. For execution-verified crashes (build +
  run + sanitizer), see HARNESS.md. Use when asked to "scan for vulns", "review
  this code for security issues", "find bugs in <dir>", "audit this code for
  vulnerabilities", or as the step between /threat-model and /triage.
argument-hint: "<target-dir> [--focus <area>] [--single] [--extra <file>] [--no-score]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Task
  - Bash(rg:*)
  - Bash(grep:*)
  - Bash(ls:*)
  - Bash(wc:*)
  - Bash(head:*)
  - Bash(file:*)
---

# /vuln-scan

Second leg of the defending-code loop (`/threat-model` → **`/vuln-scan`** →
`/triage` → `/patch`). Static vulnerability review of a source tree. Produces
`VULN-FINDINGS.json` (+ a human-readable `.md`) that `/triage` ingests
directly. Reads `THREAT_MODEL.md` if step 1 ran, and falls back to its own
recon if not — so this is a valid place to start the loop.

**This skill does not execute code.** It reads source and reasons about it.
For execution-verified findings (sanitizer crashes, reproducing PoCs), point
the user at an autonomous execution harness — see `HARNESS.md` in this skill
directory for the reference C/C++ + AddressSanitizer pipeline this group was
extracted from.

**Tool fallbacks.** Prefer the dedicated Glob and Grep tools. Some sessions
do not provision them — `allowed-tools` is a permission filter, not a loader,
so listing them here does not make them appear. When Glob/Grep are
unavailable, fall back to the read-only Bash commands whitelisted above:
`rg --files <scope>` / `ls -R` for enumeration, `rg -n` / `grep -rn` for
search, `wc` / `head` / `file` for sniffing. These are the ONLY permitted
Bash commands; do not write helper scripts or pipe target content into a
shell interpreter.

## Arguments

- `<target-dir>` (required) — directory to scan. Relative or absolute.
- `--focus <area>` — scan only this focus area (repeatable). Skips recon.
- `--single` — no subagent fan-out; one sequential pass. Use on tiny targets
  or when debugging the prompt.
- `--extra <file>` — pass the contents of `<file>` to every reviewer as an
  `EXTRA CHECKS` section of its per-spawn prompt (Step 2). Use to add
  org-specific vulnerability classes, compliance checks, or stack-specific
  patterns. Plain text; same shape as the category blocks in the
  `vuln-area-reviewer` agent definition.
- `--no-score` — skip the Step 3b confidence pass (saves a round of
  subagents). Findings keep the scanner's self-reported confidence only.

## Step 1 — Scope

1. Resolve `<target-dir>`. If it doesn't exist or has no source files, stop
   with an error.
2. Look for `<target-dir>/THREAT_MODEL.md`. If present, parse its section 3 "Entry
   points & trust boundaries" table and section 4 "Threats" table for focus areas
   and threat classes. This is the preferred scoping input. Also parse its
   section 2 "Assets" table and section 1 system context into two bullet
   lists — `assets` and `deployment_facts` — for the review brief: severity
   calibration needs what the system protects, not just where input enters.
3. If no THREAT_MODEL.md and no `--focus`: do a **quick recon** — list the
   source tree, read entry points and dispatch code, and propose 3-10 focus
   areas using the pattern `<subsystem> (<function/file>) — <key operations>`.
   During recon, also read any deploy manifests in the target (Helm chart,
   k8s YAML, compose file, Dockerfile env) and note as `deployment_facts`
   what is actually there: mounted secrets, auth in front, sessions/cookies,
   persistent state, tenancy. "Stateless, no auth, chart mounts no secret"
   changes every severity downstream.
4. If `--focus` was given, use exactly those.

Tell the user the focus areas you'll scan and the source-file count before
fanning out.

## Step 2 — Fan out

Unless `--single`, spawn **one review subagent per focus area** in parallel
— all Task calls in a SINGLE message, `subagent_type: "vuln-area-reviewer"`
(plugin installs: `defending-code:vuln-area-reviewer`). Cap at 10
concurrent. The full review brief is that agent definition's system prompt
— shared and prompt-cached across every reviewer in the wave — so each
spawn's prompt carries only the variable facts below. On tiny targets
(<15 source files), fall through to `--single` automatically.

**Fallback:** if neither agent name resolves, Read the agent definition at
`../../agents/vuln-area-reviewer.md` relative to this skill directory (same
layout in the repo and in a plugin install), and spawn `general-purpose`
subagents with its body pasted above the per-spawn block. In `--single`
mode, follow that same body inline, once per focus area sequentially.

### Per-spawn prompt (variable facts only)

```
FOCUS AREA: **{focus_area}**
FINDING ID PREFIX: F-{focus_idx:02d}-
TARGET: {target_dir}
TRUST BOUNDARY: {from THREAT_MODEL.md section 3, or "untrusted input → process memory"}
ASSETS (what is worth protecting here):
{assets bullets from THREAT_MODEL.md section 2, or "(unknown)"}
DEPLOYMENT FACTS (what is actually deployed/mounted):
{deployment_facts bullets, or "(unknown)"}
{if --extra <file> was given:
EXTRA CHECKS:
<file contents verbatim>}
```

## Step 3 — Collate

1. Collect `<finding>` blocks from all subagents. Drop `category=none`
   placeholders.
2. **Light dedupe** — if two findings cite the same `file:line` with the
   same category, keep the one with the longer description and note the
   duplicate id. (Heavy dedupe is `/triage`'s job; don't over-engineer here.)
3. Assign stable ids `F-001`, `F-002`, ... in (severity desc, file, line)
   order.

## Step 3a — Deterministic pre-filter (no subagents)

A mechanical gate between collation and the confidence pass. It exists
because prompt rules alone are not enough — reviewers ignore the
DO-NOT-REPORT list a measurable fraction of the time — and a finding that
fails a check a script could run should never cost a confidence subagent.
**Nothing is dropped**: gated findings stay in the output with a
mechanically assigned confidence and reason, and skip Step 3b.

For each finding, in order:

1. **Hallucinated path.** Resolve `file` under `<target-dir>` (as-given,
   then with common prefixes stripped). If it does not exist on disk:
   set `confidence: 0.05`, `prefilter: "hallucinated_path"`,
   `confidence_reason: "prefilter: cited file not found under target"`.
   Skip 3b for it.
2. **Test/fixture path.** Match the resolved path (case-insensitive)
   against:

   ```
   (^|/)(tests?|__tests__|mocks?|examples?|fixtures?|samples?|testdata)(/|$)
   |_test\.|\.test\.|\.spec\.|Test\.java$|Tests\.cs$
   ```

   On match: set `confidence: 0.15`, `prefilter: "test_path"`,
   `confidence_reason: "prefilter: test/example/fixture path"`. Skip 3b.
   **Exception — committed credentials stay live:** if the category is
   `hardcoded-secret` or the description evidences a committed credential
   (key material, token, password), do NOT gate it — a real secret in a
   fixture file is in source control and was likely real once. It proceeds
   to 3b at its reported confidence.

All other findings get `prefilter: null` and proceed. Report the gate's
work in the terminal ("pre-filter: X hallucinated, Y test-path, Z passed")
— silent gating reads as "nothing was gated".

## Step 3b — Confidence pass (skip if `--no-score`)

A cheap second-opinion read that **ranks** findings by signal quality.
**Nothing is dropped** — this pass calibrates `confidence` so humans and
`/triage` see high-signal findings first. Spawn **one subagent per
finding that passed the Step 3a pre-filter** in parallel — all Task calls
in one message, `subagent_type:
"vuln-confidence-scorer"` (plugin installs:
`defending-code:vuln-confidence-scorer`). The scoring instructions are that
agent definition's cached system prompt; the fallback is as in Step 2, with
`../../agents/vuln-confidence-scorer.md`. Each spawn's prompt is only:

```
FINDING:
{the full <finding> block}

TARGET: {target_dir}
```

**Resolve:** overwrite each finding's `confidence` with the score
(normalized to 0.0-1.0) and attach `confidence_reason`. Re-sort findings
by (`confidence` desc, `severity` desc, `file`, `line`) and reassign ids
`F-001..` in that order. Compute `low_confidence_count` = findings with
confidence < 0.4, for the summary line.

## Step 4 — Write output

Write **both** files to `<target-dir>/`:

**`VULN-FINDINGS.json`** — the `/triage` ingest shape:

```json
{
  "target": "<target-dir>",
  "scanned_at": "<iso8601>",
  "focus_areas": ["..."],
  "findings": [
    {
      "id": "F-001",
      "file": "relative/path.c",
      "line": 123,
      "category": "heap-buffer-overflow",
      "severity": "HIGH",
      "confidence": 0.9,
      "title": "...",
      "description": "...",
      "exploit_scenario": "...",
      "recommendation": "...",
      "confidence_reason": "...",
      "prefilter": null
    }
  ],
  "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "low_confidence": 0, "prefiltered": 0}
}
```

Findings are sorted by `confidence` desc (then severity, file, line), so
the top of the file is the highest-signal material.

**`VULN-FINDINGS.md`** — human-readable: a summary table (id | severity |
category | file:line | title), then one `### F-NNN` section per finding with
the full description.

## Step 5 — Hand back

Tell the user:

1. Counts: N findings (H/M/L split, X low-confidence, P pre-filtered),
   across K focus areas, from M source files.
2. Top 3 by confidence, one line each.
3. Next step: `> /triage <target-dir>/VULN-FINDINGS.json --repo <target-dir>`
4. Remind: these are **static candidates**, not verified. For
   execution-verified crashes, an autonomous harness is needed (see HARNESS.md).

## Constraints

- **Never execute target code.** No builds, no `docker`, no network, and no
  Bash beyond the read-only whitelist in § Tool fallbacks.
  If the user asks you to "reproduce" or "confirm with a PoC," decline and
  point at an autonomous execution harness (HARNESS.md).
- **Don't fabricate line numbers.** Every `file:line` you emit must be
  something you Read or Grep'd. If unsure of the exact line, cite the
  function and say so in the description.
- **Stay in `<target-dir>`.** Don't follow symlinks or `..` out of it.
- Findings are candidates for `/triage`, not final verdicts. **This skill
  never drops a finding** — Step 3b only ranks. `/triage` does the rigorous
  N-vote verification and is where false positives actually get removed.

## Provenance

Adapted (Apache-2.0) from
[`anthropics/defending-code-reference-harness`](https://github.com/anthropics/defending-code-reference-harness)
— the `vuln-scan` skill and its autonomous `find`/`recon` pipeline prompts.
The focus-area recon pattern and memory-safety quality tiers mirror the same
logic the autonomous pipeline uses, applied statically. The broader category
menu, DO-NOT-REPORT exclusions, per-finding confidence pass, and
`exploit_scenario`/`recommendation` output fields originate in
[`anthropics/claude-code-security-review`](https://github.com/anthropics/claude-code-security-review)'s
`/security-review` command. The Step 3a deterministic pre-filter — the
test-path exclusion regex, the committed-credential exception to it, and
the gate-before-the-expensive-stage ordering — is adapted (Apache-2.0) from
[`visa/visa-vulnerability-agentic-harness`](https://github.com/visa/visa-vulnerability-agentic-harness)'s
s5 prefilter stage. See `HARNESS.md` for the execution-verified
pipeline this static skill complements.
