#!/usr/bin/env python3
"""Fleet-wide deterministic pre-scoring gate, built on NVIDIA SkillEvaluator.

The rubric scores what a skill *says*. This scores what it *is*: invisible
Unicode, leaked home paths, credentials, and frontmatter that violates the
Agent Skills schema. None of it needs a model, a key, or the network, and none
of it is reachable by reading prose — a tag-block smuggling payload
(U+E0000..E007F) renders as nothing at all in the editor a scorer reads.

Runs `skillevaluator validate --checks schema,pii,unicode,lint --no-dedup` per
skill and sorts every finding into three buckets. The bucketing is the point:
a first measured pass over 105 skills produced 529 findings — 368 once the
two pure-policy checks are dropped — of which 28 were actionable, so the raw
exit code is not usable as a gate here.

    ACTIONABLE  real defects — fix or justify
    REVIEW      classes that are usually false here but can never be
                auto-dismissed (a real credential must not be suppressed)
    SUPPRESSED  checks that encode a house style this fleet does not share

Install (base only — no LLM or Harbor deps, nothing leaves the machine):

    uv tool install --python 3.13 \\
        "skillevaluator @ git+https://github.com/NVIDIA/SkillEvaluator.git"

Usage:

    python3 tier1-sweep.py                    # repo + user skill dirs
    python3 tier1-sweep.py --root DIR ...     # explicit roots
    python3 tier1-sweep.py --all              # show suppressed too
    python3 tier1-sweep.py --json             # machine output
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

CHECKS = "schema,pii,unicode,lint"

# Checks encoding a publication policy or house style this fleet does not
# share. Each entry states why, so a future reader can re-litigate one of them
# without re-deriving the evidence.
SUPPRESSED: dict[str, str] = {
    # SkillEvaluator's default `external` profile is a public-marketplace
    # policy requiring `metadata.author: Name <email>`. These skills carry
    # authorship in git, not frontmatter.
    "author_missing": "fleet does not use metadata.author; git carries authorship",
    # Expects `skills/<name>/`; Claude Code's layout is `.claude/skills/<name>/`.
    "folder_hierarchy": "Claude Code layout is .claude/skills/<name>/",
    # Prescribes '## Instructions' / '## Examples' headings. 196 hits on the
    # first pass — it is a template preference, not a defect.
    "body_recommended_section": "prescribes a section template this fleet does not use",
}

# Upstream ships these as advisory (they never fail its gate) and they are
# tuned for standalone tools, not skill helper scripts.
SUPPRESSED_CATEGORIES: dict[str, str] = {
    "SCRIPT_LINT": "advisory upstream; magic-number/shebang rules do not fit helper scripts",
}

# Findings that must stay visible but are usually false in a documentation
# corpus. Measured on the first pass: hardcoded_secrets 17/17 false (Jinja
# refs, `<placeholder>`, redacted `***`), ip_addresses dominated by four-part
# firmware versions (`7.30.10.50`), emails by placeholders outside upstream's
# example.com allowlist. Never auto-dismiss: one real credential outranks the
# whole false-positive tail.
REVIEW = {
    "hardcoded_secrets",
    "database_credentials",
    "emails",
    "ip_addresses",
    "phone_numbers",
    "gps_coordinates",
    "mac_addresses",
    "aws_identifiers",
    "credit_cards",
    "private_keys",
    "isolated_invisible_char",
}

DEFAULT_ROOTS = [
    Path.home() / "projects/skills/.claude/skills",
    Path.home() / ".claude/skills",
]


def discover(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        # A root may be a directory of skills, or one skill itself.
        if (root / "SKILL.md").is_file():
            found.append(root)
            continue
        for child in sorted(root.iterdir()):
            if (child / "SKILL.md").is_file():
                found.append(child)
    return found


def bucket(finding: dict) -> str:
    if finding["category"] in SUPPRESSED_CATEGORIES:
        return "suppressed"
    if finding["check_name"] in SUPPRESSED:
        return "suppressed"
    if finding["check_name"] in REVIEW:
        return "review"
    return "actionable"


def validate(skill: Path, workdir: Path) -> list[dict]:
    """Run one skill through Tier 1 and return its findings."""
    out = workdir / skill.name
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "skillevaluator",
            "validate",
            str(skill),
            "--checks",
            CHECKS,
            "--no-dedup",
            "-r",
            "json",
            "-o",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,  # a non-zero exit just means findings exist
    )
    reports = sorted(out.glob("*.json"))
    if not reports:
        raise RuntimeError(f"no JSON report written for {skill}")
    report = json.loads(reports[0].read_text())
    return [f for r in report["results"] for f in (r.get("findings") or [])]


def rel(path: str | None, skill: Path) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).relative_to(skill))
    except ValueError:
        return str(path).replace(str(Path.home()), "~")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic Tier 1 sweep over a skill fleet (SkillEvaluator)."
    )
    ap.add_argument(
        "--root",
        action="append",
        type=Path,
        dest="roots",
        help="skill directory root (repeatable; defaults to repo + user)",
    )
    ap.add_argument("--all", action="store_true", help="show suppressed findings too")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    if not shutil.which("skillevaluator"):
        print(
            "skillevaluator not on PATH. Install it with:\n"
            '  uv tool install --python 3.13 "skillevaluator @ '
            'git+https://github.com/NVIDIA/SkillEvaluator.git"',
            file=sys.stderr,
        )
        return 2

    # Enables the home-path check: upstream compares detected user paths
    # against every identity that resolves, and skips the check silently when
    # none does. Without this the highest-value check is a no-op.
    os.environ.setdefault("SKILLEVALUATOR_SUBMITTER", os.environ.get("USER", "unknown"))

    skills = discover(args.roots or DEFAULT_ROOTS)
    if not skills:
        print("no skills found", file=sys.stderr)
        return 2

    results: dict[str, dict[str, list[dict]]] = {}
    counts: Counter[str] = Counter()
    with tempfile.TemporaryDirectory(prefix="tier1-sweep-") as tmp:
        workdir = Path(tmp)
        for i, skill in enumerate(skills, 1):
            print(
                f"\r  scanning {i}/{len(skills)} {skill.name[:40]:40}",
                end="",
                file=sys.stderr,
            )
            buckets: dict[str, list[dict]] = {
                "actionable": [],
                "review": [],
                "suppressed": [],
            }
            for finding in validate(skill, workdir):
                b = bucket(finding)
                buckets[b].append(finding)
                counts[b] += 1
            results[skill.name] = buckets
    print(f"\r  scanned {len(skills)} skills{' ' * 40}", file=sys.stderr)

    if args.as_json:
        print(json.dumps({"skills": results, "counts": dict(counts)}, indent=2))
        return 1 if counts["actionable"] else 0

    show = ["actionable", "review"] + (["suppressed"] if args.all else [])
    for label in show:
        total = counts[label]
        print(f"\n=== {label.upper()} ({total}) ===")
        if not total:
            print("  none")
            continue
        for name, buckets in results.items():
            items = buckets[label]
            if not items:
                continue
            print(f"\n  {name}")
            for f in items:
                skill_dir = next(s for s in skills if s.name == name)
                loc = rel(f.get("file_path"), skill_dir)
                line = f":{f['line_number']}" if f.get("line_number") else ""
                print(
                    f"    [{f['severity'][:4]}] {f['check_name']}: {f['message'][:100]}"
                )
                if loc:
                    print(f"          {loc}{line}")

    print(
        f"\n{len(skills)} skills · {counts['actionable']} actionable · "
        f"{counts['review']} to review · {counts['suppressed']} suppressed"
    )
    if not args.all and counts["suppressed"]:
        print("(--all shows suppressed; --json for machine output)")
    return 1 if counts["actionable"] else 0


if __name__ == "__main__":
    sys.exit(main())
