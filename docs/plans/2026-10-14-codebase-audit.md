# Codebase Audit Remediation Implementation Plan

**Goal:** исправить подтверждённые проблемы Video Briefing, сохранить benchmark-результаты и добавить воспроизводимые проверки до слияния.

**Architecture:** сохранить текущие CLI, адаптеры, хранилище свидетельств и форматы результатов. Изолировать вывод каждого benchmark-запуска, передавать только безопасные типизированные ошибки в MCP и проверять отсутствие обязательной зависимости командой `doctor`. Добавить линтер и CI-матрицу на все поддерживаемые версии Python.

**Tech Stack:** Python 3.11–3.14, `uv`/`uv.lock`, pytest, Ruff, GitHub Actions.

Этот ExecPlan следует локальному стандарту ExecPlans, прочитанному перед началом работы. Он живой: разделы `Progress`, `Surprises & Discoveries`, `Decision Log` и `Outcomes & Retrospective` обновляются по мере работы. Все коммиты отправляются fast-forward в `origin/main`; force-push запрещён.

## Purpose / Big Picture

После работы `video-briefing doctor` завершится ошибкой, если отсутствует обязательная библиотека титров, а MCP-клиенты будут различать ожидаемые безопасные отказы источника и неизвестную внутреннюю ошибку. Каждый CLI-запуск benchmark получит собственную закрытую папку с прогрессом и результатами, поэтому повторный запуск не заменит прежние результаты. Ruff, тесты и сборка будут запускаться локально и в GitHub Actions на всех поддерживаемых версиях Python.

Проект остаётся source-first инструментом: не меняются извлечение источников, доказательная модель, генерация краткого обзора и Q&A, а также схема JSON результатов. Исторические отчёты, пользовательские артефакты, файлы-примеры и лицензионное решение остаются нетронутыми.

## Progress

- [x] (2026-10-14 14:26Z) Проверить точный slug и baseline. Репозиторий — `AlekseyBeketov/video-briefing`; `main` исходно совпадала с `origin/main` на `c6bec82d1cbaabc88c9612b669fd1df7bee916e0`. 172 теста прошли на Python 3.11, 3.13 и 3.14; `compileall`, offline lock-check и сборка успешны.
- [x] (2026-10-14 14:26Z) Согласовать рекомендованный объём с пользователем, записать дизайн и отправить коммит `99821af` в `origin/main`.
- [x] (2026-10-14 14:26Z) Зафиксировать до изменений состояние Git. Незатронутые пользовательские изменения: `reports/production-acceptance.md`, `.codegraph/`, `reports/citation-boundary-repair.*`, `reports/final-review.*`, `reports/retrieval-coverage-repair.*`.
- [x] (2026-10-14 14:30Z) Исправить `doctor`: ненулевой код при отсутствии обязательного captions package, нулевой при отсутствии optional ASR. Новый тест сначала подтвердил прежний ошибочный код 0; все 8 тестов `tests/test_cli.py` прошли после фикса. Коммит `79bfcdd` отправлен в `origin/main`.
- [x] (2026-10-14 14:30Z) MCP-классификация и тесты готовы: 12 тестов адаптера и MCP прошли, включая проверку, что неизвестная ошибка не раскрывает детали. Коммит `607a93e` отправлен в `origin/main`.
- [x] (2026-10-14 14:33Z) Benchmark outputs изолированы: каждый CLI запуск получает уникальную папку, progress и results пишутся приватно и атомарно, ошибку CLI сопровождает путь к run folder, протокол обновлён. 17 целевых тестов прошли; коммит `361755e` отправлен в `origin/main`.
- [x] (2026-10-14 14:37Z) Подтверждённый dead code удалён, Ruff 0.17.0 закреплён в dev extra, workflow проверяет четыре версии Python. Коммит `1d85eb6` отправлен; GitHub Actions run `38582072206` завершился успешно на Python 3.11–3.14.
- [x] (2026-10-14 14:40Z) Финальная проверка: по 184 теста прошли локально на Python 3.11, 3.13 и 3.14; Ruff, разбор YAML, `compileall`, `uv lock --check --offline`, wheel/sdist build, `doctor` и `git diff --check` успешны. Python 3.12 локально не установлен, но CI проверил его. Итоги зафиксированы в этом документе.

