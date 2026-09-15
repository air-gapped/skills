# Improvement Backlog — skill-improver

Carries ceiling/judgment findings across skill-improver runs. Read in Phase 0;
update in Phase 6. See SKILL.md §"Phase 6: Persist the backlog".

## Resolved — 2026-09-15 (floors a skill already wrote down)

- **Shipped `scripts/check-advisory-floors.py`.** Nothing verified a remediation
  floor after it was written: `freshen` re-probes sources and `advisory-lag.py`
  finds unabsorbed advisories, but a wrong floor already in a skill was invisible
  to both.
- **One real defect, found by hand before the tool existed.** `k8s-components-checker`
  credited CVE-2026-42880 to Argo CD v3.1.15 and v3.0.22; the advisory lists only
  `>= 3.2.0, < 3.2.11` and `>= 3.3.0, < 3.3.9`, neither named release carries a
  security banner, and v3.0.22 shipped three months before the fix. The same file
  stated the correct range four sections above. It survived because both minors are
  EOL, so the verdict — bump — was right for another reason.
- **Two false-negative traps are pinned by assertion.** An unbounded range contains
  every later version, so testing containment before checking for a null
  `first_patched_version` condemns every correctly-derived floor; the selfcheck
  caught that ordering bug before the tool ran. And because each noise filter can
  silence a true defect, the selfcheck replays the shipped Argo CD line verbatim and
  asserts it still comes out condemned.
- **Yield is low on purpose: 7 checkable claims from 104 advisory ids.** A line
  naming several advisories and several versions cannot be resolved by pattern.
  Skipping it is correct; attributing the versions anyway is how a checker invents
  findings. An earlier draft did exactly that and reported 27, of which none was
  real.
- Fleet currently clean: 0 flagged.

## Resolved — 2026-09-15 (dead links outside the staged-commit gate)

- **Shipped `scripts/check-links.py`.** The skillevaluator gate has a dead-link
  check, but it only runs against skills staged for a commit, so a citation in an
  unedited skill rots unobserved. Nothing swept the tree.
- **Two classes carry nearly all the rot.** Of 2573 unique URLs: documentation
  hosts (322 checked, 7 dead) and GitHub `blob`/`tree` paths (189 checked, 4
  dead). GitHub issue/PR/release and arXiv URLs were spot-checked and are stable
  by design — and they are most of the corpus, so sweeping them costs a long run
  for nothing. The tool encodes that as a `DOC_HOSTS` set plus a `blob|tree`
  regex, with `--all` to re-test the judgement later.
- **A moved file is not a renamed repo.** GitHub redirects the second and not the
  first, so all four GitHub findings had to be searched for rather than guessed
  at. One was a docs-to-generated-site migration, which kills every deep link
  into the old tree simultaneously.
- **403 and 429 are printed outside the dead list and do not set the exit code.**
  Treating either as a finding is the failure mode that makes a link sweep waste
  a morning: 403 is a user-agent block (docs.gitlab.com), 429 is this sweep's own
  concurrency (huggingface.co).
- All 11 dead links found by the manual sweep are fixed; the tool now reports 0
  dead across 519 in-class URLs, with the single docs.gitlab.com 403 in its own
  section.

## Resolved — 2026-09-15 (content scheduled to become false)

- **Shipped `scripts/check-expiring-claims.py`.** `freshen` re-probes sources that
  may have drifted; nothing looked for content carrying its own expiry date. 37
  future-dated claims across the fleet, none previously enumerated.
- **The finding is that the date is rarely the problem — the phrase beside it is.**
  A lifecycle table of future EOL dates is correct by design. What decays
  independently is a *relative descriptor* sitting next to a date, so `--relative`
  filters for those. Both `[rel]` hits were real:
  - `rancher-upgrade`: "2.11 goes EOL 2026-10-24 — **roughly three months out**"
    when it was 5½ weeks. The date never became wrong; the sentence around it did,
    in a warning whose entire purpose was the length of the runway.
  - `confluence-best-practices`: "9.2 → 2026-12-10 — **under 5 months away**",
    written 2026-07-21, now ~2.8 months. Still literally true, and understating it.
- **Both fixed by deleting the phrase, not updating it** — a replacement rots the
  same way — and replacing it with an instruction to compute from the date.
  `--relative` now returns **0** on the fleet.
- The non-relative near-term hit was `openshift-app`'s FIPS 140-2 window, 6 days
  from closing with no expiry marker; handled in that skill.
- **Read the output as advisory.** Exit is always 0 and most hits are fine. The
  two signals worth reading are proximity and the `[rel]` tag.

## Resolved — 2026-09-15 (the `no repo feed` follow-up, carried out to the end)

`advisory-lag.py` reports rows whose repo feed returns `[]` as **`no repo feed`**
rather than zero, with an instruction to check them by package against the
ecosystem database. That instruction had never been executed. It has now been,
for every package identity behind those rows.

**Result: 2 real findings out of 27 rows**, both critical-or-high, both invisible
to the repo feed:

| Package | Finding |
|---|---|
| `pip/transformers` | 4 advisories in 2026. The one that mattered: **`save_pretrained` path traversal via chat-template names** (< 5.10.0), plus the discovery that vLLM's dependency pin does not reach the floor clearing all three known fixes. Fixed in `transformers-config-tokenizers-expert` + `vllm-chat-templates`. |
| `pip/sglang` | Two **criticals** (`>= 0.5.5, <= 0.5.12`): a scheduler ROUTER socket binding `0.0.0.0` and unpickling, and an unauthenticated path traversal. Floor **0.5.13**. Fixed in `sglang-hicache`. |

**Checked and genuinely empty** — recorded so this is not re-run on a hunch:
`pip/openai`, `pip/baml-py`, `pip/nixl`, `pip/aiperf`, `pip/cloud-init`,
`pip/vllm-omni`, `pip/aibrix`, `go/github.com/grafana/mimir`,
`go/github.com/zalando/postgres-operator`,
`go/github.com/prometheus/node_exporter`, `go/github.com/ankitpokhrel/jira-cli`.
`pip/lmcache` has one **low** (hash collision, `<= 0.4.6`) which every version
`lmcache-mp` recommends already clears.

**The mapping is the reusable part.** A repo slug is not a package name, and that
is why the follow-up kept being skipped — `huggingface/transformers` →
`pip/transformers` is easy, `sgl-project/sglang` → `pip/sglang` is not obvious,
and several rows (`visa/…-harness`, `NVIDIA/SkillEvaluator`, `beatcracker/toptout`,
`NVIDIA/nvbandwidth`) have **no package identity at all** and cannot be checked
this way. Automating the fallback inside `advisory-lag.py` would need that
mapping as data; it is not derivable from the slug.

**Hit rate worth remembering:** 2 of 27. The marker is not noise — an empty repo
feed hid two criticals and a high — but most of the rows really are empty, so
budget the follow-up as a slow sweep rather than expecting a rich seam.

## Resolved — 2026-09-15 (the same gap in YAML fences)

- **Shipped `scripts/check-yaml-fences.py`**, sibling to the shell checker. 576
  YAML fences across the fleet, none previously parsed by anything.
- **One real bug, in `vllm-deployment/references/multi-node.md`** (twice — leader
  and worker templates): a LeaderWorkerSet env entry written in YAML **flow**
  style with an unquoted `fieldPath`:
  `{fieldRef: {fieldPath: metadata.annotations['leaderworkerset.sigs.k8s.io/leader-address']}}`.
  Flow style forbids `[` and `]` in a plain scalar, so the mapping — and the whole
  manifest — failed to parse. Quoting the value fixes it.
  - **Why it survived review:** in *block* style that exact value is legal, and it
    is how every `fieldRef` in Kubernetes documentation looks. The bug is the flow
    braces, not the value, and the two are far apart on the line.
  - The annotation domain was checked rather than assumed: `leaderworkerset.sigs.k8s.io`
    is correct upstream even though the `apiVersion` is `leaderworkerset.x-k8s.io/v1`.
    Not a typo; no change made there.
