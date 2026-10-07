# Source preflight: DvSwvJVens8

Статус этой фазы: реальный timed source доступен; evaluation зафиксирована до чтения candidate-generated answers. Это не реализованный E2E и не результат formal OpenResearch comparison. Исследовательская карточка `t_4924c5e9`; следующий этап `t_93e3976e` зависит также от implementation.

## 1. Identity, доступ и происхождение

Точный URL: https://www.youtube.com/watch?v=DvSwvJVens8. Название «AI PC — личный ИИ у вас дома! Объясняем», канал Droider. Анонимная watch-page вернула HTTP 200; сохранённый `ytInitialPlayerResponse` имеет exact videoId и playability `OK`, duration **1457 s = 24:17**. oEmbed отдельно подтверждает название/канал, но не является источником содержания.[1][2]

Player объявляет только `ru`, `kind=asr`, «Русский (создано автоматически)», переводимость true; original audioTrackId `ru.4`. Приоритет для этого ролика — оригинальные ru captions. Русский язык ответа не требует русского языка исходника вообще: для другого видео сначала его original language, затем реально доступный original track; машинный перевод — отдельный явно маркированный fallback.[1]

Реальная anonymous extraction: `youtube-transcript-api==1.2.4`, exact ID, `--languages ru --format json`. Первая попытка сохранена предыдущим запуском этой же карточки; повторная проверка сейчас завершилась exit 0 и дала byte-identical результат. Текст прочитан полностью, не создан по title/description.[1][5]

Выполненная повторная команда из `/Users/alexbeketov/video-briefing`:

    /usr/bin/time -p uvx --no-config --cache-dir data/reference/uv-cache --from youtube-transcript-api==1.2.4 youtube_transcript_api DvSwvJVens8 --languages ru --format json

stdout сохранён отдельно в `data/reference/yta-ru-recheck.json`, stderr — `yta-ru-recheck.stderr`. Wall `real 2.02 s`, user 0.10, sys 0.04. Это n=1 повторный preflight с уже подготовленным uv environment, НЕ cold backend benchmark и не время LLM. stderr содержит только эти timing строки. Первую попытку и повтор не усредняем: wall первой не измерен надёжно.

Reference:

- raw `data/reference/yta-ru-raw.json`, неизменный CLI outer array для одного видео;
- normalized `data/reference/reference-segments.json`, IDs `r0000`–`r0565`;
- читаемая проекция `data/reference/reference-timed.txt`;
- **566** непустых сегментов, numeric finite nonnegative start/duration;
- начало 0.760 s, максимальный конец 1454.171 s;
- union caption intervals 1422.768 s, **97.6505% длительности**, не доля правильно распознанной речи и не доказательство полного audiovisual покрытия;
- raw SHA-256 `c08f0e724cbe45db65aa1c30f338085b420f55e17d29f309272eb3580c5002ab`;
- normalized SHA-256 `64bb79566e062fa5b46bea6272d78af436835e51c43f2ae390098b448ef6fcd0`.

Raw/private data gitignored через `data/`; `git check-ignore` подтвердил raw и player. Не передавать полную расшифровку как chat attachment. Формальные source bundles A/B/C должны получить собственные hashes/provenance, а не автоматически наследовать успех reference.

## 2. Реальные ошибки и bounded независимая проверка

Direct signed timedtext route ранее вернул HTTP 200 с **zero bytes** (`ru-caption.json3`); это не доказательство отсутствия captions. Смена extractor на captions API получила реальные сегменты, без cookies/proxy. `web_extract` ранее вернул timed английский текст: происхождение перевода недостаточно установлено; `web-extract-translated.md` auxiliary-only, не goldset и не независимая проверка.[1]

Сохранённый файл `youtube-storyboard.jpg` при просмотре оказался **обложкой**, а не storyboard: надписи DGX SPARK / MAC STUDIO / AMD STRIX HALO и «ИИ ГЕРОИ». Это не timestamped evidence. По настоящей player storyboard spec анонимно получены два sheet JPEG (HTTP 200, 71265 / 37363 bytes), по 89×45 pixels/tile, sampling step 10 s. Provenance: `data/reference/storyboard-provenance.json`, retrieval script `data/reference/fetch_storyboards.py`.

Просмотрены bounded опорные tiles из sheets 0/1: около 80/340/420/660/840/950/1160/1290/1340/1420 s. Видны повторяющийся ведущий, устройства, software/screenshots, terminal/графики и поздние сцены с устройствами/интерфейсами. Это только coarse visual plausibility; мелкий текст не даёт надёжного numeric OCR. По лицу имена не устанавливались. Audio listening, audio download и forced alignment **не выполнены**; speech accuracy, 55–60 tokens/s, hardware marketing и каждый таймкод не подтверждены независимо.[1]

