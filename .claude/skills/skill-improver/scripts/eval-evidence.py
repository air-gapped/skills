#!/usr/bin/env python3
"""Extract ONLY the eval evidence a blind scorer may see, and nothing else.

A skill's `evals/` directory is not neutral ground. Alongside the eval cases it
accumulates the record of previous improvement passes: `benchmark.json` carries
`regression_verdict`, `prior_baseline`, and a `why_run` narrative of what
recently changed; dated snapshots carry the same; `case-validation.*.json`
records which changes were kept and discarded and why; `scorer-sweep.*.json`
records prior blind TOTALS, sometimes for other skills, which anchors a scorer
that has been told "most decent skills score 50-70".

That is the same leak `improvement-backlog.md` was excluded for — a scorer that
reads it is no longer blind. But `evals/` cannot simply be excluded, because the
Negative-Transfer Gate needs one number from it: `delta_pass_rate` decides
whether Dim 10 is capped at 8, and reading it is the whole point of the gate.

So the directory becomes off-limits and this script becomes the only channel.
It prints the case count, the delta, and the Dim 10 cap that implies — no
verdict text, no prior score, no assertion, no narrative.

Same principle as `frontmatter-lengths.py`: replace a judgement call the scorer
would otherwise make by reading, with a measurement it runs.

## The delta is DERIVED from the arms, never read

The canonical on-disk format is whatever the official `aggregate_benchmark.py`
writes (`run_summary.<arm>.pass_rate.{mean,stddev,min,max}` plus `runs[]`) —
the rubric mandates that tool, so its output is the standard and this repo's
two hand-rolled `summary.delta_pass_rate` files are the deviants.

But its stored `run_summary.delta.pass_rate` must not be trusted, for three
reasons visible in its source:

1. It is written as `f"{delta:+.2f}"` — a **string, rounded to 2 decimals**. A
   real +0.1875 is stored as "+0.19". That is a rendering, not a value.
2. It is `configs[0] - configs[1]` by **dict insertion order**. If the arms are
   recorded in the other order the sign silently flips.
3. Both sides use `.get(..., 0)`, so a **missing arm becomes 0** — an absent
   baseline yields a maximally positive delta. That is the same coerce-missing-
   to-zero bug the trigger and floor probes were fixed for, fail-open.

Deriving `with_skill − without_skill` from the arms fixes all three at once:
full precision, order-independent, and an absent arm produces no delta at all
rather than a flattering one. Every shape in the fleet carries the arms, so
this is also the one route that works across all of them.

Any stored delta is still read, but only as a cross-check: a stored value that
does not match a derived one is reported as a MISMATCH, meaning the file was
hand-edited or written by a different aggregator than its own arms.

Usage:
    eval-evidence.py <TARGET DIR>
    eval-evidence.py <TARGET DIR> --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Keys whose VALUES are measurements. Anything not matching stays unread.
DELTA_PREFIX = "delta_"


def as_number(value) -> float | None:
    """Deltas are stored as numbers in some benchmarks and as strings ('+0.19')
    in others. Both are measurements; only the encoding differs."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().lstrip("+"))
        except ValueError:
            return None
    return None


def find_deltas(node, path: str = "") -> list[tuple[str, float]]:
    """Collect delta measurements across the three benchmark shapes in use:
    a flat `delta_pass_rate`, a `delta` object whose children are the deltas,
    and either one encoded as a string."""
    found: list[tuple[str, float]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path}.{key}" if path else key
            if key.startswith(DELTA_PREFIX):
                number = as_number(value)
                if number is not None:
                    found.append((here, number))
                    continue
            if key == "delta" and isinstance(value, dict):
                # `{"delta": {"pass_rate": "+0.19", ...}}` — rename the children
                # to the canonical form so the cap logic sees one vocabulary.
                for sub, subvalue in value.items():
                    number = as_number(subvalue)
                    if number is not None:
                        found.append((f"{here}.{sub}", number))
                continue
            found.extend(find_deltas(value, here))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found.extend(find_deltas(value, f"{path}[{i}]"))
    return found


def rate_of(arm) -> float | None:
    """A configuration's pass rate, across the shapes in use: a bare float, or
    a stats object with a mean."""
    if isinstance(arm, dict):
        value = arm.get("pass_rate")
        if isinstance(value, dict):
            return as_number(value.get("mean"))
        return as_number(value)
    return None