- **The only other flagged block was a mislabelled fence** — a whole example
  `SKILL.md` (frontmatter *plus* body, including `` !`gh pr diff` `` dynamic
  injection) fenced as `yaml`. YAML reads a leading `!` as a tag. Re-fenced as
  `markdown`, which is what it is.
- **YAML is in much better shape than shell here** — 1 bug in 576 fences against
  7 in 753. Worth stating so a future pass does not expect a rich seam.
- Count discrepancy noted and resolved rather than papered over: an earlier
  ad-hoc run reported 623 fences. The shipped script and a raw grep of fence
  openers both give **576**, so 576 is what the docstring records.

## Resolved — 2026-09-15 (nothing was checking the inside of a shell fence)

- **Shipped `scripts/check-shell-fences.py`.** `shellcheck` runs on `.sh` files
  and the skillevaluator gate does not parse fenced code, so a broken command in
  skill markdown fails on the reader's machine and nowhere else. 753 fences
  across the fleet had never been parsed.
- **Two passes, because `bash -n` alone would have reported the fleet clean.**
  The bug that motivated this — `cmd \   # note`, where the backslash escapes a
  space and the `#` opens a comment so the next line becomes a separate command —
  leaves the block **syntactically valid**. `bash -n` passes it. It was found by
  grep, and the second pass exists so it stays found.
- **7 occurrences across 4 skills**, each in a copy-pasteable block: the ORAS
  push recipes (argo-cd-apps), the vLLM embedding serve command
  (open-webui-embeddings), the mesh bootstrap (sglang-model-gateway), and all
  three `--config.file` flags (snmp-exporter) — that last one would have run with
  only the first config file rather than failing.
- **The selfcheck asserts the negative**, that `bash -n` must *not* be credited
  with catching the continuation case. Writing that assertion is what exposed the
  first draft of this tool claiming a detection it did not have; the docstring
  had to be corrected before shipping.
- **Output is classed, because most failures are expected.** Placeholders
  (`<model>`) and prompt transcriptions (`$ cmd` / `# cmd` from vendor docs) do
  not parse by design. 23 blocks are prompt transcriptions; the fix there is a
  note that the prompt is not syntax — added to the three vendored NVIDIA files
  that carry most of them, where a `#` root-prompt line ending in `\` leaves the
  next line's pipe orphaned and errors outright rather than no-opping.
- One genuine parse failure remained after the fixes: a `case`-arm fragment
  quoted from `backup-utility` and fenced as `bash`. Re-fenced as `text` with a
  note that it is a fragment. Fleet now exits 0.

## Resolved — 2026-09-15 (the lag table could not distinguish a date from a guess)

- **A proxy date rendered as a verification date, and it cost a whole
  investigation.** `advisory-lag.py` falls back to the oldest `sources.md` row
  when a skill has no `Freshened:` stamp. It has always computed which of the
  two it used, and the docstring always warned about it — but the table printed
  the bare date, so the reader could not tell. `traefik-hardening` showed as 16
  advisories behind with two criticals; the skill already carried all of them,
  having been fixed earlier the same session. The row was ranking a 2026-07-22
  documentation-link date.
- **Same defect class as the empty-feed fix, in the same script**: an absent
  value silently rendered as a confident one. Fixed the same way — the date now
  carries a `~`, and a footer line counts the proxy rows.
- **Measured, because the size of the bias decides whether the ranking is
  usable.** 44 of 70 skills are unstamped. The proxy understates currency by a
  median of 137 days, mean 304, max 2173. On the live sweep 37 of 56 reported
  rows are proxies, including every row with an unseen critical but two.
- **Often it is not a staleness signal at all.** The oldest row is frequently a
  permanently-old artifact — `jinja-expert` cites a 2020 language spec,
  `ansible-idrac-9-10` a 2023 vendor KB. That date is when the source was
  published, not when anyone last checked it, and it will never move however
  often the skill is freshened.
- `ages` mode reads the same stamp and inherits the same blind spot. Its table
  is a fleet readout rather than a per-row decision aid, so the `~` matters less
  there, but the ranking is built on the same proxy.

## Table of Contents
- [Open](#open) — carried + new ceiling findings, author-judgment items
- [Resolved this pass — 2026-09-01 (freshen + improve, Fable 5.1 release day)](#resolved-this-pass--2026-09-01-freshen--improve-fable-51-release-day)
- [Resolved — 2026-08-20b (improve + freshen)](#resolved-this-pass--2026-08-20b-improve--freshen-self-run)
- [Discard guards — do not re-propose](#discard-guards--do-not-re-propose)
- [Resolved — 2026-08-19 (workflow-sandbox probe)](#resolved--2026-08-19-workflow-sandbox-probe)
- [Resolved this pass — 2026-08-15](#resolved-this-pass--2026-08-15-improve-self-run-dynamic-scorer-config)
- [Resolved — 2026-07-24 (scaffolding discriminator)](#resolved--2026-07-24-scaffolding-discriminator-claude-code-team-blog-pair)
- [Resolved this pass — 2026-07-24](#resolved-this-pass--2026-07-24-freshen--improve-opus-5-release-day)
- [Resolved this pass — 2026-07-18](#resolved-this-pass--2026-07-18-improve-self-run-mechanics-shakedown)
- [Discards / judged no-ops — 2026-05-28 / 2026-06-09](#discards--judged-no-ops--prior-passes-2026-05-28--2026-06-09)
- [Resolved — 2026-06-09 hotfix](#resolved--2026-06-09-hotfix-training-data-regression-guard)
- [Resolved this pass — 2026-06-09](#resolved-this-pass--2026-06-09-improve--freshen-fable-5-release-day)
- [Resolved — 2026-05-28](#resolved--2026-05-28-improve--freshen-opus-48-learnings)

## Open

- **(2026-08-20) The blind scorer's noise floor exceeds the loop's own keep
  threshold — measured, and SKILL.md amended.** 24 cells, 4 skills, n=3, via
  `claude -p --model M --effort E`. **No model tested holds within-cell spread
  under ±2** (medians 2–4, maxima 3–6; Haiku 14). A bare +2 keep is inside
  measurement error, so SKILL.md now treats it as *undecided* — confirm with a
  second cold score, or keep only when the change also simplifies. Two further
  results: **effort is flat** (Opus low/high/xhigh within ~3 points, identical
  rankings, no variance reduction — never raise scorer effort), and the
  **frontier floor is real but is a floor, not a pin** — Haiku alone reordered
  the skills and swung 14 points on one unchanged skill, while Sonnet, Opus and
  Fable all agreed on ranking; Fable was steadiest, Opus harshest, and all three
  non-Opus models sat ~+5 above Opus in absolute level. Recorded in
  `references/blind-validation.md` §Measured scorer behaviour and
  `evals/scorer-sweep.2026-08-20.json`.

  **Still open from this:** ranking stability was only shown on skills spanning
  68–86. Whether it survives on skills closer together in quality — the case
  that actually matters for batch ranking — is untested, and n=3 is thin.

- **(carried 2026-06-09, still Open) Dim 1 → 9: `philosophy` and `floor` mode
  vocabulary absent from `when_to_use`.** "philosophy mode", "boris alignment
  check", "scaffolding decay", "is my skill fighting the model's grain" — and,
  added 2026-09-01, "knowledge floor", "floor mode", "what does the model
  already know" — have no trigger phrases (only `argument-hint` + body).
  Combined `description` + `when_to_use` measured **1486/1536 on 2026-09-01**
  (50 chars free; the "1536/1536" recorded on 2026-08-20 no longer holds), so
  at most one short phrase fits before an addition must be funded by a
  deletion, per `trigger-patterns.md` §T4. Adding triggers blindly is a guess;
  do it empirically:
  `/skill-improver trigger skill-improver --missed "run a boris check on my skill"
  --missed "check my skill for scaffolding decay" --missed "what does the model
  already know about this skill's subject"`. Trigger-mode, not score-loop — the
  2026-09-01 improve pass declined to add the floor phrases for this reason.
  Both 2026-06-09 blind agents and the 2026-07-24 baseline blind also flagged a
  T6-class cross-skill collision — the installed skill-creator plugin claims
  "modify and improve existing skills" territory; the trigger run should include
  sibling-territory negatives for it.

