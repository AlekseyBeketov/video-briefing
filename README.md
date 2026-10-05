# Video Briefing

Локальный agent-friendly workflow: ссылка на видео → краткий русский разбор → вопросы по сохранённому первоисточнику.

**Статус: проектирование и реализация. Готовность пока не заявляется.**

Целевой тест: https://www.youtube.com/watch?v=DvSwvJVens8

- До трёх вариантов: Baoyu captions; summarize extraction; при необходимости local ASR или альтернативный captions backend.
- Сравнение через OpenResearch (`orx`), локально, без публикации репозитория.
- Один downstream LLM/prompt/settings для сравнения extractor-вариантов.
- Исходные расшифровки сохраняются локально вне Git. Результаты нельзя выдавать за просмотр изображения, если анализировалась только речь.

Архитектура: [docs/design.md](docs/design.md). План: [docs/plans/2026-10-05-video-briefing.md](docs/plans/2026-10-05-video-briefing.md). Методика: [docs/benchmark-protocol.md](docs/benchmark-protocol.md).

Команды установки/CLI будут добавлены после реального выполнения и проверки; ниже нет выдуманных successful outputs.
