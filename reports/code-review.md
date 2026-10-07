# Независимый code-quality review

Дата: 2026-10-07. Reviewer: coder `t_9c90bf74`, независим от implementer `t_57ebfc61`.

## Вердикт

SPEC: FAIL / REQUEST_CHANGES. QUALITY: REQUEST_CHANGES. PROJECT READY: NO.

Результат research-фазы подтверждает настоящие local OpenResearch попытки и завершённое сравнение с ограничениями, но не закрывает acceptance проекта. В `reports/spec-review.md` точно перечислены G01–G06; просмотр исходников подтвердил их по текущим строкам. Код также имеет отдельные дефекты persistence и abstention, описанные ниже. Этот review не одобряет экспериментальный результат как production-ready и не разрешает новые C runs.

## Независимая проверка SPEC

- Exact target `DvSwvJVens8`, три практически ограниченных варианта и fixed question set зафиксированы в коде/конфиге и manifest.
- Manifest содержит шесть фактических OpenResearch runs: 2 done, 4 failed. Сравнение завершено честно с отрицательными/частичными исходами, но успешного original-RU head-to-head нет. Не запускал новые orx runs: C достиг stop cap.
- Реальный сохранённый русский source даёт transcript-backed Q&A без повторной extraction в выполненном CLI smoke. Parent instrumented probe дополнительно зафиксировал extractor=0, non-LLM network=0, два реальных Ollama вызова и неизменность source hash.
- SPEC остаётся FAIL по retrieval/grounding и стабильности generation (G01–G04), метрикам/эксплуатационной воспроизводимости (G05), обещанному local timed-transcript/JSON CLI и setup (G06), а также отложенным reusable skill и final audit (G08 в `spec-review.md`).
- У tracked files нет `data/`/`artifacts/` путей; raw transcript, media и bundle находятся под игнорируемыми путями. В Git есть bounded generated briefing, не исходная расшифровка. Origin существовал заранее; upstream handoff фиксирует согласование private repo. Remote не менялся, новых push/fetch не выполнялось.

## Подтверждённые findings

### CR-01 — HIGH — generation/benchmark падает без сохранения progress

`src/video_briefing/validation.py:71-87`, `src/video_briefing/briefing.py:69-115`, `src/video_briefing/benchmark.py:68-94`, `src/video_briefing/llm.py:45-67`.

Проверка требует evidence у каждого briefing/Q&A claim, однако retry/repair обрабатывает только неизвестные ID, не отсутствующее evidence или malformed provider JSON. `run_benchmark` сохраняет артефакты лишь после всей цепочки; ошибка на brief/позднем вопросе теряет валидный промежуточный результат и точку отказа из durable run artifacts. Реальные orx failures в manifest подтверждают этот путь; JSON mode не исключил malformed output.

Исправление: fail-closed schema/response handling, ограниченные попытки восстановления без выдумывания evidence, сохранение phase/question-id/effective config и уже валидных промежуточных результатов до последующего отказа.

Acceptance: regression cases на malformed/fenced/partial JSON, missing evidence и позднюю Q&A ошибку; persisted phase, question id, model/settings, source hash и partial artifacts; старые frozen runs не изменяются.

### CR-02 — HIGH — retrieval не обеспечивает recall для grounded Q&A

`src/video_briefing/retrieval.py:47-78`, `src/video_briefing/qa.py:20-25`.

По всему source строится sparse lexical ranking, затем передаются не более 12 совпадений и radius=1. При отсутствующем match ответ сразу объявляется abstention; проверки полного source для отрицательного вывода нет. Это соответствует наблюдаемым промахам фиксированного набора: потеря числового контекста и важных соседних/поздних ограничений, включая ложные abstentions, хотя точки есть в full transcript.

Исправление: source-aware coherent windows и recall стратегия для чисел/синонимов/переведённых запросов; отделить «не найдено retrieval» от «в полном transcript отсутствует». Не менять rubric под уже увиденные ответы.

