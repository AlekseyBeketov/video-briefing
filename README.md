# Video Briefing

[Инструкция на русском](README.ru.md)

**Set up with an AI agent:** copy the prompt for [Codex CLI](docs/agent-prompts/codex.md#copyable-prompt), [Claude Code](docs/agent-prompts/claude-code.md#copyable-prompt), or [Hermes](docs/agent-prompts/hermes.md#copyable-prompt). Each page contains a ready-to-copy English prompt.

Video Briefing is a Python command-line tool and optional MCP server for working with timed video transcript evidence. It saves captions or explicitly requested local speech-to-text output, then lets you search or read the original segments with timestamps. An agent or reader can use those excerpts to write a source-grounded answer.

The normal `ingest`, `search`, and `read` workflow does not call a language model. Optional `brief` and `ask` commands do call a configured model and are separate from the evidence-first workflow.

## Prerequisites

- Python 3.11, 3.12, 3.13, or 3.14.
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) for the checkout-based setup below.
- Internet access to install Python dependencies, optionally download selected speech models, and fetch public YouTube captions. The tool does not bypass blocks, sign-in requirements, or rate limits.

The continuous-integration workflow checks Python 3.11–3.14 on Ubuntu. The project has not published a broader operating-system support matrix.

## Install from the repository

```sh
git clone https://github.com/AlekseyBeketov/video-briefing.git
cd video-briefing
uv sync --frozen
uv run video-briefing --help
uv run video-briefing doctor
```

`uv sync --frozen` installs the versions recorded in `uv.lock` into this checkout's project environment. `doctor` reports optional ASR runtime and verified model files; external FFmpeg/FFprobe entries apply only to the legacy mode. It does not contact YouTube, download models, load a model, or run inference.

## Quick start: YouTube captions

Replace `VIDEO_ID` with the ID of a public YouTube video whose timed captions you can access.

```sh
VIDEO='https://www.youtube.com/watch?v=VIDEO_ID'
uv run video-briefing ingest "$VIDEO"
uv run video-briefing search "$VIDEO" 'main ideas and decisions'
uv run video-briefing read "$VIDEO" 120 180
```

The default `captions_api` extractor uses `youtube-transcript-api` and requests Russian captions by default. `ingest` saves the source evidence locally. `search` returns a bounded set of matching transcript segments; `read` returns bounded segments in the requested time range. Both include source text and timing metadata. Use the returned excerpts as evidence and check the surrounding context before making a claim.

There is no automatic fallback to descriptions, cookies, browser sessions, proxies, or another extractor if captions are missing or access is blocked. The optional `baoyu` variant must be selected explicitly with `--variant baoyu` and separately configured.

## Quick start: local MP4

Local transcription is opt-in. Install the managed runtime and Russian model with one command from the repository:

```sh
uv run --frozen --extra asr video-briefing setup-asr --languages ru --yes
uv run --frozen --extra asr video-briefing doctor
uv run --frozen --extra asr video-briefing ingest /path/to/video.mp4 --local-asr --source-language ru
```

Choose `en` for English or `ru,en` to install both. The setup command downloads only the selected, pinned model files to the user data directory, verifies their exact size and SHA-256, and never downloads or runs an external ASR executable. If run interactively without `--languages`, it suggests a profile from the OS locale and asks before downloading. Non-interactive use requires an explicit language selection. `--yes` confirms only the displayed public model download.

