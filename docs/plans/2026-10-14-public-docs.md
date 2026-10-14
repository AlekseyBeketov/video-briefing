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
- [x] (2026-10-14) Commit this implementation plan as `f146066`; correct its Hermes sampling note in `07c68c8` after checking the current official reference.
- [x] (2026-10-14) Draft an English README and a Russian counterpart; command and claim review remains in final validation.
- [x] (2026-10-14) Draft shared MCP guidance and separate English copyable prompts for Hermes, Codex CLI, and Claude Code; client E2E runs remain unavailable.
- [x] (2026-10-14) Correct the stale skill setup instructions in both tracked copies and align architecture, pending-decision, and historical-plan text.
- [x] (2026-10-14) Add a parameterized test for byte parity of the three packaged Markdown resources; focused and full test runs remain.
- [x] (2026-10-14) Verify 11 changed documentation files' relative links, CLI help/doctor claims, and the packaged wheel's three resource files.
- [x] (2026-10-14) Run parity tests (3 passed), full pytest suite (187 passed), Ruff, offline wheel/sdist build, and `git diff --check`.
- [x] (2026-10-14) Review exact paths, commit each documentation group, and push all implementation commits to `origin/main`.
- [x] (2026-10-14) Repeat full pytest, Ruff, offline build, CLI doctor, relative-link checks, and final Git/remote review.

## Surprises & Discoveries

- Observation: The current README and integration guide describe installing a wheel, but the repository does not contain a wheel or publish an install artifact from this checkout. The integration guide hardcodes version `0.2.0`. Current Hermes documentation supports `sampling.enabled: false`; keeping it explicitly disables host model sampling for this server.
  Evidence: `README.md`, `docs/agent-integration.md`, [Hermes sampling guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp), and [MCP config reference](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference/).
- Observation: Three copies are deliberate: `skills/video-briefing/SKILL.md` and `prompts/{brief,qa}.md` are mirrored under `src/video_briefing/resources/` so the package can ship and print them. The skill copies have matched SHA-256 `cc15ea039194aa1bc3c13d3b1d692da98973811a0ba38c876d68b338540d02c4` in the baseline.
  Evidence: `video-briefing skill` output and byte comparison of repository and packaged files.
- Observation: `video-briefing --help` shows that normal source/evidence work is separate from optional model-generated `brief` and `ask`; these optional commands require an explicit privacy opt-in for cloud-backed endpoints.
  Evidence: the local Python 3.11 CLI printed the commands `doctor`, `extract`, `ingest`, `search`, `read`, `skill`, `brief`, `ask`, and `benchmark`.
- Observation: A fresh dependency sync could not reach PyPI because DNS resolution failed in the sandbox. Hermes cannot write its install state in this environment, and Claude Code is not installed. Client-specific prompts therefore cannot be declared end-to-end tested here.
  Evidence: `uv sync` failed resolving `pypi.org`; Hermes reported a locked install-state path; `claude` was not found. The installed Codex CLI's `codex mcp --help` succeeded.
- Observation: Rechecking the current Hermes documentation corrected the earlier design assumption: `sampling` is a supported key and sampling defaults to enabled, while `sampling.enabled: false` is a documented way to disable it per server.
  Evidence: official Hermes MCP guide section “MCP Sampling Support” and MCP Config Reference list `sampling` as a supported mapping (checked 2026-10-14).
- Observation: The portable source skill still instructed users to install a wheel named with a version placeholder and claimed the package had no checkout-path dependency, which contradicted the actual tracked installation guidance.
  Evidence: `skills/video-briefing/SKILL.md` and its byte-identical package resource before this change; checkout setup in `README.md` and `pyproject.toml`.
- Observation: The skill compatibility launcher also returned a user-facing message that specifically required a wheel, although its actual runtime contract is only that the CLI be on `PATH`.
  Evidence: `skills/video-briefing/scripts/video_briefing.py` calls `shutil.which("video-briefing")` and then executes the resolved CLI.

## Decision Log

- Decision: Keep `README.md` in English, add a parallel Russian README, and put common agent safety guidance in `docs/agent-integration.md` with three separate prompts.
  Rationale: This gives both language audiences a stable entry point and lets users copy the prompt matching their client without confusing the clients' different configuration models.
  Date/Author: 2026-10-14 / user-approved design.
- Decision: Use a fresh project clone and isolated project environment for prompt-driven setup; never overwrite an existing clone, skill, or agent config. On a name/path conflict, stop and ask. Do not read or print secrets, cookies, or unrelated config values.
  Rationale: `uv sync` acts on the current project's environment and may remove extraneous packages there; a dedicated non-existing clone path bounds that effect and makes the installed MCP command stable.
  Date/Author: 2026-10-14 / user-approved design.