- **(carried 2026-07-18, still Open) Rule-ceiling discard: cold-score-from-disk
  clause.** Adding "read from disk — never from the context-injected copy;
  `${CLAUDE_SKILL_DIR}` appears pre-expanded there and reads as a false
  inconsistency" to Phase 1 §Cold-score discipline moved no dim (all affected
  dims band-internal) yet has demonstrated value: this exact trap caused a
  wrong `discard (noise)` at iter 4 of the 2026-07-18 self-run. Author
  judgment: accept as rubric-invisible operational hardening.

## Resolved this pass — 2026-09-01 (freshen + improve, Fable 5.1 release day)

Baseline blind **85** (pre-pass snapshot) → final blind **86** (both Sonnet 5;
per-dim 9/6/10/9/9/7/9/9/9/8 → 9/8/9/9/9/7/9/9/9/8). The +1 total is inside
the scorer's noise and is not the finding; Dim 2 6 → 8 is, and it was the
target. **Comparator: 3 of 3 for the final, high confidence, decisive margin**,
run as bare `claude -p` from a non-repo cwd — final won from position A twice
and B once, `leakage_external: none` on all three, content leakage the dated
stamps only. Self 82 → 85. Freshen 6 findings applied / 0 discarded / 0
exceptions; improve **cap reached at 10** — 9 keeps, 1 discard — so the
ceiling is **not mapped**.

### Freshen — 29/29 rows, trigger Fable 5.1

- **Fable 5.1 (`claude-fable-5-1`, v2.1.257) priced, and its cache-read
  exception modelled.** `model-rates.json` gained per-model `cache_read`
  (0.025× on Fable 5.1 / Mythos 5.1, 0.1× everywhere else); `run-cost.py`
  and `probe-trigger.py` (which hardcoded 0.1) honour it. Sonnet 5's $2/$10
  is now permanent — the 2026-09-01 increase was cancelled.
- **Effort table**: `xhigh` adds Fable 5.1 / Mythos 5.1; `max` adds Mythos
  Preview, Sonnet 4.6 and **drops Opus 4.5**; per-message effort change
  (beta) keeps the cache on Fable 5.1 / Mythos 5.1 / Opus 5.
- **v2.1.237 → v2.1.257**, seven version rows. The one that touches this
  skill's own rules: `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` (v2.1.257) overrides
  agent-definition `model:` pins, so it silently moves the blind-scorer off
  Sonnet — stated in `blind-validation.md` §Model selection with the check
  (`run-cost.py` shows what ran). The pin itself is unaffected by the release.
- **Subagent cache TTL is configurable since v2.1.242** — Pattern 7.3 and the
  blind-validation cache note said "5 minutes even on a subscription" as a
  fixed fact; now "by default".
- **A pinned release never existed**: SkillEvaluator "v0.2.0 (2026-08-18)" —
  GitHub has only v0.1.0; the number was `pyproject.toml`'s. Re-pinned to the
  CHANGELOG version (0.2.1) with the fact stated; the gate host runs 0.2.0.
- **A date was wrong**: the Fable field guide is 2026-07-06, not 07-03.
- `fable` alias now names two releases (5.1; still 5 in gateway sessions) —
  handed to improve as a Dim 7 defect (below).

### Improve — 10 iterations, self-score column

