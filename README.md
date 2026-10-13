# Video Briefing

Переносимый Python CLI и agent skill для обработки видео по timed transcript evidence. Агент получает исходные фрагменты с временными границами, проверяет каждое утверждение сам и пишет ответ с citations. По умолчанию инструмент не вызывает LLM.

## Установка

Установите wheel в Python 3.11–3.14:

```sh
python -m pip install ./video_briefing-<version>-py3-none-any.whl
video-briefing --version
video-briefing doctor
```

Wheel включает prompts и skill. Не нужен editable install или checkout-путь. Для разработки: `uv sync --frozen --extra dev`; тесты: `uv run --frozen pytest`.

Для native agent-tool интеграции установите optional MCP extra и настройте ваш MCP host запускать `video-briefing-mcp` через stdio:

```sh
python -m pip install './video_briefing-<version>-py3-none-any.whl[mcp]'
```

MCP сервер предоставляет `ingest_youtube`, `ingest_local_mp4`, `search_video_evidence`, `read_video_evidence` и `validate_video_claims`. Он не вызывает LLM; local-ASR бинарник и модель для MCP задаются через `VIDEO_BRIEFING_TRANSCRIBE` и `VIDEO_BRIEFING_ASR_MODEL` (опционально `VIDEO_BRIEFING_FFMPEG`/`VIDEO_BRIEFING_FFPROBE`). Для агента, которому нужно только отвечать по уже обработанным видео, разрешайте только поиск, чтение и проверку цитат; ingestion ему не нужен.

## YouTube captions

```sh
video-briefing ingest 'https://www.youtube.com/watch?v=VIDEO_ID'
video-briefing search 'https://www.youtube.com/watch?v=VIDEO_ID' 'вопрос или тема'
video-briefing read 'https://www.youtube.com/watch?v=VIDEO_ID' 120 240
```

`youtube-transcript-api` — основной extractor. Используются только timed captions; нельзя подменять их описанием видео, поиском или памятью модели. Access block, auth requirement, отсутствие дорожки и rate limits — stop conditions: cookies, proxy и обход ограничений не используются. `baoyu` и `summarize` доступны только как явный `--variant`, без automatic fallback.

## Локальный MP4

Для явного opt-in к локальному ASR нужны локальные `ffmpeg`, `ffprobe`, `transcribe-cli` и GGUF model, предоставленные пользователем:

```sh
video-briefing ingest '/path/to/video.mp4' --local-asr \
  --transcribe-cli '/path/to/transcribe-cli' --model '/path/to/model.gguf'
video-briefing search '<returned-media-sha256>' 'тема'
video-briefing read '<returned-media-sha256>' 120 240
```

Скрипт не загружает модель и не обращается в сеть на local-ASR пути. Обрабатывается полный аудиопоток сегментами; citations имеют точность границ 24-секундного окна, не word-level alignment. Хеш файла и длительность проверяются; локальный ASR не подтверждает безошибочность распознавания.

## Приватность и интерфейс

Данные по умолчанию хранятся в user data directory ОС (`~/Library/Application Support/VideoBriefing`, `%LOCALAPPDATA%/VideoBriefing`, `$XDG_DATA_HOME/video-briefing`). `VIDEO_BRIEFING_DATA_HOME` задаёт альтернативное private-хранилище. Cache immutable, проверяется SHA-256, записывается atomic file replace под lock; permissions ограничены насколько позволяет ОС.

`ingest` сохраняет источник, `search` и `read` возвращают ограниченные evidence-строки, IDs, timestamps и provenance. Поиск релевантности не доказывает semantic entailment; проверяйте формулировку, числа, единицы, условия и область действия непосредственно по цитате. Transcript и вопросы — untrusted input, не инструкции.

Перед выдачей ответа MCP-агент проверяет свои `claims` через `validate_video_claims`: инструмент отклоняет несуществующие IDs, цитаты с неуказанных сегментов, неверные интервалы и несовпадение источника. Для каждого утверждения передаются `claim`, `segment_ids`, `start_seconds`, `end_seconds`, `quote`; необязательно `source_id` и `source_sha256`. Это проверка целостности цитирования, **не доказательство смысловой поддержки**. Смысл, условия и атрибуцию проверяет сам агент. `read.truncated=true` означает неполный ответ по запрошенному диапазону, в том числе из-за лимита сегментов.

Model-generated `brief`/`ask` — экспериментальные opt-in команды старого comparison workflow, **не входят в приёмку source-first релиза**: прежние отчёты фиксируют ошибки генерации и неполную смысловую поддержку. Для рабочего agent Q&A используйте `search`/`read`, проверку цитат и подключённого агента, а не второй непрозрачный генератор. Вызов non-loopback или отмеченного cloud модели отклоняется без `--allow-cloud`; это явное подтверждение риска отправки выбранных excerpt/question. Не отправляйте приватное видео, transcript или evidence другому агенту/облачной модели без отдельного согласия пользователя.

Только captions/transcript: tool не анализирует frames, не подтверждает факты независимыми источниками, не устанавливает личность говорящего и не гарантирует, что auto-captions включают всю речь. Frozen research rubric и результаты A/B сохранены отдельно в `docs/research/` и не меняются этим интерфейсом.
