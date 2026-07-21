# Improvement backlog — open-webui-valkey-websocket

Carried across `skill-improver` runs. Each Open item is a finding that the
loop attempted but couldn't apply atomically in a single iteration. Resolved
items are an audit trail of what was fixed.

## Open

1. configuration.md `maxclients` Valkey/Redis-version cliff (Dim 9) —
   stated as "newer Valkey versions / older Redis versions" without exact
   version numbers. Pinning would lift Dim 9. **Why not applied this run:**
   requires a separate Valkey/Redis-version probe (Redis 5/6? Valkey 7/8?)
   to confirm the actual default-`maxclients` cliff; out of scope for a
   single atomic iteration. (carried 2026-05-28)
2. SKILL.md "verify on the deployment's target version" handwave for the
   lagging admin endpoints (Dim 4) — lacks a concrete `curl` recipe.
   **Why not applied:** auth-token handling is environment-specific
   (cookie vs Bearer vs OAuth proxy); a one-size-fits-all snippet would
   mislead. (carried 2026-05-28)

## Resolved — 2026-07-21 (freshen)

Issue/PR states and chart versions re-probed. Two upstream jumps and one
**verification error inherited from earlier passes**.

- **#23939 was carried as OPEN for two passes while it had been CLOSED since
  2026-04-22.** The 2026-05-10 pass recorded "others confirmed open 2026-05-10",
  by which point #23939 had been closed for over two weeks, and 2026-05-28
  re-stamped the group row without re-checking the members. Corrected in both
  `sources.md` and `known-issues.md`, with the section retitled rather than
  deleted — the 0.9.0/0.9.1 content is still useful history. **Lesson recorded:
  a grouped verification row hides per-member drift; probe members, not groups.**
- **open-webui 0.9.5 → 0.10.2** (2026-07-01, via 0.9.6/0.10.0/0.10.1). The
  version floor in `SKILL.md` deliberately **stays at ≥0.9.5**: 0.9.6 and the
  0.10.x line were not audited for scaling regressions this pass, so 0.10.x is
  labelled un-vetted rather than silently recommended.
- **Line-number map explicitly marked as suspect.** It is still resolved against
  the 0.9.4 clone and was not re-resolved. The sibling `open-webui-embeddings`
  freshen the same day found `config.py` restructured by ~2000 lines between
  0.9.x and 0.10.2, so this map has almost certainly drifted — `sources.md` now
  says to re-resolve by symbol name instead of trusting it.
- **Helm chart 14.6.0 → 15.2.0** (2026-07-01), appVersion 0.10.2 — a **major**
  bump, with 15.0.0 and 15.1.0 both cut 2026-06-29. Breaking changes NOT
  reviewed; recorded as such. What *was* checked is that the structures this
  skill depends on survived: `websocket:` is still a top-level values block
  (line 66) and `replicaCount: 1` is still there (line 183).
- **Chart-repo probing gotcha recorded:** `gh release list -R
  open-webui/helm-charts` is dominated by `15.2.1-dev.N.1` prereleases — six of
  the top six on the day of this pass. Filter `dev` tags or the newest stable is
  invisible.
- **#23733 still OPEN and still unresolved.** Last activity 2026-06-17, but the
  recent thread is off-topic memory-usage discussion, not movement on frame
  amplification — so the skill's centrepiece mitigation remains necessary.
  #15162, #19840, #23650 all still open. Helm chart **#383 now CLOSED
  2026-06-28**.

## Resolved — 2026-05-28

