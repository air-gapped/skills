#!/usr/bin/env python3
"""Flag skill prose whose issue/PR state claim contradicts the tracker.

A skill that says "still OPEN" about a closed issue, or "merged" about a PR that
was closed unmerged, is wrong in a way that changes what an agent does: it either
keeps a warning alive past its fix, or retires one that is still load-bearing.
Both are decidable against the tracker, which is why this check is worth running
and the four semantic sweeps in `references/fleet-checks.md` were not.

Only three disagreement classes are reported. Each is a defect whichever side you
believe:

    A  text says open      + tracker CLOSED or MERGED
    B  text says merged    + tracker CLOSED   (i.e. closed unmerged)
    C  text says unmerged  + tracker MERGED

Deliberate "closed by the stale bot, treat as still live" wording is NOT a
finding -- see EXEMPT below. That phrasing is correct and common, and a checker
that condemned it would train its users to ignore it.

CLOSED IS NOT FIXED. The tracker distinguishes only open from closed; it does not
distinguish a fix from an inactivity autoclose. This tool tells you a claim has
drifted, never which way to rewrite it. Read `stateReason` and the closing
comment before editing:

    gh issue view <N> --repo <O>/<R> --json state,stateReason,closedAt,comments

`NOT_PLANNED` + a bot comment is abandonment and the warning stays. `COMPLETED`
with a linked PR is a fix -- and then get the version from ancestry, not from
comparing the merge date to a release date:

    git -C <clone> tag --contains <merge-sha> | grep -E '^v[0-9]+\\.[0-9]+\\.[0-9]+$' | sort -V | head -1

A merge landing after a release branch was cut ships in the release *after* the
next one, which date arithmetic gets wrong.

Usage:
    check-issue-states.py [PATH ...]     # default: .claude/skills
    check-issue-states.py --selfcheck    # offline, no network
"""

import json
import re
import subprocess
import sys
from pathlib import Path

RE_URL = re.compile(r"github\.com/([\w.-]+)/([\w.-]+)/(issues|pull)/(\d+)")

SAYS_OPEN = re.compile(
    r"\b(still open|remains open|is still open|currently open|still unfixed|"
    r"open as of|no fix yet|unfixed upstream|has not landed|still has not landed)\b",
    re.I,
)
SAYS_MERGED = re.compile(
    r"\b(merged|landed in|shipped in|fixed by PR|fix landed)\b", re.I
)
SAYS_UNMERGED = re.compile(
    r"\b(closed unmerged|never merged|not merged|closed without merging|"
    r"closed without being merged|unmerged)\b",
    re.I,
)

# Wording that deliberately reports a closed issue as a live risk. Present on a
# line, the "open" claim is about the RISK, not the tracker state, and class A is
# suppressed. Dropping this turns every correct stale-bot note into a finding.
EXEMPT = re.compile(
    r"\b(stale[- ]bot|inactivity|autoclose[d]?|auto-closed|NOT_PLANNED|"
    r"treat as (still )?(open|live)|not confirmed fixed|closed .{0,20}not fixed|"
    r"live risk)\b",
    re.I,
)


def resolve(refs, batch=40):
    """{(owner, repo, num): (kind, state, title)} via batched GraphQL."""
    out, refs = {}, sorted(refs)
    for i in range(0, len(refs), batch):
        chunk = refs[i : i + batch]
        q = (
            "query { "
            + " ".join(
                f'a{j}: repository(owner:"{o}", name:"{r}") {{ '
                f"issueOrPullRequest(number:{n}) {{ __typename "
                f"... on Issue {{ state title }} "
                f"... on PullRequest {{ state title merged }} }} }}"
                for j, (o, r, n) in enumerate(chunk)
            )
            + " }"
        )
        p = subprocess.run(
            ["gh", "api", "graphql", "-f", "query=" + q], capture_output=True, text=True
        )
        if p.returncode != 0:
            print(
                f"  ! batch {i // batch} failed: {p.stderr.strip()[:200]}",
                file=sys.stderr,
            )
            continue
        data = json.loads(p.stdout).get("data") or {}
        for j, ref in enumerate(chunk):
            node = (data.get(f"a{j}") or {}).get("issueOrPullRequest")
            if not node:
                continue
            kind = "pr" if node["__typename"] == "PullRequest" else "issue"
            state = node["state"]
            if kind == "pr" and node.get("merged"):
                state = "MERGED"
            out[ref] = (kind, state, node.get("title") or "")
    return out


def classify(text, kind, state):
    """The claim class this line makes about a ref in `state`, or None."""
    if EXEMPT.search(text):
        return None
    if SAYS_OPEN.search(text) and state in ("CLOSED", "MERGED"):
        return f"A says-open / tracker-{state}"
    if kind == "pr" and SAYS_UNMERGED.search(text) and state == "MERGED":
        return "C says-unmerged / tracker-MERGED"
    if (
        kind == "pr"
        and state == "CLOSED"
        and SAYS_MERGED.search(text)
        and not SAYS_UNMERGED.search(text)
    ):
        return "B says-merged / tracker-CLOSED (closed unmerged)"
    return None


