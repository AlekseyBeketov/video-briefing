# Независимая от implementer SPEC review

Дата: 2026-10-07. Проверяющий: research `t_93e3976e`, не автор реализации. Проверка выполнена после реальных comparison runs, без coding edits и nested reviewers. Это отдельный spec-verdict, не будущий fresh code-quality review `t_9c90bf74`.

**SPEC: FAIL / REQUEST_CHANGES. PROJECT READY: NO.** Formal tracked evidence существует, но benchmark readiness нестабилен: C sibling дважды не дал результата, достигнут stop cap. Эта карточка остаётся blocked/needs_input до решения о repair. Не приравнивать сохранённый partial comparison к принятию всего проекта.

## Проверенные команды и первичные артефакты

В `/Users/alexbeketov/video-briefing`:

- `uv run --frozen pytest` → **28 passed**,0.04s при первой независимой проверке. Это unit/fixture coverage, не доказательство live output quality.
- `uv run --frozen python -m compileall -q src tests` → exit0.
- `uv run --frozen video-briefing doctor` → exit0; Python3.13.14, configured cloud model/loopback endpoint reachable, paths tools present.
- `git diff --check` → exit0.
- `orx --version` →0.2.15; compute default local; custom instructions blank; telemetry off.
- Supported HTTP import/readback: project ID `9ddfb26b-139f-400e-8acf-6760aecc3c14`, exact repoPath, githubSyncEnabled=false, githubPublicationError=null.
- `orx exp run <id> --backend local`, followed by `orx exp wait`, `orx runs`, `orx logs`;6 persisted immutable attempts,2 done/4 failed. Full logs и completed metrics/brief/answers прочитаны, hashes checked.
- Instrumented real cached lookup/q07/q08: source hash unchanged; extractor calls0, non-LLM network attempts0, real Ollama calls2; q08 abstained.
- `git remote -v` → pre-existing origin `https://github.com/AlekseyBeketov/video-briefing.git`. Requirement no remote НЕ выполнен; remote untouched, no push/fetch.

Detailed IDs/absolute paths/UTC timestamps/hash checks — `docs/research/openresearch-manifest.json`; human interpretation — `reports/comparison.md`, machine audit/labels — `reports/comparison.json`.

## Requirements matrix

| Requirement | Verdict | Evidence |
|---|---|---|
| Exact supplied target and validated ID | PASS | benchmark.py:14–32, all saved bundles/metrics DvSwvJVens8 |
| 1–3 practical extractor variants, actual attempts | PASS availability assessment, NOT head-to-head success | Three sibling nodesA/B/C plus common baseline. A HTTP429, B und/EN, C originalRU but failed generation repeat |
| No title/description fabricated summary | PASS for observed runs | A fails empty raw; B/C actual timed contents, finite timestamps, no description-only substitute |
| Original language + same downstream | PARTIAL/FAIL | requested ru/config/model/temp same; summarize.py:91 lacks ru track selection, parser:67 marks und without refusing, B source predominantlyEN |
| Immutable provenance and stable cache identity | PARTIAL | C raw text/times exactly match fixed reference, hashes preserved; bundle metadata C lacks title/channel/duration/coverage, raw_text is serialized fetched snippets, not full untouched HTTP response. B original stdout is not saved unchanged |
| Full source brief → compact Russian output with material caveats | FAIL | Baseline real brief exists, but MoE/NAS/final conditions missing, caveat invents absence; missing/inaccurate evidence and response errors in C sibling |
| Full-source grounded follow-up | FAIL | Retrieval scans full stored bundle, but 12 sparse hits+radius1 lose critical neighbouring/late clauses; false abstentions q05/q06, missed q02/q04, B q03 wrong causal answer |
| Honest unknown answers | PASS observed q08, PARTIAL general policy | q08 safely abstains; evaluator full566-source search confirms no values. Runtime only supplied windows, no special exhaustive negative-answer verification |
| Attribution/inference separated | FAIL | root gist full surname unsupported certainty; brief rendering drops useful_ideas.kind; no verified speaker map. Some hardware advice lacks explicit source-vs-agent distinction |
| Cached follow-up no re-extraction | PASS for independently exercised path | Real guarded q07/q08 source hash stable;0 video-adapter network/extractor calls. Harness literal0 not proof on its own |
| Fixed command/env + committed snapshots + actual orx | PASS with measurement caveats | project command stable, env-i same, variant-onlyA/B config diffs, verified snapshot digest/config/retrieval/prompt hashes; baseline/root and <=3 siblings |
| Metrics effective-config/hashes/model/usage/setup/cold-warm | PARTIAL/FAIL harness, research supplement supplied | exported source-grounded manifest adequate for these runs; code omits dynamic prompt/per-response metadata, partial failures, stage setup; misleading extract_cold label; usage last brief response only |
| Declared CLI commands/help/JSON/local transcript | FAIL required surface | cli.py:21–63 only YouTube URLs and extract/brief/ask/benchmark/doctor; no timed-transcript input mode, no --json switch for all public commands, brief renders plain text |
| Reproducible project-local setup/locks | PARTIAL | Python dependencies pinned uv.lock; summarize archive verified, Bun version checked. External existing Baoyu path hardcoded, runtime source pin/hash not enforced; fixed recipe explicitly supplies external tools/Python |
| Local Git no remote/publication | FAIL no-remote; PASS no new publication here | Pre-existing origin found at orientation. API import disables sync, no remote/global/auth changes in this phase |
| Privacy/raw media ignored | PASS for current outputs | .gitignore data/,artifacts/private/,media,.env/cookies; recorded snapshots exclude private source/tools/venv; tracked report only bounded generated brief/analysis, no full transcript/audio |
| Skill canonical+default/full-copy loader audit | PENDING downstream, NOT PASS | design.md:40–41, plan tasks14–15; intentionally not deployed in this research phase |
| Fresh code review/hardening/final audit | PENDING gated | child t_9c90bf74 not released while this card blocked; do not claim approval |