## Surprises & Discoveries

- `src/video_briefing/cli.py::_doctor` печатает `youtube_transcript_api.available=false`, но всё равно возвращает код 0. Зависимость обязательна в `pyproject.toml`, поэтому автоматическая проверка сейчас скрывает неработающую установку.
- `src/video_briefing/mcp_server.py::_safe_call` сводит безопасные отказы титров к `operation_failed`. Адаптер уже различает отсутствие титров, блокировку сети и требование cookies, но MCP теряет это различие.
- `src/video_briefing/benchmark.py` создаёт `progress.json` и итоговые файлы обычным `write_text`. В проверочном каталоге с обычной маской процесс создал файлы режима `0644`. CLI повторно использует один `runs` каталог и фиксированные имена, что затирает результаты предыдущего запуска.
- Ruff 0.17.0 с правилами `E4,E7,E9,F` нашёл неиспользуемые импорты и `E402` из-за вызова `pytest.importorskip` перед MCP SDK-импортами. Импорты переставлены через module-level `try/except ImportError` и `pytest.skip`; правила не подавлялись, полный Ruff check проходит.
- Новый тест `test_doctor_returns_nonzero_when_required_captions_dependency_is_missing` подтвердил дефект: до исправления `main(["doctor"])` печатал `available: false`, но возвращал 0. После фикса весь `tests/test_cli.py` прошёл.
- Повторный benchmark использовал один и тот же `--output-dir` с фиксированными именами файлов. Тесты сначала упали на общем каталоге, неограниченных режимах и отсутствии пути диагностики; после выделения уникальной подпапки все 17 тестов benchmark и CLI прошли.
- Ruff-совместимость MCP теста достигнута через `try/except ImportError` и module-level skip, без `noqa`. Ruff 0.17.0 проверил весь `src` и `tests` без диагностик; `uv lock --check --offline` разрешил 44 пакета.
- Первый полный тестовый прогон в sandbox дал `183 passed, 1 failed`: существующий redirect regression test не смог bind `127.0.0.1` из-за sandbox policy. С разрешённым loopback тестированием тот же набор завершился `184 passed in 4.34s`.
- Первоначальный `uv run` под sandbox не имел доступа к кэшу в `~/.cache/uv`. Один запуск также заменил существующий игнорируемый `.venv` с Python 3.9 пустым окружением Python 3.14. Последующие локальные проверки должны задавать отдельный `UV_PROJECT_ENVIRONMENT` в `/tmp`; пользовательскую `.venv` не восстанавливать и не удалять.
- Нет GitHub Actions workflow и закреплённого Ruff в dev dependencies. В истории встречаются персональные absolute home-directory paths; это исторические записи, их не редактировать. Файл лицензии отсутствует; не добавлять лицензию без решения владельца.
- Git-индекс в основном checkout доступен только для чтения без эскалации. Пользователь прямо запросил коммиты и push в `main`; Git-операции требуют `require_escalated`. Согласованный дизайн уже успешно отправлен после проверки SHA удалённой ветки.

## Decision Log

