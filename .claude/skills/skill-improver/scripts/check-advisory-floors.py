#!/usr/bin/env python3
"""Check that every "CVE-X is fixed in vY" claim agrees with the advisory.

`freshen` re-probes sources and `advisory-lag.py` finds advisories a skill has
not yet absorbed. Neither checks the claim a skill already made. A remediation
floor is the one number an operator acts on directly, and it fails silently in
both directions:

  * **Too low** — the named version is still inside the affected range, so the
    skill sends an operator to a build that is still vulnerable.
  * **Attributed to the wrong line** — a version outside every affected range is
    credited with the fix. Harmless-looking, because the upgrade advice usually
    still holds for another reason, which is exactly why it survives review.

Measured 2026-09-15 across the fleet: 104 advisory ids, 21 of them cited by more
than one skill, and one skill claimed a critical Argo CD advisory was "patched"
in two minors the advisory never listed as affected — one of them in a release
shipped three months *before* the fix. The same file stated the correct range a
few sections above.

**Flags are not findings; three shapes are expected and benign.** A *per-minor
backport floor* is real and common, so a version outside the range can still be
the right floor for its line. An *unbounded range with a null first-patched
version* means the feed does not know the fix, not that none exists — resolve it
through the fix PR's merge commit and `git tag --contains`. A *negative claim*
("does not affect 3.1") is a correction, not a floor. Read every flag against
the advisory before editing.

**The check is deliberately narrow, and the yield is low.** Of those 104 ids only
**7 lines state a floor unambiguously enough to check**: one advisory per line,
the version after the fix verb, no negation. Everything else is skipped rather
than guessed at -- a line naming three advisories and five versions cannot be
resolved by pattern, and attributing them anyway is how a checker manufactures
findings. `improvement-backlog.md` is skipped entirely, because it quotes the
defective floors a skill has already corrected.

Filters that prevent false findings silence true ones just as easily, so
`--selfcheck` replays the real Argo CD defect verbatim through the same filter
and asserts it still comes out condemned. A run reporting nothing is only
trustworthy while that assertion holds.

`--verify` is the whole point of the tool and needs network plus an
authenticated `gh`. Without it the run only lists claims, which is cheap but
catches nothing.

Usage:
    python3 check-advisory-floors.py [root] [--verify] [--selfcheck]

Exit: 0 clean, 1 claims flagged, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

ADVISORY = re.compile(
    r"\b(?:CVE-\d{4}-\d{4,7}|GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4})\b"
)
# Only lines that assert a fix. A line merely naming a CVE beside a version is
# usually prose about the affected range, and treating it as a claim is noise.
ASSERTS_FIX = re.compile(
    r"\b(?:patched|fixed|resolved|clears|remediat\w*|floor)\b", re.I
)
# Ranges, not floors: "affects <= 1.6.1", "3.2.0 - 3.3.8". Skip these lines.
ASSERTS_RANGE = re.compile(r"\b(?:affected|affects|vulnerable|inside|range)\b", re.I)
# A correction is not a floor: "does not affect 3.1", "was WRONG - claimed patched".
NEGATED = re.compile(
    r"\b(?:not|never|no longer|wrong|incorrect|claimed|predates|unpatched)\b", re.I
)
# "CVSS 9.9" is a score. Parsed as a version it flags on every advisory.
NOISE = re.compile(r"\bCVSS\s*v?\d+(?:\.\d+)?", re.I)
# Go module advisories carry pseudo-versions (0.0.0-<stamp>-<sha>) that share no
# numbering with the product's own releases, so no claim can be compared to them.
PSEUDO = re.compile(r"\b0\.0\.0-\d{14}-")
VERSION = re.compile(r"\bv?(\d+\.\d+(?:\.\d+)?(?:[.-]?(?:post|rc|r)\d+)?)\b")


def parse(v: str) -> tuple[int, ...]:
    """Loose numeric key. Non-numeric suffixes are dropped, which is fine here:
    the comparisons are against release boundaries, not build metadata."""
    return tuple(int(x) for x in re.findall(r"\d+", v)[:4])


def claim_versions(line: str) -> tuple[str, list[str]] | None:
    """(advisory, floors) if this line asserts a fix, else None.

    Every filter here exists to keep the tool from inventing a finding, and each
    one can silence a real defect just as easily. `selfcheck` therefore replays
    the defect this tool was written for through this function, to prove the
    filters still let it past.
    """
    ids = set(ADVISORY.findall(line))
    # One line, several advisories: which version belongs to which id is not
    # recoverable by pattern, and guessing invents findings.
    if len(ids) != 1:
        return None
    if not ASSERTS_FIX.search(line) or ASSERTS_RANGE.search(line):
        return None
    if NEGATED.search(line):
        return None
    clean = NOISE.sub("", line)
    # Only versions AFTER the last fix verb are the floor. A line often opens
    # with the current release ("latest v3.3.11") before saying what the advisory
    # patched, and that leading version is not a claim about it.
    tail = clean[max(m.end() for m in ASSERTS_FIX.finditer(clean)) :]
    versions = [
        m.group(1) for m in VERSION.finditer(tail) if tail[m.end() : m.end() + 1] != "+"
    ]
    # A CVE id contains digits that look like versions; drop them.
    ident = sorted(ids)[0]
    versions = [v for v in versions if v != ident.split("-")[1]]
    return (ident, versions) if versions else None


def claims(root: Path) -> list[tuple[str, str, str, list[str]]]:
    """(advisory, skill, line, versions) for every line asserting a fix."""
    out = []
    for md in sorted(root.rglob("*.md")):
        skill = md.relative_to(root).parts[0]
        if skill.endswith("-workspace"):
            continue
        # improvement-backlog.md records what a skill USED to get wrong. Those
        # sentences quote the defective floor verbatim, so scanning them
        # re-reports every defect already fixed.
        if md.name == "improvement-backlog.md":
            continue
        for line in md.read_text(encoding="utf-8", errors="replace").splitlines():
            got = claim_versions(line)
            if got:
                out.append((got[0], skill, line.strip(), got[1]))
    return out


def advisory(ident: str) -> dict | None:
    if ident.startswith("GHSA-"):
        url = f"/advisories/{ident}"
    else:
        url = f"/advisories?cve_id={ident}"
    r = subprocess.run(["gh", "api", url], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(d, list):
        d = d[0] if d else None
    return d


def ranges(adv: dict) -> list[tuple[str, str | None]]:
    return [
        (v.get("vulnerable_version_range") or "", v.get("first_patched_version"))
        for v in adv.get("vulnerabilities", [])
    ]


def inside(version: str, rng: str) -> bool:
    """True if version satisfies every clause of a GitHub range string."""
    key = parse(version)
    for clause in rng.split(","):
        clause = clause.strip()
        m = re.match(r"(>=|<=|>|<|=)?\s*(\S+)", clause)
        if not m:
            return False
        op, bound = m.group(1) or "=", parse(m.group(2))
        if op == ">=" and not key >= bound:
            return False
        if op == ">" and not key > bound:
            return False
        if op == "<=" and not key <= bound:
            return False
        if op == "<" and not key < bound:
            return False
        if op == "=" and key != bound:
            return False
    return True


def judge(version: str, rs: Sequence[tuple[str, str | None]]) -> str | None:
    """None when the claim is consistent; otherwise why it is not."""
    key = parse(version)
    if any(p and parse(p) == key for _, p in rs):
        return None
    # Order matters. An unbounded range (">= 0.3.0", no upper bound) contains
    # every later version, so `inside` is trivially true and proves nothing; if
    # the feed also has no first_patched_version it simply does not know the fix.
    # Testing containment first would flag every correct floor derived the only
    # way such a floor can be derived -- from the fix PR's merge commit.
    if all(p is None for _, p in rs) and any("<" not in rng for rng, _ in rs):
        return None
    if any(rng and inside(version, rng) for rng, _ in rs):
        return "STILL VULNERABLE: named version is inside the affected range"
    return "OUTSIDE RANGE: not a patched version and not in any affected range"


def selfcheck() -> int:
    assert parse("v3.2.11") == (3, 2, 11)
    assert inside("3.3.8", ">= 3.3.0, < 3.3.9")
    assert not inside("3.3.9", ">= 3.3.0, < 3.3.9")
    assert not inside("3.1.15", ">= 3.2.0, < 3.2.11")

    argo: list[tuple[str, str | None]] = [
        (">= 3.2.0, < 3.2.11", "3.2.11"),
        (">= 3.3.0, < 3.3.9", "3.3.9"),
    ]
    # The real defect this tool was written for.
    assert (judge("3.1.15", argo) or "").startswith("OUTSIDE")
    assert (judge("3.0.22", argo) or "").startswith("OUTSIDE")
    # The correct floors must stay silent.
    assert judge("3.2.11", argo) is None
    assert judge("3.3.9", argo) is None
    # A version still inside the range is the dangerous direction.
    assert (judge("3.3.8", argo) or "").startswith("STILL VULNERABLE")
    # Unbounded range with no known patch must NOT be reported as a defect.
    assert judge("0.22.0", [(">= 0.3.0", None)]) is None

    # A line stating an affected range is not a fix claim.
    assert ASSERTS_RANGE.search("affected range is 3.2.0 - 3.3.8")
    assert ASSERTS_FIX.search("patched in v3.2.11")
    # Corrections and historical records must not read as live floors.
    assert NEGATED.search("CVE-2026-42880 does not affect this minor")
    assert NEGATED.search("patched-version matrix was WRONG - claimed patched v3.3.8")
    assert not NEGATED.search("CVE-2026-42880 patched in v3.3.9 / v3.2.11")
    # A CVSS score is not a version.
    assert VERSION.search(NOISE.sub("", "CVSS 9.9 fixed in 6.7.0")).group(1) == "6.7.0"
    # Go pseudo-versions are uncomparable, not wrong.
    assert PSEUDO.search("< 0.0.0-20260608145523-cf437d7f1e05")
    assert not PSEUDO.search(">= 3.2.0, < 3.2.11")
    # Only the versions after the fix verb count as the claim.
    assert claim_versions(
        "latest v3.3.11, CVE-2026-42880 patched in v3.3.9 / v3.2.11"
    ) == ("CVE-2026-42880", ["3.3.9", "3.2.11"])

    # THE NEGATIVE ASSERTION. Every filter above can silence a true defect as
    # easily as a false one, and a tool tuned until it reports nothing looks
    # exactly like a clean fleet. This is the line that actually shipped the Argo
    # CD misattribution, verbatim: it must still reach `judge`, and `judge` must
    # still condemn it.
    shipped = (
        "  - **CVE-2026-42880 patched** in **v3.1.15** (2026-04-21). Surveyed "
        "cluster on 3.1.x must be >= 3.1.15 if it ever handled Secrets -- but "
        "the whole minor is EOL now, so just bump."
    )
    got = claim_versions(shipped)
    assert got is not None, "filters swallowed the defect this tool exists for"
    assert "3.1.15" in got[1], got
    assert (judge("3.1.15", argo) or "").startswith("OUTSIDE")
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("root", nargs="?", default=Path(".claude/skills"), type=Path)
    ap.add_argument(
        "--verify", action="store_true", help="check claims against the advisory feed"
    )
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        return selfcheck()
    if not a.root.is_dir():
        print(f"not a directory: {a.root}", file=sys.stderr)
        return 2

    found = claims(a.root)
    by_id: dict[str, set[str]] = defaultdict(set)
    for ident, skill, _, _ in found:
        by_id[ident].add(skill)
    print(
        f"{len(found)} fix claims over {len(by_id)} advisories "
        f"({sum(1 for v in by_id.values() if len(v) > 1)} cited by more than one skill)\n"
    )

    if not a.verify:
        print("no --verify: listing only. Re-run with --verify to check the floors.")
        return 0

    flagged = 0
    for ident in sorted(by_id):
        adv = advisory(ident)
        if adv is None:
            print(f"{ident}: NO FEED ENTRY (not in the GitHub database; check by hand)")
            continue
        rs = ranges(adv)
        if not rs:
            continue
        if any(PSEUDO.search(rng) or PSEUDO.search(p or "") for rng, p in rs):
            print(
                f"{ident}: Go pseudo-versions only -- cannot be compared to a "
                f"product release number. Check by hand."
            )
            continue
        for cid, skill, line, versions in found:
            if cid != ident:
                continue
            for v in versions:
                why = judge(v, rs)
                if why:
                    flagged += 1
                    print(
                        f"\n{ident}  [{skill}]  v{v}\n  {why}\n"
                        f"  advisory: {rs}\n  line: {line[:200]}"
                    )

    print(f"\n=== {flagged} flagged ===")
    if not flagged:
        print("none.")
    else:
        print(
            "Read each against the advisory: a per-minor backport floor and a\n"
            "negative claim both flag legitimately and are not defects."
        )
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
