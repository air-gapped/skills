#!/usr/bin/env python3
"""Add eval cases until each skill has enough of them to resolve a change.

The corpus sits at a median of 3 cases per skill. At n=3 one case flipping
moves pass rate by 33 points, so `delta_pass_rate` cannot distinguish "this
edit hurt" from "one case is flaky". Every downstream measurement -- the
leanness frontier, the delta_tokens gate, any actual deletion -- needs the
denominator to be large enough that a single case is not the verdict. Eight
is the floor this uses: one flip moves 12.5 points, which sits outside
ordinary run-to-run noise without demanding a corpus nobody will maintain.

New cases are generated to COMPLEMENT the existing ones, not repeat them:
the existing prompts are shown to the writer as territory already covered.
Each new case arrives with its own outcome assertions under the same rule the
backfill used -- assert what a correct answer achieves, never that it echoes
the skill's wording -- because a case without assertions falls back to prose
judging, which is the 46.4% problem this corpus was just repaired to escape.

Coverage is spread deliberately across four shapes, since a corpus of eight
near-identical "write me a config" tasks has a large n and still measures one
thing:

    build      produce a working artifact from a described situation
    diagnose   a symptom with a non-obvious root cause
    decide     choose between defensible options and justify it
    guard      a request that is wrong or dangerous as asked

Usage:
    grow-evals.py --root .claude/skills [--target 8] [--skill keda] [--dry-run]
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
You are extending the evaluation set for a Claude Code skill. Write {n} NEW \
test cases.

The skill's domain reference:
---
{skill}
---

Cases that ALREADY EXIST — do not duplicate these situations, these \
artifacts, or these root causes:
{existing}

Write {n} new cases that cover ground the existing ones miss. Spread them \
across these shapes, in this priority order, skipping a shape only if the \
domain genuinely cannot support it:

  build      produce a working artifact from a described situation
  diagnose   a symptom whose root cause is NOT the obvious first suspect
  decide     choose between defensible options and justify the choice
  guard      a request that is wrong or dangerous exactly as asked, where a
             correct answer pushes back rather than complying

Each case needs:

- `name`: short kebab-case identifier
- `prompt`: the task, written as a real operator would ask it. Concrete and \
specific — real names, real versions, real numbers, real constraints. Long \
enough to be unambiguous. Never mention the skill, this evaluation, or that \
a test is happening.
- `expected_output`: two or three sentences on what a correct answer achieves
- `assertions`: 4 to 6 checkable claims

ASSERTION RULE, the one that matters most. Assert the OUTCOME, never the \
wording.

  BAD   "mentions --enable-expert-parallel"
  BAD   "explains that the skill recommends X"
  GOOD  "the manifest enables expert parallelism for the 2-node MoE case"
  GOOD  "identifies the pre-existing HPA as the root cause, not the 404"
  GOOD  "does NOT recommend deleting the PVC before the backup completes"

A wording assertion fails whenever the reference is reworded and passes for \
an answer that parroted a phrase without doing the work. Assert what a \
correct answer ACHIEVES so any correct route passes. Each assertion must be \
answerable from the response alone by someone who has never read the skill. \
For every `guard` case, and anywhere a destructive or irreversible option \
exists, include a NEGATIVE assertion naming what the answer must NOT do.

Return ONLY a JSON array, no prose, no fences:
[{{"name": "...", "shape": "build|diagnose|decide|guard", "prompt": "...", \
"expected_output": "...", "assertions": ["...", "..."]}}]
"""


def load_floor_module():
    spec = importlib.util.spec_from_file_location(
        "knowledge_floor", HERE / "knowledge-floor.py"
    )
    if spec is None or spec.loader is None:
        sys.exit("grow-evals: cannot load knowledge-floor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def grow(kf, path: Path, target: int, model: str | None, timeout: int):
    doc = json.loads(path.read_text())
    cases = doc.get("evals") or []
    need = target - len(cases)
    if need <= 0:
        return doc, 0, 0.0, f"already {len(cases)}"

    skill_md = path.parents[1] / "SKILL.md"
    skill = skill_md.read_text() if skill_md.is_file() else ""
    if len(skill) > 24000:
        skill = skill[:24000] + "\n...[truncated]"

    existing = "\n".join(
        f"- {c.get('name', c['id'])}: {(c.get('prompt') or '')[:220]}" for c in cases
    )
    text, cost, ok = kf.run_claude(
        PROMPT.format(n=need, skill=skill, existing=existing),
        model=model,
        timeout=timeout,
    )
    if not ok:
        return doc, 0, cost, "call failed"
    arr = kf.parse_json_array(text)
    if not arr:
        return doc, 0, cost, "no JSON array"

    next_id = len(cases)
    added = 0
    for r in arr:
        prompt = str(r.get("prompt") or "").strip()
        asserts = [
            str(a).strip() for a in (r.get("assertions") or []) if str(a).strip()
        ]
        if not prompt or len(asserts) < 3:
            continue  # a case without real assertions is prose judging again
        cases.append({
            "id": next_id,
            "name": str(r.get("name") or f"case-{next_id}").strip(),
            "prompt": prompt,
            "expected_output": str(r.get("expected_output") or "").strip(),
            "files": [],
            "assertions": asserts,
            "shape": str(r.get("shape") or "").strip() or None,
            "source": f"grow-evals {date.today().isoformat()}",
        })  # fmt: skip
        next_id += 1
        added += 1

    if added:
        doc["evals"] = cases
        doc.setdefault("provenance", {})["grown"] = (
            f"{model or 'session-default'} via grow-evals.py "
            f"{date.today().isoformat()} (+{added} to {len(cases)})"
        )
    return doc, added, cost, f"+{added} -> {len(cases)}"


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--root", default=".claude/skills")
    ap.add_argument("--skill")
    ap.add_argument("--target", type=int, default=8)
    ap.add_argument("--model", default="opus")
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("--workers", type=int, default=4)
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
    total = {"added": 0, "cost": 0.0}

    def handle(f: Path):
        doc, n, cost, note = grow(kf, f, args.target, args.model, args.timeout)
        if n and not args.dry_run:
            f.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        with lock:
            total["added"] += n
            total["cost"] += cost
        print(f"  {doc.get('skill_name', f.stem):<44}{note:>18}  ${cost:.2f}",
              file=sys.stderr, flush=True)  # fmt: skip

    print(f"growing {len(files)} eval sets to {args.target} cases on {args.model}",
          file=sys.stderr)  # fmt: skip
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(handle, files))
    print(f"\n{total['added']} cases added · ${total['cost']:.2f}"
          f"{'  (dry run, nothing written)' if args.dry_run else ''}")  # fmt: skip


if __name__ == "__main__":
    main()
