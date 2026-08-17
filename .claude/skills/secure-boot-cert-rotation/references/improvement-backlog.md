# Improvement backlog — secure-boot-cert-rotation

Carries ceiling findings across `skill-improver` runs. Read in Phase 0; updated in Phase 6.

## Open

- **Dell KB 000402373 per-generation BIOS minimums — unverifiable by agent, needs a human read.** Dell serves
  403 to automated fetches, and the one summarized read obtained on 2026-08-18 was internally inconsistent
  (labelled R260/R360/T160/T360 as 14G; they are 16G). The table in `dell-poweredge.md` therefore still carries
  its 2026-06-01 numbers and its "verify in KB 000402373" fence. **Do not update these from a scraped or
  AI-summarized read** — a wrong BIOS minimum sends someone to flash the wrong firmware. Needs an authenticated
  manual read of the live KB; also confirm whether 17G ships 2023 certs pre-installed (claimed, unconfirmed).
- **Dim 10 (Differentiation) hard-capped at 8 by the Negative-Transfer Gate.** No `evals/evals.json`, no
  `benchmark.json`, so net value over no-skill is unmeasured. Highest-value remaining action per two
  independent blind scorers. Needs an eval set (audit-triage cases across the three surfaces) and a
  with-skill/without-skill `delta_pass_rate`, not more prose.
- **Dim 7 (Resource Quality) — the audit greps are scriptable and repeated in three files.** The same
  `mokutil`/`efi-readvar` verdict logic appears in SKILL.md, `linux-bare-metal.md`, and `harvester-vms.md`.
  A bundled `scripts/audit-secureboot.sh` emitting NEEDS UPDATE / GOOD per host would remove the duplication
  and raise actionability. Deferred: worth doing only if the shell stays genuinely portable across the
  Dell/whitebox/guest split rather than growing per-surface branches.
- **Dim 6 (Simplicity) — House Rules ↔ routing/references overlap.** Unchanged judgement from the 2026-06-01
  pass: both blind agents call these "standing instructions, not waste", and they carry the hard-won lessons
  driving Dim 10. Lifting Dim 6 needs author judgment on which rules are genuinely redundant, not a mechanical
  dedup. Note House Rule 7 grew this pass (forced-update damage) — re-check length if it grows again.
- **Watch item with a real trigger, not a vague one: the dbx signing cutover.** Microsoft still signs `dbx`
  with the 2011 KEK (verified by parsing the June 2026 payload). When a dbx push appears signed by
  `KEK 2K CA 2023`, the revocation-freeze section in `mechanism.md` and the timeline in
  `gotchas-and-decisions.md` both flip from "not yet started" to live, and the skill's urgency changes. Re-probe
  the signer on the next freshen.
- **Second watch item: the first x86_64 2023-only shim.** aarch64 already crossed. No x86_64 distro has dropped
  the 2011 signature and none has published a date; Ubuntu has not shipped a new shim at all. The next
  CVE-driven shim respin is the event to catch.

## Resolved this pass (2026-08-18 — freshen + improve, ~11 weeks after the previous pass)

Ten changes kept, one per commit. Baseline blind **84/100**.

Freshen (evidence-driven):
- **Forced db updates have permanently damaged some machines** — SKILL.md said the real risk was transient
  unbootability "not hardware damage". Corrected against the LWN post-expiry retrospective, scoped to the
  forced-update path, with the High Confidence Buckets dataset as the pre-force-push check.
- **The June expiries passed with no incident** — the skill's central reassurance moved from forecast to
  dated, evidenced record; PCA 2011 (2026-10-19) still ahead.
- **The revocation freeze has not started** — the June 2026 dbx payload parses as 2011-KEK-signed, so machines
  without the 2023 KEK are not missing revocations. Abstract risk replaced with an artifact-level proof and a
  named trigger.
- **The 2023-only shim cliff arrived on aarch64** — resolved the skill's own "verify it has landed" hedge with
  a per-distro status table; Red Hat shipped dual-signed 2026-06-10, Ubuntu shipped no shim at all.
- **Stock Ubuntu fwupd cleared the 2.0.8 floor** — 2.0.20 is in both LTS `-updates` pockets, so the
  "too old, install the snap" advice was retired and the coverage-vs-version confusion untangled.
- **Harvester GA is 1.8.2**; issue #7343 confirmed fixed in 1.8.0 GA (close checked against freshen rule 3.0 —
  genuine QA verification, not a stale-bot close).
- **Event ID citation corrected** — "media is write protected" was not Microsoft's wording for 1795, and
  neither ID lives on the known-issues page; repointed to the DB/DBX update events article.
- **sources.md re-stamped** 2026-06-01 → 2026-08-18, 8 rows → 21, with Dell KB 000402373 deliberately left
  stale-and-flagged rather than updated from an unreliable read.

Improve (blind-flagged):
- **Dim 5** — added the backup + recovery ladder for a failed enrollment, including the `efi-readvar`
  next-higher-key caveat, and two gaps recorded rather than filled (Dell BIOS-rollback semantics; resetting a
  persistent KubeVirt varstore).
- **Dim 2** — TOCs for the three references now over 100 lines, resolving the prior pass's deferred item.
- **Dim 1** — frontmatter rewritten from "CAs expiring" to the actual post-expiry state, funded by trimming
  mechanism narration (combined listing 1486 → 1510 of 1536).

Boris alignment: clean on all three probes (no model-compensation language, 3 scaffold items against a
threshold of 8, no section over 30 lines).
