# Video Briefing Implementation Plan

> **Historical plan (2026-10-05).** This document records an earlier implementation proposal. Its task list, dependencies, setup directions, and acceptance conditions are superseded by the current source-first code and README. It is retained as project history; use the current README and `docs/design.md` for present-day behavior.

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Рабочий link→русский brief→grounded cached Q&A и воспроизводимое сравнение на DvSwvJVens8 в local OpenResearch, затем reusable skill в source of truth/default.

**Architecture:** Общая evidence-first оболочка с adapter variants A Baoyu, B summarize extraction, optional C ASR/captions. Одни и те же model/prompt/retrieval policy отделяют extractor evaluation от LLM variability. Локальные raw artifacts сохраняются неизменными; OpenResearch запускает только committed snapshots и фиксированный command/env.

**Tech Stack:** Python + uv/pytest (baseline recommendation), existing Baoyu TS via pinned local Bun, project-local summarize standalone, Ollama REST gemma4:31b-cloud, orx 0.2.13/local backend, local Git.

---

## Порядок и ownership
1. Research discovery/protocol и coder harness идут параллельно, максимум два агента, без nested agents. Research пишет только docs/research и не коммитит/не меняет ветки. Coder пишет src/tests/pyproject/lock/prompts/config/scripts/README и explicit-path commits.
2. Research formal OpenResearch comparison стартует только после обеих initial tasks. Создаёт собственные experiment worktrees; main не переключает на frozen branch.
3. Independent spec review → independent code-quality review; report fixes then coder repairs and packages actual skill. Final orchestrator audit independently reads artifacts/runs commands.

## Task 1: Real source preflight and acceptance set (research)
Create docs/research/preflight.md and evaluation.json. Verify title/duration/languages/access/source by primary endpoint/tools; no content inventions. Test requested id validation exactly. Read existing canonical report. Record upstream pins/tool prerequisites and decide at most one optional third variant before generated answers. Prepare source-linked topic anchors/questions from actual source; distinguish common-mode captions from independent truth. No branch edits/commits during parallel coder phase.

## Task 2: Manifest and reproducible dev environment (coder)
Create pyproject.toml, uv.lock, src/video_briefing/__init__.py, tests/test_cli.py. Pin supported Python and dependencies to installed/discovered versions; define actual CLI scripts, test/static commands. Failing test: command --help yields expected subcommands; implement minimal shell-free CLI, run focused test and explicit owned-path commit. No npm Node24 assumption on Node22. Setup all project tools under .tools with provenance/version.

## Task 3: Source schema and guardrails (coder, TDD)
Create models.py/validation.py and tests/test_validation.py. Required segments id/text/start/duration; numeric finite nonnegative time, stable id. Example unit fixture (SYNTHETIC TEST ONLY): {'id':'s0','text':'fixture','start_seconds':0.0,'duration_seconds':1.0}. Reject empty/description-only, NaN/negative times/duplicate ids/unavailable source. Fail tests first, implement, pytest focused, commit explicit paths.

## Task 4: Atomic artifact store and identity (coder, TDD)
Create store.py/tests/test_store.py. Cache keyed platform/id/source language/variant; atomic write with immutable raw hash and metadata; summary language separate. Test two titles for same id don't create false independent evidence, different variants don't overwrite, stale/incomplete artifacts rejected. Hash via hashlib; do not fabricate expected live hashes. Record timestamps from real source, not model output.

## Task 5: Adapter A — existing Baoyu (coder, TDD + real preflight)
Create adapters/baoyu.py and tests/test_baoyu.py. Wrap existing main.ts with a project-local pinned Bun runtime and explicit arguments; original language selection, raw segments/meta preserved. Parse outputs rather than trust exit0. No --speakers inference for default author attribution. Test via explicit fixture subprocess outputs then execute real target extraction once and inspect evidence. If blocked, record exact error and bounded alternative, not summary description. Install downloader project-locally if needed without cookies.

## Task 6: Adapter B — summarize extraction-only (coder)
Create adapters/summarize.py/tests/test_summarize.py. Get pinned official standalone macOS build/checksum or another justified project-local supported runtime. Verify --version and --help. JSON stdout is separate from stderr. Require actual timed transcript source; reject description fallback. Same target/source language/common downstream model. Test malformed stdout, description-only, no timestamps, normal timed fixture, backend missing. Runtime attempt logs preserved even if blocked.

## Task 7: Optional third variant (coder after preflight)
Only if justified: adapters/asr.py using yt-dlp→ffmpeg→whisper.cpp with a reasonable already available/small approved model, OR captions_api.py using youtube-transcript-api. Document model/resources/download choice; larger discretionary download needs pending decision. Test original-offset preservation, no external cloud-ASR fallback, error distinction no-captions/IP-block/auth. At most three tested variants.

