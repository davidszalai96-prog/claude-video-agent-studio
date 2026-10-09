---
name: "resolve-music-video"
description: "Plan and build DaVinci Resolve music-video edits from MiniMax H3 (ComfyUI) clips: beat-synced cuts, transitions, effects and shot continuity, using local audio/shot analysis, Gemini for semantics, and timeline files or the Resolve MCP."
---

# Music-video editing in DaVinci Resolve (H3 footage)

Use for any music-video edit, song analysis, H3 clip analysis or Resolve timeline task in this project. Check the project doc `claude/resolve-setup-and-pipeline-test.md` for the latest measured findings before starting. The project file `claude/otio_keyframe_insert.py` is a working generator for keyframed OTIO inserts.

## Hard constraints on the user's PC (Windows, device "desktop-lmpr7go")

- **D: is failing (CrystalDiskInfo).** Never write, render, cache, export, install or relink anything to D:. Don't read from D: unless the user asks.
- Resolve data is on C: — project library `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Resolve Project Library`, plus `C:\Users\%USERNAME%\Videos\{CacheClip,.gallery,Resolve Project Backups}`. As of 2026-09-29 the library holds 17 projects (incl. "Highscore"). Never open an existing project in a newer Resolve build without a `.drp` export or library backup first. Projects opened in 21.x can't be reopened in 20.3.x.
- Footage: H3 clips live in `C:\CU\output\video\` (the Highscore project uses these) and a curated set in `C:\CU\output\video\H3 keepers\` (the only one connected for staging). 24 fps, AAC 32 kHz, ~15 s (362 frames), start TC 00:00:00:00. **Resolution varies** (1504×832 and 1152×640 seen), so read `get_clip_property` rather than assuming. **Each clip is a multi-shot sequence** (~10 hard cuts per 15 s), so the edit means sub-clipping. Highscore's Timeline 1 is 1280×720 @ 24 fps.
- Gemini: free tier (user's limits: 5 requests/min, **20 requests/day**, 250k tokens/min), so requests are the scarce resource. Batch clips (see "Gemini batching" below). Default model is `gemini-3.8-flash`. On a 503 ("high demand") it's a capacity problem, not quota, so back off 10+ min or try later; it lasted 1.5 h+ on 2026-09-29. On the free tier, `gemini-2.5-flash` returns 404 and `gemini-omni-*` has a limit of 0. Background mode (Interactions API `background: true`) rejects audio. The sandbox needs `generativelanguage.googleapis.com` on the allowed-domains list. Never put the API key in the project, skills or deliverables. Prefer a key file in a connected folder on the user's PC that scripts read by path and never print, over pasting the key in chat.
- Never reproduce song lyrics in replies, docs or files. Use timing and structure only.
- **No shell on the user's PC in this setup.** Computer use can only *click* in terminals and File Explorer (no typing), and there's no device shell tool. For anything that needs commands on the PC (backups, installers, MCP setup), write a PowerShell script. **The chat can't hand `.ps1` files to the user (downloads blocked)**, so write it straight onto the PC with `device_commit_files` into the connected folder `C:\ResolveMCP`, next to a double-click `.cmd` launcher (`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0x.ps1"`). Existing launchers: `Run_MCP_Setup.cmd`, `Check_Backup.cmd`, `Set_Python_For_Resolve.cmd`. It writes JSON/CSV logs, which you read back with folder access (`device_stage_files`). Test scripts first with `pwsh` in the sandbox (GitHub release tarball), using mocks. Watch for PowerShell's case-insensitive variable names (`$sets` == `$Sets`). `device_commit_files` only takes files from `/mnt/user-data/outputs/` (cp there via bash so they don't pop up in chat); it can't create an empty folder, so commit a small README to make one.
- Resolve backup (verified 2026-09-29): `C:\DavinciResolveBackup`, made by `backup_resolve.ps1` (plan → copy → verify). It holds all 17 projects, prefs and Fusion data (SHA-256 matched), project auto-backups, gallery, CacheClip, the D: install (2,873 files, 4.07 GB) and the registry keys. Running the same script with `-Mode check` proves the backup is unchanged. Never add the backup folder as a Resolve project library, because Resolve would write into it.
- The old Resolve 20.3.0.10 on D: is **not registered with Windows** (no uninstall entry, no ProgramData files). The 21.0.4 install on C: left it in place (confirmed 2026-09-29). The panel drivers live in `C:\Program Files (x86)\Blackmagic Design\DaVinci Control Panels` and aren't in the backup. Windows last-access updates are ON, so reading D: causes tiny metadata writes.
- **MCP setup (working since 2026-09-29):** Resolve **21.0.4.5 free** is installed at **`C:\DavinciResolve`** (custom folder), and the MCP is `samuelgursky/davinci-resolve-mcp` 4.8.22 over the free-edition bridge.
  - Pin the scripting library. The Claude Desktop config env has `RESOLVE_SCRIPT_LIB=C:\DavinciResolve\fusionscript.dll`. Otherwise the MCP's drive scan finds the old 20.3 `fusionscript.dll` on the failing D: drive.
  - The MCP's auto-launch and restart only know `C:\Program Files\...`, so the user starts Resolve from `C:\DavinciResolve\Resolve.exe`.
  - **Python for Resolve on Windows:** `fusionscript.dll` reads the `PYTHON3HOME` env var, then the registry (`Software\Python\PythonCore\<ver>\InstallPath`) — **not PATH**. This PC's registry lists only a Microsoft Store Python 3.12 that Resolve can't load, so the user env var `PYTHON3HOME=C:\Program Files\Python312` is what makes `.py` scripts list. Symptom when broken: only `resolve_bridge_canary` (Lua) shows in Workspace ▸ Scripts.
  - **Each Resolve session (also after every Resolve restart):** open a project, then Workspace ▸ Scripts ▸ resolve_bridge. It's listed twice (user + all-users Scripts folders, identical); run one, once. Then `resolve_control get_version` should answer. The 21.1-only surfaces are absent (AddTransition, SetSpeed, SetFades, GetType, multicam, etc.), and so are `AddKeyframe`/`GetKeyframeCount`.
  - Decline in-app updates to 21.1+ (free 21.1 drops Python scripting).
  - The **Highscore** project was upgraded to 21 (its 20.3 copy is in the backup). For tests, work in a duplicated timeline or a new project. "Timeline 1 (Claude test)" is the test duplicate; bin "Claude test" holds Claude's inserts and scratch timelines.

