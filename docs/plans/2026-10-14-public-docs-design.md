# Дизайн публичной документации и agent setup

## Цель

Сделать проект понятным новому пользователю и дать ему безопасный копируемый prompt для настройки Video Briefing в Hermes, Codex CLI или Claude Code. Основной README будет английским, рядом появится русская локализация. Документы описывают только поведение, подтверждённое исходниками, CLI и уже выполненными проверками.

Подтверждённый репозиторий: `AlekseyBeketov/video-briefing`, remote `origin` указывает на `https://github.com/AlekseyBeketov/video-briefing.git`. Установленная версия пакета — `0.2.0`; Python ограничен `>=3.11,<3.15`. CI проверяет Python 3.11–3.14 на Ubuntu. Установочный сценарий из checkout — `uv sync --frozen`; необязательный MCP extra подключается через `--extra mcp`.

## Структура

- `README.md` — английская точка входа: назначение, prerequisites, установка, quick start, YouTube и local MP4, agent/MCP setup, configuration, ограничения, troubleshooting, разработка и статус лицензии.
- `README.ru.md` — эквивалентная русская версия с переключателем языков в обе стороны.
- `docs/agent-integration.md` — общие требования к установке и privacy model, точные MCP tool names и ссылки на три agent-specific инструкции.
- `docs/agent-prompts/hermes.md`, `codex.md`, `claude-code.md` — официальный MCP setup reference соответствующего агента, отдельный англоязычный copyable prompt и явный статус проверки prompt в реальном клиенте.
- `skills/video-briefing/SKILL.md` и `src/video_briefing/resources/SKILL.md` — синхронные переносимый и packaged экземпляры skill. Оба нужны: первый поставляется в репозитории, второй входит в Python package и печатается командой `video-briefing skill`.
- Тест проверяет идентичность намеренно продублированных `SKILL.md`, `brief.md` и `qa.md` между исходными `skills/`/`prompts/` и packaged resources.
- `docs/design.md` будет приведён к текущему source-first поведению; `docs/pending-decisions.md` — к фактически открытым решениям; старый план 2026-10-05 получит заметную отметку, что это историческая запись.

## Подтверждённое поведение, которое попадёт в документы

По умолчанию CLI не вызывает LLM. YouTube ingestion получает только доступные timed captions; язык по умолчанию — русский, а extractor по умолчанию — `youtube-transcript-api`. `search` и `read` возвращают bounded evidence для синтеза вызывающим агентом. MCP предоставляет `ingest_youtube`, `ingest_local_mp4`, `search_video_evidence`, `read_video_evidence` и `validate_video_claims`; read-only профиль состоит из последних трёх инструментов.

Local MP4 требует явного `--local-asr` и пользовательских FFmpeg/FFprobe, `transcribe-cli` и GGUF model. Этот путь локально обрабатывает аудио, поддерживаемая модель рассчитана на русский, а timestamps ограничены 24-секундными окнами. Команды `brief` и `ask` существуют как optional model-generated workflow; cloud-backed и non-loopback endpoints требуют явного `--allow-cloud`. Validator проверяет источник, буквальные quotes, segment IDs и границы времени, но не смысловую поддержку и внешнюю истинность.

Кэш хранится вне checkout в системном data directory, который можно заменить через `VIDEO_BRIEFING_DATA_HOME`. MCP сам не вызывает LLM, однако переданные вызывающему агенту evidence-фрагменты становятся контекстом его модели; README и prompts должны прямо указать на это.

## Безопасность и границы

Prompts требуют сначала проверить OS, Python, `uv`, CLI, README и официальные инструкции MCP выбранного агента. Установка использует отдельный clone и Python environment; существующую папку, `.venv`, agent config или skill-файл нельзя перезаписывать. Совпадающая конфигурация переиспользуется; конфликт имени или необходимость destructive edit останавливают работу до вопроса пользователю. Секреты не читаются и не выводятся; cookies, proxies, credential reuse, `sudo`, обновления системного Python и автоматические cloud/model installs не используются.

Agent prompts проверяют `video-briefing doctor`, наличие `video-briefing-mcp` и фактический MCP connection/tool catalog. Ingestion частного видео запрещён без отдельного разрешения. Если нет безопасного публичного URL или доступного cached source, prompt должен честно отметить, что проверка MCP schema прошла, а content end-to-end не проверен.

Лицензия не выбирается этим изменением: `LICENSE` в репозитории отсутствует, поэтому README не будет называть проект лицензированным и укажет, что условия использования/распространения пока не определены. Исследовательские rubric, исторические reports и артефакты OpenResearch останутся нетронутыми. Публикация release, смена visibility и выбор лицензии не входят в этот scope.

## Официальные источники для agent-конфигураций

- [Codex CLI MCP](https://developers.openai.com/codex/mcp) — `codex mcp add/list`, user/project config, `enabled_tools` allowlist.
- [Claude Code MCP](https://code.claude.com/docs/en/mcp) — stdio config, local scope и connection checks; prompt сохраняет штатное подтверждение tool calls.
- [Hermes Agent MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) и [reference config](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference/) — `mcp_servers`, `tools.include`, `sampling.enabled` и `hermes mcp test`. Hermes включает MCP sampling по умолчанию; конфигурация явно отключает его, поскольку Video Briefing не просит модельные ответы от хоста.
- [uv installation](https://docs.astral.sh/uv/getting-started/installation/) — prerequisites и установка `uv`.

## Проверка

В текущем checkout CLI `--help`, `--version` (`0.2.0`), `doctor` и вывод packaged skill выполнены на ранее установленном Python 3.11 окружении. `doctor` не делает network probes и сообщил обязательную captions dependency доступной. Установленный skill совпадает с обоими tracked экземплярами по SHA-256. В этой среде новый `uv sync` не удалось завершить из-за DNS недоступности PyPI; предыдущий успешный CI и package/wheel acceptance остаются отдельными датированными доказательствами, не заменяют эту попытку. `hermes` CLI недоступен для записи install state, `claude` CLI не найден; установленный `codex mcp --help` доступен. Поэтому три конкретных prompts будут отмечены как не прошедшие end-to-end запуск в соответствующем клиенте.

Дата сверки внешних agent/uv docs и локальной CLI: 2026-10-14. При повторной сверке выяснено, что актуальная документация Hermes поддерживает `sampling.enabled: false`; параметр останется как fail-closed privacy setting.
