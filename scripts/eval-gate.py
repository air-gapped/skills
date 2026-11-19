#!/usr/bin/env python3
"""Pre-push gate: a skill with eval cases is not pushed with unmeasured changes.

For each skill that has evals/evals.json and whose content differs between the
remote and what is being pushed, evals/last-run.json must carry the hash of the
content being pushed. outcome-eval.py writes that file on every measured run,
so one run of the cases the change touches clears the gate. Check-only.

    eval-gate.py                         outgoing commits (pre-commit pre-push env)
    eval-gate.py --base REV --head REV   one past range (for testing)
    eval-gate.py --selfcheck
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = ".claude/skills"
IMPROVER = f"{SKILLS}/skill-improver/scripts"


def load_hasher():
    spec = importlib.util.spec_from_file_location(
        "skill_content", REPO / IMPROVER / "skill_content.py"
    )
    if spec is None or spec.loader is None:
        sys.exit("eval-gate: cannot load skill_content.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.content_hash_at


def git(*args):
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True
    )


def verdict(old_hash, new_hash, has_evals, stamp_hash):
    """None when the push is fine for this skill, else the reason it is not."""
    if not has_evals or old_hash == new_hash:
        return None
    if stamp_hash is None:
        return "its eval cases have not been run since"
    if stamp_hash != new_hash:
        return "it changed again after the last eval run"
    return None


def selfcheck():
    assert verdict("a", "a", True, None) is None  # unchanged
    assert verdict("a", "b", False, None) is None  # no eval cases
    assert verdict("a", "b", True, None)  # changed, never measured
    assert verdict("a", "b", True, "a")  # measured before the change
    assert verdict("a", "b", True, "b") is None  # measured on this content
    assert verdict("", "b", True, "b") is None  # new skill, measured
    print("selfcheck: all assertions passed")
    return 0


def main(argv):
    if "--selfcheck" in argv:
        return selfcheck()
    if "--base" in argv:
        base, head = argv[argv.index("--base") + 1], argv[argv.index("--head") + 1]
    else:
        base = os.environ.get("PRE_COMMIT_FROM_REF", "")
        head = os.environ.get("PRE_COMMIT_TO_REF", "")
        if not head or set(head) == {"0"}:
            return 0  # branch delete
        if not base or set(base) == {"0"}:
            base = git("merge-base", head, "origin/main").stdout.strip()
        if not base:
            return 0
    hash_at = load_hasher()
    changed = git("diff", "--name-only", base, head, "--", SKILLS).stdout.split()
    names = sorted({p.split("/")[2] for p in changed if p.count("/") > 2})
    rc = 0
    for name in names:
        rel = f"{SKILLS}/{name}"
        has_evals = (
            git("cat-file", "-e", f"{head}:{rel}/evals/evals.json").returncode == 0
        )
        stamp = git("show", f"{head}:{rel}/evals/last-run.json")
        stamp_hash = None
        if stamp.returncode == 0:
            try:
                stamp_hash = json.loads(stamp.stdout).get("content_hash")
            except ValueError:
                stamp_hash = None
        why = verdict(
            hash_at(REPO, base, rel), hash_at(REPO, head, rel), has_evals, stamp_hash
        )
        if why:
            rc = 1
            print(
                f"eval gate: {name} changed and {why}.\n"
                f"  Run the cases this change touches, then commit {rel}/evals/last-run.json:\n"
                f"    python3 {IMPROVER}/outcome-eval.py {rel} --case '<NN-glob>,<NN-glob>'\n"
                f"  Case names: {rel}/evals/evals.json. State the spend first: about\n"
                "  $2 per case at the default 3 runs. Read the weak cases it lists\n"
                "  and fix what they show before pushing.",
                file=sys.stderr,
            )
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
