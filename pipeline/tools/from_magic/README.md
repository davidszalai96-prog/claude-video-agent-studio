# Tools from the Nhato "Magic" edit (reference copies)

Copied on 2026-10-10, unchanged, from `C:\CU\output\video\Nhato Magic - Video-edit\edit\` (`tools\*.py` and `gemini\prompt_*.md`). The originals and the Magic folder were not touched. No media, run scripts or logs were copied. The files contain no keys and no lyrics (checked before copying).

They are **references, not studio tools yet**. The Pipeline TD adopts what is useful in Phase 2:
- generalize hard-coded paths and song names;
- move the code into `pipeline/tools/`;
- add tests;
- install the dependencies the studio venv lacks.

Until then, no agent runs them as they are.

| File | What it does (from its docstring) | Needs | Hard-coded |
| --- | --- | --- | --- |
| `tools/cands.py` | Rows of `clip:frame` items, frames f-2..f+3, to compare cut candidates | PIL, OpenCV | Windows Consolas font |
| `tools/clip_sim.py` | CLIP ViT-H-14 image embeddings per shot → shot similarity | torch, open_clip, transformers, safetensors, scipy, OpenCV | `C:\CU\models\clip_vision\clip-vit-h-15-laion2b-s32B-b79k.safetensors` |
| `tools/cutsheet.py` | `edit/cut_sheet.md`: one line per section plus the frame-exact beatmap | stdlib | Magic title and excerpt times |
| `tools/dense.py` | Dense contact sheets: every STEP frames, 10 per row, frame number and shot ID | PIL, OpenCV | Consolas font |
| `tools/drop_map.py` | Beat-by-beat map of the cut window from the stems → `edit/music/drop_map` | librosa, soundfile, numpy | `music/Nhato - Magic.beats.json` |
| `tools/make_plan.py` | Shot plan (source frames + beats) → `edit/plan.json` for video-use's `beatmap.py`, with a lint | numpy | song path, start bar 58, 1280×720 |
| `tools/motion.py` | Per-frame motion energy and luma per shot → `edit/shots/motion.json` | OpenCV, numpy | — |
| `tools/selfcheck.py` | Self-eval of a render against `edl.json`: cut accuracy, stray jumps, sync | PIL, OpenCV, numpy | song path, Consolas font |
| `tools/stems.py` | HDemucs (`HDEMUCS_HIGH_MUSDB_PLUS`) stems for part of the song | torch, torchaudio, soundfile | song window |
| `tools/strip.py` | Thumbnail grid: rows = clips, columns = given frames | PIL, OpenCV, numpy | Consolas font |
| `gemini/prompt_song.md` | Gemini prompt: sections, events, energy curve, bass character of a song excerpt (audio only, no lyrics) | — | — |
| `gemini/prompt_clips.md` | Gemini prompt: per-shot visual inventory of AI clips (framing, action, camera, key moments, artifacts) | — | — |
| `gemini/prompt_critique.md` | Gemini prompt: strict critique of a cut (sync, static shots, repeats, artifacts, flashes, watermarks) | — | Magic's 41 s length and 9.4 s build-up |

The Magic edit itself is the worked example of the video-use route: `edit/project.md`, `plan.json`, `edl.json`, `beatmap.md`, `cut_sheet.md`, `shots/` and `music/` in that folder. See the `video-use-studio` skill.
