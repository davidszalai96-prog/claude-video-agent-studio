---
name: "h3-gacha-pipeline"
description: "Plan, prompt and run MiniMax H3 gacha-style videos end to end in the user's ComfyUI: ref2va prompts, ultimate sequences, Krea 2 element sheets, API-queued runs, QA and batch tracking."
---

# H3 gacha video pipeline

End-to-end procedure for the user's MiniMax H3 work: rewriting prompts into the official full-reference (ref2va) format, directing Wuthering Waves / Honkai: Star Rail-style showcases and ultimate-ability sequences, generating reference element sheets with Krea 2, queuing ComfyUI workflows over the API, checking results, and tracking batches. It is meant to run unattended once a pipeline is approved, so follow it closely and record new findings in the project docs.

Running state:
- **Studio work** keeps its state in the project folder (tracker, render log, dailies) under the `studio-conventions` skill.
- **Standalone gacha work** keeps it in the claude.ai project "Minimax H3 Prompts", which is not on this PC: `claude/reruns-batch-procedure.md` (batch status table), `claude/ult-sequence-research.md` (ultimate research and tests) and `claude/h3-prompting-notes.md` (older H3 lessons).

Record new H3 findings in `docs/notes/` in this repo.

## 1. Environment

- ComfyUI root is `C:\CU` on the user's PC. Output is `C:\CU\output`, workflows are `C:\CU\user\default\workflows`, inputs are `C:\CU\input`. ComfyUI 0.37, RTX 5090 (32 GB), 128 GB RAM. ComfyUI runs in its own venv `C:\CUVenv`, started by `C:\Users\david\Desktop\ComfyUI.bat`; never install into that venv.
- **Converting and queuing.** Drive ComfyUI through Claude in Chrome (Claude Code started with `--chrome`) on the **studio's own ComfyUI tab** at `http://127.0.0.1:8188`, running JavaScript in the page against ComfyUI's own HTTP API.
  - Never use or reload the user's own ComfyUI tab.
  - Don't click the canvas.
  - Jobs are queued from that tab with its own client ID, so the user can watch progress and the preview node there.
- **Monitoring** runs from the shell against the same HTTP API, which keeps working if the browser connection goes idle. The details are in the `comfy-bridge` skill.
- **Files.** Claude Code has a local shell and reads and writes files directly on disk.
  - Writes are allowed only in this repo and in each project's footage folder (`CLAUDE.md`, rule 6).
  - Never move or rename the user's folders (rule 9 below).
- **Gemini.** Video review is available through the `gemini-video-review` skill. The key is in `C:\CU\output\video\geminiapi.txt` (an `AQ.` key).
  - Pass that path with `--key-file`. Never open, print or copy the file.
  - 503 "high demand" is common: wait 10+ minutes and retry the same request. In a studio project, Dailies & QC skips a failed Gemini call instead of waiting on it, and never blocks a stage on it.

## 2. Standing rules (user decisions)

1. sol-attn (BlockSparseAttention, node 190) is the default for H3, for speed (user decision 2026-10-09; it replaces the earlier "no sol-attn for high-motion work").
   - It applies to H3 video generation only, never to Krea.
   - When the user reports low quality, or VRAM fills, switch to the chunking setup with no sol (attention profile `chunked` in §4).
2. Decode H3 with H3 VAE Decode (Blend Mode) = legacy.
3. Free VRAM with KJNodes `VRAM_Debug` pass-throughs (all three options on) after samplers and decodes. The user decided the existing H3regenrunsTest memory setup is fine; no VRAM_Debug is needed after the text encoder.
4. Queue only the nodes that feed active outputs (graphToPrompt already drops bypassed nodes). At the end of a batch, POST `/api/free {"unload_models":true,"free_memory":true}`.
5. TaoMate LoRA needs at least 3 of its own steps; skip it in pass 1 if the clip will be de-roped.
6. Judge motion in playback, never from stills. For the music video, audio is never needed.
7. Never build big comparison grids inside ComfyUI (100+ GB RAM). Use ffmpeg xstack/drawtext from the shell (ffmpeg is on PATH).
8. Never use video references (`ref_videos`) locally: far too much compute.
9. Batches: don't rename folders. Track finished items in the project doc's status table.
10. No dialogue or voice lines in generations (user decision 2026-10-05). Keep sound effects and music.
11. Work inside each character's regen folder: `output/video/Reruns/<Folder>/`. Put ultimate-sequence assets (Krea prompts, sheets, H3 prompts, videos) in `Reruns/<Folder>/Ultimate/`. Point SaveVideo and Image Saver paths there.
    - In a studio project, outputs go to the project's footage folder instead. The user chooses it at project definition, and it must be inside `C:\CU\output`. Takes go in `units/<TAKE>/`, with the prompt saved beside the take, and stills in `stills/<ID>/`. The SaveVideo prefix is the footage folder relative to output plus `units/<TAKE>/<TAKE>`.

