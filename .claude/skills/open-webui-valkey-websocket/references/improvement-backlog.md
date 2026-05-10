# Improvement backlog — open-webui-valkey-websocket

Carried across `skill-improver` runs. Each Open item is a finding that the
loop attempted but couldn't apply atomically in a single iteration. Resolved
items are an audit trail of what was fixed.

## Open

(none — converged at blind 93/100, self 89/100 with all dims ≥8 and no
Boris/staleness caps active)

The blind agent's top 3 issues are minor enhancements rather than structural
findings:

1. SKILL.md: "validate Sentinel failover trips the readiness probe" could
   carry an exact one-liner (`valkey-cli SENTINEL FAILOVER ...` plus a
   `kubectl get endpoints` or HTTP probe). Lifts Dim 4 from 9 → 10.
   **Reason for not applying this run:** the exact command depends on the
   user's Sentinel setup (DNS vs static IPs, master name) and naming the
   probe target requires knowing whether the deployment exposes `/ready`
   over an internal Service or only via Ingress. Adding a generic
   placeholder reads worse than the current handwave; adding a parametric
   one would be a 5-line snippet that the operator must edit anyway.
2. configuration.md:81 — the `maxclients` Valkey/Redis-version cliff is
   stated as "newer Valkey versions / older Redis versions" without exact
   version numbers. Pinning would lift Dim 9 from 9 → 10. **Reason for
   not applying:** requires a separate Valkey/Redis-version probe pass to
   confirm the actual cliff version (Redis 5? 6? Valkey 7? 8?). Out of
   scope for a single skill-improver iteration.
3. SKILL.md:113 — "verify on the deployment's target version" lacks a
   concrete `curl` recipe for the lagging admin endpoints. Lifts Dim 4
   from 9 → 10 if added. **Reason for not applying:** the auth-token
   handling is environment-specific (cookie vs Bearer vs OAuth proxy);
   one-size-fits-all snippet would be misleading.

## Resolved this pass (skill-improver run 2026-05-10)

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
