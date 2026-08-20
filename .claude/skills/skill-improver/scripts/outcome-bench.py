#!/usr/bin/env python3
"""Outcome benchmark for one skill: with_skill vs without_skill pass rate.

Produces the run-directory layout that skill-creator's aggregate_benchmark.py
expects, so `delta_pass_rate` comes from the official aggregator rather than
from arithmetic done here.

Hermetic, following knowledge-floor.py's pattern: each condition gets ONE
stable project dir (stable so the prompt-cache prefix is shared, empty-or-
minimal so skill resolution is controlled by construction rather than by
instruction). `--setting-sources project` means only that dir's .claude/skills
resolves -- the operator's profile skills never leak into either condition.

  without_skill : empty project dir  -> no skill can resolve
  with_skill    : project dir containing ONLY the skill under test
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Mutation and network denied in both conditions: the eval prompts are
# planning-shaped and the assertions grade the plan, so tool use would add
# variance without adding signal. Read/Glob/Grep/Skill stay ALLOWED because
# with_skill must be able to actually load the skill -- that is the treatment.
DENY = ["Bash", "Edit", "Write", "NotebookEdit", "Agent", "Task",
        "WebFetch", "WebSearch"]  # fmt: skip

CACHE = Path.home() / ".cache" / "skill-improver"


def project_dirs(skill_src: Path) -> tuple[Path, Path]:
    without = CACHE / "bench-without"
    with_ = CACHE / "bench-with"
    without.mkdir(parents=True, exist_ok=True)
    (without / ".claude").mkdir(exist_ok=True)
    (without / ".claude" / "skills").mkdir(exist_ok=True)

    dest = with_ / ".claude" / "skills" / skill_src.name
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_src, dest)
    return without, with_


def run_claude(prompt: str, cwd: Path, timeout: int = 420) -> tuple[str, bool]:
    cmd = ["claude", "-p", prompt, "--output-format", "json",
           "--setting-sources", "project", "--disallowedTools", *DENY]  # fmt: skip
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(cwd), env=env, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return "", False
    if p.returncode != 0:
        return "", False
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError:
        return "", False
    return d.get("result", "") or "", True


GRADER = """You are grading one response against a list of assertions.

For EACH assertion, decide whether the RESPONSE satisfies it. Judge only what
the response actually says -- do not credit it for things it merely gestures at,
and do not penalise it for extra content. An assertion about "plans to" or
"proposes" is satisfied if the response clearly commits to that action.

Return STRICT JSON, no prose, no code fence:
{"expectations":[{"text":"<assertion verbatim>","passed":true|false,
"evidence":"<short quote or why it failed>"}]}

ASSERTIONS:
%s

RESPONSE:
%s
"""


def grade(response: str, assertions: list[str], cwd: Path) -> dict:
    if not response.strip():
        return {
            "expectations": [
                {"text": a, "passed": False, "evidence": "empty response"}
                for a in assertions
            ]
        }
    numbered = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(assertions))
    out, ok = run_claude(GRADER % (numbered, response), cwd)
    if not ok:
        return {
            "expectations": [
                {"text": a, "passed": False, "evidence": "grader failed"}
                for a in assertions
            ]
        }
    t = out.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        d = json.loads(t)
    except json.JSONDecodeError:
        return {
            "expectations": [
                {"text": a, "passed": False, "evidence": "unparseable grader output"}
                for a in assertions
            ]
        }
    exps = d.get("expectations", [])
    # Normalise: the aggregator requires text+passed on every row.
    fixed = []
    for i, a in enumerate(assertions):
        e = exps[i] if i < len(exps) else {}
        fixed.append(
            {
                "text": a,
                "passed": bool(e.get("passed", False)),
                "evidence": str(e.get("evidence", ""))[:400],
            }
        )
    return {"expectations": fixed}


def one_run(case: dict, cond: str, cwd: Path, out_root: Path, grader_cwd: Path) -> str:
    resp, ok = run_claude(case["prompt"], cwd)
    g = grade(resp, case["assertions"], grader_cwd)
    passed = sum(1 for e in g["expectations"] if e["passed"])
    total = len(g["expectations"])
    grading = {
        "summary": {
            "pass_rate": (passed / total) if total else 0.0,
            "passed": passed,
            "failed": total - passed,
            "total": total,
        },
        "expectations": g["expectations"],
        "response_ok": ok,
    }
    d = out_root / f"eval-{case['id']}" / cond / "run-1"
    d.mkdir(parents=True, exist_ok=True)
    (d / "grading.json").write_text(json.dumps(grading, indent=2))
    (d / "response.txt").write_text(resp)
    return f"eval-{case['id']:<2} {cond:<14} {passed}/{total}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    evals = json.loads((a.skill / "evals" / "evals.json").read_text())["evals"]
    without, with_ = project_dirs(a.skill)
    print(f"{len(evals)} cases x 2 conditions, {a.workers} workers", flush=True)

    jobs = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for c in evals:
            jobs.append(ex.submit(one_run, c, "without_skill", without, a.out, without))
            jobs.append(ex.submit(one_run, c, "with_skill", with_, a.out, without))
        for f in as_completed(jobs):
            print(" ", f.result(), flush=True)
    print("done ->", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