- Decision: сохранить архитектуру и добавить только исправления подтверждённых отказов, защиты результатов и автоматических проверок. Rationale: так выполняется цель поддерживаемости без переписывания работающих частей. Date/Author: 2026-10-14, пользователь согласовал рекомендованный объём.
- Decision: каждый CLI benchmark запуск записывать в отдельную дочернюю папку внутри заданного `--output-dir`, создаваемую с режимом `0700`; файлы и временные файлы создавать с режимом `0600` и атомарной заменой. Rationale: текущие фиксированные имена перезаписывают результаты, а права файлов не ограничены самим приложением. Уже существующие родительские каталоги не менять.
- Decision: показывать отдельные безопасные коды для ожидаемых ошибок адаптера титров и локального ASR; все неизвестные исключения оставлять обобщёнными. Rationale: пользователь MCP получает полезную диагностику без утечки исходного текста или деталей неожиданных ошибок.
- Decision: включить Ruff `E4,E7,E9,F`, не ослаблять правила ради optional-import теста, закрепить версию Ruff и проверить lock-файл. Rationale: стандартные ошибки импорта/синтаксиса и неиспользуемый код ловятся в CI; опциональный SDK корректно пропускает integration-тест без глобальных исключений.
- Decision: workflow запускается для pull request и push в `main` на Python 3.11, 3.12, 3.13 и 3.14; использует `uv.lock`, тесты с `dev` и `mcp` extras, Ruff, `compileall` и `uv build`. Rationale: покрывает весь объявленный диапазон Python и доступные проверки пакета.
- Decision: каждый смысловой коммит отправлять в удалённый `main` после проверки, что удалённая ветка стоит на его родителе; не переписывать удалённую историю. Rationale: прямое указание пользователя.

## Outcomes & Retrospective

Подтверждённые проблемы исправлены. `doctor` теперь возвращает ненулевой код, если обязательная зависимость captions отсутствует. MCP передаёт безопасные и различимые причины ошибок источника и ASR, сохраняя обобщённый ответ для неизвестных исключений. Benchmark CLI создаёт новую закрытую папку на каждый запуск, атомарно пишет приватные файлы, больше не затирает прежние запуски и указывает папку диагностики при ошибке. Удалены только неиспользуемые импорты/привязка и helper `_tool_version`, у которого не было вызовов. Добавлены закреплённый Ruff, GitHub Actions для всех поддерживаемых версий и regression tests.

Локально каждый из наборов на Python 3.11, 3.13 и 3.14 завершился `184 passed`; CI run `38582072206` завершился `success` на 3.11, 3.12, 3.13 и 3.14, включая lock-check, Ruff, pytest, compileall и сборку wheel/sdist. `doctor` в текущем окружении вернул JSON со всеми ожидаемыми установленными обязательными зависимостями и код 0. Локальные тесты требовали разрешить loopback для уже существующего HTTP regression test; один ограниченный sandbox прогон отказал на bind, тот же полный набор с разрешённым loopback прошёл.

Не принято решений о лицензии. Персональные home-directory paths в исторических tracked-записях сохранены по границе задачи; их очистка требует отдельного решения. Python 3.12 не установлен локально, но проверен CI. Реальные обращения к YouTube, Baoyu, Ollama и облачным моделям не выполнялись: изменения проверены на fixture и локальном loopback. Начальный неудачный запуск `uv` заменил игнорируемый `.venv` с Python 3.9 на пустое окружение 3.14; дальнейшие проверки использовали `/tmp`, `.venv` не восстанавливался. В Git остались только перечисленные исходные пользовательские изменения.

### Audit Inventory

Reviewed package modules: `src/video_briefing/__init__.py`, `src/video_briefing/adapters/__init__.py`, `src/video_briefing/adapters/baoyu.py`, `src/video_briefing/adapters/captions_api.py`, `src/video_briefing/benchmark.py`, `src/video_briefing/briefing.py`, `src/video_briefing/citation_validation.py`, `src/video_briefing/cli.py`, `src/video_briefing/evidence_api.py`, `src/video_briefing/grounding.py`, `src/video_briefing/llm.py`, `src/video_briefing/local_asr.py`, `src/video_briefing/mcp_server.py`, `src/video_briefing/models.py`, `src/video_briefing/qa.py`, `src/video_briefing/resources/__init__.py`, `src/video_briefing/retrieval.py`, `src/video_briefing/source_guards.py`, `src/video_briefing/store.py`, and `src/video_briefing/validation.py`.

