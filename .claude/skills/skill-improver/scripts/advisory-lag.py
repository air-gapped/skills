#!/usr/bin/env python3
"""Rank skills by security advisories their upstream published since they were verified.

Freshen priority is usually read off a date: the oldest stamp goes first. That
ordering is blind to the thing most worth catching. A skill verified 8 weeks ago
whose upstream shipped a critical authentication bypass in week 6 is a worse
liability than one verified 6 months ago against a project that shipped nothing.

For each skill this reads `references/sources.md`, takes the `Freshened:` stamp
(or the oldest per-row date on legacy files), picks the GitHub repo that file
references most, and counts advisories published after that date.

Usage:
    python3 advisory-lag.py [root]          # default root: .claude/skills
    python3 advisory-lag.py --json [root]

Read the output as a LEAD, not a verdict:

  * Repo attribution is "most-referenced repo in sources.md". A skill covering
    many products (a compatibility matrix, a protocol implemented by several
    servers) gets attributed to one of them and its count means little.
  * An advisory against a project does not necessarily touch the subject of a
    given skill about that project. Confirm relevance before acting.
  * A legacy sources.md with no `Freshened:` stamp falls back to its OLDEST row
    date, which understates currency and inflates the count.

Needs `gh` authenticated. Skills whose repo has no advisory feed, or where the
API call fails, are skipped silently rather than reported as zero — an
unreachable feed is not the same as a clean one.

One thing this script deliberately does not report, because you cannot get it
from the feed: **a version floor**. Measured 2026-09-15 across three upstreams
(vllm-project/vllm 35 advisories, open-webui/open-webui 69,
rancher/rancher 23), `first_patched_version` was null for **every single
advisory** in the window. Tooling that reads that field concludes nothing is
fixed. Derive a floor from the `vulnerable_version_range` ceilings instead, and
treat a populated `first_patched_version` as the exception rather than the rule.
"""

import argparse
import collections
import json
import re
import subprocess
from pathlib import Path

DATE = re.compile(r"(20\d\d-\d\d-\d\d)")
REPO = re.compile(r"github\.com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)")
# Repos that describe the tooling rather than a skill's subject.
SKIP_ORGS = {"anthropics", "modelcontextprotocol"}


def verified_date(src: Path):
    text = src.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Freshened:\s*(20\d\d-\d\d-\d\d)", text)
    if m:
        return m.group(1), "stamp"
    dates = DATE.findall(text)
    return (min(dates), "oldest-row") if dates else (None, None)


def main_repo(src: Path):
    counts = collections.Counter()
    for org, repo in REPO.findall(src.read_text(encoding="utf-8", errors="replace")):
        if org.lower() in SKIP_ORGS:
            continue
        counts[(org, repo.removesuffix(".git"))] += 1
    return counts.most_common(1)[0][0] if counts else None


def advisories(org, repo):
    try:
        out = subprocess.run(
            ["gh", "api", f"repos/{org}/{repo}/security-advisories", "--paginate"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return json.loads(out.stdout or "[]") if out.returncode == 0 else None
    except Exception:
        return None


def collect(root: Path):
    rows = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        src = d / "references" / "sources.md"
        if not src.exists():
            continue
        since, how = verified_date(src)
        rp = main_repo(src)
        if not (since and rp):
            continue
        adv = advisories(*rp)
        if adv is None:
            continue
        newer = [a for a in adv if (a.get("published_at") or "") > since]
        if not newer:
            continue
        sev = collections.Counter(a.get("severity") for a in newer)
        rows.append(
            {
                "skill": d.name,
                "upstream": f"{rp[0]}/{rp[1]}",
                "verified": since,
                "verified_from": how,
                "new": len(newer),
                "critical": sev.get("critical", 0),
                "high": sev.get("high", 0),
                "worst": next(
                    (s for s in ("critical", "high", "medium", "low") if sev.get(s)),
                    None,
                ),
            }
        )
    # critical first, then high, then volume
    rows.sort(key=lambda r: (r["critical"], r["high"], r["new"]), reverse=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".claude/skills")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = collect(Path(a.root))
    if a.json:
        print(json.dumps(rows, indent=2))
        return
    print(
        "%-34s %-30s %-12s %4s %4s %4s"
        % ("skill", "upstream", "verified", "new", "crit", "high")
    )
    for r in rows:
        mark = "!" if r["critical"] else " "
        print(
            "%s%-33s %-30s %-12s %4d %4d %4d"
            % (
                mark,
                r["skill"],
                r["upstream"],
                r["verified"],
                r["new"],
                r["critical"],
                r["high"],
            )
        )
    print(
        "\n%d skills have unseen advisories. Rows marked ! have an unseen CRITICAL."
        % len(rows)
    )
    print(
        "Counts are leads: check that the advisory touches the skill's subject before acting."
    )


if __name__ == "__main__":
    main()
