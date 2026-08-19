#!/usr/bin/env python3
"""Write outcome assertions for eval cases that have none.

62 of 90 cases are graded by an LLM judge against a prose `expected_output`
paragraph -- the subjective text comparison SkillLens (arXiv:2605.23899)
measured at 46.4%, worse than chance. Discrete assertions turn that into a
checklist a grader can actually check.

The distinction that makes or breaks this pass:

    TEXT RECALL   "mentions --enable-expert-parallel"
    OUTCOME       "the manifest sets expert parallelism correctly for a
                   2-node MoE deployment"

The first tests whether the answer echoes the skill's wording, so it fails
the moment the skill is reworded and PASSES for a model that parroted the
phrase without doing the work. It makes leanness unmeasurable by construction:
delete the sentence, fail the eval, conclude the sentence was load-bearing.
The second tests the result and admits any correct path to it, including a
leaner skill or a model that needs no prompting at all.

So every assertion here must be answerable from the response alone, by
someone who has never read the skill.

Usage:
    backfill-assertions.py --root .claude/skills [--skill keda] [--dry-run]
    backfill-assertions.py --model opus --workers 4

Writes assertions into each case and records the model in
`provenance.assertions_source`. Cases that already have assertions are left
alone unless --redo is passed.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import importlib.util
import json
import sys
import threading
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent

PROMPT = """\
You are writing grading assertions for an evaluation of a Claude Code skill.

Each assertion is one checkable claim about a response. A grader reads only \
the response and the assertion and answers yes or no.

THE RULE THAT MATTERS MOST. Assert the OUTCOME, never the wording.

  BAD   "mentions --enable-expert-parallel"
  BAD   "explains that the skill recommends X"
  BAD   "uses the phrase 'blast radius'"
  GOOD  "the manifest enables expert parallelism for the 2-node MoE case"
  GOOD  "identifies the pre-existing HPA as the root cause, not the 404"
  GOOD  "does NOT recommend deleting the PVC before the backup completes"

A wording assertion fails whenever the reference document is reworded, and \
passes for an answer that parroted a phrase without doing the work. Assert \
what a correct answer ACHIEVES, so that any correct route to it passes.

Rules:
1. 4 to 6 assertions per case.
2. Each must be answerable from the response alone by someone who has never \
read the skill.
3. Each must be independent -- no assertion may presuppose another.
4. Prefer specifics that can be wrong: values, flags with their settings, \
ordering constraints, named root causes, explicit thresholds.
5. Where the task has a destructive, irreversible, or plainly wrong option, \
include at least one NEGATIVE assertion naming what the answer must NOT do.
6. Do not assert on tone, length, formatting, or structure.

Domain reference (for grounding facts only -- never assert that the response \
resembles this text):
---
{skill}
---

Cases:
{cases}

Return ONLY a JSON array, no prose, no fences:
[{{"id": <id>, "assertions": ["...", "..."]}}]
"""


def load_floor_module():
    spec = importlib.util.spec_from_file_location(
        "knowledge_floor", HERE / "knowledge-floor.py"
    )
    if spec is None or spec.loader is None:
        sys.exit("backfill: cannot load knowledge-floor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def backfill(kf, path: Path, model: str | None, timeout: int, redo: bool):
    doc = json.loads(path.read_text())
    cases = doc.get("evals") or []
    todo = [c for c in cases if redo or not c.get("assertions")]
    if not todo:
        return doc, 0, 0.0, "already complete"

    skill_md = path.parents[1] / "SKILL.md"
    skill = skill_md.read_text() if skill_md.is_file() else ""
    # Trim: grounding needs the substance, not every reference table.
    if len(skill) > 24000:
        skill = skill[:24000] + "\n...[truncated]"

    blob = "\n\n".join(
        f"id: {c['id']}\nname: {c.get('name', '')}\ntask given to the model:\n"
        f"{c['prompt']}\n\nwhat a correct answer should achieve:\n"
        f"{c.get('expected_output', '(not recorded)')}"
        for c in todo
    )
    text, cost, ok = kf.run_claude(
        PROMPT.format(skill=skill, cases=blob), model=model, timeout=timeout
    )
    if not ok:
        return doc, 0, cost, "call failed"
    arr = kf.parse_json_array(text)
    if not arr:
        return doc, 0, cost, "no JSON array returned"

    by_id = {c["id"]: c for c in cases}
    n = 0
    for r in arr:
        cid = r.get("id")
        a = [str(x).strip() for x in (r.get("assertions") or []) if str(x).strip()]
        if cid in by_id and a:
            by_id[cid]["assertions"] = a
            n += 1
    if n:
        doc.setdefault("provenance", {})["assertions_source"] = (
            f"{model or 'session-default'} via backfill-assertions.py "
            f"{date.today().isoformat()}"
        )
    return doc, n, cost, f"{n}/{len(todo)} cases"


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--root", default=".claude/skills")
    ap.add_argument("--skill", help="one skill only")
    ap.add_argument("--model", default="opus")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    kf = load_floor_module()
    root = Path(args.root)
    files = (
        [root / args.skill / "evals" / "evals.json"]
        if args.skill
        else sorted(root.glob("*/evals/evals.json"))
    )
    files = [f for f in files if f.is_file()]

    lock = threading.Lock()
    total = {"cases": 0, "cost": 0.0}

    def handle(f: Path):
        doc, n, cost, note = backfill(kf, f, args.model, args.timeout, args.redo)
        if n and not args.dry_run:
            f.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        with lock:
            total["cases"] += n
            total["cost"] += cost
        print(
            f"  {doc.get('skill_name', f.stem):<44}{note:>22}  ${cost:.2f}",
            file=sys.stderr,
            flush=True,
        )

    print(f"backfilling assertions across {len(files)} files on {args.model}",
          file=sys.stderr)  # fmt: skip
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(handle, files))

    print(f"\n{total['cases']} cases given assertions · ${total['cost']:.2f}"
          f"{'  (dry run, nothing written)' if args.dry_run else ''}")  # fmt: skip


if __name__ == "__main__":
    main()
