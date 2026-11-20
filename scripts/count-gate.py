#!/usr/bin/env python3
"""Pre-push gate: the skill count stated in README.md and in the GitHub
repository description matches the number of skills being pushed.

A skill is a tracked .claude/skills/<name>/SKILL.md. The README is read from
the pushed commit; the description is read with `gh`. When `gh` is missing or
GitHub cannot be reached, the description check is skipped with a note and the
push goes on. Check-only.

    count-gate.py              outgoing commits (pre-commit pre-push env)
    count-gate.py --head REV   one commit (for testing)
    count-gate.py --selfcheck
"""

import os
import re
import subprocess
import sys

COUNT = re.compile(r"(\d+)\s+(?:installable\s+)?(?:reference\s+)?skills\b")


def stated(text):
    """The first '<n> ... skills' number in a text, or None."""
    m = COUNT.search(text or "")
    return int(m.group(1)) if m else None


def problems(actual, readme_text, description):
    """Messages for each place whose stated count differs from `actual`."""
    out = []
    n = stated(readme_text)
    if n is not None and n != actual:
        out.append(
            f"README.md says {n} skills; the repo has {actual}. Edit the number."
        )
    n = stated(description)
    if n is not None and n != actual:
        fixed = COUNT.sub(
            lambda m: m.group(0).replace(m.group(1), str(actual), 1), description, 1
        )
        out.append(
            f"the GitHub description says {n} skills; the repo has {actual}. Fix with:\n"
            f"    gh repo edit --description {fixed!r}"
        )
    return out


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None


def selfcheck():
    desc = "Marketplace — 77 installable reference skills across things."
    assert stated(desc) == 77 and stated("no number here") is None
    assert problems(77, "has 77 installable reference skills", desc) == []
    got = problems(78, "has 77 skills", desc)
    assert len(got) == 2 and "README.md says 77" in got[0], got
    assert "78 installable reference skills" in got[1], got[1]
    assert problems(78, "no count", None) == []  # nothing stated, nothing to check
    print("selfcheck: all assertions passed")
    return 0


def main(argv):
    if "--selfcheck" in argv:
        return selfcheck()
    head = os.environ.get("PRE_COMMIT_TO_REF", "") or "HEAD"
    if "--head" in argv:
        head = argv[argv.index("--head") + 1]
    if set(head) == {"0"}:
        return 0  # branch delete
    files = run("git", "ls-tree", "-r", "--name-only", head, "--", ".claude/skills")
    if files is None or files.returncode != 0:
        return 0
    actual = sum(
        1
        for f in files.stdout.splitlines()
        if f.count("/") == 3 and f.endswith("/SKILL.md")
    )
    readme = run("git", "show", f"{head}:README.md")
    desc = run("gh", "repo", "view", "--json", "description", "--jq", ".description")
    if desc is None or desc.returncode != 0:
        print(
            "count gate: GitHub description not checked (gh unavailable)",
            file=sys.stderr,
        )
    found = problems(
        actual,
        readme.stdout if readme and readme.returncode == 0 else "",
        desc.stdout.strip() if desc and desc.returncode == 0 else None,
    )
    for msg in found:
        print(f"count gate: {msg}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
