#!/usr/bin/env python3
"""Induced-cost probe: what the skill costs to OBEY, not what it costs to load.

Every other cost signal in this rubric measures the skill's text -- Dim 2 counts
lines, Dim 6 counts scaffolding. None of them sees the bill the skill runs up at
execution time. A 90-line skill that says "read every reference before you
start", fans out uncapped subagents, and pins `effort: xhigh` is cheap to load
and expensive to obey; it scores well on both text dimensions today.

Four triggers, all STRUCTURAL. None of them judges whether prose "feels
wasteful" -- SkillLens (arXiv:2605.23899) clocked that judgment at 46.4%, worse
than chance, so this probe only reports things a regex can point at:

  1. effort-pin      frontmatter `effort:` at high/xhigh/max on a multi-mode
                     skill -- the pin overrides the session on every
                     invocation, cheap modes included
  2. eager-read      an unconditional "read all references first" where the
                     skill's own structure shows only one branch needs them
  3. uncapped-fanout spawn/subagent/parallel instructions with no agent-count
                     cap anywhere near them
  4. over-obedience  "verify twice" / "be maximally thorough" / "investigate
                     fully even when..." -- instructions a current model
                     follows too literally

Trigger 4 is the priced one. On Anthropic's support-desk evaluation, removing
"verify twice" cut cost per ticket by a THIRD with no accuracy change, and the
same page states these patterns "appear in tool descriptions and skills, and are
worth removing there too" (see references/quality-rubric.md, Boris section).

THE CAP IS TWO-SIDED. Leaner is not automatically cheaper: a skill trimmed until
it is vague makes the agent flail, and re-derived context costs more than the
text it saved. This probe deliberately has no "too short" trigger -- Dim 5
(Completeness) is that brake, and a hit here never justifies a cut that drops
scope the description promises.

Usage:
    induced-cost-probe.py [SKILL.md] [--refs] [--verbose] [--json]

Exit status is 1 when any trigger fires, 0 when clean -- so it composes into a
batch sweep the way scaffold-probe.py does.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FENCE_RE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN_RE = re.compile(r"`[^`]*`")
# Mention vs use. A rubric that *discusses* these patterns quotes them --
# `removing "verify twice" cut cost by a third` is analysis, not an instruction
# to verify twice. Quoting is the reliable signal for mention in this corpus:
# instructions are written as bare imperatives, never in quotation marks.
QUOTED_RE = re.compile(r"\"[^\"]{0,120}\"|“[^”]{0,120}”|'[^']{2,120}'")
# Table rows are reference material -- a source inventory, a discriminator's
# example column -- not the skill's own instructions to itself.
TABLE_ROW_RE = re.compile(r"^\s*\|")


def strip_mentions(text: str) -> str:
    """Remove code spans and quoted spans; blank out table rows entirely."""
    if TABLE_ROW_RE.match(text):
        return ""
    return QUOTED_RE.sub(" ", CODE_SPAN_RE.sub(" ", text))


# --- 1. effort pin -----------------------------------------------------------
EFFORT_RE = re.compile(r"^\s*effort\s*:\s*[\"']?(high|xhigh|max)[\"']?\s*$", re.I)
# A skill is multi-mode when it advertises alternatives the caller picks
# between: `mode` in argument-hint, a pipe-separated mode list, or 2+ headings
# that name a mode.
MODE_HEADING_RE = re.compile(r"^#{2,4}\s+.*\bmode\b", re.I)
ARGHINT_MODE_RE = re.compile(r"^\s*argument-hint\s*:.*\b(mode|\|)", re.I)

# --- 2. eager read -----------------------------------------------------------
# Imperative + universal quantifier + read verb, with no conditional in the
# sentence. "Read the rubric when scoring" is fine; "Read every reference
# before starting" is the trigger.
# "load" is dropped from the verb set on purpose: "permanent context load" and
# "load-bearing" are nouns, and they sit next to the same quantifiers. The four
# remaining verbs are unambiguous imperatives in this corpus.
EAGER_READ_RE = re.compile(
    r"\b(read|re-read|open|ingest)\b[^.\n]{0,40}\b"
    r"(all|every|each|entire|whole|complete)\b[^.\n]{0,40}"
    r"\b(reference|file|doc|documentation|directory|subdir|skill)",
    re.I,
)
# A read is SCOPED when something in the sentence says *which* read happens
# *when*. Progressive disclosure phrases it as point-of-use ("read each
# reference at its question", "read the one for the mode you are in"), which is
# the pattern this probe must not punish -- it is the fix, not the defect.
CONDITIONAL_RE = re.compile(
    r"\b(if|when|unless|only|where|should you|in case|for the mode|"
    r"whichever|as needed|on demand|relevant|at its|at the point|"
    r"per (?:question|section|step|phase|mode)|as you (?:reach|hit|get)|"
    r"that (?:applies|matches|covers)|the one for)\b",
    re.I,
)

# --- 3. uncapped fan-out -----------------------------------------------------
# Narrow on purpose. An earlier version matched any mention of "subagent" and
# fired 16-27 times on skills whose text says "Cap at 10 concurrent" three
# lines away -- a detector that fires on two thirds of a fleet is a constant,
# not a diagnostic (the same 61%-vs-31% argument the rubric makes about raw
# numbered-item counting). Only an IMPERATIVE to spawn counts, and the cap is
# looked for file-wide: stating the cap once is stating it.
FANOUT_RE = re.compile(
    r"\b(spawn|launch|fan out|fan-out)\b[^.\n]{0,60}"
    r"\b(agent|subagent|task|reviewer|scorer|worker|verifier|per )\b"
    r"|\bone (agent|subagent|task|reviewer|scorer|verifier) per\b"
    r"|\ball .{0,20}\b(in a single message|in one message|in parallel)\b",
    re.I,
)
CAP_RE = re.compile(
    r"\b(cap(?:ped)? (?:at|to)|at most|no more than|max(?:imum)?(?: of)?|"
    r"up to|limit(?:ed)? to|batch(?:es)? of|shard(?:ed)? (?:at|into))\b"
    r"[^.\n]{0,24}\d"
    r"|\d[^.\n]{0,24}\b(concurrent|at a time|in flight|per wave|per batch|max)\b"
    r"|\bconcurrent\w*\b[^.\n]{0,24}\d"
    r"|\bbudget the fan-?out\b",
    re.I,
)

# --- 4. over-obedience -------------------------------------------------------
OVER_OBEDIENCE = [
    (r"\bverify twice\b|\bdouble-?check (?:everything|every|twice)\b", "verify-twice"),
    (
        r"\b(be |stay )?maximally (thorough|complete|detailed|comprehensive)\b",
        "maximally-X",
    ),
    # `exhaustive` alone is often a MODE NAME ("Exhaustive | 12+ agents") rather
    # than an instruction. Require it to modify an action, or be the adverb.
    (
        r"\binvestigate fully\b|\bexhaustively\b|\bleave no stone\b"
        r"|\b(be|being|stay) exhaustive\b"
        r"|\ban? exhaustive (search|review|sweep|analysis|read|pass)\b",
        "exhaustive",
    ),
    (r"\bre-?read the (entire|whole|full)\b", "reread-entire"),
    (r"\balways (double-?check|re-?verify|re-?read|confirm again)\b", "always-recheck"),
    (
        r"\beven when (?:the |it |they )?\w+ (?:looks?|seems?|appears?) (?:simple|trivial|obvious|fine)\b",
        "no-early-exit",
    ),
]
OVER_OBEDIENCE_RE = [(re.compile(p, re.I), name) for p, name in OVER_OBEDIENCE]
# A negated form is the opposite instruction. "This list is not meant to be
# exhaustive" disclaims coverage; flagging it inverts the trigger's meaning.
NEGATED_RE = re.compile(
    r"\b(not|never|isn't|is not|aren't|are not|no need to|rather than|"
    r"instead of|non-)\b[^.\n]{0,40}"
    r"\b(exhaustive\w*|maximally|verify twice|thorough)\b",
    re.I,
)


class Hit:
    def __init__(self, trigger: str, lineno: int, text: str, detail: str = "") -> None:
        self.trigger = trigger
        self.lineno = lineno
        self.text = text.strip()[:100]
        self.detail = detail

    def as_dict(self) -> dict:
        return {
            "trigger": self.trigger,
            "line": self.lineno,
            "text": self.text,
            "detail": self.detail,
        }


def read_lines(path: Path) -> list[tuple[int, str, bool]]:
    """(lineno, text, in_frontmatter). Fenced code is dropped: it holds
    examples and command syntax, not instructions the model obeys."""
    out: list[tuple[int, str, bool]] = []
    in_fence = False
    in_fm = False
    fm_done = False
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if raw.strip() == "---" and not fm_done:
            if not in_fm and lineno <= 3:
                in_fm = True
                continue
            if in_fm:
                in_fm = False
                fm_done = True
                continue
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        out.append((lineno, raw, in_fm))
    return out


def probe(path: Path, verbose: bool, cap_corpus: str = "") -> tuple[list[Hit], dict]:
    lines = read_lines(path)
    body = [(n, t) for n, t, fm in lines if not fm]
    fm = [(n, t) for n, t, is_fm in lines if is_fm]
    hits: list[Hit] = []

    # 1. effort pin, only when the skill has cheap modes to be pinned over.
    effort = [(n, t) for n, t in fm if EFFORT_RE.match(t)]
    multi_mode = sum(1 for _, t in body if MODE_HEADING_RE.match(t)) >= 2 or any(
        ARGHINT_MODE_RE.match(t) for _, t in fm
    )
    for n, t in effort:
        if multi_mode:
            hits.append(
                Hit(
                    "effort-pin",
                    n,
                    t,
                    "pins effort over every mode, cheap ones included",
                )
            )

    # 2. eager read without a conditional in the same line.
    for n, t in body:
        clean = strip_mentions(t)
        if EAGER_READ_RE.search(clean) and not CONDITIONAL_RE.search(clean):
            hits.append(Hit("eager-read", n, t, "no conditional scopes the read"))

    # 3. fan-out with no cap stated ANYWHERE in the file. One hit per file:
    # the defect is "this skill never bounds its fan-out", which is a single
    # fact about the skill, not one fact per sentence that mentions agents.
    fanout_lines = [(n, t) for n, t in body if FANOUT_RE.search(strip_mentions(t))]
    if fanout_lines:
        # The cap may legitimately be stated in a table row or a quoted
        # example, so scan the unstripped text when looking for it: a cap
        # anywhere is a cap, and missing one produces a false POSITIVE.
        # `cap_corpus` widens that search to the WHOLE SKILL. Fan-out policy is
        # stated once, in SKILL.md; a reference file carrying the per-spawn
        # tail is not uncapped just because it does not restate the number.
        whole = " ".join(CODE_SPAN_RE.sub(" ", t) for _, t in body) + " " + cap_corpus
        if not CAP_RE.search(whole):
            n, t = fanout_lines[0]
            hits.append(
                Hit(
                    "uncapped-fanout",
                    n,
                    t,
                    f"{len(fanout_lines)} fan-out instruction(s), "
                    "no agent-count cap anywhere in the file",
                )
            )

    # 4. over-obedience phrasing.
    for n, t in body:
        clean = strip_mentions(t)
        if NEGATED_RE.search(clean):
            continue
        for pat, name in OVER_OBEDIENCE_RE:
            if pat.search(clean):
                hits.append(Hit("over-obedience", n, t, name))
                break

    stats = {
        "file": str(path),
        "multi_mode": multi_mode,
        "hits": len(hits),
        "by_trigger": {
            k: sum(1 for h in hits if h.trigger == k)
            for k in ("effort-pin", "eager-read", "uncapped-fanout", "over-obedience")
        },
    }
    return hits, stats


def report(path: Path, hits: list[Hit], stats: dict, *, verbose: bool) -> None:
    print(f"{path}")
    for k, v in stats["by_trigger"].items():
        print(f"  {k:<16}: {v}")
    if verbose:
        for h in hits:
            print(f"    L{h.lineno} [{h.trigger}/{h.detail}]: {h.text}")
    if hits:
        print(
            f"  VERDICT: Dim 6 capped at 6 — {len(hits)} induced-cost trigger(s). "
            "Fix the trigger, not the length: Dim 5 still holds the floor."
        )
    else:
        print("  VERDICT: clean — no induced-cost cap")


# Positive and negative cases per trigger. A structural detector is only worth
# its cap if it is shown to fire on the shape it names AND stay quiet on the
# near-miss that shares its vocabulary -- the near-misses below are all real
# text from this fleet that an earlier, looser version of this probe flagged.
SELFTEST: list[tuple[str, str, bool, str]] = [
    # (trigger, text, should_fire, why)
    (
        "eager-read",
        "Read all reference files before you begin.",
        True,
        "unconditional read of everything",
    ),
    (
        "eager-read",
        "Read every doc in the directory first.",
        True,
        "same shape, different wording",
    ),
    (
        "eager-read",
        "Read each reference file at its question.",
        False,
        "point-of-use = progressive disclosure, the fix not the defect",
    ),
    (
        "eager-read",
        "Read the rubric when scoring a dimension.",
        False,
        "conditional scopes it",
    ),
    (
        "eager-read",
        "permanent context load — every installed skill's description",
        False,
        "'load' as a noun; the verb set excludes it for exactly this line",
    ),
    (
        "uncapped-fanout",
        "Spawn one subagent per focus area, all in one message.",
        True,
        "fan-out imperative with no cap in the file",
    ),
    (
        "uncapped-fanout",
        "Spawn one subagent per focus area. Cap at 10 concurrent.",
        False,
        "cap stated",
    ),
    (
        "uncapped-fanout",
        "20 subagents in flight at once is the ceiling.",
        False,
        "cap stated in the in-flight idiom",
    ),
    (
        "over-obedience",
        "After each edit, verify twice before continuing.",
        True,
        "the priced pattern: -1/3 cost when removed",
    ),
    (
        "over-obedience",
        "Be maximally thorough in your review.",
        True,
        "unbounded effort instruction",
    ),
    (
        "over-obedience",
        "Search exhaustively for call sites.",
        True,
        "adverb form is an instruction",
    ),
    (
        "over-obedience",
        "| Exhaustive | 12+ | 4 | Literature reviews |",
        False,
        "mode-name label in a table, not an instruction",
    ),
    (
        "over-obedience",
        'removing "verify twice" cut cost per ticket by a third',
        False,
        "mention, not use: the rubric discussing the pattern it bans",
    ),
    (
        "over-obedience",
        '| Cost page | url | ...prompt audit, "verify twice"... |',
        False,
        "a sources.md row inventorying the evidence",
    ),
    (
        "eager-read",
        '| **Scaffold** | "Read the target skill\'s entire directory." | Yes |',
        False,
        "the discriminator table quoting its own example",
    ),
    (
        "over-obedience",
        "This list is not meant to be exhaustive.",
        False,
        "negated form disclaims coverage; flagging it inverts the trigger",
    ),
    (
        "over-obedience",
        "Investigate fully even when the ticket looks simple.",
        True,
        "no-early-exit, forces tool calls on trivial input",
    ),
]


def selftest() -> int:
    """Assert each trigger fires on its shape and stays quiet on the near-miss."""
    failures = 0
    print("induced-cost-probe self-test")
    for trigger, text, should_fire, why in SELFTEST:
        clean = strip_mentions(text)
        if trigger == "eager-read":
            fired = bool(EAGER_READ_RE.search(clean)) and not CONDITIONAL_RE.search(
                clean
            )
        elif trigger == "uncapped-fanout":
            fired = bool(FANOUT_RE.search(clean)) and not CAP_RE.search(clean)
        elif trigger == "over-obedience":
            fired = not NEGATED_RE.search(clean) and any(
                pat.search(clean) for pat, _ in OVER_OBEDIENCE_RE
            )
        else:
            fired = bool(EFFORT_RE.match(clean))
        ok = fired == should_fire
        failures += 0 if ok else 1
        mark = "ok  " if ok else "FAIL"
        want = "fire" if should_fire else "quiet"
        print(f"  {mark} {trigger:<16} expect {want:<5} — {why}")
        if not ok:
            print(f"       text: {text}")
    print(f"  {len(SELFTEST) - failures}/{len(SELFTEST)} cases pass")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("skill", nargs="?", default="SKILL.md", type=Path)
    ap.add_argument(
        "--selftest",
        action="store_true",
        help="check each trigger fires on its shape and not on near-misses",
    )
    ap.add_argument("--refs", action="store_true", help="also probe references/*.md")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.skill.exists():
        print(f"error: {args.skill} not found", file=sys.stderr)
        return 2

    targets = [args.skill]
    if args.refs:
        targets += sorted((args.skill.parent / "references").glob("*.md"))

    # Build the cap corpus once from every file in the skill, so a fan-out cap
    # stated in SKILL.md covers the reference files that carry the spawn tails.
    cap_corpus = " ".join(
        t.read_text(encoding="utf-8", errors="replace")
        for t in [args.skill] + sorted((args.skill.parent / "references").glob("*.md"))
        if t.exists()
    )

    payload = []
    total = 0
    for target in targets:
        hits, stats = probe(target, args.verbose, cap_corpus)
        total += len(hits)
        if args.json:
            payload.append({**stats, "detail": [h.as_dict() for h in hits]})
        else:
            report(target, hits, stats, verbose=args.verbose)

    if args.json:
        print(json.dumps(payload, indent=2))

    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
