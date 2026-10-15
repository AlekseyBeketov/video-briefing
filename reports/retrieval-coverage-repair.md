# Semantic retrieval repair — t_081ae46a

## Verdict: blocked, not semantic PASS

Final cached packet v19 completed all five outputs (brief, q05/q06/q07/q08), exit 0. 135 tests pass with no skips here. However, source review of the fresh brief returned 28 supported, 7 partial and 1 unsupported claims. Narrow SR-01/SR-02/SR-03 regressions are resolved; broader source-faithful completion is not established. Dependent rereview t_1d07e629 is not released on a false PASS.

Verifier: this coder gpt-6.1-sol/openai-codex run, independent of Gemma generation/audit, NOT independent implementation review or final project acceptance. One supplied caption source is not independent hardware/identity/release truth. No commit or push.

## Preserved scope and revision

Source: DvSwvJVens8 / captions_api / ru; 566 unchanged segments.

- Raw SHA-256: `940d5b89a1d24b30f256d352f97d3d6624a5f296a1707780b777dbdb17d1e3af`.
- Evaluation SHA-256: `7abd485c1549e336497346a7cf571098a7ca18c8662ddf8f81ad781a0c94d1a1`.
- Branch: `main`; HEAD `4de6fe19a19d55e756ea89cce161aa1a2aa037a6`; uncommitted repairs preserved.
- Code/test/prompt mapping digest: `5b0d2f9e657e4360e9b863834490bcc13c4b6030022cb33a501228b586bdfe32`. Definition and individual hashes: companion JSON report.
- This resume changed briefing/source guards and regressions, plus the reports. Earlier retrieval/grounding/QA/prompt repair remains preserved.
- No extraction/store/raw/evaluation/README/model-config/default-profile-wrapper edits. Twenty protected before/after hashes agree.

## Corrective changes

1. Repair invalid IDs on atomic coverage examples and their quantity entries before folding. Preserve example quantities after citation repair: bogus IDs and folded multi-example ledgers cannot establish a narrow example window.
2. Repair candidates must belong to the supplied inventory and stay inside their per-claim request. Out-of-scope citation repair fails closed.
3. Gate shared- and single-subject transfer of a quantity between source-named alternatives, even under a false-positive support auditor. These are narrow guards, not arbitrary entailment.
4. Retain earlier software provenance for conditional CUDA interpretations. Vendor omission uses an exact source product phrase and a bounded vendor bridge, not external product knowledge or ASR equivalence. CUDA remains inference.
5. Preserve completed, bounded source sentences explicitly qualifying a named product as untested/unknown-performance. Only the exact product or its immediately preceding sentence in the same continuous run can anchor the quote. No arbitrary neighbouring padding or cross-gap joining; the auditor cannot silently erase the preserved qualification.

## Explicit defect closure

SR-01: original v8 claim 13 directly compared to source. Missing s00142 carries 5.1B active/token. Fresh v19 brief claim 14 retains 117B total, 5.1B active/token and 80GB. Atomic citation/quantity lifecycle and false-positive omission regressions pass.

SR-02: original v8 claim 19 directly compared to source. s00278-s00283 assigns 200B to DJX/DGX; s00300 names RTX separately. Shared- and single-subject transfer guards and real-source regressions pass. No shared 200B claim recurs in v19. This does not establish arbitrary roles elsewhere.

SR-03: fresh brief and q05 keep CUDA as inference with both the incomplete final condition and earlier NVIDIA software platform (s00405-s00409). Vendor-omission/bridge regressions pass. No verbatim CUDA caption invented.

## Final execution

    RETRIEVAL_SMOKE_DIR=retrieval-repair-semantic-v19 uv run --frozen python artifacts/private/run_retrieval_repair_smoke.py > artifacts/private/retrieval-repair-semantic-v19.log 2>&1

