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

**Step 6: ComfyUI bridge, read-only.** List the workflows. Open them in a ComfyUI tab, convert them with graphToPrompt and write, for each of H3regenrunsTest, H3ultRefsTest2 and H3regensElements:
- `manifests/<id>.json`: per-job parameters with node IDs and input names, seed node, broadcast inputs to wire, outputs, measured costs.
- `profiles/<id>.default.json`: every other value, as you saved it.
- `snapshots/<id>/<date>_<hash>.api.json`.

Plus `bridge/comfy_api.py` (status, queue, history, free, outputs, logs; no submit until step 8's check exists), `bridge/page_recipes.js` and `skills/comfy-bridge/SKILL.md`. Nothing is queued.

**Step 7: watchdog and restart**
- `pipeline/watchdog/vram_watch.py`: headroom check, halt detection, VRAM log. `--dry-run` simulates halts from recorded inputs and never touches a process.
- `restart_comfyui.ps1`: `-DryRun` prints the PIDs it would end and the command it would run.
- `config.json` (5-minute progress timeout, 2-minute API timeout, 15 s wait, 3-minute start timeout, two restarts per window) and `comfyui_launch.json` (exact launcher path and arguments).
- `skills/vram-watch/SKILL.md` and dry-run tests.

**Step 8: guardrail hooks** in `.claude/hooks/`:
- `guard-paths.ps1`: blocks any D: path and any write outside the allowed roots. Write and Edit are blocked exactly. Bash and PowerShell commands are checked best-effort for redirections and file cmdlets.
- `guard-comfy-submit.ps1`: blocks `/api/prompt` POSTs from the shell or the Chrome JavaScript tool without an approved ticket whose window is open.
- `guard-secrets.ps1`: blocks reading or printing the Gemini key file.
- `record-approval.ps1`: see 3.F.
- `pipeline/tools/ticket.py`: create a proposed ticket, check whether a window is open.
- Hook tests.

**Step 9: Resolve MCP.** `.mcp.json` with the `davinci-resolve` command and env copied from Claude Desktop's config, including `RESOLVE_SCRIPT_LIB=C:\DavinciResolve\fusionscript.dll`. Then verify with `resolve_control get_version` in a new throwaway project that you open.

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

**G. Write allowlist.** The design allows writes only to the repo and `C:\CU\output\studio`. That would also block Claude Code's own scratch folder (`%TEMP%\claude\…`) and this project's memory folder (`~\.claude\projects\C--claude-video-agent-studio\memory`).
*Approved 2026-10-09:* allow those two as well. The hooks also guard the Gemini key file, which the KICKOFF rules require but step 8 doesn't list.

**H. Workflows (open, see the expansion below).** All three named workflows are present (last saved 5 Oct). Newer H3 workflows exist too: H3ultRefsTest3, H3ultSingleRef, H3ultSingleRefSparse, H3ult_Solenne_v3–v5 and H3ult_Xiaoyu_v1–v3.

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
- *Recommendation:* in step 6, write manifests for H3regensElements, H3regenrunsTest and H3ultRefsTest2 as KICKOFF says, plus H3ult_Xiaoyu_v3_textcats as the newest setup if you use it for production. Each new configuration is marked unmeasured until a smoke test in an approved window measures it.

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
- Whether the frontmatter supports per-agent effort ("Opus, high effort" for the Prompt Writer) gets checked in step 4.

**L. Resolve MCP.**
- Claude Desktop's config already defines `davinci-resolve`, and the Desktop app's Code tab already loads it. The project `.mcp.json` is what CLI sessions need. Whether the Desktop app then shows the server twice gets checked in step 9.
- The MCP's auto-launch only knows `C:\Program Files\…`, so you start Resolve from `C:\DavinciResolve\Resolve.exe`. You also run Workspace ▸ Scripts ▸ resolve_bridge once per session.

**M. Long GPU jobs vs agent turns.** H3 jobs take 22–33 minutes, and an agent can't sit in one turn that long cheaply. The bridge gets a `wait` command (blocking, at most 10 minutes per call) and the watchdog log. How the Render Wrangler paces a 3-hour window is designed in Phase 2.

**N. Other.**
- `C:\CU\output\studio` doesn't exist yet. Phase 1 doesn't need it; I'll ask before creating it.
- Drives E: and F: exist and aren't mentioned in the design. Reads from them stay allowed; writes are blocked like everything outside the allowed roots.

## 4. Decisions needed

Your "OK" accepts the proposals as written. Change any of them by number:

1. ~~Studio venv at `.venv`, light packages now (3.A).~~ Approved.
2. ~~Approval policy (3.F).~~ Decided: you define it per project at intake.
3. ~~The write allowlist plus scratch and memory folders (3.G).~~ Approved.
4. ~~A dedicated studio ComfyUI tab (3.D).~~ Approved. Jobs run in that tab, so that is where you watch progress and the preview node.
5. Which workflows get manifests (3.H): open.
6. ~~Port four skills now; the h3 split later (3.J).~~ Approved.
