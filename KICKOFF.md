# Kickoff prompt for Claude Code

Start Claude Code in `C:\claude-video-agent-studio` with `claude --chrome`, then paste everything below the line (or type: "Read KICKOFF.md and start Phase 1").

---

You are building an agentic animation studio in this repository (`C:\claude-video-agent-studio`, remote `origin` = github.com/davidszalai96-prog/claude-video-agent-studio).

**Read first, fully:**

1. `docs/studio-design.md` — the approved design: 15 agents, lifecycle, run tickets, VRAM watchdog and restart procedure, data model, tool layer, build order. It is the spec. Where it and anything else disagree, it wins; ask me if it is silent.
2. `docs/notes/resolve-setup-and-pipeline-test.md` — measured facts about DaVinci Resolve 21.0.4 free and its MCP on this PC.
3. `.claude/skills/*/SKILL.md` — four working skills (H3 + Krea in ComfyUI, Gemini review, Resolve music-video, Resolve edit). They were written for a claude.ai cloud session with no shell on this PC, browser-only ComfyUI access and "device file tools". Here you have a local shell, so their environment sections need porting. Every measured number and every rule in them stays.

**Hard rules from the first minute (put them in CLAUDE.md first):**

- I am the only approver. Ask before anything with side effects outside this repo.
- Never queue a ComfyUI job, restart ComfyUI or start a GPU run without an approved run ticket and an open window from me. Building and reading are fine; rendering is not.
- Never read from or write to D: (failing drive).
- Never open, modify or render an existing DaVinci Resolve project. Tests use a new project.
- Never print, log or commit the Gemini key (`C:\CU\output\video\geminiapi.txt` is read by scripts only). Never write song lyrics into any file.
- No dialogue or voice lines in generation prompts.
- Media (renders, audio, images from ComfyUI) never goes into git.

**Phase 1 — Foundation.** Work through these in order. After each one: show me what changed, commit with a clear message, and wait for my OK before the next. Push only when I say so.

1. **Plan.** Propose the repo layout (design sections "Data model" and "Implementation") and the list of files you will create in this phase. Note anything in the design that does not fit this PC.
2. **CLAUDE.md and settings.** Studio rules, naming conventions, folder layout, and `.claude/settings.json` with conservative permissions.
3. **Port the four skills** to local Claude Code: rewrite only the environment parts (ComfyUI through Claude in Chrome on my open ComfyUI tab plus the local HTTP API from the shell; files directly on disk; no `.cmd` launcher workarounds needed). Show me the diff of each skill.
4. **Agent files.** The 15 agents in `.claude/agents/` from the design's agent specs and org chart: Producer as the session agent with `tools: Agent(...)` limited to the studio agents; specialists without the Agent tool; model tier per the org chart table; short descriptions, detail in the body; skills preloaded where the design says so.
5. **Data schemas and project template.** JSON schemas for tracker, run ticket, task envelope, job spec, QC report, selects and EDL; `templates/project/` with the 00_admin … 10_wrap folders.
6. **ComfyUI bridge, read-only.** List `C:\CU\user\default\workflows`, open my ComfyUI tab, convert H3regenrunsTest, H3ultRefsTest2 and H3regensElements with graphToPrompt, and write their manifests and default configuration profiles under `pipeline/comfy/`. Do not queue anything.
7. **VRAM watchdog and restart script** (design: Tool layer → ComfyUI restart procedure). Build them with a dry-run mode and test the dry run only. Find the exact path of `ComfyUI.bat` on my desktop and record it. The live restart test happens later, in a window I approve, with no job running.
8. **Guardrail hooks.** PreToolUse hooks (PowerShell on Windows) that block writes to D:, writes outside this repo and `C:\CU\output\studio`, and any ComfyUI submit without an approved, open run ticket.
9. **Resolve MCP for Claude Code.** Add the `davinci-resolve` server at project scope (`.mcp.json`), copying command and env (including `RESOLVE_SCRIPT_LIB=C:\DavinciResolve\fusionscript.dll`) from Claude Desktop's config. Verify with `resolve_control get_version` while a throwaway test project is open.

Then stop and report. Phase 2 (the core loop on a pilot project I will define) starts only after I review Phase 1.
