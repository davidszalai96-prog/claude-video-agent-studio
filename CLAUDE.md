# Claude video agent studio

An agentic animation studio on this PC: a Producer and 14 specialist agents plan, generate (Krea 2 and MiniMax H3 in ComfyUI), review and edit (DaVinci Resolve or video-use) music videos and other short films.

- The spec is `docs/studio-design.md`. Where it and anything else disagree, it wins, except where a decision recorded in `docs/phase1-plan.md` (section 3) changes it. If both are silent, ask the user.
- Measured facts are in `docs/notes/`. Working conventions (IDs, statuses, handoffs, notes, tickets) are in the `studio-conventions` skill.

## Hard rules

1. **The user is the only approver.** Ask before anything with side effects outside this repo.
2. **The user defines each project's rules when the project is defined.** The Producer asks, and never assumes, three things:
   - the **approval policy** for GPU work;
   - the **workflow templates**: the saved ComfyUI workflows this project uses. There are no global defaults; if none are named, prompt the user at project initialization;
   - the **footage folder**: where ComfyUI writes this project's takes and stills. It must be inside `C:\CU\output`, because ComfyUI refuses to save anywhere else; `C:\CU\output\studio\<CODE>` is the suggestion.

   The Producer drafts them in `00_admin/policy_proposal.json`. When the user approves it, a hook records the approval, with a copy of the policy, in `projects/<CODE>/00_admin/approvals/policy.json`. Until a project has a recorded policy, nothing is queued in ComfyUI for it without an approved run ticket whose window is open. Building and reading are always fine; rendering is not.
3. **Agents never write approvals.**
   - Nothing under `00_admin/approvals/` is written by an agent. A hook records the user's answers there.
   - An agent never claims an approval that isn't recorded.
4. **ComfyUI is shared with the user's other work.**
   - Never change a saved workflow without approval.
   - Never reload or drive the user's own ComfyUI tab. The studio uses its own tab, and jobs are queued from that tab with that tab's client ID, so the user can watch progress and previews there.
   - Only the watchdog restarts ComfyUI, and only inside an approved window, through `ComfyUI.bat`.
   - One GPU job at a time.
5. **Never read from or write to D:** (failing drive). This includes listing it, querying it, and relinking or caching anything to it.
6. **Writes are allowed only in:**
   - this repo;
   - each project's recorded footage folder;
   - Claude Code's scratch folder (`%TEMP%\claude\…`);
   - this project's memory folder (`~\.claude\projects\C--claude-video-agent-studio\memory`).
7. **Never open, modify or render an existing DaVinci Resolve project.**
   - The studio creates and loads only projects named `STUDIO_<...>`, for example `STUDIO_MAG` or `STUDIO_TEST_20261010`.
   - Every other Resolve call needs such a project created or loaded in the same session (the guard hook enforces this).
   - It never deletes projects, switches databases or uses cloud projects.
   - Never update Resolve past 21.0.x.
8. **The Gemini key** (`C:\CU\output\video\geminiapi.txt`) is read by scripts only, by path. Never print, log, copy or commit it, and never read it with a file tool.
9. **Never write song lyrics** into any file or reply. Use timing and structure only.
10. **No dialogue or voice lines in generation prompts.** Sound effects and music are fine.
11. **Media never goes into git:** renders, audio, images, model files.
12. **Never install into ComfyUI's venv** (`C:\CUVenv`). The studio has its own venv (see below).

## Guardrails are enforced by hooks

- `.claude/hooks/guard.ps1` (PreToolUse) blocks breaches of rules 2–8 before they run, in every permission mode. See the `studio-conventions` skill (Guardrails).
- `.claude/hooks/record-approval.ps1` (PostToolUse on AskUserQuestion) records approvals from the user's answers. Questions are marked with `pipeline\tools\ticket.py marker`.
- File tools are checked exactly; shell commands are checked best-effort. A block is never worked around: report it and ask.

## Working protocol (Phase 1)

Work through `KICKOFF.md` Phase 1 one step at a time. After each step, show what changed, commit locally with a clear message, and wait for the user's OK. Push only when the user says so.

## Environment on this PC

