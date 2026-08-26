# Porting a Values File Across Chart Versions

**Applies when** the values file is a full copy of the chart's `values.yaml` with
edits applied inline. **Does not apply** to a sparse override file — that has no
common ancestor with the new defaults, so there is nothing to three-way merge.

You need three files. If you do not have the ancestor, stop and recover it first
(§ Keep the Ancestor).

| role | file |
|---|---|
| MINE | the values file you deploy today |
| OLDER (ancestor) | the stock `values.yaml` yours was made from |
| YOURS (theirs) | the stock `values.yaml` of the target version |

## Never Use `patch`

```bash
patch -F3 -o out.yaml stock-new.yaml < site.patch    # DO NOT
```

`patch` gets a diff and a target, never the ancestor, so it cannot tell "this
line changed under me" from "my anchor is gone". With fuzz it relaxes context
matching until something nearby matches — an edit meaning *"inside the
`hostPort:` block, set `enabled: true`"* landed on `hostFirewall:` after upstream
deleted `hostPort:`, flipping a security setting on with exit 0 and no warning.

Do not reach for `--no-fuzz` or a smaller `-F` instead. The missing ancestor is
the defect; fuzz only decides how far it slides.

## Merge

```bash
diff3 -m mine.yaml stock-old.yaml stock-new.yaml > merged.yaml
```

Order is **MINE, OLDER, YOURS — middle is always the ancestor.** Getting it wrong
does not error, it emits a plausible wrong file. Prefer the git form for readable
markers:

```bash
git merge-file -p --diff3 mine.yaml stock-old.yaml stock-new.yaml > merged.yaml
```

`-p` writes stdout; without it `mine.yaml` is overwritten in place. `--diff3`
puts the base inside each conflict (`ours ||||||| base ======= theirs`), so you
can tell whether you moved or upstream did. **Exit code is the conflict count.**

Treat every conflict as a decision to make, not noise to clear — the count is
small and false positives are rare. Expect these shapes:

- **Key deleted upstream** — empty "theirs" side. Decide whether it was
  load-bearing before dropping your value.
- **Rename** — both names in one block with the base between them. No tool
  reports renames semantically; this block is the only signal you get.
- **Restructured block** — re-derive your setting against the new shape.

## Do Not Produce the File With a YAML-Aware Tool

`yq`, `dyff`, `dasel`, `jd` parse and re-emit, and every round trip can drop a
comment, a quoting style, or a type — a values file carries thousands of comment
lines and `port: "6443"` must stay a string. Use them to **report** only;
`dyff between` is good pre-merge triage. Never pipe the merged file through them.

Do not substitute a syntax-aware merge driver (mergiraf and similar) either. It
produces byte-identical output here: both sides come from `helm show values`, so
line context is already stable and there are no reindentation conflicts for it to
suppress.

## Verify — Compare Sets, Not Counts

Flatten each file to `dotted.path = json_value` leaves and assert both:

```
edit-set(mine-new vs stock-new)  ==  edit-set(mine-old vs stock-old)
    → every customisation carried, nothing invented

churn(mine-old → mine-new)       ==  churn(stock-old → stock-new)
    → every upstream change applied, nothing clobbered
```

Both must hold with symmetric difference 0. Equal *counts* prove nothing.

Do the set operations in code. Two ways this silently produces wrong answers:

- **Raw `diff` output** — line numbers differ, byte-identity is impossible.
- **`comm` on Python-sorted files** — locale collation mismatch.

Then diff the rendered output (`helm template` at both versions) and the main
ConfigMap specifically. A clean port changes no values; only keys traceable to a
documented upstream change should move.

## Grep for the Previous Version String

```bash
grep -n '1\.19\.6' merged.yaml     # the version you came FROM
```

The merge's blind spot is a value that looks like configuration but tracks the
chart — an image tag or digest copied from the old chart's own default, a sidecar
image, a schema URL. A three-way merge carries it forward faithfully, leaving an
old-version container in a new-version workload. Nothing in the merge detects
this; make the grep a standing post-merge step.

## `helm lint` Does Not Catch a Misspelled Key

`helm template` exits 0 with empty stderr on a key no chart ever reads — the
setting simply never applies. This holds even for charts shipping
`values.schema.json`, unless that schema sets `additionalProperties: false`
(most do not, and most charts ship no schema at all).

So a passing lint is not evidence your keys are valid. The set difference above
is the real check. Authoring side: `chart-structure.md` § `additionalProperties`.

## Keep the Ancestor

Keep the stock file matching the values file you currently deploy — it is the
ancestor for the next merge. Older ones can be pruned.

If one was deleted, git still has the blob. `git log -1 -- <path>` on a deleted
file returns the *deletion* commit, where it no longer exists; walk back:

```bash
for c in $(git log --all --format=%H -- "$f"); do
  git cat-file -e "$c:$f" 2>/dev/null && { git show "$c:$f"; break; }
done
```

## Practical

- Enable **`git rerere`** for a recurring port — the same hunk stops asking twice
  across bumps.
- **Run the port and the verification as separate passes.** A single pass gets
  the merge mechanics right and rides past forward-facing default changes on
  already-enabled features. Start the verification pass by confirming the "stock"
  files really are byte-identical to `helm show values` for their version.
- **Read the chart's templates or source, not its changelog**, to decide whether
  a key deleted upstream was load-bearing. Release notes rarely say.