## Pipeline that works (measured 2026-09-29)

1. **Song (local, free).** Decode with ffmpeg, then run librosa beat tracking and fit a constant grid. Compute per-bar band energies (sub <120 Hz, low, mid, high) to find section changes, bass cuts and silences. For vocal timing, separate a vocal stem with the UVR `UVR-MDX-NET-Voc_FT.onnx` model (GitHub release asset `TRvlvr/model_repo`; n_fft 7680, hop 1024, dim_f 3072, dim_t 256, compensate 1.021) on onnxruntime CPU, then run pyin voicing plus RMS on the stem.
   - Highscore (Teminite & Panda Eyes): 110.0 BPM constant; beat grid starts at 0.498 s; kick on beats 1+3. Bars start where (song beat index % 4 == 0). 8-bar phrases start at 116.13, 133.59, 151.04, 168.50, 185.95 s. 131.41 s is a 1-bar bass cut, 148.86 s is a 1-bar dip, and 151.04 s starts a new section (mids drop, vocals stop). 185.95 s starts a section with a bass change and vocals back. **203.41–205.59 s is a full bar of silence**, and the next drop lands at 205.59 s. 1:54.000 is exactly beat 209. In this section, vocals are short chops (0.15–0.7 s), not sung lines.
   - In Highscore's Timeline 1 the song is on A4 at 86400 with source start 0, so song time = (frame − 86400) / 24. A bar is 52.36 frames; beats inside a bar land at +0, +13, +26, +39 frames.
   - **Audio offset:** Resolve plays the mp3 later than ffmpeg's gapless decode, and its MP4/AAC renders add uncompensated priming. Measured together: the rendered audio is ~51 ms later than the grid. Sub-frame sync is fine as is (the beat lands about a frame after the visual hit). For frame-exact work, put an ffmpeg-decoded WAV of the song on the timeline. When checking sync in a render, cross-correlate against the source instead of trusting absolute onset times.
