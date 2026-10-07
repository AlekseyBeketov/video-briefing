---
name: video-briefing
description: Use when a user shares a video URL and needs a source-grounded summary or transcript Q&A. Run the project CLI, cite timed evidence, and abstain honestly.
---

# Video Briefing

Use the checked-in project CLI; do not substitute browsing, video descriptions, model memory, or an uncited summary. Default to Russian for a Russian source. This workflow processes captions only: it does not watch frames, verify spoken audio, diarize speakers, or independently fact-check hardware claims.

## Run it

The helper routes to the project's frozen `uv` environment and reuses the exact stored transcript for follow-up questions. Set `VIDEO_BRIEFING_PROJECT` if the checkout is not `/Users/alexbeketov/video-briefing`.

```sh
python3 /Users/alexbeketov/video-briefing/skills/video-briefing/scripts/video_briefing.py brief 'https://www.youtube.com/watch?v=VIDEO_ID'
python3 /Users/alexbeketov/video-briefing/skills/video-briefing/scripts/video_briefing.py ask 'https://www.youtube.com/watch?v=VIDEO_ID' --question 'Вопрос по видео'
```

For another installed copy, use its absolute `scripts/video_briefing.py` path. Run `python3 .../video_briefing.py --help` for the exact interface. Default extraction variant is the tested anonymous `captions_api`; `baoyu` and `summarize` are optional alternatives, not fallbacks to try automatically. Keep the same URL, `--language ru`, and `--variant captions_api` for reproducible source-bound questions.

The summary is organized into gist, topics, useful ideas, speaker emphasis, and caveats. Keep `author_statement` separate from `assistant_inference`; do not turn a speaker's heuristic into a universal rule or label the channel as proof of speaker identity. Cite segment IDs and timestamps whenever presenting a factual source claim. Q&A emits JSON claims with resolved segment IDs/times; distinguish the video's claims from external fact.

## Grounding and limitations

- Use only saved timed transcript evidence. If extraction reports no captions, say so; never replace the transcript with a title, description, or invented summary.
- If retrieval finds no supporting passage, use the tool's abstention and state that the saved transcript did not yield evidence. Do not claim exhaustive absence unless the full source was checked independently.
- An `evidence` ID proves only that a segment exists, not that it semantically supports the claim. Review the cited passage for meaning, numeric units, context, caveats, and conditional recommendations.
- The adapter does not use browser cookies, credentials, proxies, or paid ASR. A network/IP block is a stop condition, not a prompt to bypass access controls. Authentication-required and no-caption errors are reported separately.
- The configured Ollama endpoint is cloud-backed (`gemma4:31b-cloud`); transcript excerpts/questions are sent for remote inference. Do not describe the full workflow as offline or private-local.
- Do not infer visual facts, on-screen numbers, speaker identity, or audio details from captions. Auto-captions can omit speech; bounded storyboard previews are not full-video inspection.

## Troubleshooting

Run `cd "$VIDEO_BRIEFING_PROJECT" && uv run --frozen video-briefing doctor`. It checks model endpoint reachability and reports installed versions of the configured caption client, Bun, and summarize binary. Install the pinned Python environment with `uv sync --frozen`. Only if the chosen optional extractor is needed, run `scripts/setup-tools.sh` and follow `README.md`; Baoyu remains an external skill dependency.

- `No captions are available`: verify the requested language; this source has no usable captions in that language. Do not use description-only fallback.
- `blocked this network/IP`: YouTube rejected the anonymous request. Stop and report it; do not rotate proxies or add cookies.
- `requires authentication/cookies`: report that the workflow cannot access this source without authentication; it intentionally does not read or use cookies.
- Model endpoint unavailable: follow `README.md` to check the configured Ollama endpoint. Do not switch models or cloud/local policy without user approval.

## Canonical source

The runnable CLI, pinned dependencies, regression tests, prompts, and evidence contracts live in the `video-briefing` project. Read `references/limitations.md` before describing this as production-ready. The installed skill tree is independently audited against the committed canonical tree during deployment.
