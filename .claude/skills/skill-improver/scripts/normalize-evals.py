#!/usr/bin/env python3
"""Normalize every skill's evals.json onto one schema, and stamp provenance.

An audit on 2026-08-19 found 26 eval files carrying 11 distinct shapes: `name`
vs `eval_name` vs no case name at all, `assertions` vs `expectations` vs
nothing, a stray top-level `notes`, one file with a `method_note` and 25
without, and no file recording what wrote it or when. 15 of the 26 were
created in the Opus 4.7 era, four model generations back.

That matters beyond tidiness. An eval set written for an older model DEFENDS
the older skill: a case that expects a flag to be mentioned because Opus 4.7
needed the reminder fails when the reminder is deleted, even though the
current model does it unprompted. The oracle is biased in exactly the
direction that hides the leanness finding it is meant to test. Uniform shape
plus recorded provenance is the precondition for ever trusting it.

Canonical schema (version 2):

    {
      "skill_name": str,
      "schema_version": 2,
      "provenance": {"created": date, "normalized": date,
                     "assertions_source": str|null, "harness": str},
      "method_note": str,                       # optional
      "evals": [{"id": int, "name": str, "prompt": str,
                 "expected_output": str, "files": [], "assertions": [str]}]
    }

This script only moves and renames. It never invents an assertion -- cases
that lack them keep an empty list and are reported, because writing them is a
judgement task that belongs to a separate, reviewable pass.

Usage:
    normalize-evals.py --root .claude/skills [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

SCHEMA_VERSION = 2
HARNESS = "skill-creator eval loop (aggregate_benchmark)"

# Old field name -> canonical. Both renames are lossless.
CASE_ALIASES = {"eval_name": "name", "expectations": "assertions"}
CASE_ORDER = ["id", "name", "prompt", "expected_output", "files", "assertions"]


def created_date(path: Path) -> str:
    """First commit that added the file, or today for an untracked one."""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%ad", "--date=short",
             "--", path.name],
            capture_output=True, text=True, cwd=path.parent,
        ).stdout.strip()  # fmt: skip
    except OSError:
        return ""
    return out.split("\n")[-1] if out else ""


def slug(text: str, fallback: str) -> str:
    """A case name derived from its prompt: enough to identify it in a report."""
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    stop = {"the", "a", "an", "i", "my", "we", "our", "how", "do", "is", "to",
            "for", "of", "in", "on", "and", "with", "you", "me", "it", "that"}  # fmt: skip
    keep = [w for w in words if w not in stop][:5]
    return "-".join(keep) or fallback


def normalize(path: Path) -> tuple[dict, dict]:
    loaded = json.loads(path.read_text())
    raw: dict = {"evals": loaded} if isinstance(loaded, list) else loaded
    cases = raw.get("evals") or []

    report = {"renamed": 0, "named": 0, "no_assertions": 0, "no_expected": 0}
    out_cases = []
    for i, c in enumerate(cases):
        c = dict(c)
        for old, new in CASE_ALIASES.items():
            if old in c:
                c[new] = c.pop(old)
                report["renamed"] += 1
        if not c.get("name"):
            c["name"] = slug(c.get("prompt", ""), f"case-{i}")
            report["named"] += 1
        c.setdefault("expected_output", "")
        if not c["expected_output"]:
            report["no_expected"] += 1
        c.setdefault("files", [])
        c.setdefault("assertions", [])
        if not c["assertions"]:
            report["no_assertions"] += 1
        c["id"] = i  # renumber densely; ids were not always contiguous
        out_cases.append({k: c[k] for k in CASE_ORDER if k in c} |
                         {k: v for k, v in c.items() if k not in CASE_ORDER})  # fmt: skip

    prov = raw.get("provenance") or {}
    doc = {
        "skill_name": raw.get("skill_name") or path.parents[1].name,
        "schema_version": SCHEMA_VERSION,
        "provenance": {
            "created": prov.get("created") or created_date(path),
            "normalized": date.today().isoformat(),
            "assertions_source": prov.get("assertions_source"),
            "harness": prov.get("harness") or HARNESS,
        },
    }
    # A stray top-level `notes` is the same thing `method_note` records.
    note = raw.get("method_note") or raw.get("notes")
    if note:
        doc["method_note"] = note
    doc["evals"] = out_cases
    return doc, report


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--root", default=".claude/skills")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(Path(args.root).glob("*/evals/evals.json"))
    print(f"{'skill':<44}{'cases':>6}{'renamed':>8}{'named':>7}{'no-assert':>10}")
    print("-" * 75)
    tot = {"cases": 0, "renamed": 0, "named": 0, "no_assertions": 0, "no_expected": 0}
    gaps = []
    for f in files:
        doc, rep = normalize(f)
        n = len(doc["evals"])
        tot["cases"] += n
        for k in ("renamed", "named", "no_assertions", "no_expected"):
            tot[k] += rep[k]
        if rep["no_assertions"]:
            gaps.append((doc["skill_name"], rep["no_assertions"], n))
        if not args.dry_run:
            f.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        print(f"{doc['skill_name'][:43]:<44}{n:>6}{rep['renamed']:>8}"
              f"{rep['named']:>7}{rep['no_assertions']:>10}")  # fmt: skip

    print("-" * 75)
    print(f"{len(files)} files · {tot['cases']} cases · {tot['renamed']} fields renamed "
          f"· {tot['named']} cases named · {tot['no_expected']} without expected_output")  # fmt: skip
    print(f"\ncases still lacking assertions: {tot['no_assertions']}/{tot['cases']}")
    print("These are graded by an LLM judge against a prose paragraph — the")
    print("subjective text comparison SkillLens measured at 46.4%. Backfilling")
    print("them as OUTCOMES (not text recall) is the next pass.")
    if gaps:
        worst = sorted(gaps, key=lambda g: -g[1])[:8]
        print("\nlargest gaps: " + ", ".join(f"{s} {a}/{n}" for s, a, n in worst))
    if args.dry_run:
        print("\n(dry run — nothing written)")


if __name__ == "__main__":
    main()
