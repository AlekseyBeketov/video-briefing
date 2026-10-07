# OpenResearch: read-only discovered contract

Discovery only in research preflight, 2026-10-05 UTC. No project import, run, SQLite edit, new daemon, or agent.

## Observed installation and live service

- Executable `/Users/alexbeketov/.cargo/bin/orx`, `orx --version` -> **0.2.15**. Body/design version0.2.13 is not the current CLI observation. Existing daemon was not restarted; don't assume its binary version solely from current CLI.
- `GET http://127.0.0.1:4791/api/projects` -> HTTP200, `{"projects":[]}`.
- Saved `data/reference/orx-project-path-status.json` -> exists/directory true, gitState ready, resolvedPath `/Users/alexbeketov/video-briefing`, githubOwner/githubRepo null, initialized true.
- Endpoint from served UI: `GET /api/project-path/status?path=<URL-encoded-absolute-path>`.
- `orx compute status --json`: defaultBackend local, local enabled/configured. This does not authorize other discovered backends.
- `orx compute instructions show --json`: content empty; no custom compute instructions. Do not write global compute settings.

## Supported local import, discovered from served dashboard

`data/reference/orx-dashboard.js` contains:

    Wyn=e=>xt("/api/projects",e)

`xt` issues JSON POST with content-type application/json. The folder import form constructs name/path/creationMode/createFolder/requireNewFolder/initializeGit/githubSyncEnabled/locale. Observed folder-mode payload, to be submitted ONLY downstream after implementation and method commit:

    {
      "name": "Video Briefing DvSwvJVens8",
      "path": "/Users/alexbeketov/video-briefing",
      "creationMode": "folder",
      "createFolder": false,
      "requireNewFolder": false,
      "initializeGit": true,
      "githubSyncEnabled": false,
      "locale": "en"
    }

`initializeGit:true` is the served form value; checkout already has Git. Downstream must re-check path status and contract before submitting rather than invent a different endpoint or initialize a new repository. Folder mode has no paperId/cloneUrl and no GitHub sync. Form consumes response `.project` and `.githubPublicationError`; require no publication error and read back the exact registered ID/path.

Readback available from discovered API: GET `/api/projects`, locate response project by exact returned ID and verify path/Git/publication state; `orx project view <project-id>` reads the exact target. A dedicated GET `/api/projects/<id>` contract was not established here: do not assume it exists. Experiment/read evidence endpoints observed: GET `/api/projects/<id>/experiments`, GET `/api/projects/<id>/runs`, GET `/api/runs/<run-id>/log?offset=<offset>`.

Import body and API discovery are evidence, not an executed import. Served script URL from saved dashboard HTML: `http://127.0.0.1:4791/assets/index-CUlsDMzd.js`. Saved `orx-dashboard.js` SHA256: `8ce67f6dcf0092e87f08071baf23c481ba4c7dcd58a2955553d8cc056b7934ad`. If daemon/UI changes, re-read served source or primary handler schema before state changes.

## Formal immutable local run contract

Authoritative installed read-only commands exercised:

    orx skill orx-create
    orx skill orx-compute
    orx skill orx-git
    orx skill orx-evidence
    orx skill compute/local

1. Import existing Git checkout via supported HTTP/UI, verify returned project. Commit evaluation/protocol/actual harness with explicit owned paths, no raw source/media. No remote/push required.
2. Establish ACTUAL run command from final manifest once:

       orx project edit <project-id> --run-command '<fixed actual command>'

   A hypothetical Python module command in design is not a tested executable contract. Do not run until actual implementation entrypoint/uv.lock/tools/model paths exist.
3. First `orx create-experiment <project-id> --title ...` is baseline root. Create co-equal variant children with `--parent <root-experiment-id>` and hypothesis descriptions; maximum3 variants. Later parentless nodes implicitly attach to oldest root unless `--baseline` asks another root.
4. Per node only committed config selects backend/cache mode. Command and environment remain byte-for-byte equivalent across nodes. Code/config editing uses a separately owned worktree, never switches shared main. Commit before launch; runner extracts immutable archive of recorded branch commit. Untracked `.tools/.venv/data` do not travel with it.
5. Fixed paths to tools/evidence/model must be deliberately available from snapshot and same environment; no different command/env per variant. Package install/setup and upstream cache state measured separately.
6. Only formal launch:

       orx exp run <experiment-id> --backend local

   Local backend starts detached run and supervise process; no flavor/host/image/timeout flags. Run evidence under `<orx data dir>/local-runs/<run-id>/`. Do not substitute direct bench invocation for tracked experiment.
7. `orx exp wait <experiment-id>` -> after any return reconcile `orx runs <project-id>`, inspect `orx logs <run-id>` then relevant FULL persisted logs/artifacts. Status/compact preview alone isn't result. `wait --timeout` is wait timeout, not local job timeout.
8. Freeze nodes that have answered; no edits/merge/rebase of answered branch. At most2 answerless repairs then blocker. New hypothesis -> child. Run evidence must identify real variant/settings/model/prompt/source hashes, wall timings, artifacts and commit.

No formal project IDs, experiment IDs or run IDs yet. Existing daemon reuse is mandatory; no `orx agent`, no nested coding sessions and no direct DB modifications.