Reviewed tests: `tests/test_adapters.py`, `tests/test_benchmark.py`, `tests/test_briefing.py`, `tests/test_cached_qna.py`, `tests/test_captions_api.py`, `tests/test_citation_validation.py`, `tests/test_cli.py`, `tests/test_evidence_api.py`, `tests/test_fixed_source_recall.py`, `tests/test_generation_coverage.py`, `tests/test_llm.py`, `tests/test_llm_safety.py`, `tests/test_local_asr.py`, `tests/test_mcp_server.py`, `tests/test_qa.py`, `tests/test_qa_citation_boundaries.py`, `tests/test_retrieval.py`, `tests/test_retrieval_windows.py`, `tests/test_source_guards.py`, `tests/test_store.py`, and `tests/test_validation.py`.

Также изучены метаданные пакета и lock (`pyproject.toml`, `uv.lock`), `.gitignore`, `README.md`, `config/experiment.json`, `scripts/setup-tools.sh`, документы о дизайне/агентах/benchmark/отложенных решениях, исследовательские манифесты и evaluation, существующие review/release/comparison отчёты. В итоговые коммиты вошли только перечисленные в плане файлы, дизайн и этот отчёт; пользовательские изменения остались вне коммитов.

### Security Review Notes

Проект предоставляет локальный CLI и MCP stdio, а не HTTP UI: XSS, CSRF и браузерная авторизация не относятся к его интерфейсам. Проверены URL и модельные endpoint validation, отказ от loopback/private URL для недоверенного источника, запрет credentials в endpoint, явный privacy opt-in для облачной модели, ограничения и очищенное окружение локальных subprocess, immutable source cache и bounded citation validation. MCP не возвращает source text для неожиданных исключений; новые типы ошибок разрешают показывать только безопасные сообщения. SHA-256 используется для целостности и provenance данных, не как аутентификация. Тесты используют synthetic fixtures; живые YouTube/LLM-сервисы не проверялись.

## Context and Orientation

Корень checkout — текущая рабочая директория; package source находится в `src/video_briefing/`, тесты — в `tests/`. `cli.py` объявляет команды и превращает исключения в JSON-ошибки; `benchmark.py` записывает промежуточный прогресс и итоговые JSON/Markdown файлы; `adapters/captions_api.py` обращается за публичными титрами; `mcp_server.py` преобразует операции в инструменты MCP. `local_asr.py` запускает локальный ASR и содержит `LocalASRError`. `store.py` уже показывает безопасный образец записи: ограниченная папка, временный файл и `os.replace`.

`uv.lock` фиксирует версии зависимостей. В `pyproject.toml` уже есть Python-диапазон `>=3.11,<3.15`, extras `dev` и `mcp`, а также базовая конфигурация Ruff. Отчёт benchmark содержит source-derived текст, поэтому режимы доступа и сохранение предыдущих запусков имеют значение. `docs/benchmark-protocol.md` описывает отдельные артефакты каждого запуска.

Работа идёт в текущей локальной ветке `main`, содержащей дизайн-коммит `99821af`. Перед каждым push сначала читать `rtk git ls-remote origin refs/heads/main`; разрешать только fast-forward. Все команды локальной оболочки запускать через `rtk`. Для `uv` использовать `/tmp/video-briefing-uv-cache` и отдельные `UV_PROJECT_ENVIRONMENT` в `/tmp`. Не добавлять в индекс пользовательские отчёты или `.codegraph/`.

## Plan of Work

Сначала добавить узкие тесты для статуса `doctor` и кодов ошибок MCP, затем изменить только классификацию этих отказов. После этого изолировать benchmark-запуски: выбранный `--output-dir` трактуется как контейнер запусков, а CLI создаёт внутри новую папку с UTC-временем и коротким случайным суффиксом. Внутри неё прогресс и итоговые артефакты сохраняются атомарно с закрытыми правами; при ошибке пользователь получает путь к сохранённому `progress.json`. Обновить описание протокола, не меняя схемы результатов.

