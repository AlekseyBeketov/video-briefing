# Архитектура и границы решения

## Текущий пользовательский сценарий
Пользователь получает доступный YouTube-транскрипт с таймкодами или явно включает локальную обработку MP4, затем ищет и читает сохранённые исходные сегменты. Сам CLI/MCP не составляет ответ по умолчанию: вызывающий агент синтезирует ответ из возвращённых фрагментов и указывает их источники. Необязательные CLI-команды `brief` и `ask` создают модельный текст отдельно и не входят в обычный evidence-first сценарий.

## Источники и adapters
YouTube: основной extractor — `youtube-transcript-api` через `captions_api`; `baoyu` доступен только как явно выбранный альтернативный адаптер. Автоматического fallback и извлечения доказательств из описания видео нет.

Локальный MP4: явный opt-in к офлайн ASR. Optional `asr` extra ставит официальный Python binding `transcribe-cpp` и PyAV; `setup-asr` загружает закреплённую и проверенную по SHA-256 модель в private user data directory. Для русского используется GigaAM v3 e2e-RNN-T Q8_0 (274 MB, MIT), для английского — NVIDIA Parakeet TDT-CTC 110M Q8_0 (135 MB, CC-BY-4.0 с атрибуцией). Установка предлагает язык по локали ОС только как предположение и требует подтверждения; язык аудио каждого источника должен быть известен, а выбор не является auto-detection. Обработка MP4 и transcript локальны; PyAV декодирует аудио, FFmpeg и FFprobe не нужны в managed path. Сегментное время ограничено 24-секундными окнами, это не пословное выравнивание. Старый пользовательский `transcribe-cli` + GGUF путь сохранён как legacy compatibility mode.

CLI поддерживает YouTube URL/video ID и локальный MP4 с явным opt-in к ASR. Необязательный MCP предоставляет ingestion и ограниченные инструменты работы с evidence; он не вызывает LLM. Другие платформы и Gemini/vision не являются реализованными возможностями.

## Структура
Python CLI/package и общая типизированная схема артефактов; backend adapters используют безопасные subprocess/HTTP без `shell=True`. Закреплённые зависимости находятся в `pyproject.toml`/`uv.lock`; ASR runtime опционален через отдельный `asr` extra, а pinned GGUF модели пользователь устанавливает отдельной командой в системный каталог данных. Постоянные evidence хранятся там же вне checkout. Конфигурации экспериментов, отчёты, prompts, тесты и skill отслеживаются в Git, если не содержат приватных данных. Исторические implementation plans не являются пользовательской документацией и удалены из актуального дерева; история изменений сохраняется в Git. Если существующий проект другого стека существенно проще — ADR до изменения контракта, а не лишняя перепись.

В `src/video_briefing/` находятся CLI, модели, хранилище, валидация, retrieval, briefing, benchmark, локальный ASR и MCP. YouTube adapters: `baoyu` и `captions_api`. Адаптера и установщика `summarize` больше нет.

## Единый evidence bundle
Video identity: validated platform + exact id DvSwvJVens8, original URL, identified source language, extraction variant/version. Cache key не зависит от title и summary language; persistent cache требует полного serialized raw source и запрещает overwrite при изменении hash.
Segments: id, text, start_seconds, duration_seconds, optional source_speaker with certainty; raw original saved unchanged. Metadata: title/channel/duration/fetched_at/source_type/manual-or-auto/language/extractor_version/content_hash/coverage/warnings. Transcript needs nonempty text AND valid numeric timestamps. Description-only source must fail loudly.
Normalized timing нельзя выдавать за forced alignment; Baoyu sentence timestamps пропорциональные — цитирование по raw snippets. Несколько участников без evidence attribution остаются unnamed.
Generated briefing includes claims/evidence segment ids. Follow-up answers contain citation references resolved to actual source intervals, and a distinction between author statement and inference.

## Pipeline
Загрузка: validate URL → получить доступные timed captions через выбранный extractor или явно включить локальный ASR для MP4 → проверить identity, время и provenance → сохранить immutable evidence bundle локально. В режиме по умолчанию запросы `search`/`read` и MCP-инструменты возвращают ограниченные исходные сегменты, временные границы и provenance; вызывающий агент отвечает сам. MCP `validate_video_claims` проверяет совпадение буквальных цитат, segment IDs, identity и времени.

Follow-up: открыть сохранённый artifact → найти исходные сегменты с соседним контекстом → показать их вызывающему агенту. Пропуск в выдаче поиска не доказывает отсутствие темы во всём видео. Последующий вопрос не запускает автоматическую повторную загрузку источника. Опциональные `brief`/`ask` используют настроенную модель только как отдельный workflow с явным согласием для cloud-backed или non-loopback endpoint.

## Optional model generation
Model inference is not part of the default source/evidence workflow. The optional `brief` and `ask` commands accept the Ollama-compatible endpoint and model settings from the selected experiment config. A non-loopback endpoint or one marked cloud-backed is rejected unless the user explicitly passes `--allow-cloud`; source excerpts and questions may then leave the machine. Never download another model, add API keys, or switch providers automatically. The caller agent can also synthesize from MCP evidence, but that sends tool output to the agent's provider under that provider's own data policy.

## Research and benchmark tooling
OpenResearch and the fixed-target benchmark configuration support a bounded comparison experiment; they are not needed for ordinary CLI/MCP use and do not change the default source-first behavior. Historical run details and dated outcomes remain in `docs/research/` and `reports/`.

The earlier research protocol used a loopback-only dashboard and did not use managed compute, account login, or publication. Those run-specific settings and tool versions are historical; for any new comparison, inspect the currently installed OpenResearch version and its supported interface first. Never edit its internal SQLite database directly.

The current CLI exposes `video-briefing benchmark --config config/experiment.json`. This is an experiment command, not part of normal installation or evidence lookup. The previous formal comparison used one committed config and command across its nodes; retain its exact settings and caveats with the dated research records instead of copying them as a general user recipe.
Baseline: shared harness controls. Round one: at most three sibling extractor variants. Follow-up winner child only if an actual hypothesis improves grounding/retrieval/cache; no tree decoration. Read final logs and metrics, not statuses alone. Answered experiment branches remain frozen forever. Review/hardening uses main/new branch outside frozen nodes.

## Privacy and safety
No global updates; public target video only; no cookies, proxies, auth file reads or credential display. Bind all services 127.0.0.1. Abort on unavailable network/access instead of bypassing. Normal dependency downloads are allowed in the project; substantial model downloads/paid services or user policy changes go to pending-decisions. Keep exact sources/pins/checksums/license provenance.

## Acceptance of the current source-first workflow
Confirm the locked setup, `video-briefing doctor`, successful ingestion for an authorized and reachable source, bounded `search`/`read` evidence with source identity and timestamps, and valid citation-boundary checks. Run the automated tests. A live model response or comparative benchmark is optional and must be reported separately; a successful source lookup does not prove that a free-form answer is semantically supported. If captions are blocked or unavailable, preserve the exact source error and do not substitute a title or description.
