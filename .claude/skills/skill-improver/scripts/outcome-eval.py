#!/usr/bin/env python3
"""Measure whether a skill helps a model do its tasks, with `claude plugin eval`.

Converts the skill's `evals/evals.json` (skill-creator format: prompt +
assertions) into plugin-eval cases, wraps the skill in a throwaway plugin under
`mktemp -d`, and runs every case with the skill and without it. With
`--against <git-ref|dir>` it also runs the other version of the skill (skill arm
only) and prints the three side by side.

Each assertion is one LLM grader, so a run scores the fraction of assertions it
passed. A run that errored is NO SCORE: excluded, never counted as 0.

By default every prompt starts with "Use the <name> skill for this." so the
measurement is about the skill's content, not its triggering (trigger mode
measures that). `--natural` drops the line.

    outcome-eval.py <skill-dir> [--against REF|DIR] [--runs 3] [--case GLOB]
        [--model sonnet] [--judge-model M] [--with-only] [--max-cost-usd 20]
        [--write-benchmark] [--natural]
    outcome-eval.py --selfcheck

Runs keep their logs (`--keep-temp`, ~140 KB each under /tmp), and the script
reads them for what the test cost: tokens per model for the answering runs
(grader calls excluded), and the plan's 5-hour and weekly usage before the first
run and after the last, from each log's `rate_limit_event`. Plan usage is whole
percents, includes anything else using the plan meanwhile, and is absent for
API-key logins.

`--write-benchmark` writes `evals/benchmark.plugin-eval.json` with
`with_skill` / `without_skill` pass rates, which `eval-evidence.py` reads for the
Dim 10 gate.
"""

import argparse
import fnmatch
import hashlib
import json
import shutil
import statistics as st
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_content import content_hash  # noqa: E402

HEAD = "---\nmax_turns: 20\ntimeout_seconds: 600\nallowed_tools: [Read, Glob, Grep, Skill]\n---\n\n"


def build_plugin(skill: Path, evals: list, name: str, natural: bool) -> Path:
    root = Path(tempfile.mkdtemp(prefix=f"outcome-eval-{name}."))
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(
            {"name": "outcome-eval", "version": "0.0.1", "description": "outcome eval"}
        )
    )
    # evals/ is excluded: it holds the assertions the run is graded on.
    shutil.copytree(
        skill, root / "skills" / name, ignore=shutil.ignore_patterns("evals")
    )
    lead = "" if natural else f"Use the {name} skill for this.\n\n"
    for e in evals:
        d = root / "evals" / f"{e['id']:02d}-{e['name']}"
        (d / "graders").mkdir(parents=True)
        (d / "prompt.md").write_text(HEAD + lead + e["prompt"] + "\n")
        for i, a in enumerate(e["assertions"]):
            text = a if isinstance(a, str) else a.get("text") or json.dumps(a)
            (d / "graders" / f"a{i}.md").write_text(
                "---\ntype: llm\nweight: 1\n---\n\nPASS only if this holds for the final answer: "
                + text
                + "\nJudge content only; ignore formatting and extra correct detail.\n"
            )
        (d / "graders" / "skill.md").write_text(
            "---\ntype: tool_used\ntool: Skill\n---\n"
        )
    return root


