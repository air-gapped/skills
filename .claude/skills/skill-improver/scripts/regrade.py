#!/usr/bin/env python3
"""Re-bucket stored floor-mode answers with a stricter grader. No probing.

The first fleet pass graded into three buckets, and the CONFLICTS count came
out inflated because two different things had nowhere else to go:

  · answers that AGREE but add or omit detail  ("GA in 1.24" vs "1.24+";
    a superset list of scalers; the right value without the version)
  · answers the model HEDGED  ("as of my knowledge that's...")

Both landed in CONFLICTS, which is the bucket the whole mode exists to
surface, so it was the one that could least afford noise. Reviewing 22 of 42
conflicts by hand, roughly a third were one of the two cases above.

This adds a fourth bucket and re-grades from the answers already on disk, so
the fix costs grading calls only -- the probes are not repeated:

  KNOWS      matches in substance
  PARTIAL    same direction, incomplete or less specific -- NOT a conflict
  UNKNOWN    does not know, hedges, refuses, or answers something else
  CONFLICTS  confident, specific, and contradicts the reference

Usage:
    regrade.py --dir .floor-results [--dir .floor-results-haiku] [--dry-run]

Results are rewritten in place with the new buckets; the original counts are
kept under `buckets_v1` so a re-grade can be audited rather than trusted.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import importlib.util
import threading
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

BUCKETS = ("KNOWS", "PARTIAL", "UNKNOWN", "CONFLICTS")

GRADE_PROMPT = """\
You are grading whether a model already knows facts that a reference document \
asserts.

CRITICAL: the reference is presumed CORRECT. It is maintained and re-verified \
continuously, often past the model's training cutoff. When the model's answer \
disagrees, that is the MODEL being stale -- never evidence the reference is \
wrong. Never grade the reference.

Choose exactly one bucket per item:

- KNOWS: matches the reference in substance. Wording, formatting, and extra \
correct detail do not matter. A superset that includes everything the \
reference says is KNOWS, not CONFLICTS.
- PARTIAL: points the same direction but is incomplete or less specific -- \
right value with the version omitted, some list items missing, the right idea \
stated vaguely. PARTIAL is NOT a conflict.
- UNKNOWN: says it does not know, refuses, answers something unrelated, or \
HEDGES about its own knowledge ("as of my knowledge", "I believe", "as of my \
training data"). A hedged answer is UNKNOWN even when the content looks close.
- CONFLICTS: confident, specific, and genuinely contradicts the reference -- a \
different version number, a different flag name, an opposite yes/no. Reserve \
this for answers that would lead someone to do the WRONG thing.

When torn between PARTIAL and CONFLICTS, choose PARTIAL. When torn between \
UNKNOWN and CONFLICTS, choose UNKNOWN. CONFLICTS must be earned.

Return ONLY a JSON array, no prose, no fences, one object per item, in order:
[{{"id": <id>, "bucket": "KNOWS|PARTIAL|UNKNOWN|CONFLICTS", "why": "<under 15 \
words>"}}]

Items:
{items}
"""


def load_floor_module():
    """knowledge-floor.py has a dash in its name, so import it by path."""
    spec = importlib.util.spec_from_file_location(
        "knowledge_floor", HERE / "knowledge-floor.py"
    )
    if spec is None or spec.loader is None:
        sys.exit("regrade: cannot load knowledge-floor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def regrade_cell(kf, claims, answers, grader_model, timeout, chunk=10):
    by_id = {c["id"]: c for c in claims}
    ids = [int(k) for k in answers]
    out: dict[int, dict] = {}
    cost = 0.0
    for k in range(0, len(ids), chunk):
        batch = ids[k : k + chunk]
        items = "\n\n".join(
            f"id: {cid}\nquestion: {by_id[cid]['question']}\n"
            f"reference answer: {by_id[cid]['skill_answer']}\n"
            f"model answer: {answers.get(str(cid), answers.get(cid, ''))}"
            for cid in batch
            if cid in by_id
        )
        if not items:
            continue
        text, c, ok = kf.run_claude(
            GRADE_PROMPT.format(items=items), model=grader_model, timeout=timeout
        )
        cost += c
        arr = kf.parse_json_array(text) if ok else None
        if not arr:
            for cid in batch:
                out[cid] = {"bucket": "UNGRADED", "why": "grader failed"}
            continue
        for r in arr:
            cid = r.get("id")
            if cid in by_id and r.get("bucket") in BUCKETS:
                out[cid] = {"bucket": r["bucket"], "why": str(r.get("why", ""))[:60]}
        for cid in batch:
            out.setdefault(cid, {"bucket": "UNGRADED", "why": "missing from grader"})
    return out, cost


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--dir", action="append", required=True)
    ap.add_argument("--grader-model", default="sonnet")
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--workers",
        type=int,
        default=6,
        help="files re-graded concurrently. Grading is one short call per 10 "
        "claims, so this is the whole wall-clock story: serial, 136 files is "
        "an hour; at 6, minutes.",
    )
    args = ap.parse_args()

    kf = load_floor_module()
    total_cost = 0.0
    moved = {b: 0 for b in (*BUCKETS, "UNGRADED")}
    files = [f for d in args.dir for f in sorted(Path(d).glob("*.json"))
             if not f.name.startswith("_")]  # fmt: skip
    print(f"re-grading {len(files)} result files", file=sys.stderr)

    lock = threading.Lock()

    def handle(f: Path):
        nonlocal total_cost
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            return
        if not d.get("cells"):
            return
        claims = d["claims"]
        changed = False
        file_cost = 0.0
        for cell in d["cells"].values():
            answers = cell.get("answers") or {}
            if not answers:
                continue
            graded, cost = regrade_cell(
                kf, claims, answers, args.grader_model, args.timeout
            )
            file_cost += cost
            cell.setdefault("buckets_v1", cell["buckets"])
            cell["buckets"] = {
                b: [c for c, g in graded.items() if g["bucket"] == b]
                for b in (*BUCKETS, "UNGRADED")
            }
            cell["detail"] = {str(k): v for k, v in graded.items()}
            with lock:
                for b in cell["buckets"]:
                    moved[b] += len(cell["buckets"][b])
            changed = True
        if changed and not args.dry_run:
            # This file's own grading cost only. The serial version added the
            # running accumulator, which inflated every file after the first.
            d["total_cost_usd"] = round((d.get("total_cost_usd") or 0) + file_cost, 4)
            f.write_text(json.dumps(d, indent=2) + "\n")
        with lock:
            total_cost += file_cost
        print(f"  {f.stem}", file=sys.stderr, flush=True)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(handle, files))

    print(f"\nre-graded totals: {moved}")
    print(
        f"grading cost ${total_cost:.2f}"
        f"{'  (dry run, nothing written)' if args.dry_run else ''}"
    )


if __name__ == "__main__":
    main()
