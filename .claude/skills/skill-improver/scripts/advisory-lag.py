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
  * A sources.md with no `Freshened:` stamp falls back to its OLDEST row date.
    That is a proxy, not a verification date, and the `verified` column marks it
    with a `~`. Measured over the fleet on 2026-09-15, 44 of 70 skills are
    unstamped and the proxy understates currency by a median of 137 days (mean
    304, max 2173). Often it is not a staleness signal at all: the oldest row is
    frequently a permanently-old artifact — a 2020 language spec, a 2023 vendor
    KB — whose date is when the source was published, not when anyone last
    checked it. Confirm against the skill's own text before treating a `~` row
    as behind; it may already carry the advisories this counts as unseen.

Needs `gh` authenticated. Skills whose repo has no advisory feed, or where the
API call fails, are skipped silently rather than reported as zero — an
unreachable feed is not the same as a clean one.

**An empty result is not zero advisories.** `repos/<o>/<r>/security-advisories`
returns `[]` both for a repo that has published none and for one where the token
lacks `repository_advisories=read` — and the second case is common on repos you
do not administer. huggingface/transformers returns `[]` here while the global
database lists four 2026 advisories for the same package. Empty rows are
therefore reported as `no repo feed`, not skipped, so the gap is visible. Check
those against the ecosystem database, which is a different endpoint keyed by
package rather than repo:

    gh api "/advisories?ecosystem=pip&affects=<package>&per_page=50"

**On version floors.** Where the repo-level feed does return data, this pass
measured `first_patched_version` null for every advisory across
vllm-project/vllm (35), open-webui/open-webui (69) and rancher/rancher (23), so
a floor there has to come from `vulnerable_version_range` ceilings. The global
database behaves differently and does populate the field. Do not generalise
either way: check which endpoint answered before trusting that field.

**And a populated `first_patched_version` can still name a version you cannot
install.** GHSA-xrqw-3rrv-vx5w records `5.10.0` for transformers; that release
was yanked for being published from a corrupted branch, and the first usable fix
is 5.10.1.
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
        if not adv:
            # Empty is ambiguous: no published advisories, or no read permission
            # on a repo we do not administer. Surface it rather than hide it.
            rows.append(
                {
                    "skill": d.name,
                    "upstream": f"{rp[0]}/{rp[1]}",
                    "verified": since,
                    "verified_from": how,
                    "new": 0,
                    "critical": 0,
                    "high": 0,
                    "worst": None,
                    "note": "no repo feed - check the ecosystem database by package",
                }
            )
            continue
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
        "%-34s %-30s %-13s %4s %4s %4s  %s"
        % ("skill", "upstream", "verified", "new", "crit", "high", "note")
    )
    for r in rows:
        mark = "!" if r["critical"] else " "
        # "~" = no Freshened: stamp, so this date is the oldest source row, a proxy.
        when = r["verified"] + ("~" if r["verified_from"] == "oldest-row" else "")
        print(
            "%s%-33s %-30s %-13s %4d %4d %4d  %s"
            % (
                mark,
                r["skill"],
                r["upstream"],
                when,
                r["new"],
                r["critical"],
                r["high"],
                r.get("note", ""),
            )
        )
    unseen = [r for r in rows if r["new"]]
    nofeed = [r for r in rows if not r["new"]]
    print(
        "\n%d skills have unseen advisories. Rows marked ! have an unseen CRITICAL."
        % len(unseen)
    )
    if nofeed:
        print(
            "%d more returned an EMPTY repo feed, which is not the same as zero: the "
            "token may lack repository_advisories=read. Check those by package against\n"
            '  gh api "/advisories?ecosystem=<eco>&affects=<package>&per_page=50"'
            % len(nofeed)
        )
    proxy = [r for r in rows if r["verified_from"] == "oldest-row"]
    if proxy:
        print(
            "%d rows show `~`: no Freshened: stamp, so the date is the oldest source row "
            "rather than a\n  verification date. It understates currency (fleet median 137d) "
            "and can be a permanently\n  old citation, not a stale check. Read the skill before "
            "trusting such a row's count." % len(proxy)
        )
    print(
        "Counts are leads: check that the advisory touches the skill's subject before acting."
    )


if __name__ == "__main__":
    main()
