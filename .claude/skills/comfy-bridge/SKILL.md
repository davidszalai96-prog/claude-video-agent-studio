---
name: comfy-bridge
description: How the studio reaches ComfyUI - the studio's own Chrome tab, the page recipes (load a saved workflow, apply an attention profile, graphToPrompt), the loopback receiver, workflow manifests and default profiles, and the read-only shell client for status, progress, environment pin and update checks. Use for any manifest work, workflow conversion, ComfyUI monitoring, or before queuing anything.
---

# ComfyUI bridge

ComfyUI (0.37.0, frontend 1.53.6 on 2026-10-09) is shared with the user's other work. The studio converts and queues in **its own Chrome tab**, and monitors from the shell. Rules in `CLAUDE.md` come first:
- the project's recorded approval policy;
- one GPU job at a time;
- never touch the user's tab or saved workflow files.

| Piece | File | Who uses it |
| --- | --- | --- |
| Page recipes (`window.studio`) | `pipeline/comfy/bridge/page_recipes.js` | Render Wrangler, Pipeline TD |
| Loopback receiver (page → disk) | `pipeline/comfy/bridge/receiver.py` | same |
| Shell client (read-only) | `pipeline/comfy/bridge/comfy_api.py` | Render Wrangler, watchdog, Pipeline TD |
| Manifests, profiles, snapshots | `pipeline/comfy/manifest_tool.py`, `manifests/`, `profiles/`, `snapshots/` | Pipeline TD (writes), Render Wrangler (reads) |
| Environment pin | `pipeline/comfy/env_pin.json` (`comfy_api.py pin --write`) | Pipeline TD |

All Python runs with `.venv\Scripts\python.exe`.

## The studio tab

- **The user opens it.** ComfyUI answers 403 to any request marked `Sec-Fetch-Site: cross-site` (`C:\CU\server.py`, origin_only_middleware), and Chrome marks navigations started by the extension that way. So the user types `http://127.0.0.1:8188` into a tab of Claude's tab group, once.
  - After that, page scripts run normally, and `location.reload()` from the page works.
  - Never ask to disable that protection or change ComfyUI's launch flags.
- **Find the tab** with `tabs_context_mcp` at the start of every session. Tab IDs and the tab group change when the extension reconnects. If the group is gone, ask the user to open the studio tab again.
- **Never use the user's own ComfyUI tab.** The studio tab shows progress and the preview node for every studio job, because jobs are queued from it with its own client ID.
- **Load the recipes** after each page load: read `page_recipes.js` and evaluate its whole text with `javascript_tool`. ComfyUI's page object is the global `app`, and `studio.ready()` must be true.
- **Leftovers:** `studio.load()` opens each workflow as a temporary "Unsaved Workflow (n)" in the studio tab. They are harmless. Don't save them, and don't close the tab while a beforeunload prompt could appear.
- **Reading results:** the extension's output filter hides strings that look like tokens. File names with several dots show up as `[BLOCKED: JWT token]`. Read results from disk, not from the tool output.

## Moving data from the page to disk

1. Start the receiver in the background before the page sends anything:
   `... receiver.py --out pipeline/comfy/incoming --max <n> --timeout <s>`
   It listens on 127.0.0.1:8199 only, accepts only the ComfyUI page's origin, writes only inside the repo, and exits after `--max` files or `--timeout` seconds.
2. In the page, call `await studio.send("<name>.json", data)`.
3. `pipeline/comfy/incoming/` is ignored by git, because raw output holds per-job prompts. Ingest it, then delete it.

## Making a manifest for a project template (Pipeline TD)

1. `manifest_tool.py list` lists the saved workflows, newest first, and marks those that already have a manifest.
2. `manifest_tool.py inspect <template>` shows the MODEL chain with attention roles, per-job candidates, savers, seeds and broadcast nodes.
3. `manifest_tool.py init <template> --kind h3|krea|other` writes a draft.
   - For H3 it detects the prompt, references, seed, duration, megapixels, output, preview node, attention nodes and the `sol` / `chunked` / `sage` profiles.
   - For Krea and other templates, fill in `per_job`, `forced` and `wiring` by hand. Every `forced` and `wiring` entry names its source (a skill section or a user decision), and records the `saved_value` it replaces.
4. In the studio tab, convert the template as saved, and for H3 also with `sol` and `chunked` (`manifest_tool.py modes <id> <profile>` prints the modes):
   `await studio.send("<T>.as_saved.json", await studio.convertTemplate("<T>"))`
   `await studio.send("<T>.sol.json", await studio.convertTemplate("<T>", {profile: <modes>, label: "sol"}))`
5. `manifest_tool.py ingest <id> pipeline/comfy/incoming/<T>.<label>.json` for each file. This writes a snapshot with per-job values replaced by `<per_job:name>`, a config hash and, for as-saved, the default profile. It verifies that each profile's bypassed nodes are absent from the prompt and its enabled nodes present.
6. `manifest_tool.py check <id>`: every line must be PASS. A new template stays `unmeasured` until a smoke test in an approved window measures it.

The saved file's SHA-256 is in the manifest. If the user re-saves the workflow, `check` fails until the manifest is re-drafted and re-ingested.

Manifests done on 2026-10-09:
- `H3regenrunsTest`: saved as `sage`; 25 API nodes.
- `H3ultRefsTest2`: saved as `chunked`; 3 references.
- `H3regensElements`: Krea, with the §7 patches from `h3-gacha-pipeline`.
  - Node 13 is saved at 1920×1080; the manifest forces 2560×1440 as the skill records.
  - `56:54.switch` is saved wired to `56:50`, and the skill's patch forces it to `false`.

## Converting a job (Render Wrangler)

- Load the job's template.
- Set the attention profile's modes (H3 only; `sol` unless the project switched to `chunked`).
- Run `graphToPrompt`.
- Set the `per_job` values from the job spec, then apply `forced` values and `wiring`.
- Record the config hash (`manifest_tool.config_hash` over the prompt with per-job placeholders) with the take.
- Leave every other value as saved, preview node included.

**Queuing is not available yet.** It arrives behind the guardrail hooks (Phase 1, step 8). Until then nothing is queued from the page or the shell.

## Monitoring from the shell (read-only)

- `comfy_api.py status`: version, launch arguments, VRAM, queue, last sampler progress.
- `comfy_api.py logs --progress`: the newest progress line, e.g. `{"step": 12, "total": 28, "age_s": 41}`. ComfyUI keeps only the latest state of a progress bar and re-stamps it on every step, so `age_s` is the time since the last sampler step. The watchdog uses it.
- `comfy_api.py wait <prompt_id> --timeout 600 --every 60` blocks for at most 10 minutes per call. `history` and `outputs` read results.

## Before any studio job: the update checks

The user updates ComfyUI for other work too. Run `comfy_api.py checks`; it must be all PASS:
- the API answers;
- the environment matches the pin;
- the console-log feed works;
- every node class the manifests need is installed.

Then run `manifest_tool.py check <id>` for each template in the job list. On any FAIL, queue nothing and report what changed. The Pipeline TD re-pins (`comfy_api.py pin --write`) and re-converts only after the user knows about the update.