Следом удалить доказанно мёртвый helper и неиспользуемые привязки/импорты. Добавить закреплённый Ruff в dev extra, включить `E4,E7,E9,F`, привести optional MCP test imports в соответствие и добавить workflow. Каждый законченный блок проверять, коммитить отдельным сообщением и отправлять fast-forward в `origin/main`. В конце выполнить локальную матрицу доступных версий, пройти полный diff и записать фактический итог в этот документ.

## Concrete Steps

### Task 1: Исправить результат `doctor` при отсутствующей зависимости

Файлы: `tests/test_cli.py` и `src/video_briefing/cli.py`, функция `_doctor`.

Добавить тест, который подменяет `package_version` исключением `PackageNotFoundError`, стабилизирует вызовы `subprocess.run`, вызывает `main(["doctor"])` и проверяет JSON с `available: false` и ненулевой код. Сначала запустить точечный тест и убедиться, что он падает только на ожидаемом коде возврата. Затем вернуть 1 после вывода отчёта, если обязательный `youtube-transcript-api` отсутствует; отсутствующие optional ASR-инструменты не должны менять код.

Проверить командой `rtk uv run --python 3.13 --frozen --extra dev --extra mcp pytest tests/test_cli.py -q`. Ожидается, что все CLI-тесты пройдут. Зафиксировать только два файла коммитом `fix(cli): fail doctor without captions dependency`, проверить родителя по `origin/main` и отправить `main`.

### Task 2: Передавать безопасные причины ошибок через MCP

Файлы: `src/video_briefing/adapters/captions_api.py`, `src/video_briefing/mcp_server.py`, `tests/test_captions_api.py`, `tests/test_mcp_server.py`, `docs/agent-integration.md`.

Добавить отдельные типы ожидаемого отказа адаптера для недоступных титров, сетевой блокировки и обязательной аутентификации/cookies; сохранить существующие безопасные сообщения и ограничения анонимного доступа. В `_safe_call` сопоставить эти типы со стабильными кодами `source_unavailable`, `source_blocked` и `source_auth_required`. Сопоставить безопасный `LocalASRError` с `source_processing_failed`. `ValueError` остаётся `invalid_input`; неизвестное исключение остаётся `operation_failed` с обобщённым сообщением.

Сначала добавить тесты для каждого типа и проверить их падение. Затем проверить полные коды и сообщения, а также что неожиданный `RuntimeError` не раскрывает его текст. Для адаптера оставить существующие проверки запрета cookies и сетевых обходов. Запустить `rtk uv run --python 3.13 --frozen --extra dev --extra mcp pytest tests/test_captions_api.py tests/test_mcp_server.py -q`. Коммит `fix(mcp): preserve safe source error reasons`; затем проверить удалённого родителя и отправить.

### Task 3: Изолировать и защитить benchmark-запуски

Файлы: `src/video_briefing/benchmark.py`, `src/video_briefing/cli.py`, `tests/test_benchmark.py`, `tests/test_cli.py`, `docs/benchmark-protocol.md`.

Добавить helper CLI, который создаёт уникальную папку `run-<UTC timestamp>-<short uuid>` внутри корня `--output-dir`. Новый каталог запуска получает режим `0700`; не менять режим уже существующего корня, указанного пользователем. Путь запуска передавать как `progress_dir` и в `write_run`, а в успешном JSON-ответе возвращать файлы из этой папки. При исключении обернуть ошибку безопасным сообщением с путём к `progress.json`; оригинальные подробности уже сохранены локально самим benchmark.

В `benchmark.py` заменить фиксированные `.tmp` файлы общим атомарным writer: создавать родительскую папку ограниченно, временный файл через `tempfile.mkstemp` в той же папке, записывать и `fsync`, затем вызывать `os.replace`; убирать временный файл при ошибке. Создаваемые файлы должны иметь `0600` на POSIX. Не менять схемы `progress.json`, `metrics.json`, `briefing.md` и `answers.json`. Текущий CLI-корень `~/.../runs` и явно заданный `--output-dir` становятся контейнером, так что завершённые и неудачные запуски остаются в отдельных дочерних папках.

