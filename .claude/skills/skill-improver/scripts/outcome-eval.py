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
        [--model sonnet] [--judge-model sonnet] [--max-cost-usd 20]
        [--write-benchmark] [--natural]
    outcome-eval.py --selfcheck

`--write-benchmark` writes `evals/benchmark.plugin-eval.json` with
`with_skill` / `without_skill` pass rates, which `eval-evidence.py` reads for the
Dim 10 gate.
"""

import argparse
import json
import shutil
import statistics as st
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

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
        "--json",
        str(out),
    ]
    if a.case:
        cmd += ["--case", a.case]
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
                if g["name"].startswith("a") and g["name"][1:].isdigit()
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
            f"runs {len(sc)}/{len(runs)} scored  cost/run ${st.mean(c for _, c, _ in runs):.3f}  "
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
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("skill", nargs="?", type=Path)
    ap.add_argument("--against")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--case")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--judge-model", default="sonnet")
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
    skill = a.skill.resolve()
    name = skill.name
    evals = json.loads((skill / "evals" / "evals.json").read_text())["evals"]
    work = Path(tempfile.mkdtemp(prefix=f"outcome-eval-{name}-results."))
    main_res = run(
        build_plugin(skill, evals, name, a.natural),
        work / "current.json",
        a,
        "with-without",
    )
    cols = {
        "without": run_scores(main_res, "without"),
        "current": run_scores(main_res, "with"),
    }
    cost = main_res["costUsd"]
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
        cost += ref_res["costUsd"]
    text, means = summarize(cols)
    print(text)
    print(f"total cost ${cost:.2f}; raw results in {work}")
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
