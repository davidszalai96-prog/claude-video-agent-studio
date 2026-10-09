# Resolve setup and pipeline test (2026-09-29)

This covers the H3 music-video pipeline test for *Highscore* (Teminite & Panda Eyes). Lyrics are intentionally not reproduced here; the notes use timing and structure only.

## 1. Default Resolve folders on C: (read-only check)

Resolve 20.3 is installed on **D:** (failing drive), but all of its data lives on **C:**:

| What | Where | Found |
|---|---|---|
| Project library | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Resolve Project Library\Resolve Projects\Users\guest\Projects` | **17 projects**: dávid, feint laurence visualizer, Fight coreography, Gemini, Highscore, Levi, Magic, Okaerinasai, sliding in the 90s, The Jetsons + ZZZ, Underclass Hero, Untitled Project 1–6 |
| Preferences | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Preferences` | present |
| Support data | `%APPDATA%\...\Support\` | .crashreport, .LUT, ACES Transforms, DolbyVision, easyDCP, Fairlight, Fusion, logs |
| Render cache | `C:\Users\%USERNAME%\Videos\CacheClip` | 14 project cache folders + `audio` |
| Gallery stills | `C:\Users\%USERNAME%\Videos\.gallery` | 15 project folders |
| Auto project backups | `C:\Users\%USERNAME%\Videos\Resolve Project Backups` | 10 project folders |
| System-wide data | `C:\ProgramData\Blackmagic Design\DaVinci Resolve\{Fusion,Support}` | folder structure only, **0 files** (checked by the backup run) |
| `C:\Program Files\Blackmagic Design` | **does not exist** | the panel drivers are in `C:\Program Files (x86)\Blackmagic Design\DaVinci Control Panels` |

`Videos\Captures` is Windows Game Bar, not Resolve.

**What this means for a C: install:**

- The installer doesn't overwrite projects. The library, prefs, cache and backups stay where they are, and the new install uses them.
- ~~The installer removes the D: copy~~ Corrected by the backup run: the D: copy (20.3.0.10) is **not registered with Windows** (no uninstall entry, no Resolve registry key, no ProgramData files). So a fresh 21.0.4 install on C: most likely leaves D: alone. Confirm after installing.
- Risk: opening a project in **21.x** means **20.3.x can no longer open it**. The library itself stays 20.3.2-compatible (Blackmagic, Resolve 21 release notes). Back up first with Project Manager → library → Back Up and/or Export Project (.drp), saving to C:.

## 2. Which Resolve for the MCP (samuelgursky/davinci-resolve-mcp v4.8.x)

| Build | MCP access | Transitions / speed via API |
|---|---|---|
| Free 20.3.x or 21.0.x | In-app bridge (Workspace ▸ Scripts ▸ resolve_bridge; measured on free 21.0.3.7) | Not directly. An imported OTIO carries dissolves, speed **and keyframes** (measured on 21.0.4, section 10) |
| **Free 21.1+** | **No.** Blackmagic moved the Python API to Studio in 21.1 (2026-09-08); free keeps only the interactive console | — |
| Studio 21.1+ ($295 one-time) | External scripting, **plus Blackmagic's own native MCP server** (Studio-only) | Yes: native AddTransition, SetSpeed, SetFades |

Everything the MCP installs lands on C: (managed copy in AppData, bridge script in Fusion\Scripts\Utility, Claude Desktop config). Windows note: the installer sets PYTHONHOME to avoid a Resolve 20.3 multi-Python crash (issue #26). Don't let Resolve auto-update a free install to 21.1+.

## 3. Song grid: Highscore, excerpt 1:54–3:24 (measured locally)

- **110.0 BPM**, constant. Beat grid starts at 0.498 s (1:54.000 is exactly beat 209). Kick is on beats 1 and 3. Bar = 2.182 s, 8-bar phrase = 17.45 s.
- Phrase starts (song time): **1:56.13, 2:13.59, 2:31.04, 2:48.50, 3:05.95**.
- Events:
  - 2:11.41 = one-bar bass cut.
  - 2:28.86 = one-bar dip.
  - 2:31.04 = new section (mids drop, vocals stop; 16 bars).
  - 3:05.95 = section with a bass change and vocals back.
  - **3:23.41–3:25.59 = one full bar of silence**, and the next drop hits at 3:25.59.
- Vocal stem (UVR MDX-Net Voc_FT): no sustained sung lines in this excerpt, only 16 short pitched bursts (0.15–0.7 s), consistent with vocal chops.
  - Clip-time onsets: 2.26, 3.34, 3.89, 6.64, 7.22, 11.54, 12.09, 15.39, 16.33, 19.27, 28.72, 72.12, 75.45, 77.18, 79.28, 85.63 s.
  - None between 29 s and 72 s.

## 4. Gemini video report vs the real clip (MiniMax_H3_00308_.mp4)

The clip is 1504×832, 24 fps, 362 frames, and 10 real shots (9 hard cuts). Gemini listed 11 shots: its shots 6 and 7 are one shot joined by a whip-tilt.

| Cut | Measured | Gemini | Error |
|---|---|---|---|
| 1→2 | 3.333 s (f80) | 3.200 | −133 ms |
| 2→3 | 5.542 (f133) | 5.400 | −142 ms |
| 3→4 | 8.000 (f192) | 8.000 | 0 |
| 4→5 | 9.125 (f219) | 9.100 | −25 ms |
| 5→6 | 10.583 (f254) | 10.400 | −183 ms |
| 6→7 | 11.375 (f273) | 11.200 | −175 ms |
| 7→8 | 12.208 (f293) | 12.000 | −208 ms |
| 8→9 | 13.125 (f315) | 13.000 | −125 ms |
| 9→10 | 14.042 (f337) | 13.900 | −142 ms |

- **Timing:** Gemini is always early or exact. The median error is 142 ms (about 3–4 frames), so its timecodes are usable for meaning but not for cutting.
- **Semantics:** correct everywhere, including the door-kick timing, the spaghetti tilt-down, the heel slip, the plates in the air, the applause and the top-down finale.
- **Motion:**
  - Shot 2 screen direction is **reversed**. The camera trucks left at about 480 px/s and the waitress walks right-to-left; Gemini said left-to-right. Two methods agree (optical flow and phase correlation).
  - Shot 1 camera pulls back as she advances; Gemini called it static then a push-in.
  - The top-down finale has a slow push or expansion; Gemini called it static.
- **Local detectors:** PySceneDetect AdaptiveDetector found 8/9 cuts with 0 false positives. ContentDetector had 5 false positives from whips, tilts and foreground wipes. Contact-sheet verification settled every boundary.

## 5. Gemini audio transcription

- Prepared one structured request: the 90 s excerpt as 16 kHz mono FLAC, asking for JSON with vocals, sections, events and notes, and "do not fill lyrics from memory". The sandbox can reach `generativelanguage.googleapis.com` after the allowed-domain change.
- On 2026-09-29, around 18:02–18:11, every free-tier flash model returned **503 "high demand"**: 3.8, 3.7 and 3.5, including a text-only ping and the Interactions API. `gemini-2.5-flash` returns 404 for new users, and `gemini-omni-*` has a free-tier limit of 0.
- Retried at 18:54 and 19:34: still 503. Background mode (Interactions API `background: true`) rejects audio, because it routes to `gemini-3.8-flash-agent`, which has no audio input.
- Scoring plan (ready in the session scripts): compare Gemini's vocal entries to the stem chop onsets above, and its section and event times to the phrase grid.
- Batching plan for video analysis: up to 10 clips per request, which is 1 of the 20 free requests a day. Not as a .zip: each clip goes in as its own video part, labelled by filename, and the whole request must stay under 100 MB (shrink the clips or use the Files API). At about 25k tokens per clip at 6 fps, 8 clips is about 200k tokens, which fits the 250k/min cap; 2–3 fps is enough.

## 6. Resulting pipeline

1. Local song grid and vocal stem.
2. Local shot detection with contact-sheet check.
3. Optical-flow motion and screen direction.
4. Gemini for semantics only, as one JSON request per clip, snapped to the local timings.
5. Edit plan on the bar and phrase grid.
6. ffmpeg preview.
7. Deliver to Resolve by build, per section 2: OTIO/.drt import plus MCP live for grades, Fusion, markers and render.

Skills saved: `resolve-music-video` (this pipeline) and `resolve-edit` (adapted from the MCP repo, with a 21.1 speed/transition correction).

## 7. Backup of the Resolve setup (done and verified 2026-09-29, 19:59)

`C:\DavinciResolveBackup` was made by `backup_resolve.ps1`, run by the user. Robocopy only read the sources; D: was read last and nothing was written to it (apart from last-access timestamps).

| Set | Files | Size | Check |
|---|---|---|---|
| AppData Blackmagic Design (17 Project.db, prefs, Fusion, LUT cache, logs) | 219 | 98 MB | SHA-256 source = backup for all 219 |
| Videos\Resolve Project Backups | 20 | 0.2 MB | SHA-256 |
| Videos\.gallery | 14 | 1 KB | SHA-256 |
| Videos\CacheClip | 215 | 75 MB | count + size + time |
| D:\Program Files\Blackmagic Design (Resolve 20.3.0.10) | 2,873 | 4.07 GB | count + size + time |
| Registry (HKCU/HKLM Blackmagic Design) + installed-products list | 4 files | — | exported |

Other findings:

- ProgramData and Documents Blackmagic folders are empty; AppData\Local and C:\Program Files Blackmagic folders don't exist.
- Installed Blackmagic products: DaVinci Resolve Control Panels 2.3.4.0 and Blackmagic RAW 5.1 only.
- Integrity later: run `backup_resolve.ps1 -Mode check`, which re-hashes the backup against the saved manifests.
- C: had 163 GB free.
- The PC has Node 26.8.1, npm 11.19 and git 2.53. Python is only the Microsoft Store alias, so the MCP needs a real Python 3.12.

## 8. Next: Resolve 21.0.4 free on C: + MCP

1. **Download:** DaVinci Resolve 21.0.4 (05 Aug 2026), the last free build with Python scripting: https://www.blackmagicdesign.com/support/download/f1b3986a11634684b538ff3d1d4b55d6/Windows
2. **Install:** run the installer with the default path on C:. Decline any update to 21.1.
3. **MCP:** run `setup_resolve_mcp.ps1`. It installs Python 3.12 (winget), runs `npx davinci-resolve-mcp setup --clients claude-desktop`, installs the bridge, and writes `C:\ResolveMCP\status.json`.
4. **Connect:** restart Claude Desktop. In Resolve, make a **new test project**, then Workspace ▸ Scripts ▸ resolve_bridge.

**Update (20:50):** Resolve 21.0.4 was installed to **`C:\DavinciResolve`**, not the default Program Files path. The API docs and modules are in the usual `C:\ProgramData\...\Support\Developer\Scripting`. The old D: 20.3 install is still there, untouched by the installer.

- Pitfall: when the default path is missing, the MCP's library discovery probes **every drive** for `Blackmagic Design\DaVinci Resolve\fusionscript.dll`. On this PC that would find the **old 20.3 on D:**.
- Fix: `setup_resolve_mcp.ps1` now auto-detects the install folder and sets `RESOLVE_SCRIPT_LIB=C:\DavinciResolve\fusionscript.dll` and `RESOLVE_SCRIPT_API` before setup. It then checks, and if needed corrects, the `davinci-resolve` entry in Claude Desktop's config, keeping a backup of the config first.
- The MCP's auto-launch and restart of Resolve are hard-coded to `C:\Program Files\...\Resolve.exe`, so with this folder Resolve must be started manually from `C:\DavinciResolve\Resolve.exe`. Starting it manually is needed for the free bridge anyway.

**Delivery note:** this chat client can't download `.ps1` files. So scripts are written straight onto the PC in `C:\ResolveMCP` (a connected folder), each with a double-click `.cmd` launcher:

- `Run_MCP_Setup.cmd` runs `setup_resolve_mcp.ps1`.
- `Check_Backup.cmd` runs `backup_resolve.ps1 -Mode check`.

The first setup attempt (20:50) stopped at step 1 because Resolve wasn't at the default path. Nothing was installed then.

## 9. MCP connected (2026-09-29, ~21:20)

- `resolve_control get_version` answers over the free-edition bridge: **Resolve 21.0.4.5**, MCP **4.8.22** (up to date). 25 surfaces are absent on this build, all of them 21.1 additions (AddTransition, SetSpeed, SetFades, GetType, multicam, output blanking and others).
- **Why `resolve_bridge` was missing:** Resolve's `fusionscript.dll` finds Python 3 through the `PYTHON3HOME` env var, then the registry (`Software\Python\PythonCore\<ver>\InstallPath`). It does **not** use PATH. The registry only listed a Microsoft Store Python 3.12, which Resolve can't load. Fix: the user env var `PYTHON3HOME=C:\Program Files\Python312`. The earlier PATH change was offered for undo.
- Each session: open a project, then Workspace ▸ Scripts ▸ resolve_bridge. It's listed twice (user and all-users folders); run one, once.
- Open project at connect time: **Highscore**, upgraded to 21 by the user. Timeline 1 is 24 fps, 1280×720, 3 video + 4 audio tracks, 21 items. The media pool has 18 items: 14 H3 clips with audio, 1 audio file, 2 renders and the timeline. Tests should run on a duplicated timeline.

## 10. First test edit: beat pulse at 01:56:03 (2026-09-29, ~22:00)

**Brief:** in a duplicate of Timeline 1, rework the V2 clip at 01:01:56:03 to pulse on the beat, discarding its zoom, and use at least one transition, one speed change, fades and zoom. It was done blind: no vision and no Gemini, only timeline data and the song grid.

**Slot:**

- 89187–89239 is 52 frames, one bar at 110 BPM, starting on the bar-53 phrase downbeat (116.13 s).
- Beats fall on relative frames 0, 13, 26 and 39, and the next downbeat is 52, a hard cut to V1/V3.
- The original clip was MiniMax_H3_00295_.mp4 (1152×640), src 206–257. It had a zoom keyframe punch, 3.48 → 1.0 over its first 4 frames, which the static readback showed only as ZoomX 1.12.

**Built:**

- The nested timeline **"Pulse insert 0156 (Claude)"** (bin "Claude test") replaces the clip on V2, 89187–89239. Nothing else changed.
- Inside it:
  - A = src 206–231 at 100% (beats 1–2).
  - A **6-frame Cross Dissolve** is centred on beat 3.
  - B = src 219–231 at **50%**, optical flow with Enhanced Better. It's a slow-motion replay of A's second half across beats 3–4.
  - **Zoom keyframes on every beat:** 1.15 on the downbeat, 1.10 on beat 3 (the kick), and 1.06 on beats 2 and 4. Each decays by ×0.6 per frame back to 1.0.
  - **Opacity keyframes:** a fade-in from black over 4 frames (15 → 100%), and a fade-out over the last 6 frames (100 → 10%) into the hard cut on the next downbeat.

**Route** (21.0.4 free has no AddTransition, SetSpeed, SetFades or AddKeyframe):

1. Export the timeline with EXPORT_OTIO to learn Resolve's own shape.
2. Author a Resolve-shaped OTIO:
   - Clip.2 items, a Transition.1 (`SMPTE_Dissolve`, in/out offset 3) and LinearTimeWarp.1 with `time_scalar` 0.5.
   - `Resolve_OTIO` effect metadata carrying `"Key Frames"` for Transform (`transformationZoomX/Y`) and Composite (`opacity`, scale 0–100).
3. Import it with `import_timeline_checked` (importSourceClips=True, sourceClipsPath).
4. Place the new timeline's pool item on V2 with AppendToTimeline.

**Key finding: the OTIO importer on 21.0.4 honours `Resolve_OTIO` effect keyframes.** A re-export returned every key unchanged.

- Keys are clip-relative record frames: 0 is the clip's first frame. Negative keys are allowed and are needed to cover a transition's pre-roll.
- Only non-default parameters are written. The IDs used here are `transformationZoomX/Y` (Transform, Type 2) and `opacity` (Composite, Type 1).
- IDs for other parameters: set a static value via the API, export OTIO, and read the ID.
- The Edit-page fade handles are the "Video Faders" effect, whose parameter IDs aren't known yet.

**Render check.** A render of 89181–89244 was compared with a plain render of src 200–261:

- **Zoom:** matched the plan within 0.0002 on all 34 frames where it could be measured.
- **Opacity:** matched within 0.01 (fade-in 0.15 / 0.40 / 0.65 / 0.84; fade-out 0.85 / 0.55 / 0.25).
- **Dissolve:** renders as a linear blend. B's share is 0.25 / 0.58 / 0.92 at frames 24 / 26 / 28, so it isn't inert.
- **Slow-mo:** B shows src 219 + (t−26)/2, and the in-between frames are synthesised, neither duplicated nor blended.
- **Audio:** the render's audio sits **~51 ms later** than the song decoded by ffmpeg. The likely causes are Resolve playing the mp3 without its 25 ms encoder-delay trim, plus about 21 ms of AAC priming (the render's audio edit list is 0). As a result, beats are heard about 1 frame after the zoom-peak frame starts, which is acceptable. For frame-exact work, put a WAV of the song on the timeline.

**MCP gotchas met:**

- `append_to_timeline` record_frame is relative to the timeline start. A top-level `record_frame_mode` was ignored, and the first placement landed at 175587; it was deleted.
- Nearly every mutating call auto-archives the timeline, and `begin_run` did not thread them.
- `delete_timelines` needs a confirm token.
- A render job leaves In/Out marks on its timeline.

**Left in the project:**

- Bin "Claude test": the insert timeline, a second pool copy of 00295 (made by the OTIO import) and a scratch reference timeline, all disposable.
- Bin "Archive": the MCP auto-archives.
- On disk: `C:\ResolveMCP\interchange` (OTIOs) and `C:\ResolveMCP\verify` (two short MP4s).