Добавить тесты, что два запуска получают разные каталоги, POSIX-режимы каталога и файлов ограничены, все финальные пути возвращаются, а неудачный многочастный запуск сохраняет читаемый `progress.json` и его путь виден CLI. Не выполнять генерацию с реальным источником или облачной моделью. Обновить `docs/benchmark-protocol.md` описанием контейнера запусков и локальной приватной папки.

Запустить `rtk uv run --python 3.13 --frozen --extra dev --extra mcp pytest tests/test_benchmark.py tests/test_cli.py -q`. Ожидаются зелёные тесты и отсутствие временных файлов после успешной замены. Коммит `fix(benchmark): isolate and protect run outputs`, затем fast-forward push.

### Task 4: Удалить мёртвый код и добавить Ruff

Файлы: `src/video_briefing/cli.py`, `src/video_briefing/local_asr.py`, `src/video_briefing/adapters/baoyu.py`, `tests/test_mcp_server.py`, `pyproject.toml`, `uv.lock`.

Удалить `_tool_version`, который не вызывается; удалить неиспользуемый `re` из `local_asr.py` и `asyncio` из `tests/test_mcp_server.py`; заменить неиспользуемую привязку `platform` результата `parse_video_url` в `baoyu.py` на `_`. Не удалять более крупные модули, ресурсы, prompts или отчёты.

Добавить `ruff==0.17.0` в dev extra и в `[tool.ruff.lint]` явно выбрать `E4`, `E7`, `E9`, `F`. Исправить порядок optional MCP-импортов через верхнеуровневый `try`/`pytest.skip(..., allow_module_level=True)`, сохранив пропуск теста, если MCP extra не установлен. Не добавлять `noqa` и не игнорировать правила. Пересобрать `uv.lock` и выполнить `rtk uv run --python 3.13 --frozen --extra dev --extra mcp ruff check src tests`.

Ожидается отсутствие lint-диагностик. Коммит `chore: remove dead code and add Ruff checks`, затем проверить `origin/main` и отправить.

### Task 5: Добавить CI workflow

Создать `.github/workflows/ci.yml`. Workflow запускается на pull request в `main` и push в `main`, даёт только `contents: read`, использует матрицу Python `3.11`, `3.12`, `3.13`, `3.14` и не останавливает остальные версии из-за первой ошибки.

Использовать `actions/checkout` и официальный `astral-sh/setup-uv`, закрепив actions полными commit SHA с комментарием версии. Для `setup-uv` установить Python из matrix и включить cache. В каждом job выполнить `uv lock --check`, `uv sync --locked --extra dev --extra mcp`, `ruff check src tests`, `pytest`, `python -m compileall -q src tests` и `uv build`. Установка должна использовать extras из lock-файла; никакой сетевой/LLM-интеграционный тест не запускать.

Проверить YAML локально доступным parser/linter, если он уже установлен; не добавлять инструмент только ради одной проверки. CI-команду повторить локально на текущей Python-версии. Коммит `ci: add python quality checks`, проверить удалённого родителя и отправить.

### Task 6: Финальная проверка и отчёт

После всех коммитов выполнить полный набор тестов с extras `dev` и `mcp` на локально установленных Python 3.11, 3.13 и 3.14. Для каждой версии задать отдельный `UV_PROJECT_ENVIRONMENT` в `/tmp`; пример формы команды:

    rtk env UV_CACHE_DIR=/tmp/video-briefing-uv-cache UV_PROJECT_ENVIRONMENT=/tmp/video-briefing-py313-env uv run --python 3.13 --frozen --extra dev --extra mcp pytest

Также выполнить Ruff, `python -m compileall -q src tests`, `uv lock --check --offline`, `uv build --out-dir /tmp/video-briefing-final-dist --offline` и `git diff --check`. Полные проверки обязательны по критериям текущей задачи, несмотря на обычное правило проекта, что пользователь запускает полную сборку.

