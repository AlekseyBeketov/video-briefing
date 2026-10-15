# Независимый final technical review — текущая ревизия

Дата: 2026-10-07. Reviewer: coder, независимый audit `t_1d07e629`. Это промежуточная ревизия до corrective repair `t_081ae46a`; после неё отчёт должен быть обновлён повторной проверкой. Проект не принят.

## Вердикт

- SPEC: FAIL — текущий живой краткий brief не сохраняет важные предзаданные source anchors; retrieval не покрывает необходимые поздние/контекстные места для нескольких fixed questions.
- QUALITY: REQUEST_CHANGES — confirmed regression/functional gap остаётся в полноисточниковом retrieval и итоговом brief, несмотря на предыдущие repairs.
- PROJECT READY: NO.

## Исполненные проверки

Репозиторий: `/Users/alexbeketov/video-briefing`; branch `main`; HEAD `4de6fe19a19d55e756ea89cce161aa1a2aa037a6`; production hardening commit `f4012de75d92acb2457f398721cea6eedb9dee38`. Ремонт `t_4eec35ee` незакоммичен и находится в working tree (это было запрещено коммитить); audit читал именно working tree. До/после проверок сохранены uncommitted изменения; `.codegraph/` оставлен нетронутым.

- `uv run --frozen pytest` → exit 0, 45 passed.
- `uv run --frozen python -m compileall -q src tests` → exit 0.
- `git diff --check` → exit 0.
- `uv run --frozen video-briefing --help`, `ask --help` → exit 0; доступны doctor/extract/brief/ask/benchmark.
- `uv run --frozen video-briefing doctor` → exit 0; Python 3.13.14, Ollama reachable, youtube-transcript-api 1.2.4, Bun 1.4.2, summarize 0.25.1; configured Baoyu source exists.
- Настоящий cached CLI ask для фиксированного NAS/Mini Scloud вопроса → exit 0, 3 claims; Q08 exact temperature/battery вопрос → exit 0 и честный abstention без claims. Оба источника: DvSwvJVens8 / ru / captions_api / 566 сегментов / SHA-256 `940d5b89a1d24b30f256d352f97d3d6624a5f296a1707780b777dbdb17d1e3af`. Requested model `gemma4:31b-cloud`, returned `gemma4:31b`, cloud-backed; это не offline inference.
- Installed default skill wrapper выполнил новый реальный `brief` из существующего bundle; 5 provider calls, отчётливо отмечена cloud-backed модель, тот же source hash. Raw transcript не включён и не прикладывается.
- `orx runs 9ddfb26b-139f-400e-8acf-6760aecc3c14` → 6 реальных runs: 2 done, 4 failed. Все 6 exact run IDs, статусы, commits и log SHA-256 сверены с `docs/research/openresearch-manifest.json`; все 6 original log files существуют и их hashes совпадают с manifest. Подробности — `reports/comparison.md` и `docs/research/openresearch-manifest.json`. Никаких новых orx runs не запускал. Установленный сейчас orx CLI `0.2.17`; manifest фиксирует исторический runtime `0.2.15` на момент runs.
- `git ls-files data artifacts` → пусто; private bundle/source paths подтверждены `git check-ignore`. `git remote -v` показывает существующий `origin` fetch/push на private GitHub repo. Remote не добавлялся/не изменялся, push/fetch не выполнялись. Предыдущий handoff документирует одобрение владельца private repo; поэтому не удалял remote. Это не новый запрос на разрешение, но фактическое состояние не является «remote отсутствует».

## SPEC: подтверждённый content/retrieval gap

Заранее замороженный протокол и source-linked expected ranges: `docs/research/evaluation.json`, SHA-256 `7abd485c1549e336497346a7cf571098a7ca18c8662ddf8f81ad781a0c94d1a1`. На текущей ревизии retrieval тестирован по всему фактическому 566-сегментному cached source. Числа ниже — доля сегментов нужных reference ranges, попавших в retrieved context, не качество ответа:

- q04 DGX conditional benchmark range r0277–r0289: 0/13; laptop no-test/caveat r0334–r0345: 0/12.
- q05 final conditional recommendation r0526–r0563: 6/38; ранняя speaker intro and vendor ranges не включены.
- q06 OpenAI-compatible API r0460–r0463: 0/4; late API range r0475–r0487: 5/13.
- q03 limitation range r0199–r0201: 0/3.

Сгенерированный на текущем code revision brief содержит темы UMA/zero-copy, памяти, vendor ecosystem, clusters и ОС, однако пропускает существенные заранее заявленные части: MoE 117B/5.1B/80GB; ограничения цифры 55–60 tok/s и отсутствие ноутбучных тестов; условную итоговую рекомендацию; API в кластере; точное разделение уже доступных NAS-функций и обещанного поиска по всем типам файлов. Это не «не было в источнике»: fixed evaluation указывает соответствующие диапазоны в полном cached transcript.

Примеры source-link spot-check (время из исходных captions; близкие сегменты сверены с raw cached bundle, hash выше):

- q01 trade-off: s00126–s00129, примерно 315–326с: единая память уступает GDDR7 по пиковой скорости, зато в неё помещается модель целиком.
- q07 NAS: s00513–s00516, примерно 1305–1316с: NAS дома 24x7, подключён к сети и хранит данные для AI; s00518–s00523, примерно 1316–1332с: ассистент, image/video search, Docker/VM названы доступными, full-file-type search обещан на конец Q3 2026.
- q07/NAS entity boundary: s00497–s00500, примерно 1261–1276с: caption разносит имя устройства по границе сегментов; исправленный Q&A включает `s00497` перед continuation `s00498`, плюс соседние уточняющие segments.

Фактический live brief — короткий русский текст, но наличие валидных IDs само по себе не подтверждает семантическую поддержку. Retrieval попадания по fixed ranges указывают на остающийся риск неполных/ложно-отрицательных ответов. Отрицательный Q08 вывод ограничен captions, не всем аудио/видео.

## Качество repairs, skill и provenance

- Текущий `qa.py` содержит source-bounded exact phrase citation completion; это исправляет конкретную границу названия, не является semantic entailment validator. NAS cached Q&A и source segments подтверждают границу; Q08 abstains. Тесты 45/45 проходят.
- `ArtifactStore.save` сверяет уже сохранённый source hash и отказывает при изменении; test suite включает conflict/write-once behavior. Runtime cache lookup выполняется без extractor: `ask` вызывает `_get_bundle(..., extract_if_missing=False)`, и `tests/test_cached_qna.py` monkeypatch-ит `_run_extractor` на fail. Реальные cached ask вернули unchanged source hash.
- `skills/video-briefing`, `/Users/alexbeketov/skills/custom/video-briefing` и `/Users/alexbeketov/.hermes/skills/custom/video-briefing` — обычные каталоги без symlink; файлы `SKILL.md`, `references/limitations.md`, `scripts/video_briefing.py` имеют идентичные tree file SHA-256: `c47190f50c52d29db89a7d84f877462273e083e766936db1781051f6a67cc7dd`, `58c40f2db053ddbc91e0926696ad0e6ecc9d56007e4325b4689879150de80b95`, `c1a92d5724df765d2cd873abaae0b45da83130737b89e5d39556fa8777eb92c0`. Registry `/Users/alexbeketov/skills/system/registry/skill-catalog.yaml` фиксирует revision `4de6fe1`, matching file/tree hashes и `hermes_profiles: [default]`; `hermes -p default skills list` показывает `video-briefing` enabled. Другие профили не проверялись и не менялись.
- Исходные OpenResearch comparison runs заморожены, metrics старого commit не перенесены на текущий code. Два старых завершённых run — это не подтверждение новой brief quality.

## Блокирующий corrective handoff

Создан coder repair `t_081ae46a` по неполноте retrieval coverage и brief anchors, без зависимости от текущей audit-карточки; он добавлен как parent к этому review. После завершения будет повторно проверена фактическая новая ревизия, полный test/CLI/cached source path и evidence coverage; этот отчёт и companion JSON обновятся. До rereview окончательный вердикт остаётся SPEC FAIL / QUALITY REQUEST_CHANGES. Публичных/raw transcript artifacts нет.