- Decision: Preserve `sampling.enabled: false` in the Hermes config example because it is officially supported and opts out of server-initiated model inference.
  Rationale: Video Briefing's MCP server does not use MCP sampling, so denying that capability follows least privilege without inventing a product feature.
  Date/Author: 2026-10-14 / official Hermes documentation rechecked.
- Decision: Update both portable skill copies to describe source checkout installation and the stable project environment instead of a placeholder wheel install.
  Rationale: The current repository provides no wheel in its checkout, while `uv sync --frozen` and the optional MCP extra are the verifiable installation path.
  Date/Author: 2026-10-14 / current project metadata and CLI.
- Decision: Change the skill wrapper's missing-CLI message to direct users to the README and the actual PATH requirement.
  Rationale: The old message incorrectly implied that the wrapper itself required or installed a wheel; its code only looks up the executable.
  Date/Author: 2026-10-14 / launcher source.
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

Implemented English and Russian READMEs, shared MCP setup guidance, copyable prompts for Hermes/Codex CLI/Claude Code, synchronized portable/package skill instructions, a package-resource parity test, current source-first architecture and pending-decision notes, and a historical banner for the superseded 2026-10-05 plan. The wrapper's missing-CLI message now matches its actual PATH lookup. Existing research records, reports, rubrics, and pre-existing user modifications were left untouched.

The final checks returned 187 passing tests, `All checks passed!` from Ruff, a successful offline source-distribution and wheel build, a successful `video-briefing doctor`, and resolved relative links in 13 checked Markdown files. The built wheel's `SKILL.md`, `brief.md`, and `qa.md` exactly match the repository resource copies. The planned commits `4c72895`, `f146066`, `07c68c8`, `af7857d`, `4a35e4f`, and `a7b0e01` were pushed in order to `origin/main`.

The agent prompts remain explicitly unverified end-to-end in their respective clients: Hermes could not write its install state, Claude Code was absent, and Codex CLI help alone does not prove a client connection. A fresh dependency sync could not resolve PyPI because sandbox DNS was unavailable; the already-prepared Python 3.11 environment supported the tests and packaging checks. These are verification limits, not claims of successful client setup or fresh-install testing.

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

Rewrite `docs/agent-integration.md` to remove the hardcoded wheel assumption and retain the officially supported Hermes `sampling.enabled: false` safeguard. Explain the current source checkout install (`uv sync --frozen --extra mcp`) and the executable/configuration model. Document tool names and the distinction between read-only and ingestion permissions. Include a privacy note that tool output may be sent to the calling agent's model. Link to the three client pages.

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

   Expected result: three parameterized parity cases pass, one for each source/package pair. Then run the full suite and Ruff as permitted by the prepared environment:

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

Each client page must include the official documentation link, an English prompt, configuration guidance that agrees with that source, safety stop conditions, explicit runtime checks, and the honest statement that it was not end-to-end tested in the actual client here. The Hermes example may set the documented `sampling.enabled: false` field to disable server-requested model inference. No prompt may say it has installed or connected successfully before reporting command output that proves it.

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

Baseline and implementation verification: the existing prepared Python 3.11 environment returned CLI version `0.2.0`; final `doctor` reported `youtube-transcript-api 1.2.4`, `network_probes: false`, and no model inference. Three resource-parity cases passed, the full test suite returned `187 passed`, Ruff returned `All checks passed!`, and the final offline `uv build` produced both an sdist and wheel in `/private/tmp/video-briefing-docs-final-dist`. The built wheel's `SKILL.md`, `brief.md`, and `qa.md` bytes matched the source package resources. Relative links resolved in all 13 checked documentation files. A fresh `uv sync` could not reach PyPI because sandbox DNS failed. Codex CLI MCP help was available; Hermes could not write its install state and Claude Code was absent. Therefore none of the three new prompts was end-to-end tested with its target client.

## Interfaces and Dependencies

Keep the existing CLI, MCP server, package metadata, and agent integration contract unchanged. Documentation may describe only behavior exposed by `src/video_briefing/cli.py`, `src/video_briefing/mcp_server.py`, and package resources. Do not add runtime dependencies for documentation or parity coverage.

The parity test should expose one test function in `tests/test_resource_parity.py` and compare raw bytes for these mappings:

    skills/video-briefing/SKILL.md <-> video_briefing.resources/SKILL.md
    prompts/brief.md              <-> video_briefing.resources/brief.md
    prompts/qa.md                 <-> video_briefing.resources/qa.md

Markdown paths are relative to the repository root. Agent executable/config examples must follow each linked official client guide and the existing server's stdio contract. Configuration shown for a client must not claim that the project automatically edits that client's configuration.

Plan history: created on 2026-10-14 after the user approved the recommended documentation scope. The official Hermes docs were rechecked on 2026-10-14 and corrected an early assumption about the `sampling` field; the supported field is retained as an explicit deny setting. The worktree had existing unrelated report and indexing artifacts before this plan was added; all implementation commits must use explicit paths.
