---
name: "gemini-video-review"
description: Send video files to the Google Gemini API for frame-level analysis (shots, cuts, camera moves, actions, effects, physics, artifacts, audio) and review the result against the prompt or storyboard that produced the video. Use this whenever the user wants a video analyzed, reviewed, QA'd, described or checked with Gemini, including AI-generated clips (MiniMax H3, ComfyUI, Veo, Kling, Wan, Sora and similar), renders, edits and footage. Trigger on phrases like "send this to Gemini", "analyze the video", "what went wrong in this generation", "check the clip against the prompt", "compare these renders", or batch reviews of several clips, even when Gemini isn't named but a video needs a close, timestamped look. Works on any video path in any project; it needs no editor or other app.
---

# Gemini video review

Two scripts, used together:

- `scripts/gemini_video.py` sends one or more videos to Gemini and saves a JSON report per video. Standard library only.
- `scripts/frames.py` pulls frames into labeled contact sheets (and optionally lists cut times) so you can look at the video yourself.

Gemini watches every sampled frame and hears the audio, so it is fast and thorough. It also makes mistakes: timestamps drift by a few tenths of a second, it can swap left and right, and if it is told what to expect it tends to report seeing it. Your own look at the frames is the check on it. A good review uses both.

## 1. Before running anything

**Files.** Claude Code's shell runs on the user's PC, so use real paths:
- `<footage folder>\units\…` for studio takes (the project's footage folder, recorded in its `00_admin/approvals/policy.json`);
- `C:\CU\output\video\…` for earlier clips.

Never read from D:. If a file is somewhere this session can't reach, say so plainly. Don't build a workaround through an unrelated app such as a video editor's script menu; it is fragile and hard for the user to repeat.

**Where reports go.** Always pass `--out`, because the scripts otherwise write next to the video:
- for a studio take: `projects/<CODE>/06_dailies/<TAKE>/` (reports) and `…/sheets/` (contact sheets);
- outside a project: Claude Code's scratch folder.

The studio may write only inside this repo and each project's footage folder.

**Network.** The script calls `https://generativelanguage.googleapis.com` directly from this PC.

**Tools.** Run the scripts with the studio venv, `.venv\Scripts\python.exe`; bare `python` is the Microsoft Store alias.
- `gemini_video.py` needs only the standard library.
- `frames.py` needs ffmpeg (on PATH) and Pillow for the contact sheets. Pillow arrives with the venv's media stack; install it first if it's missing.

## 2. The API key

The key must never pass through the conversation. Once it is in the transcript it can be copied, logged or shared along with the chat. So:

- Never `cat`, `view`, `type`, `echo` or print anything that could contain the key, including key files and environment variables.
- Never ask the user to paste the key into chat. Ask where it is stored (a file path or a variable name) instead.
- Never copy the key into scripts, reports, project files or this skill.

The script finds the key by itself and reports only where it found it. It checks these places in order:

1. `--key-file PATH`
2. `GEMINI_API_KEY` or `GOOGLE_API_KEY`, then any environment variable holding a Gemini-style key
3. The Windows user environment in the registry
4. `*.txt` files in the video's own folder (turn off with `--no-key-scan`)

If it finds nothing, ask the user for the path to their key file or to set `GEMINI_API_KEY`. Keys are created at Google AI Studio.

**On this PC** the key file is `C:\CU\output\video\geminiapi.txt`. Always pass it explicitly, as `--key-file "C:/CU/output/video/geminiapi.txt"`, and never open, print or copy that file. Reading it with a file tool is blocked by the project settings.

## 3. Pick the video

Don't assume the newest file is the one the user means.

- If the user named or described a file, use that one.
- Otherwise list the folder and let them choose:

```bash
.venv/Scripts/python.exe .claude/skills/gemini-video-review/scripts/gemini_video.py --list "C:/CU/output/video"
```

  This prints modified time, duration, size and name, newest first. Show the user the handful that plausibly match and ask which one.
- Use `--newest DIR` only when the user asked for the latest or newest clip.

## 4. Run Gemini

From the repo root, with `G=.claude/skills/gemini-video-review/scripts` and `KEY="C:/CU/output/video/geminiapi.txt"`:

```bash
.venv/Scripts/python.exe $G/gemini_video.py "PATH/clip.mp4" --key-file "$KEY" --out OUTDIR                     # blind shot breakdown, 12 fps
.venv/Scripts/python.exe $G/gemini_video.py "PATH/clip.mp4" --key-file "$KEY" --dry-run                        # check key, duration, token estimate
.venv/Scripts/python.exe $G/gemini_video.py "PATH/clip.mp4" --key-file "$KEY" --out OUTDIR --start 6 --end 12  # one segment only
.venv/Scripts/python.exe $G/gemini_video.py a.mp4 b.mp4 c.mp4 --key-file "$KEY" --out OUTDIR --batch --fps 6   # several clips, ONE request
.venv/Scripts/python.exe $G/gemini_video.py "PATH/clip.mp4" --key-file "$KEY" --out OUTDIR --mode compare --gen-prompt prompt.txt
.venv/Scripts/python.exe $G/gemini_video.py "PATH/clip.mp4" --key-file "$KEY" --out OUTDIR --mode custom --prompt-file ask.txt --json
```

**Modes.** Default to `shots`, and do the prompt comparison yourself.

| Mode | What Gemini gets | When to use |
|---|---|---|
| `shots` (default) | No knowledge of the intent. It describes each shot: cuts, framing, camera moves, action, who holds what, hair and cloth behavior, effects, idle stretches, physics, artifacts, audio. | First pass, almost always. |
| `compare` | The generation prompt, and a request for beat-by-beat adherence. | When the user wants a formal checklist and there is request budget for a second call. |
| `custom` | Your own instructions from `--prompt-file`. | Narrow questions. Add `--json` if you want structured output. |

The `shots` mode is the default because it is blind. If Gemini knows what should happen, it is biased toward reporting it.

**Focused checks.** Use `--extra` to point Gemini at something specific, and word it neutrally so it doesn't reveal the expected answer. For example, write `--extra "Say what holds the sword in each shot."`, not "Confirm the hair holds the sword."

**Choosing fps.** Tokens grow linearly with fps.

- About 12 fps for fast action, anime, impacts and smears.
- About 6 fps for ordinary motion.
- 1–2 fps for talking heads or long videos.

Add `--low-res` to use roughly four times fewer tokens per frame when a batch is large.

**Reports.** Each run writes `<video name>.gemini-<mode>.json` next to the video, or into `--out DIR`. Read it with a file viewer. The analysis sits under `"analysis"`. If Gemini didn't return valid JSON, the text is under `"analysis_raw"`. Failed runs keep the error, with a hint, under `"error"`.

## 5. Take your own look

`SHEETS` is the take's `06_dailies/<TAKE>/sheets/` folder, or a scratch folder outside a project:

```bash
.venv/Scripts/python.exe $G/frames.py "PATH/clip.mp4" --out "$SHEETS/overview" --cuts             # 4 fps sheets + cut times
.venv/Scripts/python.exe $G/frames.py "PATH/clip.mp4" --out "$SHEETS/zoom_9-11" --fps 12 --start 9 --end 11
.venv/Scripts/python.exe $G/frames.py "PATH/clip.mp4" --out "$SHEETS/keys" --times 1.5,4.9,6.3 --width 960
```

View the `sheet_*.jpg` images. Every tile is labeled with its timestamp.

1. Start with the 4 fps overview.
2. Zoom in at 12 fps on the spans where something looks wrong or where Gemini's report and the prompt disagree.

`--cuts` lists likely hard cuts. Fast whips, flashes and impact frames also register as cuts, so confirm them on the sheets.

Check any Gemini claim that would change a recommendation, such as "the hand holds the sword" or "nothing moves from 9 to 10 s", against the frames before you repeat it.

## 6. Report back

Write for the person who made the video. The goal is the next, better generation. Use this shape:

1. **Verdict:** one or two sentences.
2. **What worked** and **what went wrong**, each item with timestamps. Merge Gemini's findings with your own. Mark anything you could not confirm on the frames.
3. **If a generation prompt exists,** a table with one row per shot or beat: prompt beat, intended time, what actually happened (with time), and status (done / partial / missing / contradicted).
4. **Likely causes and concrete prompt changes.** Quote the wording to change and the replacement.

Keep it to prose plus that one table. Don't paste the raw JSON.

## 7. Limits, cost, errors

- One run is one request. `--batch` sends up to 10 videos as a single request, which matters on the free tier.
- Input tokens ≈ seconds × fps × 258, plus about 32 per second of audio. A 15 s clip at 12 fps is about 47k tokens. `--dry-run` prints the estimate.
- The script retries HTTP 500 and 503 twice, then stops. For other errors the report carries a hint.

See `references/gemini_notes.md` for:

- free-tier limits measured on the user's key
- model choice
- timing accuracy
- the full error table

Read it when a run fails, when planning a large batch, or when changing models.
