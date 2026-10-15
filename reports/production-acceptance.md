# Video Briefing: production acceptance smoke

> Historical smoke from October 7, 2026. It records an earlier implementation snapshot and is not the current project-readiness or ASR-installation status. See the root README for current setup instructions.

Date: Wednesday, October 7, 2026. This is a bounded live workflow smoke, not a declaration that the project passed the independent acceptance reviews. The recorded spec and code reviews are FAIL / REQUEST_CHANGES (`reports/spec-review.md`, `reports/code-review.md`, `reports/review-findings.json`).

## Implemented winner and real source

The exercised path is the actual project CLI with `captions_api`, using the supplied URL `https://www.youtube.com/watch?v=DvSwvJVens8`, Russian timed captions, and the existing cloud-backed Ollama model. It loaded the already saved 566-segment transcript (`youtube-transcript-api 1.2.4`), whose SHA-256 is `940d5b89a1d24b30f256d352f97d3d6624a5f296a1707780b777dbdb17d1e3af`. Briefing metadata returned the same source hash. The original Q01/Q08 files were found to be empty during independent review, so they did not substantiate the earlier claim of retained Q&A outputs. They have now been replaced by actual cached wrapper stdout from the bounded repair smoke described below; all four new invocations returned that same hash and segment count. A code-path regression test asserts cached Q&A never calls the extractor. No raw transcript is included here.

The requested model was `gemma4:31b-cloud`; the endpoint reported the actual model as `gemma4:31b`, and metadata marked it cloud-backed. The final live brief took 19.57 seconds across four inference calls, with 22,199 prompt tokens and 5,305 completion tokens reported across per-call usage; the result metadata records each call and reports usage complete. The exact source-bound JSON is retained in ignored `artifacts/private/production-brief.json`. Do not interpret these timings as a repeatable performance benchmark.

## Bounded content check

The produced Russian brief covers UMA/zero-copy, Apple/NVIDIA/AMD ecosystems, VRAM/model size, multi-machine clusters, and AI NAS; it marks one recommendation as assistant inference and cites timed segment IDs. A programmatic check found 105 citation references, all resolving to IDs in the saved source; no unknown IDs. This validates referential integrity, not semantic correctness. The brief still contains claims requiring human context review, and the fixed evaluation review identifies missing or over-compressed qualifications; this smoke does not close those review findings.

Author-emphasis follow-up (fixed q01, regenerated October 7, 2026 at 11:07:55 UTC): the retained answer describes redesigning memory architecture for local LLMs rather than merely adding an NPU, emphasizes model fit over peak speed, and states unified memory trails GDDR7 in peak speed. Its three claims cite `s00151`–`s00154`, `s00126`–`s00129`, and `s00126`–`s00128`. Cached Q&A elapsed time: 2.240466 seconds. Actual stdout: ignored `artifacts/private/production-q01.json` (3,803 bytes; file SHA-256 `163c2d758eb04c111018e75034b3157651de126fa0c83080847c705c444c5fc1`). The earlier 2.35-second result was not retained in that file and is not presented as verified evidence for this repair.

Unsupported-answer follow-up (fixed q08, regenerated October 7, 2026 at 11:07:57 UTC): asked for exact measured ASUS RTX Spark temperature and battery hours. The answer abstained: “В сохранённой расшифровке не найдено подходящего подтверждения; это не доказывает, что тема нигде в видео не упоминается.” It returned no factual claims and reused the same transcript hash. Human evaluation had checked all 566 reference captions and found no such measured values, but this workflow did not inspect all video frames/audio; the abstention is therefore bounded to transcript evidence. Cached Q&A elapsed time: 0.785581 seconds. Actual stdout: ignored `artifacts/private/production-q08.json` (1,293 bytes; file SHA-256 `1b4e46e4c4c7d1ccad4f39ac5cb170812baf4933e4a698d69a33ed0609767b09`). The earlier 0.97-second result was not retained in that file and is not presented as verified evidence for this repair.

The runnable skill wrapper was exercised on q08 and returned the structured cached answer. `doctor` reported Python 3.13.14, Ollama reachable, captions client 1.2.4, Bun 1.4.2, summarize 0.25.1, and Baoyu source present.

## Citation boundary repair smoke (t_4eec35ee)

The installed default wrapper and the checkout wrapper were both exercised on the review's exact NAS question. Both returned the product-identity claim with `s00497`–`s00500`, now including the caption containing “Mini Sform N5” before the “Max” continuation. Actual installed-wrapper stdout is retained in ignored `artifacts/private/production-nas-citation-repair.json` (3,882 bytes; SHA-256 `b62edbaedc453a7e30f50349355ffe51b44d55fb7a005ac98fd240a85d8f4a75`); checkout stdout is retained separately. These are real model results, not constructed JSON. No new brief/extraction or OpenResearch run was started.

The four new runs used process-local guards that deny extractor imports/calls and Python network destinations other than the configured `127.0.0.1:11434/api/chat`; `UV_OFFLINE=1` prevents uv dependency network access. Each run recorded guards loaded in both wrapper and CLI processes, one allowed Ollama connection, and zero guard denials. Source raw/bundle file hashes were unchanged before/after every run. This means no transcript extraction/network access, NOT network-free inference: the existing Ollama model remains cloud-backed, and daemon egress is not measured by Python audit hooks. Exact commands, environment, results and limitations are recorded in `reports/citation-boundary-repair.md` / `.json`; private logs and runner remain ignored.

## Verification and repository state

- `uv run --frozen pytest`: 45 passed after this repair (previous hardening run: 37).
- `uv run --frozen python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- CLI `doctor`, root help, and brief help: passed.
- No OpenResearch runs were started; immutable comparison branches/records were not changed.
- No remote operations, credential/cookie/proxy use, paid fallback, or raw transcript/media publication.

`artifacts/private/production-brief.json` is the previously retained brief, not regenerated by this repair. `production-q01.json` and `production-q08.json` are now nonempty, checked JSON outputs of the new cached smoke, not recovery of the missing original runs. All are local ignored evidence, not public artifacts. The old comparison runs and their metrics apply only to their recorded implementation revision, not automatically to later hardening changes. Project-level acceptance remains NOT READY until the independent audit closes remaining semantic grounding/retrieval and other documented findings.