Acceptance: regression на все 8 замороженных вопросов с требуемыми evidence ranges; покрыть 5.1B, контекстные caveats, условный финальный выбор, API/NAS различение; unknown ответ не должен выводиться из неполных excerpts.

### CR-03 — HIGH — язык и provenance extraction не обеспечивают сравнимость

`src/video_briefing/adapters/summarize.py:41-79,83-99`, `src/video_briefing/adapters/captions_api.py:21-65`, `src/video_briefing/benchmark.py:48-65`.

`summary_language` не контролирует language extractor; summarize при отсутствии языка назначает `und`, но pipeline продолжает brief/QA. Benchmark не блокирует/маркирует non-comparable source. Реальный B run вернул преимущественно английские timed captions при заявленном RU, а metadata не фиксирует выбранную track/translation lineage.

Исправление: определить source-language policy отдельно от output language; сохранять фактический track metadata/raw stdout где применимо; язык неизвестен или не совпадает — остановить как non-comparable либо явно маркировать fallback.

Acceptance: mismatch/`und` fixture fail-closed, track provenance проверяется; русский output проверяется отдельно; не добавлять ASR/cookies/auth fallback.

### CR-04 — HIGH — evidence ID валиден не значит, что утверждение поддержано

`src/video_briefing/validation.py:54-87`, `src/video_briefing/briefing.py:107-129,145-165`, `src/video_briefing/qa.py:29-46`.

`validate_citations` не сканирует поле `gist_evidence`, хотя briefing validator отдельно его требует; неизвестный gist ID в итоге может дать неясный `KeyError` при разрешении времени. При пустом gist evidence коды автоматически присваивают gist все topic IDs без semantic проверки. `render_brief` теряет `useful_ideas.kind`; caveats не имеют citations. В Q&A пустой claims[] делает `abstained=true`, даже если свободный answer содержит неподтверждённые фактические утверждения.

Исправление: валидировать каждый citation field и ссылку на support; не выводить gist citations из unrelated topics; сохранять source/inference labels; валидировать caveat/answer prose либо заменять на безопасный пустой abstention.

Acceptance: tests на неизвестные gist IDs, неподдержанный factual free-answer, пустые claims с фактическим prose, caveat citations и отображение inference/source labels; ссылки проверяются на ID и контекст.

### CR-05 — MEDIUM — метрики и effective request не отражают полный inference

`src/video_briefing/benchmark.py:45-94`, `src/video_briefing/llm.py:45-67`, `src/video_briefing/briefing.py:69-80,132-141`, `src/video_briefing/cli.py:152-158`.

`extract_cold` измеряет только cache miss wrapper extraction и может включать upstream warm cache; warm timings фактически не измерены. В model metadata попадает только `last_response` (последний вызов), не все chunks/synthesis/QA. Harness не записывает prompt hash/retrieval/effective config и промежуточные данные в каждом run-result; фактически runtime QA system находится в `qa.py`, не в tracked `prompts/qa.md`. Research manifest корректно раскрыл эти ограничения для завершённых runs, но код не обеспечивает такую полноту в будущем.

Исправление: переименовать/измерять cache state, сохранять per-call requested/returned model, usage, prompt/retrieval/version hashes и effective settings; явно обозначать unavailable fields, стоимость не считать нулём.

Acceptance: fake multi-call response regression плюс actual bounded live smoke: метрики перечисляют все вызовы или явно отмечают неполноту; cached Q&A показывает тот же source hash и 0 extraction/network.

### CR-06 — MEDIUM — заявленная CLI/setup поверхность неполна

`docs/design.md:11,16,20-21`, `src/video_briefing/cli.py:21-63,110-126,144-149`, `README.md:16-53`.

В дизайне обещаны local timed transcript input и общий `--json` на публичных командах, но CLI предоставляет только YouTube URL, без local timed transcript и без общего JSON интерфейса. `doctor` сообщает наличие файла фиксированного абсолютного Baoyu skill path и наличие runtime, не проверяет требуемые версии/реальный запуск; setup скрипт ставит Bun и summarize, но Baoyu dependency остаётся внешней. Это ограничивает чистую воспроизводимость и честную диагностику отсутствующих компонентов.

