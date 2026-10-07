# Video Briefing — реальные OpenResearch runs и частичный результат

Дата: 2026-10-07. Карточка `t_93e3976e`. Target: https://www.youtube.com/watch?v=DvSwvJVens8.

## Вывод

**COMPLETED_COMPARISON_WITH_GAPS. Победитель не установлен; проект SPEC FAIL.** Реальные local orx runs выполнены: 6 попыток, 2 `done`, 4 `failed`. Original-RU baseline captions_api завершился, но его brief/Q&A не проходят содержательный rubric. Оба запуска sibling C упали в генерации; после двух answerless attempts дальнейшие повторы прекращены, C next-run gate=needs-input. A недоступен с HTTP429. B завершился с timed содержанием, но language=`und`, текст преимущественно английский, есть искажения относительно русского reference. Это **не успешный original-language head-to-head**, не универсальный рейтинг и не готовый проект. Исследовательская карточка принимает accurate completed comparison с отрицательными результатами и освобождает существующую review/hardening цепочку; новые C runs этим не разрешаются.

Предварительная рекомендация только по extraction: `captions_api` сохраняет все 566 исходных RU segments с точным совпадением текста/start/duration reference. Путь пригоден для дальнейшего исправления, а не доказанно лучший стабильный пользовательский workflow. Generation/grounding readiness блокирует принятие проекта и следующие C experiments, но не передачу готовых research findings в независимое review. Исходное видео и существующая модель доступны, credentials не требуются.

## 1. Метод и неизменные условия

Evaluation заранее зафиксирована в `docs/research/evaluation.json`: 8 questions, 8 anchors; SHA256 `7abd485c1549e336497346a7cf571098a7ca18c8662ddf8f81ad781a0c94d1a1`. Expected points/reference ranges не передаются модели. В этой фазе прочитан полный reference из 566 timed segments, затем actual generated brief/answers и их cited source context.

Recipe до запусков закоммичен на main как `c90fc6fe897b521c473199fea4ff32dd9d094154`, `docs/research/run-recipe.md`. Код реализации — `8aeb6970ffe5d69bf7e023db86c4fa60c4440e8a`. Root controls → три co-equal extractor siblings, никаких декоративных потомков. Изменение A/B только `config/experiment.json.variant`, C совпадает с root. Каждый branch имеет собственный worktree под `artifacts/private/orx-worktrees/`; main не переключался. Recorded Git tar snapshots проверены по digest, private data/tools/.venv в них отсутствуют.

Один fixed command/env во всех 6 runs, exact string в `docs/research/openresearch-manifest.json`. `env -i` очищает inherited environment; HOME и uv cache project-private. Python и pinned Bun/summarize доступны через заранее проверенные absolute paths; source/prompts/evaluation читаются из immutable snapshot, а не подменяются main checkout. Default store/output snapshot-relative, после выполнения artifacts/logs скопированы в durable project-private `artifacts/private/comparison-audit/<run-id>/`.

Model: Ollama `http://127.0.0.1:11434`, requested `gemma4:31b-cloud`, observed returned `gemma4:31b`, temperature0, request timeout300s. Это cloud-backed inference, не offline. Runtime: orx0.2.15 (не исторический0.2.13), uv0.12.1, Python3.13.14, Bun1.4.2, summarize0.25.1, youtube-transcript-api1.2.4, Ollama0.35.1.

Brief system SHA256 `0885d3b93a4268a78ce3c4f07946b4d3c62de8ab0d85761c058ac6db18445957`. Actual QA system string SHA256 `e448565b891f3f61d71d5f7163c647bc051c297b13f37edb0095b443d7b09c9a`. Runtime использует `qa.py:SYSTEM`, **не** `prompts/qa.md`; hash этого неиспользуемого файла приведён отдельно. Hashes retrieval/briefing/QA code, lock/config/evaluation — на каждый run в manifest. Dynamic full request prompt hashes и все provider responses implementation не сохраняет; они не выдуманы.

## 2. Наблюдаемое сравнение

