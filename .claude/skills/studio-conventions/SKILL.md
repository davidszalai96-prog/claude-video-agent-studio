---
name: studio-conventions
description: Working conventions every studio agent follows - IDs and versions, where files go, unit statuses, the task envelope and report format, notes and decisions, change tiers, run tickets and approvals. Use whenever creating, naming, moving or handing off any project file, dispatching or reporting a task, or touching run tickets.
---

# Studio conventions

The rules in `CLAUDE.md` come first. This skill is how the agents work together inside them. The design behind it is `docs/studio-design.md` (sections "Data model" and "Quality system").

## Files are the source of truth

- Everything for a film lives in `projects/<CODE>/` (layout in `CLAUDE.md`). Takes rendered by ComfyUI live in `C:\CU\output\studio\<CODE>\units\` and the tracker points to them.
- Hand over **paths and IDs, never pasted content**. To point inside a file, use a fragment: `04_boards/shotlist.json#MAG_SQ010_U020`.
- Never overwrite a versioned file. Write the next version (`v002`, `v003`, …) and leave the old one.
- Logs (`render_log.jsonl`, `vram_log.jsonl`) are append-only: one JSON object per line.
- Timestamps are ISO 8601 local time with offset, e.g. `2026-10-10T21:00:00+02:00`.
- JSON files follow the schemas in `pipeline/schemas/`. Validate with `.venv\Scripts\python.exe pipeline\tools\validate.py projects\<CODE>`.

## IDs

Patterns are in `CLAUDE.md` (Naming). In addition:

- Sequences and units step by 10 (`SQ010`, `SQ020`; `U010`, `U020`), so a new one can be inserted between them.
- Shots step by 10 inside a unit (`SH010`, `SH020`).
- A take is one render: one prompt version, one seed and one configuration hash. Take `v###` counts renders of that unit; the prompt file carries the same version as the take it was written for.
- Assets: `CHAR_` character, `PROP_` prop or cutout, `ENV_` environment, `VFX_` effect, `GFX_` graphic overlay. Lowercase names with underscores: `CHAR_nyxara_v002`.
- Tasks `T-####`, notes `N-###`, decisions `D-###` and run tickets `R-###` are numbered per project by the Producer, never reused.

## Unit statuses

`planned → boarded → prompt_ready → awaiting_run_approval → queued → rendering → rendered | halted → in_dailies → approved | approved_with_selects | retake_requested → in_edit → locked`

- A unit with `retake_requested` stays in the edit with its current take.
- An approved retake sends the unit back to `prompt_ready` with `attempt` raised by one. The new take replaces the old one only if it scores better.
- `halted` takes are never rerun with the same configuration.

## Task envelope (Producer → agent)

Every dispatch has exactly this shape (schema: `pipeline/schemas/task_envelope.schema.json`):

```json
{
  "task_id": "T-0123",
  "agent": "prompt-writer",
  "objective": "Write the ref2va prompt for MAG_SQ010_U020 from shot list v002",
  "inputs": ["04_boards/shotlist.json#MAG_SQ010_U020", "03_art/prompt_blocks.json"],
  "outputs": ["05_prompts/MAG_SQ010_U020_v001.txt", "05_prompts/lint/MAG_SQ010_U020_v001.json"],
  "acceptance": ["lint passes", "11 shots in slot order", "60-65 words per second"],
  "budget": {"gpu_min": 0, "gemini_requests": 0, "max_turns": 30},
  "due": "before the next run request",
  "escalate_if": "a shot cannot fit the word budget"
}
```

Paths in `inputs` and `outputs` are relative to `projects/<CODE>/`.

## Report (agent → Producer)

End every task with a short report, never a chat essay:

```
task: T-0123  status: done | partial | blocked | escalated
wrote: <paths, one per line>
acceptance: <each criterion: pass / fail, with the evidence path>
notes: <at most 5 lines: surprises, risks, what the next agent needs to know>
escalation: <only if escalate_if was met: what, and the options>
```

Write only the files named in `outputs`, plus scratch files under your own working folder. If you need to write anything else, report it instead of writing it.

## Notes and decisions

- **Notes** (`00_admin/notes.md`): one entry per note.
  - `N-014 · <shot ID or timecode> · <what is wrong> · <why it matters> · <result wanted> · tier T0–T4 · owner · open | in_progress | closed`.
  - Say what, never how.
- **Decisions** (`00_admin/decisions.md`): `D-007 · <date> · <decided by> · <what> · <why>`.

## Change tiers

| Tier | Example | Route | Cost |
| --- | --- | --- | --- |
| T0 Edit | trim, reorder, timing, swap a select | Editor | minutes, no GPU |
| T1 Post | grade, speed, zoom pulse, flash, overlay, title | Editor or Finishing | minutes, no GPU |
| T2 Regenerate | a unit misses a beat: new seed or wording | Prompt Writer → Render Wrangler → Dailies & QC | 22–33 GPU-min per unit |
| T3 Re-board | new or changed shots in a sequence | Storyboard, then T2 per unit | keyframes plus every unit in the sequence |
| T4 Redesign | character, style block or story change | Art Director or Asset Designer, then T3 | every unit that uses it (from the asset registry) |

T0 and T1 go straight into the next cut. T2 and up spend GPU time and follow the project's approval policy.

## Run tickets and approvals

- **Policy.** The user defines the approval process for each project at intake. It is recorded in `00_admin/approvals/policy.json` from the user's own answer. Until it exists, nothing runs in ComfyUI without an approved ticket and an open window.
- **Ticket.** The Producer writes a proposed ticket to `00_admin/run_tickets/R-###.json` (schema `run_ticket.schema.json`): the jobs, each workflow and its configuration (changes shown as a diff against the default profile), estimated GPU minutes, VRAM risk, and the proposed window.
- **Approval.** The Producer asks the user, naming the ticket and the window. The user's answer is recorded by a hook to `00_admin/approvals/R-###.json`. Agents never write anything under `00_admin/approvals/` and never treat a ticket as approved without that record.
- **Window.** Nothing starts after the window ends. A job that cannot finish before the end waits for the next window.
- **Retakes and pickups** ride along with the next ticket, unless the project's policy allows them inside an approved ticket.

## What never goes into a project file

- Song lyrics.
- Dialogue or voice lines in generation prompts.
- The Gemini key, or any key or token.
- Media in git. Renders, audio and images stay on disk and are ignored by `.gitignore`; the tracker points to them.