## Точные дефекты и acceptance для implementer

### G01 HIGH — generation contract не обеспечивает устойчивый benchmark

Evidence: root run `6177d70e…` log:6 — `Every non-abstaining Q&A claim must cite evidence`; C run `e5aec712…` log:6 — `Every briefing claim, including gist, needs evidence segment ids`; C run `8bf1516a…` log:6 — malformed provider JSON, parse93:5. Root retry `5809a015…` succeeds, поэтому reachable provider и usable source не равны стабильному контракту.

Files: `qa.py:13,35–39` schema допускает empty evidence у claims, validator запрещает; `briefing.py:76–115` handling repairs only unknown IDs, не missing evidence; `llm.py:45–67` не гарантирует provider JSON compliance; `benchmark.py:69–94`, `cli.py:155–156` сохраняют результат только после всей цепочки.

Fix: bounded response/schema handling с сохранением валидного source grounding, fail-closed diagnostics/progress и question/part identity; не выдумывать evidence и не ослаблять validation. Сохранять valid intermediate brief/answers и ошибку до отказа последующего этапа. Лимит новых formal runs не обходить; решение о repair требуется после stop cap.

Acceptance: regression tests для empty/missing evidence, malformed/fenced/partial JSON и late-question error; persisted effective config/source/model/phase/question-id + partial outputs; real repaired fixed-command orx child/run только после согласования, без изменения answered branches.

### G02 HIGH — retrieval теряет исходный смысл и критические ограничения

Files: `retrieval.py:47–78`, `qa.py:20–25`, `briefing.py:54–80`. Correct source scanned but fragmented12 matches permit semantic misses. Actual root q02 excludes s00142=5.1B; q04 lacks r0270–r0273/0334–0345; q06 lacks API r0483–r0487; q05 fails final recs r0526–r0560. B Russian question versus EN source worsens ranking. All data exist in full source; это не missing-video blocker.

Fix: coherent passage windows, query-language/source-language policy and recall for numeric/comparison/limitations/late answers; distinguish retrieved miss from whole-source absence. Rubric нельзя менять под новые ответы.

Acceptance: source-derived regression cases для8 fixed questions с expected evidence recall, then real source-grounded answers сохраняют5.1B, context caveat, conditional final choice, API andNAS distinction; wrong/overbroad abstention fails tests. Gold answers не попадают в prompt.

### G03 HIGH — summarize не контролирует original-language source/track provenance

Files: `summarize.py:67–78,83–99`, `benchmark.py:52–65`; requested language записан в metadata, но не передаётся extractor и не проверяется.

