# Public Documentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish accurate English and Russian setup documentation and safe, copyable setup prompts for Hermes, Codex CLI, and Claude Code, while reconciling stale project text.

**Architecture:** Keep `README.md` as the English entry point and `README.ru.md` as its Russian counterpart. Put common MCP/privacy guidance in `docs/agent-integration.md`, with one agent-specific setup page and prompt per client under `docs/agent-prompts/`. Preserve intentional packaged-resource copies and test their byte-for-byte parity.

**Tech Stack:** Markdown, Python 3.11–3.14, `uv`, pytest, Ruff, the `video-briefing` CLI, and optional MCP stdio integration.

---

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. The repository has no checked-in `PLANS.md`; the local planning rules used for this file are `/Users/alexbeketov/.codex/Plans.md`.

## Purpose / Big Picture

After this work, a new user can understand what Video Briefing does, install it using a command that matches the repository, inspect timed transcript evidence, and connect it to one of the three documented MCP clients without silently granting unrelated tools. The user can follow the same facts in English or Russian. Maintainers can detect drift between the portable skill/prompts and the copies shipped inside the Python package.

The observable result is a set of checked-in documentation pages and a passing parity test. A reader can start with `README.md` or `README.ru.md`, run `video-briefing --help` and `video-briefing doctor`, and use the agent-specific page to configure an MCP server. Prompts must report whether they actually connected and must not claim a live-client check that was not performed.

## Progress

- [x] (2026-10-14) Confirm exact repository slug and remote: `AlekseyBeketov/video-briefing`, `https://github.com/AlekseyBeketov/video-briefing.git`.
- [x] (2026-10-14) Audit existing README, integration guide, architecture notes, pending decisions, package resources, CLI help, and Python package metadata.
- [x] (2026-10-14) Agree on the documentation design and commit `docs/plans/2026-10-14-public-docs-design.md` as `4c72895`.
- [ ] Commit this implementation plan before editing public or maintained documentation.
- [ ] Replace the Russian-only root README with an accurate English entry point and add its Russian counterpart.
- [ ] Add shared MCP guidance and separate English copyable prompts for Hermes, Codex CLI, and Claude Code.
- [ ] Correct stale design/decision/plan text and add automated packaged-resource parity coverage.
- [ ] Verify links, commands, content consistency, relevant tests and quality checks; review the exact diff and push each change to `origin/main`.

## Surprises & Discoveries

- Observation: The current README and integration guide describe installing a wheel, but the repository does not contain a wheel or publish an install artifact from this checkout. The integration guide hardcodes version `0.2.0` and includes a Hermes `sampling` field that is absent from the current official Hermes config schema.
  Evidence: `README.md`, `docs/agent-integration.md`, and the current Hermes MCP config reference.
- Observation: Three copies are deliberate: `skills/video-briefing/SKILL.md` and `prompts/{brief,qa}.md` are mirrored under `src/video_briefing/resources/` so the package can ship and print them. The skill copies have matched SHA-256 `cc15ea039194aa1bc3c13d3b1d692da98973811a0ba38c876d68b338540d02c4` in the baseline.
  Evidence: `video-briefing skill` output and byte comparison of repository and packaged files.
- Observation: `video-briefing --help` shows that normal source/evidence work is separate from optional model-generated `brief` and `ask`; these optional commands require an explicit privacy opt-in for cloud-backed endpoints.
  Evidence: the local Python 3.11 CLI printed the commands `doctor`, `extract`, `ingest`, `search`, `read`, `skill`, `brief`, `ask`, and `benchmark`.
- Observation: A fresh dependency sync could not reach PyPI because DNS resolution failed in the sandbox. Hermes cannot write its install state in this environment, and Claude Code is not installed. Client-specific prompts therefore cannot be declared end-to-end tested here.
  Evidence: `uv sync` failed resolving `pypi.org`; Hermes reported a locked install-state path; `claude` was not found. The installed Codex CLI's `codex mcp --help` succeeded.

## Decision Log

- Decision: Keep `README.md` in English, add a parallel Russian README, and put common agent safety guidance in `docs/agent-integration.md` with three separate prompts.
  Rationale: This gives both language audiences a stable entry point and lets users copy the prompt matching their client without confusing the clients' different configuration models.
  Date/Author: 2026-10-14 / user-approved design.
- Decision: Use a fresh project clone and isolated project environment for prompt-driven setup; never overwrite an existing clone, skill, or agent config. On a name/path conflict, stop and ask. Do not read or print secrets, cookies, or unrelated config values.
  Rationale: `uv sync` acts on the current project's environment and may remove extraneous packages there; a dedicated non-existing clone path bounds that effect and makes the installed MCP command stable.
  Date/Author: 2026-10-14 / user-approved design.
