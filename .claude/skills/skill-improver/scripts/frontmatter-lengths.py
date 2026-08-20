#!/usr/bin/env python3
"""Exact frontmatter field lengths for a SKILL.md — the numbers Dim 1 and Dim 9 score on.

Both dimensions hinge on character counts (1,536 combined listing cap for
`description` + `when_to_use`; 1,024 hard max on `description` alone). A model
estimating those lengths is a measured failure mode: a scorer was observed
reporting 1,120 for a field that measures 847 and hard-failing Dim 9 to 3 on it
(2026-08-20). Run this instead of estimating.

FIRST it checks the block is parseable YAML, because a broken block is the one
failure this tool used to make INVISIBLE. Claude Code loads an unparseable
frontmatter block by dropping every field: the name falls back to the directory
name, the description to the first line of the body, and `allowed-tools`,
`model`, and `disable-model-invocation` silently stop applying. Nothing warns at
normal verbosity. This script measured such files with regex and printed
confident, healthy-looking numbers for fields the loader had already discarded
(found on two skills, 2026-08-20). Regex cannot see the difference; a parser can.

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

    # Parse gate. A block that does not parse is a hard fail regardless of what
    # any field measures, so report it and stop rather than printing lengths the
    # loader will never use.
    try:
        import yaml
    except ImportError:
        print(
            "WARNING: PyYAML not installed — cannot verify the frontmatter parses. "
            "Lengths below are regex-derived and would look identical for a block "
            "that Claude Code loads with every field dropped. `pip install pyyaml`."
        )
    else:
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            where = f" at frontmatter line {mark.line + 1}" if mark else ""
            print(
                f"SPEC VIOLATION: frontmatter is not valid YAML{where} -> Dim 9 hard-fail cap at 3"
            )
            print(f"  {str(e).splitlines()[0]}")
            if mark:
                lines = fm.split("\n")
                if 0 <= mark.line < len(lines):
                    print(f"  {mark.line + 1}> {lines[mark.line][:200]}")
            print(
                "  Claude Code loads this skill with EVERY frontmatter field dropped: "
                "name falls back to the directory name, description to the first body "
                "line, and allowed-tools/model/disable-model-invocation stop applying."
            )
            print(
                "  Usual cause: an unquoted value containing ': '. Fix by making the "
                "value a block scalar (`description: >-`, value indented on the next line)."
            )
            return 1
        if not isinstance(parsed, dict):
            print(
                "SPEC VIOLATION: frontmatter is not a YAML mapping -> Dim 9 hard-fail cap at 3"
            )
            return 1

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