Исправление: либо сузить документацию до реализованной поддержки, либо добавить local timed input и стабильный JSON контракт; диагностировать фактические версии/зависимости и дать ясную ошибку для отсутствующего Baoyu source.

Acceptance: CLI help smoke для документированных команд и JSON схемы; отдельная local transcript fixture без сети; `doctor` тестирует missing/mismatched dependencies и возвращает actionable diagnostics.

### CR-07 — MEDIUM — заявленная immutable cache identity не защищена от перезаписи

`src/video_briefing/store.py:25-36,38-52`, `tests/test_store.py:11-18`.

Cache key намеренно не включает title, но `save()` безусловно перезаписывает bundle/raw для того же `(platform, video_id, language, variant)`. Тест прямо закрепляет, что новое содержимое с тем же ключом перетирает старое. Это противоречит дизайну immutable raw evidence и может молча заменить источник для сохранённых ссылок/benchmark cache.

Исправление: immutable write-once semantics для source identity или versioned content snapshots; при несовпадающем hash возвращать явный conflict/новый snapshot, не перезаписывая исходник.

Acceptance: тест сохраняет исходный hash после повторной extraction с изменившимся raw; конфликт диагностируется, выбор новой версии явный, cache read проверяет обе metadata/source hashes.

### CR-08 — MEDIUM — Baoyu может принять устаревший output за новый extraction

`src/video_briefing/adapters/baoyu.py:24-40`.

Каталог повторно используется по `video_id/language`; после exit code 0 адаптер выбирает последний по mtime `transcript-raw.json` из дерева, не проверяя, что файл создан/изменён текущим запуском. Если upstream завершится успешно, но не создаст свежий output, может быть загружен старый transcript как будто это актуальный extraction.

Исправление: уникальный временный output directory на invocation либо зафиксировать до запуска существующие outputs и потребовать новый verified file; проверять target metadata.

Acceptance: subprocess fixture с pre-existing stale JSON и exit 0 без нового файла завершается ошибкой; нормальный свежий output с target ID принимается.

## Проверки в этой review-сессии

Выполнены в `/Users/alexbeketov/video-briefing`:

- `uv run --frozen pytest` → 28 passed in 0.09s.
- `uv run --frozen python -m compileall -q src tests` → exit 0.
- `uv run --frozen video-briefing --help` и `... benchmark --help` → exit 0; help показывает пять subcommands, но не JSON/local transcript surface.
- `uv run --frozen video-briefing doctor` → exit 0, Ollama reachable=true; Baoyu source, Bun, summarize отмечены как существующие.
- `uv run --frozen video-briefing ask 'https://www.youtube.com/watch?v=DvSwvJVens8' 'Какую рекомендацию по NAS и какие функции Mini Scloud уже доступны или обещаны?' --variant captions_api` → exit 0; вернул структурированные claims с сохранёнными segment IDs/timestamps. Это реальный cached CLI Q&A smoke, не повторная extraction/формальный orx run; точность ответа не утверждается одним фактом успешного вызова.
- `git diff --check` → exit 0.
- `git ls-files data artifacts` → пусто. `git check-ignore -v` подтвердил игнорирование локальных `source.raw`, bundle и reference raw transcript.
- `git status --short` → только pre-existing untracked `.codegraph/`; не трогал. `git remote -v` показал существующий origin; не менялся.

## Non-blocking notes

- Успешные segment IDs/time resolution нужны, но сами по себе не доказывают смысловую поддержку citations.
- Загруженный `.codegraph/` оставлен как есть, не добавлялся в report scope.
- Не выполнялись новые extraction, новые orx runs, изменения кода, commits, push/fetch, установка/публикация skills.

## Рекомендованный следующий шаг

Сначала закрыть CR-01–CR-04 и проверить regression на фиксированном source/evaluation без изменения уже frozen результатов; затем CR-05–CR-08 и повторная независимая acceptance-проверка. После этого разрешённый downstream hardening task может выполнить свой scoped skill workflow. Текущий review не считает проект принятым.