- Decision: Mark each client prompt as not end-to-end tested in its actual client in this environment.
  Rationale: Source review and CLI help are not proof that an agent host successfully connects. Hermes is not writable, Claude Code is absent, and the planned prompts are being authored in this work.
  Date/Author: 2026-10-14 / implementation evidence.
- Decision: Do not add or select a license, publish a release, or alter the repository's visibility.
  Rationale: The repository has no `LICENSE`, and the user-approved context reserves license and release choices for the user.
  Date/Author: 2026-10-14 / user-approved scope.
- Decision: Leave research data, reports, rubrics, and pre-existing user changes untouched; mark the old 2026-10-05 plan as historical instead of rewriting its record.
  Rationale: Those files preserve evidence and provenance; the old plan describes a prior implementation phase rather than current setup instructions.
  Date/Author: 2026-10-14 / user-approved design.

## Outcomes & Retrospective

Pending. Update this section after implementation and final validation. Record the exact commits pushed, actual test results, which prompts were and were not checked in their clients, and any remaining network limitation.

## Context and Orientation

The repository is `AlekseyBeketov/video-briefing`; its working directory is `/Users/alexbeketov/video-briefing`, and its default branch is `main`. The Python package metadata in `pyproject.toml` declares package version `0.2.0`, Python `>=3.11,<3.15`, the `video-briefing` CLI, and the optional `video-briefing-mcp` executable. CI covers Python 3.11–3.14 on Ubuntu. This is not evidence that every operating system is supported.

`src/video_briefing/cli.py` defines the CLI. `src/video_briefing/mcp_server.py` implements MCP stdio and tool names. MCP means the Model Context Protocol used by an agent host to launch a local program and call its declared tools. YouTube ingestion defaults to timed captions; the normal CLI and MCP evidence tools do not call an LLM. The MCP tools are `ingest_youtube`, `ingest_local_mp4`, `search_video_evidence`, `read_video_evidence`, and `validate_video_claims`. A read-only profile uses the last three tools. Optional model-generated `brief` and `ask` are separate and may require `--allow-cloud` when the selected model endpoint is cloud-backed or not loopback.

`README.md` is currently Russian-only and contains an example wheel filename that does not exist in the checkout. The actual checkout setup is `uv sync --frozen`; MCP development/use from the checkout requires `uv sync --frozen --extra mcp`. These commands may access PyPI and create/update the target environment. The checked-in lock file is `uv.lock`. Do not run a sync against a user's existing `.venv` to validate this documentation; use a dedicated disposable environment or existing prepared environment.

The public/setup files to add are `README.ru.md`, `docs/agent-prompts/hermes.md`, `docs/agent-prompts/codex.md`, and `docs/agent-prompts/claude-code.md`. The common page is `docs/agent-integration.md`. The package resource files `skills/video-briefing/SKILL.md`, `prompts/brief.md`, and `prompts/qa.md` intentionally have byte-identical copies under `src/video_briefing/resources/`. A new `tests/test_resource_parity.py` should fail if any pair drifts.

The maintained architecture and decision pages are `docs/design.md` and `docs/pending-decisions.md`. `docs/plans/2026-10-05-video-briefing.md` is an old planning record and should receive a short historical/superseded notice, while dated research and reports remain immutable. The repository has no `LICENSE`; documentation must say that reuse/distribution terms have not been specified and must not claim an open-source license.

Official client guidance reviewed for the agent pages:

- Codex CLI MCP: <https://developers.openai.com/codex/mcp>
- Codex CLI: <https://developers.openai.com/codex/cli>
- Claude Code MCP: <https://code.claude.com/docs/en/mcp>
- Claude Code setup: <https://code.claude.com/docs/en/setup>
- Hermes MCP guide: <https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp>
- Hermes MCP config reference: <https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference/>
- `uv` installation: <https://docs.astral.sh/uv/getting-started/installation/>
- Python downloads: <https://www.python.org/downloads/>

## Plan of Work

First add this plan as its own commit and push it to `origin/main`. Then write `README.md` and `README.ru.md` from the observed CLI/package behavior. Both files must match on supported Python versions, setup, useful commands, MCP names, privacy boundaries, the lack of a license, and known limits. Keep language navigation links at the top. Include one safe YouTube example using a placeholder ID, one cached search/read example, and a local MP4 example clearly labelled as requiring separately installed local ASR dependencies. Mention that actual captions/network access may fail and that a doctor check does not test network access.

