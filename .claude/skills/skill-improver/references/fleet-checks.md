# Fleet checks — what each one catches, and how to read it

Six checkers under `scripts/`, each testing something a parser can decide. Run
them over the whole tree, not just the skill being edited: every one of them found
defects in skills nobody was touching.

Each section below gives the invocation, what the check found when it was written,
and — the part that matters — which of its hits are *expected* and must not be
"fixed". A checker whose false positives get treated as findings costs more than
the defects it catches.

---

## A Fence Is Code, and Nothing Else Checks It

Skill markdown is copy-paste material. `shellcheck` runs on `.sh` files; **no gate
looks inside a ```bash fence**, so a broken command fails on the reader's machine
rather than here. Run
`python3 ${CLAUDE_SKILL_DIR}/scripts/check-shell-fences.py [root]` after editing
any block a reader is meant to run.

It makes two passes because one is not enough. `bash -n` catches syntax errors.
It does **not** catch `cmd \   # note` — the backslash escapes the space, the `#`
opens a comment, and the next line silently becomes a separate command. That
stays syntactically valid and means something else, so a regex pass exists
alongside the parser. Measured 2026-09-15: 753 fences, **7 occurrences across 4
skills, none visible to `bash -n`** — one had been quietly dropping two of three
`--config.file` flags.

Read the output by class: broken continuations and unexplained parse failures are
real, while placeholder blocks (`<model>`) and prompt transcriptions (`$ cmd` /
`# cmd`, copied from vendor docs) are expected to fail and are fixed with a note
about the convention, never by editing the command.

