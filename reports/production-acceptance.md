# Video Briefing: production acceptance smoke

Date: Wednesday, October 7, 2026. This is a bounded live workflow smoke, not a declaration that the project passed the independent acceptance reviews. The recorded spec and code reviews are FAIL / REQUEST_CHANGES (`reports/spec-review.md`, `reports/code-review.md`, `reports/review-findings.json`).

## Implemented winner and real source

The exercised path is the actual project CLI with `captions_api`, using the supplied URL `https://www.youtube.com/watch?v=DvSwvJVens8`, Russian timed captions, and the existing cloud-backed Ollama model. It loaded the already saved 566-segment transcript (`youtube-transcript-api 1.2.4`), whose SHA-256 is `940d5b89a1d24b30f256d352f97d3d6624a5f296a1707780b777dbdb17d1e3af`. Briefing metadata returned the same source hash. The two Q&A invocations also returned that same hash and segment count; they used the saved source path rather than triggering extraction. A code-path regression test asserts cached Q&A never calls the extractor. No raw transcript is included here.

The requested model was `gemma4:31b-cloud`; the endpoint reported the actual model as `gemma4:31b`, and metadata marked it cloud-backed. The final live brief took 19.57 seconds across four inference calls, with 22,199 prompt tokens and 5,305 completion tokens reported across per-call usage; the result metadata records each call and reports usage complete. The exact source-bound JSON is retained in ignored `artifacts/private/production-brief.json`. Do not interpret these timings as a repeatable performance benchmark.

## Bounded content check

The produced Russian brief covers UMA/zero-copy, Apple/NVIDIA/AMD ecosystems, VRAM/model size, multi-machine clusters, and AI NAS; it marks one recommendation as assistant inference and cites timed segment IDs. A programmatic check found 105 citation references, all resolving to IDs in the saved source; no unknown IDs. This validates referential integrity, not semantic correctness. The brief still contains claims requiring human context review, and the fixed evaluation review identifies missing or over-compressed qualifications; this smoke does not close those review findings.

Author-emphasis follow-up (fixed q01): the answer says the author emphasizes memory capacity/model fit over peak speed and states unified memory trails GDDR7 in peak speed. It returns claims with `s00126`–`s00129` around 315–322 seconds and `s00150`–`s00154` around 376–385 seconds. Live CLI inference time: 2.35 seconds.

Unsupported-answer follow-up (fixed q08): asked for exact measured ASUS RTX Spark temperature and battery hours. The answer abstained: “В сохранённой расшифровке не найдено подходящего подтверждения; это не доказывает, что тема нигде в видео не упоминается.” It returned no factual claims and reused the same transcript hash. Human evaluation had checked all 566 reference captions and found no such measured values, but this workflow did not inspect all video frames/audio; the abstention is therefore bounded to transcript evidence. Live CLI inference time: 0.97 seconds.

The runnable skill wrapper was exercised on q08 and returned the structured cached answer. `doctor` reported Python 3.13.14, Ollama reachable, captions client 1.2.4, Bun 1.4.2, summarize 0.25.1, and Baoyu source present.

## Verification and repository state

- `uv run --frozen pytest`: 37 passed.
- `uv run --frozen python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- CLI `doctor`, root help, and brief help: passed.
- No OpenResearch runs were started; immutable comparison branches/records were not changed.
- No remote operations, credential/cookie/proxy use, paid fallback, or raw transcript/media publication.

`artifacts/private/production-brief.json`, `production-q01.json`, and `production-q08.json` are local ignored evidence, not public artifacts. The old comparison runs and their metrics apply only to their recorded implementation revision, not automatically to later hardening changes. Project-level acceptance remains NOT READY until the independent audit closes remaining semantic grounding/retrieval and other documented findings.
