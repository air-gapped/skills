# Improvement backlog

Carries open quality findings across `/skill-improver` runs. Items here are ceiling-hit issues that require multi-file restructure, mode switching, online re-probing, or author judgment — not single-iteration `improve` mutations.

## Open

- **Re-resolve open-webui line numbers against v0.9.5** — Dim 8/9 —
  references/sources.md rows 1-3 (utils.py:677 / external.py:14 / config.py
  line numbers). The pins are valid for v0.9.2 (commit `8dae237a0bfd`,
  confirmed real via `gh` on 2026-05-28) but upstream latest is now v0.9.5
  (2026-05-10). Line numbers may have drifted across v0.9.3/v0.9.4/v0.9.5.
  Cannot be applied in one iteration because it requires checking out the
  v0.9.5 tree and re-resolving each line by function name — an online/clone
  step, not a text edit. The function-name anchors in the rows already
  mitigate the drift for readers, so this is low-priority polish.

## Resolved — 2026-07-21 (freshen)

Nine refs re-probed. One upstream minor jump, one confirmed-still-broken
upstream bug, and one file that quietly got restructured.

- **open-webui v0.9.5 → v0.10.2** (2026-07-01, via v0.9.6/v0.10.0/v0.10.1). All
  cited line numbers **re-resolved against the v0.10.2 tag** rather than carried
  forward with a warning: `generate_openai_batch_embeddings` 677→845,
  `get_embedding_function` 905→1073, `asyncio.gather` fan-out 963→1138,
  `ExternalReranker` 14→13, `predict` 27→26, `requests.post` 50→49.
- **`config.py` was restructured, not appended to.** Every RAG key moved *down*
  by roughly two thousand lines (RAG_EMBEDDING_BATCH_SIZE 2948→994,
  CONCURRENT_REQUESTS 2960→1000, RERANKING_ENGINE 2972→1008,
  EXTERNAL_RERANKER_URL 3001→1023) in a file that is still 3136 lines long. A
  line number that moves *backwards* by that much is the signature of a
  reorganisation, and it is why the version note now says to resolve by symbol
  name and never by remembered line.
- **Defaults re-read and unchanged**: `RAG_EMBEDDING_CONCURRENT_REQUESTS` still
  defaults to `0`, and both reranker keys still default to empty strings — so
  the skill's "you must set these explicitly" framing holds.
- **`external.py` still uses synchronous `requests.post`**, not httpx, at 69
  lines. The blocking-reranker characterisation the skill builds on survives the
  0.10 jump intact.
- **The `encoding_format: None` gotcha is still live.** PR 25395 (fix) and 25698
  (revert two days later) are unchanged, issue 25388 is still closed-but-broken,
  and the general fix — **PR #24277, still OPEN** — has not merged. So the
  per-model `encoding_format` pin remains *necessary*, not merely defensive.
  Recorded #24277 in both `sources.md` and `gotchas.md` as the single tell for
  when the workaround can be retired.
- **TEI is unchanged at v1.9.3** (2026-03-23, no release in ~4 months), and its
  two CLI defaults re-resolved to lines **60 and 82 exactly** as claimed. The
  Blackwell image-tag row was not re-probed and is left stamped 2026-05-28
  rather than given a date it did not earn.

## Resolved — 2026-05-28

- **Spec hard-fail fixed: `description` 1036 → 1010 chars** (Dim 9 cap at 3
  lifted). The frontmatter `description` exceeded the 1024-char spec cap;
  trimmed wording ("as a proxy in front of" → "proxying"; "↔" → "-";
  shortened the closing clause) without dropping any trigger phrase.
- **Listing budget restored: combined description+when_to_use 2151 → 1531
  chars** (under the 1536 truncation budget, +5 headroom) (Dim 1). Trimmed
  `when_to_use` 1115 → 521 by removing trigger phrases already implied by
  `description` (kept the highest-signal distinctive ones + the NOT-for
  boundary), so trailing triggers and the exclusion clause no longer
  truncate.
- **Blackwell GPU-arch rows made concrete** (Dim 5). Replaced the
  "check current TEI release tags" placeholder in gotchas.md §5 with the
  three real image tags from the TEI README (verified 2026-05-28):
  `100-1.9.x` (B200/GB200, SM 10.0), `120-1.9.x` (RTX 50xx/PRO 6000,
  SM 12.0), `121-1.9.x` (DGX Spark GB10, SM 12.1, multi-arch).
- **Freshen**: re-stamped sources.md rows 1-10 `Last verified: 2026-05-28`
  after `gh`-re-confirming every pin (open-webui v0.9.2 / commit
  8dae237a0bfd, litellm 934ecdca78, TEI 5bc4d88, PRs 25395/25698, issue
  25388). Added a version note recording that open-webui latest is now
  v0.9.5 (benign drift) and that TEI latest release is v1.9.3. Added a new
  sources row for the TEI Blackwell image-tag table.

## Resolved (pass 3, 2026-05-01)

Freshen pass. All 11 sources verified against fresh local clones (open-webui
v0.9.2, litellm @934ecdca78, text-embeddings-inference @5bc4d88) plus `gh`
for PR/issue state plus WebFetch for the HF discussion.

- **Dim 9 cap lifted: 6 → 9-10** — sources.md gained `Last verified` +
  `Pinned` on every row.
- **Open WebUI line numbers updated** (single version-drift, multi-site fix):
  utils.py 560-639 → 677; utils.py 858-913 → 905 + asyncio.gather 963;
  external.py 38-79 → 14 (predict 27); gotchas utils.py:584 → 698,
  external.py:49 → 50.
- **Verified fresh, no content change:** LiteLLM PR #25395 (MERGED 2026-04-12),
  PR #25698 (revert, MERGED 2026-04-14), issue #25388 (CLOSED 2026-04-14);
  TEI defaults 32/512; TEI routes present; HF disc #9 max_length=1024 claim.

Pass 1 (2026-05-01, restructure) and Pass 2 (2026-05-01, 5-iter improve loop,
blind 90/100) — see git history if tracked.
