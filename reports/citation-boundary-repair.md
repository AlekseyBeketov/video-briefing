# Citation boundary и восстановление smoke evidence — t_4eec35ee

Дата проверок: 7 октября 2026 года. Закрыты только два конкретных замечания repair-карточки; это не финальная приёмка проекта.

## Revision для rereview

- Base HEAD: `4de6fe19a19d55e756ea89cce161aa1a2aa037a6`.
- Новый commit не создавался: карточка прямо запрещает изменять commits. Исправление находится в рабочем дереве; base HEAD не содержит этот patch.
- Code revision SHA-256: `82f44e76f49c1a78e20442555dd643b8711e948443b24192018fbe51124208e3`. Это SHA-256 canonical JSON с file hashes `src/video_briefing/qa.py`, `prompts/qa.md`, `tests/test_qa_citation_boundaries.py` (sort_keys=true, separators=comma/colon); точные hashes приведены в companion JSON.
- Для проверки читать рабочее дерево, а не только `git show HEAD`. Skill/wrapper не изменён; установленный default wrapper побайтно сверён с wrapper в checkout.

## Исправление и deterministic regression

- Q&A prompt требует ссылаться на полное имя/фразу, включая все caption segments на границе.
- После прежней проверки unknown IDs / обязательных citations / retrieval-context membership resolver дополняет только exact token phrases, пересекающие уже cited segment. Игнорируются только перечисленные caption audio-event markers; source text не переписывается.
- Добавляются только сегменты самой найденной фразы в уже переданных модели непрерывных retrieval windows. Не добавляются безусловные соседние сегменты; не соединяются окна через пропуски; исходные model citations сохраняются.
- Фиксированная fixture содержит маленький excerpt `s00496`–`s00501` из реального source с hash `940d5b89a1d24b30f256d352f97d3d6624a5f296a1707780b777dbdb17d1e3af`. Все шесть texts/times и metadata дополнительно сопоставлены с полным локальным bundle. Полный transcript не включён в тесты и остаётся ignored.
- С неизменным fake model response (имя Mini Sform N5 Max, citations только `s00498`–`s00500`) исполнение исходного `HEAD:src/video_briefing/qa.py` в памяти даёт неполный range; новое исполнение даёт ровно `s00497`–`s00500`. Аналогичный неполный response проверен на полном живом cached source, а не только fixture.
- Regression tests также проверяют idempotence, forward/backward и three-caption phrases, отсутствие padding/соединения retrieval gaps, repeated phrases, отклонение unknown/пустых/out-of-context citations.

## Реальный cached smoke

Запуск runner: `uv run --frozen python artifacts/private/run_citation_repair_smoke.py` (exit 0). Runner/guards/logs и source-bound stdout хранятся локально в ignored `artifacts/private/`; они не являются public deliverables. Runner сохраняет только реально полученный, успешно разобранный и проверенный stdout, а не синтезирует ответы.

Все runs: video `DvSwvJVens8`, variant `captions_api`, language `ru`, 566 segments, raw SHA-256 `940d5b89a1d24b30f256d352f97d3d6624a5f296a1707780b777dbdb17d1e3af`. Raw file hash пересчитан; bundle загружен через проверяющий hashes ArtifactStore. Source raw/bundle hashes не изменились до/после каждого run.

Для каждого command ниже: `UV_OFFLINE=1`; `PYTHONPATH=/Users/alexbeketov/video-briefing/artifacts/private/citation-repair-guard:/Users/alexbeketov/video-briefing/src`; `CITATION_SMOKE_AUDIT_LOG` указывает на соответствующий лог ниже. Эти переменные были переданы только child processes; global config не изменён.

### nas-installed

UTC start: 2026-10-07T11:07:51.253815+00:00

```sh
python3 /Users/alexbeketov/.hermes/skills/custom/video-briefing/scripts/video_briefing.py ask 'https://www.youtube.com/watch?v=DvSwvJVens8' --question 'Что автор говорит о NAS и какие функции Mini Scloud уже доступны или обещаны?' --variant captions_api --language ru
```

Exit 0; stderr пустой; cached Q&A elapsed 2.197662s; claims 3; abstained=false.
Actual stdout: `artifacts/private/production-nas-citation-repair.json`; 3882 bytes; file SHA-256 `b62edbaedc453a7e30f50349355ffe51b44d55fb7a005ac98fd240a85d8f4a75`.
Evidence IDs по claims: `[["s00497", "s00498", "s00499", "s00500"], ["s00517", "s00518", "s00519", "s00520"], ["s00520", "s00521", "s00522", "s00523"]]`.
Private audit log: `artifacts/private/nas-installed-citation-repair-audit.jsonl`; SHA-256 `be2ee07330d881ca450f63c35df608af2c949fca6d0122d54159c32171fdcd28`.

### nas-checkout

UTC start: 2026-10-07T11:07:53.572760+00:00

```sh
python3 /Users/alexbeketov/video-briefing/skills/video-briefing/scripts/video_briefing.py ask 'https://www.youtube.com/watch?v=DvSwvJVens8' --question 'Что автор говорит о NAS и какие функции Mini Scloud уже доступны или обещаны?' --variant captions_api --language ru
```