| Вариант | Реальный runtime/content статус | Source | Measured extraction / brief / all QA / pipeline, s | Решение |
|---|---|---|---|---|
| A Baoyu | failed, HTTP429 + empty snippets, upstream exit0 не принят за успех | нет valid timed content | stage metrics отсутствуют; orx wall16.026 | Негативный результат доступа; freeze, no retry/cookies/proxy |
| B summarize | done, но original-language invariant нарушен | 560 segments, und, EN-dominant; точный перевод/track lineage не установлен | 2.401379 / 21.545689 / 13.878475 / 37.825542 | Не valid RU comparator; не winner по скорости |
| C captions_api baseline | одна из двух root attempts done; другой root failed | 566 RU auto-captions, exact reference match | 2.385863 / 31.957697 / 13.433841 / 47.777401 | Реальная viability, но содержание имеет material gaps |
| C captions_api sibling | две attempts failed в brief generation | обе extraction сохранили 566 RU segments и тот же hash | stage metrics отсутствуют; orx wall36.049 и22.035 | Answerless cap достигнут, needs-input/repair |

Это single-video case study, последовательность root fail → root done → A → B → C fail → C fail. n=1 для A/B sibling; C sibling n=2 failures; root C n=2 attempts, один полный output. Root результат не переименовывается в успешный sibling. Нет randomized order, confidence intervals или universal score.

Столбец `extract_cold` исходного harness ошибочно так назван: здесь это **fresh wrapper store, upstream cache uncertain**. Shared isolated HOME мог прогреть summarize extraction cache. Не доказан cold upstream и не измерен startup/setup целиком. stdout фиксирует создание venv, build и установку8 packages за3–4ms, но это только install substage. Full orx wall включает orchestration и bootstrap: успешные root52.065s, B42.058s; эти времена не смешиваются с pipeline perf_counter. Длительность неудач — failure wall, не extraction latency.

Cost: **not measured**. Метрики provider usage отражают лишь последний briefing response: root5231 prompt/940 completion tokens, B2872/1616. Это не сумма chunks/synthesis/repair/8 Q&A и не общая стоимость. Нельзя считать пропуски нулём.

## 3. Источник и таймкоды

Reference: RU YouTube auto-captions, duration1457s, first0.760s, max end1454.171s. Все четыре captions_api extractions в formal attempts совпадают с reference по всем566 text/start/duration tuples. Candidate IDs `s00001`…`s00566` соответствуют reference `r0000`…`r0565`; namespaces не смешиваются.

Candidate raw SHA256 `940d5b89a1d24b30f256d352f97d3d6624a5f296a1707780b777dbdb17d1e3af`; reference raw `c08f0e724cbe45db65aa1c30f338085b420f55e17d29f309272eb3580c5002ab`, normalized `64bb79566e062fa5b46bea6272d78af436835e51c43f2ae390098b448ef6fcd0`. Разница hashes объясняется разным serialization/outer format, **не** изменением текста/times. Hash check выполнен до/после.

B raw SHA256 `1e5f0c3b283d41187836a5d1f5f30b61e3423d3ad2acda0226e3223068b0b09d`. Его source contains16092 Latin letters,3 Cyrillic,2 Thai; RU candidate14787 Cyrillic,1491 Latin,2 Thai. Это counts символов, не language confidence/accuracy. Raw B captions в1326.476s дают `Q3 2020`, тогда как original r0521/1326.080s —2026. В840.896s B даёт120GB models, original r0337 —120 млрд. Следовательно, upstream content distortion реален; нельзя приписать всю ошибку downstream LLM или считать B независимым truth.

Timestamp checks: nonempty/unique IDs и finite nonnegative starts/durations проходят у сохранённых B/C bundles. Union intervals: C1422.768s (97.6505% duration), B1417.902s (97.3165%). Это плотность subtitle intervals, не доля правильно распознанной речи, не completeness audio/visual content и не alignment accuracy. Baoyu valid timings не получены; proportional sentence precision не оценивалась. Raw captions не forced alignment.

Reference и extractor C могут использовать тот же YouTube track: **common-mode caption bias**. В этой фазе audio не прослушивалось, new frames не анализировались. Preflight bounded storyboard previews только coarse plausibility; device numbers, лица/diarization и hardware truth независимо не подтверждены.

