# Sources — vllm-gemma-4-31b

External references cited by SKILL.md and `references/*.md`. Each row carries
the upstream URL, classification, last verification date, and pinned version
or git ref where applicable. Re-probe via `/skill-improver freshen vllm-gemma-4-31b`.

## Authoritative model + template sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r01 | https://huggingface.co/google/gemma-4-31B-it/raw/main/chat_template.jinja | hf-model | 2026-07-21 | sha256:`ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4` (18683 B; **DRIFTED AGAIN** — third distinct hash in three passes: `94899c0f…` 16934 B 2026-04-30 → `36e3a42e…` 17466 B 2026-05-28 → this). Now carries a Google header comment: *"Published: 2026-07-09 — Fixed tool-calling loops, turn closures, and thinking content-ordering."* |
| r02 | https://huggingface.co/cyankiwi/gemma-4-31B-it-AWQ-4bit | hf-model | 2026-07-21 | Repo `lastModified` 2026-07-03, but that commit is *"Fix Model Size: 38.94 GB -> 20.90 GB"* (README only). Its `chat_template.jinja` hashes `94899c0f…25bff413` — **byte-identical to the 2026-04-30 canonical**, last touched by the 2026-04-30 `Upload folder using huggingface_hub` commit. 114 lines behind canonical. 951,914 downloads. |
| r03 | https://huggingface.co/RedHatAI/gemma-4-31B-it-speculator.eagle3 | hf-model | 2026-07-21 | `lastModified` 2026-04-14 — untouched since the original audit. Ships no `chat_template.jinja` at all (siblings: README, config.json, config.py, model.safetensors), so the staleness finding in r02 does not apply to it. Vanilla EAGLE3, still no P-EAGLE prep tokens. |

## vLLM engine sources

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r04 | https://github.com/vllm-project/vllm | github | 2026-07-21 | v0.25.1 latest (2026-07-14); then v0.25.0 (07-11), v0.24.0 (06-29), v0.23.0 (06-15), v0.22.1 (06-05), v0.22.0 (05-29), v0.21.0 (05-15). Skill's "0.20+" floor still valid, but the **audit baseline v0.20.0 is now five minors old** — the measured numbers in `bench-numbers.md` have not been re-run against 0.25. |
| r05 | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/engine/arg_utils.py | github-source | 2026-07-21 | v0.25.1 (blob sha `c7a9335bbeb0535d87a93e407fb874c3d2efb65b`). `get_batch_defaults` now at lines **2397-2478** (was 2207-2288 at v0.20.0). GPU branch logic **unchanged**: `device_memory >= 70*GiB_bytes and "a100" not in device_name` → 16384/8192 tokens, 1024 seqs; H100 and H200 still share it. New since v0.20.0: a `current_platform.is_tpu()` sub-branch (V6E/V5E) inside the same function — so "only hardware-aware default" now means *only function*, not *only branch*. |
| r06 | https://github.com/vllm-project/vllm/blob/v0.25.1/vllm/v1/spec_decode/llm_base_proposer.py | github-source | 2026-07-21 | v0.25.1 (blob sha `756c5f3b3717204f45744a3d57fa8dc6d188d54c`). P-EAGLE requirement intact at lines 352-366 (was 341), but the **check order reversed**: `dflash_config["mask_token_id"]` is now tried *first*, then `pard_token`, then `ptd_token_id`. Sets `self.parallel_drafting_token_id`; raises the three-name `ValueError` otherwise. |

## vLLM issue / PR citations

| Ref | URL | Classification | Last verified | Pinned |
|---|---|---|---|---|
| r07 | https://github.com/vllm-project/vllm/issues/35467 | github-issue | 2026-07-21 | still OPEN — "non-optimal performance of `linear` for medium batches" (B200 numerical proof of HBM-bandwidth-bound saturation). Latest comment: *"FI impl is ready. Have to check current state"* — a fix is in flight, so re-probe next pass. |
| r08 | https://github.com/vllm-project/vllm/issues/22780 | github-issue | 2026-07-21 | **CLOSED `NOT_PLANNED` 2025-12-14 by the stale bot** (*"automatically closed due to inactivity"*), NOT by a fix. The prior "closed" note read as resolved; it is not. The BnB-4bit concurrency regression is unaddressed upstream, which *strengthens* this skill's AWQ-over-BnB recommendation. See skill-improver `freshen-patterns.md` §3.0. |
| r09 | https://github.com/vllm-project/vllm/issues/6801 | github-issue | 2026-07-21 | OPEN but **stale-bot-marked** — "automatically marked as stale… will be closed if no further activity within 30 days." Expect it CLOSED/`NOT_PLANNED` by the next pass; that will mean abandonment, not delivery. The Pareto-knob framing it supports stands on its own. |
| r10 | https://github.com/vllm-project/vllm/pull/17885 | github-pr | 2026-07-21 | MERGED 2025-05-11 — "[Perf] Use small max_num_batched_tokens for A100". Still the origin of the A100 carve-out; its `NOTE(Kuntai)` comment survives verbatim in v0.25.1. |

## Notes

**The staleness thesis is no longer inferential (2026-07-21).** The prior two
passes argued "the quant's template is probably stale because canonical keeps
moving." This pass diffed them directly: `cyankiwi`'s file is byte-identical to
the 2026-04-30 canonical and 114 lines behind the current one. That converts the
skill's central recommendation — always `--chat-template` the canonical pull —
from a precaution into a measured defect list (see SKILL.md fact #3).

**How to re-probe r01/r02 next pass** (the whole finding is four commands):

```bash
curl -sSL -o /tmp/g4.jinja  https://huggingface.co/google/gemma-4-31B-it/raw/main/chat_template.jinja
curl -sSL -o /tmp/cy.jinja  https://huggingface.co/cyankiwi/gemma-4-31B-it-AWQ-4bit/raw/main/chat_template.jinja
sha256sum /tmp/g4.jinja /tmp/cy.jinja
diff /tmp/g4.jinja /tmp/cy.jinja | grep -c '^[<>]'     # 114 on 2026-07-21
head -7 /tmp/g4.jinja                                  # Google stamps a Published: date in-file
```

That in-file `Published:` header is new and is the cheapest signal available —
read it before hashing anything.

- **Do not treat any r01 hash as a pin.** Three passes, three hashes. The hash
  chain is kept as *evidence of drift rate*, not as a value to match against.
- **`lastModified` on an HF repo does not mean the weights or template moved.**
  r02 reported 2026-07-03 while its template had not been touched since
  2026-04-30 — the commit edited the README. Read
  `/api/models/<repo>/commits/main` titles, not the timestamp.
- **r05/r06 are now re-pinned at v0.25.1** (the honest gap the 2026-05-28 pass
  flagged is closed). Both claims survived five minors; only line numbers and
  the P-EAGLE check *order* moved. Cite symbols, not lines — the line-number
  pins have been re-written twice now for zero semantic change.
- **Still not re-probed:** the EAGLE3 / TRITON_ATTN / spec-config CLI surface
  against 0.21–0.25, and the `bench-numbers.md` measurements, which remain
  v0.20.0 observations. Re-running those needs GPU time, not a probe.