Rewrite `docs/agent-integration.md` to remove the hardcoded wheel assumption and obsolete Hermes field. Explain the current source checkout install (`uv sync --frozen --extra mcp`) and the executable/configuration model. Document tool names and the distinction between read-only and ingestion permissions. Include a privacy note that tool output may be sent to the calling agent's model. Link to the three client pages.

Create one page per supported client. Each page must name the official setup reference, provide a ready-to-copy English prompt, and show the relevant configuration shape based on current official docs. A prompt must first inspect prerequisites and the project README, verify the exact project remote, choose a new unique clone and isolated project environment, install only through project instructions, and run `video-briefing --version`, `video-briefing doctor`, MCP executable checks, and the client-specific MCP connection/tool-catalog check. It must never overwrite existing config/skill/clone files, reveal secrets, read browser cookies, install global system packages, make cloud calls without opt-in, ingest private media, or broaden permissions silently. On conflicts or any destructive step, stop and ask. If the client or live source cannot be tested, report the precise missing test instead of claiming success. State that these prompts were not run end-to-end in the authoring environment.

Update `docs/design.md` only where confirmed claims conflict with the current source-first behavior. Correct the user-facing result and pipeline so a reader does not infer automatic model generation as the default, remove obsolete implementation requirements that no longer describe the product, and retain still-valid constraints. Update `docs/pending-decisions.md` to list at least the unresolved license choice and supported-platform policy; do not answer either on the user's behalf. Add a short banner to the old 2026-10-05 plan that it is historical and superseded for current setup, preserving its contents below. Do not change reports, `docs/research/`, rubrics, or pre-existing dirty files.

Add `tests/test_resource_parity.py` using `importlib.resources.files("video_briefing.resources")` and paths relative to the repository root. For `SKILL.md`, `brief.md`, and `qa.md`, assert that the resource bytes equal their tracked counterparts in `skills/video-briefing/` or `prompts/`. Run the new test first and verify it passes; an intentional temporary mismatch may be used only in a temporary copy if a red-phase demonstration is needed. Do not edit the duplicate content just to force a red test.

Finally check all repository-relative Markdown links and exact shell command names against files, CLI help, and the available environment. Check external official links reviewed above. Run the parity test, full available pytest suite, Ruff, `git diff --check`, and the relevant safe CLI checks. If a dependency or network block prevents a check, record its exact output and environment condition. Review the final staged diff to make sure only approved documentation, test, and plan files are included. Commit each coherent change explicitly and push each commit to `origin/main` after confirming `main` is a fast-forward of the remote.

## Concrete Steps

All commands run from `/Users/alexbeketov/video-briefing`. Follow the repository instruction to invoke commands through `rtk`. Never stage the pre-existing modified `reports/production-acceptance.md`, untracked `.codegraph/`, or untracked research/report artifacts.

1. Confirm the current commit and remote tracking state, then stage and commit only this plan:

       rtk git status --short --branch
       rtk git add docs/plans/2026-10-14-public-docs.md
       rtk git diff --cached --check
       rtk git commit -m "docs: plan public setup documentation"
       rtk git push origin main

   Expected result: the plan appears in the commit; user files remain unstaged. A successful push reports `main -> main`.

2. Edit English and Russian README pages and the common agent integration guide. Review every claimed command against `pyproject.toml`, `src/video_briefing/cli.py`, and `rtk env UV_CACHE_DIR=/private/tmp/video-briefing-uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/video-briefing-final-py311-env uv run --no-sync video-briefing --help`. Check `uv --version`, `python --version`, and `video-briefing doctor` only in a safe existing or temporary environment. Commit those explicit docs paths and push.

3. Create the three client-specific pages and copyable prompts. For config examples, verify the key/command against the official docs linked in the page; do not add non-documented fields. Check each prompt for a new clone path, non-overwrite behavior, no secret/cookie reads, bounded permissions, health checks, and honest reporting. Commit and push only the three prompt files.

4. Update `docs/design.md`, `docs/pending-decisions.md`, and add the historical note to `docs/plans/2026-10-05-video-briefing.md`. Re-read each diff to ensure historical claims remain attributable to the old plan and unresolved decisions stay unresolved. Commit and push those exact paths.

