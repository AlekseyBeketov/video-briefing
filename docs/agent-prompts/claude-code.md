# Set up Video Briefing with Claude Code

[Claude Code MCP guide](https://code.claude.com/docs/en/mcp) · [Claude Code setup](https://code.claude.com/docs/en/setup) · [Shared integration guide](../agent-integration.md)

## Copyable prompt

```text
Set up the Video Briefing MCP server for Claude Code.

Use the current official project instructions at https://github.com/AlekseyBeketov/video-briefing and the repository's README.md. Before changing anything, check the operating system, Python version (the project requires 3.11–3.14), `uv`, Git, and the Claude Code CLI. Read the current Claude Code MCP guide at https://code.claude.com/docs/en/mcp and verify the current syntax for local-scope stdio servers, `claude mcp add`, `claude mcp list`, and `/mcp`.

If I requested local MP4 transcription, determine which source language(s) I want to transcribe. Use context to suggest Russian or English only when the intended video language is clear; otherwise ask whether to install `ru`, `en`, or `ru,en`. The language used in this chat and the OS locale do not prove the language of future videos. Explain the selected model, download size, and license before downloading. Do not download both models by default. If I requested YouTube captions only, skip local ASR model downloads.

Safety requirements:
- Do not read, print, copy, or ask me to paste secrets, browser cookies, credential files, or unrelated Claude configuration values.
- Do not use sudo, modify system Python, install a global package, use a proxy, or make an unapproved cloud/model call.
- Do not overwrite an existing checkout, skill, Claude config, or MCP server entry. If the chosen path or `video-briefing` server name already exists, stop and report the collision without removing or replacing it.
- Do not ingest a video or local file during setup. Only use a public source if I separately provide it and authorize that check.
- Stop and ask before any destructive change or before installing a missing system prerequisite. Use official installation instructions only.

At the start, record the project directory where you are running Claude Code. If prerequisites are available, choose a new absolute clone path and a separate private data path; verify that neither target already exists. Clone only the exact repository above, confirm `git remote get-url origin`, read its README, then run from the new checkout. For MCP without local MP4 support, run:

    uv sync --frozen --extra mcp
    uv run --frozen --extra mcp video-briefing --version
    uv run --frozen --extra mcp video-briefing doctor

If local MP4 transcription was requested, use both extras and install only the selected language profile:

Use the same private `VIDEO_BRIEFING_DATA_HOME` for setup, the final `doctor` check, and the Claude MCP server entry. Set it only for these process invocations; do not edit a shell profile.

    uv sync --frozen --extra mcp --extra asr
    uv run --frozen --extra mcp --extra asr video-briefing setup-asr --languages ru --yes
    uv run --frozen --extra mcp --extra asr video-briefing doctor

Replace `ru` with the agreed `en` or `ru,en`. The installer downloads a pinned model and the Python runtime; it does not need a user-supplied `transcribe-cli`, GGUF path, FFmpeg, or FFprobe. Stop if `uv` reports an unsupported native wheel; do not compile or install system packages as a workaround.

Confirm that the checkout's `.venv` contains `video-briefing-mcp`. Use its absolute path as the local stdio server command. On macOS/Linux it is `<clone>/.venv/bin/video-briefing-mcp`; on Windows it is `<clone>/.venv/Scripts/video-briefing-mcp.exe`.

Return to the original project directory before adding the Claude Code MCP entry so local scope belongs to the project where you will use the tools, not the installation clone. If there was no project directory, ask me where the local-scoped integration should apply. Check `claude mcp list` before changing configuration. If a server named `video-briefing` already exists, stop without changing it. Otherwise add a local-scope stdio server using Claude Code's documented CLI syntax:

    claude mcp add video-briefing --scope local --env 'VIDEO_BRIEFING_DATA_HOME=/ABSOLUTE/PATH/TO/PRIVATE/VIDEO-BRIEFING-DATA' -- '/ABSOLUTE/PATH/TO/video-briefing-mcp'

Replace the example paths with the verified paths. Keep the default Claude Code confirmation behavior for MCP tools; do not auto-approve tool calls or change permission settings. If Claude Code cannot restrict this server to read-only tools in its current configuration model, leave ingestion calls unapproved and explain that limitation rather than claiming the tools were removed.

Run `claude mcp list` and `claude mcp get video-briefing`, then start or reload Claude Code and use `/mcp` to verify that the server connected and to inspect its tool list. If local ASR was installed, verify the selected language appears ready in `doctor`. Do not call ingestion tools or process media as a setup test. If the MCP connection or catalog check fails, report the exact output and leave the config intact.

Report the Python and CLI versions, the doctor result, the installed executable path, the local config scope (never print config contents), and the MCP status/tool names. State which checks you could not run. Do not claim a successful connection unless Claude Code itself confirms it.
```

## Verification status

**Not end-to-end tested in Claude Code in this environment.** The current official Claude Code MCP and setup pages were checked on 2026-10-14. Claude Code was not installed in the authoring environment, so its CLI add command and live connection were not exercised.