Проверить `rtk git show --stat --oneline` для каждого нового коммита, итоговый `rtk git status --short --branch` и `rtk git ls-remote origin refs/heads/main`. Убедиться, что все созданные для задачи коммиты есть в удалённой истории и изменённые пути соответствуют плану; пользовательские отчёты, `.codegraph/`, секреты и случайные файлы в индекс не попадали. После этого вписать реальные числа тестов, команды и результаты в `Progress`, `Surprises & Discoveries` и `Outcomes & Retrospective`, закоммитить отчёт `docs: record codebase audit results` и отправить его в `main`.

## Validation and Acceptance

Поведение считается исправленным, если тест показывает ненулевой код `doctor` при отсутствующей обязательной зависимости, MCP возвращает отдельные безопасные коды для ожидаемых сбоев и обобщает неизвестные, а два benchmark запуска не делят файлы и не затирают друг друга. На POSIX права нового каталога запуска равны `0700`, файлов — `0600`; при ошибке в каталоге остаётся валидный `progress.json`.

Качество подтверждается зелёными Ruff, pytest на Python 3.11/3.13/3.14, компиляцией модулей, lock-check, сборкой wheel и sdist, а также workflow на четырёх версиях Python. Финальное сообщение содержит только фактически выполненные команды и результаты; неуспешные или недоступные проверки указываются явно.

## Idempotence and Recovery

Повторные локальные проверки безопасны: каждая версия Python использует отдельное `/tmp` окружение, а каждый CLI benchmark запуск пишет в новый дочерний каталог. Источники, локальный cache свидетельств, tracked отчёты и существующий `.venv` не трогать. При неудачном тесте сначала диагностировать конкретную ошибку; одинаковую ошибку после двух попыток исследовать по документации перед повторной правкой.

Если push отклонён из-за обновившегося `origin/main`, не использовать force-push: загрузить новую историю, проверить изменения, выполнить fast-forward/rebase только собственных коммитов и повторно проверить diff. Если escalation для записи Git будет отклонена, сохранить изменения локально и сообщить точную причину, не делая вид, что push выполнен.

## Artifacts and Notes

Дизайн записан в `docs/plans/2026-10-14-codebase-audit-design.md` (коммит `99821af`), план/отчёт — в этом документе. Коммиты отправлены по порядку: `99821af`, `80383aa`, `79bfcdd`, `607a93e`, `361755e`, `1d85eb6`, затем коммит этого отчёта. Базовое состояние: `172` теста на Python 3.11, 3.13 и 3.14 проходили до правок. После изменений `184` теста прошли на каждой локально установленной версии. `ruff check src tests`, `python -m compileall -q src tests`, `uv lock --check --offline`, `git diff --check`, сборка wheel и sdist успешны. [CI run `38582072206`](https://github.com/AlekseyBeketov/video-briefing/actions/runs/38582072206) успешен на Python 3.11–3.14; `video-briefing doctor` smoke test вернул 0.

## Interfaces and Dependencies

`video_briefing.cli._doctor(args: argparse.Namespace) -> int` сохраняет прежний JSON-отчёт и возвращает код 1 при отсутствии `youtube-transcript-api`; отсутствие необязательных ASR-компонентов не меняет его.

`video_briefing.adapters.captions_api` предоставляет узкие исключения для ожидаемых недоступности титров, блокировки сети и необходимости аутентификации. `video_briefing.mcp_server._safe_call(operation)` преобразует только эти исключения и `LocalASRError` в безопасные стабильные ответы; неизвестные исключения не раскрываются.

CLI `benchmark --output-dir PATH` трактует `PATH` как корень хранения запусков и создаёт уникальный дочерний каталог. `benchmark._save_progress(output_dir, progress)` и `benchmark.write_run(result, output_dir)` сохраняют существующие payload-схемы, используя новые уникальные временные файлы, атомарную замену и закрытые режимы.

Ruff доступен из dev extra и применяет `E4,E7,E9,F`. `.github/workflows/ci.yml` использует только закреплённые official actions, читает lock-файл и проверяет полный объявленный диапазон Python.