| iter | Δ | status | change |
|---|---|---|---|
| 1 | +1 | keep | Floor Mode extracted to `references/floor-patterns.md`; SKILL.md 497 → 463 (the baseline blind's top issue) |
| 2 | +1 | keep | `knowledge-floor.py` records `resolved_model` per cell from `modelUsage`; `floor-fleet.py` passes it through; stubbed-subprocess self-check |
| 3 | +1 | keep | "Phases 0–6" → 0–7 in SKILL.md and improve-loop.md's title |
| 4 | 0 | keep (simplification) | provenance sentence (`e379abd`) dropped from the citation rule |
| 5 | 0 | keep (simplification) | blind-validation stub: "two rules" listing three → three imperatives |
| 6 | 0 | keep (simplification) | §State the Spend states its rule instead of arguing it |
| 7 | 0 | keep (simplification) | blind-validation.md "why dynamic replaced the pin" paragraph deleted — DUPLICATE of the section's own rationale |
| 8 | 0 | keep (simplification) | Pattern 6.1's dedup table no longer repeated in SKILL.md |
| 9 | 0 | **discard** | extracting §A Measurement That Failed to a one-rule reference: Dim 2 band unchanged at 439 lines, a 16th reference for one rule is the too-granular failure, and the per-mode failure mechanisms land a hop from the rule they justify |
| 10 | 0 | keep (simplification, widened pass) | Philosophy stub keeps the origin's status, not its story. Compared against: a Freshen-stub rules line (additive, Δ0), the "(Fable 5 / Opus 5, v2.1.154+)" label (true as written), floor trigger vocabulary (blocked — trigger-probe run, folded into the Open item) |

SKILL.md 497 → 455 lines. Comparators flagged two regressions on the winning
side — the `e379abd` example and the 62/520/292/138/90 breakdown — both are
iterations 4 and 8 by design: the breakdown lives in Pattern 6.1, the hash in
git.

### Not a ceiling

One discard in ten does not map a ceiling. What the pass did not try, and
why: Dim 1 phrases for `floor` / `philosophy` (blocked on a trigger-probe run —
Open item); Dim 10 above 8 (blocked on an eval corpus that resolves a delta —
`eval-evidence.py` reports the worst of four measurements inside the noise
band at 8 cases; `grow-evals.py` is the fix and the final blind named it too).
Both blockers are real absent things, not effort.

## Resolved — 2026-08-20b (improve + freshen, self-run)

Baseline blind **86/100**, final blind **86/100** (both Sonnet 5, on snapshots).
**No measurable movement in the total** — and that is the honest headline, not a
hedge. Per-dim the two runs disagree by a point in both directions (Dim 2 7→8,
Dim 8 9→8), which is inside this scorer's measured spread (median 4, max 6).

Two caveats on the final score, stated because they cut against the pass:
the final blind ran on a snapshot taken **before** the X-row citation fixes and
before the orphaned-script documentation, so neither is reflected in it; and its
Dim 8 deduction was for those orphaned scripts, which have since been fixed.
Neither is grounds for claiming a higher number — a score not taken is not a
score.

**The pass's value is in Dim 9, not in the total.** Two of the findings below
are factual errors that no rubric dimension can see — the loop was telling
itself to size fan-outs against a cap that had been deleted, and citing a quote
to a file that does not contain it. Both were caught by probes, not by reading.

### Freshen — all 29 rows probed (three parallel `web-searcher` agents)

- **Removed cap still being taught.** SKILL.md §Batch Mode named three live
  fan-out caps; **v2.1.224 removed the 200-subagent-per-session spawn cap**
  outright (*"long-running sessions no longer refuse new agents"*). Corrected
  to two caps plus the removal. Verified against the primary `CHANGELOG.md`.
- **Misattributed quote.** sources.md credited
  `skill-creator/scripts/improve_description.py` as the source of
  `"be a little pushy"`. It is not in that file. The guidance — and its
  rationale, that Claude *"has a tendency to 'undertrigger' skills"* — is in
  `skill-creator/SKILL.md`. Both rows corrected and `trigger-patterns.md`
  Pattern T4 re-attributed. `improve_description.py` remains the source of the
  overfitting guard and the ≤200-word / 1024-char targets.
- **v2.1.219 → v2.1.237**, seven new rows in `anthropic-skill-design.md`.
  Notably **v2.1.221's `prompt-audit`** subcommand on the bundled `claude-api`
  skill, which audits prompts *and tool descriptions* for "patterns written for
  older models" — first-party tooling aimed at the same target as the
  model-version-compensation cap, now cited in `quality-rubric.md`
  §Boris Alignment Check as a hypothesis source.
- **A subagent report was wrong and the skill was right.** A probe claimed
  nesting-depth default moved 1→3 in v2.1.232; the primary changelog shows
  v2.1.219 already carried it. Existing text kept. §"The Skill Outranks
  Training Data" applies to subagent findings, not only to model priors — the
  rule was written for the latter and just earned its keep on the former.
- **This file's own contract fixed.** sources.md was the last file in the fleet
  still on the legacy per-row `Last verified` format that Freshen Mode replaced
  with a single `Freshened:` header stamp. Stamped 2026-08-20; the staleness
  report now reads it as `full`. SKILL.md §Additional Resources still described
  the legacy behaviour — a straight contradiction with its own §Freshen Mode,
  also fixed.

### Improve

- **A citation that four rules rested on says none of what was attributed to
  it.** The `x.com/Mnilax` row had been marked `ignore-freshen` as "X
  unfetchable, content quoted in skill", so no pass had ever read it. Read
  through the operator's browser this pass: it is a third-party post about
  *nine patterns that waste 73% of your tokens*, and contains **none** of the
  five claims it was sourced for ("don't box the model in", the bitter lesson
  applied to skills, "give it a tool, not context up front", build for the
  model 6 months out, plan-mode default). The Boris Alignment Check survives
  untouched — it was re-attributed to the first-party context-engineering blog
  in July, which carries all three capped patterns plus the cost evidence — but
  the *podcast origin* named by Philosophy Mode, freshen §4b and the trigger
  Minimalism Test is now **unverified rather than refuted**, and is labelled as
  such in SKILL.md, `quality-rubric.md` and the row itself. The rubric's line
  "the X row is unfetchable and cannot be re-probed" was false and is gone.
  **The general lesson, and the reason the escalation rule above matters:
  `ignore-freshen` on a row that was merely bot-blocked is how a bad citation
  survives indefinitely — nobody re-reads what the file says cannot be read.**
- **`bcherny` Steps-of-AI-Adoption row is now partially verified.** Ladder
  steps 0–3 confirmed verbatim from the linked claude.ai artifact (the primary
  source; the tweet is just a pointer). The step-4 "AI-native (1,000+)" label,
  the "I don't prompt Claude anymore … my job is to write loops" quote, and
  "Anthropic self-reports step 3" could not be reached — the embedded artifact
  iframe would not scroll past step 3. Recorded as unverified, not dropped.


- **Withdrawn cap not swept through its dependents.** The 2026-08-20 step-count
  withdrawal left three live references to a cap that no longer exists:
  `improve-loop.md` Phase 0 told the loop three Boris patterns cap Dims 6/4/9,
  `freshen-patterns.md` pointed at a rubric section renamed out of existence,
  and `scaffold-probe.py`'s docstring still said "cap triggered". All three
  corrected. Dim 8.
- **The 1,536-char cap was stated but never measured.** `trigger-patterns.md`
  Phase T4 listed it as a hard constraint with no instruction to check it, so
  an over-cap mutation truncates in silence and the probe scores a description
  the model never saw whole. Added the measurement step and the at-the-cap rule
  (an addition must be funded by a deletion). Grounded in a measured instance:
  this skill sits at exactly **1536/1536** while this very backlog recorded
  "~230 chars of headroom" — that figure is now corrected too.
- **Bot-blocks were treated as terminal.** `freshen-patterns.md` §2.4 sent a
  `402`/`403` straight to an inline "unverifiable" exception note. Four
  `x.com` rows — including the origin source for the Boris Alignment Check —
  had therefore gone unverified across several passes, when the operator's
  logged-in browser reads them fine. Added the escalation rule, and corrected
  the F2 description of `web-searcher`, which had understated its own tooling
  as "Bash/gh/WebFetch" when it also carries full browser control. That
  understatement is why the escalation never occurred to any prior pass.

- **Four scripts were orphaned.** `normalize-evals.py`,
  `backfill-assertions.py`, `grow-evals.py` and `regrade.py` existed, were
  non-trivial, and were referenced from nowhere — a Pattern 2.2 gap the final
  blind caught and both blind runs before it missed. Documented in
  §Additional Resources under a new "Eval-corpus maintenance (fleet-wide, not
  per-run)" sub-heading, with the reason each exists. Fixed rather than filed:
  nothing was absent, so it failed the admission test. SKILL.md 391 → 403
  lines, well inside the 500 ceiling.

### Backlog hygiene

Open 4 → 3. The symptom→mode dispatch-table entry moved to a new
**Discard guards** section: a change judged net-negative is a guard against
re-proposal, not work pending a blocker, and its only obstacle was the size of
the rewrite — effort, which the admission test explicitly rejects. The three
remaining Open items each name a genuinely absent thing (a measurement run, a
trigger-probe run, an operator ruling).

## Pass record — 2026-08-20 (self-run, commits aa0db2f + follow-up)

**Blind 83, 85, 82 — no detectable change.** 4 iterations, 4 keeps, 0
discards. **Stopped early — not a ceiling.**

Three blind scores were taken across near-identical states and the spread is 3
points, inside this scorer's measured noise (Sonnet: spread median 4, max 6 —
`evals/scorer-sweep.2026-08-20.json`). The run was first reported as "83 → 85";
that was noise read as signal, and the loop's own rule — a bare +2 is
*undecided* — applies to it. The third score settles it: the honest result of
this pass is **no measurable movement in the total**, mean 83.3.

That does NOT make the iterations worthless, and the distinction matters. Two
of them fixed things a score cannot see: a measurement script that was
silently wrong, and four dead rows in this file. The rubric scores the skill's
text; neither defect lived there. **A pass whose value does not show up in the
total is a normal outcome, not a failed one** — but it must be reported as
"no movement, here is what was fixed", never as a delta the metric did not
produce.

Cheap check worth repeating: this run is itself a three-sample replication of
the scorer-noise finding, taken on a different skill from the sweep that
produced it, and it reproduced.

| iter | change | effect |
|---|---|---|
| 1 | purged 4 already-RESOLVED rows squatting under `## Open` | backlog only — the scorer is blind to this file by design |
| 2 | `frontmatter-lengths.py`: `\w+:` → `[\w-]+:` field lookahead | Dim 1 7→9 (the 99-char overrun was the bug, not the file) |
| 3 | scoped the Phase 0 eager-read to point-of-use | cleared the induced-cost half of the Dim 6 cap |
| 4 | TOC for `improve-loop.md` (198 lines, 9 siblings had one) | Dim 8; applied after the final blind, so unscored |

**That "next iteration" is void.** The pass above closed by naming a scaffold
restructure as the next hypothesis, on the grounds that `scaffold-probe.py`
capped Dim 6 at 6. Hours later the same day the step-count cap was withdrawn
entirely (no source states a threshold; Anthropic's degrees-of-freedom guidance
recommends explicit steps for fragile work; SkillLens measured format as
non-predictive). There is no cap to lift, so there is no iteration to run —
recorded here so a later pass does not inherit the plan without the retraction.

**Two findings about this skill's own tooling, both shipped hours earlier:**
`frontmatter-lengths.py` had never been run against a file with a hyphenated
frontmatter key, so `argument-hint:` was folded into `when_to_use` — it had
already been cited as evidence in two blind scores and a bead before the bug
surfaced. And the skill was the only one of 68 with resolved rows left under
Open, having written the delete-do-not-tick rule an hour before.

## Discard guards — do not re-propose

