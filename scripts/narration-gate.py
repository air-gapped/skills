#!/usr/bin/env python3
"""Pre-commit gate: skill markdown states what to do, not how it was checked.

Fails when a line ADDED to a skill's markdown says how or whether a fact was
verified, or cites a source line number. That belongs in the skill's
references/sources.md, which an agent does not load mid-task. Existing lines
are not judged. Check-only.

    narration-gate.py                      staged changes against HEAD
    narration-gate.py --base REV --head REV   one past change (for testing)
    narration-gate.py --selfcheck
"""

import re
import subprocess
import sys

SCOPE = ".claude/skills"
# skill-improver is exempt: verification status is its subject matter.
EXEMPT = re.compile(r"/(sources|improvement-backlog)\.md$|/evals/|/skill-improver/")
PATTERNS = [
    ("verification status", r"\b(not|never) (yet )?(run|tested|tried|verified|confirmed|checked) (live|in code|against (a|the) |on a (live|real|running))"),
    ("verification status", r"(?<![\"`])\b(untested|unverified|unconfirmed|unchecked)\b(?![\"`])"),
    ("verification status", r"\bconfirm (it )?live\b"),
    ("how it was found", r"\b(read|derived|taken) from (the )?(v[\d.]+ )?source\b"),
    ("how it was found", r"\bsource[- ]read(ing)?\b|\bper (the )?source\b|\bfrom reading\b"),
    ("how it was found", r"\bwe (found|saw|measured|tried|think|decided|checked|assumed)\b"),
    ("dated check", r"\b(measured|verified|checked|probed|confirmed|tested) (on|at) \d{4}-\d{2}-\d{2}"),
    ("source line number", r"\.(py|go|rs|ts|js|c|h):\d+\b|(~|\b(around|about|near|at) )line \d+\b"),
]  # fmt: skip
COMPILED = [(kind, re.compile(rx, re.IGNORECASE)) for kind, rx in PATTERNS]


def findings(diff):
    """Yield (path, kind, text) for each added line that narrates."""
    path, in_fence = None, False
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path, in_fence = line[6:], False
            continue
        if path is None or not path.startswith(SCOPE) or not path.endswith(".md"):
            continue
        if EXEMPT.search(path):
            continue
        body = line[1:]
        if line[:1] in "+ " and body.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not line.startswith("+") or in_fence:
            continue
        for kind, rx in COMPILED:
            if rx.search(body):
                yield path, kind, body.strip()
                break


def report(found):
    for path, kind, text in found:
        print(f"{path}: {kind}: {text[:110]}", file=sys.stderr)
    if found:
        skills = sorted({p.split("/")[2] for p, _, _ in found if p.count("/") > 2})
        print(
            "\nnarration gate: the lines above say how or whether a fact was checked. "
            "An agent reading the skill cannot act on that.\n"
            "  - State the fact, or the action to take, with no account of the checking.\n"
            "  - Put where it came from and how far it was verified in "
            f"{SCOPE}/<skill>/references/sources.md ({', '.join(skills)}).\n"
            "  - A claim too uncertain to state plainly: leave it out of the skill.\n"
            "Then stage and commit again.",
            file=sys.stderr,
        )
    return 1 if found else 0


def selfcheck():
    def diff(path, *added):
        return f"+++ b/{path}\n@@\n" + "\n".join(f"+{a}" for a in added)

    skill = f"{SCOPE}/x/SKILL.md"
    bad = [
        "Signin returns a token (untested against a live instance).",
        "Read from v0.13.4 source, not run live.",
        "The key is checked in utils/auth.py:512.",
        "accepted only when the flag is true (around line 512).",
        "We found that the import ignores unknown keys.",
        "Verified on 2026-11-18 against the tag.",
    ]
    for line in bad:
        assert list(findings(diff(skill, line))), line
    good = [
        "With the flag off every API key gets a 403.",
        "Run the import, then compare the response with the file.",
        "Tests that are not run in CI must be listed here.",  # a rule, not a status
        "Use `--line 12` to select the row.",
    ]
    for line in good:
        assert not list(findings(diff(skill, line))), line
    assert not list(findings(diff(f"{SCOPE}/x/references/sources.md", bad[0])))
    assert not list(findings(diff("README.md", bad[0])))
    fenced = diff(
        skill, "```bash", "grep -n foo utils/auth.py:512", "```", "After the fence."
    )
    assert not list(findings(fenced))
    print("selfcheck: all assertions passed")
    return 0


def main(argv):
    if "--selfcheck" in argv:
        return selfcheck()
    cmd = ["git", "diff", "--cached", "-U100000", "--", SCOPE]
    if "--base" in argv:
        base, head = argv[argv.index("--base") + 1], argv[argv.index("--head") + 1]
        cmd = ["git", "diff", "-U100000", base, head, "--", SCOPE]
    diff = subprocess.run(cmd, capture_output=True, text=True).stdout
    return report(list(findings(diff)))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
