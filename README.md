# Video Briefing

Локальный agent-friendly workflow: ссылка на видео → краткий русский разбор → вопросы по сохранённому первоисточнику.

**Статус реализации:** CLI, общая evidence-модель, кэш и два обязательных extractor adapter реализованы. На целевом ролике Baoyu получил HTTP 429, summarize вернул 560 timed segments на английском без достоверного language tag; отдельный captions-only adapter `youtube-transcript-api` 1.2.4 извлекает оригинальные русские captions. Это не formal OpenResearch comparison.

Целевой тест: https://www.youtube.com/watch?v=DvSwvJVens8

- Три ограниченных варианта: Baoyu, summarize extraction-only, `youtube-transcript-api` captions-only. Последний не ASR и выбран как рабочий fallback без скачивания модели.
- Сравнение через OpenResearch (`orx`), локально, без публикации репозитория.
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

# Вопрос читает сохранённый bundle; при cache miss завершается ошибкой, не скачивает видео
uv run --frozen video-briefing ask 'https://www.youtube.com/watch?v=DvSwvJVens8' \
  'Как автор объясняет компромисс объединённой памяти?' --variant captions_api

# Повторяемый run: target/questions и extractor выбираются только из committed config
uv run --frozen video-briefing benchmark --config config/experiment.json
```

Evidence хранится под `artifacts/private/`, не коммитится. Q&A ищет полный сохранённый transcript и цитирует только реальные segment IDs/timestamps. Summary/Q&A используют настроенный Ollama `gemma4:31b-cloud`: модель фактически cloud-backed, не offline; это один и тот же downstream для вариантов.

## Проверенные команды

```sh
uv run --frozen pytest
uv run --frozen video-briefing --help
uv run --frozen video-briefing doctor
```

Research evaluation и 8 фиксированных вопросов находятся в `docs/research/evaluation.json`. В LLM передаётся только `question`, не expected points/ranges. Полный протокол и известные ограничения: [docs/benchmark-protocol.md](docs/benchmark-protocol.md), [docs/research/preflight.md](docs/research/preflight.md). Для новой структуры проекта напоминание: `codegraph init -i`.