- **(2026-07-24) Dim 6/4: symptom → mode dispatch table** in §Invocation
  (13 lines). Net-negative: the table duplicated guidance already carried by
  the Trigger Mode stub ("Use trigger mode when…") and Standalone Evaluation
  step 4, so the Dim 4 gain was cancelled by Dim 6 redundancy. Do not
  re-propose as an addition — if mode dispatch is wanted at the entry point it
  has to *replace* those two passages. **Moved out of Open 2026-08-20:** a
  judged-net-negative change is a guard against re-proposal, not work pending a
  blocker, and it fails the admission test (the only thing standing in its way
  was the size of the rewrite, which is effort, not an absent thing). Keeping it
  under Open inflated the count with something nobody should ever do.

## Resolved — carried entries purged from Open 2026-08-20

Four entries sat under `## Open` already carrying RESOLVED or DECIDED markers —
the oldest since 2026-08-16. Their resolutions are recorded in the dated
sections below and in the commits that closed them; the duplicate Open rows
added nothing but an inflated count. Deleted rather than re-ticked, per
`backlog-format.md` §"Drain duty": the diff is the record.

A fleet sweep the same day found this skill was the ONLY one of 68 with
resolved items squatting in Open (4 of its 8). Writing the rule and being its
sole violator is the finding worth keeping.

## Resolved — 2026-08-19 (workflow-sandbox probe)

- **(2026-08-15; DECIDED 2026-08-19, operator — DECLINED) Dim 1: no
  blind-visible record of the invocation-fit decision, and none is being
  added.** Both 2026-08-15 blind agents flagged "the invocation-fit question
  is never self-applied". The decision itself is unchanged and settled: model
  invocation stays ON, because proactive firing is the entire point of the
  skill (`trigger` mode exists to make it fire), so `disable-model-invocation`
  would remove the description from Claude's context and defeat it. What was
  rejected is the *remedy* — a 3-line note in SKILL.md §Invocation, attempted
  as iter 9 at Δ0 (Dim 1 scores the description, which the note does not
  touch). It buys nothing but silencing a recurring false flag, and it grows
  a SKILL.md that only just reached the lean band and is now guarded by the
  line-ceiling gate above. **A blind scorer's Dim 1 note about the
  invocation-fit question being unaddressed is dismissed with this reason**
  — same handling as the `effort: xhigh` ruling below. Do not re-propose the
  note; if the recurring flag is ever worth retiring, the fix belongs in the
  blind-scorer agent (a documented, deliberate invocation choice is not a
  Dim 1 defect), not in this skill's line count.

- **(2026-08-19) Induced-cost cap added — `scripts/induced-cost-probe.py` +
  `quality-rubric.md` §Induced cost.** Every prior cost signal measured the
  skill's TEXT (Dim 2 lines, Dim 6 scaffolding); none saw the runtime bill the
  skill induces. Four structural triggers, no prose judgement (SkillLens 46.4%
  limit): `effort-pin` (frontmatter effort at high+ on a multi-mode skill),
  `eager-read` (unconditional read-everything), `uncapped-fanout` (spawn
  imperative with no agent-count cap anywhere in the skill), `over-obedience`
  ("verify twice" / "be maximally thorough" / no-early-exit). Caps Dim 6 at 6;
  the two-sided half is binding — Dim 5 is the brake, and a hit never
  justifies a cut that drops promised scope. **Tuning is the substance here:**
  the first version fired on 4 of 6 skills, mostly on text that *quoted* these
  patterns while discussing them, which is the 61%-vs-31% constant-not-a-
  diagnostic failure. Narrowed by stripping quoted spans and table rows
  (mention vs use), widening cap detection to the whole skill directory,
  dropping "load" from the read verbs ("permanent context load" is a noun),
  requiring `exhaustive` to modify an action (it is a mode NAME in
  autoresearch), and skipping negated forms ("not meant to be exhaustive").
  Fleet result: **3 of 68 fire with `--refs`**, all three verified by hand.
  `--selftest` (17 cases) asserts each trigger fires on its shape and stays
  quiet on the near-miss sharing its vocabulary — run it after any pattern
  edit.

- **(operator-accepted 2026-08-19) Line-ceiling gate is in improve-loop
  Phase 4.** `wc -l SKILL.md` runs before the decision rule; a change that
  leaves the file over 500 lines *and* longer than it was is a Dim 2
  regression regardless of total, discarded as `discard (line ceiling)` with
  both counts. Scoped to growth past the ceiling, not to skills already over
  it — a change that shrinks an over-500 file still passes. Rubric-invisible
  (Δ0, reverted 2026-07-24); accepted on the miss that motivated it (freshen
  additions took a SKILL.md 493 → 506 with every dimension band-internal, so
  only a manual count caught it) and on the cost evidence added the same day,
  which prices length rather than merely disliking it. This closes the last
  of the three 2026-07-24 rule-ceiling discards.

- **(operator-accepted 2026-08-19) Freshen recency filter is in
  `freshen-patterns.md` §F2.** Under 7 days since the last pass, re-probe
  only the row kinds that can move in a week — changelogs, release tags and
  versions, pinned commits, registry rows, launch pages — and leave doc,
  spec, paper, and standards rows alone. Restated for the current contract:
  the 2026-07-24 draft assumed per-row `Last verified` columns, but F6 has
  since moved to a single header stamp, so the rule now says a filtered pass
  **keeps the old header stamp** (same reason a rate-limited pass does — the
  stamp means "every row, on this date"), and on legacy per-row files
  restamps only rows actually probed. Rubric-invisible (Δ0, reverted
  2026-07-24), accepted on the operational argument: Dim 9's staleness cap
  reads that date and trusts it, so a restamp on unprobed content disarms
  the cap permanently and silently, which is the one failure mode nothing
  downstream can detect.

- **Boris caps now carry measured cost evidence.** `quality-rubric.md`
  §Boris Alignment Check cited only the >80% system-prompt reduction, which
  shows lean prompts are *survivable*, not that fat ones are *expensive*.
  Added from *Optimizing for cost and intelligence* (re-probed 2026-08-19,
  `sources.md` row restamped): Opus 4.8-era prompts cost **36% more per
  ticket** on Opus 5 at unchanged accuracy; the audit returns **14%** plus
  five accuracy points (14% again on Sonnet 4.6 → 5); removing "verify
  twice" cut cost **by a third**; and a retired thinking setting,
  contradictory rules, and a hand-rolled scratchpad each restored **7-11
  accuracy points**. The page states the patterns apply to skills, so this
  is evidence about the rubric's own subject, not an analogy. Maps
  one-to-one onto the cap table — "verify twice" is Dim 6 scaffolding, the
  scratchpad is scaffolding fighting the grain, an old model's workarounds
  are the compensation cap — which turns the caps from a style preference
  into a priced defect.