Автосубтитры заметно искажают термины: «DJX», «Blackwall», «Rockm»; финальная software оговорка неполная и не называет CUDA явно. Без аудио не утверждаем, какое слово действительно произнесено. Reference — тот же тип YouTube captions, который могут использовать A/B/C, поэтому **common-mode bias** неизбежен. Expected answers проверяют source-grounding/preservation, не правдивость железных характеристик и не независимую ASR accuracy. Сомнительные названия и будущие hardware claims не исправляем молча внешним знанием.[1]

## 3. Предобъявленные варианты и prerequisites

Selection ранее сохранена в `docs/research/selection.md`; generated brief/Q&A не читались.

A. Existing Baoyu skill version **1.1.0**, `/Users/alexbeketov/.hermes/skills/media/baoyu-youtube-transcript`. Docs pin `JimLiu/baoyu-skills@1567581c26ec29f4216c6e6835415bf30343b0e3`. Нужен project-local pinned Bun и проверка upstream scripts/hash; skill availability ≠ runtime success. Raw snippets, без `--speakers`/перевода/AI postprocessing. Sentence timestamps пропорциональны тексту, не forced alignment; source speaker inference не audio diarization.[3]

B. `steipete/summarize` extraction-only timed JSON, docs pin `ddbae2bfceac77d31eb24582523d131cdf0816d6`. Общий downstream, не собственное summary. `--extract` не вызывает summary LLM, но extraction может использовать configured remote providers: вызов должен явно исключать paid ASR/description substitute. Проверить actual installed `--help`, JSON source/segments, stdout отдельно от stderr.[4]

npm требует **Node 24+**; live Node **v22.22.3** не подходит. Официальные standalone macOS arm64/x64 archives требуют macOS13+, не Node. Installation/version/checksum конкретного release принадлежат coder; здесь не установлены и не объявлены рабочими. Не менять глобальный Node.[8]

C. Рекомендованный optional third — **youtube-transcript-api 1.2.4**, не ASR. Подтверждённый captions-only путь, нет необходимости скачивать discretionary whisper model; не независимый audio reference. Package metadata: Python `>=3.8,<3.15`, MIT. README docs pin `8f150ba8836da30a36bcd40e8fca226ed179ba72`; version pin и docs SHA — разные сущности. A/B обязательны как попытки, C только если реализован; четвёртый вариант не добавлять.[5]

Live inventory: uv **0.12.1**, python3 **3.14.5**, Node **22.22.3**, PATH ffmpeg **8.1.1**, orx **0.2.15**. Task/design передали orx0.2.13 и иной FFmpeg path: downstream сохраняет **фактические** executable paths/versions, не переписывает переданные сведения как измерения. На момент проверки `.tools` отсутствовал; параллельный coder может его подготовить. Не устанавливал A/B tools и не читал candidate outputs.

Общий analysis: existing Ollama `http://127.0.0.1:11434`, requested `gemma4:31b-cloud`, temperature0, **cloud-backed, не offline**. Parent readiness smoke returned `gemma4:31b`, OK, elapsed0.632s — переданное наблюдение, не мой видеоанализ. Formal runs фиксируют requested/returned model, settings/prompt/chunking/retrieval hashes и usage; стоимость без pricing/usage — not measured, не zero.

## 4. Content-aware fixed evaluation

`docs/research/evaluation.json`: schema_version1, protocol `DvSwvJVens8-caption-case-v1`, predeclared UTC `2026-10-05T21:43:01Z`. Root `questions` содержит **8** объектов `{id, kind, question, anchors, reference_segment_ranges, expected_points, reject, ...}`. Ranges inclusive в reference namespace. Harness передаёт модели **только вопрос**, не expected answers и не reference/gold windows. Candidate IDs могут отличаться; сопоставление по реальному тексту/интервалам, не номеру ID.

Topic anchors из полного source:

- a01 память/UMA/zero-copy: 206.920–345.800 s, r0078–r0137;
- a02 GPT OSS 120B/MoE: 343.199–384.759 s, r0138–r0151;
- a03 Apple+software caveat: 407.039–558.399 s, r0161–r0226;
- a04 NVIDIA+условность benchmarks/анонсов: 560.720–877.240 s, r0228–r0350;
- a05 AMD/x86/ROCm/Windows: 874.680–1112.720 s, r0351–r0439;
- a06 software-sharded кластеры: 499.639–516.279 и 1113.799–1256.359 s;
- a07 NAS/always-on/available-versus-promised: 1257.080–1338.890 s;
- a08 условные рекомендации: 1340.240–1433.120 s.[1]

Восемь fixed вопросов: главный акцент и компромисс UMA; total/active parameters/memory GPT OSS; Mac software limitation; условность DGX speed и laptop claims; финальный выбор+осторожная attribution; кластеры+API; NAS+что только обещано; точная температура/автономность ASUS RTX Spark как **unknown-answer**. Рекламные блоки r0042–r0077/r0326–r0333 не обязательные technical themes.[1]

q08: прочитаны все 566 captions и выполнен whole-source search `температур/нагрев/автоном/батар/градус/час/ASUS`. Измеренных градусов/часов не найдено; r0334–r0345 прямо оговаривают отсутствие полноценной картины тестов. Правильный ответ отказывается придумывать числа, ограничивает вывод доступной расшифровкой и не выдаёт это за просмотр всего audiovisual источника.[1]