- **Dim 8 PR-list conflation** — SKILL.md L23 Yjs/streaming PR list
  rewritten to match issue-23733.md grouping (delta #23735, replay #23736,
  Yjs #24124/#24126/#24171); previously omitted #24124 and mislabeled the
  delta/replay vs Yjs sets. Iter 1.
- **Dim 9 version freshen 0.9.4 → 0.9.5** (gh-verified latest stable
  v0.9.5, 2026-05-10) — bumped the `≥0.9.5` non-negotiable and current-
  stable annotations in SKILL.md, configuration.md L3 verified-against +
  Sentinel pin, and the helm reference. Iter 2.
- **Dim 9 helm-chart freshen 14.4.0 → 14.6.0** (gh-verified
  open-webui-14.6.0, appVersion 0.9.5, 2026-05-20) — helm-chart.md L3 +
  Recent chart history table gained 14.5.0/14.6.0 rows; sources.md helm row
  re-stamped 2026-05-28. Iter 2.
- **Dim 4 Sentinel-failover validation** — replaced the closing handwave
  with a concrete two-command check (`valkey-cli SENTINEL FAILOVER` →
  `kubectl get endpoints`). Iter 3.
- **issue-23733.md status re-stamp** — 2026-05-10 → 2026-05-28 (OPEN,
  upstream-updated 2026-05-27 per gh); four-vs-five PR count reconciled to
  five. Iter 4.
- **Dim 6 §23733 restatement trim** — known-issues.md §23733 body collapsed
  to a one-line pointer at issue-23733.md (removed the third restatement of
  the bug story). Iter 5.
- **Dim 7 single-stream caveat** — check-amplification.sh interpretation
  block now states the chunk-size brackets are per single stream and must
  be divided by concurrent-stream count. Iter 5.
- **Freshen re-stamp** — sources.md verification log + status sentence
  (#23733 OPEN, #23987 CLOSED, all five Yjs/delta PRs CLOSED-unmerged) and
  known-issues.md header re-stamped to 2026-05-28 with gh evidence noted.

## Resolved — 2026-05-10

- **Dim 9 hard-fail (description > 1024)** — split frontmatter into
  `description` (592 chars) + `when_to_use` (853 chars), trimmed
  low-value triggers to fit combined ≤1536. Iter 1.
- **Dim 9 staleness cap (sources.md no Last verified dates)** — added a
  per-source-group verification log table with `Last verified: 2026-05-10`
  on every row. Iter 2.
- **Dim 6 Boris cap (13-step strict-workflow-scaffolding playbook)** —
  collapsed numbered "Production playbook" into a 5-item "non-negotiables"
  bullet list focused on irreducible facts. Iter 3.
- **Dim 3 second-person uses (~25 instances)** — converted to imperative
  across SKILL.md and all 6 reference files; only the verbatim maintainer
  quote retains "you" (legitimate exception). Iter 4.
- **Dim 7 missing verification script** — added
  `scripts/check-amplification.sh` that samples `valkey-cli MONITOR` for
  Socket.IO PUBLISH ops with heuristic CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE
  estimate; cross-linked from SKILL.md reference index. Iter 5.
- **Simplification** — unified the secret-material code block into the main
  env block (no separate ```bash``` fence, fewer scaffolding paragraphs).
  Iter 6 (kept on simplification-tie grounds).
- **Freshen F1: #23987 closed** — Sentinel coroutine regression fix shipped
  in 0.9.4 (closed 2026-05-08, release 2026-05-09). Updated triage table,
  known-issues entry, recommendation table, and verification log.

## Score progression

| iter | self | blind | delta-self | status | description |
|---|---|---|---|---|---|
| 0 | 73 | 83 | — | baseline | initial state |
| 1 | 76 | — | +3 | keep | split desc → ≤1024 chars; fix Dim 9 hard-fail |
| 2 | 79 | — | +3 | keep | sources.md verification log with `Last verified: 2026-05-10` |
| 3 | 86 | — | +7 | keep | collapse 13-step playbook → 5 non-negotiables (Boris cap lifted) |
| 4 | 88 | — | +2 | keep | convert second-person to imperative across skill |
| 5 | 89 | — | +1 | keep | add scripts/check-amplification.sh + reference-index pointer |
| 6 | 89 | — | 0 | keep (simpler) | unify secret block into main env block |
| F1 | 89 | 93 | 0 | keep (freshen) | #23987 closed; fix shipped in 0.9.4 |

Cumulative: self +16, blind +10. All dims ≥9 in the blind score.

## Next-run recommendations

When `skill-improver` runs again on this skill:

- **Re-probe #23733 status** — if the Yjs-document-streaming PRs land, the
  centerpiece bug story changes and `CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE`
  may become unnecessary.
- **Re-probe Open WebUI version** — line numbers in sources.md will drift
  past 0.9.4. Refresh against new HEAD.
- **Stamp the verification-log dates** — if no content changes, just bump
  `Last verified:` to the run date so the staleness cap stays clear.
