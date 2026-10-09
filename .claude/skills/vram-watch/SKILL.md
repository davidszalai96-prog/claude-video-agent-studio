---
name: vram-watch
description: Keeping the GPU safe during a render window - the headroom check before each H3 job, the launch check, running the VRAM watchdog in the background, what its state means, the automatic ComfyUI restart procedure and its limits, getting the studio tab back afterwards, and dry runs. Use whenever a window starts or ends, before queuing an H3 job, after a halt, or when testing the watchdog.
---

# VRAM watch and restart

H3 can fill VRAM and nearly halt the PC. So every H3 job:
- runs alone;
- runs after a headroom check;
- runs under a watchdog that closes and reopens ComfyUI by itself when a job halts.

The design is `docs/studio-design.md`, Tool layer → ComfyUI restart procedure. Settings are in `pipeline/watchdog/config.json`. All Python runs with `.venv\Scripts\python.exe`, and `W` below means `... pipeline\watchdog\vram_watch.py`.

## At the start of a window (Render Wrangler)

1. **Launch check:** `W launch-check`. It confirms that the running ComfyUI was started by `C:\Users\david\Desktop\ComfyUI.bat` with that file's arguments. If it reports a mismatch, tell the user before the window starts, because a restart would reopen ComfyUI with ComfyUI.bat, not with the launcher they used.
2. **Update checks:** `comfy_api.py checks` (comfy-bridge skill). All must PASS.
3. **Start the watchdog in the background** (Bash `run_in_background`):
   `W watch --project projects\<CODE> --run-id R-###`
   - It refuses unless `00_admin/approvals/R-###.json` is an approval the user recorded, the ticket is unchanged since, and the window is open.
   - It logs to the project's `00_admin/vram_log.jsonl`.
   - It exits at the window's end (when no job is running), or when it stops with an alert.

## Before each H3 job

- **Headroom:** `W headroom --required-gb <peak> --project projects\<CODE>`. `<peak>` is the configuration's recorded peak VRAM from the manifest or the Librarian's safe table, or `unmeasured_required_gb` (26 GB) for a configuration never measured.
  - It also fails when ComfyUI's queue is busy, when Resolve, Fusion or Blender is running, or when another ComfyUI instance is up.
  - On a failure, skip the job and report it. Never queue anyway.
- **Tell the watchdog** which job it is watching. When you queue, write `pipeline/watchdog/runtime/current_job.json` with `project`, `run_id`, `output_id`, `prompt_id`, `config_hash`, `attention_profile` and `required_gb`.

## What the watchdog does

It follows ComfyUI's console log (the age of the newest sampler progress line), the queue, the API and NVML, every 15 s.

**A halt is:**
- no sampler step for **5 min** while a job runs;
- no first step **10 min** after a job started (model load and text encode print no progress);
- or no API answer for **2 min**.

Progress lines stamped before a job started never count for that job.

**On a halt** it logs `halt_detected` (job, last step, peak VRAM), then:
- **Inside the window, with fewer than 2 restarts so far:** it runs `restart_comfyui.ps1`:
  1. Close the console tree that runs ComfyUI.bat, and nothing else (`taskkill /T` on that `cmd.exe`).
  2. Wait 15 s.
  3. Check GPU memory. If more than 8 GB is still used, it reports `memory_not_released`: a reboot may be needed, and the window stops.
  4. Reopen ComfyUI as `explorer.exe ComfyUI.bat`, which is like a double-click, so ComfyUI does not belong to the studio's processes.
  5. Wait up to 3 min for the API.
- **Third halt in a window, or a halt after the window ended:** no restart. Status `stopped_alert`; tell the user.

It writes its state to `pipeline/watchdog/runtime/state.json`: `watching`, `window_end` or `stopped_alert`, plus the restart count and the last event. Read it after every `comfy_api.py wait`.

## After a restart (Render Wrangler)

1. Mark the halted take `halted` in the tracker. It is never rerun with the same configuration.
2. If the halt was a VRAM fill on `sol`, the project's H3 jobs switch to `chunked`. Report that to the Producer, who records it.
3. **Getting the studio tab back.**
   - The tab must be reloaded **from the page itself**, and only once `comfy_api.py status` shows the API answering. Run `location.reload()` with the JavaScript tool, then load `page_recipes.js` again. ComfyUI's frontend may also reconnect by itself.
   - Never navigate the tab from the extension: ComfyUI answers 403 to extension-started navigations (comfy-bridge skill).
   - If the tab shows a Chrome error page, it can't be recovered without the user. End the window and ask the user to reopen the studio tab.
4. Continue with the next job if the window still has time.
5. Retry a failed job once, and only when the failure was not memory-related.

## Rules

- **Never run `restart_comfyui.ps1` yourself without `-DryRun`.** Only the watchdog runs it, only inside an approved window. The guardrail hooks block any other call.
- **Outside an approved window** (for example stills under a no-approval policy), the watchdog may run with `--dry-run` to log VRAM, but it never restarts ComfyUI. Stop and report instead.
- **At the end of the window:** the watchdog exits by itself. Free memory (comfy-bridge skill), and include its events in the window report.

## Dry runs and tests

- `W simulate all` runs six scripted scenarios through the real state machine: normal job, stall, API down, memory not released, three halts, halt after the window. `--dry-run` shows the watchdog's own dry-run mode.
- `W watch --dry-run --window-minutes 5` watches the live ComfyUI but never ends or starts a process; it prints "would close and reopen".
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -File pipeline\watchdog\restart_comfyui.ps1 -DryRun` shows exactly which processes a restart would end, and the relaunch command.
- The live restart test (close, wait 15 s, reopen with ComfyUI.bat, API answers) runs once, in a window the user approves, with no job running. It is done before the first unattended window.
