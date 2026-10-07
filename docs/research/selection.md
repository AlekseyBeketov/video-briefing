# Predeclared extractor shortlist

Зафиксировано до получения variant-generated briefing/Q&A. Исследовательская фаза; generated answers не читались.

A — существующий Baoyu 1.1.0 из `/Users/alexbeketov/.hermes/skills/media/baoyu-youtube-transcript`, без `--speakers`, переводов и AI-постобработки. Сохранять raw `{text,start,duration}`; proportional sentence timestamps не использовать как alignment.

B — `steipete/summarize`, extraction-only (`--youtube web --extract --timestamps --json` после проверки установленного help). Его собственное summary не участвует; description fallback и облачный ASR запрещены. Использовать standalone либо project-local поддерживаемый runtime, не глобальный Node upgrade.

C — предварительно `youtube-transcript-api`, captions-only; не local ASR. Причина: для первого bounded preflight нет подтверждённого локального whisper model/runtime, captions extractor не требует скачивания ASR-модели. Это третья реализация доступа к тем же YouTube captions, не независимый content truth. Окончательная доступность C определяется реальной попыткой. При отсутствии captions/доступа к audio C допустимо не запускать; не добавлять четвёртый extractor.

Все варианты: один точный URL `https://www.youtube.com/watch?v=DvSwvJVens8`; original source language, не требование русского transcript; общий downstream Ollama `gemma4:31b-cloud`, temperature 0. Облачная природа модели явно указывается. Никаких cookies, proxies, ключей, paid API, nested agents или profile edits. Setup и preflight не считать formal OpenResearch comparison; реальные formal runs — следующая фаза.
