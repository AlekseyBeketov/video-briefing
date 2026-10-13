# Архитектура и границы решения

## Результат для пользователя
Ссылка без дополнительных вопросов → краткая суть, темы, полезные идеи, акценты и ограничения автора с таймкодами. Последующие вопросы читают полный сохранённый транскрипт и ближайший контекст. Целевой ответ компактный, по-русски, без пересказа каждой минуты.

## Источники и adapters
YouTube: основной extractor — `youtube-transcript-api` через `captions_api`; `baoyu` доступен только как явно выбранный альтернативный адаптер. Автоматического fallback и извлечения доказательств из описания видео нет.

Локальный MP4: явный CPU-only ASR через пользовательские `ffmpeg`/`ffprobe`, CLI `transcribe.cpp` и модель GigaAM GGUF. Аудио не отправляется в облачный ASR; бинарник и модель устанавливаются отдельно и не входят в пакет. Границы чанков не являются пословным выравниванием.

CLI поддерживает YouTube URL/video ID и локальный MP4 с явным opt-in к ASR. Необязательный MCP предоставляет ingestion и ограниченные инструменты работы с evidence; он не вызывает LLM. Другие платформы и Gemini/vision не являются реализованными возможностями.

## Структура
Python CLI/package и общая типизированная схема артефактов; backend adapters используют безопасные subprocess/HTTP без `shell=True`. Закреплённые зависимости находятся в `pyproject.toml`/`uv.lock`. Пользователь устанавливает ASR runtime отдельно; постоянные evidence хранятся в системном каталоге данных. Конфигурации экспериментов, отчёты, prompts, тесты и skill отслеживаются в Git, если не содержат приватных данных. Если существующий проект другого стека существенно проще — ADR до изменения контракта, а не лишняя перепись.

В `src/video_briefing/` находятся CLI, модели, хранилище, валидация, retrieval, briefing, benchmark, локальный ASR и MCP. YouTube adapters: `baoyu` и `captions_api`. Адаптера и установщика `summarize` больше нет.

## Единый evidence bundle
Video identity: validated platform + exact id DvSwvJVens8, original URL, identified source language, extraction variant/version. Cache key не зависит от title и summary language; persistent cache требует полного serialized raw source и запрещает overwrite при изменении hash.
Segments: id, text, start_seconds, duration_seconds, optional source_speaker with certainty; raw original saved unchanged. Metadata: title/channel/duration/fetched_at/source_type/manual-or-auto/language/extractor_version/content_hash/coverage/warnings. Transcript needs nonempty text AND valid numeric timestamps. Description-only source must fail loudly.
Normalized timing нельзя выдавать за forced alignment; Baoyu sentence timestamps пропорциональные — цитирование по raw snippets. Несколько участников без evidence attribution остаются unnamed.
Generated briefing includes claims/evidence segment ids. Follow-up answers contain citation references resolved to actual source intervals, and a distinction between author statement and inference.

## Pipeline
validate URL → choose adapter → timed source → verify/provenance → immutable file bundle → chunk full source when needed → common LLM brief → validate cited segment ids → render concise Russian output.
Q&A: open artifact → search saved transcript using terms/aliases + context windows → common LLM grounded claims → validate cited IDs → render only cited claim text. Search miss is not proof of absence from full video; unknown answer stays qualified. No automatic re-extraction on follow-up.

## Model path
Available local Ollama endpoint http://127.0.0.1:11434 has gemma4:31b-cloud. This model is CLOUD-backed, not offline. Use one fixed explicitly recorded model/settings/prompt hash across extractor comparisons if real smoke succeeds; never pull another model or add API keys automatically. Inference is plain API, not nested autonomous agents. If unavailable, document provider blocker; a manual agent evidence-reading result may be separately labelled but cannot replace scripted benchmark/model logs.
Coding profile: configured gpt-6-luna + reasoning_effort max through openai-codex. User wording luna-6-max is recorded literally; runtime model/settings mapping follows inspected profile and cached model metadata, not silent invented provider names.

## OpenResearch
orx 0.2.13 is installed; telemetry already disabled. Local dashboard is initially stopped. Start loopback only with --no-agent --no-browser to avoid exceeding agent cap. Import local Git through supported local API/dashboard (discover actual schema); never edit internal SQLite directly. No managed compute/login/publication.
Set one fixed run command after implementation exists, e.g. uv run --frozen python -m video_briefing.benchmark --config config/experiment.json (example contract, coder establishes actual package entrypoint). Same environment across all nodes. Committed config selects variant/cache/run mode; no command/env per-node changes.
Baseline: shared harness controls. Round one: at most three sibling extractor variants. Follow-up winner child only if an actual hypothesis improves grounding/retrieval/cache; no tree decoration. Read final logs and metrics, not statuses alone. Answered experiment branches remain frozen forever. Review/hardening uses main/new branch outside frozen nodes.

## Privacy and safety
No global updates; public target video only; no cookies, proxies, auth file reads or credential display. Bind all services 127.0.0.1. Abort on unavailable network/access instead of bypassing. Normal dependency downloads are allowed in the project; substantial model downloads/paid services or user policy changes go to pending-decisions. Keep exact sources/pins/checksums/license provenance.

## Completion
Actual CLI link→brief and cached follow-up answer on supplied video, inspected evidence citations, comparison table with measured not invented timing, OpenResearch ids/commits/logs, reproducible setup, passing tests, canonical+default full-copy skill, local Git with no remote. If external target content is genuinely inaccessible, task remains blocked with exact reason, not marked end-to-end done.