def find_arms(node, path: str = "") -> list[tuple[str, float | None, float | None]]:
    """Locate every with_skill/without_skill pair and return their pass rates.

    The arms are the measurement; the stored delta is a rendering of it. Both
    the official aggregator and the hand-rolled files carry the arms, so
    deriving from them is the one route that works everywhere AND avoids three
    defects in the stored value (see module docstring).
    """
    found: list[tuple[str, float | None, float | None]] = []
    if isinstance(node, dict):
        if "with_skill" in node and "without_skill" in node:
            found.append(
                (
                    path or "<root>",
                    rate_of(node["with_skill"]),
                    rate_of(node["without_skill"]),
                )
            )
        for key, value in node.items():
            found.extend(find_arms(value, f"{path}.{key}" if path else key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found.extend(find_arms(value, f"{path}[{i}]"))
    return found


def count_cases(evals_dir: Path) -> tuple[int | None, str]:
    """Case count only — never the prompts, expected outputs, or assertions."""
    for name in ("evals.json", "evals.yaml", "evals.yml"):
        path = evals_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None, f"{name} (unparseable)"
        if isinstance(data, dict) and isinstance(data.get("evals"), list):
            return len(data["evals"]), name
        if isinstance(data, list):
            return len(data), f"{name} (legacy flat)"
        return None, f"{name} (unrecognized shape)"
    return None, ""


def cap_for(deltas: list[tuple[str, float]]) -> tuple[int, str]:
    """Map measured evidence onto the Negative-Transfer Gate's Dim 10 cap."""
    rates = [v for _, v in deltas]
    if not rates:
        return 8, "no delta_pass_rate measured — unmeasured cap applies"
    # Several benchmarks may be present (per-model, per-date). The gate asks
    # whether the skill loses to no-skill, so the worst measurement governs.
    worst = min(rates)
    if worst < 0:
        return 2, f"delta_pass_rate {worst:+.3f} is negative — skill loses to no-skill"
    if abs(worst) < 0.01:
        return (
            6,
            f"delta_pass_rate {worst:+.3f} is ~0 — check delta_tokens for the 3-vs-6 split",
        )
    return (
        10,
        f"delta_pass_rate {worst:+.3f} is positive — no cap, score on the evidence",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Blind-safe eval evidence extract.")
    ap.add_argument("target", type=Path, help="skill directory")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    evals_dir = args.target / "evals"
    if not evals_dir.is_dir():
        out = {
            "has_evals": False,
            "cases": None,
            "deltas": [],
            "dim10_cap": 8,
            "cap_reason": "no evals/ directory — unmeasured cap applies",
        }
    else:
        cases, source = count_cases(evals_dir)
        deltas: list[tuple[str, float]] = []
        stored: list[tuple[str, float]] = []
        incomplete: list[str] = []
        for path in sorted(evals_dir.glob("*.json")):
            if not path.name.startswith("benchmark"):
                continue
            try:
                data = json.loads(path.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            for where, with_rate, without_rate in find_arms(data):
                if with_rate is None or without_rate is None:
                    # One arm unmeasured. The official aggregator defaults the
                    # missing side to 0, which turns an absent baseline into a
                    # maximally positive delta. Refuse instead.
                    incomplete.append(f"{path.name}:{where}")
                    continue
                deltas.append((f"{path.name}:{where}", with_rate - without_rate))
            for key, value in find_deltas(data):
                stored.append((f"{path.name}:{key}", value))
        cap, reason = cap_for(deltas)
        out = {
            "has_evals": True,
            "cases": cases,
            "case_source": source,
            "deltas": [{"path": k, "value": v} for k, v in deltas],
            "stored_deltas": [{"path": k, "value": v} for k, v in stored],
            "incomplete_arms": incomplete,
            "dim10_cap": cap,
            "cap_reason": reason,
        }

    if args.as_json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"eval evidence for {args.target}")
    if not out["has_evals"]:
        print("  evals/: absent")
    else:
        cases = out["cases"]
        print(
            f"  cases: {cases if cases is not None else 'UNKNOWN'}"
            f"{' (' + out['case_source'] + ')' if out['case_source'] else ''}"
        )
        if out["deltas"]:
            print("  delta_pass_rate (derived from the arms):")
            for d in out["deltas"]:
                print(f"    {d['value']:+.4f}  {d['path']}")
        else:
            print(
                "  delta_pass_rate: none derivable (no with_skill/without_skill pair)"
            )
        for path in out.get("incomplete_arms", []):
            print(f"    INCOMPLETE — one arm unmeasured, no delta: {path}")
        # Cross-check. A stored value that disagrees means the file was edited
        # by hand or written by a different aggregator than its arms.
        for s in out.get("stored_deltas", []):
            if not s["path"].endswith(("delta_pass_rate", "delta.pass_rate")):
                continue
            near = [d for d in out["deltas"] if abs(d["value"] - s["value"]) <= 0.005]
            if not near:
                print(
                    f"    MISMATCH — stored {s['value']:+.4f} at {s['path']} "
                    "does not match any derived delta; trust the arms"
                )
    print(f"  Dim 10 cap: {out['dim10_cap']}  — {out['cap_reason']}")
    print("\nThis is the ONLY evidence from evals/ a blind scorer may use. Do not")
    print("open the directory: it also holds prior scores, keep/discard records,")
    print("and regression verdicts, which un-blind the pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
