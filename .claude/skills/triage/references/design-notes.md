# triage design notes

- **Checkpoints are per-phase JSON**, not conversation state. A CLI
  `--resume` restores transcript history but doesn't help when the
  orchestrator's context window itself fills; file-backed checkpoints let a
  brand-new session pick up from the last completed phase. `./.triage-state/`
  is scratch — add to `.gitignore`.
- **Dedupe runs before verify** to cut verifier spend by the duplication
  factor (often 2-4x on multi-scanner input) at the cost of one cheap
  subagent.
- **Semantic dedupe is one agent**, given only id/file/line/category/title
  and the data-flow refs where a scanner supplied them:
  enough to cluster, not enough to leak one scanner's reasoning into
  another finding's verification.
- **Bash is allowed narrowly** for `git log` (owner hints), `jq`/`find`
  (ingest), and `python3 .claude/skills/triage/scripts/checkpoint.py` (state I/O).
  The actual safety property is "no execution of target code," which is
  preserved.
- **`CANNOT_VERIFY`** exists so verifiers aren't forced into a false
  binary. It maps to `needs_manual_test` under recall policy and to a drop
  under precision policy.
- **Threat-model boost is capped at one step** — and gated on the asset
  actually existing — so a stated threat can't re-inflate a LOW back to
  HIGH and defeat the impact x exploitability rule.
- **`severity_label` is separate from `severity`.** Sorting always uses the
  impact x exploitability HIGH/MEDIUM/LOW; the label is presentation-layer
  for whatever standard the reviewer's tooling expects.
- **Pipeline `report.json` ingest is best-effort.** Those reports describe
  ASAN crashes with prose exploitability analysis rather than the
  file/line/category shape static verifiers expect. Expect more
  `needs_manual_test` verdicts on that input than on static-scanner JSON.
- **Sharding at ~40 parallel Agent calls** is a conservative ceiling for typical
  agent-spawn limits; tune up if your runtime allows.
- **No network**, deliberately. CVE-database enrichment and upstream-fix
  checks would help ranking but break the air-gapped-review property.
