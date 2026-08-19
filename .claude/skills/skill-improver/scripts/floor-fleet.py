#!/usr/bin/env python3
"""Run floor mode across a fleet of skills, resumably, and rank the results.

A fleet pass is hours of `claude -p` calls, so nothing here holds state in
memory: each skill's result lands in its own JSON file the moment it finishes,
and a re-run skips whatever is already on disk. Kill it and restart it freely.

Usage:
    floor-fleet.py --root .claude/skills --models sonnet,opus
    floor-fleet.py --report            # re-print the leaderboard, no probing
    floor-fleet.py --skills keda,helm  # a subset

Output per skill: <out>/<skill>.json, plus a leaderboard on stdout ranked by
the share of claims the strongest probed model already knows -- the skills
most likely to be carrying content the model no longer needs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLOOR = HERE / "knowledge-floor.py"

# Weakest to strongest. Columns sort by this so "strongest model" is the last
# one, whichever subset of tiers a pass happened to probe.
TIER_ORDER = ["haiku", "sonnet", "opus", "fable", "mythos"]


def tier_rank(label: str) -> int:
    base = label.split("/")[0]
    return TIER_ORDER.index(base) if base in TIER_ORDER else len(TIER_ORDER)


def find_skills(root: Path) -> list[Path]:
    return sorted(p.parent for p in root.rglob("SKILL.md"))


def run_one(skill: Path, models: str, max_claims: int, timeout: int, workers: int):
    cmd = [
        sys.executable, str(FLOOR),
        "--skill", str(skill),
        "--models", models,
        "--max-claims", str(max_claims),
        "--timeout", str(timeout),
        "--workers", str(workers),
        "--json",
    ]  # fmt: skip
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return {"skill": skill.name, "error": (p.stderr or "")[-400:]}
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"skill": skill.name, "error": "unparseable output"}


def summarize(d: dict) -> dict | None:
    if d.get("error") or not d.get("cells"):
        return None
    n = len(d.get("claims") or [])
    if not n:
        return None
    cells = {k: d["cells"][k] for k in sorted(d["cells"], key=tier_rank)}
    strongest = list(cells)[-1]
    out = {
        "skill": d["skill"],
        "claims": n,
        "strongest": strongest,
        "cost": round(d.get("total_cost_usd", 0), 3),
        "cells": {},
    }
    for label, c in cells.items():
        b = c["buckets"]
        out["cells"][label] = {
            "knows": len(b["KNOWS"]),
            "unknown": len(b["UNKNOWN"]),
            "conflicts": len(b["CONFLICTS"]),
        }
    s = out["cells"][strongest]
    out["known_share"] = s["knows"] / n
    out["conflicts"] = s["conflicts"]
    return out


def leaderboard(out_dir: Path, merge_dirs: list[Path] | None = None):
    """Rank skills. Extra dirs are additional passes over the SAME claim sets
    (e.g. a later cheaper-model pass); their cells merge into one row."""
    rows, failed, total_cost = [], [], 0.0
    for f in sorted(out_dir.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        total_cost += d.get("total_cost_usd", 0) or 0
        for extra in merge_dirs or []:
            g = extra / f.name
            if not g.is_file():
                continue
            try:
                e = json.loads(g.read_text())
            except json.JSONDecodeError:
                continue
            if len(e.get("claims") or []) != len(d.get("claims") or []):
                continue  # different denominator, not comparable
            d.setdefault("cells", {}).update(e.get("cells") or {})
            total_cost += e.get("total_cost_usd", 0) or 0
        s = summarize(d)
        (rows if s else failed).append(s or d.get("skill", f.stem))
    if not rows:
        print("no completed skills yet", file=sys.stderr)
        return
    rows.sort(key=lambda r: -r["known_share"])

    labels = sorted({lab for r in rows for lab in r["cells"]}, key=tier_rank)
    head = "".join(f"{lab[:9]:>11}" for lab in labels)
    print(f"\n{'skill':<44}{'claims':>7}{head}{'known':>8}{'conf':>6}")
    print("-" * (44 + 7 + 11 * len(labels) + 14))
    for r in rows:
        cells = "".join(
            f"{r['cells'].get(lab, {}).get('knows', 0):>6}/{r['claims']:<4}"
            for lab in labels
        )
        print(
            f"{r['skill'][:43]:<44}{r['claims']:>7}{cells}"
            f"{r['known_share']:>7.0%}{r['conflicts']:>6}"
        )

    n = len(rows)
    avg = sum(r["known_share"] for r in rows) / n
    conf = sum(r["conflicts"] for r in rows)
    print("-" * (44 + 7 + 11 * len(labels) + 14))
    print(
        f"{n} skills · mean known {avg:.0%} on the strongest model"
        f" · {conf} total conflicts · ${total_cost:,.2f}"
    )
    if failed:
        print(f"\nno result ({len(failed)}): {', '.join(str(x) for x in failed[:12])}")
    print(
        "\nHigh 'known' = the model already carries most of what this skill asserts"
        "\n-> deletion CANDIDATES, to confirm with an eval delta, never to cut blind."
        "\n'conf' = claims where the model is confidently WRONG. That content is the"
        "\nskill earning its keep; make it louder rather than leaner.\n"
    )


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--root", default=".claude/skills")
    ap.add_argument("--out", default=".floor-results")
    ap.add_argument("--models", default="sonnet,opus")
    ap.add_argument("--max-claims", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--skills", default="", help="comma list, else the whole root")
    ap.add_argument("--report", action="store_true", help="print leaderboard only")
    ap.add_argument(
        "--merge", default="", help="comma list of extra result dirs to fold in"
    )
    ap.add_argument("--redo", action="store_true", help="ignore existing results")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    merge = [Path(m.strip()) for m in args.merge.split(",") if m.strip()]
    if args.report:
        leaderboard(out_dir, merge)
        return

    if args.skills:
        names = [s.strip() for s in args.skills.split(",") if s.strip()]
        skills = [Path(args.root) / n for n in names]
    else:
        skills = find_skills(Path(args.root))

    todo = [
        s for s in skills if args.redo or not (out_dir / f"{s.name}.json").is_file()
    ]
    print(
        f"{len(skills)} skills, {len(skills) - len(todo)} already done, "
        f"{len(todo)} to probe on [{args.models}]",
        file=sys.stderr,
    )

    t0 = time.time()
    for i, skill in enumerate(todo, 1):
        started = time.time()
        d = run_one(skill, args.models, args.max_claims, args.timeout, args.workers)
        (out_dir / f"{skill.name}.json").write_text(json.dumps(d, indent=2) + "\n")
        s = summarize(d)
        el = time.time() - t0
        eta = el / i * (len(todo) - i)
        if s:
            cells = " ".join(
                f"{lab}={c['knows']}/{s['claims']}" for lab, c in s["cells"].items()
            )
            print(
                f"[{i}/{len(todo)}] {skill.name:<40} {cells}"
                f"  conf={s['conflicts']}  ${s['cost']:.2f}"
                f"  {time.time() - started:.0f}s  eta {eta / 60:.0f}m",
                file=sys.stderr,
                flush=True,
            )
        else:
            print(
                f"[{i}/{len(todo)}] {skill.name:<40} FAILED: "
                f"{str(d.get('error'))[:90]}  eta {eta / 60:.0f}m",
                file=sys.stderr,
                flush=True,
            )

    leaderboard(out_dir, merge)


if __name__ == "__main__":
    main()