Each output has its actual artifact SHA-256, elapsed time, generation/support metadata and evidence IDs recorded in the companion JSON and private runs.json. Raw hash agrees in all five outputs. Zero extractor calls; uv offline; eleven allowed loopback Ollama connections; zero guard denials. Existing inference is cloud-backed: daemon egress/cost were not measured. This is NOT a fully offline or zero-cost claim.

Captured requests contain no evaluator field keys, expected_points/reference ranges or evaluation.json reads. A field-key scan is not universal prose-leakage proof; runtime guards have no frozen target quantities, reference/video IDs or rubric table.

Eight core retrieval ranges pass at the same budget. NOT all frozen ranges pass: q05 self-introduction r0030-r0031 remains 0/2. Precise surname/identity/per-segment linkage stays unverified; attribution is neutral.

## Full source check and remaining defects

All 56 returned substantive claims were read against exact cited original captions. Full texts, evidence IDs and individual notes are in `reports/retrieval-coverage-repair.json`. Exact citation inspection: `artifacts/private/retrieval-repair-semantic-v19/source-inspection.txt`; helper never participates in generation.

    brief: 36 claims — 28 supported, 7 partial, 1 unsupported
    q05:     8 claims — 8 supported
    q06:     7 claims — 7 supported
    q07:     4 claims — 3 supported, 1 partial
    q08:     1 claim  — 1 supported; abstained=true

B-05, unsupported brief claim 17: the output assigns the 38 tok/s GPT OSS 120B run to Linux. s00382-s00389 says Linux can go further in GPU memory allocation, then describes the run WITHOUT establishing its OS. Gemma audit returns explicit. IDs/recall/exit 0 do not prove this OS-to-benchmark relationship.

B-06: a03/a05/a08 remain partial. Other remaining issues: required-versus-consensus 70–90B paraphrase, lost vendor-report provenance for 14 tok/s, missing as-a-rule price hedge, illustrative archive/RAG wording, overbroad closed-laptop inference. Apple-specific large GPU-memory-pool explanation is still too heading-level. Repetitive headings/numeric inventory mean concision is also partial.

a04 now retains 55–60 tok/s medium-context conditions, context decline, and source lack-of-testing/performance/heat/battery qualification. a06 retains sharding versus physical memory, delays, adding nodes and API abstraction. a07/q07 separate available NAS search/assistant/container capabilities from promised full-file search and its end-Q3-2026 date. This is a historic source-time promise, NOT verified release status on October 8, 2026. q08 invents no measurements and does not imply audio/frame inspection.

## Checks

    uv run --frozen pytest                            exit 0 — 135 passed
    uv run --frozen python -m compileall -q src tests  exit 0
    git diff --check                                 exit 0

Exact outputs: private v19 `pytest.txt`, `compileall.txt`, `diff-check.txt`. Private-source tests explicitly skip if the supplied cache is absent elsewhere; they ran here.

## Failed/invalidated attempts retained

- v16: out-of-scope per-claim citation repair, failed closed; original traceback/requests retained.
- v17: executor edited briefing.py during inference, violating the protected fingerprint. NOT final smoke evidence, not selected for PASS.
- v18: brief completed; q05 exceeded bounded malformed-JSON retries. No synthesized/fixed expected response substituted.
- Prior history remains in companion JSON and `artifacts/private/retrieval-repair-v15-report-snapshot.json`.
- v19 is the final single packet on the unchanged code, reported WITH its semantic failure, not best-of-selected as success.

## Needed decision

Independent OpenAI verification and targeted deterministic gates were already authorized and exercised. Do not request that permission again. They expose, rather than solve, arbitrary false-positive generated relationships.

Choose the next stage: switch actual generation/support audit to an already available backend under bounded budget, or approve a source-first extractive final numeric/non-numeric clause design. No new paid service, model/profile/credential edits or open-ended repeated sampling are inferred. Until B-05/B-06 are resolved by a fresh source-supported packet, retain t_081ae46a as blocked and keep downstream rereview/project acceptance gated.