## Task 8: Shared LLM driver and brief contract (coder, TDD + smoke)
Create llm.py/briefing.py/prompts/brief.md/tests/test_briefing.py. Existing Ollama plain REST interface; call timeout/limits explicit, fixed gemma4 model/temp. Clearly cloud-backed. Generate structured brief with valid evidence ids, distinguish interpretations, then render Russian. No nested agent. Reject unsupported citations/speaker claims; malformed provider response != invented result. Bound full-source chunks, preserve coverage and source indices. Run actual provider smoke and target briefing; record effective settings/hash/usage if provided.

## Task 9: Grounded cached Q&A (coder, TDD + real smoke)
Create retrieval.py/prompts/qa.md/tests/test_retrieval.py/tests/test_qa.py. Search full timed source with aliases/neighbour windows; summary is navigation only. User question injection is untrusted. Deterministic validation resolves cited ids to actual times. Test unknown citations, no-evidence abstention, host/guest uncertainty, content instruction injection, relevant passage beyond first chunk. Cached follow-up test replaces extraction/network-adapter call with a fail assertion; source hash stable. LLM inference request is allowed; no re-fetch video.

## Task 10: Benchmark harness (coder, TDD)
Create benchmark.py/scripts/run_benchmark.* and tests/test_benchmark.py. Read only committed experiment config. Emit METRICS_JSON and compact logs containing variant/model/prompt/source hashes/counts and measured perf_counter timings. Respect stable external evidence root in same env across OpenResearch snapshot dirs; don't infer local main .venv exists in run snapshot. Write artifacts to durable per-run dir and print exact absolute paths. Have bench cold→brief→fixed questions→warm reuse workflow; no command/env per-node differences. Synthetic unit mode can't be confused with live benchmark; exact target mandatory live case.

## Task 11: Local OpenResearch real experiments (research)
Read orx skill orx-create/orx-compute/orx-git/orx-evidence and compute/local. orx up --no-agent --no-browser, bind loopback; discovery via supported API schema not sqlite edits. Import existing repo without remote. Set actual fixed run command once. Commit shared harness and evaluation spec before run. Baseline root plus <=3 siblings changing committed variant config only. Each node immutable after answered; use worktrees. orx exp run --backend local, wait appropriately, read full relevant logs/metrics. Two failed answerless attempts cap then explicit blocker. Do not replace formal runs with direct commands and claim tracked experiment.

## Task 12: Comparison report (research)
Create reports/comparison.md, reports/comparison.json and docs/research/openresearch-manifest.json. Include ids/branches/commits/config/prompt/provider hashes, measured n/time, support coverage and source-linked brief/Q&A examples, setup burden, blocked paths, limitations. Review generated claims against actual raw source and independently inspect several offsets if media available. Winner only if real evidence; honest ties permitted. No fake cost zero, fake latency, universal generalization, or title-based summary.

## Task 13: Spec compliance then quality review (independent runs)
Spec reviewer checks exact user task and all gates (local Git, actual target video, up to3 variants, real orx runs, source-grounded Q&A/cache, pending decisions). Return PASS or concrete gaps before quality review starts. Quality reviewer independently reads code/diff/tests, actual backend subprocess safety, LLM network behavior, snapshots, cache validation, raw data ignore and citations; runs suite/CLI smoke. Critical/important issues require repair + rereview; self-review isn't independent approval.

## Task 14: Harden winner and publish LOCAL skill (coder)
Fix validated issues on main/new production branch, not frozen experiment nodes. Update README with actual proven setup/commands, model/privacy caveats, diagnostics/fallback rules. Create skills/video-briefing/SKILL.md with references/scripts from proven workflow. Frontmatter lowercase name, one-line trigger, no secrets; full copies to canonical custom/video-briefing and default custom/video-briefing. Existing destination divergence => stop, never overwrite. Add exact skill registry entry via targeted existing-manifest edit, provenance current git commit and full-tree checksums; no fleet/other profile edits. Verify tree hashes, no symlinks and loader discovery. Local commit tracked deliverables/metrics/bounded report; no raw transcripts/audio/credentials.

## Task 15: Final orchestrator gate
Independently inspect Git root/status/log/remotes, run actual declared tests and CLI cached question, inspect orx project/runs/logs/manifests, final brief on DvSwvJVens8, skill paths/hashes. Deliver concise Russian result, actual comparison, usage commands, repo path, OpenResearch dashboard link/ids and report/media attachments. If blocked/incomplete, identify exact missing acceptance; do not say done. Remind codegraph init -i for new repo, or report real index check if performed. No remote added.
