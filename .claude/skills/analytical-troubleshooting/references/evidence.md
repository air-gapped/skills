# Evidence Base

Why each mechanism in this skill is here. Full research report with sources:
`.claude/skills/autoresearch/results/analytical-troubleshooting-skill-research-2026-07-29.md`
(this repo). Summary of the load-bearing findings:

## Provenance of the method

The comparative-specification core (IS/IS-NOT across What/Where/When/Extent,
distinctions and changes, testing causes against the specification,
independent verification) comes from the problem-analysis tradition founded
by Charles Kepner and Benjamin Tregoe (*The Rational Manager*, 1965; *The New
Rational Manager*, 1981). The method is used industrially (ITIL problem
management lists it; 8D's root-cause discipline embeds IS/IS-NOT comparative
analysis; several large support organizations trained on it). This skill is
an original formulation influenced by that tradition — the name
"Kepner-Tregoe" is a trademark of Kepner-Tregoe, Inc., and nothing here
reproduces their materials.

Adjacent sources deliberately blended in: staged diagnostic-strategy ordering
and families-of-variation pruning (quality-engineering literature, de Mast
2013; Steiner/MacKay/Ramberg on the Shainin system), probability÷cost test
sequencing and value-of-information (decision-theoretic troubleshooting,
Breese & Heckerman 1996), half-split doctrine (military maintenance manuals),
one-variable/audit-trail/fix-verification discipline (Agans; Zeller's
scientific debugging and delta debugging), parallel differential with
per-candidate opposing evidence (clinical diagnosis practice).

## Why these mechanisms, specifically

- **Staging (cheap tests first, spec on escalation):** diagnosis science
  orders strategies by expected effort — recognized problems need
  recognition, not analysis; comparative specification pays when the space
  is large, tests are expensive, or cheap guessing has failed. Expected-cost
  math (order by p/c, observe only when information is worth its cost)
  formalizes the fast path; the ~3-failures exit bound formalizes its end.
- **IS-NOT tracking:** LLMs measurably favor confirming tests; forcing a
  hypothesis *and its complement* to be tracked raised rule-discovery
  success substantially in controlled tests (~42%→56%). The IS-NOT column is
  that mechanism made permanent.
- **3–5 parallel mechanism-hypotheses:** anchoring on a single suggested
  cause survives even explicit contradicting evidence in tested models;
  parallel differentials with supporting *and opposing* evidence per
  candidate outperform single-track reasoning in clinical-diagnosis AI.
- **Phase-exit artifacts over exhortation:** models claim procedural
  compliance and then skip steps; verifiable artifacts (a table with every
  cell answered, a numbered hypothesis list, named refutation targets)
  close that gap where prose rules don't.
- **The re-emitted table:** long-context evidence degrades (mid-context
  facts effectively vanish); a maintained, re-printed specification keeps
  live evidence where attention actually lands.
- **Human as sensor / agent as process leader:** the tradition's own
  facilitation doctrine — a non-expert process leader asking the questions
  keeps experts from drowning the analysis in assumptions — maps exactly
  onto the agent/human split, and agent-side evidence fabrication is a
  documented failure mode the `[observed]`-only rule exists to block.
- **Structured method at all:** the best independent trial of structured
  troubleshooting training (navy technicians, Human Factors 2000) roughly
  doubled solve rates in less time vs. conventional training; debiasing
  research finds *scaffolding* (checklists, tables, decision support)
  outperforms trained judgment, which decays in weeks. A skill is
  scaffolding.
- **Two-regime honesty:** cause-hunting is legitimate during live diagnosis
  and misleading as a theory of accidents; resilience-engineering critiques
  of "root cause" apply to post-incident learning, which is why the skill
  hands that regime off instead of claiming it.
- **Expertise caveat:** theory knowledge does not predict troubleshooting
  success; evidence interpretation and strategy-switching do — hence the
  strategy toolkit and the opportunistic staging rather than one rigid
  ladder.