Exit 0; stderr пустой; cached Q&A elapsed 1.912958s; claims 3; abstained=false.
Actual stdout: `artifacts/private/production-nas-checkout-citation-repair.json`; 3845 bytes; file SHA-256 `6853901dedbecd9f0c99f53109b4e9e396c9512e23aa82c68d27102678ddefba`.
Evidence IDs по claims: `[["s00497", "s00498", "s00499", "s00500"], ["s00517", "s00518", "s00519", "s00520"], ["s00520", "s00521", "s00522", "s00523"]]`.
Private audit log: `artifacts/private/nas-checkout-citation-repair-audit.jsonl`; SHA-256 `000d74d5a18663e99bbf7b72dba53fb37605c0c007576498e187b2b35798b398`.

### q01

UTC start: 2026-10-07T11:07:55.617236+00:00

```sh
python3 /Users/alexbeketov/.hermes/skills/custom/video-briefing/scripts/video_briefing.py ask 'https://www.youtube.com/watch?v=DvSwvJVens8' --question 'На чём автор делает главный акцент при объяснении нового AI PC: на мощности NPU или на памяти? Какой компромисс он описывает у объединённой памяти?' --variant captions_api --language ru
```

Exit 0; stderr пустой; cached Q&A elapsed 2.240466s; claims 3; abstained=false.
Actual stdout: `artifacts/private/production-q01.json`; 3803 bytes; file SHA-256 `163c2d758eb04c111018e75034b3157651de126fa0c83080847c705c444c5fc1`.
Evidence IDs по claims: `[["s00151", "s00152", "s00153", "s00154"], ["s00126", "s00127", "s00128", "s00129"], ["s00126", "s00127", "s00128"]]`.
Private audit log: `artifacts/private/q01-citation-repair-audit.jsonl`; SHA-256 `6588be60572f750fbfb489c2ba1b0e28872c7d7793c4329feca0cd12417ebf3b`.

### q08

UTC start: 2026-10-07T11:07:57.989573+00:00

```sh
python3 /Users/alexbeketov/.hermes/skills/custom/video-briefing/scripts/video_briefing.py ask 'https://www.youtube.com/watch?v=DvSwvJVens8' --question 'Назови точную измеренную температуру под нагрузкой и время автономной работы в часах ноутбука ASUS на RTX Spark, приведённые в этом видео.' --variant captions_api --language ru
```

Exit 0; stderr пустой; cached Q&A elapsed 0.785581s; claims 0; abstained=true.
Actual stdout: `artifacts/private/production-q08.json`; 1293 bytes; file SHA-256 `1b4e46e4c4c7d1ccad4f39ac5cb170812baf4933e4a698d69a33ed0609767b09`.
Evidence IDs по claims: `[]`.
Private audit log: `artifacts/private/q08-citation-repair-audit.jsonl`; SHA-256 `0f51df466811f36aaabeb40f8bfaf50283629925e09b34aad99ee85a395200b7`.

## Честное исправление smoke record

- До repair `production-q01.json` и `production-q08.json` имели 0 bytes. Они не подтверждали прежние заявленные сохранённые outputs; старые timings 2.35s / 0.97s не переносятся на новые artifacts.
- Теперь оба файла содержат реальный stdout новых cached invocations, с проверенным source identity/hash. Q01 даёт три cited claims про память; Q08 честно abstains и не содержит factual claims.
- `reports/production-acceptance.md` явно различает эти новые reruns и несохранённые original Q&A outputs. Старый brief не перезапускался; прежние OpenResearch metrics/history не редактировались.

## Что означает отсутствие extraction/network

- Guards загружены в оба Python процесса каждого запуска: wrapper и project CLI.
- Любой вызов `_run_extractor`, import adapters/captions client, Python network destination вне `127.0.0.1:11434`, либо subprocess вне uv запрещён. Audit logs: по одному разрешённому Ollama connection на run, zero guard denials; источник неизменён. uv запущен offline.
- Эти проверки подтверждают отсутствие transcript extraction/network доступа из wrapper/CLI. Это НЕ network-free inference: `gemma4:31b-cloud` возвращён endpoint как `gemma4:31b`, cloud-backed=true. Сетевой egress Ollama daemon не отслеживается Python audit hooks.
- `extract`, `brief`, OpenResearch runs не запускались. Новые модели/credentials/paid fallback не использовались.

## Verification

- `uv run --frozen pytest`: exit 0; 45 passed in 0.06s.
- `uv run --frozen python -m compileall -q src tests`: exit 0; без output, успешно.
- `git diff --check`: exit 0; без output, успешно.

## Ограничения и handoff

Это lexical citation-boundary repair, не универсальная semantic entailment validation, не гарантия качества всей retrieval-системы и не внешняя проверка написания названия/характеристик из captions. Resolver не получает дополнительный context вне supplied excerpts; paraphrases остаются предметом independent review.

Git commits/remotes/history, skill copies, credentials и global config не изменены. Существующий untracked `.codegraph/` не затрагивался. Public deliverables — этот отчёт, companion JSON и уточнённый production smoke report; private transcript/JSON/logs остаются ignored и не прикладываются.

Implementation-фаза передаётся в существующую dependent rereview-карточку `t_1d07e629`. Whole-project acceptance остаётся pending.