5. Add `tests/test_resource_parity.py`. From the repository root run:

       rtk env UV_CACHE_DIR=/private/tmp/video-briefing-uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/video-briefing-final-py311-env uv run --no-sync pytest tests/test_resource_parity.py -q

   Expected result: one parity test passes and checks all three pairs. Then run the full suite and Ruff as permitted by the prepared environment:

       rtk env UV_CACHE_DIR=/private/tmp/video-briefing-uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/video-briefing-final-py311-env uv run --no-sync --extra dev --extra mcp pytest
       rtk env UV_CACHE_DIR=/private/tmp/video-briefing-uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/video-briefing-final-py311-env uv run --no-sync --extra dev ruff check .

   Do not retry a network-dependent sync if DNS remains unavailable. If a command reports missing packages, preserve that failure as a limitation rather than modifying the repository `.venv`.

6. Validate documentation and final repository state:

       rtk git diff --check
       rtk git status --short --branch
       rtk git diff --stat
       rtk git diff -- README.md README.ru.md docs/agent-integration.md docs/agent-prompts docs/design.md docs/pending-decisions.md docs/plans/2026-10-05-video-briefing.md tests/test_resource_parity.py

   Manually verify every relative Markdown link resolves, the English and Russian pages provide the same critical facts, no public file claims a license or unsupported feature, and no user artifact or secret was staged. Push each implementation commit and verify local `main` matches the advertised remote tip when connectivity allows.

## Validation and Acceptance

Acceptance is observable when both READMEs link to each other and describe commands present in the current CLI; `video-briefing --help` includes the documented commands; and `video-briefing doctor` reports local dependency availability without implying a network test. MCP instructions use `video-briefing-mcp` and the five current tool names, with a separate read-only profile containing `search_video_evidence`, `read_video_evidence`, and `validate_video_claims`.

Each client page must include the official documentation link, an English prompt, configuration guidance that agrees with that source, safety stop conditions, explicit runtime checks, and the honest statement that it was not end-to-end tested in the actual client here. The Hermes example must not contain the unsupported `sampling` key. No prompt may say it has installed or connected successfully before reporting command output that proves it.

The parity test must pass for all three source/package pairs. The available full test suite and Ruff should pass if the prepared Python environment has the locked dev/MCP dependencies. `git diff --check` must pass. A failed network install is not a test pass; record the DNS/PyPI reason separately. No claim is made that Codex, Hermes, or Claude Code client setup was end-to-end tested by this implementation.

## Idempotence and Recovery

Documentation edits are additive except for replacing stale prose in explicitly listed maintained files. The old historical plan is preserved beneath its banner. The package copies are kept intentionally and the parity test prevents future drift. A failed test or formatting check should be fixed in its own scoped files, then the same checks rerun.

Before each commit, use explicit file paths with `git add`; never use `git add -A` because the working tree contains pre-existing reports and `.codegraph/` artifacts. If push fails due DNS or authentication, keep the local commit intact, report that exact reason, and retry only when connectivity is available. If `origin/main` has advanced, fetch and inspect before integrating; do not force push or rewrite remote history.

## Artifacts and Notes

Repository and package facts confirmed during planning:

    name: video-briefing
    version: 0.2.0
    python: >=3.11,<3.15
    CI: Python 3.11–3.14 on Ubuntu
    checkout install: uv sync --frozen
    MCP checkout install: uv sync --frozen --extra mcp
    primary CLI: video-briefing
    MCP executable: video-briefing-mcp

Baseline verification: `--help`, `--version` (`0.2.0`), `doctor`, `skill`, and Codex CLI MCP help succeeded in the previously prepared Python 3.11/Codex environment. A fresh package sync failed because sandbox DNS could not resolve PyPI. The exact prompts are not end-to-end tested with client applications in this environment.

## Interfaces and Dependencies

Keep the existing CLI, MCP server, package metadata, and agent integration contract unchanged. Documentation may describe only behavior exposed by `src/video_briefing/cli.py`, `src/video_briefing/mcp_server.py`, and package resources. Do not add runtime dependencies for documentation or parity coverage.

The parity test should expose one test function in `tests/test_resource_parity.py` and compare raw bytes for these mappings:

    skills/video-briefing/SKILL.md <-> video_briefing.resources/SKILL.md
    prompts/brief.md              <-> video_briefing.resources/brief.md
    prompts/qa.md                 <-> video_briefing.resources/qa.md

Markdown paths are relative to the repository root. Agent executable/config examples must follow each linked official client guide and the existing server's stdio contract. Configuration shown for a client must not claim that the project automatically edits that client's configuration.

Plan history: created on 2026-10-14 after the user approved the recommended documentation scope. The worktree had existing unrelated report and indexing artifacts before this plan was added; all implementation commits must use explicit paths.