## 4. Grounding, coverage и полезность

ID validation не равно смысловой поддержке. Все49 reference occurrences в root brief и38 в его QA разрешаются; B58 brief и35 QA occurrences также существуют. Unknown IDs в этих completed outputs —0. Рендер даёт таймкоды реальных segments. Существующий gist validator не полностью охватывает gist_evidence — это gap, успешные outputs отдельно проверены researcher.

Human rubric: gist block=1 review unit, каждая bullet=1 unit, а не число атомарных factual propositions. QA counts относятся к structured `claims[]`; свободный answer prose и omissions оценены отдельно question labels. Labels считаются программно, без искусственного quality score.

| Оценка | C completed root | B noncomparable completed |
|---|---:|---:|
| Brief supported / partial / unsupported | 6 / 5 / 1 из12 units | 11 / 6 / 0 из17 |
| Structured QA claims supported / partial / unsupported vs original | 15 / 2 / 0 из17 | 8 / 3 / 1 из12 |
| Questions pass / partial / fail | 2 / 4 / 2 из8 | 2 / 1 / 5 из8 |
| Anchors present / partial / absent | 0 / 5 / 3 из8 | 1 / 6 / 1 из8 |

Полная разметка каждого unit/question/anchor с rationale — `reports/comparison.json:reviews`. C brief полезен как компактная навигация по UMA/zero-copy/vendors, но пропускает MoE example, NAS и conditional final recommendation. B brief содержит больше categories, но это другая caption representation, нет основания ранжировать качество extractors причинно.

Основные наблюдения по fixed questions:

- q01 partial у обоих: компромисс памяти неполный; q02 root пропускает active5.1B, потому что actual retrieval не включает s00142/r0141. B q02 проходит числовой пример, но это не преимущество оригинального extractor: его границы snippets другие.
- q03 C generic software caveat неполный; B ошибочно заменяет software compatibility ограничением peak memory speed. Структурно валидные отдельные claims не оправдывают причинный answer prose.
- q04 fail у обоих: actual windows теряют small/medium context, slowing with context и laptop no-test caveats. В **полном** B и RU источнике они есть. Нельзя выдавать отсутствие в windows за отсутствие в видео.
- q05 fail: оба false-abstain при доступной финальной conditional recommendation1340–1425s. q06 C partial, B fail: поздний OpenAI-compatible API1230–1244s не попадает в нужный context.
- q07 C pass: различает NAS24x7 и available-versus-promised, сохраняет2026. B English answer пропускает rationale и повторяет upstream2020. Его date claim поддержан candidate, но **unsupported относительно original**, это явно разделено в JSON.
- q08 оба abstain без придуманных градусов/часов. Отрицательный вывод model ограничен supplied excerpts; researcher независимо проверил full566-caption source и explicit test caveat832.839–863.639s. Не утверждается отсутствие всех возможных visual values.

Attribution: root brief пишет полное имя «Валерий Истишев» из auto-caption self-introduction, хотя exact surname и per-segment map не установлены. Это overclaim policy, не доказательство выдуманного гостя. B neutral presenter attribution безопаснее; ни один результат не подтверждает diarization. C caveat превращает ошибки написания product names и partial outline в отсутствие содержания, в частности Mini Scloud/archive context, присутствующий1287–1335s.

Bounded useful example: «NAS работает дома24/7, подключён к сети и хранит данные» — root q07, candidate s00513–s00515/1304.880–1314.080s, original r0512–r0514. «Поиск по всем типам файлов обещают добавить…2026» — s00521–s00522/1323.440–1330.440s, r0520–r0521. Это пересказ утверждений ролика, не проверка текущего vendor release.

## 5. Отдельная instrumented cached Q&A verification

Без новой extraction, на копии actual root bundle. Monkeypatch fail-on-extractor всех adapters/CLI; блокируются requests network и urllib/socket destinations кроме existing Ollama `/api/chat`. Выполнены существующие lookup + real q07/q08; не заменяет experiment и не улучшает formal benchmark задним числом.

