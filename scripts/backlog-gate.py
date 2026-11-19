#!/usr/bin/env python3
"""Pre-commit gate for <skill>/references/improvement-backlog.md. Check-only.

Compares each staged backlog with its version at HEAD and fails when the change:

  parks work    adds an entry to a section headed `## Unblocked`
  hides a block adds an entry under `## Open` with no `Blocker:` line
  drops a guard leaves fewer discard-guard entries than HEAD had

    backlog-gate.py <file>...                   staged version against HEAD
    backlog-gate.py --base REV --head REV <file>  one past change (for testing)
    backlog-gate.py --selfcheck
"""

import re
import subprocess
import sys

ENTRY = re.compile(r"^(### |- |\d+\. |\*\*)")
GUARD_HEADING = re.compile(r'(?i)discard|do not re-propose|do not "fix"|settled')
GUARD_ENTRY = re.compile(r"(?i)^(### |- |\d+\. |\*\*)\W*(discard|rejected)")
FORMAT = ".claude/skills/skill-improver/references/backlog-format.md"


def sections(text):
    """Yield (heading, [entry blocks]) for each `## ` section."""
    heading, blocks = "", []
    for line in text.splitlines():
        if line.startswith("## "):
            yield heading, blocks
            heading, blocks = line, []
        elif ENTRY.match(line):
            blocks.append(line)
        elif blocks and line.strip():
            blocks[-1] += "\n" + line
    yield heading, blocks


def summarize(text):
    unblocked, open_entries, guards = [], [], 0
    for heading, blocks in sections(text):
        if heading.startswith("## Unblocked"):
            unblocked += blocks
        elif heading.startswith("## Open"):
            open_entries += blocks
        if GUARD_HEADING.search(heading):
            guards += len(blocks)
        else:
            guards += sum(1 for b in blocks if GUARD_ENTRY.match(b))
    return unblocked, open_entries, guards


def check(old, new):
    """Return the list of failures for one backlog going from old to new."""
    old_unblocked, old_open, old_guards = summarize(old)
    new_unblocked, new_open, new_guards = summarize(new)
    fails = []
    if len(new_unblocked) > len(old_unblocked):
        fails.append(
            f"{len(new_unblocked) - len(old_unblocked)} entr(ies) added under "
            "`## Unblocked`. Work an agent can do now is done in this pass, not "
            f"filed. Do it, or delete the entry. Rule: {FORMAT} §Open."
        )
    known = {b.splitlines()[0] for b in old_open}
    for block in new_open:
        first = block.splitlines()[0]
        if first not in known and "Blocker:" not in block:
            fails.append(
                f"new Open entry has no `Blocker:` line: {first[:70]!r}. Name the "
                "absent thing (release, credential, unreachable endpoint, purchase, "
                f"spend above the ceiling). No such thing: do the work. Rule: {FORMAT}."
            )
    if new_guards < old_guards:
        fails.append(
            f"discard-guard entries fell from {old_guards} to {new_guards}. A guard "
            "records a change that was tried and rejected, and deleting it lets the "
            "next pass propose it again. Move it under `## Discard guards` instead."
        )
    return fails


def git_show(spec):
    r = subprocess.run(["git", "show", spec], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def selfcheck():
    base = "## Open\n\n_None._\n\n## Discard guards\n\n- tried X, worse\n- tried Y, worse\n"
    assert check(base, base) == []
    parked = base + "\n## Unblocked — actionable\n\n- rewrite the table\n"
    assert len(check(base, parked)) == 1, check(base, parked)
    filed = base.replace("_None._", "- wait for v2\n  some context")
    assert len(check(base, filed)) == 1, check(base, filed)
    named = base.replace("_None._", "- wait for v2\n  Blocker: v2 is not released")
    assert check(base, named) == []
    assert check(named, named.replace("some", "more")) == []  # old entries pass
    cut = base.replace("- tried Y, worse\n", "")
    assert len(check(base, cut)) == 1, check(base, cut)
    reworded = base.replace("tried Y, worse", "tried Y; it scored lower")
    assert check(base, reworded) == []
    diary = "## Resolved this pass\n\n- Discard: cut the table\n- Kept: new row\n"
    assert len(check(diary, "## Open\n")) == 1  # a guard inside a deleted diary
    assert (
        check(
            "",
            parked.replace("\n## Unblocked — actionable\n\n- rewrite the table\n", ""),
        )
        == []
    )
    print("selfcheck: all assertions passed")
    return 0


def main(argv):
    if "--selfcheck" in argv:
        return selfcheck()
    base, head = "HEAD", ""  # "" = the index
    if "--base" in argv:
        base = argv.pop(argv.index("--base") + 1)
        argv.remove("--base")
    if "--head" in argv:
        head = argv.pop(argv.index("--head") + 1)
        argv.remove("--head")
    rc = 0
    for path in argv:
        new = git_show(f"{head}:{path}")
        if not new:
            continue  # deleted in this change
        for fail in check(git_show(f"{base}:{path}"), new):
            print(f"{path}: {fail}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
