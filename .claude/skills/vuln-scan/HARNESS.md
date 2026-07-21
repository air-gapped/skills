# The autonomous execution harness (pointer)

This `defending-code` skill group is the **static / interactive half** of a
find-and-fix loop: `threat-model` → `vuln-scan` → `triage` → `patch`. Every
skill here reads and writes files only — it never builds, runs, or detonates
the target. That makes the group safe to run unsandboxed against any local
checkout, but it also means discovery is *static*: findings are reasoned from
source, not proven by a crash.

The **execution-verified** half — build the target, craft an input, run it
under a sanitizer until it crashes 3/3, verify in a fresh container, write an
exploitability report, then generate and re-attack a patch — lives in a
separate reference implementation this group was extracted from:

> **`anthropics/defending-code-reference-harness`**
> https://github.com/anthropics/defending-code-reference-harness
> (Apache-2.0). Accompanying write-up:
> https://claude.com/blog/using-llms-to-secure-source-code

## What it is

A Python pipeline (`vuln-pipeline`) for **C/C++ memory-safety** bugs, using
**Docker + AddressSanitizer** for the build/detector and **gVisor** for
agent isolation (egress locked to the model API). Seven stages: build → recon
→ find → verify → dedupe → report → patch. It is a *reference, not a product* —
it will not run on every codebase out of the box.

**Two things worth knowing before you run it** (both verified 2026-07-21):

- **It tags its own API traffic.** `harness/auth.py` stamps a declared usage
  marker on outbound agent requests — `anthropic-cyber-runbook: pipeline` plus
  `User-Agent: cyber-runbook/<version> (claude-cli/<version>)`. **First-party
  callers only**; the code notes Bedrock/Vertex rewrite the `User-Agent`, so the
  marker doesn't apply there. If you are running this in an environment where
  outbound request attribution matters, know it before, not after.
- **It is no longer only find-and-fix.** A **detection & response track** landed
  2026-07-16 — `dnr-pipeline`, a `dnrcanary` target, and `dnr-hunt` /
  `dnr-respond` skills — alongside the scan→triage→patch pipeline this group was
  extracted from. Not part of the seven stages above; mentioned so the repo's
  scope doesn't surprise you.

## When you'd reach for it

- You want **execution-verified crashes** (a reproducing PoC), not static
  candidates — i.e. the false-positive rate of static review is too high for
  your purpose.
- The target is **C/C++** (or you're willing to port). The harness ships a
  `/customize` skill that interviews you and rewrites its prompts/detector for
  another language, vuln class, or detection signal (exception, canary file,
  differential mismatch, etc.).
- You have Docker and can run a sandbox. Agent-spawning subcommands refuse to
  start outside gVisor unless explicitly overridden.

For most non-C/C++ stacks (web/API, IaC, Python services, infra), the static
group here plus your own test/CI sandbox is the pragmatic path; the blog post's
own framing is "you don't necessarily need to run PoCs in a sandbox — frontier
models are good at finding vulnerabilities from source alone; budget the saved
time for verification instead."

## Running it (from a clone)

```bash
git clone https://github.com/anthropics/defending-code-reference-harness
cd defending-code-reference-harness
python3 -m venv .venv && .venv/bin/pip install -e .
./scripts/setup_sandbox.sh                       # installs gVisor, builds agent images (needs Docker)
export ANTHROPIC_API_KEY=sk-ant-...              # or CLAUDE_CODE_OAUTH_TOKEN

bin/vp-sandboxed run <target> --model <m> --runs 3 --parallel --stream --auto-focus
bin/vp-sandboxed patch results/<target>/<ts>/ --model <m>
```

Its output `results/<target>/<ts>/` directory is directly ingestible by the
`triage` and `patch` skills in this group (point them at the directory).

## Managed alternative

Anthropic also offers **Claude Security**
(https://claude.com/product/claude-security) — a hosted product that scans,
multi-stage-verifies, and manages findings across projects. The harness above
is the open reference; Claude Security is the managed version.

## Attribution

The four skills in this group (`threat-model`, `vuln-scan`, `triage`, `patch`)
and the bundled `checkpoint.py` are adapted under the Apache License 2.0 from
`anthropics/defending-code-reference-harness`. The `vuln-scan` category menu
and exclusion rules additionally draw on
`anthropics/claude-code-security-review`. The repo-specific `quickstart` and
`customize` skills and the Python `harness/` were intentionally **not**
extracted — `quickstart` is a front door for that repo, `customize` ports that
repo's pipeline, and the harness is the execution engine described above.