| What | Where / value |
| --- | --- |
| ComfyUI | 0.37.0 at `C:\CU`; API `http://127.0.0.1:8188`; its own venv `C:\CUVenv` |
| ComfyUI launcher | `C:\Users\david\Desktop\ComfyUI.bat` (vcvars64 → `C:\CUVenv` → `python main.py --cuda-device 0 --disable-pinned-memory --disable-comfy-compiler`) |
| ComfyUI folders | workflows `C:\CU\user\default\workflows`, input `C:\CU\input`, output `C:\CU\output`. Each project's footage folder is inside output: `<footage>\units\<TAKE>\` for H3 takes, `<footage>\stills\<ID>\` for Krea stills. |
| GPU / RAM | RTX 5090 32 GB / 128 GB |
| Studio Python | `.venv\Scripts\python.exe` (3.12.10, built from `C:\Program Files\Python312`). Bare `python` on PATH is the Microsoft Store alias, so never use it. |
| ffmpeg / ffprobe | 8.1.2 on PATH (winget) |
| Shells | Windows PowerShell 5.1 (no pwsh 7) and Git Bash. Hook scripts use 5.1 syntax. |
| DaVinci Resolve | 21.0.4.5 free at `C:\DavinciResolve`. Start it manually, open a project, then run Workspace ▸ Scripts ▸ resolve_bridge once per session. |
| Resolve MCP | samuelgursky/davinci-resolve-mcp 4.8.22 with `RESOLVE_SCRIPT_LIB=C:\DavinciResolve\fusionscript.dll` |
| video-use | user-level skill at `~\.claude\skills\video-use` |
| Claude Code | `C:\Users\david\.local\bin\claude.exe` |

## Repo layout

```
CLAUDE.md, .mcp.json
.claude\agents\         the 15 studio agents (producer.md … librarian.md)
.claude\skills\         studio-conventions, h3-gacha-pipeline, gemini-video-review,
                        resolve-music-video, resolve-edit, comfy-bridge, vram-watch
.claude\hooks\          guardrail hooks (PowerShell 5.1)
docs\                   design spec, Phase 1 plan, measured notes
pipeline\               schemas\, comfy\ (manifests, profiles, snapshots, bridge),
                        watchdog\, tools\, tests\, constants.json
templates\project\      00_admin … 10_wrap
projects\<CODE>\        one folder per film, made from the template
```

## Project folder (from the design)

```
projects\<CODE>\
  00_admin\    tracker.json, budget.json, policy_proposal.json, run_tickets\, approvals\ (hook only),
               tasks\, gates\, notes.md, decisions.md, render_log.jsonl, vram_log.jsonl
  01_brief\    brief.md, project.yaml
  02_story\    song_map.json, concepts.md, treatment.md, beat_sheet.json
  03_art\      style_bible.md, prompt_blocks.json, assets\<asset>\v###\
  04_boards\   shotlist.json, keyframes\, animatic\
  05_prompts\  <UNIT>_v###.txt, lint\, jobs\<OUTPUT_ID>.json
  06_dailies\  <TAKE>\ report.md, qc.json, sheets\
  07_edit\     edl_v###.json, previews\
  08_finish\   conform\, renders\
  09_delivery\
  10_wrap\
<footage folder>\      chosen by the user, inside C:\CU\output: units\<TAKE>\, stills\<ID>\
```

A rerun batch outside a film is defined like a project, with its own footage folder.

## Naming

| Level | Pattern | Example |
| --- | --- | --- |
| Project | 3 uppercase letters | `MAG` |
| Sequence | `<CODE>_SQ###` (steps of 10) | `MAG_SQ010` |
| Generation unit | `<SEQ>_U###` | `MAG_SQ010_U020` |
| Shot | `<UNIT>_SH###` | `MAG_SQ010_U020_SH030` |
| Take | `<UNIT>_v###` | `MAG_SQ010_U020_v003` |
| Select | `<SHOT>_v###_s#` | `MAG_SQ010_U020_SH030_v003_s1` |
| Asset | `<TYPE>_<name>_v###` with TYPE in CHAR, PROP, ENV, VFX, GFX | `CHAR_nyxara_v002` |
| Krea still | `<ASSET>_c##` (sheet candidate) or `<SHOT>_kf_v###[_c##]` (keyframe) | `CHAR_nyxara_v002_c03` |
| Run ticket / note / decision / task | `R-###`, `N-###`, `D-###`, `T-####` | `R-004` |

Versions are always three digits (`v001`). Agents pass each other paths and IDs, never pasted content.

## Launching the studio (after Phase 1)

`claude --agent producer --chrome` from a terminal in this folder. In the Desktop app, use `"agent": "producer"` in `.claude/settings.local.json`. Phase 1 itself is built in a normal session.
