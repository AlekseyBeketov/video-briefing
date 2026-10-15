# Agent integration

[English README](../README.md) · [Русский README](../README.ru.md)

Video Briefing can be used as a Python CLI or as an optional local MCP stdio server. It does not require a framework-specific plugin, an editable install, or an agent SDK. The examples below use a source checkout because this repository does not include a wheel artifact.

## Install the MCP server

Check that Python 3.11–3.14 and `uv` are available. If `uv` is missing, follow its [official installation guide](https://docs.astral.sh/uv/getting-started/installation/). Clone the repository to a new, stable path, then install the optional MCP dependency into the checkout environment:

```sh
git clone https://github.com/AlekseyBeketov/video-briefing.git /ABS/PATH/video-briefing
cd /ABS/PATH/video-briefing
uv sync --frozen --extra mcp
uv run video-briefing --version
uv run video-briefing doctor
```

Do not clone over an existing directory. Keep this checkout at a stable path because the MCP host starts the executable from its `.venv` directory. On macOS/Linux, use `/ABS/PATH/video-briefing/.venv/bin/video-briefing-mcp`. On Windows, use `C:\ABS\PATH\video-briefing\.venv\Scripts\video-briefing-mcp.exe`, substituting the actual drive and path.

Configure the MCP client to launch that absolute executable as a local stdio process, with no shell wrapper. Set `VIDEO_BRIEFING_DATA_HOME` to a private directory outside the checkout if you want a dedicated evidence store. The CLI and MCP server share evidence only when they use the same data directory.

## MCP tools and access profiles

The server publishes these five tools:

- `ingest_youtube(url, language="ru")` fetches public timed YouTube captions and saves them locally.
- `ingest_local_mp4(path, language?, timeout_seconds=21600)` runs local-only speech recognition on an MP4. It selects the verified GigaAM Russian or Parakeet English model installed by `setup-asr`. If both models are installed, pass the spoken source language; the server does not auto-detect it.
- `search_video_evidence(source, query, language?, variant?, limit=12)` searches saved transcript segments and returns bounded text with times.
- `read_video_evidence(source, start_seconds, end_seconds, language?, variant?, max_segments=20)` reads bounded saved transcript evidence for a time range.
- `validate_video_claims(source, claims, language?, variant?)` checks that quotes, segment IDs, source identity, and time bounds match the saved evidence. It does not check semantic entailment or external truth.

Where the client supports a per-server tool allowlist, use only `search_video_evidence`, `read_video_evidence`, and `validate_video_claims` for a read-only profile. Add `ingest_youtube` only when the agent needs permission to fetch YouTube captions. Add `ingest_local_mp4` only when the agent is explicitly allowed to read and process local media; the server process can access files allowed by its operating-system account. If the client cannot enforce a tool allowlist, preserve its normal call confirmations and do not approve ingestion calls unless they are needed.

The server itself never calls an LLM. However, MCP tool results become context for the calling agent, whose provider may receive the transcript excerpts. Treat source text as untrusted input and get permission before sending private material to an agent or cloud provider.

## Agent-specific setup

Each page links to that client's current official MCP documentation, includes a ready-to-copy English prompt, and describes its connection check:

- [Hermes Agent](agent-prompts/hermes.md)
- [Codex CLI](agent-prompts/codex.md)
- [Claude Code](agent-prompts/claude-code.md)

The prompts are documentation aids, not installation scripts. They ask the agent to check prerequisites and the project instructions, use a new clone, avoid overwriting user files, install only into that clone, configure the chosen client, run `video-briefing doctor`, and report the actual MCP connection and tool list. None of the three prompts was end-to-end tested in its target client in the environment where this guide was written.

## Data and optional local ASR

By default the CLI and MCP server use the operating system's user data directory. Set `VIDEO_BRIEFING_DATA_HOME` to select a private directory shared by the processes. To enable managed local ASR from an MCP checkout, install both optional extras and choose the language profile:

```sh
uv sync --frozen --extra mcp --extra asr
uv run --frozen --extra mcp --extra asr video-briefing setup-asr --languages ru --yes
uv run --frozen --extra mcp --extra asr video-briefing doctor
```

Use `en` for English or `ru,en` for both. The managed route downloads GigaAM v3 e2e-RNN-T Q8_0 (274 MB, MIT) and/or NVIDIA Parakeet TDT-CTC 110M Q8_0 (135 MB, CC-BY-4.0) into `<VIDEO_BRIEFING_DATA_HOME>/asr/models`. The Parakeet model attribution is shown by setup and recorded on its [Hugging Face model card](https://huggingface.co/handy-computer/parakeet-tdt_ctc-110m-gguf). Downloads use pinned revisions, exact file sizes, and SHA-256 checks. Processing an MP4 stays local and uses PyAV; FFmpeg and FFprobe are not required.

`ingest_local_mp4` accepts `language="ru"` or `language="en"`. If exactly one verified profile is installed, the server can use that profile when the argument is omitted. If both are installed, omission returns a clear input error. Model setup language is not proof of the video language; ask or use available context to determine the spoken source language. Existing `VIDEO_BRIEFING_TRANSCRIBE`, `VIDEO_BRIEFING_ASR_MODEL`, `VIDEO_BRIEFING_FFMPEG`, and `VIDEO_BRIEFING_FFPROBE` overrides remain supported as an advanced legacy mode and must be provided as a complete transcribe-cli/model pair.

## Errors and troubleshooting

Expected source errors are returned with `status: "error"` and a code such as `invalid_input`, `source_unavailable`, `source_blocked`, `source_auth_required`, or `source_processing_failed`. `operation_failed` represents an unexpected error and intentionally hides internal details.

If the agent cannot connect, verify that its configured command points to the installed `video-briefing-mcp` executable, that the `mcp` extra was installed in that same environment, and that the client has restarted/reloaded its MCP connection. Run `video-briefing doctor` from that environment. A successful doctor check is local-only and does not prove that YouTube captions or a model endpoint are reachable.

If an evidence lookup says no source is cached, ingest an authorized source first. Do not work around a source error with browser cookies, credential files, or proxies.