Evidence B: und,560 EN-dominant segments; timed date1326.476s=2020 vs original1326.080s=2026; announced model120GB vs120 млрд. Config summary_language ru не заставляет QA: B q06/q07 English.

Fix: select/verify actual original track or fail as noncomparable before analysis; preserve original stdout+track/version provenance. Enforce explicit Russian output and avoid unsupported translated-source claims. Fallback language must be labelled, not silently counted as same-source comparison.

Acceptance: fixture/live language mismatch rejection, provenance und handling, same fixed model contract; original-language output or honest backend noncomparability, no paid-ASR/auth/cookie fallback.

### G04 HIGH — citation existence/attribution ≠ support

Files: `validation.py:54–68` scans evidence/segment_ids but not gist_evidence; `briefing.py:108–127` derives missing gist citations from topics without verifying gist meaning; `render_brief:155–161` drops source|inference kind; `qa.py:45–46` can label factual answer with empty claims abstained without checking answer prose.

Evidence root full surname in gist without verified identity/map; false absence caveat; mislinked Mac s00545 to mini-PC cluster; B q03 unsupported software causation and q04 context→text drift despite valid IDs. All49/58 brief citation occurrences existing does not close this requirement.

Fix: deterministic validation of all citation fields, cite each factual caveat, preserve inference/source labels in render, conservative unnamed speaker policy; quality checks for unsupported free answer claims. Never fabricate IDs or equate channel with speaker.

Acceptance: tests unknown gist evidence, empty claims with factual non-abstention, caveat citations, unsupported name/inference labels; real brief matches full-source review and keeps key caveats.

### G05 MEDIUM — harness measurement/progress недостаточны для воспроизводимых выводов

Files: `benchmark.py:49,84–93`, `write_run:97–114`, `cli.py:152–158`. cache_mode unused; extract_cold0 can simply mean cache hit, warm0 is literal; usage/model only last brief response, prompt hashes only brief system. Runtime QA prompt differs from tracked prompts/qa.md. No effective-config/hash logs by harness; no stage setup time and partial result on error.

Fix: measured/clearly named cache state, actual instrumented extraction reuse, per-call usage/requested-returned model/prompt+retrieval version, effective config/timeouts/tool versions/source hashes and durable per-run files; report cost unavailable honestly. Don't imply0 cost/full offline/cold without evidence.

Acceptance: regression/live orx result exposes required fields and explicit failure/missing metrics, includes all inference calls or labels incomplete usage. Cached follow-up verifies exact hash and0 source-network calls. Research supplement for current runs is not a permanent code fix.

### G06 MEDIUM — spec surface/setup/metadata mismatch

Files: `cli.py:21–63` lacks local timed input and common --json; C metadata `captions_api.py:56–64` lacks title/channel/duration/coverage; A `baoyu.py:13,41–42` hardcodes external path/version and not verified upstream content pin. README setup cannot alone recreate project without external existing skill.

Acceptance: align documented supported scope or implement promised surface, explicit path/provenance/error contracts; validate all bundle metadata and setup dependency checks, source-language versus summary-language separation. Не расширять scope ASR/vision/MCP без user decision.

### G07 POLICY/STATE — no remote requirement не выполнен

Origin existed before researcher changes. It was neither removed nor used. Need owner's decision/reconciliation for exact no-remote spec, not stealth edit to `.git/config` and not retrospective no-publication claim. Downstream can keep no-new-publication evidence separate from no-remote criterion.

### G08 PENDING — canonical/default skill и final audit

Не дефект этой research ownership, но часть whole-project acceptance. Выполняет уже существующая downstream hardening lane после code-quality review и validated repairs. Canon/profile skill stores, AGENTS/global config/auth не трогались.

## Handoff/stop

Сохранены completed baseline и B actual outputs,6 logs/config/snapshots с real IDs/hashes и human content labels. `reports/observed-baseline-briefing.md` — exact existing generated baseline, **not approved final artifact**. Raw transcript не прикладывается.

Implementer notified via durable comments on `t_57ebfc61`. Further local experiment retries stopped at C cap. Needs input: authorize/reroute concrete readiness repairs and reconcile inherited remote policy, затем возобновить эту comparison card с соблюдением fixed contract/immutable history. Никаких fabricated orx result, pending cost/cookie default or arbitrary timeout approval.
