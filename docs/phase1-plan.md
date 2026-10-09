# Phase 1 plan: Foundation

Proposed 2026-10-09. Phase 1 step 1 of `KICKOFF.md`. It builds on `docs/studio-design.md` (sections "Data model", "Tool layer" and "Implementation"). The PC facts below were checked read-only on 2026-10-09.

## 1. Repo layout after Phase 1

`(n)` = the step that creates it. Anything without a number already exists.

```
C:\claude-video-agent-studio\
  CLAUDE.md                     (2) studio rules, naming, folder layout, approval flow
  .gitattributes                (2) line endings: *.ps1 CRLF, *.py/*.json/*.md LF in the repo
  .gitignore                    (2) extended: .venv, comfy snapshots of outputs, agent scratch
  .mcp.json                     (9) davinci-resolve, project scope
  requirements.txt              (2) studio venv packages (see 3.A)
  .claude\
    settings.json               (2) conservative permissions; hooks wired in (8)
    agents\                     (4) 15 agent files (list in step 4 below)
    hooks\                      (8) PowerShell 5.1 guardrail hooks
    skills\
      gemini-video-review\      (3) ported
      h3-gacha-pipeline\        (3) ported
      resolve-music-video\      (3) ported
      resolve-edit\             (3) ported
      studio-conventions\       (2) IDs, folders, statuses, task envelope, run-ticket flow
      comfy-bridge\             (6) page recipe + shell API + manifest use
      vram-watch\               (7) headroom check, watchdog, restart procedure
  docs\
    studio-design.md, notes\, phase1-plan.md (this file)
  pipeline\
    constants.json              (5) planning constants from the design's measured costs
    schemas\                    (5) JSON Schemas
    comfy\
      manifests\                (6) one per workflow
      profiles\                 (6) default configuration profile per workflow
      snapshots\                (6) graphToPrompt output + UI-file hash per workflow, dated
      bridge\                   (6) comfy_api.py (shell HTTP client), page_recipes.js
    watchdog\                   (7) vram_watch.py, restart_comfyui.ps1, config.json, comfyui_launch.json
    tools\                      otio_keyframe_insert.py (exists); (5) new_project.py, validate.py; (8) ticket.py
    tests\                      (5)(7)(8) schema, watchdog dry-run and hook tests
  templates\
    project\                    (5) 00_admin … 10_wrap with seed files
  projects\                     created per project from the template (Phase 2)
C:\CU\output\studio\<CODE>\units\   ComfyUI writes takes here (created in Phase 2, with your OK)
```

## 2. Files per step

