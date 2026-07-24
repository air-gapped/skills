#!/usr/bin/env python3
"""Boris scaffolding probe with a criterion discriminator.

The naive detector (`rg -c '^\\s*\\d+\\. ' SKILL.md >= 8`) cannot tell
procedural scaffolding from encoded acceptance criteria. It counts both, so a
skill that correctly writes down invariants a model cannot infer gets the same
Dim 6 cap as one that spells out steps plan mode would discover.

This probe splits them. A numbered item is a CRITERION when it carries at least
one of:

  1. a prohibition / invariant  ("do NOT", "never", "must", "non-optional")
  2. a named failure or causal clause  ("because", "otherwise", "silently",
     "hides", "regress")
  3. an explicit threshold or quantity  (">= 8", "+2 or more", "5 iterations")

Those three are the text properties SkillLens (arXiv:2605.23899) measured as
predictive of downstream utility -- Failure Mechanism Encoding, High-Risk Action
Blacklist, and Actionable Specificity. Everything else is SCAFFOLD, and only
SCAFFOLD counts toward the cap.

Usage:
    scaffold-probe.py [SKILL.md] [--refs] [--threshold N] [--verbose]

Exit status is 1 when the scaffold count meets the threshold (cap triggered),
0 otherwise -- so it composes into a batch sweep.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ITEM_RE = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^#{1,6}\s")

# Conservative on purpose: a marker that fires too easily reclassifies
# scaffolding as criteria and silently neuters the cap.
MARKERS: list[tuple[str, str]] = [
    (
        "prohibition",
        r"\bdo not\b|\bdon't\b|\bnever\b|\bmust\b|\bnon-optional\b|"
        r"\brequired\b|\bonly if\b|\bonly when\b",
    ),
    (
        "failure",
        r"\bbecause\b|\botherwise\b|\bso cause\b|\bso that\b|\bsilently\b|"
        r"\bhides?\b|\bbreaks?\b|\bdestroys?\b|\bregress\w*\b|\bstale\b|"
        r"\bwrong\b|\binflated\b|\bbias\w*\b",
    ),
    (
        "threshold",
        # Comparison operators must sit next to a digit: a bare `<` matches
        # every `<skill-name>` placeholder in the file.
        r"[≥≤]\s*\d|[<>]\s*\d|\d\s*[<>]|\+\d|\bat least \d|"
        r"\bcap(?:ped)? at \d|"
        r"\b\d+\s*(?:\+|or more|lines|items|iterations|chars|characters|"
        r"runs|%|seconds|minutes)\b",
    ),
]

# A numbered list is often a decision table or a differential-diagnosis list
# rather than a sequence of steps -- "condition -> action" carries judgment the
# model cannot infer, so it is not scaffolding even without a failure marker.
BRANCH_RE = re.compile(
    r"→|->|^\s*(?:if|when|does|do|is|are|has|have|should|no|yes)\b[^.]*\?|\?\s*$",
    re.IGNORECASE,
)

# Inline code spans hold examples and flag syntax, not claims. Leaving them in
# lets a sample status line like `score: 74 (+2)` register as a threshold.
CODE_SPAN_RE = re.compile(r"`[^`]*`")


class Item:
    def __init__(self, lineno: int, text: str) -> None:
        self.lineno = lineno
        self.lines = [text]

    @property
    def body(self) -> str:
        return " ".join(self.lines)

    def matched_markers(self) -> list[str]:
        body = CODE_SPAN_RE.sub(" ", self.body).lower()
        marks = [name for name, pat in MARKERS if re.search(pat, body)]
        if BRANCH_RE.search(self.body):
            marks.append("branch")
        return marks


def parse_items(path: Path) -> list[Item]:
    """Collect numbered items with their continuation lines, skipping fences."""
    items: list[Item] = []
    current: Item | None = None
    in_fence = False

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            current = None
            continue
        if in_fence:
            continue

        match = ITEM_RE.match(raw)
        if match:
            current = Item(lineno, match.group(3))
            items.append(current)
            continue

        # A continuation line keeps the item open; a heading or blank-then-flush
        # line closes it. Markers routinely land on wrapped lines, so dropping
        # continuations would under-count criteria.
        if current is None:
            continue
        if not raw.strip() or HEADING_RE.match(raw):
            current = None
            continue
        current.lines.append(raw.strip())

    return items


def probe(path: Path, threshold: int, verbose: bool) -> int:
    items = parse_items(path)
    scaffold = [i for i in items if not i.matched_markers()]
    criteria = [i for i in items if i.matched_markers()]

    print(f"{path}")
    print(f"  numbered items : {len(items)}")
    print(f"  criteria       : {len(criteria)}  (carry a marker — do not count)")
    print(f"  scaffold       : {len(scaffold)}  (threshold {threshold})")

    if verbose:
        for item in scaffold:
            print(f"    SCAFFOLD  L{item.lineno}: {item.body[:88]}")
        for item in criteria:
            marks = ",".join(item.matched_markers())
            print(f"    CRITERION L{item.lineno} [{marks}]: {item.body[:70]}")

    if len(scaffold) >= threshold:
        print(f"  VERDICT: Dim 6 capped at 6 — {len(scaffold)} scaffold items")
        return 1
    print("  VERDICT: clean — no strict-workflow-scaffolding cap")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("skill", nargs="?", default="SKILL.md", type=Path)
    ap.add_argument("--refs", action="store_true", help="also probe references/*.md")
    ap.add_argument("--threshold", type=int, default=8)
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    if not args.skill.exists():
        print(f"error: {args.skill} not found", file=sys.stderr)
        return 2

    status = probe(args.skill, args.threshold, args.verbose)

    if args.refs:
        for ref in sorted((args.skill.parent / "references").glob("*.md")):
            probe(ref, args.threshold, args.verbose)

    return status


if __name__ == "__main__":
    sys.exit(main())
