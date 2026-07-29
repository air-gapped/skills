# The Comparative Specification

Contents: [Question set per dimension](#question-set-per-dimension) ·
[IS-NOT discipline](#is-not-discipline) ·
[Mining distinctions and changes](#mining-distinctions-and-changes) ·
[Worked example](#worked-example-compact) ·
[Table maintenance](#table-maintenance)

The specification is a boundary drawn around the problem. Everything inside
(IS) must be explained by the true cause; everything just outside (IS-NOT)
must be *spared* by it. Causes are tested against this boundary, which is why
the quality of the whole analysis is capped by the quality of the table.

## Question set per dimension

Ask every question. Answer, mark "N/A", or mark "unknown — to check". Never
silently skip: the objectivity of the method lives in asking the questions
that "probably don't matter".

### WHAT (identity)

| IS | COULD BE, but IS NOT |
|---|---|
| Which specific object (host, pod, board, job, binary) shows the deviation? | Which similar objects could plausibly show it, but don't? |
| What exactly is the deviation — what do you *observe* (error text, code, smell, sound, measurement)? | What other deviations would be unsurprising here, yet are absent? |

The absent-deviation question is underrated: "it OOMs but never segfaults",
"it corrupts writes but reads are fine" carves the mechanism space hard.

### WHERE (location)

| IS | COULD BE, but IS NOT |
|---|---|
| Where is the object when the deviation appears (site, rack, cluster, region, environment)? | Where else does the same object/kind run without the deviation? |
| Where *on* the object is the deviation (which subsystem, port, partition, code path, phase)? | Where on the object could it appear, but doesn't? |

### WHEN (timing)

| IS | COULD BE, but IS NOT |
|---|---|
| When was it first observed (clock/calendar, as precise as evidence allows)? | When could it have started earlier, but demonstrably hadn't? |
| Since then: continuous or episodic? Any pattern (time of day, load, cron, moon phase — check, don't scoff)? | When does it *not* occur despite conditions looking the same? |
| When in the object's lifecycle does it hit (boot, warm, under load, at scale-out, on the Nth request)? | At which lifecycle points does it never hit? |

### EXTENT (magnitude)

| IS | COULD BE, but IS NOT |
|---|---|
| How many objects are affected? | How many could be, but aren't? |
| How large is a single deviation (error rate, latency, count, temperature)? | How bad could it plausibly be, but isn't? (Fails 5% of requests — why not 100%?) |
| How many deviations per object? | |
| Trend: growing, stable, shrinking — in count and in size? | |

## IS-NOT discipline

The IS-NOT column is the **closest logical comparison** — the twin that
escaped. Not "the rest of the universe". Good IS-NOT entries:

- the same host last Tuesday (before onset)
- the identically-specced node in the next rack
- the same job against the staging database
- the other 9 of 12 VMs on the same schedule

A vague IS-NOT ("nothing else is broken") produces no distinctions. A tight
one ("node4 fails, node3 — same image, same rack, same day of install — does
not") practically hands you the cause. Failed fast-path experiments belong
here too: "swapped PSU, no change" is a hard-won IS-NOT.

## Mining distinctions and changes

For each filled IS / IS-NOT pair:

1. **Distinction:** what is different, special, or unique about the IS side
   compared to its IS-NOT twin? (Hardware revision, firmware, config drift,
   workload mix, physical position, who set it up, procurement batch...)
2. **Change:** what changed in, on, or around that distinction — and exactly
   when? Date every change and check it against the WHEN row. A change that
   postdates onset cannot be the cause; a change that aligns with onset is a
   prime suspect.

Causes are then hypothesized as mechanisms running *through* a distinction or
change: "because <distinction/change>, <mechanism>, therefore <exactly this
IS pattern and not the IS-NOT>".

## Worked example (compact)

Deviation: `nightly-pg` backup job killed (exit 137) on 3 of 12 VMs, since
the 19th.

| | IS | COULD BE, but IS NOT | Distinction → Change |
|---|---|---|---|
| WHAT | nightly-pg exits 137 (OOM-kill) `[observed]` | other jobs on same VMs fine; no other exit codes seen | job streams full dump through gzip |
| WHERE | vm-04, vm-07, vm-11 `[observed]` | remaining 9 VMs, same playbook | the 3 are the only VMs upgraded to DB v16 `[reported]` → upgraded on the 18th |
| WHEN | first 03:12 on the 19th, nightly since `[observed]` | never before the 19th; never on manual daytime runs `[reported]` | nightly runs overlap the analytics batch; manual runs don't |
| EXTENT | 3 VMs, every night, whole job dies | not 12; not intermittent; job never merely slow | deterministic, not load-flaky |

Candidates: H1 "v16 dump allocates more, tips the VM into OOM during the
analytics overlap" — explains WHERE (only upgraded VMs), WHEN (nightly overlap
yes, manual no; onset the night after upgrade), EXTENT (deterministic).
H2 "storage backend degraded" — fails WHERE (why only the upgraded 3?) and
WHEN (why never daytime?): killed on paper. Verify H1 cheapest: run one
nightly-window dump on an upgraded VM with memory tracking `[observed]`
before touching any config.

Note what the IS-NOT bought: two candidates died without a single test, and
the verification test was chosen to *refute* H1 (if memory stays flat, H1 is
dead too).

## Table maintenance

- Re-emit the current table after every material update and at every stage
  transition. In long sessions, the freshly-printed table is what keeps the
  evidence in view — trust the table, not memory of the table.
- Multi-session or team investigations: persist the table + hypothesis list
  to a file (e.g. `TROUBLESHOOTING-<slug>.md`) and treat it as the single
  source of truth; re-read it before resuming, because a stale recollection
  of the spec is worse than none.
- Revise the problem statement when the spec sharpens it ("backups broken" →
  "nightly-pg OOM-killed on v16 VMs during analytics overlap"). A statement
  that got more precise mid-analysis is the method working, not scope creep.
- Provenance tags are load-bearing at test time: a candidate refuted only by
  an `[assumed]` cell is not refuted; an `[assumed]` cell propping up the
  favorite candidate is the first thing to go verify.