## 3. ComfyUI API recipe (browser JavaScript)

- **Open a workflow** (in the studio's own tab only). Call `app.extensionManager.workflow.openWorkflow(ws.getWorkflowByPath('workflows/NAME.json'))`, then reload the page.
  - Without the reload, the tab switches but `app.rootGraph` keeps the old graph, and graphToPrompt then returns the wrong workflow.
  - If `getWorkflowByPath` returns null for a newly written file, reload first.
  - Before any reload, check that no open workflow has unsaved changes, and stop if one does.
- **Check before queuing.** Confirm known node IDs exist in `app.rootGraph`. Then `p = await app.graphToPrompt()` gives `p.output` (the API prompt) and `p.workflow`.
- **Patch values by node ID** in `p.output`. Subgraph nodes appear as `"parent:child"`.
- **Queue** with POST `/api/prompt` and body `{prompt, client_id: app.api.clientId, extra_data: {extra_pnginfo: {workflow}}}`. Mirror the same values into `workflow.nodes[].widgets_values` so the saved file embeds the real workflow. Check `node_errors`: jobs with node errors fail at once.
  - In the studio, queue only what the project's approval policy allows. The `comfy-bridge` skill and the guardrail hooks check it before each submit.
- **Monitor.** Poll `/api/history/<id>` (`status.status_str`, `outputs`) and `/api/queue`, from the shell; the page's `progress` event via `app.api.addEventListener` also works while the tab is connected. Don't poll faster than every few minutes for long H3 jobs.
  - Progress messages go only to the client that queued the job (the studio tab). The shell-side watchdog follows ComfyUI's console log instead (`vram-watch` skill).
- **Long text** (prompts): write the .txt directly to disk under the output folder (studio: the project's footage folder). Read it in the page with `fetch('/api/view?filename=..&subfolder=..&type=output').then(r=>r.text())`, rather than pasting it into JavaScript.
- **Images.** Fetch them from `/api/view` (type=output) as a blob and upload with POST `/api/upload/image` (FormData `image`, `subfolder`, `type=input`, `overwrite=true`). Reference them as `subfolder/name`.
- **Anything Everywhere and similar broadcast nodes** don't show up in graphToPrompt. Connect those inputs yourself (see the Krea section). Frontend-only seed randomizers (easy globalSeed, rgthree) don't run over the API, so set seeds explicitly.
- **Save locations.** The SaveVideo `filename_prefix` is relative to output, e.g. `video/Reruns/<Folder>/<Folder>_15s`. Image Saver uses `path` plus `filename`.
- **New workflow files.** Build the UI JSON in Python from the base file (copy nodes, add links `[id, from, slot, to, slot, type]`, bump `last_node_id`/`last_link_id`).
  - The workflows folder is the user's and lies outside the studio's write folders, so writing a new file there needs the user's approval.
  - Then open it with the reload trick and graphToPrompt it to validate before queuing.
- **Configuration changes without touching the saved file** (attention profiles, §4): set `node.mode` (0 = on, 4 = bypass) on `app.rootGraph` nodes in the studio tab before `graphToPrompt`, and don't save the workflow.

## 4. H3 workflows

- **`H3regenrunsTest`** (base for everything). 25 API nodes.
  - 138 prompt (PrimitiveStringMultiline) → 136 MiniMaxH3ReferenceToVideo.
  - 195 LoadImage (ref_image_0); 92 SaveVideo prefix.
  - 132 duration in seconds; 131 computes frames as `max(5,round(s*24)) + (5 - that % 17) % 17`, so 15 s gives 362 frames and 10 s gives 242.
  - 192 megapixels (Float string) → 115 ResolutionSelector 16:9 ×32: 0.98 MP gives 1344×768.
  - res_multistep, 28 steps, simple; fixed seed 831837948015784; no LoRA; legacy decode; VRAM_Debug after decode; `ref_image_size` "max".
  - Timing: 0.98 MP, 15 s, 1 reference takes 22–28.5 min (45–62 s per step). Two queued jobs run back to back without RAM trouble.
- **`H3ultRefsTest`**: the same plus LoadImage 235 → `ref_images.ref_image_1` and 236 → `ref_images.ref_image_2`; 1.5 MP (1664×928); 10 s (243 frames). Used for character sheet + cutout sheet + VFX sheet tests. With the Sage patches it ran at about 70 s per step (33 min) with 3 refs at "max", with no VRAM or RAM trouble.
- **Speed configuration** (user suggestion, used from `H3ultRefsTest2` onward; check the timing on the first run): the model chain is 127 UNET → 152 preview → 187 ModelAttentionBackend "comfy kitchen attention" (on) → 159 PathchSageAttentionKJ (bypassed) → 158 MiniMaxChunkFeedForward chunks 2 / seq_threshold 4096 (on) → 155 MiniMaxLowVRAMAttention head_chunks 4 (on) → 153 MiniMaxH3MemoryEfficientSageAttentionPatch (bypassed). Set node modes 0 = on and 4 = bypass in the UI JSON.
- The node accepts up to 9 pictures, 3 videos (never use them) and 3 audios. "max" ref size (2048 short edge) costs time with several refs; "match" is the faster option if VRAM or time becomes a problem.
- **Attention profiles** (user decision 2026-10-09).
  - Each project's H3 templates are chosen by the user, and each template's manifest records its sol-attn node and chunking nodes. The sol node's own settings come from the template as saved.
  - Two sol nodes are in use:
    - ComfyUI's built-in "Model Sparse Attention" (`BlockSparseAttention`, method sol-attn: tau 1.3, start 0.2, end 1.0, min_tokens 12288);
    - the custom "Patch Sol-Attn" (`SolAttnPatch`, `ComfyUI-SolAttn_triton`). The user's setup on 2026-10-09: tau 1.30, start 0.20, end 0.90, min_tokens 4096, int8_qk true, sink exact_kv_and_rows, morton true, 2d_frame.
  - If a template has no sol node, ask the user before using it.
  - The H3ult/regenruns family shares one model chain with the same node IDs: 127 UNET → 152 preview (taeh3, the live preview the user watches) → 187 ModelAttentionBackend → 159 PathchSageAttentionKJ → 158 MiniMaxChunkFeedForward → 155 MiniMaxLowVRAMAttention → 153 MemoryEfficientSageAttentionPatch → 154 LoRA → 190 BlockSparseAttention → 193 → sampler.
  - A profile is a set of node modes, applied in the page before graphToPrompt (§3):
    - **`sol` (default for every H3 job):** 187 and 190 on; 153, 155, 158 and 159 bypassed. This is H3ultSingleRefSparse as saved. Its time and VRAM peak are not measured yet; plan with the measured non-sol numbers above as the upper bound until a smoke test measures them.
    - **`chunked` (fallback when the user reports low quality or VRAM fills):** 187, 155 and 158 on; 153, 159 and 190 bypassed. This is H3ultRefsTest2 as saved.
    - **`sage`:** 159 and 153 on; 155, 158, 187 and 190 bypassed. This is H3regenrunsTest as saved, and the setup behind its measured 22–28.5 min.
  - Leave every other node as the user saved it, 152 included.

## 5. Writing H3 ref2va prompts

Official guide: https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md (and `_base_en.md`). Write six sections in order: `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, `non_diegetic_music`.

- **Subjects.** Each referenced character is `<Subject N>` and cites its `<Picture N>` inside the definition; don't add a standalone picture line. Props, effects, styles and interfaces can be subjects too. For items on a multi-item sheet, define each by position: "the shattering crystal-wing burst at the bottom left of `<Picture 3>`".
- **Summary.** Starts with a task-type prefix, `[reference generation]` for these.
- **Retention analysis.** Characters and props are usually `fully_preserved`. Animated effects taken from a sheet are `partially_preserved`. A style applied to something else (such as an impact-frame look) is `attribute_transfer`.
- **Detailed description.**
  - Open with one or two style sentences before `[Shot 1]`. `[Shot 1]` has no timestamp; later shots start with `At 00:SS.mmm,`.
  - Camera vocabulary: push in/pull out, zoom, pan, truck, tilt, pedestal, arc shot, tracking, static, shake slightly/strongly, roll, each with "with small/large amplitude" and "at slow/fast speed". Use one camera move per shot.
  - The guide's dialogue format is `(S1)` with `<d>[English] ...</d>`, but the user wants no dialogue (rule 10), so leave speakers out.
- **Budget.** About 60–65 words of detailed description per second worked (940 words for 15 s and 11 shots; 636 for 10 s and 8 shots; all shots in order). 2,000+ word prompts led to beats being compressed or reordered. Ultimate test 2 deliberately overloads at about 98 words per second (985 words for 10 s, 2,040 words in total) to see what H3 keeps; update this line with the result. Shots of 0.9–1.8 s work. Widen any 0.3 s montage cuts from the source prompts to about 1 s.
- **Directing.** One shot, one camera setup, one beat. Describe only what is visible, as one continuous action from start to end. Plan each shot in layers: intent, subject and action, frame, optics (24/35/50/85 mm only with a reason), camera, performance and physics, light and space, continuity. Keep screen direction consistent and state it in the opening.
- **Positive phrasing only.** Negations introduce the forbidden thing. Describe properties that make the unwanted behavior implausible instead.
- **Known traps.**
  - Calling butterfly-patterned sleeves "wings" made H3 add real wings on the back. Write "enormous wide sleeves patterned like butterfly wings".
  - Generated look-alikes copy the reference subject's materials, so give each generated entity its own material description (for example, a stone golem of "weathered grey-white stone blocks, moss in the seams, gold eye slits").
  - Ignore stray tags at the end of source prompts that belong to other characters.
- **Impact frames: prompt them in text only.** Never reference an impact-frame image. In ultimate test 1, the black-and-white impact frame taken from the VFX sheet was held for about 0.6 s, like a shot; the user rejected that. Text wording that worked in MiniMax_H3_00239_ (3 of 4 landed where asked):
  - "insert a two-frame black-and-white impact inversion: the whole frame turns white, [subject] becomes a solid black silhouette, black ink speed lines explode outward, only [her eyes / a small violet star] stay lit";
  - "freeze for about 0.08 seconds on a graphic impact frame: a bright cyan center, jagged white petals, a deep-purple corona, black radial spikes";
  - "the shot ends on a two-frame pure white flash". This landed exactly (2 frames at the end of the shot) in ultimate test 1 too.
  Check every run at frame level (§8).
- **Animate everything.** In every shot, describe how each element moves:
  - Props: the "!!" card pulses three times, swelling and shrinking, with ink droplets flying off; the standee flips in like a thrown card, rocks on its base and tips forward; the banner slams in with a springy bounce while its LED dots chase; the sunglasses drop and snap on.
  - The enemy rattles, dangles and flails.
  - Giant figures perform an action (grab, pinch, swing) rather than pose.
  In test 1, elements described only by appearance came out almost static: "between a cinematic and an infographic" (user).
- **Referenced effects must be brief and moving.** Show sheet effects only at their peak moment, for about a second or less, with a build-up, peak and dissipation ("blooms, spins, shatters into tiny butterflies", "flashes for a split second, then explodes into tumbling shards that fade within half a second"). In test 1 they sat on screen like paintings.
- **Overload with prompted effects.** Pro ultimates have far more particles than test 1 did. Add a global effects sentence in the style opening and 4–6 layers per shot: glitter, star dust, spark showers, crescent smears, shockwave rings that ripple the air, light streaks, lens flares, chromatic aberration, paper confetti, motion-blurred afterimages, debris.
- **Use H3's camera strength.** H3 handles extreme perspectives and any camera move well, so use them: worm's-eye straight up, top-down with the eruption rushing at the lens, extreme foreshortening of a weapon thrust into the lens, a camera flying inside a swarm (describe it as placed among them; avoid "POV"), barrel rolls (roll clockwise/counterclockwise), fast arc shots, whip pans, crash push-ins.
- **Tone:** an epic, climactic, absurd showcase, never a calm infographic.
- Wuthering Waves showcase style opening that worked: "cel-shaded 3D anime game cinematic in the style of a Wuthering Waves character showcase: clean thin outlines, soft two-tone shading, glossy highlights…, strong warm rim light, bloom on every <element> effect, fluid cloth and hair motion".
- Save every prompt next to its output as `prompt_15s_ref2va.txt` (or `promptN_...` for folders with several prompts). One video per prompt.

## 6. Ultimate-ability sequences (HSR / WuWa grammar)

Reference analysis (two HSR ultimates, about 10 s each, real-time engine at 60 fps):

- **Structure:** trigger pose → face or eye close-up → portal transition (crash zoom into the iris that becomes a nebula, curtain, white-out) → emblem/motif hold (1–2 s) → scale shift or theatrical reveal (giant silhouette, pop-up stage) → comic 2D beat (flat cutout "!!" with scratchy brush ink, die-cut standee of the character, puppet or doodle victim) → impact frames (1–4-frame black-and-white ink, white-out, black frame) → climax blast → 1.5–2.5 s payoff hold with a graphic overlay (striped LED-dot banner with the character sticker in sunglasses).
- **Timing:** shots of 0.3–3.4 s (average about 1.3 s), plus 2–4-frame inserts. The snap comes from timing, holds, hit-stop and editing, not from a low frame rate.
- **Sound:** bass drops and glass shatters on impacts, whooshes on whips. Pro ultimates have a voice line, but leave it out here (rule 10).
- **Studio techniques:** hand-keyed poses cheated to camera; keyed cameras per shot; stylized layered VFX (build-up → impact → fade-out); camera-facing manga-line planes; screen post (1–2-frame inverted or white frames, chromatic aberration, radial blur, bloom, FOV drop on impact); flat 2D cards in 3D space.
- **H3 split of work:** prompt the beats in H3 as continuous moves (8 shots per 10 s, about 11 per 15 s). Put sub-0.25 s inserts, extra impact frames, hit-stop holds and chromatic flashes in post (DaVinci Resolve skills) when H3 misses them.
- **Test 1** (Nyxara, `Reruns/Celestial Butterfly Oracle/Ultimate/`, 8 shots): every beat landed in order, and the sheet props and effects were reproduced faithfully. Problems:
  - the referenced effects were static and on screen too long;
  - the impact frame from the sheet was held 0.6 s;
  - the eye push hard-cut to the nebula instead of transforming;
  - the giant silhouette just stood there;
  - the "!!" barely moved.
- **10 s template v2** (`h3_ult_prompt_10s_test2.txt`, 9 shots, prompt prepared):
  - 0–1.0 low-angle 24 mm, staff double spin and slam; a starlight ring cracks the floor; fast arc
  - 1.0–1.9 staff thrust into the lens, crash push into the gem
  - 1.9–3.0 sigil blooms, spins and shatters into butterflies; barrel roll; two-frame white flash
  - 3.0–4.3 worm's-eye: a colossal starlight figure of her plucks the puppet up by its rods and shakes it like a toy above the spinning magic circle
  - 4.3–5.5 dangling puppet; "!!" pulses ×3, "?!" spins, standee flips in and points; whip pan
  - 5.5–6.7 camera flies inside the butterfly swarm; two-frame text-only black-and-white impact inversion; roll
  - 6.7–7.7 hit burst flashes for a split second then tumbles away; puppet pieces scatter; shockwave
  - 7.7–8.8 top-down: eruption and spinning crescent rush up past the lens; the giant dissolves into stardust
  - 8.8–10 payoff: banner bounces in with chasing LED dots, standee springs up, sunglasses drop and snap on
- Give the enemy one consistent identity across all shots (e.g., the filigree shadow puppet from the cutout sheet). The H3 prompt references the character sheet, the cutout sheet and the VFX sheet; leave out the sheet's impact-frame panel.

## 7. Element sheets with Krea 2 (`H3regensElements`)

- **Workflow.** Krea 2 turbo fp8, Qwen3-VL 4B encoder, ClownsharK linear/euler 8 steps cfg 1, refine pass 0.2 (res_2s), about 35–38 s per image.
  - API patches: `46.value` = prompt; force `56:54.switch = false` (raw prompt; the enhancer stays off as saved); seeds in 187 and 128; `156:155.path` / `.filename` for the save location.
  - Connect the Anything Everywhere inputs: `203.clip` and `56:55.clip` = `["6",0]`; `195.vae` and `109:99.vae` = `["5",0]`.
  - Set ResolutionMaster (node 13) to **2560×1440**. The user asked for 1440p after a 1080p standee came out with mismatched eyes.
- **Layout.** A neat N-by-M grid on a plain background with generous spacing, each item fully visible and separated, and "completely wordless and unlabeled: the items are its only content". Light or mid-grey background for cutouts, black for VFX.
- **Cutout style that worked** (`krea_cutouts_prompt_v2.txt` in `Reruns/Celestial Butterfly Oracle/Ultimate/`; the VFX v3 prompt is next to it): "comic overlays in Honkai: Star Rail"; thick die-cut cards with visible paper edge and thickness, rough hand-cut white border, crisp drop shadow, tilted; dry-brush black ink with ragged scratchy edges and splatter, halftone screentone, slight violet/cyan print misregistration, holographic and gold foil accents.
  - Premium versions of each prop: brush-ink "!!"/"?!" on extruded slabs; a character standee "in polished official gacha illustration style" (not chibi), with the character described in full; a filigree shadow-theatre puppet on rods; glowing chalk doodles; holographic pixel sunglasses; holographic butterfly and gold-foil moon stickers; an angular banner with a white/black double border and gold LED-dot halftone stripes.
  - Plain solid-shape stickers look amateur.
- **VFX style that worked** (v3): "real-time game visual-effect renders captured at their most intense peak frame, as seen in Honkai: Star Rail ultimate cutscenes … rendered like premium in-engine anime VFX, not flat illustrations": additive glow overexposing to white at the core, volumetric bloom and haze, semi-transparent energy sheets and flipbook-style smear shapes, motion blur, particles at several depths, prismatic fringes, dark accent strokes; a white-hot → magenta/violet → indigo gradient.
  - The concept-sheet framing produced flat icons. Make each effect distinct in silhouette (the emblem and the hit burst came out too alike).
  - Leave an impact-frame panel off the VFX sheet, since impact frames are prompted in text only. Use that slot for another signature effect (e.g., a shockwave ring or ribbon trail).
- **Review.** Before use, check faces and eyes on any character item, that every listed item is present, and that items are separated. The user chose cutouts v2 seed 20261008 and VFX v3 seed 20261011 for the Nyxara test. In an approved production run there is no user review: apply these checks yourself and regenerate with a new seed when one fails. In a studio project, the project's approval policy sets how many retakes a still gets and how the user chooses between candidates.
- **Splitting into single-item references** (optional, up to 9 pictures in total): a background-difference mask with dilation and connected components works when items are spaced (the VFX v1 sheet split 6/6). Use a fixed grid crop when the panels fill their cells (VFX v3: 3×2 cells of 640×540 at 1080p).

## 8. QA after each run

- `ffprobe` for duration, size, frame count and audio. A 1 fps 4×4 contact sheet checks shot order and content. Strips at the native frame rate around key beats check impact frames and flashes.
- To scan for impact frames, flag frames with mean saturation below 40 and more than 60 % near-black or near-white pixels.
- Use the Gemini `shots` mode (blind) at 12 fps for motion and audio, and verify its claims on the frames. Motion itself must be judged in playback, by the user or by Gemini.
- Report what worked and what didn't, with timestamps, and record durable findings in the project docs.

## 9. Batch reruns (`output/video/Reruns`)

Gacha rerun batches. Each batch is defined like a project (user decision 2026-10-09):
- When the batch is defined, ask the user where to create its new footage folder. It must be inside `C:\CU\output`.
- That folder becomes one of the write folders. The existing `output/video/Reruns` folders are read-only sources (character sheets, original prompts).
- Sheet uploads go through ComfyUI's `/api/upload/image` from the page, as in §3.
- In the steps below, read "the batch's footage folder" wherever `Reruns/<Folder>` is the output.

- Each folder holds a character sheet (`*.png~tplv-...-image.png`) and `prompt.txt` / `prompt2.txt` (10 s originals).
- For each folder:
  1. Rewrite each prompt to 15 s ref2va (§5) in a Wuthering Waves showcase style.
  2. Commit it to the folder.
  3. Upload the sheet to `input/reruns/<Folder>_sheet.png`.
  4. Queue H3regenrunsTest with node 138 = the prompt, 195 = the sheet, 92 = `video/Reruns/<Folder>/<Folder>[_promptN]_15s`.
  5. Verify the output.
  6. Mark the folder done in the status table of `reruns-batch-procedure.md`.
- Free memory at the end of each batch.