`scripts/check-yaml-fences.py` is the sibling for ```yaml blocks. 576 fences,
**one real bug**: a `fieldPath` containing `[` and `]` sat unquoted inside a YAML
**flow** mapping (`{...}`), which forbids those characters in a plain scalar. The
same value is legal in block style, which is why it read as correct. Expect this
one to be quiet — its value is the next edit, not the current run. Go/Jinja
templating is reported separately, since a Helm chart is not YAML until rendered.

## Content Scheduled to Become False

`freshen` catches sources that drifted. It does not catch content that is correct
today and wrong on a date already written into it. Run
`python3 ${CLAUDE_SKILL_DIR}/scripts/check-expiring-claims.py [root] [--relative]`
alongside a freshen pass.

**The dates are not the interesting part — the phrases beside them are.** A
lifecycle table full of future EOL dates is working as intended. What rots is a
*relative descriptor*: "2.11 goes EOL 2026-10-24 — roughly three months out" had a
correct date and a wrong description of it, 5½ weeks later, in a warning whose
only job was conveying how short the runway was. `--relative` reports exactly
those. Measured 2026-09-15: 37 future-dated claims, 2 worth acting on, and both
`[rel]` hits were real.

Fix them by deleting the relative phrase and instructing the reader to compute
from the date. A replacement phrase rots identically.

**This section is itself the checker's one standing false positive.** The example
above quotes a real date beside a real relative phrase, so `--relative` flags this
file every run. It is a quotation of a defect, not a live claim — leave it. A run
whose only `[rel]` hit is this paragraph is a clean run.

## Two Classes of Link Rot, and the Rest Is Noise

The skillevaluator gate checks links only in skills **staged for a commit**, so a
citation rots for months in any skill nobody edits. Run
`python3 ${CLAUDE_SKILL_DIR}/scripts/check-links.py [root] [--workers N]` to sweep
the whole tree.

It checks two classes and skips the rest. Measured 2026-09-15 over 2573 unique
URLs: **documentation hosts** (322 checked, 7 dead — doc sites reorganise
silently, the old path 404s while the product is fine) and **GitHub `blob`/`tree`
paths** (189 checked, 4 dead — GitHub redirects a renamed *repo*, never a *moved
file*). GitHub issue/PR/release and arXiv URLs are stable by design and are most
of the corpus; sweeping them buys nothing. `--all` drops the filter when that
judgement needs re-testing.

**A moved file is searched for, not guessed at.** All four GitHub findings were
relocations, so no edit to the path would have found them — and when a project
migrates its docs to a generated site, every deep link into the old tree dies at
once.

Two statuses are not findings. **403** means this fetcher was refused, not that the
page is gone — and a bare `curl` retry distinguishes the two kinds: a user-agent
block serves the real page to it, a bot challenge returns 403 again with an
interstitial title. The second still is not a dead link; it just cannot be cleared
from a terminal. **429** means this sweep
tripped a rate limit — lower `--workers` and re-run rather than recording it.
Both print in their own sections, outside the dead list, and neither affects the
exit code.

Add a host to `DOC_HOSTS` when a skill starts citing it. A host that is absent is
simply never swept.

## A Remediation Floor Is the Number an Operator Acts On

`freshen` re-probes sources; `advisory-lag.py` finds advisories a skill has not
absorbed. Neither checks a floor the skill already wrote down. Run
`python3 ${CLAUDE_SKILL_DIR}/scripts/check-advisory-floors.py [root] --verify`
after any edit that names a CVE and a fixed version.

It fails in two directions and only one of them is loud. **Too low** sends an
operator to a build still inside the affected range. **Attributed to the wrong
line** credits a version the advisory never listed — which changes no upgrade
advice, reads as correct, and therefore survives review indefinitely. Measured
2026-09-15: 104 advisory ids across the fleet, one skill crediting a critical
Argo CD advisory to two minors it never affected, one of them in a release that
shipped three months before the fix existed. That file stated the correct range
four sections above the error.

**Read every flag before editing; three shapes flag legitimately.** A per-minor
backport floor sits outside the advisory's range by design. An unbounded range
with a null `first_patched_version` means the feed does not know the fix — derive
it from the fix PR's merge commit, never read it as "no fix". A negative claim
("does not affect 3.1") is a correction, not a floor.

The tool checks 7 lines out of those 104 ids and skips the rest. That is the
intended trade: a line naming several advisories cannot be resolved by pattern,
and guessing manufactures findings. Because every such filter can also hide a
true defect, `--selfcheck` replays the Argo CD line verbatim and asserts it still
comes out condemned — a clean run means nothing if that assertion has been tuned
away.

## A Ragged Table Loses Its Last Column Silently

No renderer warns about a table whose rows and header disagree on width — it
**drops every cell past the header count** and renders the rest as if intended.
Run `python3 ${CLAUDE_SKILL_DIR}/scripts/check-tables.py [root]` after editing any
table, and after adding a column to one.

The dropped cell is the last one, which is where a table puts its payload.
Measured 2026-09-15: 34 ragged rows across 7 files. The worst had a header
reading `| Symptom | Issue | Fix |` over rows written with an extra
model/scenario column, so the **Fix** column was discarded on exactly the rows
carrying a model-specific workaround. Too-short rows are the quieter half and
still wrong: a single value spanning a two-variant comparison renders as an empty
cell, which reads as *absent on that variant* rather than *same on both*.

**When the rows agree with each other and only the header disagrees, fix the
header.** Ragged rows cluster, because they come from one table whose shape
changed and whose header did not follow.

Two things are content, not borders: a `|` inside backticks, and an escaped `\|`.
Documentation tables write alternatives that way constantly, so a checker missing
either reports a clean fleet as broken — an earlier draft of this one produced 13
findings, all of them escaped pipes. Both cases are pinned by `--selfcheck`.

## Which Fleet Sweeps Pay, and Three That Do Not

Every checker in this directory tests something a parser can decide. That is not a
coincidence, and it is the rule for proposing the next one.

**Syntactic sweeps pay.** A fence either parses or it does not; a table row either
matches its header or it does not; a URL either resolves or it does not; a version
either is inside an advisory's range or it is not. Each of those found real defects
on a fleet that looked healthy — including a troubleshooting table silently dropping
its **Fix** column and a critical advisory credited to two release lines it never
affected.

**Three semantic sweeps were tried on 2026-09-15 and produced nothing but false
positives. Do not rebuild them without a sharper idea:**

| Sweep | Why it failed |
|---|---|
| Reference files nothing points at | A pointer can be a bare filename, a relative path, a `[[wikilink]]`, or live in another reference rather than the body. Three drafts, 21 → 9 → 1 hits, and the last one was reachable too. |
| Two different versions called "latest" in one file | Grouping by version family lumps unrelated products together — a ten-product comparison row reads as one product contradicting itself. 53 hits, none real. |
| Cross-skill pointers that resolve to no skill | Backtick-quoted lowercase-hyphenated tokens are mostly frontmatter fields, agent types, CLI flags and component names. 79 hits, none real. |

The distinction is not "hard versus easy". It is whether the thing being checked has
a **decidable** definition. When it does not, the sweep's own false-positive rate
becomes the finding, and a checker whose only demonstrated output is noise costs more
than the defects it was meant to catch.

**One real defect did come out of those three**, found by reading the hits rather
than by the rule: a compatibility registry carrying a component its index never
listed. Run a loose sweep once by hand if you like — just do not ship it.
