---
name: video-use-studio
description: How the studio uses the video-use skill (the ffmpeg editing route, music-video mode) inside its rules - which folder it works in, which helpers serve which studio task, how its plan/EDL relate to the studio EDL, approvals, animation slots (HyperFrames, PIL, slot-local Remotion; never ~/motion), keys and GPU windows. Use together with the video-use skill whenever the Editor, Finishing or Music & Timing works through video-use.
---

# video-use in the studio

`video-use` (user-level skill, `~/.claude/skills/video-use/`) is the studio's second editor route next to DaVinci Resolve (design: Tool layer → Editor adapter). It edits with ffmpeg from plans, and its **music-video mode** was built on H3 footage. The Nhato "Magic" edit used it: `C:\CU\output\video\Nhato Magic - Video-edit\edit\` is the worked example, and that project's own tools are in `pipeline/tools/from_magic/`.

Read the video-use skill for how it works. This skill is only about how it fits the studio. Where they disagree, `CLAUDE.md` and this skill win.

## Where it works

- **`<videos_dir>` is the project's footage folder**, the one in `00_admin/approvals/policy.json`. Its takes are in `units/`, and video-use writes everything into `<footage folder>\edit\`. That folder is inside the studio's write roots, and it is media-heavy, so it is never in git.
- Never write inside `~/.claude/skills/video-use/` (its own rule 12), and **never write in `C:\Users\david\motion`** (user decision 2026-10-10). Reading its asset library is fine: copy what a slot uses into the slot.
- Run the helpers with video-use's own venv:
  `"$HOME/.claude/skills/video-use/.venv/Scripts/python.exe" "$HOME/.claude/skills/video-use/helpers/<helper>.py" ...`
  The studio venv lacks its media stack. `PYTHONUTF8=1` is set in the user's Claude Code settings.

## Which helper serves which studio task

| Studio task (agent) | video-use helper | Studio artifact of record |
| --- | --- | --- |
| Song map (Music & Timing) | `beats.py <song>` → `edit/music/<song>.map.md`, `.beats.json` | `02_story/song_map.json`, written from the beats output, with frame conversions |
| Shot structure (Dailies & QC may use it) | `shots.py <dir>` → `shots_packed.md`, contact sheets, `shots.json` | `06_dailies/<TAKE>/qc.json`. Dailies still does its blind pass and the frame checks itself |
| Cut plan and previews (Editor) | `plan.json` → `beatmap.py` → `edl.json` + `beatmap.md`; `render.py --draft` | `07_edit/edl_v###.json` (studio EDL) and `07_edit/previews/cut_v###.mp4` |
| Master on the video-use route (Finishing) | `render.py` (no `--draft`), `grade.py`, overlays | `08_finish/renders/`, `08_finish/conform_report.md` |
| Animation data (Finishing) | `audio_frames.py` | inside the slot folder |

- **EDL of record.** The studio EDL stays the editor-neutral record at every cut version, so the route can switch to Resolve without re-editing.
- **Working files.** video-use's `plan.json` and `edl.json` are working files. Name them per version (`edit/plan_v###.json`, `edit/edl_v###.json`) and reference them from the studio EDL's changelog.
- **Converter.** The Pipeline TD builds the video-use EDL → studio EDL converter in Phase 5. Until then the Editor writes both.

## Studio rules that change video-use's defaults

- **Approvals.** video-use's rule 11 ("strategy confirmation before execution") is met through the studio:
  - the Director signs off the plan;
  - the Producer takes it to the user at G1 (plan) or G3 (cut);
  - subagents never ask the user themselves.
  The user's notes come back as numbered notes.
- **No transcription for music videos.** Don't run Scribe on the clips; it burns the user's ElevenLabs hours. Never read or print the ElevenLabs key or any `.env`; video-use's scripts read it themselves.
- **No lyrics, ever.** Timing and structure only.
- **Animation slots** live in `<footage folder>\edit\animations\slot_<id>\`:
  - HyperFrames and PIL slots are fine.
  - Remotion only as a project scaffolded inside the slot folder (`npx create-video@latest`), never the shared `~/motion/remotion` project.
  - Each slot is its own task. The Producer dispatches slots to `finishing` in parallel; specialists can't start agents themselves.
- **GPU windows.** No final render and no HyperFrames or Remotion render during an approved H3 window. CPU-only ffmpeg draft previews are fine.
- **Finishing in Resolve instead.** `edl.json` and `beatmap.md` give frame-exact source in/out per shot. The Resolve route conforms from the studio EDL (`resolve-music-video` skill).

## Choosing the route

- Finishing picks Resolve or video-use per project from the Librarian's editor record:
  - conforms that passed first time;
  - render mismatches;
  - failures;
  - time spent.
- Until the record has data, the Producer asks the user. video-use is the natural first choice for a beat-cut H3 music video with ffmpeg effects (punch, pulse, flash, speed). Resolve is the choice for grading depth, Fusion effects and a timeline the user wants to open.
- Record every route outcome for the Librarian.