**Step 2: CLAUDE.md and settings**
- `CLAUDE.md`: hard rules (from KICKOFF), the approver rule, naming (IDs from the design's Data model table), folder layout, change tiers, the run-ticket flow, and how to launch the studio.
- `.claude/settings.json`: allow read-only tools, edits inside the repo, and the git read commands. Ask for everything else. Deny `Read` on D: and on the Gemini key file. No `agent` key yet (see 3.C).
- `.claude/skills/studio-conventions/SKILL.md`: the conventions every agent preloads.
- `.gitattributes`, `.gitignore` additions, `requirements.txt`.

**Step 3: port the four skills.** Only the environment parts change; every measured number and rule stays. One diff per skill.
- `h3-gacha-pipeline` §1 and §3: local shell and files on disk; ComfyUI through Claude in Chrome plus the HTTP API from the shell. Studio output paths replace `Reruns/` when the skill runs inside the studio. The claude.ai project-doc references point to `docs/notes/`.
- `resolve-music-video`: remove the "no shell / `.cmd` launcher / `device_commit_files`" section. Point to `pipeline/tools/otio_keyframe_insert.py` and `docs/notes/`. The PC constraints stay.
- `gemini-video-review`: the key comes from `--key-file C:\CU\output\video\geminiapi.txt` with `--no-key-scan`. The scripts run with the studio venv. Paths are local.
- `resolve-edit`: barely changes; add the local install facts (C:\DavinciResolve, the bridge per session).

**Step 4: agents** in `.claude/agents/`: `producer`, `director`, `writer`, `music-timing`, `art-director`, `asset-designer`, `storyboard`, `prompt-writer`, `render-wrangler`, `pipeline-td`, `dailies-qc`, `editor`, `finishing`, `delivery-qc`, `librarian`. Model tier per the org chart. The Producer gets `tools: Agent(<the 14>), Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion`. Specialists get no Agent tool. `memory: project` throughout. Skills are preloaded per the design.

**Step 5: schemas and template**
- `pipeline/schemas/`: `tracker`, `run_ticket`, `task_envelope`, `job_spec`, `qc_report`, `selects`, `edl` (`.schema.json`, draft 2020-12), plus `project` (project.yaml) and `budget`.
- `templates/project/00_admin … 10_wrap`: `tracker.json`, `budget.json`, `notes.md`, `decisions.md`, `run_tickets/`, empty `render_log.jsonl` and `vram_log.jsonl`, and `01_brief/brief.md` and `project.yaml` skeletons.
- `pipeline/tools/new_project.py` (template → `projects/<CODE>`), `pipeline/tools/validate.py` (checks a project against the schemas), and `pipeline/constants.json`.

*Built 2026-10-09:*
- 14 schemas. Beyond the list above: `common` (IDs, timestamps, paths), `policy` (the project definition the user approves), `approval` (hook-written records) and the two log-line formats.
- Run tickets no longer carry `approved_by`. Approval lives only in a hook-written record bound to the ticket's or policy's SHA-256, so editing an approved file voids the approval.
- `new_project.py footage` creates a footage folder only from a matching recorded approval, and only inside `C:\CU\output`.
- `validate.py` adds the cross-file rules the schemas can't express: file names equal IDs, windows are ordered, tickets use only approved templates, per-job policy holds, IDs belong to the project, approvals are not stale, log lines are valid, and no template placeholders are left.
- 47 tests in `pipeline/tests/`.

**Step 6: ComfyUI bridge, read-only.** List the workflows and build the manifest tooling. A project's workflow templates (3.H) are turned into manifests when the project is initialized. Step 6 proves the tooling read-only on H3regenrunsTest, H3ultRefsTest2 and H3regensElements: it opens each in the studio's ComfyUI tab, converts it with graphToPrompt and writes:
- `manifests/<id>.json`: per-job parameters with node IDs and input names, seed node, broadcast inputs to wire, the sol and chunking nodes for H3, outputs, measured costs.
- `profiles/<id>.default.json`: every other value, as you saved it.
- `snapshots/<id>/<date>_<hash>.api.json`.

These three become the first entries in the manifest library. They are not defaults.

*Built 2026-10-09:*
- `bridge/comfy_api.py`: read-only shell client (status, queue, history, wait, logs, progress age, environment pin, pre-job checks). There is no submit command.
- `bridge/page_recipes.js`: `window.studio` in the studio tab (load a saved file, set modes, graphToPrompt, send).
- `bridge/receiver.py`: a loopback receiver, so page output reaches disk without copy-paste.
- `manifest_tool.py`: list, inspect, init (H3 auto-detection), modes, ingest and check.
- `manifest.schema.json`, and `env_pin.json` (ComfyUI 0.37.0, frontend 1.53.6, 119 custom node packs).
- All three manifests pass `check`. The `sol`, `chunked` and `sage` conversions were verified on the real files, and the preview node 152 stays as saved.
- 12 more tests (59 in total).

*Found in step 6:*
- **ComfyUI blocks extension-started navigations.** Its server answers 403 to any request marked `Sec-Fetch-Site: cross-site` (`server.py:162`), which Chrome sets when the extension opens a URL. So the user opens the studio tab once by typing the address. The tab's own `location.reload()` works afterwards. The restart path for unattended windows is designed in step 7, without weakening that protection.
- **The extension forgets its tab group when it reconnects.** It then needs the studio tab opened again.
- **Krea template:** node 13 is saved at 1920×1080. The user decided (2026-10-09) on 2560×1440 for character sheets and 1920×1080 for everything else, so width and height are per-job values. Also, `56:54.switch` is saved wired to `56:50`, and the skill's patch forces it to `false`.
- **Node labels:** ComfyUI reports several packs' nodes as `comfyui-workflow-encrypt`, because that extension re-exports the global node list. It is a labeling quirk; the environment pin goes by folder.

Plus `bridge/comfy_api.py` (status, queue, history, free, outputs, logs; no submit until step 8's check exists), `bridge/page_recipes.js` and `skills/comfy-bridge/SKILL.md`. Nothing is queued.

**Step 7: watchdog and restart**
- `pipeline/watchdog/vram_watch.py`: headroom check, halt detection, VRAM log. `--dry-run` simulates halts from recorded inputs and never touches a process.
- `restart_comfyui.ps1`: `-DryRun` prints the PIDs it would end and the command it would run.
- `config.json` (5-minute progress timeout, 2-minute API timeout, 15 s wait, 3-minute start timeout, two restarts per window) and `comfyui_launch.json` (exact launcher path and arguments).
- `skills/vram-watch/SKILL.md` and dry-run tests.

*Built 2026-10-09:*
- `vram_watch.py` has four commands: `headroom`, `launch-check`, `watch` (real only inside an approved, open window; `--dry-run` never ends or starts a process) and `simulate` (six scripted scenarios).
- `restart_comfyui.ps1 -DryRun` lists the exact processes a restart would end, and the relaunch command.
- `config.json`, plus `comfyui_launch.json` recording `C:\Users\david\Desktop\ComfyUI.bat`, its arguments and the observed process tree.
- `studio_lib.approved_window()`, which step 8's hooks reuse.
- The vram-watch skill, and 15 more tests (74 in total).

*Dry runs on 2026-10-09:*
- The launch check passes.
- Headroom: 27.9 GB free, so a 24 GB peak passes and a 30 GB peak is refused.
- One minute of live watching ended cleanly at the window's end.
- The restart dry run found exactly `cmd.exe /c ComfyUI.bat` → venv python → `Python312\python.exe` on 8188.

*Decisions made in step 7 (proposed defaults, tunable in `config.json`):*
- **No first step:** a job without its first sampler step after 10 min counts as halted, because model load and text encode print no progress lines.
- **Memory released:** means total GPU use below 8 GB, because Windows reports no per-process VRAM. Idle use was 3.6 GB.
- **Unmeasured configurations:** need 26 GB free until their peak is recorded.
- **Relaunch:** ComfyUI is relaunched through `explorer.exe`, like a double-click, so it doesn't belong to Claude Code's processes and can't be closed with them.

*The studio tab after a restart:*
- The page reloads itself (`location.reload()`) once the API answers. That reload is not cross-site, so ComfyUI's 403 check doesn't apply.
- If the tab ever shows an error page, the window ends and the user reopens the tab.
- ComfyUI's protection stays on.

*Still to do:* the live restart test (close, wait 15 s, reopen, API answers), in a window the user approves, with no job running.

**Step 8: guardrail hooks** in `.claude/hooks/`:
- `guard-paths.ps1`: blocks any D: path and any write outside the allowed roots. Write and Edit are blocked exactly. Bash and PowerShell commands are checked best-effort for redirections and file cmdlets.
- `guard-comfy-submit.ps1`: blocks `/api/prompt` POSTs from the shell or the Chrome JavaScript tool without an approved ticket whose window is open.
- `guard-secrets.ps1`: blocks reading or printing the Gemini key file.
- `record-approval.ps1`: see 3.F.
- `pipeline/tools/ticket.py`: create a proposed ticket, check whether a window is open.
- Hook tests.

*Built 2026-10-10:*
- **`guard.ps1`** (PreToolUse on Write, Edit, NotebookEdit, MultiEdit, Bash, PowerShell and both browsers' JavaScript tools) blocks:
  - the failing drive;
  - writes outside the repo, an approved footage folder, the scratch folder and the memory folder;
  - Gemini key and `.env` reads;
  - approval writes;
  - studio agents changing guardrail files;
  - unmarked or unapproved ComfyUI submits, submits while the queue is busy, and submits by agents other than the Render Wrangler and the Pipeline TD;
  - interrupting ComfyUI or clearing its queue or history;
  - running the restart script for real, or killing ComfyUI;
  - the terminal approval command.

  It takes about 0.27 s per call. Read, Glob and Grep are not hooked; the settings' deny rules already cover the failing drive and the key files for them.
- **`record-approval.ps1`** (PostToolUse on AskUserQuestion) records approved or rejected answers, only for marked questions, bound to the file's SHA-256. A previous record moves to `history/`.
- **`ticket.py`** has `marker`, `summary`, `status`, and `approve` (the user's terminal fallback, which refuses without an interactive terminal).
- The approval schema now also accepts `recorded_by: user:terminal`.
- 61 more tests (135 in total). `test_hooks.py` runs the real PowerShell hooks.

*Live checks in this session (the hooks hot-load from settings):*
- The guard blocked a probe naming the restart script.
- Approving a throwaway test ticket, whose window had already ended, produced a valid record bound to the ticket. The test project was then deleted.
- Claude Code 2.1.296 puts the answers in both `tool_input.answers` and `tool_response.answers`, keyed by the question text.
- Hooks also run in bypass-permissions mode.
- Without `--agent`, the payload has no `agent_type`. The guardrail-file and submitter checks therefore apply to studio agents only, and the build session can still edit the hooks.

*Limits, stated plainly:*
- Shell commands are checked by pattern, so a script that writes through an indirect path (for example a Python file that builds the path at run time) can slip past. File tools are exact.
- Pattern checks also give false positives: a command whose text merely mentions the failing drive's letter followed by a colon, or names the approvals folder next to a writer such as Python, is blocked. Write such text to a file with a file tool instead.
- A click on ComfyUI's Queue button through the browser's computer tool can't be told apart from other clicks. Agents are instructed to queue only by script.
- Opening an existing Resolve project through the MCP is not hooked yet. It is a candidate for step 9.

**Step 9: Resolve MCP.** `.mcp.json` with the `davinci-resolve` command and env copied from Claude Desktop's config, including `RESOLVE_SCRIPT_LIB=C:\DavinciResolve\fusionscript.dll`. Then verify with `resolve_control get_version` in a new throwaway project that you open.

*Built and verified 2026-10-10:*
- `.mcp.json` has the same command and env as Claude Desktop's config. `claude mcp get davinci-resolve` shows it at project scope, "pending approval" until the user approves it on the first `claude` run in this folder.
- The guard enforces rule 7: the studio creates or loads only `STUDIO_<...>` projects, and every other Resolve call needs one created or loaded in the same session.
- The user opened a new test project `STUDIO_TEST_20261010` and ran the bridge.
  - `resolve_control get_version` answered: Resolve 21.0.4.5, MCP 4.8.22. The 25 surfaces absent on this build are all 21.1 additions.
  - `project_manager get_current` named the test project.
  - A `timeline list` call was blocked by the guard live, because no `STUDIO_` project had been created or loaded through the MCP in the session.
- The MCP reports an available update to 4.10.3, which was not applied; updating is the user's decision.
- The test project stays in Resolve. The studio never deletes projects, so the user can delete it whenever they like.

## 3. What does not fit this PC, and what I propose

**A. Python.** `python` on PATH is the Microsoft Store alias, and there is no `py` launcher. `C:\Program Files\Python312` (3.12.10) has no packages. ComfyUI's venv (`C:\CUVenv`) has most of what the studio needs, but installing into it could break ComfyUI.
*Approved 2026-10-09:* ComfyUI.bat keeps using its own venv, and the studio gets a separate one: a studio venv at `.venv` in the repo, built from `C:\Program Files\Python312`, installed from PyPI. Phase 1 needs only light packages: jsonschema, pyyaml, requests, websocket-client, psutil, nvidia-ml-py and opentimelineio. The media stack (numpy, opencv-python, scenedetect, librosa, onnxruntime, Pillow, soundfile) is installed when Phase 2 first needs it. Installing needs your OK, because it downloads packages.

**B. Shell.** Only Windows PowerShell 5.1 is installed (no pwsh 7), so the hooks use 5.1 syntax. Each hook call costs roughly 0.3–0.5 s of PowerShell start-up per matched tool call.

**C. Running the session as the Producer.** Claude Code 2.1.296 is at `C:\Users\david\.local\bin\claude.exe` and supports `--agent` and `--chrome`, plus an `agent` setting.
- Phase 1 is built in a normal session. Setting `agent: producer` in the shared `settings.json` now would turn this build session into the Producer, which by design cannot write code.
- *Proposal:* the studio is launched with `claude --agent producer --chrome`, or with `"agent": "producer"` in `.claude/settings.local.json` for the Desktop app, once Phase 1 is done.

**D. Reloading your ComfyUI tab.** The working recipe (openWorkflow, then reload the page) changes what your tab shows, and it can drop unsaved edits in an open workflow.
*Approved 2026-10-09:* the studio opens its own ComfyUI tab in Chrome, which is the same server and the same queue that you see. Before any reload it checks for unsaved workflows and stops if there are any.

**E. Jobs run in the browser; the watchdog follows the console log.** You need to watch each job's progress and its preview node in ComfyUI. ComfyUI sends `progress`, preview and `executed` messages only to the websocket of the client that queued the job (`main.py:448`, `execution.py:737`). Connecting with the browser's clientId would replace your tab's socket (`server.py:281`).
*Decided (2026-10-09):*
- Every job is queued from the browser tab with that tab's own client ID, as in the current recipe. That tab shows the progress bar and the preview node exactly as when you queue by hand.
- The watchdog never queues. It follows ComfyUI's console log, which is the feed behind ComfyUI's terminal panel:
  - it subscribes over its own websocket (`PATCH /internal/logs/subscribe`), with `/internal/logs/raw` as a polling fallback;
  - every entry is timestamped, and the sampler's step counter is in it (`app/logger.py` keeps `\r` progress updates);
  - it also reads `/api/queue`, `/api/history` and nvidia-smi.
- Checked read-only in step 7; the live test waits for an approved window.

**E2. ComfyUI updates.** You use ComfyUI outside the studio too, and you will update it. Two things the studio relies on are internal to ComfyUI and can change in any update: the `/internal/logs` feed that the watchdog reads, and the page functions used to open and convert workflows (`openWorkflow`, `graphToPrompt`).
*Proposal:*
- The studio records the ComfyUI version it was tested with (0.37.0 on 2026-10-09).
- Before any studio job, the bridge compares that version, and it runs read-only checks on any change: the log feed shows sampler steps, each workflow converts, and the manifest node IDs still match.
- If a check fails, nothing is queued and you get a report of what broke. An update can stop the studio, but it can never leave a job running unwatched.

**F. Approval policy (decided 2026-10-09).**
- You define the approval process for each project when the project is defined. The Producer's intake interview always asks; it never assumes.
- Your answer is recorded as the project's approval policy, the same unforgeable way as an approval (F2). Agents cannot write or change it.
- Until a project's policy is recorded, the strictest rule applies: nothing is queued without an approved ticket, stills included.
- The intake offers the answers you gave on 2026-10-09 as a starting point, which you can change per project:
- **H3:** you approve a batch of jobs plus a time window (the design's run ticket).
- **H3 retakes inside an approved batch:** the studio may retake a failed unit once, changing one variable (new seed, or one wording change). It does so only while the ticket's GPU-minute cap and window still hold. Every retake appears in the end-of-window report. Anything beyond that becomes a retake request, as in the design.
- **Krea stills (sheets and keyframes):**
  - No approval is needed. This changes KICKOFF's hard rule for stills only; H3 and every other workflow still need a ticket.
  - Each still may be retaken up to 3 times when its details are off.
  - After each retake, the candidates are shown to you to choose from, and generation continues meanwhile. If you haven't chosen by the time a later task needs the still, the agent chooses (the Asset Designer, with the Director for hero characters). Your later choice still replaces the agent's choice, up to the point where an H3 unit has used that still; after that, a change is a Tier 4 change.
  - *Safety rule for stills,* asked at intake with the policy, because you also use ComfyUI yourself: a still is queued only when ComfyUI's queue is empty and no H3 job is running. Stills are queued one at a time, so your own jobs wait at most one still (about 35 s). Outside an approved window the watchdog never restarts ComfyUI; it stops and tells you.
- **Enforcement:** the submit hook reads the project's recorded policy. Under the starting-point policy, it allows a job without a ticket only when it comes from a workflow whose manifest is marked as a still (H3regensElements today). A prompt that contains an H3 node, or that comes from any unmarked workflow, needs an approved ticket with an open window.

**F2. Recording an approval so it can't be forged.** If the run-ticket check only reads a JSON file, an agent could write "approved" itself.
*Proposal (how decision 2 is enforced):* approvals and the project's approval policy come only from your answers in chat. The Producer asks with a question that names the ticket and the window. A `PostToolUse` hook records your answer to `00_admin/approvals/` (`policy.json` and `R-###.json`). A `PreToolUse` hook blocks every agent write to that folder. The submit hook, the bridge and the watchdog all trust only those records plus the clock.
*Fallback,* if the Desktop app doesn't pass answers to hooks: you run one approve command in your own terminal.

**G. Write allowlist.** The design allows writes only to the repo and `C:\CU\output\studio`. The studio folder is replaced by each project's footage folder (G2). That would also block Claude Code's own scratch folder (`%TEMP%\claude\…`) and this project's memory folder (`~\.claude\projects\C--claude-video-agent-studio\memory`).
*Approved 2026-10-09:* allow those two as well. The hooks also guard the Gemini key file, which the KICKOFF rules require but step 8 doesn't list.

**G2. A footage folder per project (decided 2026-10-09).**
- Every project, a rerun batch included, gets its own footage folder for everything ComfyUI renders for it: H3 takes and Krea stills.
- When the project is defined, the Producer asks you where to create it, and creates it only after you answer. The answer is recorded with the project's policy (F2), so no agent can redirect writes. The allowed write roots are then: the repo, each project's recorded footage folder, Claude Code's scratch folder and this project's memory folder.
- *Constraint:* the folder must be inside `C:\CU\output`, because ComfyUI refuses to save anywhere else (`folder_paths.py:552`, "Saving image outside the output folder is not allowed"). ComfyUI.bat doesn't change the output directory. Never on D:. `C:\CU\output\studio\<CODE>` is offered as the suggestion.
- Layout inside it: `units/<TAKE>/` for H3 takes (with the prompt beside each take), `stills/<ID>/` for Krea sheets and keyframes.

**H. Workflows (decided 2026-10-09, revised the same day; see the end of this section).** All three named workflows are present (last saved 5 Oct). Newer H3 workflows exist too: H3ultRefsTest3, H3ultSingleRef, H3ultSingleRefSparse, H3ult_Solenne_v3–v5 and H3ult_Xiaoyu_v1–v3.

What a manifest is: for one saved workflow, it lists which values the studio may change per job (prompt, reference images, seed, duration, output path) and declares every other value to be yours. It also records how long the configuration takes and how much VRAM it needs. Only workflows with a manifest can be used by the studio.

The newer files compared with H3ultRefsTest2 (a read-only diff of node modes and values):

| Workflow | Differs from H3ultRefsTest2 in | Is it a new configuration? |
| --- | --- | --- |
| H3ultRefsTest3 | duration 7 s, other reference images, output path | No: same configuration, different per-job values |
| H3ultSingleRef | 1 reference (235/236 removed), 12 s | Only the reference count |
| H3ultSingleRefSparse | 1 reference, 14 s, BlockSparseAttention (sol-attn) on, LowVRAM attention and chunked feed-forward off | Yes: a different memory/attention setup |
| H3ult_Solenne_v5 | as SingleRefSparse, plus the pruned int8 model (`minimax_h3_fl2va_pruned_int8_convrot`), 1.4 MP, 16 s | Yes: another model file and resolution |
| H3ult_Xiaoyu_v3_textcats | as Solenne_v5, plus one more VRAM_Debug (237) | Same as Solenne_v5 |

The three named workflows also differ from each other in their memory setup: H3regenrunsTest runs with the Sage patches (153 and 159 on), and H3ultRefsTest2 with kitchen attention, chunked feed-forward and LowVRAM attention. Both have the live preview node (152 ModelPreviewOverrideKJ with taeh3), which is what you watch.

Points for you:
- The newest setup turns BlockSparseAttention (sol-attn) on. Standing rule 1 in h3-gacha-pipeline says not to use sol-attn for high-motion work. Which one is current?
- The newest setup has no measured time or VRAM peak in the docs. Today's ComfyUI logs show two runs with the pruned model (17:40 and 17:45). Neither finished: the first was interrupted, and the second log stops after the model load, before ComfyUI was restarted at 18:00.
- A manifest is per configuration, not per file: the H3ultRefsTest3 and SingleRef files would be jobs on an existing manifest, not new workflows.
*Decided 2026-10-09 (revised):*
- There are **no global default workflows**. For each project you name the workflow templates it uses: saved ComfyUI workflows, e.g. one Krea template for stills and one or more H3 templates.
- If none are named when the project is initialized, the Producer prompts you to define them. Nothing is queued for a project without templates.
- At project initialization the Pipeline TD makes a manifest and a default profile from each template, as you last saved it, and keeps them in the manifest library (`pipeline/comfy/manifests/`) for reuse.
- A new template is marked unmeasured until a smoke test in an approved window measures it.
- You can change a project's templates, or request any value change, at any time. A change shows as a diff against the template's default profile in the next run request.

**H2. Attention profile for H3 (decided 2026-10-09).** sol-attn is the default for every H3 job, for speed. It applies to H3 video generation only, never to Krea. This replaces standing rule 1 in h3-gacha-pipeline ("no sol-attn for high-motion work"); step 3 updates the skill.
- All H3 workflows share one model chain with the same node IDs: 127 UNET → 152 preview → 187 kitchen attention → 159 Sage KJ → 158 chunked feed-forward → 155 LowVRAM attention → 153 memory-efficient Sage → 154 LoRA → 190 BlockSparseAttention → 193 → sampler. A profile is a set of node modes there:

| Profile | On | Bypassed | Matches |
| --- | --- | --- | --- |
| `sol` (default) | 187, 190 | 153, 155, 158, 159 | H3ultSingleRefSparse as you saved it |
| `chunked` (fallback) | 187, 155, 158 | 153, 159, 190 | H3ultRefsTest2 as you saved it |
| `sage` (as saved in H3regenrunsTest) | 159, 153 | 155, 158, 187, 190 | H3regenrunsTest as you saved it |

- Profiles are defined per manifest. Each H3 manifest records which node in its template is the sol-attn node and which are the chunking nodes, because templates can differ. Two sol-attn nodes are in use:
  - ComfyUI's built-in **Model Sparse Attention** (`BlockSparseAttention`, node 190 in the H3ult/regenruns family): tau 1.3, start 0.2, end 1.0, min_tokens 12288, extra_tokens 256, sink exact_kv_and_rows.
  - The custom **Patch Sol-Attn** (`SolAttnPatch` from `ComfyUI-SolAttn_triton`), as in your screenshot of 2026-10-09: tau 1.30, start 0.20, end 0.90, min_tokens 4096, int8_qk true, sink exact_kv_and_rows, morton true, morton_curve 2d_frame, use_tma false. Of the saved files, only `ref2va.json` has exactly these values.
- The sol node's own settings come from the template as you saved it. If an H3 template has no sol-attn node, the Producer asks you before using it.
- The profile is applied in the studio's ComfyUI tab before graphToPrompt. Your saved workflow files are never changed.
- **Fallback:** when you report low quality, or VRAM fills (a watchdog halt, or a peak at the limit), the studio switches that project's H3 jobs to `chunked` without a new approval. It records the switch as a decision and reports it.
- `sol` has no measured time or VRAM peak yet. Until the first smoke test measures it, budgets use the measured non-sol numbers (22–33 min per unit) as the upper bound.

**I. ComfyUI launcher.** It is `C:\Users\david\Desktop\ComfyUI.bat`: vcvars64, then `C:\CUVenv`, then `python main.py --cuda-device 0 --disable-pinned-memory --disable-comfy-compiler`. Other launchers sit next to it (ComfyUINSFW.bat, "ComfyUI - LTX2.bat" and others), and a restart always reopens with ComfyUI.bat.
*Proposal:* at the start of a window the watchdog compares the running ComfyUI's command line with ComfyUI.bat's and warns you if they differ. "Close ComfyUI" means the python.exe listening on 8188 plus its parent cmd.exe console, and nothing else.

**J. Skills.**
- The design lists h3-prompting, krea-sheets, comfy-bridge, vram-watch, studio-conventions and video-use; four skills exist today.
- *Approved 2026-10-09:* port the four under their current names, and add studio-conventions (step 2), comfy-bridge (step 6) and vram-watch (step 7). Splitting h3-gacha-pipeline into h3-prompting and krea-sheets waits until the Prompt Writer and the Asset Designer first run; until then they preload h3-gacha-pipeline.
- video-use is already installed for your user at `~\.claude\skills\video-use`, with its own venv and `.env`. Agents preload it by name; it is not copied into the repo.
- The same four skills also exist as claude.ai account skills (`anthropic-skills:…`), which keep the cloud environment sections. Studio agents preload the project copies by name. In the main session, both copies are visible.

**K. Design details that don't apply here.**
- The example agent file's `mcp__comfyui` / `mcpServers: comfyui` doesn't exist. The Render Wrangler uses the Claude in Chrome tools and Bash.
- "Haiku for polling" is unnecessary, because polling is done by scripts, not by a model.
- Per-agent effort is supported (checked in step 4), and the Prompt Writer uses `effort: high`.
- Subagents cannot use AskUserQuestion, so only the Producer asks the user, as the design intends.
- The Art Director gets Bash, which the design doesn't list, so it can build mood-board and look-test contact sheets. It never runs ComfyUI.

**L. Resolve MCP.**
- Claude Desktop's config already defines `davinci-resolve`, and the Desktop app's Code tab already loads it. The project `.mcp.json` is what CLI sessions need. Whether the Desktop app then shows the server twice gets checked in step 9.
- The MCP's auto-launch only knows `C:\Program Files\…`, so you start Resolve from `C:\DavinciResolve\Resolve.exe`. You also run Workspace ▸ Scripts ▸ resolve_bridge once per session.

**M. Long GPU jobs vs agent turns.** H3 jobs take 22–33 minutes, and an agent can't sit in one turn that long cheaply. The bridge gets a `wait` command (blocking, at most 10 minutes per call) and the watchdog log. How the Render Wrangler paces a 3-hour window is designed in Phase 2.

**N. Other.**
- No footage folder exists yet. Each one is created at project definition, where you choose it (G2).
- Drives E: and F: exist and aren't mentioned in the design. Reads from them stay allowed; writes are blocked like everything outside the allowed roots.

## 4. Decisions needed

Your "OK" accepts the proposals as written. Change any of them by number:

1. ~~Studio venv at `.venv`, light packages now (3.A).~~ Approved.
2. ~~Approval policy (3.F).~~ Decided: you define it per project at intake.
3. ~~The write allowlist plus scratch and memory folders (3.G).~~ Approved.
4. ~~A dedicated studio ComfyUI tab (3.D).~~ Approved. Jobs run in that tab, so that is where you watch progress and the preview node.
5. ~~Which workflows get manifests (3.H).~~ Decided: you give workflow templates per project, and the Producer prompts for them at project initialization if they're missing.
7. ~~Footage location (3.G2).~~ Decided: you choose a footage folder for each project when it is defined.
6. ~~Port four skills now; the h3 split later (3.J).~~ Approved.

## 5. Phase 1 result (2026-10-10)

All nine steps are done and committed locally; nothing is pushed yet. The studio is ready for Phase 2 once the items below are settled.

**Before the first real window:**
1. **Restart test.** The live restart test (close ComfyUI, wait 15 s, reopen with ComfyUI.bat, API answers) runs once, in a window the user approves, with no job running.
2. **Smoke tests.** Each workflow template gets a smoke test in an approved window. `sol` has no measured time or VRAM peak yet.
3. **Approve the Resolve MCP.** The user approves the project-scope `davinci-resolve` server on the first `claude` run in this folder.

**How to start the studio:** double-click `Start_Studio.cmd` (added 2026-10-10).
- It starts ComfyUI if it isn't running, starts Chrome, puts the studio-tab address on the clipboard, optionally starts Resolve, and runs `claude --agent producer --chrome` here.
- The Resolve bridge still needs the user: open a `STUDIO_` project, then Workspace > Scripts > resolve_bridge.
- The studio tab can't be opened by the launcher. The extension only controls tabs in its own tab group, and ComfyUI refuses navigations started by the extension. So the user pastes the address into the group's tab when the studio asks. In the Desktop app, use `"agent": "producer"` in `.claude/settings.local.json`. The user opens the studio's ComfyUI tab by typing `http://127.0.0.1:8188` into a tab of Claude's tab group.

**Recommended:** run studio sessions in a normal permission mode, not bypass. The hooks hold in every mode, but the settings' "ask" rules for pushes and guardrail files only prompt outside bypass.

**Phase 2** begins with the pilot project's brief from the user, starting at S0.