2. **Shots (local).** Run PySceneDetect `AdaptiveDetector` (found 8/9 real cuts with no false positives) plus frame-difference peaks. **Then verify every boundary on a contact sheet** of frames n-1/n. `ContentDetector` flagged camera whips, tilts and foreground wipes as cuts (5 false positives out of 14). Keep in-shot whip-pans and tilts as motion, not cuts.
3. **Motion (local).** Use Farneback optical flow at 376 px width per frame: the median (dx, dy) gives camera pan/tilt direction, and radial divergence gives push-in (+) or pull-out (-). Cross-check screen direction with `cv2.phaseCorrelate` on a background band. Keep screen direction consistent across cuts.
4. **Gemini (semantics only).** Ask for JSON per shot: action, subject and screen position, framing, the time of each impact moment (kick, slip, catch), continuity (wardrobe, props), and artifacts or unusable frames. **Treat its timecodes as ±0.25 s.** It ran 0–208 ms early (median 142 ms, about 3–4 frames), so snap to step 2. Never trust its left/right direction without step 3 (it reversed one tracking shot).
5. **Edit plan.** Put phrase starts and drops on hard cuts, impact moments on hits, and fast cutting in high-energy bars. Use the silences and bass cuts for holds, freezes or flash frames. Put match-on-action and motion-matched cuts where the flow vectors agree. Beat pulses: zoom punch on the beat frame, decaying ~×0.6 per frame; downbeat biggest (≈1.15), kick beats ≈1.10, backbeats ≈1.06.
6. **Preview first.** Render an ffmpeg preview with trim/concat, `xfade` transitions, speed changes, zoom punches and flash frames, so iterations are cheap.
7. **Deliver to Resolve.** Pick the route by edition and version:
   - **Free 20.3 / 21.0.x:** use the `samuelgursky/davinci-resolve-mcp` in-app bridge. Live API: place clips at exact frames; set **static** transform, crop, opacity, composite mode, retime *quality* (`RetimeProcess` 3 = optical flow, `MotionEstimation` 4 = Enhanced Better); markers; LUT/CDL/DRX grades; renders. No transitions, speed, fades, keyframes or razor through the live API. **Carry those in an imported OTIO** (see the next section), which carries dissolves, constant retimes and keyframes. The alternative is a `.drt` from the MCP's offline `drt.assemble_from_interchange` (cuts, dissolves, retimes, multi-track, audio; no keyframes).
   - **Free 21.1+:** Blackmagic moved the Python API to Studio (the free edition keeps only the interactive console), so the bridge won't work. Use file import only.
   - **Studio 21.1+:** Blackmagic's own native MCP server (Studio-only, since 21.1 on 2026-09-08), native `TimelineItem.AddTransition` (simple/Fusion/OFX by name), `SetSpeed` and `SetFades`, plus external scripting.
   - Edit-page ResolveFX aren't in the API. Deliver them as a DRX grade (Color-page nodes can hold ResolveFX), a Fusion comp, or a UI step.
8. **UI handoffs.** Name the operation, and don't invent menu locations. For UI-only steps, computer use is fine (one-offs such as importing a timeline, running the bridge, applying a transition to all selected edits). It's too slow to use for whole edits. To flatten a nested insert into the parent timeline, the user can use Decompose in Place.

## Keyframed effects, dissolves and speed on free 21.0.x (OTIO route, render-verified 2026-09-29)

This was proven on the 01:56:03 test edit: zoom within 0.0002, opacity within 0.01, a 6-frame dissolve blending linearly, and 50% optical-flow slow-mo. Generator: project file `claude/otio_keyframe_insert.py`.

1. **Learn Resolve's shape first.** `timeline export_timeline_checked` (format otio, `require_temp_path: false`, path under `C:\ResolveMCP\interchange`), stage it, read it.
   - It also reveals keyframes the live API hides. `get_transform` shows only a static value (e.g. ZoomX 1.12), while the clip actually carried keys 0: 3.48 → 4: 1.0.
2. **Author a Resolve-shaped OTIO:**
   - Timeline.1 with `global_start_time` 86400 @ 24.
   - One `Video 1` Track.1 with `metadata {"Resolve_OTIO": {"Locked": false}}`.
   - Clip.2 with a `media_references` map, `active_media_reference_key`, `available_range`, a bare Windows path in `target_url`, and timecode-absolute source frames.
3. **Effects on a clip:**
   - **Speed:** `LinearTimeWarp.1` with `time_scalar` (first in the list). `source_range.duration` is the RECORD length.
   - **Keyframes:** `Effect.1` with `effect_name: "Resolve Effect"` and `metadata.Resolve_OTIO` = {Effect Name, Name, Enabled, Display Type 1, Type, Parameters: [{Parameter ID, Parameter Value, Default Parameter Value, Variant Type "Double", minValue, maxValue, "Key Frames": {"<frame>": {"Value": v, "Variant Type": "Double"}}}]}.
   - Known IDs: Transform (Type 2) `transformationZoomX` / `transformationZoomY`; Composite (Type 1) `opacity` (0–100).
   - To find another ID, set a static value through the API on a throwaway item, export OTIO and read it.
   - **Key frames are clip-relative record frames.** 0 is the clip's first frame. A value before the first key holds the first key's value, so add keys at negative frames to cover a transition's pre-roll on the incoming clip. Give the outgoing clip keys through its tail handle.
   - Emit a key wherever the curve moves, plus both ends of every flat stretch. Interpolation isn't carried; linear between keys worked.