def run(plugin: Path, out: Path, a, ablation: str) -> dict:
    cmd = [
        "claude",
        "plugin",
        "eval",
        str(plugin),
        "--trust-plugin",
        "--no-publish",
        "--model",
        a.model,
        "--judge-model",
        a.judge_model,
        "-j",
        str(a.jobs),
        "--threshold",
        "0",
        "--max-cost-usd",
        str(a.max_cost_usd),
        "--runs",
        str(a.runs),
        "--ablation",
        ablation,
        "--keep-temp",
        "--json",
        str(out),
    ]
    print("running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=False)
    return json.loads(out.read_text())


def run_scores(result: dict, arm: str) -> dict:
    """{case: [score or None per run]} — score = fraction of assertion graders passed."""
    out = {}
    for c in result["cases"]:
        for r in c["arms"].get(arm, []):
            gs = [
                g
                for g in r["graders"]
                if g["name"].startswith("a")
                and g["name"][1:].isdigit()
                # A grader whose judge call failed measured nothing: NO SCORE, not FAIL.
                and not str(g.get("explanation") or "").startswith("grader threw")
            ]
            score = (
                None
                if r.get("error") or not gs
                else sum(g["passed"] for g in gs) / len(gs)
            )
            out.setdefault(c["name"], []).append(
                (
                    score,
                    r["costUsd"],
                    any(g["name"] == "skill" and g["passed"] for g in r["graders"]),
                )
            )
    return out


def run_usage(results: list) -> tuple[dict, list, int]:
    """Read every run's kept log: ({model: [in, out, cache_read, cache_write]},
    [(startedAt, unifiedWindows)], runs whose log is missing)."""
    tokens: dict = {}
    windows = []
    missing = 0
    for res in results:
        for c in res["cases"]:
            for runs in c["arms"].values():
                for r in runs:
                    p = Path(r.get("tracePath") or "")
                    if not p.is_file():
                        missing += 1
                        continue
                    last = None
                    for line in p.read_text(errors="replace").splitlines():
                        try:
                            e = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if e.get("type") == "rate_limit_event":
                            last = (e.get("rate_limit_info") or {}).get(
                                "unifiedWindows"
                            ) or last
                        elif e.get("type") == "result":
                            for m, u in (e.get("modelUsage") or {}).items():
                                t = tokens.setdefault(m, [0, 0, 0, 0])
                                for i, k in enumerate(
                                    (
                                        "inputTokens",
                                        "outputTokens",
                                        "cacheReadInputTokens",
                                        "cacheCreationInputTokens",
                                    )
                                ):
                                    t[i] += u.get(k) or 0
                    if last:
                        windows.append((r.get("startedAt") or "", last))
    return tokens, windows, missing


def usage_text(tokens: dict, windows: list, missing: int) -> str:
    total = sum(sum(v) for v in tokens.values())
    parts = ", ".join(
        f"{m} {sum(v) / 1e6:.2f}M (out {v[1] / 1e3:.0f}K)"
        for m, v in sorted(tokens.items(), key=lambda x: -sum(x[1]))
    )
    lines = [
        f"tokens, answering runs only: {total / 1e6:.2f}M — {parts or 'none read'}"
    ]
    if missing:
        lines.append(f"  {missing} run log(s) missing: their tokens are NOT counted")
    if not windows:
        lines.append("plan usage: not reported (API-key login, or no run logs)")
        return "\n".join(lines)
    windows.sort(key=lambda w: w[0])
    first, last = windows[0][1], windows[-1][1]
    cells = []
    for key, label in (("seven_day", "week"), ("five_hour", "5-hour window")):
        a, b = first.get(key) or {}, last.get(key) or {}
        if "utilization" not in a or "utilization" not in b:
            continue
        u0, u1 = round(a["utilization"] * 100), round(b["utilization"] * 100)
        note = (
            " (window reset during the test; not comparable)"
            if a.get("resetsAt") != b.get("resetsAt")
            else ""
        )
        cells.append(f"{label} {u0}% -> {u1}% ({u1 - u0:+d}){note}")
    lines.append(
        "plan usage: "
        + "; ".join(cells)
        + " — whole percents, includes other use of the plan meanwhile"
    )
    return "\n".join(lines)


def case_key(e: dict) -> str:
    return f"{e['id']:02d}-{e['name']}"


def baseline_id(e: dict, model: str, judge: str) -> str:
    """Changes whenever a stored without-skill score for this case stops being
    comparable: the case text, the answering model or the judge changed."""
    blob = json.dumps([e, model, judge], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def stored_baselines(
    stamp: dict, evals: list, model: str, judge: str
) -> tuple[dict, list]:
    """({case: stored entry}, [cases with no usable stored score])."""
    have, missing = {}, []
    for e in evals:
        b = (stamp.get("baselines") or {}).get(case_key(e))
        if b and b.get("id") == baseline_id(e, model, judge):
            have[case_key(e)] = b
        else:
            missing.append(case_key(e))
    return have, missing


def weak_names(
    result: dict, floor: float = 0.7, stored: dict | None = None
) -> list[str]:
    """Names of cases where the skill scores under `floor` or below the
    without-skill score (measured, else stored)."""
    out = []
    for c in result["cases"]:
        means = {}
        for arm in ("with", "without"):
            sc = [s for s, _, _ in run_scores({"cases": [c]}, arm).get(c["name"], [])]
            sc = [s for s in sc if s is not None]
            means[arm] = st.mean(sc) if sc else None
        w, wo = means["with"], means["without"]
        if wo is None and stored and c["name"] in stored:
            wo = stored[c["name"]]["score"]
        if w is not None and (w < floor or (wo is not None and w < wo)):
            out.append(c["name"])
    return out


def weak_cases(
    result: dict, evals: list, floor: float = 0.7, stored: dict | None = None
) -> list[str]:
    """Cases where the skill loses to the without arm or scores under `floor`,
    with each failing assertion and how many runs failed it. `stored` supplies
    without-skill scores when this run had no without arm."""
    texts = {f"{e['id']:02d}-{e['name']}": e["assertions"] for e in evals}
    out = []
    for c in result["cases"]:

        def mean(arm):
            sc = [
                s
                for s, _, _ in run_scores({"cases": [c]}, arm).get(c["name"], [])
                if s is not None
            ]
            return st.mean(sc) if sc else None

        w, wo = mean("with"), mean("without")
        if wo is None and stored and c["name"] in stored:
            wo = stored[c["name"]]["score"]
        if w is None or not (w < floor or (wo is not None and w < wo)):
            continue
        fails: dict = {}
        for r in c["arms"].get("with", []):
            for g in r["graders"]:
                if (
                    g["name"][1:].isdigit()
                    and g["name"].startswith("a")
                    and not g["passed"]
                ):
                    fails[int(g["name"][1:])] = fails.get(int(g["name"][1:]), 0) + 1
        out.append(
            f"{c['name']}: skill {w:.2f} vs without {'-' if wo is None else f'{wo:.2f}'}"
        )
        for i, n in sorted(fails.items()):
            a = texts.get(c["name"], [""] * (i + 1))[i]
            a = a if isinstance(a, str) else json.dumps(a)
            out.append(f"  failed {n}x: {a[:160]}")
    return out


def summarize(cols: dict) -> tuple[str, dict]:
    """cols: {label: {case: [(score, cost, fired)]}} -> (table text, {label: mean pass rate})."""
    labels = list(cols)
    cases = sorted({c for col in cols.values() for c in col})
    lines = ["case".ljust(40) + "".join(f"{lab:>12}" for lab in labels)]
    means = {}
    for case in cases:
        cells = []
        for lab in labels:
            sc = [s for s, _, _ in cols[lab].get(case, []) if s is not None]
            cells.append(f"{st.mean(sc):12.2f}" if sc else f"{'NO SCORE':>12}")
        lines.append(case[:40].ljust(40) + "".join(cells))
    for lab in labels:
        runs = [x for v in cols[lab].values() for x in v]
        sc = [s for s, _, _ in runs if s is not None]
        means[lab] = st.mean(sc) if sc else None
        lines.append(
            f"{lab}: pass {means[lab] if means[lab] is None else round(means[lab], 3)}  "
            f"runs {len(sc)}/{len(runs)} scored  cost/run ${st.mean(c for _, c, _ in runs) if runs else 0:.3f}  "
            f"skill fired {sum(f for _, _, f in runs)}/{len(runs)}"
        )
    return "\n".join(lines), means


def selfcheck() -> int:
    cols = {
        "with": {"x": [(1.0, 0.1, True), (None, 0.1, False)]},
        "without": {"x": [(0.0, 0.05, False), (0.5, 0.05, False)]},
    }
    text, means = summarize(cols)
    assert means == {"with": 1.0, "without": 0.25}, means  # errored run excluded, not 0
    assert "runs 1/2 scored" in text
    fake = {
        "cases": [
            {
                "name": "x",
                "arms": {
                    "with": [
                        {
                            "error": None,
                            "costUsd": 0.1,
                            "graders": [
                                {"name": "a0", "passed": True},
                                {"name": "a1", "passed": False},
                                {"name": "skill", "passed": True},
                            ],
                        }
                    ]
                },
            }
        ]
    }
    assert run_scores(fake, "with") == {"x": [(0.5, 0.1, True)]}
    threw = {
        "cases": [
            {
                "name": "x",
                "arms": {
                    "with": [
                        {
                            "error": None,
                            "costUsd": 0.1,
                            "graders": [
                                {
                                    "name": "a0",
                                    "passed": False,
                                    "explanation": "grader threw: judge call failed: API Error",
                                }
                            ],
                        }
                    ]
                },
            }
        ]
    }
    assert run_scores(threw, "with") == {
        "x": [(None, 0.1, False)]
    }  # judge failure is NO SCORE
    weak_res = {
        "cases": [
            {
                "name": "00-x",
                "arms": {
                    "with": [
                        {
                            "error": None,
                            "costUsd": 0,
                            "graders": [
                                {"name": "a0", "passed": False},
                                {"name": "a1", "passed": True},
                            ],
                        }
                    ],
                    "without": [
                        {
                            "error": None,
                            "costUsd": 0,
                            "graders": [
                                {"name": "a0", "passed": True},
                                {"name": "a1", "passed": True},
                            ],
                        }
                    ],
                },
            }
        ]
    }
    w = weak_cases(
        weak_res, [{"id": 0, "name": "x", "assertions": ["names the flag", "ok"]}]
    )
    assert (
        w[0].startswith("00-x: skill 0.50 vs without 1.00")
        and "failed 1x: names the flag" in w[1]
    ), w

    d = Path(tempfile.mkdtemp(prefix="outcome-eval-selfcheck."))

    def trace(name, util, resets, tok):
        p = d / name
        p.write_text(
            "\n".join(
                json.dumps(e)
                for e in (
                    {
                        "type": "rate_limit_event",
                        "rate_limit_info": {
                            "unifiedWindows": {
                                "seven_day": {"utilization": util, "resetsAt": 9},
                                "five_hour": {"utilization": util, "resetsAt": resets},
                            }
                        },
                    },
                    {
                        "type": "result",
                        "modelUsage": {
                            "claude-sonnet-5-5": {
                                "inputTokens": tok,
                                "outputTokens": 1,
                                "cacheReadInputTokens": 0,
                                "cacheCreationInputTokens": 0,
                            }
                        },
                    },
                )
            )
        )
        return str(p)

    res = {
        "cases": [
            {
                "name": "x",
                "arms": {
                    "with": [
                        {
                            "tracePath": trace("b", 0.18, 2, 10),
                            "startedAt": "2026-10-03T02",
                        },
                        {
                            "tracePath": trace("a", 0.16, 1, 5),
                            "startedAt": "2026-10-03T01",
                        },
                        {"tracePath": str(d / "gone"), "startedAt": "2026-10-03T03"},
                    ]
                },
            }
        ]
    }
    tokens, windows, missing = run_usage([res])
    assert tokens == {"claude-sonnet-5-5": [15, 2, 0, 0]} and missing == 1, (
        tokens,
        missing,
    )
    text = usage_text(tokens, windows, missing)
    assert (
        "week 16% -> 18% (+2)" in text
        and "not comparable" in text
        and "1 run log(s) missing" in text
    ), text
    # A stored without-skill score is reused only for the same case text, model
    # and judge; a reworded case or another judge must be measured again.
    e1, e2 = (
        {"id": 1, "name": "a", "prompt": "p"},
        {"id": 2, "name": "b", "prompt": "q"},
    )
    stamp = {
        "baselines": {"01-a": {"score": 0.5, "id": baseline_id(e1, "sonnet", "haiku")}}
    }
    have, missing = stored_baselines(stamp, [e1, e2], "sonnet", "haiku")
    assert list(have) == ["01-a"] and missing == ["02-b"], (have, missing)
    assert stored_baselines(stamp, [e1], "sonnet", "sonnet")[1] == ["01-a"]
    assert stored_baselines(stamp, [dict(e1, prompt="x")], "sonnet", "haiku")[1] == [
        "01-a"
    ]

    # A case is doubted when the skill scores low or below the other arm,
    # measured or stored; a strong case is left alone.
    def arm(*scores):
        return [
            {"graders": [{"name": "a0", "passed": s}], "costUsd": 0} for s in scores
        ]

    doubt = {
        "cases": [
            {
                "name": "low",
                "arms": {"with": arm(True, False, False), "without": arm(False)},
            },
            {
                "name": "loses",
                "arms": {"with": arm(True, True, False), "without": arm(True)},
            },
            {
                "name": "fine",
                "arms": {"with": arm(True, True, True), "without": arm(False)},
            },
            {"name": "one-arm", "arms": {"with": arm(True, True, True)}},
        ]
    }
    assert weak_names(doubt) == ["low", "loses"], weak_names(doubt)
    assert weak_names(doubt, floor=0.5, stored={"one-arm": {"score": 1.0}}) == [
        "low",
        "loses",
    ]
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("skill", nargs="?", type=Path)
    ap.add_argument("--against")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--case", help="comma-separated globs over NN-name, e.g. 03-*,06-*")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument(
        "--judge-model",
        help="Default: sonnet with --write-benchmark, else haiku. A haiku-judged "
        "case that comes out weak is run again under sonnet, which decides it.",
    )
    ap.add_argument(
        "--with-only",
        action="store_true",
        help="Run only the with-skill arm and compare with the without-skill "
        "scores stored in evals/last-run.json. Refused when a selected case has "
        "no stored score for this model, judge and case text.",
    )
    ap.add_argument(
        "--weak-floor",
        type=float,
        default=0.7,
        help="A case scoring under this with the skill counts as weak (default 0.7).",
    )
    ap.add_argument("--max-cost-usd", type=float, default=20)
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--natural", action="store_true")
    ap.add_argument("--write-benchmark", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not a.skill:
        ap.error("skill directory required")
    if not a.judge_model:
        a.judge_model = "sonnet" if a.write_benchmark else "haiku"
    skill = a.skill.resolve()
    name = skill.name
    evals = json.loads((skill / "evals" / "evals.json").read_text())["evals"]
    if a.case:
        # Selected here, not by plugin eval: its --case glob has no [..] classes
        # and silently runs zero cases when nothing matches.
        pats = [p.strip() for p in a.case.split(",") if p.strip()]
        evals = [
            e
            for e in evals
            if any(fnmatch.fnmatch(f"{e['id']:02d}-{e['name']}", p) for p in pats)
        ]
        if not evals:
            ap.error(f"--case {a.case!r} matches no case in evals.json")
    stamp_path = skill / "evals" / "last-run.json"
    try:
        stamp = json.loads(stamp_path.read_text())
    except (OSError, ValueError):
        stamp = {}
    stored: dict = {}
    if a.with_only and (a.write_benchmark or a.against):
        ap.error("--with-only measures one arm; drop --write-benchmark and --against")
    if a.with_only:
        stored, missing = stored_baselines(stamp, evals, a.model, a.judge_model)
        if missing:
            ap.error(
                "--with-only: no stored without-skill score for "
                + ", ".join(missing)
                + f" (model {a.model}, judge {a.judge_model}; a case decided by "
                "the sonnet judge is not reused under haiku). Run these cases once "
                "without --with-only."
            )
    work = Path(tempfile.mkdtemp(prefix=f"outcome-eval-{name}-results."))
    main_res = run(
        build_plugin(skill, evals, name, a.natural),
        work / "current.json",
        a,
        "none" if a.with_only else "with-without",
    )
    cost = main_res["costUsd"]
    results = [main_res]
    judges = {case_key(e): a.judge_model for e in evals}
    doubted = (
        weak_names(main_res, a.weak_floor, stored) if a.judge_model == "haiku" else []
    )
    if doubted:
        # The cheap judge fails long answers that meet a check. A weak case is
        # run again, both arms, and the sonnet-judged result replaces it.
        print(f"second opinion (sonnet judge) on: {', '.join(doubted)}")
        again = run(
            build_plugin(
                skill, [e for e in evals if case_key(e) in doubted], name, a.natural
            ),
            work / "second-opinion.json",
            argparse.Namespace(**{**vars(a), "judge_model": "sonnet"}),
            "with-without",
        )
        redone = {c["name"]: c for c in again["cases"]}
        main_res["cases"] = [redone.get(c["name"], c) for c in main_res["cases"]]
        judges.update(dict.fromkeys(redone, "sonnet"))
        cost += again["costUsd"]
        results.append(again)
    without = run_scores(main_res, "without")  # every case measured in this run
    measured = set(without)
    for k, b in stored.items():
        without.setdefault(k, [(b["score"], 0.0, False)])
    cols = {
        "stored" if a.with_only else "without": without,
        "current": run_scores(main_res, "with"),
    }
    if a.against:
        other = Path(a.against)
        if not other.is_dir():
            other = Path(tempfile.mkdtemp(prefix=f"outcome-eval-{name}-ref."))
            top = subprocess.run(
                ["git", "-C", str(skill), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            rel = skill.relative_to(top)
            arc = subprocess.run(
                ["git", "-C", top, "archive", a.against, "--", str(rel)],
                capture_output=True,
                check=True,
            ).stdout
            subprocess.run(
                ["tar", "-x", "-C", str(other), f"--strip-components={len(rel.parts)}"],
                input=arc,
                check=True,
            )
        ref_res = run(
            build_plugin(other, evals, name, a.natural),
            work / "against.json",
            a,
            "none",
        )
        cols["against"] = run_scores(ref_res, "with")
        results.append(ref_res)
        cost += ref_res["costUsd"]
    text, means = summarize(cols)
    means["without"] = means.pop("stored") if a.with_only else means["without"]
    print(text)
    weak = weak_cases(main_res, evals, a.weak_floor, stored)
    if weak:
        print(f"\nweak cases (answers and grader evidence: {work}/current.json):")
        print("\n".join(weak))
    print(f"API-price estimate ${cost:.2f}; raw results in {work}")
    usage = run_usage(results)
    print(usage_text(*usage))
    resolved = sorted(usage[0])
    baselines = dict(stamp.get("baselines") or {})
    if a.with_only:
        were = sorted({m for b in stored.values() for m in b.get("models", [])})
        if were and were != resolved:
            print(
                f"warning: stored without-skill scores were measured on {were}, this "
                f"run answered on {resolved}. Run once without --with-only before "
                "trusting the comparison."
            )
    for e in evals:
        k = case_key(e)
        sc = [s for s, _, _ in without.get(k, []) if s is not None]
        if k in measured and sc:
            baselines[k] = {
                "score": round(st.mean(sc), 4),
                "id": baseline_id(e, a.model, judges[k]),
                "judge": judges[k],
                "models": resolved,
                "date": date.today().isoformat(),
            }
    if means["current"] is not None and means["without"] is not None:
        # Every measured run leaves a stamp tied to the content it ran against,
        # so a later check can tell whether the skill changed since.
        (skill / "evals" / "last-run.json").write_text(
            json.dumps(
                {
                    "date": date.today().isoformat(),
                    "content_hash": content_hash(skill),
                    "cases": [case_key(e) for e in evals],
                    "runs_per_case": a.runs,
                    "model": a.model,
                    "models_resolved": resolved,
                    "judge_model": a.judge_model,
                    "judges": judges,
                    "with_skill": round(means["current"], 4),
                    "without_skill": round(means["without"], 4),
                    "without_from": "stored" if a.with_only else "this run",
                    "baselines": baselines,
                },
                indent=2,
            )
            + "\n"
        )
        print("wrote evals/last-run.json")
    if (
        a.write_benchmark
        and means["current"] is not None
        and means["without"] is not None
    ):
        (skill / "evals" / "benchmark.plugin-eval.json").write_text(
            json.dumps(
                {
                    "metadata": {
                        "tool": "claude plugin eval via outcome-eval.py",
                        "date": date.today().isoformat(),
                        "model": a.model,
                        # The alias moves with each release; the ids the
                        # answering runs reported are what the numbers rest on.
                        "models_resolved": sorted(usage[0]),
                        "judge_model": a.judge_model,
                        "runs_per_case": a.runs,
                        "cases": len(evals),
                        "forced_invocation": not a.natural,
                    },
                    "run_summary": {
                        "with_skill": {
                            "pass_rate": {"mean": round(means["current"], 4)}
                        },
                        "without_skill": {
                            "pass_rate": {"mean": round(means["without"], 4)}
                        },
                    },
                },
                indent=2,
            )
            + "\n"
        )
        print("wrote evals/benchmark.plugin-eval.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
