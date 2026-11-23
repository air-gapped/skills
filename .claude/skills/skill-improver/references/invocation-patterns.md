# Invocation and trim

Every automatic skill's name, `description` and `when_to_use` are in context on
every turn, inside one listing budget shared by all skills. When the listing
overflows, Claude Code drops descriptions, least-used skills first, and a skill
without its description is chosen less. Decide first whether a skill belongs
in the listing at all (`invocation`). Trim only the skills that stay automatic
(`trim`).

## Measure

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/listing-cost.py [<skills-root> ...]
python3 ${CLAUDE_SKILL_DIR}/scripts/neighbours.py <skill-dir> --root <skills-root> [--root ...]
```

`listing-cost.py` gives mode, listing characters, ~tokens, share, uses and
flags per skill. Report every decision with the tokens it saves.
`neighbours.py` ranks the automatic skills closest to a target.

`uses` is a hint, not proof: zero uses can mean the description was being
dropped from the listing.

## `invocation`: one row per skill

Output: `skill | decision | one-line reason | listing tokens saved | follow-up`.
Run steps 0–2 per skill. Over a fleet, run step 2 across the whole set before
deciding any member.

### Step 0: needed at all?

Propose retiring the skill (`git mv` to a `removed/` folder; never delete) when
one of these holds. Retiring is proposed with its evidence, never applied
unasked.

| Signal | Check |
|---|---|
| Duplicate | a local copy of a plugin or upstream skill (same body, or an older version of it) |
| Official upstream skill exists | the product's own repo ships a skill for the same job, for a newer version of the spec |
| Dead target | the project or product it serves has been idle for months, or is archived |
| Unmaintained port | a port of another tool's workflow with a handful of uses and no recent change |
| Name collision | `NAME~` flag: another skill's name contains this one's, and the wrong one gets invoked |

### Step 1: how is it invoked?

| Decision | When | Frontmatter |
|---|---|---|
| slash-only | side effects; a fixed procedure; planning or audits the user starts; one-off migrations; a thinking method or checklist the user asks for by name | `disable-model-invocation: true`, plus an `argument-hint` so `/name` is easy to type |
| paths | the skill belongs to certain files (`**/Cargo.toml`, `**/*.rs`, `.beads/**`, `.github/**`, `**/Chart.yaml`) | `paths:` glob list |
| automatic | reference knowledge needed mid-task, on questions that name no file | none; go on to `trim` |

- A slash-only skill leaves the listing, so its description length stops
  mattering: do not trim it.
- A slash-only skill runs only when the user types `/name` (or writes `/name`
  in a sentence). The Skill tool refuses it.
- `paths` activates the skill only for files Claude reads, edits or writes
  that match. A general question with no matching file misses it. Name that
  miss in the reason column.
- Choose `paths` over automatic when the work happens in those files: the
  tool's state or config lives in the repo (`.beads/`, `.github/`, a
  language's manifest), so its questions come up where the files are. Accept
  the general-question miss; do not keep the skill automatic for it.
- `paths` globs are relative to the working directory and match only files
  inside it. A personal config file outside any project (`~/.config/...`)
  never matches: make that skill slash-only, not `paths`.
- An audit, compatibility check or plan the user runs on purpose is
  slash-only, also when it heads a family.

Calibration, decided by hand:

| Kind of skill | Decision |
|---|---|
| release tagging; publishing a repo; a video-to-notes pipeline; a one-off tracker migration | slash-only |
| window-manager or terminal config | slash-only |
| a thinking exercise the user asks for by name | slash-only |
| upgrade planning, compatibility audits, a hardening checklist, a migration runbook (`k8s-components-checker`, `rancher-upgrade`, `traefik-hardening`, `postgres-operator-cloudnative-pg-migration`, `openshift-app`) | slash-only |
| a language toolkit (Rust); an issue tracker stored in the repo; CI config | paths |
| product reference used mid-task (`keycloak-iam`, `argo-cd-apps`, `keda`, `helm`); a CLI reference (`gh-cli`); log reduction (`lessence`); test-quality review | automatic |

### Step 2: family check

Find related skills: a shared name prefix, the same plugin in
`.claude-plugin/marketplace.json`, a skill that names another's `/name`, or a
skill that reads another's output file.

| Family | Decision |
|---|---|
| Pipeline: a fixed order, each step reads the previous step's output | every member slash-only; the first member's description names the order |
| Reference family: members cover parts of one subject | one automatic umbrella with a full description and a map of the members; members slash-only, or automatic with a one-line description |
| Family of procedures (upgrades, audits, migrations) | every member slash-only; no automatic umbrella unless one member answers mid-task reference questions |

A router or umbrella names slash-only members as `/name` for the user to
type. It cannot invoke them.

### Where a fix goes

| Skill comes from | Change |
|---|---|
| This repo or another repo you own | frontmatter in its `SKILL.md` |
| A tool that installs or syncs it (a vendor CLI, `npx skills`, a design kit, claude.ai sync) | `skillOverrides` in settings: `on`, `name-only`, `user-invocable-only`, `off`. The tool's next update overwrites the file. |
| A plugin | `skillOverrides` does not apply. Turn the plugin on or off with `/plugin`, or change the plugin's source. |

- A skill outside any git repository must carry `metadata: {origin: <url or
  tool>}` (`ORIGIN` flag). Without it nobody can tell whether a file edit
  survives the next update.
- `paths`, `disable-model-invocation`, `when_to_use` and `argument-hint` are
  Claude Code fields (`CC:` flag). claude.ai upload and the Skills API reject
  them with "Unexpected key(s) in SKILL.md frontmatter". The Agent Skills spec
  allows only `name`, `description`, `license`, `compatibility`, `metadata`
  and `allowed-tools`. When the skill is also published there, publish a copy
  without those fields.

### Across skills

For each family and each neighbour pair, compare the decision rules. When two
skills give opposite advice on the same situation (one judges the person's
attitude, the other says to look at the conditions), report the pair and both
rules. Do not edit one to match the other.

## `trim`: shortest description that still works

Automatic skills only. A slash-only skill is never trimmed.

### Scoring

1. Trigger accuracy is the score: should-trigger passes, should-not passes,
   and sibling passes (neighbours' queries that must not fire this skill).
2. Fewer characters breaks a tie.
3. Adding characters needs a higher score.
4. 1,536 characters is a ceiling, not a target.
5. Keep version numbers out of the description and `when_to_use`. The
   always-loaded text goes stale first; the version belongs in the body.

### Procedure

1. **Eval set.** The skill needs `references/trigger-evals.json`. Build it as
   in `trigger-patterns.md` §Eval-set construction, from the body, not the
   description. Then add the neighbour queries:
   `neighbours.py <skill-dir> --root <root> --top 5 --eval-out $T/evals.json`.
   It copies each neighbour's should-trigger queries as `sibling:<name>`
   negatives. Write two by hand for a neighbour that has none. Delete a sibling
   query the target's body also covers.
2. **Price it.** Calls = queries × 3, plus 4 more runs for each query the first
   look leaves undecided, per measurement. Print the total before the first probe.
3. **Baseline.**
   `probe-trigger.py --skill-path <dir> --eval-set $T/evals.json --runs-per-query 7 --neighbour <dir> ... > $T/p0.json`.
   The neighbours are installed beside the skill, so a sibling query has to
   pick the right skill.
4. **Cut in steps.** Run the steps in this order and measure after each one
   (`--description "<text>"`, no file write):

   | Step | Cut |
   |---|---|
   | 1 | text that carries nothing: version numbers, bare counts, the name or identity restated, "covers", "reference for", synonyms after the first 1–2 terms users type |
   | 2 | lists: example trigger phrases that repeat the subject, catalogues of flags or backends or models; keep each symptom the body solves and each term a user would put in a query |
   | 3 | the description's scope sentence, down to what the skill does and the decision it helps with |

5. **Compare.** `neighbours.py --score $T/evals.json $T/p0.json $T/p1.json ...`
   prints chars, then passed/measured for trigger, other should-not, and
   sibling queries. Keep a step only when no group falls below baseline. A
   group that falls by one query at 3 runs is re-measured at 7 before the step
   is dropped.
6. **Stop** at the last passing version. Write that text to the frontmatter.
7. **Report** before and after: characters, ~tokens, listing share, the score
   lines. Save the eval set with the sibling queries to
   `references/trigger-evals.json`.