def scan(roots):
    lines, refs = [], set()
    for root in roots:
        for f in sorted(Path(root).rglob("*.md")):
            for ln, text in enumerate(
                f.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                hits = {
                    (m.group(1), m.group(2), int(m.group(4)))
                    for m in RE_URL.finditer(text)
                }
                if hits:
                    lines.append((f, ln, text, hits))
                    refs |= hits
    if not refs:
        print("no issue/PR citations found.")
        return 0

    print(f"resolving {len(refs)} citations across {len(lines)} lines...")
    state = resolve(refs)
    if not state:
        print(
            "NO RESULT — the tracker could not be reached; nothing is reported as clean."
        )
        return 2

    findings, ambiguous = [], []
    for f, ln, text, hits in lines:
        known = {r: state[r] for r in hits if r in state}
        multi = len({v[1] for v in known.values()}) > 1
        for ref, (kind, st, title) in known.items():
            cls = classify(text, kind, st)
            if not cls:
                continue
            row = (
                f,
                ln,
                f"{ref[0]}/{ref[1]}#{ref[2]}",
                cls,
                title[:70],
                text.strip()[:160],
            )
            (ambiguous if multi else findings).append(row)

    def dump(label, rows):
        print(f"\n=== {label}: {len(rows)} ===")
        if not rows:
            print("none.")
        for f, ln, ref, cls, title, text in rows:
            print(f"{f}:{ln}\n  {ref}  [{cls}]  {title}\n  > {text}")

    dump("state claims contradicting the tracker", findings)
    dump("AMBIGUOUS — line cites refs in differing states, decide by hand", ambiguous)
    unresolved = len(refs) - len(state)
    if unresolved:
        print(f"\n{unresolved} citation(s) did not resolve and were NOT checked.")
    return 1 if findings else 0


def selfcheck():
    """Offline. Every case is a real line this sweep met on 2026-09-15."""
    # --- the defects this tool exists for: each must still be caught ---
    caught = [
        (
            "| PR #48290 — enable MRV2 for pooling by default | fresh (still OPEN) | Not merged. |",
            "pr",
            "MERGED",
            "A",
        ),
        (
            "| #22607 PP + HiCache consistency meta | **Still OPEN** (activity 2026-07-10). |",
            "issue",
            "CLOSED",
            "A",
        ),
        (
            "| vLLM issue #39663 | fresh (**still OPEN**, updated 2026-08-06) | Warning kept. |",
            "issue",
            "CLOSED",
            "A",
        ),
        (
            "- #35048 — MiniMax latency +24% — **still OPEN, but marked**. |",
            "issue",
            "CLOSED",
            "A",
        ),
        (
            "A candidate fix (PR #22120) was merged and shipped in v0.5.11.",
            "pr",
            "CLOSED",
            "B",
        ),
        ("PR #27010 was closed unmerged and is not the fix.", "pr", "MERGED", "C"),
    ]
    for text, kind, state, want in caught:
        got = classify(text, kind, state)
        assert got and got.startswith(want), f"MISSED {want}: {text!r} -> {got}"

    # --- the exemption. Correct stale-bot wording must NOT be condemned. This
    # is the line that decides whether the tool is usable: without it, every
    # honest "closed by the bot, still a live risk" note becomes a finding and
    # the whole report gets ignored.
    exempt = [
        "**Treat as still open** — the stale bot closed it 2026-06-18, no fix.",
        "**CLOSED 2026-07-04 for INACTIVITY, not fixed** — still open in substance.",
        "CLOSED `NOT_PLANNED` 2026-09-02 by the inactivity bot; the warning still stands.",
        "Shows CLOSED/COMPLETED but treat as live risk; no fix yet.",
    ]
    for text in exempt:
        got = classify(text, "issue", "CLOSED")
        assert got is None, f"FALSE POSITIVE on deliberate wording: {text!r} -> {got}"

    # --- agreement is silence ---
    assert (
        classify("#30760 is still open, candidate PR unmerged.", "issue", "OPEN")
        is None
    )
    assert (
        classify("PR #27010 merged 2026-08-25, first tag v0.5.19.", "pr", "MERGED")
        is None
    )
    assert classify("PR #40041 is still open and unmerged.", "pr", "OPEN") is None

    # --- the URL regex must find both kinds, and not over-match ---
    u = "https://" + "github.com/o/r/pull/12 and https://" + "github.com/a/b/issues/7"
    assert {
        (m.group(1), m.group(2), m.group(3), int(m.group(4)))
        for m in RE_URL.finditer(u)
    } == {("o", "r", "pull", 12), ("a", "b", "issues", 7)}
    assert not RE_URL.search("https://" + "github.com/o/r/commit/abc123")

    print("selfcheck OK — 6 real defects caught, 4 deliberate phrasings exempt")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--selfcheck"]
    if "--selfcheck" in sys.argv[1:]:
        sys.exit(selfcheck())
    sys.exit(scan(args or [".claude/skills"]))