The Russian profile uses GigaAM v3 e2e-RNN-T Q8_0 (274 MB, MIT). The English profile uses NVIDIA Parakeet TDT-CTC 110M Q8_0 (135 MB, CC-BY-4.0; attribution is included in the setup output and [model card](https://huggingface.co/handy-computer/parakeet-tdt_ctc-110m-gguf)). Both models run locally and require the spoken language to be known; installation does not detect the language of an arbitrary video. If both profiles are installed, `--source-language` is required.

To use the English model:

```sh
uv run --frozen --extra asr video-briefing setup-asr --languages en --yes
uv run --frozen --extra asr video-briefing ingest /path/to/video.mp4 --local-asr --source-language en
```

Use the returned media SHA-256 to search or read the saved local evidence:

```sh
uv run video-briefing search MEDIA_SHA256 'тема'
uv run video-briefing read MEDIA_SHA256 120 180
```

Local ASR processes audio on this machine. Its timestamps identify 24-second processing windows, not word-level alignment, and its transcript may contain recognition errors.

For a long-lived environment, install the runtime once with `uv sync --frozen --extra asr`. When using MCP for local MP4s, install both extras with `uv sync --frozen --extra mcp --extra asr` before running `setup-asr`. The managed route uses PyAV and does not need FFmpeg or FFprobe. Existing `--transcribe-cli`/`--model` and `VIDEO_BRIEFING_TRANSCRIBE`/`VIDEO_BRIEFING_ASR_MODEL` settings remain available as a legacy compatibility route.

## Connect an agent

The optional MCP server lets an MCP-capable agent call Video Briefing tools through a local stdio process. From the repository, install the extra with:

```sh
uv sync --frozen --extra mcp
uv run video-briefing --version
uv run video-briefing doctor
```

The MCP server exposes `ingest_youtube`, `ingest_local_mp4`, `search_video_evidence`, `read_video_evidence`, and `validate_video_claims`. Where the agent supports a per-server tool allowlist, enable only `search_video_evidence`, `read_video_evidence`, and `validate_video_claims` for a read-only setup. If it does not, keep its normal tool confirmations and do not approve ingestion calls unless needed.

See [the shared agent integration guide](docs/agent-integration.md) and the copyable setup prompts for [Hermes](docs/agent-prompts/hermes.md), [Codex CLI](docs/agent-prompts/codex.md), and [Claude Code](docs/agent-prompts/claude-code.md).

The MCP server does not call a model. Its evidence output becomes part of the calling agent's context, so the agent's provider may receive transcript excerpts. Review the provider's data handling before using private or sensitive sources.

## Configuration and data

Evidence is stored outside the repository in the operating system's user data directory:

- macOS: `~/Library/Application Support/VideoBriefing`
- Windows: `%LOCALAPPDATA%/VideoBriefing`
- Linux and other Unix systems: `$XDG_DATA_HOME/video-briefing`, or `~/.local/share/video-briefing` when `XDG_DATA_HOME` is unset

Set `VIDEO_BRIEFING_DATA_HOME` to use a different private data directory. Set the same value in the CLI and MCP server environments when they should share the same evidence cache. Do not point it at a public or version-controlled directory.

Managed ASR models are stored under `<VIDEO_BRIEFING_DATA_HOME>/asr/models` (or under the default OS data directory shown above). No ASR paths need manual configuration. Advanced legacy installations may still use `VIDEO_BRIEFING_TRANSCRIBE`, `VIDEO_BRIEFING_ASR_MODEL`, `VIDEO_BRIEFING_FFMPEG`, and `VIDEO_BRIEFING_FFPROBE`.

The optional `brief` and `ask` commands use the Ollama-compatible endpoint and settings in `config/experiment.json` by default. Review that configuration before use. A cloud-backed or non-loopback endpoint requires an explicit `--allow-cloud` flag because it may receive transcript excerpts and questions. `ask` uses cached evidence and does not fetch a missing source; run `ingest` first. These optional generation commands do not replace the normal source-first workflow.

## Evidence and limits

- Video Briefing reads timed captions or explicitly selected local audio transcription. It does not analyze video frames, verify claims against independent sources, or guarantee that automatic captions include every spoken word.
- A successful citation check confirms that quoted text, segment IDs, source identity, and time bounds match stored evidence. It does not prove that a paraphrase is semantically supported or that an outside-world claim is true.
- A missing cache entry means the source must be ingested before `search`, `read`, or `ask` can use it.
- YouTube may withhold captions, require authentication, block an anonymous request, or rate-limit access. Stop on those errors; do not work around them with cookies or proxies.
- The project is open source under the MIT License; see [LICENSE](LICENSE). Third-party speech models have separate licenses listed above.

## Troubleshooting

**`doctor` reports a missing `youtube-transcript-api` dependency.** Run `uv sync --frozen` from the repository root and retry. `doctor` checks local dependency availability, not network access to YouTube.

**Search or read says no matching evidence is cached.** Run `video-briefing ingest` for that URL or MP4 first. Ensure the source language and variant match the saved evidence.

**YouTube captions are unavailable or access is blocked.** The tool will report the source error. Try again later or choose another source you are authorized to use; the tool does not use cookies, authentication files, or proxies to bypass access restrictions.

**The MCP server is missing or the agent cannot connect.** Install the `mcp` extra, confirm the configured command points to the environment's `video-briefing-mcp` executable, then restart/reload the agent and inspect its MCP status page. Run `video-briefing doctor` in the same environment as the server.

**Local MP4 ingestion reports a missing ASR model.** Run `uv run --frozen --extra asr video-briefing setup-asr --languages ru --yes` or choose `en` for English. Run `doctor` to check installed model hashes. If both models are installed, pass `--source-language ru` or `--source-language en`; the tool does not guess the spoken language of a video.

**`setup-asr` reports a missing runtime or unsupported wheel.** Run `uv sync --frozen --extra asr` from the repository, then retry. The Python package provides prebuilt native wheels for macOS arm64/x86_64, Linux x86_64/aarch64, and Windows x86_64; this repository's live real-model check was performed on macOS arm64 with Python 3.14. On another platform, report the exact `uv` error instead of installing a compiler or system package automatically.

**Model download is incomplete or its checksum fails.** Setup removes its temporary partial file and does not activate the model. Retry on a stable connection. If the target model path already exists with different contents, setup leaves it untouched; move or back up that file yourself before retrying.

## Development

```sh
uv sync --frozen --extra dev --extra mcp
uv run --frozen pytest
uv run --frozen ruff check .
```

## License

Video Briefing is distributed under the [MIT License](LICENSE). The downloaded Parakeet model is separately licensed under CC-BY-4.0; GigaAM v3 is MIT-licensed.
