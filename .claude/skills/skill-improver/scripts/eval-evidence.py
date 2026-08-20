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
It prints the case count, every `delta_*` measurement it can find with the JSON
path it came from, and the Dim 10 cap those imply. It prints no verdict text, no
prior score, no assertion, and no narrative.

Same principle as `frontmatter-lengths.py`: replace a judgement call the scorer
would otherwise make by reading, with a measurement it runs.

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
    rates = [v for k, v in deltas if k.endswith(("delta_pass_rate", "delta.pass_rate"))]
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
        for path in sorted(evals_dir.glob("*.json")):
            if not path.name.startswith("benchmark"):
                continue
            try:
                data = json.loads(path.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            for key, value in find_deltas(data):
                deltas.append((f"{path.name}:{key}", value))
        cap, reason = cap_for(deltas)
        out = {
            "has_evals": True,
            "cases": cases,
            "case_source": source,
            "deltas": [{"path": k, "value": v} for k, v in deltas],
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
            print("  measurements:")
            for d in out["deltas"]:
                print(f"    {d['value']:+.4f}  {d['path']}")
        else:
            print("  measurements: none (no benchmark*.json with a delta_* value)")
    print(f"  Dim 10 cap: {out['dim10_cap']}  — {out['cap_reason']}")
    print("\nThis is the ONLY evidence from evals/ a blind scorer may use. Do not")
    print("open the directory: it also holds prior scores, keep/discard records,")
    print("and regression verdicts, which un-blind the pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