4. **Transitions:** `Transition.1`, `transition_type: "SMPTE_Dissolve"`, name "Cross Dissolve", with `in_offset`/`out_offset`. Keep the cut strictly inside the span, e.g. 3/3. Both clips need handles. Imported transitions enumerate as items named "Cross Dissolve".
5. **Fades:** use opacity keys over black. A single-sided OTIO transition at a gap won't import. The Edit-page fade handles live in the "Video Faders" effect, whose IDs aren't known yet.
6. **Import:** use `timeline import_timeline_checked` with `options {timelineName (unique), importSourceClips: true, sourceClipsPath: "C:\\CU\\output\\video"}` and `require_temp_path: false`.
   - Set the media pool folder first (bin "Claude test"). The import adds a second pool copy of the source clip there.
   - The transition counts as one "offline" item in the result; that's expected.
7. **Place into the edit:**
   - `timeline set_current` back to the target, then `timeline delete_clips` (ripple false) for the old item.
   - Then `media_pool append_to_timeline` with `clip_infos [{media_pool_item_id: <timeline pool id>, start_frame 0, end_frame N (exclusive), record_frame: <frame − 86400>, track_index, media_type 1}]`.
   - **record_frame is relative to the timeline start.** A top-level `record_frame_mode: "absolute"` was ignored and the clip landed 86400 frames late.
8. **Verify by render, not readback:**
   - Setup: `render prepare_render_job` with `from_preset "H.264 Master"`, mp4/H264, MarkIn/MarkOut and `require_temp_target: false` into `C:\ResolveMCP\verify`. Also render a plain scratch timeline of the same source range as the reference.
   - Zoom and opacity: fit per frame with `E ≈ a·zoom_s(R)`.
   - Dissolve: fit `E ≈ wA·A + wB·B`.
   - Retime: odd frames must differ from both neighbours.
   - Cleanup: delete the render jobs. The render leaves In/Out marks on the timeline.

**MCP housekeeping:**

- Most mutating calls auto-archive the current timeline (`<name>_archived_vNN`, created in the current bin); `begin_run` did not group them. Move archives to the "Archive" bin with `media_pool move_clips`.
- `delete_timelines` returns a confirm token (a user decision), so leave scratch timelines in "Claude test" and tell the user.
- Nested timeline items read back source frames 0..N−1.

## Gemini batching (free tier)

- One request can carry **up to 10 videos** (Gemini 2.5+). It counts as **1** of the 20 daily requests however many clips it holds.
- **Not a .zip.** Zip isn't an accepted input type. Send each clip as its own video part (`video/mp4`), each preceded by a text part naming the file. Ask for one JSON object per clip, keyed by filename, so clips can't be mixed up.
- Size: inline requests must stay **under 100 MB total**, and base64 adds about 33%. Either shrink the clips first (`ffmpeg -vf scale=752:-2 -c:v libx264 -crf 28 -c:a aac -b:a 96k`; Gemini samples frames at low resolution anyway) or upload with the Files API (2 GB per file on free) and reference the URIs.
- Tokens: the user's Codex run used about 25k tokens for one 15 s clip at 6 fps, so 8 clips come to about 200k. That fits the 250k/min cap with little headroom. Exact cut timing comes from local detection, so 2–3 fps is enough for semantics (roughly halves tokens). Set it per clip (`videoMetadata.fps` in generateContent, `processing.fps` in Interactions) and keep 6 fps only for fast-action clips.
- Prompt per clip: shots with rough in/out, action, subject screen position, camera move, impact moments, continuity (wardrobe/props), and artifacts or unusable ranges. Treat every timestamp as approximate, and snap to local shot detection and frame strips.
- If a batch fails with 503, retry the same batch later. Don't split it into more requests.

## MCP session start (once the MCP is installed)

Confirm the Resolve build and edition, and whether you're on the bridge or external scripting. Read the list of what this build can't do (`resolve_control get_version` → `build.unavailable_on_this_build`). Report the project, timeline fps and resolution, and the media pool shape. Don't edit until the user confirms. Probe methods with `name in dir(obj)`, never `hasattr`. Before editing a clip, export OTIO to see its real keyframes and retimes.