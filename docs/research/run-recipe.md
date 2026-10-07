# Formal local OpenResearch contract

Зафиксировано 2026-10-07 перед formal variant outputs; evaluation SHA256 `7abd485c1549e336497346a7cf571098a7ca18c8662ddf8f81ad781a0c94d1a1` неизменен.

## Hypotheses and tree

Baseline/root: captions_api проверяет, что один original-RU timed source проходит общий brief + 8 cached questions в immutable snapshot. Затем co-equal siblings A Baoyu, B summarize, C captions_api проверяют единственный выбор extractor. A/B — обязательные попытки; C заранее выбран preflight вместо ASR. C sibling — повторный независимый запуск pipeline после baseline, не отдельная новая методика. n=1 на sibling; baseline C отдельно, не смешивать в среднее. Порядок baseline C → A → B → C; нет randomized order, upstream cache/model warm-order confounds. Только local backend, никаких orx/других агентов.

## Fixed command

    env -i HOME=/Users/alexbeketov/video-briefing/artifacts/private/orx-home PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin UV_CACHE_DIR=/Users/alexbeketov/video-briefing/artifacts/private/orx-uv-cache VIDEO_BRIEFING_BUN=/Users/alexbeketov/video-briefing/.tools/bun/node_modules/.bin/bun VIDEO_BRIEFING_SUMMARIZE=/Users/alexbeketov/video-briefing/.tools/summarize/summarize /opt/homebrew/bin/uv run --frozen --python /Users/alexbeketov/video-briefing/.venv/bin/python python -m video_briefing.cli benchmark --config config/experiment.json

Same command/env every node. Only committed `config/experiment.json.variant` changes. Inference endpoint/model/temp/timeout are committed config constants: http://127.0.0.1:11434, gemma4:31b-cloud, temp0, timeout300. Returned model is logged separately. Cloud-backed, not offline. Existing external Python/tool paths are preverified, not expected to travel in Git archive. HOME/cache roots are project-private, no global credential/config reads supplied by recipe. Shared upstream cache remains uncertain: fresh per-snapshot wrapper store ≠ cold network extraction.

CLI default root/store/output are snapshot-relative. Each isolated local-run source therefore has its own artifact store and `artifacts/private/runs/{metrics.json,briefing.md,answers.json}`. Collect actual absolute paths from logs/runner, preserve private artifacts; no raw transcript attachments or commits. Reference source at main `data/reference` is evaluator-only, never model prompt. Before/after hash checks verify goldset/source unchanged. A missing tool/model/evaluation prerequisite is setup failure, not scientific failure.

## Existing-state exceptions and known measurement gaps

At orientation main commit8aeb697 already has `origin=https://github.com/AlekseyBeketov/video-briefing.git`. No remote added, removed, fetched or pushed here. Import has explicit githubSyncEnabled=false; strict 'no remote' spec is a documented gap, not a pass. Dashboard was not reachable on4791; existing daemon was absent, so restored only loopback `orx up --no-agent --no-browser --no-telemetry --port4791`, no second agent.

Harness currently does not enforce cache_mode, source-language equality or persist effective-config/prompt/retrieval hashes. Research records exact committed config/source files/hashes separately. Harness usage fields describe only last briefing response; full pipeline cost not measured. Literal warm extractor_calls0 is NOT instrumentation. Research must independently run existing cached lookup/Q&A with fail-on-extractor and network-adapter guards; no full extraction for this verification.

Runtime versions verified before runs: orx0.2.15, uv0.12.1, Python3.13.14, Bun1.4.2, summarize0.25.1, youtube-transcript-api1.2.4, Ollama0.35.1. summarize official archive SHA256 `6d361feb48e77accb20ae0cd9eb1ae1e69298e26079200e57a98df7e6e720571`; binary SHA256 `02bae0e28549ba9542864cbed2e754cc4f9b5b6976ed59a1ccbabc324291d4f3`. Baoyu main.ts SHA256 `c838bb93c88702d06eef79e22e0861a256dc3996841ae26a592431236917ddc5` (existing skill, no writes).

## Stop/assessment

Read full logs/metrics after `orx exp run --backend local` and `orx exp wait`; freeze every answered node, including negative availability results. Max2 answerless repairs/node; repeat setup defect on second node stops experiment, not endless retry. No model/provider/source replacement. Same-caption agreement is preservation/grounding, not independent audio truth. Report supported/partial/unsupported/unverifiable claims against full reference and cited context; predefined8 anchors,8 questions. One valid RU workflow and failed/noncomparable alternatives is usable MVP, NOT successful head-to-head content superiority. downstream review/hardening/final audit remain required.
