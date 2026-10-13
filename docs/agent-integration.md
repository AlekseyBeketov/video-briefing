# Подключение к агентам

Video Briefing не требует отдельного framework-specific плагина. Переносимый контракт — установленный Python CLI, `SKILL.md` и optional MCP stdio. Не требуется работать из исходного репозитория или давать агенту его код.

## Установка

Из checkout соберите артефакт командой `uv build`, затем установите wheel в отдельный Python 3.11–3.14 env:

```sh
python -m pip install './video_briefing-0.2.0-py3-none-any.whl[mcp]'
video-briefing --version
video-briefing doctor
video-briefing skill
```

Команда `skill` выводит переносимую инструкцию. Сохраните её как `SKILL.md` в обычном каталоге skills выбранного агента. Репозиторий также содержит полный пакет `skills/video-briefing/`. MCP executable в конфигурации должен указывать на **установленный** `video-briefing-mcp`, не на checkout или editable environment.

CLI `ingest` предварительно обрабатывает видео; агенту, который лишь задаёт вопросы, достаточно доступа к сохранённому кэшу. Для общих данных задайте `VIDEO_BRIEFING_DATA_HOME` одинаково у CLI и MCP. Не помещайте этот private-каталог внутрь Git.

## Hermes

Пример блока для выбранного пользователем профиля; этот документ сам ничего не устанавливает и не меняет профиль:

```yaml
mcp_servers:
  video_briefing:
    command: /ABS/PATH/TO/VENV/bin/video-briefing-mcp
    args: []
    env:
      VIDEO_BRIEFING_DATA_HOME: /ABS/PATH/TO/PRIVATE/DATA
    tools:
      include:
        - search_video_evidence
        - read_video_evidence
        - validate_video_claims
      prompts: false
      resources: false
    sampling:
      enabled: false
```

Загрузите skill и проверьте реальные callable schemas после старта агента. Для независимого consumer-теста нужны только эти три инструмента, отключённые web/browser/terminal/files/прочие MCP и пустой cwd вне checkout. Приёмка в этом репозитории выполнена именно таким fail-closed harness на Hermes `gpt-6-luna / high`.

## Codex

Эквивалентный stdio-конфиг:

```toml
[mcp_servers.video_briefing]
command = "/ABS/PATH/TO/VENV/bin/video-briefing-mcp"
args = []
enabled_tools = ["search_video_evidence", "read_video_evidence", "validate_video_claims"]

[mcp_servers.video_briefing.env]
VIDEO_BRIEFING_DATA_HOME = "/ABS/PATH/TO/PRIVATE/DATA"
```

Имя модели выбирается отдельно и не является зависимостью инструмента. Exact `gpt-6-luna` был отклонён установленным Codex CLI при ChatGPT-авторизации, поэтому **Codex consumer E2E для этой модели не заявляется**. MCP stdio/package contract проверен независимо от имени модели; не подменяйте неподдерживаемую модель молча.

Для других агентов используйте те же executable, environment и три read-only tools; если MCP не поддерживается, подключайте CLI через skill и разрешённый агентом shell bridge. Это уже другой профиль полномочий, не эквивалент изолированной MCP-приёмке.

## Ingestion и приватность

Если агенту нужно самостоятельно добавлять источники, отдельно разрешите `ingest_youtube` и/или `ingest_local_mp4`. Локальный ASR требует заранее настроенных доверенных `VIDEO_BRIEFING_TRANSCRIBE` и `VIDEO_BRIEFING_ASR_MODEL`; опционально задаются `VIDEO_BRIEFING_FFMPEG`/`VIDEO_BRIEFING_FFPROBE`. Эти бинарники, модель и медиа не распространяются вместе с пакетом.

Разрешение на локальный ASR не разрешает отправку расшифровки облачному агенту. Получите отдельное согласие на источник, провайдера и цель. Сам MCP server не вызывает LLM; передача его tool-output облачному агенту уже передаёт текст провайдеру.

## Ответы и доказательства

Для ответственных фактов используйте source-first формат: фактические `claims` — прямые цитаты (`claim == quote`), рядом IDs и временные границы. Пересказ помечайте редакторским обзором, а не автоматически проверенным фактом. Перед final вызывайте `validate_video_claims`; invalid исправляйте через повторное чтение или удаление неподтверждённого утверждения. Проверка цитат не доказывает смысловую поддержку свободного пересказа и не подтверждает действующее право или внешнюю истинность.

При `truncated=true` прочитайте продолжение. Визуальные вопросы, внешний курс валют и незакэшированный источник должны приводить к честному отказу/ошибке, а не к поиску, скрытому download или выдуманному ответу.
