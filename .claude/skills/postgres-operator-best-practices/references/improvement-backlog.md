# Improvement backlog — postgres-operator-best-practices

Carries ceiling findings across skill-improver runs. Append-only history.

## Open

- **No trigger-mode measurement yet** (Dim 1, empirical). The description
  and `when_to_use` were written by hand and sized by inspection, never
  measured. Run `/skill-improver trigger postgres-operator-best-practices`
  to get actual fire/silence rates — the sibling skill shares much of this
  trigger space, so the run needs to check both directions of confusion
  (this skill firing on migration queries and vice versa), not just this
  skill's own recall.
- **No quality-scoring run yet** (all dims). Created 2026-08-25 from a
  research pass, not from an improve loop; no blind baseline exists.

## Resolved this pass — 2026-08-25

Initial build-out from the raw research findings file.

- Split `findings-2026-08-25.md` (483 lines) into four scoped references:
  `upgrade-v1-v2.md`, `dcs-endpoints.md`, `operations.md`, `sources.md`.
  SKILL.md pointers rewritten from section anchors to file paths.
- `sources.md` restructured into the house per-URL table format so freshen
  mode can probe rows and stamp them individually.
- Site inventory removed from skill content per the standing convention that
  cluster names, namespaces, hostnames and versions-at-site never ship in a
  skill; the generic hygiene items it implied were lifted into
  `operations.md` §"Configuration hygiene worth auditing".
- Duplicated #3170 paragraph removed from SKILL.md (stated twice, once in
  the v2.0.1 defect list and again under the issue-tracker traps).
- Release/issue claims independently re-verified against the GitHub API
  before landing: release lists for both operators enumerated unfiltered,
  and seven issue numbers checked for state and title.