Speaker: textual self-introduction r0030 и sign-off r0562 поддерживают «ведущий, Валерий»; фамилия в captions различается. Exact identity и per-segment map не установлены. Нейтральное «ведущий/говорящий» предпочтительнее; channel≠speaker proof. Не приписывать рекламный/гостевой cutaway текст одному человеку.[1]

## 5. Engineering rubric и метрики

Hard gates: actual timed content вместо description; immutable raw+provenance; finite times и resolvable citation IDs; без unsupported attribution; cached Q&A source hash неизменен, инструментально доказаны extractor/network-adapter calls=0; реальные logs/metrics/config/prompts. Unit fixtures не live result.

Содержательная review: каждый существенный claim и каждый Q&A против source context; labels supported/partial/unsupported/unverifiable, questions pass/partial/fail, anchors present/partial/absent. Считаем реальные labels и denominators. Несколько anchors допустимо объединить в компактную тему; не требовать 8 headings. Нет popularity score и искусственного weighted winner. Useful compact RU brief: gist, themes, practical ideas, author emphasis, material caveats; agent inference отдельно от слов автора.

Измерять setup отдельно; extraction/brief LLM/per-Q&A/total/warm artifact/cached follow-up wall seconds, реальные n и failures. План n=1 на variant, поэтому warm-order/stochastic-provider confounds явно отметить. Wrapper cold store не доказывает cold upstream: `summarize --no-cache` отключает summary cache, **не transcript/extraction/media**. Без доказанного изолированного cache писать possibly extraction-cached, не cold.[7]

Сначала gates, затем grounded usefulness+setup+measured latency; честный tie возможен. Один usable backend с неудавшейся альтернативой — MVP, не успешное content head-to-head. Один видео-кейс не универсальный рейтинг.

## 6. OpenResearch и next-stage blockers

Existing daemon `127.0.0.1:4791` reused; live GET `/api/projects` 200, `{projects:[]}`. Ничего не импортировано; nodes/runs/SQLite/daemon/agents не изменены. Официальная общая документация доступна, но конкретный local contract установлен по live CLI/UI, не по общему описанию compute marketplace.[6]

Installed create/local-run guidance прочитана и сохранена; immutable commit и evidence rules — в отдельных installed docs.[9][10]

Git freezing и полные logs обязательны.[11][12] Minified served import form также прочитан. Точный read-only discovery/handoff — `docs/research/openresearch-contract.md`.

Следующей фазе нужны реальные A/B extraction, общий LLM/QA, working harness и explicit-path commit protocol до immutable runs. `questions_file` repo-root path semantics и ru original-first должны быть согласованы coder; durable tools/source/artifacts не появятся автоматически в git archives. Эти замечания переданы в implementation card. Reference успех не заменяет адаптеры, tests и formal orx evidence.

Доступ ко всему source НЕ заблокирован; capability/credentials/cookies/paid decisions сейчас не нужны. Large ASR model не выбран и не скачивается, поэтому pending policy decision не создаём. Paid/proxy/cookies fallback запрещены; HTTP empty, RequestBlocked/IpBlocked, unavailable/private/age restriction и no-captions различать, не объявлять любую ошибку отсутствием captions.[5]

Политические/бюджетные решения будущего этапа идут в существующий `docs/pending-decisions.md` через владельца этого документа и genuine needs_input, без timeout defaults. В этом run ownership только docs/research и data/reference; no source/config/AGENTS/profile edits, no branch/index/commit operations, no nested agents.

## Sources

[1] https://www.youtube.com/watch?v=DvSwvJVens8
[2] https://www.youtube.com/oembed?url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DDvSwvJVens8&format=json
[3] https://raw.githubusercontent.com/JimLiu/baoyu-skills/1567581c26ec29f4216c6e6835415bf30343b0e3/skills/baoyu-youtube-transcript/SKILL.md
[4] https://raw.githubusercontent.com/steipete/summarize/ddbae2bfceac77d31eb24582523d131cdf0816d6/docs/extract-only.md
[5] https://raw.githubusercontent.com/jdepoix/youtube-transcript-api/8f150ba8836da30a36bcd40e8fca226ed179ba72/README.md
[6] https://openresearch.sh/docs
[7] https://raw.githubusercontent.com/steipete/summarize/ddbae2bfceac77d31eb24582523d131cdf0816d6/docs/cache.md
[8] https://raw.githubusercontent.com/steipete/summarize/ddbae2bfceac77d31eb24582523d131cdf0816d6/docs/install.md
[9] file:///Users/alexbeketov/video-briefing/data/reference/orx-create.txt
[10] file:///Users/alexbeketov/video-briefing/data/reference/orx-compute-local.txt
[11] file:///Users/alexbeketov/video-briefing/data/reference/orx-git.txt
[12] file:///Users/alexbeketov/video-briefing/data/reference/orx-evidence.txt
