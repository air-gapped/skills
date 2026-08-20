#!/usr/bin/env python3
"""Exact frontmatter field lengths for a SKILL.md — the numbers Dim 1 and Dim 9 score on.

Both dimensions hinge on character counts (1,536 combined listing cap for
`description` + `when_to_use`; 1,024 hard max on `description` alone). A model
estimating those lengths is a measured failure mode: a scorer was observed
reporting 1,120 for a field that measures 847 and hard-failing Dim 9 to 3 on it
(2026-08-20). Run this instead of estimating.

Usage: frontmatter-lengths.py <path-to-SKILL.md>
"""

import re
import sys

CAP_COMBINED = 1536
CAP_DESCRIPTION = 1024


def field(fm: str, name: str) -> str | None:
    # [\w-] not \w: YAML keys may contain hyphens (argument-hint, allowed-tools).
    # With \w the lookahead misses them and the preceding field swallows the rest
    # of the frontmatter — measured 2026-08-20 inflating a combined total by 99
    # chars and inventing an overrun that did not exist.
    m = re.search(rf"^{name}:\s*(.*?)(?=^[\w-]+:|\Z)", fm, re.S | re.M)
    return m.group(1).strip() if m else None


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    text = open(sys.argv[1], encoding="utf-8").read()
    parts = text.split("---")
    if len(parts) < 3:
        print("no YAML frontmatter found", file=sys.stderr)
        return 1
    fm = parts[1]

    combined = 0
    for name in ("name", "description", "when_to_use"):
        value = field(fm, name)
        if value is None:
            print(f"{name}: ABSENT")
            continue
        print(f"{name}: {len(value)} chars")
        if name != "name":
            combined += len(value)

    desc = field(fm, "description")
    if desc is not None and len(desc) > CAP_DESCRIPTION:
        print(
            f"SPEC VIOLATION: description {len(desc)} > {CAP_DESCRIPTION} hard max "
            f"-> Dim 9 hard-fail cap at 3"
        )
    print(
        f"description+when_to_use: {combined} chars "
        f"(listing cap {CAP_COMBINED}, overrun {max(0, combined - CAP_COMBINED)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
