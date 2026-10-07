# Video Briefing

Локальный agent-friendly workflow: ссылка на видео → краткий русский разбор → вопросы по сохранённому первоисточнику.

**Статус acceptance:** реализован рабочий evidence-first workflow, но сравнение не дало production-победителя: в сохранённом OpenResearch отчёте 2 runs завершились, 4 завершились ошибкой; успешного original-RU head-to-head нет. `captions_api` — проверенный operational fallback для этого URL, не объявляется научным победителем. См. `reports/comparison.md` и `reports/spec-review.md`.

Целевой тест: https://www.youtube.com/watch?v=DvSwvJVens8

- Три ограниченных варианта: Baoyu, summarize extraction-only, `youtube-transcript-api` captions-only. Последний не ASR; сравнение зафиксировано в `reports/comparison.md` с честными failed/partial результатами.
- OpenResearch runs выполнялись локально. Никаких новых экспериментов не запускайте без проверки текущего run cap и `docs/research/openresearch-manifest.json`.
- Один downstream LLM/prompt/settings для сравнения extractor-вариантов.
- Исходные расшифровки сохраняются локально вне Git. Результаты нельзя выдавать за просмотр изображения, если анализировалась только речь.

Архитектура: [docs/design.md](docs/design.md). План: [docs/plans/2026-10-05-video-briefing.md](docs/plans/2026-10-05-video-briefing.md). Методика: [docs/benchmark-protocol.md](docs/benchmark-protocol.md).

## Быстрый старт

```sh
uv sync --frozen --extra dev
./scripts/setup-tools.sh
uv run --frozen video-briefing doctor
```

`setup-tools.sh` устанавливает Bun 1.4.2 локально в `.tools/` и официальный `summarize` 0.25.1 macOS arm64 release с проверкой SHA-256. Python-зависимость captions adapter зафиксирована в `uv.lock`; A/B не требуют ключей. Скрипт не меняет глобальный Node/Bun и не читает cookies.

## CLI

```sh
# Извлечь и сохранить оригинальный русский timed transcript
uv run --frozen video-briefing extract 'https://www.youtube.com/watch?v=DvSwvJVens8' \
  --variant captions_api --languages ru

# Краткий русский brief; на cache miss сначала извлечёт источник
uv run --frozen video-briefing brief 'https://www.youtube.com/watch?v=DvSwvJVens8' \
  --variant captions_api --languages ru

# Та же операция со структурированными JSON citations/model metadata
uv run --frozen video-briefing brief 'https://www.youtube.com/watch?v=DvSwvJVens8' \
  --variant captions_api --languages ru --json

# Вопрос читает сохранённый bundle; при cache miss завершается ошибкой, не скачивает видео
uv run --frozen video-briefing ask 'https://www.youtube.com/watch?v=DvSwvJVens8' \
  'Как ведущий объясняет компромисс объединённой памяти?' --variant captions_api --languages ru

# Повторяемый run: target/questions и extractor выбираются только из committed config
uv run --frozen video-briefing benchmark --config config/experiment.json
```

Evidence хранится под `artifacts/private/`, не коммитится. Raw transcript сохраняется целиком локально; cache write-once: новый текст с тем же `(platform, video_id, language, variant)` выдаёт conflict, исходник не перезаписывается. `ask` читает только сохранённый bundle, cache miss завершается ошибкой без повторной extraction. Ответ отображается только из claims с существующими segment IDs/timestamps; цитата подтверждает место в источнике, но не является автоматическим доказательством смысловой поддержки.

Briefing и Q&A используют настроенный Ollama `gemma4:31b-cloud`: модель cloud-backed, не offline. Ollama endpoint получает вопросы и фрагменты расшифровки; учитывайте это при работе с приватными видео. Успешный Ollama endpoint не означает, что обработка локальная. Токены учитываются, если endpoint их вернул; стоимость не измеряется.

Поддерживаются YouTube URL/ID и timed caption/transcript adapters `baoyu`, `summarize`, `captions_api`. Description-only output запрещён; видео, которые требуют входа, cookies, прокси или платного ASR, не обходятся. Визуальные кадры не анализируются. `summarize` с неизвестным/несовпавшим языком отклоняется, а не маскируется под RU.

## Диагностика и приватность

- `video-briefing doctor` выдаёт JSON о Python, Ollama endpoint и доступности project-local Bun/summarize и Baoyu source. Если Ollama недоступен, сначала проверьте loopback endpoint/model в `config/experiment.json`; это не проверка YouTube-доступа.
- `captions_api` без доступных captions завершится ошибкой: попробуйте другой доступный caption adapter. Не подменяйте исходник описанием.
- HTTP 429/5xx — временное ограничение/ошибка upstream: остановитесь и повторите позже; не вращайте клиентов и не добавляйте прокси.
- IP/network restriction отличается от отсутствия captions. В текущем режиме cookies/auth не используются; не добавляйте их для обхода ограничения.
- Raw transcript, media, per-run progress/diagnostics и bundles остаются в ignored `data/`/`artifacts/private/`; не прикладывайте их к публичным issue. Отправляемые отчёты должны содержать только bounded цитаты и hashes.
- Переменные `VIDEO_BRIEFING_BUN`, `VIDEO_BRIEFING_SUMMARIZE` и `VIDEO_BRIEFING_BAOYU` могут указывать на уже имеющиеся local tools; секреты и cookies в них не задаются.

## Проверенные команды

```sh
uv run --frozen pytest
uv run --frozen video-briefing --help
uv run --frozen video-briefing doctor
```

Research evaluation и 8 фиксированных вопросов находятся в `docs/research/evaluation.json`. В LLM передаётся только `question`, не expected points/ranges. Полный протокол и известные ограничения: [docs/benchmark-protocol.md](docs/benchmark-protocol.md), [docs/research/preflight.md](docs/research/preflight.md). Для новой структуры проекта напоминание: `codegraph init -i`.
