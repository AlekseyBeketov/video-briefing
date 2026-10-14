# Сравнение: заранее заданный протокол

## Исследовательский вопрос
Какой из 1–3 реально доступных workflow даёт самый быстрый и проверяемый краткий разбор и ответы по видео DvSwvJVens8 без повторной загрузки? Основной causal comparison: extractor, downstream LLM/prompt/settings одинаковы. Это один кейс, не универсальный рейтинг.

## До запусков
Research фиксирует metadata/access/source language и формирует набор expected topic anchors и 5–8 вопросов из реального первоисточника с evidence windows. Добавить один проверяемый вопрос, на который источник не отвечает (полный поиск), один про оговорку/ограничение, один про мнение конкретного участника если он установлен. Сохранить evaluation specification до чтения variant-generated answers; не подгонять rubric под победителя.
Если reference source — те же captions, это common-mode bias: не объявлять независимый ground truth. Проверить несколько опорных моментов по доступному audio/frames или честно пометить независимую проверку не выполненной.

## Константы
Один точный URL, source language policy, один common LLM model/provider, prompt hash, generation settings, question set, chunking/retrieval policy, timeout policy, environment и fixed OpenResearch run command. backend choice и режим cold/warm задаются committed config. Первое окружение setup/model download не входит в steady-state extraction timing — отдельная метрика.

## Метрики (обязательные)
- Backend actual status / source_type / language / timed segments / duration / coverage limitations.
- Setup time и measured wall seconds extraction, LLM briefing, per-Q&A, total cold, warm artifact reuse; явно указать одну попытку или повторы и реальные n.
- Cache hit: повторный вопрос использует exact same source hash; external extractor/network calls during cached Q&A = 0 (instrument/test, не догадка).
- Grounding: сколько проверенных cited claims/answers реально поддержаны source; invented/unknown segment ids = 0.
- Topic coverage: явно заданные anchors, найденные/пропущенные темы. Не трактовать token density как correctness.
- Attribution/author emphasis: не приписаны ли guest claims host; evidence available vs textual inference.
- Unknown answer: abstains when source does not support claim; не делает общий ответ от себя от имени автора.
- Concision/usefulness: выбранный rubric с независимым source-linked review, субъективность маркируется. No unsupported numerical aggregate winner score.
- Provider model/settings, reported usage if provider supplies it, cloud/local distinction. Missing usage/cost = not measured, not zero.

## Выход каждого запуска
metrics.json, effective-config.json, prompt hashes, source bundle reference/hash, briefing.md, answers.json/md, runtime versions, stdout/stderr diagnostic logs, OpenResearch run/experiment ids and recorded commit. Raw transcript/audio are private gitignored; portable tracked reports refer to those local evidence and contain only bounded examples.

CLI `benchmark --output-dir PATH` treats `PATH` as a run container and creates a unique `run-<UTC timestamp>-<id>` subdirectory for every attempt, including failures. The run directory is private (`0700` on POSIX), result and progress files are private (`0600`), and failed-run diagnostics stay at `progress.json` inside that directory. Repeated runs therefore retain earlier outputs; the CLI prints the actual result paths.

## Выбор
Сначала hard gates: actual content (не description), valid timed evidence, no unsupported attribution, cached Q&A path, passing tests. После этого compare actual latency/setup complexity + grounded usefulness. Equal extraction from same captions may honestly yield no material content advantage; don't manufacture a winner.

## Ограничения
Не объявлять проверку изображения без frames/vision. Недоступный backend отражать как blocked/failed; optional third variant may be omitted with reason. Один successful backend разрешён как рабочий MVP, но как comparison failure — не скрывать вторую неудавшуюся попытку. Недоступность всех content sources — blocker E2E, никаких summaries по названию/description.