- **`DEFAULT_BASE` cannot be derived — measured, not assumed.** The 2026-07-24
  item asked whether `batch-workflow.js` should compute its skills root from
  `${CLAUDE_SKILL_DIR}`. It cannot: a zero-agent probe run enumerated the
  workflow sandbox's entire global set as `log, phase, console, budget,
  setTimeout, clearTimeout, Date, agent, parallel, pipeline, workflow, args`
  — no `process`, no env, no filesystem, and `eval` disabled. `args.baseDir`
  is therefore the only portability mechanism there is. What changed instead:
  the header documents why derivation is impossible (so this does not get
  re-opened without a re-probe), the constant notes it is one machine's
  layout and that it is deliberately *not* the same root as `REF`
  (skill-improver is installed under `~/.claude/skills`; the skills it
  improves live in the plugin repo), and recon gained a STEP 0 — confirm
  `SKILL.md` is readable, else STOP and report the bad base. A wrong
  `baseDir` previously produced agents that could not read the target; the
  guard makes that a stopped run instead of a plausible-looking score.

## Resolved this pass — 2026-08-15 (improve, self-run; dynamic scorer config)

Baseline self **81** / blind **82** (aligned, no 2+ gaps) → final self **83** /
blind **82**. 8 keeps, 2 discards, 10-iteration cap reached. Scorer config for
this and future runs changed before the loop (operator-directed, commit
`12ebe38`): blind scorers now **inherit the session model** (same model for
baseline+final within a run; frontier floor) with **effort pinned `high`** —
the per-release model pin is retired; this run's scorers ran on the session
model (Fable 5). *(2026-08-16 revision: the effort pin was dropped the next
day on operator instruction — scorers now inherit session model AND effort;
the run log records the effective effort.)* Pre-loop the operator also landed five writing-for-agents
patterns (`dc8d04e`): negation→positive (3.4), completion demand (Dim 4 +
4.3), invocation-fit (Dim 1 + T0 gate + 9.3), co-location (Dim 8 + 8.3),
synonym collapse (T5 fix 2).

**Keeps:**
- **iter 1 (+1, noise-confirmed):** aligned 3 stale runs-per-query spots in
  trigger-patterns.md (defaults table, T4 fix order, worked example) to the
  N=7 decision floor.
- **iter 2 (simplification):** collapsed the drifted §Decision rules
  duplicate (missing the mean-rate tie-break) into a pointer at T5/T7; −10
  lines, single source restored.
- **iter 3 (+1, noise-confirmed):** Batch Mode summary now binds exhaustive
  coverage — every scanned skill gets a row, skipped/crashed marked
  (first application of new Pattern 4.3).
- **iter 4 (simplification):** SKILL.md Dim 10-cap paragraph collapsed to a
  rubric §Negative-Transfer Gate pointer; SkillLens figures single-sourced.
- **iter 5 (simplification):** philosophy P4's fragile cross-skill example
  pointer (`instructions-triage` backlog — machine-local) replaced by
  canonical `backlog-format.md`.
- **iter 6 (+1, noise-confirmed):** batch-philosophy scope corrected from
  `~/.claude/skills/` to the scan-skills.sh target list.
- **iter 7 (defect fix):** missing blank line before `---` made the whole
  Native-loops paragraph render as a setext H2; fixed.
- **iter 10 (simplification):** §Blind Validation "When to Run" sub-list
  folded into one sentence pointing at Phase 0 step 6 / §On stop; −6 lines.
- **post-cap (final-blind finding):** two residual "default 3" spots iter 1
  missed (probe-mechanism step 5, cost-budget math 195→455) fixed; the
  final bias check flagged self Dim 8 = 10 vs blind 8 over exactly these —
  self Dim 8 settles at 9.

**Discards (anti-re-proposal guards):**
- **iter 8:** trimming the v2.1.105 boundary from trigger-patterns' T4
  constraint as "provenance archaeology" — reverted: the version is the
  decision boundary for which cap applies, and trigger mode loads without
  the rubric. Shape guard: do not trim version markers from point-of-use
  constraints.
- **iter 9:** rule-ceiling — invocation-fit self-record (moved to Open).

## Resolved — 2026-07-24 (scaffolding discriminator; Claude Code team blog pair)

Triggered by two Anthropic posts published two days apart: Thariq Shihipar's
*"The new rules of context engineering for Claude 5 generation models"*
(2026-07-24) and Delba de Oliveira's *"Building verification loops in Claude Code
with skills"* (2026-07-22). Read as a pair they resolve on one axis — **delete
procedure the model can rediscover; keep acceptance criteria it cannot infer** —
and that exposed a defect in the Boris check's detector.

**The defect.** `rg -c '^\s*\d+\. ' SKILL.md >= 8` counts every numbered item, so
a skill that correctly encodes invariants got the same Dim 6 cap as one spelling
out discoverable steps. Delba's post argues the exact opposite: *"Reject any
migration that drops a column without a backfill step" is a deterministic rule no
generic linter will catch but a project-specific one will.* The naive detector
penalized precisely the content both posts say to keep — and it is the same
property SkillLens already measured as predictive (Failure Mechanism Encoding,
High-Risk Action Blacklist, Actionable Specificity), so the rubric was internally
contradicting itself.

**The fix.** New `scripts/scaffold-probe.py` classifies each numbered item:

| Species | Counts toward cap |
|---|---|
| **Scaffold** — unconditional imperative, no encoded judgment | Yes |
| **Criterion** — prohibition, named failure, or explicit threshold | No |
| **Branch** — decision table / differential diagnosis, condition → action | No |

Rubric §"The scaffolding discriminator" and freshen §4b probe #2 both now call
the script instead of the raw count.

**Measured effect (92 installed skills).** Naive detector caps **56 (61%)**;
scaffold-only caps **29 (31%)**. A detector firing on three of every four skills
is a constant, not a diagnostic.

**Two classifier bugs found by testing, not by reading:**
1. The threshold marker's bare `[<>]` class matched every `<skill-name>`
   placeholder, and `(+2)` inside an example status line read as a real
   threshold. Fixed by requiring a digit adjacent to comparison operators and
   stripping inline code spans before matching.
2. The scaffold/criterion binary was itself wrong. `vllm-caching` scored 0
   criteria / 13 scaffold — but its numbered lists are a decision table
   (SKILL.md L68–73) and a differential-diagnosis list (L169–175), neither of
   which is procedural and neither of which carries a failure marker. That
   required the third class; with it `vllm-caching` is clean at 6 scaffold.

**Not resolved by this pass:** skill-improver still caps itself at 20 scaffold.
The branch class did not rescue it — its phase lists genuinely are sequential
imperatives. See the carried Dim 2 extraction item under Open, which now carries
the per-section scaffold breakdown.

## Resolved — 2026-07-24 (evidence gaps found while running `autoresearch`)

Two defects in this skill surfaced by *using* it, not by scoring it. Both are
cases where the improver could not detect its own errors.

**1. Negative-Transfer Gate added (rubric §, new).** SkillLens's headline number
— skills help in 75% of extractor-target pairs, so **25% are net-harmful**, 47%
in the worst domain — had been sitting in a `sources.md` row since 2026-07-18 and
never reached the rubric or the loop. Nothing here ever asked *is this skill
worse than no skill*. Dim 10's own stated test ("if this skill were deleted,
would Claude produce noticeably worse results?") **is** that question, answered
by intuition — the judgement SkillLens clocked at 46.4%, worse than chance.
Dim 10 is now capped by measured `delta_pass_rate`: 2 if negative, 5 if ≈0,
uncapped if positive, and **8 while unmeasured** (a 9–10 asserts an outcome, not
a reading). Measurement reuses skill-creator's existing
`scripts/aggregate_benchmark.py`, which already computes with_skill vs
without_skill — deliberately not rebuilt here. Also wired into the blind-scorer
prompt so blind runs apply the same cap.

**2. Trigger mode's decision rule was unsound at its own default.** At
`--runs-per-query 3` a query can only score 0/0.33/0.67/1.0, so any query near
the 0.5 threshold is a coin flip and train moves ±1–2 on resampling alone. The
`autoresearch` run demonstrated both failure directions in one session: N=3
manufactured a 0.67 → 0.00 "regression" on the canonical query (6/7 vs 5/7 at
N=7 — pure noise) which cost a full wasted iteration built on a fabricated
proper-noun-placement mechanism, *and* hid a real 1/7 → 6/7 fix behind a tied
pass count. Fixed: probe default 3 → **7**; decision now allows a keep on mean
trigger rate (+≥0.10, no should-NOT regression) when the binary count ties;
guidance to re-measure only disputed queries at high N; T4 row rewritten to say
fractional rates mean *underpowered measurement*, not a mutation problem. The
"mirrors skill-creator" claim was corrected — the methodologies now differ on
this axis and the doc says so.

*Note the shape of both:* this skill warns targets about reward hacking and
noise, and was itself thresholding single-sample noise and scoring utility by
vibes. Running it against a real target found what scoring it never did.

## Resolved this pass — 2026-07-24 (freshen + improve, Opus 5 release day)

Baseline self **83** (post-freshen) / blind **83** → final self **88** / blind
**84**. 5 freshen findings applied, 5 improve keeps, 5 improve discards,
iteration cap reached at 10. No dimension had a 2+ self-vs-blind gap in either
direction at the final check.

**Freshen — Claude Code v2.1.214 → v2.1.219, Opus 5 launch day** (verified via
`gh api` changelog/commits, the Opus 5 launch page, and the live skills doc):
- **Blind-validation model pin moved Fable 5 → Opus 5** (`model: "opus"`,
  `xhigh`). Corrected mid-session after the operator produced the launch
  benchmark table: Opus 5 leads Fable 5 on GDPval knowledge work, BrowseComp
  agentic search, HLE-with-tools, and agentic terminal coding, and carries a
  May-2026 cutoff (vs Jan 2026) that directly reduces false Dim 9 flags on
  freshened claims; Fable 5's wins are sub-1-point coding margins plus legal.
  **Process failure worth remembering:** the first pass of this freshen kept
  the pin on the strength of the docs' "most capable widely released model"
  label and a fetched-page summary, without reading the benchmark rows — a
  vendor tier label is positioning, not measurement. `blind-validation.md`
  §Model selection now states both signals, why the measurements win for this
  task, and that re-pinning requires benchmark rows matching the scoring task.
- `anthropic-skill-design.md`: new frontmatter rows `background` (v2.1.218 —
  `context: fork` skills background by default, `background: false` restores the
  blocking turn and the full tool set) and `arguments`; `disable-model-invocation`
  now notes subagent-preload and scheduled-task blocking (v2.1.196); version rows
  v2.1.215/217/218/219.
- SKILL.md §Batch Mode: fan-out sizing now names all three live caps — 20
  concurrent subagents (v2.1.217), 200 subagents + 200 web searches per session
  (v2.1.212), and the <15-agent medium workflow size guideline (v2.1.219).
- SKILL.md §Standalone Evaluation: new scope boundary — every metric here scores
  the skill's *text*, never its outputs; output-quality evals live in the
  skill-creator plugin loop (`evals/evals.json`, per-case clean-context runs,
  `benchmark.json`, blind A/B), methodology at agentskills.io.
- `sources.md`: new 2026-07-24 pass section; changelog + releases pinned
  v2.1.219; anthropics/skills pinned 1f630fdf (2026-07-22, skill-creator path
  unchanged since 2026-04-20 → Trigger Mode mirroring still accurate); new rows
  for the Opus 5 launch page, the agentskills.io output-quality methodology
  page, and the skill-creator **plugin** install path
  (`anthropics/claude-plugins-official`, the copy the official docs now point at).

**Improve** (rubric hill-climb; self-score column):
- **iter 1 (keep, +2 → 85):** extracted the blind-scorer prompt, model pin,
  parallel-scoring variant, and bias-check table to
  `references/blind-validation.md`, leaving a stub that keeps the two binding
  rules inline. SKILL.md 506 → 421, back under the 500-line spec ceiling.
- **iter 2 (keep, +1 noise-confirmed → 86):** fixed the Boris compensation-language
  probe in `quality-rubric.md` — the `\|` table-cell escapes made the pasted
  command a valid regex that silently matched nothing (verified: escaped form
  exit 1 / 0 matches, corrected form 6 matches). Probe moved below the table
  with the reason stated so it cannot be re-escaped. Closes a carried item.
- **iter 4 (keep, +1 noise-confirmed → 87):** unified the canonical blind prompt
  with `batch-workflow.js` `blindPrompt()` — Dim 9 staleness + spec hard-fail
  caps, `evals/` read step, blind framing — and marked the reference block
  canonical. Closes the two-pass "blind prompts non-comparable" item.
- **iter 6 (keep, simplification → 87):** extracted the Phase 6 backlog format
  (Open/Resolved admission rules, carry-forward, append-only rule) to
  `references/backlog-format.md`. SKILL.md 421 → 379.
- **iter 8 (keep, +1 confirmed → 88):** `scan-skills.sh` now discovers nested
  `.claude/skills/` directories (directory-qualified skills, v2.1.205) that
  `batch --all` silently skipped; tested against a synthetic monorepo and the
  live repo (93 rows, no duplicates). Also removed shipped `__pycache__` /
  `.ruff_cache` cruft.
- **post-cap fixes (Opus 5 re-score of the final artifact):** batch blind
  scorers now carry the same explicit pin as a solo run
  (`model: 'opus'`, `effort: 'xhigh'` in `batch-workflow.js`) — they previously
  inherited the session model, contradicting the binding pin rule and making
  batch and solo blind scores non-comparable; the Batch Mode dynamic-workflow
  label "Fable 5 / Opus 4.8" corrected to "Fable 5 / Opus 5"; TOC added to this
  file (310 lines, a non-optional Phase 0 read, and the only >100-line
  reference without one).
- **post-cap fix (final-blind finding):** `probe-trigger.py` denied `Task` but
  not `Agent` — the canonical name since v2.1.63 — so a probed agent could still
  spawn subagents, breaking the hermetic-probe guarantee the file's own comments
  promise. Both names are now denied.

Discards this pass (anti-re-proposal guards):
- **iter 3:** `discard (noise)` — porting only the Dim 9 cap sentence into the
  blind prompt left the rest of the drift in place; Dim 8 stayed band-internal.
  Re-proposed at full scope as iter 4 → kept.
- **iter 5, 7, 10:** rule-ceiling — line-ceiling gate, freshen recency filter,
  reciprocal drift comment (all moved to Open above).
- **iter 9:** net-negative — symptom → mode dispatch table (moved to Open above).

## Resolved this pass — 2026-07-18 (improve, self-run: mechanics shakedown)

Baseline self **83** / blind **85** → final self **85** (Dim 8 flag accepted →
effective ~83–84) / blind **83**. 4 kept, 6 discarded, cap reached at 10.
First live exercise of the rejected-edit buffer and +1 noise floor (added
2026-07-18, commit 98bf0af); every decision-rule path fired at least once.

- **iter 1 (keep, +1 noise-confirmed):** decision rule partitioned by delta
  (+2+/+1/Δ0/worse/crash) — removed the header-contradicts-body nesting the
  98bf0af noise floor shipped with.
- **iter 2 (keep, simplification):** trimmed the rhetorical tail from the
  Phase 4 discard bullet.
- **iter 5 (keep, +1 noise-confirmed):** flattened the philosophy-patterns P0
  A→B chain by naming the three check-section anchors in the SKILL.md
  Philosophy stub (anchors verified on disk). Baseline-blind Dim 8 nit closed.
- **iter 7 (keep, +1 noise-confirmed):** snapshot-aware keep/discard state
  handling — commit each keep, or snapshot when commits are not permitted;
  discard-revert restores the last kept snapshot instead of `git checkout`
  (which reverts to HEAD and silently destroys uncommitted keeps — this
  exact data loss occurred at iter 4 of this run and was recovered from
  scratchpad snapshots).

Discards this pass (anti-re-proposal guards):
- **iter 3:** `discard (noise)`-status example row in rubric §Results Log
  Format — Dim 8 pinned by the then-open P0 chain; pure addition.
- **iter 4:** `discard (noise)` — P0-chain flatten +1 failed cold rescore
  against a *false* blocker (see incident below); re-proposed and kept as
  iter 5 under the buffer's new-evidence exemption.
- **iter 6:** rule-ceiling — cold-score-from-disk clause (moved to Open).
- **iter 8:** "run log"→"results log" rename — single co-referential
  occurrence, below rubric granularity; Δ0, no line reduction.
- **iter 9:** mode-name tags on section headings (`score`, `improve`) —
  band-internal on all affected dims; Δ0.
- **iter 10:** Phase 0 baseline-snapshot location `/tmp` → scratch dir —
  cosmetic seam, not behavioral; replaced a concrete path with a placeholder.

Process incidents (self-run lessons, both recoverable):
- **Context-vs-disk trap:** when the target skill is the currently-invoked
  one, the context-injected SKILL.md has `${CLAUDE_SKILL_DIR}` pre-expanded;
  scoring against it produced a phantom "hardcoded path" inconsistency and a
  wrong discard (iter 4). Always score against the on-disk file.
- **Revert footgun:** `git checkout -- <file>` on discard (iter 4) wiped
  uncommitted keeps 1–2; recovered from per-keep scratchpad snapshots and
  fixed structurally in iter 7.

## Discards / judged no-ops — prior passes (2026-05-28 / 2026-06-09)

- **(carried 2026-05-28) Dim 2: collapse the freshen/trigger mode-summary stubs
  into one table** (a final blind agent's suggestion). DISCARD — the prose stubs
  carry the trigger context the model uses to know the modes exist; a table
  would compress that signal for ~3 lines. Net-negative. Applies equally to the
  philosophy stub added 2026-06-09.
- **Dim 6: trim ~20–30 lines of deliberate reinforcement** ("Operating Rules"
  restating phase rules; "What a stop is NOT"; "Open is NOT a wishlist"). Blind
  agents scored Dim 6 at 6–7 citing this density both passes. The 2026-05-28 run
  analyzed the deletion and DISCARDED it: the overlap is standing-instruction
  reinforcement that survives compaction (`anthropic-skill-design.md` §"Skill
  Content Lifecycle"). Author decision stands; re-evaluate only if a future
  blind agent shows the redundancy causing *behavioral* errors, not just
  rubric-cosmetic cost.

## Resolved — 2026-06-09 (hotfix: training-data regression guard)

**User-reported incident:** an `improve` run on `rust-expert` mutated factual
claims from training-data memory, regressing content the skill had been
freshened to AFTER the model's knowledge cutoff. Root cause: only `freshen`
mode was required to go online — `improve` hypotheses and blind-scorer
findings could alter external-world claims (versions, dates, model names,
flags, SHAs) from the model's stale prior, and nothing treated a
version-downgrade as the alarm signal it is.

**Fix (4 files, every point where a mutation or score can originate):**
- SKILL.md: new Operating Rule §"The Skill Outranks Training Data" (never
  mutate external-world claims from memory; downgrade = mandatory online
  probe; binds blind scorers); Phase 2 "Factual-claim hypotheses require a
  probe"; blind-agent prompt Dim 9 guard.
- quality-rubric.md Dim 9 check method: verification = online probes / local
  execution / sources.md stamps, never scorer memory; recent stamp outranks
  the prior.
- improvement-patterns.md: Dim 9 guard banner; Patterns 9.1/9.2 now require
  cited online probes and forbid memory-based "corrections".
- scripts/batch-workflow.js: recon STEP 3 (no memory-based Dim 9 docking),
  STEP 4 (factual-claim hypotheses only from STEP 5 probes), apply
  WORKSTREAM A rule (freshen evidence required, downgrades presumed stale),
  blindPrompt Dim 9 guard.

## Resolved this pass — 2026-06-09 (improve + freshen, Fable 5 release day)

Baseline self **84** / blind **82** → final self **88** / blind re-run after
post-flag fixes (see below). 13 kept changes, 0 discards (iteration cap reached;
no ceiling claim made).

**Freshen — Fable 5 / Claude Code v2.1.155–170** (verified via `gh` changelog +
https://www.anthropic.com/news/claude-fable-5-mythos-5):
- SKILL.md Blind Validation model pin: Opus 4.8 → **Fable 5** (`claude-fable-5`,
  Mythos-class tier above Opus, v2.1.170, 2026-06-09); `model: "opus"` →
  `model: "fable"` in the Agent-call instruction (tail fixed after the final
  blind agent caught the incomplete first edit).
- Dynamic-workflow opt-in language: trigger keyword `workflow` → `ultracode`
  (renamed v2.1.160) in both Workflow sections; "agents inherit Opus" → "the
  session model"; batch-workflow.js comment likewise.
- `anthropic-skill-design.md`: effort row (`xhigh` = Fable 5 + Opus 4.8/4.7);
  version-table rows v2.1.157/160/163/169/170; Key Settings rows
  `disableBundledSkills` + `CLAUDE_CODE_SAFE_MODE`.
- `improvement-patterns.md` §9.3: effort example → Fable 5 / Opus 4.8.
- `sources.md`: new 2026-06-09 pass section; changelog pinned v2.1.170; Fable 5
  news row; anthropics/skills re-pinned c30d329f (2026-06-07, skill-creator
  unchanged); agentskills spec re-pinned 5d4c1fda (2026-05-20 name-field docs
  clarification — matches rubric, no drift).

**Improve** (rubric hill-climb + blind-agent findings):
- Fixed broken `rg -nE`/`rg -inE` detection commands in quality-rubric.md §Boris
  and freshen-patterns.md §4b — in ripgrep `-E` is `--encoding`, so the
  documented Boris probes errored as written (verified live, corrected forms
  tested). Dim 7.
- Rewrote the broken awk section-length detector in freshen-patterns.md §4b
  (first rule's `next` made the print rule unreachable — probe #3 silently
  output nothing); new one-liner tested. Dim 7 (final-blind finding).
- Extracted Philosophy Mode (P0–P4, batch, anti-patterns) to
  `references/philosophy-patterns.md` with stub + pointer — SKILL.md 497→427
  lines, all five non-default modes now uniformly extracted. Dim 2 6→7
  (baseline-blind top issue).
- Fixed "Phase 0 step 4" → "step 5" off-by-one in Blind Validation §When to Run.
  Dim 8 (baseline-blind finding).
- Resolved the rubric/trigger-patterns voice contradiction: rubric Dim 1 failure
  example now distinguishes true second person ("You can use this...") from
  acceptable imperative ("Use this skill when..." — the form Anthropic's own
  skill-creator optimizer emits). Dim 8 (baseline-blind finding).
- Batch sub-mode list now includes `philosophy` (was freshen/improve/trigger
  only, contradicting the mode's own batch section). Dim 8 (final-blind finding).
- Converted 5 second-person slips in trigger-patterns.md to imperative (Boris
  quote and intentional examples untouched). Dim 3.

## Resolved — 2026-05-28 (improve + freshen, Opus 4.8 learnings)

Baseline self **81** / blind **84** → final self **89** / blind **90**. 12 kept changes.

**Freshen to Opus 4.8 / Claude Code v2.1.154** (verified via `gh` changelog +
anthropic.com news; Dim 9 6/7 → 10):
- SKILL.md Blind Validation model selection: "Opus 4.6+" → "Opus 4.8
  (`claude-opus-4-8`)".
- `anthropic-skill-design.md`: `effort` field notes Opus 4.8 defaults to `high`
  (`xhigh`/`max` for harder); added `disallowed-tools` frontmatter field
  (v2.1.152); added version-table rows v2.1.152 + v2.1.154.
- `improvement-patterns.md` §9.3: Opus 4.6 → Opus 4.8 effort example.
- `sources.md`: new "Most recent freshen pass: 2026-05-28" section; changelog row
  stamped 2026-05-28 / pinned v2.1.154; new Opus 4.8 news-page row; added a TOC.
- **Dynamic workflows** (the headline Opus 4.8 learning, maps to this skill's
  multi-agent core): notes in Blind Validation (§"Parallel scoring" — fan out N
  scorers, take the median, opt-in guarded) and Batch Mode (parallel baseline
  scoring via the `Workflow` tool).

**Improve** (rubric hill-climb):
- Extracted the Freshen Mode (F0–F6) and Trigger Mode (T0–T7) workflows from
  SKILL.md into `freshen-patterns.md` / `trigger-patterns.md` (one level deep,
  TOC + internal §-refs rewritten). SKILL.md **736 → 499 lines** (under the 500
  ceiling); Boris numbered-line count **70 → 40** (remaining lines are core
  methodology, rubric-exempt — confirmed by blind agent, no Dim 6 cap). Dim 2
  5→8, Dim 6 6→8.
- Converted 5 second-person slips to imperative (Dim 3 9 → 10).
- Reworded the backlog-reference self-contradiction at SKILL.md Phase 6 (Dim 8).

*(2026-05-28 record restored 2026-06-09 — dropped in that day's backlog rewrite;
prior-pass history stays in the live file so future loops inherit it without
digging through git.)*
