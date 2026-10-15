# Set up Video Briefing with Hermes Agent

[Hermes MCP guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) · [Hermes MCP config reference](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference/) · [Shared integration guide](../agent-integration.md)

## Copyable prompt

```text
Set up the Video Briefing MCP server for this Hermes Agent installation.

Use the current official project instructions at https://github.com/AlekseyBeketov/video-briefing and the repository's README.md. Before changing anything, check the operating system, Python version (the project requires 3.11–3.14), `uv`, Git, and the Hermes CLI. Read the current Hermes MCP guide and configuration reference at:
- https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
- https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference/

If I requested local MP4 transcription, determine which source language(s) I want to transcribe. Use context to suggest Russian or English only when the intended video language is clear; otherwise ask whether to install `ru`, `en`, or `ru,en`. The language used in this chat and the OS locale do not prove the language of future videos. Explain the selected model, download size, and license before downloading. Do not download both models by default. If I requested YouTube captions only, skip local ASR model downloads.

Safety requirements:
- Do not read, print, copy, or ask me to paste secrets, browser cookies, credential files, or unrelated agent configuration values.
- Do not use sudo, modify system Python, install a global package, use a proxy, or make an unapproved cloud/model call.
- Do not overwrite an existing checkout, skill, Hermes config, or MCP server entry. If the chosen path or `video_briefing` server name already exists, stop and report the collision without deleting or replacing it.
- Do not ingest a video or local file during setup. Only use a public source if I separately provide it and authorize that check.
- Stop and ask before any destructive change or before installing a missing system prerequisite. Use official installation instructions only.

If prerequisites are available, choose a new absolute clone path and a separate private data path; verify that neither target already exists before using it. Clone only the exact repository above, confirm `git remote get-url origin`, read its README, then run from the new checkout. For MCP without local MP4 support, run:

    uv sync --frozen --extra mcp
    uv run --frozen --extra mcp video-briefing --version
    uv run --frozen --extra mcp video-briefing doctor

If local MP4 transcription was requested, use both extras and install only the selected language profile:

Use the same private `VIDEO_BRIEFING_DATA_HOME` for setup, the final `doctor` check, and the Hermes server entry. Set it only for these process invocations; do not edit a shell profile.

    uv sync --frozen --extra mcp --extra asr
    uv run --frozen --extra mcp --extra asr video-briefing setup-asr --languages ru --yes
    uv run --frozen --extra mcp --extra asr video-briefing doctor

Replace `ru` with the agreed `en` or `ru,en`. The installer downloads a pinned model and the Python runtime; it does not need a user-supplied `transcribe-cli`, GGUF path, FFmpeg, or FFprobe. Stop if `uv` reports an unsupported native wheel; do not compile or install system packages as a workaround.

Confirm that the checkout's `.venv` contains `video-briefing-mcp`. Use its absolute path as the stdio `command` in Hermes. On macOS/Linux it is `<clone>/.venv/bin/video-briefing-mcp`; on Windows it is `<clone>/.venv/Scripts/video-briefing-mcp.exe`.

Before editing Hermes configuration, use the documented Hermes commands to check whether `video_briefing` is already configured. If it is absent, add only this server entry to the existing `mcp_servers` mapping in the user's chosen Hermes profile, preserving every other entry and never rewriting the whole file:

    mcp_servers:
      video_briefing:
        command: "/ABSOLUTE/PATH/TO/video-briefing-mcp"
        args: []
        env:
          VIDEO_BRIEFING_DATA_HOME: "/ABSOLUTE/PATH/TO/PRIVATE/VIDEO-BRIEFING-DATA"
        tools:
          include:
            - search_video_evidence
            - read_video_evidence
            - validate_video_claims
          resources: false
          prompts: false
        sampling:
          enabled: false

Replace both example paths with the verified absolute paths. `sampling.enabled: false` is documented Hermes configuration and explicitly prevents server-initiated model sampling. Do not broaden the tool allowlist without asking me.

Validate with `hermes mcp test video_briefing`, then start or reload a Hermes session and inspect its MCP status/tool catalog. Confirm that the three allowed tools are discoverable. If local ASR was installed, verify the selected language appears ready in `doctor`. Do not call ingestion tools or process media as a setup test. If the CLI or session cannot connect, stop and report the exact failure instead of claiming success.

Report the Python and CLI versions, the doctor result, the installed executable path, the config scope/path (never print its contents), the MCP test result, and the discovered tool names. State which checks you could not run. Do not claim a successful connection unless Hermes itself confirms it.
```

## Verification status

**Not end-to-end tested in Hermes in this environment.** The current official Hermes config reference was checked on 2026-10-14. `hermes mcp test <name>` and the `sampling.enabled` setting are documented, but this environment's Hermes install state was not writable, so this exact prompt and config merge were not run in Hermes.
