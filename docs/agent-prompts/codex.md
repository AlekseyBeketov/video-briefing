# Set up Video Briefing with Codex CLI

[Codex CLI MCP guide](https://developers.openai.com/codex/mcp) · [Codex CLI guide](https://developers.openai.com/codex/cli) · [Shared integration guide](../agent-integration.md)

## Copyable prompt

```text
Set up the Video Briefing MCP server for Codex CLI.

Use the current official project instructions at https://github.com/AlekseyBeketov/video-briefing and the repository's README.md. Before changing anything, check the operating system, Python version (the project requires 3.11–3.14), `uv`, Git, and the Codex CLI. Read the current Codex CLI MCP guide at https://developers.openai.com/codex/mcp and verify the current syntax for `codex mcp add`, `codex mcp list`, stdio server configuration, and the `enabled_tools` setting.

Safety requirements:
- Do not read, print, copy, or ask me to paste secrets, browser cookies, credential files, or unrelated Codex configuration values.
- Do not use sudo, modify system Python, install a global package, use a proxy, or make an unapproved cloud/model call.
- Do not overwrite an existing checkout, skill, Codex config, or MCP server entry. If the chosen path or `video-briefing` server name already exists, stop and report the collision without removing or replacing it.
- Do not ingest a video or local file during setup. Only use a public source if I separately provide it and authorize that check.
- Stop and ask before any destructive change or before installing a missing system prerequisite. Use official installation instructions only.

If prerequisites are available, choose a new absolute clone path and a separate private data path; verify that neither target already exists. Clone only the exact repository above, confirm `git remote get-url origin`, read its README, then run from the new checkout:

    uv sync --frozen --extra mcp
    uv run video-briefing --version
    uv run video-briefing doctor

Confirm that the checkout's `.venv` contains `video-briefing-mcp`. Use its absolute path as the stdio server command. On macOS/Linux it is `<clone>/.venv/bin/video-briefing-mcp`; on Windows it is `<clone>/.venv/Scripts/video-briefing-mcp.exe`.

Check `codex mcp list` before editing config. If a server named `video-briefing` already exists, stop without changing it. Otherwise use the official Codex CLI command to add the stdio server, passing `VIDEO_BRIEFING_DATA_HOME` as a non-secret environment variable. Codex documents this command shape:

    codex mcp add video-briefing --env 'VIDEO_BRIEFING_DATA_HOME=/ABSOLUTE/PATH/TO/PRIVATE/VIDEO-BRIEFING-DATA' -- '/ABSOLUTE/PATH/TO/video-briefing-mcp'

Replace the example paths with the verified paths. Codex CLI's add command does not expose a per-tool allowlist option, so use the documented `enabled_tools` field in the matching `mcp_servers.video-briefing` table in `~/.codex/config.toml` to keep only the read-only tools enabled:

    [mcp_servers.video-briefing]
    command = "/ABSOLUTE/PATH/TO/video-briefing-mcp"
    args = []
    enabled_tools = ["search_video_evidence", "read_video_evidence", "validate_video_claims"]

    [mcp_servers.video-briefing.env]
    VIDEO_BRIEFING_DATA_HOME = "/ABSOLUTE/PATH/TO/PRIVATE/VIDEO-BRIEFING-DATA"

Do not rewrite `config.toml`. Preserve unrelated settings. If the table appeared during the CLI add step, edit only that new table to add `enabled_tools`; if you cannot safely identify and merge that table, stop and ask instead of replacing the file. Do not change the Codex tool-approval policy or enable ingestion tools without my permission.

Run `codex mcp list`, then open a Codex CLI session and use `/mcp` to verify that the server connected and only the three read-only tools are listed. Do not call ingestion tools or process media as a setup test. If the MCP connection or catalog check fails, report the exact output and leave the config intact.

Report the Python and CLI versions, the doctor result, the installed executable path, the config scope/path (never print its contents), and the MCP status/tool names. State which checks you could not run. Do not claim a successful connection unless Codex itself confirms it.
```

## Verification status

**Not end-to-end tested in Codex CLI in this environment.** The official Codex MCP page and local `codex mcp --help` were checked on 2026-10-14. Codex CLI command help is not proof that this newly written prompt successfully configures or connects the server, so the prompt remains explicitly unverified.
