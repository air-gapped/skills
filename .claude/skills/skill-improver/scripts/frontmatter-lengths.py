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

Exit: 0 measured, no violation; 1 a SPEC VIOLATION line was printed (block does
not parse, or `description` over the hard max) or there is no frontmatter; 2 the
file could not be read.

Usage: frontmatter-lengths.py <path-to-SKILL.md> | --selfcheck
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_frontmatter import read_frontmatter  # noqa: E402

CAP_COMBINED = 1536
CAP_DESCRIPTION = 1024


def selfcheck() -> int:
    """Offline. Each planted file must exit the way its defect demands."""
    import subprocess
    import tempfile
    from pathlib import Path

    def run(body: str | None, env: dict | None = None) -> tuple[int, str]:
        path = Path(tempfile.mkdtemp(prefix="fm-lengths-")) / "SKILL.md"
        if body is not None:
            path.write_text(body, encoding="utf-8")
        p = subprocess.run(
            [sys.executable, __file__, str(path)],
            capture_output=True,
            text=True,
            env=env,
        )
        return p.returncode, p.stdout + p.stderr

    # The plant: block scalars measure as the loader reads them — indicator,
    # indentation and folded line breaks are not characters of the value.
    blocks = "---\nname: b\ndescription: |-\n  ab\n  cd\nwhen_to_use: >-\n  ef\n  gh\n---\n# b\n"
    rc, out = run(blocks)
    assert rc == 0 and "description: 5 chars" in out, (rc, out)
    assert "description+when_to_use: 10 chars" in out, (rc, out)
    # Same file with PyYAML unimportable: the fallback reader, same numbers.
    shadow = Path(tempfile.mkdtemp(prefix="fm-lengths-noyaml-"))
    (shadow / "yaml.py").write_text("raise ImportError('hidden for the selfcheck')\n")
    rc, out = run(blocks, dict(os.environ, PYTHONPATH=str(shadow)))
    assert rc == 0 and "WARNING: PyYAML not installed" in out, (rc, out)
    assert "description: 5 chars" in out, (rc, out)
    assert "description+when_to_use: 10 chars" in out, (rc, out)

    rc, out = run("---\nname: ok\ndescription: short\n---\n# ok\n")
    assert rc == 0 and "description: 5 chars" in out, (rc, out)
    # The plant: a description over the hard max is a violation, not a reading.
    rc, out = run(f"---\nname: long\ndescription: {'x' * 1100}\n---\n# long\n")
    assert rc == 1 and "SPEC VIOLATION: description 1100 > 1024" in out, (rc, out)
    rc, out = run("---\nname: bad\ndescription: a: b: c\n---\n# bad\n")
    assert rc == 1 and "not valid YAML" in out, (rc, out)
    rc, out = run("# no frontmatter\n")
    assert rc == 1 and "no YAML frontmatter" in out, (rc, out)
    rc, out = run(None)
    assert rc == 2 and "no such file" in out and "Traceback" not in out, (rc, out)
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    if sys.argv[1] == "--selfcheck":
        return selfcheck()
    try:
        text = open(sys.argv[1], encoding="utf-8").read()
    except OSError as e:
        print(f"no such file: {sys.argv[1]} ({e.strerror})", file=sys.stderr)
        return 2
    parts = text.split("---")
    if len(parts) < 3:
        print("no YAML frontmatter found", file=sys.stderr)
        return 1
    fm = parts[1]

    # Parse gate. A block that does not parse is a hard fail regardless of what
    # any field measures, so report it and stop rather than printing lengths the
    # loader will never use.
    parsed = None
    fallback: dict = {}
    try:
        import yaml
    except ImportError:
        print(
            "WARNING: PyYAML not installed — cannot verify the frontmatter parses. "
            "Lengths below come from the fallback reader and would look identical for "
            "a block that Claude Code loads with every field dropped. `pip install pyyaml`."
        )
        try:
            fallback = read_frontmatter(text, use_yaml=False)
        except ValueError:
            fallback = {}
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

    def value_of(name: str) -> str | None:
        # Measure what the LOADER sees, not the raw block text. A `>-` folded
        # scalar spans many indented lines; YAML folds each newline+indent to a
        # single space, so a capture of the raw block is longer than the real
        # string by ~2 chars per continuation line. Measured 2026-08-25 across
        # 61 skills: a regex over the block over-counted by up to 54 chars and
        # invented a cap overrun on 15 skills that are in fact under it — and
        # it bites hardest on skills near the cap, where the fix an agent then
        # applies is to delete real trigger phrases. Without PyYAML the shared
        # fallback reader applies the same scalar rules; the warning above
        # still flags that the block's validity is unverified.
        v = (parsed if isinstance(parsed, dict) else fallback).get(name)
        return None if v is None else str(v)

    combined = 0
    for name in ("name", "description", "when_to_use"):
        value = value_of(name)
        if value is None:
            print(f"{name}: ABSENT")
            continue
        print(f"{name}: {len(value)} chars")
        if name != "name":
            combined += len(value)

    desc = value_of("description")
    violation = desc is not None and len(desc) > CAP_DESCRIPTION
    if violation:
        print(
            f"SPEC VIOLATION: description {len(desc)} > {CAP_DESCRIPTION} hard max "
            f"-> Dim 9 hard-fail cap at 3"
        )
    print(
        f"description+when_to_use: {combined} chars "
        f"(listing cap {CAP_COMBINED}, overrun {max(0, combined - CAP_COMBINED)})"
    )
    return 1 if violation else 0


if __name__ == "__main__":
    raise SystemExit(main())