- source hash before=after `940d5b89…d1e3af`;
- actual extractor calls0, non-LLM network attempts0, Ollama requests2;
- warm artifact read0.002781333s;
- q07 real cached answer2.179709459s, q08 abstention0.964862833s;
- оба returned `gemma4:31b`; собственные actual usage metadata сохранены.

Evidence: `artifacts/private/comparison-audit/cached-verification/result.json`, probe `data/reference/verify_cached_existing.py`. Число0 в formal harness было literal, не instrumentation; только эта проверка и unit guard подтверждают concrete reuse path.

## 6. IDs, failures и стоп

Project `9ddfb26b-139f-400e-8acf-6760aecc3c14`, dashboard http://127.0.0.1:4791. Supported `POST /api/projects` folder import с explicit githubSyncEnabled=false; exact GET returned ID/path verified. Origin pre-existed и **не** удалён/пушен. Поздний coordinator comment1791361841 на t_57ebfc61 фиксирует одобренный пользователем private repo: это изменение исторического no-remote условия, а не новый blocker; новые push/publication не разрешены. Старый daemon отсутствовал; восстановлен только loopback `--no-agent --no-browser --no-telemetry`, новых agent processes нет.

| Node | Experiment ID | Run ID | Recorded commit/result |
|---|---|---|---|
| root | 88a9843c-4f89-481a-ad37-e425e63ded33 | 6177d70e-8aea-44e0-87bf-0ee25001779f | c90fc6f, Q&A claim without evidence |
| root | тот же | 5809a015-d997-4e87-a83c-47161c4fc8ce | c90fc6f, done |
| A | 843d23fc-586c-48cc-9f76-57c17b12e809 | 33687786-f205-4bdf-8a12-7df3ff34244d | 2605513, HTTP429/empty |
| B | 3c86189a-b281-4b25-ad7b-8386f1c5cc48 | 2ee2889d-0806-4726-9e34-bd7f78775142 | 71ffd10, done/noncomparable |
| C | 5abe83c1-deed-4c57-a604-6e7b6aa4b6e9 | e5aec712-5911-47d4-94ca-dea601e84221 | c90fc6f, brief claim missing evidence |
| C | тот же | 8bf1516a-6b39-4bec-a61f-037b2dd44781 | c90fc6f, malformed Ollama JSON at93:5 |

Full logs реально прочитаны. Абсолютные original/exported log/artifact paths, UTC dates, branch/full commit hashes, source tar digest и effective configs — manifest. Failed generation не сохраняет intermediate brief/answers: missing metrics не являются zero metrics и не заменены fixtures. Root/A/B answered branches заморожены; C provisional оставлен без дальнейших правок/reruns по cap.

## 7. Следующий шаг и артефакты

Не запускать больше C experiments до readiness repair/explicit go-ahead: schema+validation согласовать, безопасно обработать malformed/missing-evidence response без ослабления grounding, сохранять progress/question-id/full bounded provider diagnostics; исправить retrieval и source-language enforcement. Конкретные дефекты переданы durable comments implementation card и перечислены в `reports/spec-review.md`. Исследовательская фаза завершается с accurate negative/partial results; pre-created независимое review t_9c90bf74 → hardening t_b57e77ae выполняют следующую фазу, не duplicated same-card review. Любой новый scientific branch сохраняет immutable answered history и fixed contract; pipeline repairs не маскируют прошлые failures.

`reports/observed-baseline-briefing.md` — byte-identical **actual generated** baseline artifact, SHA256 `5ba1b78bf1af9bb0a801df9054d22f1f442200341fcac15a5ecf089c353391f2`. Он **не approved final brief**, содержит описанные недостатки. Не улучшен вручную и не является fabricated substitute. Raw copyrighted transcript/audio не прикладываются.

Sources: target YouTube и private reference, predefined evaluation/preflight; official installed `orx skill orx-create/orx-experiment-tree/orx-compute/orx-git/orx-evidence/compute/local`; live dashboard POST schema и точный GET readback; actual local logs/metrics/source bundles. Upstream pinned documentation/provenance links — `docs/research/preflight.md:103–116` и `docs/research/sources-ledger.json`. Ни remote publication, ни paid compute, ни model download, cookies/proxy/auth/config/AGENTS/skill writes в этой фазе не выполнялись.
