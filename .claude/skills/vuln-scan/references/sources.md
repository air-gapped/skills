# sources.md — external references for `vuln-scan` (freshen index)

Freshened: 2026-09-22 — every row probed; all URLs 200 and no cited repo is archived. The Visa harness advanced to v1.4.0 and every cited lineage — the prefilter regexes, the per-chunk threat_id stamp, the specialist hints — still holds verbatim, with call-graph context injection now in s6_verify.py.

One row per external reference this skill depends on. `skill-improver freshen`
probes each URL, classifies staleness, and re-stamps `Last verified:`.

**Freshened: 2026-09-15 — every URL probed and every cited repo checked for archival.** All resolve; none is archived. One URL moved: OWASP's risk-rating methodology now serves from `community.owasp.org`, not `owasp.org/www-community/` — it still returns 200 at the old address, so only the effective URL shows it. Surveys
at use time read this only to surface staleness.

Re-run `/skill-improver freshen vuln-scan` quarterly or when the upstream
security-review tooling changes.

## defending-code reference harness (provenance + execution pipeline)

- URL: https://github.com/anthropics/defending-code-reference-harness
- Probe: `gh repo view anthropics/defending-code-reference-harness --json pushedAt,isArchived`
- Note: the skill is adapted (Apache-2.0) from this repo's `vuln-scan` skill and
  its autonomous `find`/`recon` pipeline prompts. `HARNESS.md` points operators
  here for execution-verified scanning.
- Last verified: 2026-09-15  (active; not archived; **last push 2026-08-06**, up from 2026-07-16).

  **The prompts this skill lifts are unchanged.** `harness/prompts/find_prompt.py`
  appears in a `--since=2026-06-15` commit sweep, but **only** via anthropics/defending-code-reference-harness#13 dated
  2026-06-15 itself — the inclusive-boundary artifact of that filter, and the
  same PR the prior pass already reviewed. `recon_prompt.py` does not appear at
  all, and neither does `.claude/skills/vuln-scan/`. The recon pattern and
  memory-safety tiers are intact (10 tier/recon markers still present in
  `find_prompt.py`). *Use `--since=2026-06-16` next pass to avoid re-reviewing
  the boundary commit.*

  **Changed, and reflected in `HARNESS.md`:**
  - **Declared usage marker on outbound agent API requests** (anthropics/defending-code-reference-harness#22,
    2026-07-11): `harness/auth.py` stamps `anthropic-cyber-runbook: pipeline`
    plus `User-Agent: cyber-runbook/<version> (claude-cli/<version>)` via
    `_with_usage_marker()`. **First-party callers only** — Bedrock/Vertex
    rewrite the `User-Agent`. Operator-visible, so it belongs in the setup
    pointer rather than only in a sources row.
  - **Detection & response track** (2026-07-16): `dnr-pipeline`, `dnrcanary`
    target, `dnr-hunt` / `dnr-respond` skills. The harness is no longer only
    the find-and-fix loop this group was extracted from.
  - `docs/pipeline.md` gained a full CLI flag tree and batch-sizing guidance;
    a Bedrock guardrail now warns on bare model IDs missing an
    inference-profile prefix (2026-07-06).

## claude-code-security-review (category menu + exclusion rules)

- URL: https://github.com/anthropics/claude-code-security-review
- Probe: `gh repo view anthropics/claude-code-security-review --json pushedAt,isArchived`
- Note: the review-brief category menu, DO-NOT-REPORT exclusions, per-finding
  confidence pass, and `exploit_scenario`/`recommendation` fields originate in
  this action's `/security-review` command.
- Last verified: 2026-09-15  (active; not archived; **still last pushed 2026-02-11** — now unchanged for ~7 months, so the category menu, DO-NOT-REPORT exclusions, confidence pass and `exploit_scenario`/`recommendation` fields are stable)

## visa-vulnerability-agentic-harness (Step 3a pre-filter lineage)

- URL: https://github.com/visa/visa-vulnerability-agentic-harness
- Probe: `gh repo view visa/visa-vulnerability-agentic-harness --json pushedAt,isArchived`
- Note: the Step 3a deterministic pre-filter is adapted (Apache-2.0) from this
  repo's s5 stage. v1.5.0 (2026-10-09) split `s5_prefilter.py` into the
  `vvaharness/pipeline/stages/s5/` package: the test-path regex is now
  `EXCLUDE_PATH_RE` and the credential text pattern `SECRET_TEXT_RX`, both in
  `s5/rules.py`, applied by `s5/gates.py`. The regex is unchanged at v1.5.1.
  `s5/gates.py` `reject()` also refuses a finding whose line is outside
  1..len(file) (new in v1.5.0; absent from v1.4.0) — the source of the
  Step 3a `hallucinated_line` gate.
  The "model ignores the prompt rule ~10%" justification for a mechanical
  gate is in the `s5_prefilter.py` docstring through v1.4.0 and was dropped
  in the split. The Step 2 call-graph context block's "starting point, not
  evidence" stance matches `s6/prompts.py` at v1.5.1 ("A missing graph edge
  is NOT by itself a refutation"). Lenses: `SPECIALIST_HINTS`
  (`vvaharness/lang/hints.py`) through v1.4.0, replaced in v1.5.0 by 17
  per-family `vvaharness/skills/<lens>/SKILL.md` files that include the six
  this skill reserves. s3 at v1.5.1 builds one investigation unit per threat
  id (`threat_unit_id`); through v1.4.0 each chunk cited a `threat_id`.
  Checked 2026-10-27 in a local clone at v1.5.1 (`0e6f00d`).

## "Using LLMs to secure source code" (methodology write-up)

- URL: https://claude.com/resources/articles/using-llms-to-secure-source-code
- Probe: bare `curl -sS -L -w '%{url_effective}'` — expect HTTP 200 at this
  URL; the find-and-fix loop framing comes from here. The old
  `claude.com/blog/using-llms-to-secure-source-code` address redirects here
  (seen 2026-10-27).
- The article lays out six steps (threat model, sandbox, discovery,
  verification, triage, patching). "Seven stages" and "reference, not a
  product" are the harness README's words, not the article's.

## Claude Security (managed alternative named in HARNESS.md)

- URL: https://claude.com/product/claude-security
- Probe: bare `curl -sS -L` — expect HTTP 200 and the product still named
  "Claude Security".
- Supports HARNESS.md "Managed alternative": the page says Claude "scans your
  codebase for vulnerabilities, validates findings, and recommends patches";
  "Every finding passes adversarial verification before it reaches your
  team"; projects connect repositories; Claude "marks it fixed once the fix
  ships". The write-up calls it "Anthropic's managed product for agentic
  vulnerability detection and patching."

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
