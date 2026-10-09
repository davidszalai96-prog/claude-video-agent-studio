# Agentic Animation Studio — Operating Design v1

Oct 9, 2026 · @D

## At a glance

The studio is 15 specialist agents led by one orchestrator, the Producer, built around your setup: Claude Code on your PC, Krea 2 and MiniMax H3 in ComfyUI in your browser, DaVinci Resolve or video-use for editing, and Gemini only when a question needs it. Until the studio is fully developed, you are its only client and the approver at every gate.

**Design principles**

1. **Spend GPU time last.** Ideas are tested on the cheapest medium first: words, then Krea stills (\~35 s each), then an animatic, and only then H3 (22–33 min per clip). You approve the plan on the animatic, before any H3 time is spent.
2. **You hold the GPU.** Nothing renders without your approval. You approve each batch, its ComfyUI configuration (your saved defaults unless you change them) and a time window such as the next 3 hours; the studio stops when the window ends.
3. **The pipeline never waits.** Agents may request retakes, but only you approve them. Meanwhile the edit goes on with the footage that exists, and if a retake is not approved the existing take is used.
4. **Protect the machine.** H3 can fill VRAM and halt the PC, so every H3 job runs alone, after a headroom check and under a watchdog that closes and reopens ComfyUI when a job halts.
5. **One orchestrator, specialists below it.** Only the Producer talks to you and dispatches work. Each specialist sees only its task and its files, so its context stays clean.
6. **Files are the source of truth, not chat.** Brief, bible, shot list, prompts, takes, notes and decisions live in one project folder under fixed IDs. Agents hand each other paths and structured results.
7. **Nobody grades their own work.** The Prompt Writer never judges its own takes. Dailies & QC reviews blind first, then against the plan, and the Director signs off creatively under you.
8. **Measure with code, judge with models.** Beat grids, cut detection, motion direction, flash counts, VRAM and budgets are scripts. Claude reads frames itself; Gemini, which is unreliable, answers only questions frames cannot, and its timings are snapped to local measurements.
9. **The studio learns.** Every retake cause, VRAM incident and editor success or failure is recorded, and measured values replace planning guesses after each project.
10. **Tools sit behind adapters.** Only the Render Wrangler touches ComfyUI and only Finishing touches the editor. Resolve and video-use are two implementations of the same editor adapter, chosen by measured success rate.

**Your workflow, mapped to the studio**

| Your step | Studio stages | Your approval |
| --- | --- | --- |
| You define the project and requirements | S0 Intake | G0 Brief sign-off |
| Studio plans and presents the plan | S1 Development, S2 Visual development, S3 Boards and animatic | G1 Plan approval |
| Studio generates footage in ComfyUI | S4 Pilot, S5 Generation and dailies | Run approval for every batch: jobs, configuration, time window |
| Studio analyses the footage and requests more | S6 Coverage and pickups | Retake and pickup approval, which never blocks the edit |
| You review and send changes; the studio adjusts | Notes loop back to S3, S5 or S6 | G2 Footage lock |
| Studio edits the video | S7 Editorial | G3 Picture lock |
| You accept or ask for adjustments | S8 Finishing, S9 Delivery QC | G4 Final acceptance |
| (added) | S10 Wrap: post-mortem and playbook updates | — |

Three things are added to your outline that professional studios rely on: a brief sign-off before any work (G0), a pilot on one or two hero units before mass generation (S4), and picture lock before finishing (G3), so grading and effects are never redone on a cut that is still moving.

## How a studio works, and what changes with AI footage

A professional animation pipeline is organised around one fact: a change costs more at every later stage, so decisions are made as early and as cheaply as possible.

- **Pre-production** decides what the film is: story, visual development (style, characters, color script), storyboards and an animatic, which is the boards timed to the soundtrack. Most creative decisions are made here.
- **Production** makes the footage the plan asks for. Work is tracked shot by shot with statuses, reviewed every day in dailies, and sent back as retakes with numbered notes.
- **Post-production** assembles and finishes: assembly, rough cut, fine cut, picture lock, then conform, grade, effects, sound mix, mastering and QC. Finishing starts only after picture lock.

Studio habits this design adopts: a bible every artist follows, IDs and versions on everything (v001, v002), daily review of new work, notes with numbers and owners, formal handoffs between departments (turnovers), picture lock, final QC and a post-mortem.

**What changes when H3 and Krea make the footage**

|  | Traditional studio | This studio |
| --- | --- | --- |
| Unit of rendering | One shot | One generation unit: an H3 clip of 10–15 s holding about 8–11 shots, which the Editor sub-clips |
| Control | Artists control every frame | Prompt and references steer; each take is a sample, so alternatives and selection replace frame control |
| Consistency | Model sheets enforced by artists | Krea reference sheets plus fixed text descriptions, checked on every take |
| Previs | Hand-drawn boards | Krea keyframes at \~35 s each give an animatic close to the final look |
| Footage needed | Close to one second made per second used | Some takes fail; plan about 2–3 s generated per 1 s used until the pilot measures it |
| Cheapest fix | Redraw or re-render the shot | Often post: impact frames, flashes, speed, zoom pulses and grade cost minutes, not GPU time |
| Scarcest resource | Artist time | GPU time (about two H3 units an hour) and VRAM headroom; Gemini is a fallback, not a dependency |

**Where to catch a problem, cheapest first**

1. In words (brief, treatment, shot list): seconds to change.
2. In a Krea still or the animatic: \~35 s of GPU per image.
3. In the edit or in post, on footage that already exists: minutes, no GPU.
4. In a new H3 take: 22–33 min of GPU per unit.
5. In a character or style change after production starts: every unit that uses it must be regenerated.

## Lifecycle: stages and gates

Eleven stages run in three phases, and you decide at five gates. At each gate your notes can send work back to the cheapest stage that can fix them.

*[Diagram: Production lifecycle · 11 stages in three phases, 5 user gates — see the online version: https://claude.ai/code/artifact/6d7ced8e-9362-48e3-80fa-3e3c07aa075d]*

Read it row by row: pre-production ends at G1, production at G2 and post-production at G4. Each dashed arc is a gate sending your notes back one stage or further.

**Stages**

| Stage | Goal | Lead agents | Outputs | Exit check |
| --- | --- | --- | --- | --- |
| S0 Intake | Agree what we are making | Producer | brief.md, project.yaml, budget caps | G0 |
| S1 Development | A story built on the music | Writer, Music & Timing, Director | song map, 2–3 concepts, treatment, beat sheet, asset list | Director approves the treatment |
| S2 Visual development | Lock the look and the cast | Art Director, Asset Designer, Render Wrangler | style bible, prompt blocks, look test, approved sheets in the asset library | Director approves look test and sheets |
| S3 Boards and animatic | Plan every shot and its cost | Storyboard & Layout, Prompt Writer, Producer | shot list, generation units, keyframes, animatic, draft prompts, GPU budget and schedule | G1 |
| S4 Pilot | Prove the prompt template on 1–2 hero units | Prompt Writer, Render Wrangler, Dailies & QC | pilot takes, QC reports, revised template, first measured yield | You and the Director: the template works |
| S5 Generation and dailies | Render every unit in approved windows and review every take | Render Wrangler, Dailies & QC, Prompt Writer | takes, QC reports, selects, retakes | Every planned unit rendered once; retake requests sent to you |
| S6 Coverage and pickups | Find what the edit still lacks | Editor, Director, Dailies & QC | assembly cut, coverage report, pickup units | G2 |
| S7 Editorial | Cut the film on the music | Editor, Director | cut versions with previews, editor-neutral EDL | G3 |
| S8 Finishing | Conform, grade, post effects, sound | Finishing & Conform | NLE timeline, master render, conform report | Render matches the locked EDL |
| S9 Delivery QC | Prove the master is correct and safe | Delivery QC | QC report, deliverables, checksums | G4 |
| S10 Wrap | Keep what we learned | Librarian & R&D, Producer | post-mortem, playbook updates, planning constants, archive | — |

**Your gates**

| Gate | You decide | What you see | Notes usually go back to |
| --- | --- | --- | --- |
| G0 Brief sign-off | The brief is right | One-page brief, budget caps, schedule | S0 |
| G1 Plan approval | Spend GPU time on this plan | Treatment, style bible, cast sheets, animatic on the song, GPU-hours and dates | S1–S3 |
| G2 Footage lock | The footage is enough to cut | Assembly cut on the song, dailies gallery, pickups done, open issues | S3 re-board, S5 retake, S6 pickup |
| G3 Picture lock | The cut is final | Cut preview with changelog since the last version | S7, or S5/S6 for a missing shot |
| G4 Final acceptance | Ship it | Master files and the QC report | S8, or S7 |

The Producer classifies every note by change tier (see Quality system) and states the cost of anything that needs GPU time before acting on it.

**Recurring approvals in production.** Two approvals repeat between G1 and G2, and neither stops other work:

- **Run approval:** the Producer sends the next batch (jobs, workflow and configuration, estimated GPU minutes, VRAM risk) and you approve it with a window, for example the next 3 hours. Nothing runs outside an approved window.
- **Retake and pickup approval:** requests from Dailies & QC and the Editor ride along with the next run request. Until you approve one, the edit uses the existing take.

## Org chart: 15 agents in five groups

The Producer is the only agent that talks to you and the only one that starts other agents. The Director holds creative authority under you; the other 13 are specialists that receive a task, write files and report back.

*[Diagram: Studio org chart · Producer, Director and 13 specialists in four groups — see the online version: https://claude.ai/code/artifact/6d7ced8e-9362-48e3-80fa-3e3c07aa075d]*

Every arrow from the Producer is a dispatched task; results come back as files plus a short report, never as chat.

| # | Agent | Studio roles it covers | Group | Model tier | Runs when |
| --- | --- | --- | --- | --- | --- |
| 1 | Producer (orchestrator) | Producer, line producer, production coordinator | Production office | Opus | Always: it is the session itself |
| 2 | Director | Director, creative lead | Production office | Opus | Every stage review and gate |
| 3 | Writer | Screenwriter, story artist | Pre-production | Opus | S1 and rewrites |
| 4 | Music & Timing | Music supervisor, music editor | Pre-production | Sonnet + scripts | S1; sync checks in S7–S9 |
| 5 | Art Director | Art director, color stylist | Pre-production | Opus | S2; style reviews throughout |
| 6 | Asset Designer | Character, prop, environment and VFX designer | Pre-production | Sonnet | S2; asset pickups |
| 7 | Storyboard & Layout | Storyboard artist, layout artist, cinematographer | Pre-production | Opus | S3; re-boards |
| 8 | Prompt Writer | Shot briefs for the generator (AI-specific role) | Production | Opus, high effort | S3–S6 |
| 9 | Render Wrangler | Render wrangler | Production | Sonnet (Haiku for polling) | S2–S6, only in windows you approve |
| 10 | Dailies & QC | Animation supervisor, continuity, QC | Production | Opus | After every take |
| 11 | Editor | Editor, assistant editor | Post-production | Opus | S6–S7 |
| 12 | Finishing & Conform | Online editor, colorist, compositor, mixer | Post-production | Sonnet | S8 |
| 13 | Delivery QC | Mastering and delivery QC | Post-production | Sonnet | S9 |
| 14 | Pipeline TD | Pipeline technical director | Studio services | Opus | On demand |
| 15 | Librarian & R&D | Production librarian, R&D | Studio services | Sonnet | After dailies; between projects |

Model tier is one line in each agent file (`opus`, `sonnet`, `haiku`), so an agent can be moved up or down without touching anything else. Continuity is covered twice on purpose: per take by Dailies & QC, across shots by the Editor. Sound design sits in Finishing; split it into its own agent for projects with narrative sound.

## Agent specs: production office and pre-production

Each spec gives the agent's mission, what it reads and writes, its task breakdown, its tools, when its work counts as done, and what it must never do. These become the system prompts in the agent files.

### 1 · Producer (orchestrator)

**Mission.** Runs the project and is the only agent that talks to you. It turns requests into tasks, dispatches them, tracks every task, budget and note, and runs the gates. It does no creative or technical work itself.

**Reads:** your messages, the tracker, agent reports. **Writes:** brief.md, project.yaml, plan and schedule, budget.json, gate review pages, notes log, decision log, status reports.

**Tasks**

1. Run the intake interview with fixed questions: deliverable and platform, runtime, aspect ratio and resolution, audio (song, excerpt in and out), story idea, style references, characters, must-haves, no-gos, deadline, GPU-hour cap, the times the GPU is usually free, review cadence.
2. Write brief.md and project.yaml, create the project folder from the template, and assign the project code.
3. Break each stage into tasks with an owner agent, inputs, expected outputs, acceptance criteria, dependencies and budget.
4. Dispatch each task with the standard task envelope (see Data model) and record it in the tracker.
5. Read each agent's result, update statuses, and unblock or re-plan.
6. Prepare each run request: the jobs, each workflow with its current configuration (your saved defaults, with any change shown as a diff), estimated GPU minutes, VRAM risk from the recorded peaks, and a proposed window. Start nothing until you approve it as a run ticket.
7. Attach open retake and pickup requests to the next run request, each with its cause, exact change and cost. Never hold the edit while a request waits.
8. Keep budgets current: GPU minutes planned against used (from the render log), retake requests, Gemini calls. Ask you before any cap is exceeded.
9. Build each gate's review page: what to decide, what changed since the last gate, cost to date and forecast, open risks, and two or three explicit options.
10. Turn your feedback into numbered notes (N-001 …), classify each by change tier, show the cost of expensive ones, route them, and track them to closed.
11. Keep the decision log: what was decided, by whom, why and when.
12. At wrap, commission the post-mortem and archive the project.

**Tools:** starts only studio agents; reads and writes inside the project folder; tracker and budget scripts; asks you questions. No ComfyUI or editor tools, which forces delegation.

**Done when:** every task has an owner and acceptance criteria, every note has a status, and the forecast is updated after each stage. **Never:** change creative content, skip a gate, start a render outside an approved window, or spend past a cap without your OK.

### 2 · Director

**Mission.** Owns the creative vision and the quality bar. Approves every artifact internally before it reaches you, and decides retake, fix in post, alternative select or omit.

**Reads:** brief, all creative artifacts, QC reports, contact sheets, previews. **Writes:** director's statement, numbered notes, sign-offs, retake decisions.

**Tasks**

1. Write the director's statement: the film in one sentence, tone, references, camera language, pacing, and what great looks like for this project.
2. Choose among the Writer's concepts and set the north star.
3. Review and sign off: treatment, style bible and look test, cast sheets, storyboard and animatic, hero-unit prompts, pilot results, cut versions.
4. Write notes in a fixed form: where (shot ID or timecode), what is wrong, why it matters, the result wanted. Say what, never how.
5. For each flagged shot, recommend a retake (only you can approve one), a post fix or another select, with the Producer's cost figure. Footage is never dropped without your OK.
6. Settle creative conflicts between agents, for example when the Editor wants a shot QC rated partial.
7. Compare work against the reference films and the best earlier takes.

**Tools:** read, vision on frames and contact sheets, write notes. It sees motion through QC's frame strips, flow data and Gemini reports; you remain the judge of motion in playback. No generation or editor tools.

**Done when:** every gate package carries a Director sign-off with all notes addressed. **Never:** rewrite prompts or edit directly.

### 3 · Writer

**Mission.** Turns the brief into a story built on the music and on what H3 does well: continuous action, extreme camera moves, spectacle.

**Reads:** brief, director's statement, song map. **Writes:** concepts.md, treatment.md, beat\_sheet.json, asset\_list.json.

**Tasks**

1. Read the brief, the director's statement and the song map (sections, drops, silences, energy curve).
2. Write two or three distinct concepts: logline, one paragraph, why it fits the music, the signature image, feasibility notes.
3. After the Director's pick, write the treatment: arc by song section, characters, settings, key images, and an emotional curve matched to the energy curve.
4. Write the beat sheet, one row per musical phrase or story beat: time range, what happens, emotion, visual motif, energy 1–5, and the sync points that must land (drops, silences, bass cuts).
5. List every asset needed (characters, props, environments, effects, graphic overlays), each with a one-line description.
6. Revise from notes.

**Done when:** every second of runtime belongs to a beat, every sync point in the song map has a planned image, and the asset list is complete. **Never:** reproduce lyrics, or write dialogue or voice lines for generation.

### 4 · Music & Timing Analyst

**Mission.** Provides the timing ground truth that every other agent cuts to.

**Reads:** audio file, excerpt in and out, project fps. **Writes:** song\_map.json, song\_map.png, the song as WAV, sync reports.

**Tasks**

1. Decode the audio to WAV with ffmpeg. The WAV also goes on the editor timeline, which avoids the \~51 ms mp3/AAC offset measured in Resolve.
2. Track beats and fit a constant grid: BPM, first-beat offset, bars, 8-bar phrases. Flag any tempo change.
3. Compute per-bar band energies (sub, low, mid, high) to find sections, drops, bass cuts and silences.
4. Separate a vocal stem (UVR MDX-Net) and list vocal events by time, telling chops from sung lines.
5. Convert everything to frames at the project fps. At 110 BPM and 24 fps a bar is 52.36 frames, with beats at +0, +13, +26 and +39.
6. Publish song\_map.json and a picture of it (energy curve, sections, events).
7. In editorial and finishing, verify sync by cross-correlating renders against the source and report the offset.

**Tools:** Python with ffmpeg, librosa and onnxruntime; read and write. **Done when:** the grid fit error is reported, sections and events carry a confidence, and frame conversions are included. **Never:** reproduce lyrics.

### 5 · Art Director

**Mission.** Defines the look and keeps it identical across every image and clip.

**Reads:** brief, references, director's statement, treatment. **Writes:** style\_bible.md, palette.json, colorscript.png, prompt\_blocks.json, look-test verdict.

**Tasks**

1. Collect references into a mood board (contact sheet with sources).
2. Write the style bible: rendering style, line and shading, palette in hex, lighting rules, lens defaults, materials, effects language, camera grammar.
3. Make the color script: palette and lighting per sequence along the energy curve.
4. Write the canonical text blocks: the H3 style opening (one or two sentences), the global effects sentence, and Krea style suffixes per asset type (character, cutout, effects, environment). Positive phrasing only.
5. Commission look tests: four to eight Krea stills, then one short H3 test when the style is new.
6. Review sheets, boards and dailies for style drift.
7. Freeze the blocks at G1. A later change is a Tier 4 change, because it touches every unit.

**Tools:** read, write, vision, job requests to the Render Wrangler. **Done when:** the Director approves the look test and the blocks are versioned and frozen.

### 6 · Asset Designer

**Mission.** Produces every reference image H3 needs and keeps the asset library.

**Reads:** asset list, style blocks. **Writes:** approved sheets and single-item references, asset\_registry.json, one canonical description per asset.

**Tasks**

1. Specify each asset: ID, description with its own materials (generated look-alikes copy materials), sheet type (character turnaround and expressions, cutout props, effects at their peak frame, environment plate) and grid layout.
2. Write the Krea prompt from the proven pattern: a wordless, unlabeled grid on a plain background with generous spacing at 2560×1440; light or mid grey for cutouts, black for effects.
3. Put a seed sweep of three or four seeds per sheet into the next run request.
4. Check each result: faces and eyes, every item present, items separated, style match, each effect distinct in silhouette. Reject and regenerate failures.
5. Pick winners (the Director signs off on hero characters) and record prompt, seed and version.
6. Split sheets into single-item references when needed, with a background mask and connected components, or a fixed grid crop.
7. Register each asset with ID, version, files, canonical description and the units that use it.
8. Build the reference pack for each generation unit. H3 accepts up to 9 pictures; three is the measured configuration.

**Tools:** read, write, vision, Python for splitting, job requests to the Render Wrangler. **Done when:** every listed asset is approved, registered and described. **Never:** put an impact-frame panel on an effects sheet (impact frames are prompted in text only), or use real people or existing copyrighted characters as subjects.

### 7 · Storyboard & Layout

**Mission.** Turns the beat sheet into a shot-by-shot plan packed into H3 generation units, then into an animatic.

**Reads:** beat sheet, song map, style bible, asset registry. **Writes:** shotlist.json, keyframes, animatic\_v###.mp4, post\_fx\_list.json.

**Tasks**

1. Split the runtime into sequences: song sections or story acts.
2. Design each shot: ID, slot on the beat grid, intent, subject and action, framing, angle, lens with a reason, one camera move in H3's vocabulary, screen direction, light, continuity in and out, assets, sync point, and edit role (hero, cutaway, insert, transition).
3. Pack shots into generation units: about 8 shots per 10 s or 11 per 15 s, shots of 0.9–1.8 s, one location and cast per unit where possible, references within the pack.
4. Add coverage: two alternatives for each hero moment, and shots planned slightly longer than their edit slot so the Editor has handles.
5. Move what H3 does badly to the post list: inserts under 0.25 s, extra impact frames, hit-stops, flashes, titles and overlays.
6. Commission one Krea keyframe per shot (composition and pose) and check it.
7. Build the animatic: keyframes timed to the song map with simple push and pan moves, shot IDs and beat markers burned in.
8. Revise from Director and gate notes.

**Tools:** read, write, vision, Python and ffmpeg, job requests to the Render Wrangler. **Done when:** every beat and sync point is covered, each unit is self-contained and inside the prompt budget, and screen direction is consistent across units.

## Agent specs: production

Production separates writing, running and judging: the Prompt Writer writes, the Render Wrangler runs, Dailies & QC judges, and none of them does another's job.

### 8 · Prompt Writer

**Mission.** Writes each unit's H3 prompt in the official ref2va format and proves it passes the lint before it is queued.

**Reads:** unit spec, reference pack, canonical descriptions, style blocks, the H3 playbook. **Writes:** prompts/\<unit>\_v###.txt, lint report, job spec.

**Tasks**

1. Read the unit spec, the reference pack and the current playbook.
2. subject\_definitions: one `<Subject N>` per character, prop or effect, each citing its `<Picture N>` inside the definition; position-based references for items on multi-item sheets.
3. summary, starting with `[reference generation]`.
4. retention\_analysis per subject: fully\_preserved, partially\_preserved or attribute\_transfer.
5. detailed\_description: style opening, `[Shot 1]`, then `At 00:SS.mmm,` for each later shot; one camera move per shot; every element animated; referenced effects brief, with build, peak and dissipation; four to six effect layers per shot; positive phrasing only.
6. overall\_soundscape (sound effects only, no dialogue) and non\_diegetic\_music.
7. Hold the budget: about 60–65 words of detailed description per second of video.
8. Run the prompt linter (section order, timestamps matching the shot slots, word budget, negation and dialogue scan, picture count, known-trap phrases) and fix until it passes.
9. Write the job spec for the Render Wrangler: workflow ID, duration, megapixels, reference mapping, seed, output path.
10. For a retake you approved, apply QC's diagnosis, change one variable at a time (wording or seed, not both) and record the diff.

**Tools:** read, write, the linter. No ComfyUI access. **Done when:** the lint passes and the Director has spot-checked hero units. **Never:** review its own takes.

### 9 · Render Wrangler

**Mission.** Runs the GPU, only inside windows you approve. It is the only agent that submits ComfyUI jobs; it keeps the machine healthy, stops a VRAM problem before it becomes a halt, and accounts for every output.

**Reads:** approved run tickets, job specs, workflow manifests, your saved workflows in ComfyUI. **Writes:** render\_log.jsonl, vram\_log.jsonl, registered outputs, an end-of-window report.

**Tasks**

1. Submit nothing without an approved run ticket whose window is open. When the window ends, start nothing new.
2. Fit the jobs into the window by measured duration. A job that cannot finish before the window ends waits for the next window.
3. Use each workflow exactly as you last saved it. Open it in your ComfyUI tab, convert it with the page's own graphToPrompt, change only the per-job values (prompt, references, seed, output path), and record a snapshot and hash of the configuration with the take.
4. Before each H3 job, compare free VRAM with the configuration's recorded peak and confirm nothing else is using the GPU (a second job, a Resolve render). Too little headroom: skip the job and report it.
5. Run one GPU job at a time, grouped by model (all Krea, then all H3), and submit the next job only when the previous one has finished, so a restart can only ever lose the job that halted.
6. At the start of the window, launch the watchdog as a background script. It follows ComfyUI's progress messages and VRAM for every job and, when a job halts, runs the restart procedure (see Tool layer) by itself, so no permission prompt or agent turn can delay a recovery.
7. After a restart, reload the ComfyUI tab, check that the API answers, reopen the next workflow and continue if the window still has time. The halted job is marked halted and is not rerun with the same configuration; a lower-VRAM configuration is proposed for your approval.
8. Retry a failed job once only when the failure was not memory-related.
9. On completion, register the output (path, hash, ffprobe facts including resolution), save the prompt beside it, log GPU minutes and peak VRAM, and notify Dailies & QC.
10. At the end of the window, stop the watchdog, free memory and post the report: done, halted (with the restart count), failed, minutes used, what comes next.

**Tools:** Claude Code's Chrome connection to your ComfyUI tab; the shell for ComfyUI's HTTP API, nvidia-smi and the watchdog with its restart script; read and write in the render folders; ffprobe. **Done when:** every job has a full record (ticket, configuration hash, prompt ID, output, metrics) and there are no orphan files. **Never:** run outside an approved window, change your workflow configuration without your approval, write outside approved folders, or use video references.

### 10 · Pipeline TD

**Mission.** Builds and maintains the machinery the other agents use: workflow manifests, adapters, scripts and benchmarks.

**Reads:** workflows in C:\\CU, failure reports, R&D requests. **Writes:** workflow manifests, adapter code, tools, benchmarks.md, the environment pin.

**Tasks**

1. For every production workflow, write a manifest: named parameters mapped to node IDs, which values the studio sets per job (prompt, references, seed, output path) and which belong to you (everything else), outputs, and measured time and peak VRAM per configuration.
2. Keep a default configuration profile per workflow, taken from the workflows as you saved them, and produce the diff of your changes for each run request.
3. Wire broadcast-node inputs (Anything Everywhere) explicitly and set seeds explicitly, since front-end seed randomisers do not run over the API.
4. Smoke-test each manifest with a minimal job inside an approved window, and test the restart procedure once (close, wait 15 s, reopen with ComfyUI.bat, API answers) before the first unattended window.
5. Build and maintain the ComfyUI bridge (browser conversion and queuing, shell monitoring), the VRAM watchdog with its ComfyUI restart script, and the editor adapter interface with its Resolve and video-use implementations.
6. Build and maintain the deterministic tools: linter, shot detector, flow analysis, contact sheets, flash scan, resolution fitting, budget calculator, ffmpeg previewer, OTIO generator.
7. Measure time and peak VRAM per configuration, and test whether setting NVIDIA's "CUDA – Sysmem Fallback Policy" to prefer no fallback for ComfyUI's Python turns a VRAM overflow into a clean out-of-memory error instead of a near-halt.
8. Pin the environment (ComfyUI version, custom nodes, model file hashes) and re-run the smoke tests after any update.
9. Fix failures escalated by the Render Wrangler.

**Tools:** shell and Python, read and write in the pipeline folders, the ComfyUI adapter in test mode. **Done when:** every production workflow has a manifest and a passing smoke test.

### 11 · Dailies & QC

**Mission.** The independent judge of every take. It reviews blind first, then against the plan, and turns every take into selects or a retake order.

**Reads:** the take, the unit's shot list, the reference pack, and the prompt only after the blind pass. **Writes:** QC report, qc.json, contact sheets, selects.json, retake orders.

**Tasks, per take**

1. Technical: ffprobe for duration, fps, frame count, resolution and audio; black or frozen frames.
2. Structure: detect cuts with PySceneDetect AdaptiveDetector, verify every boundary on a contact sheet, and map detected shots to planned shots.
3. Blind description: Claude's own reading of frame strips at native fps around each cut and beat, written down before the prompt is read.
4. Motion: optical flow for camera direction, push or pull, and jitter; screen direction against the plan. Motion quality on hero shots goes to you for playback review.
5. Gemini only when needed: a question that frames and flow cannot settle (motion feel, audio), batched with other takes, and skipped without blocking when the API fails.
6. Frames: faces, eyes, hands, fidelity to the character sheet, morphing, stray text, impact frames.
7. Compliance table: planned shot, intended time, what happened, status (done, partial, missing, contradicted).
8. Score each shot with the rubric and mark its usable frame ranges as selects. Every take stays in the pool, so even a weak take gives its best ranges.
9. Verdict per unit: Approved, Approved with selects, or Retake requested. A request states the cause, the exact wording change and the GPU cost, and goes to you through the Producer; it never stops the edit.
10. Send durable findings to the Librarian.

**Tools:** Python (ffprobe, PySceneDetect, OpenCV, frame extraction), the Gemini review skill when needed, vision, read and write in the dailies folders. **Done when:** every planned shot has a status and every claim behind a retake is verified on frames. **Never:** see the prompt before the blind pass, approve its own suggested changes, or drop a take from the pool.

## Agent specs: post-production and studio services

Post-production works on an editor-neutral cut list, so only Finishing knows which editor is in use; the two service agents keep the machinery and the knowledge current.

### 12 · Editor

**Mission.** Builds the film from selects, on the music, in an editor-neutral format, from sources of any resolution, without ever waiting for a retake.

**Reads:** selects, shot list, animatic, song map, post list. **Writes:** edl\_v###.json, preview cut\_v###.mp4, coverage report, changelog.

**Tasks**

1. Read each source's resolution and aspect ratio from the tracker. H3 output varies (1504×832 and 1152×640 seen, 1344×768 and 1664×928 configured), all close to but not exactly 16:9.
2. Set the timeline to the deliverable resolution. Default fit: scale to fill and crop the overflow, centred unless a shot needs reframing; never stretch. Record scale, crop and position per clip in the EDL; zoom pulses multiply on top of that fit.
3. Flag every clip upscaled by more than about 1.5× (proposed threshold). Finishing then chooses, with you, between an approved upscale batch and a smaller master.
4. Assembly: replace each animatic keyframe with the best select, and keep keyframes where footage is missing so holes stay visible. Build with what exists; mark where an approved retake will land and swap it in when it arrives.
5. Coverage review with the Director: holes, weak shots, continuity breaks and rhythm problems become pickup requests, specified as shots for Storyboard and sent to you through the Producer.
6. Rough cut on the grid: phrase starts and drops on hard cuts, impact moments on hits, fast cutting in high-energy bars, holds in silences.
7. Match cuts: match on action and motion-matched cuts where flow vectors agree; keep screen direction.
8. Fine cut: frame trims, constant speed changes, dissolves, zoom pulses on beats (downbeat about 1.15, kick about 1.10, backbeat about 1.06, decaying ×0.6 per frame) and flash frames.
9. Express every version as an editor-neutral EDL (tracks, source file with in and out, per-clip fit, record in and out, speed, transitions, keyframed effects, markers) and render an ffmpeg preview at the timeline resolution with burn-ins.
10. Apply notes and keep a changelog between versions.
11. At picture lock, hand the EDL to Finishing as a turnover package.

**Tools:** read, write, Python and ffmpeg, vision on frames. No editor tools; Finishing owns them. **Done when:** every frame traces to a source file and frame, and sync is verified against the song map.

### 13 · Finishing & Conform

**Mission.** Turns the locked EDL into a finished master inside the editor: DaVinci Resolve or video-use, whichever has the better measured success rate, through the same adapter.

**Reads:** locked EDL, post list, style bible, song WAV. **Writes:** editor project and timeline, master render, conform report.

**Tasks**

1. Pick the editor route for this project from the Librarian's success-rate record (Resolve or video-use), then check that route: build, edition and unavailable features for Resolve; install and helpers for video-use.
2. Create a new project or timeline from the studio template at the deliverable resolution. In Resolve, set the project's mismatched-resolution rule to scale full frame with crop, so zoom 1.0 means fitted. Never edit an existing project without a backup or .drp export.
3. Conform the EDL through the adapter. Resolve 21.0.4 free: OTIO import for dissolves, retimes, keyframes and per-clip fit; the live API for placement, static transforms, markers and retime quality. video-use: its ffmpeg helpers, driven from the same EDL.
4. Verify the conform by rendering it and comparing it frame by frame with the preview.
5. Resolution: apply the per-clip fit from the EDL. Upscaling happens only through an approved ComfyUI upscale batch, or by delivering at a smaller size; you choose.
6. Grade: match exposure, white balance and saturation across units, then apply the look from the style bible.
7. Post effects from the list: impact frames, flashes, chromatic aberration, glows, titles. Use Fusion comps or DRX grades where the API cannot reach; name any UI step precisely and never guess where a control sits.
8. Audio: the song WAV on the timeline, an optional effects layer, loudness to target.
9. Render the master and platform versions, never during an active H3 window, since editor renders also use VRAM. Then clean up render jobs and archive bins.

**Tools:** the editor adapter (Resolve MCP or video-use), read and write in the finishing folders, Python (OTIO generator, frame compare). **Done when:** the master matches the locked cut frame for frame and every post item is done or waived.

### 14 · Delivery QC

**Mission.** The last independent check before you see a final.

**Reads:** master files, deliverable specs. **Writes:** delivery report, checksums, deliverables package.

**Tasks**

1. Check specs per deliverable: resolution, fps, codec, bitrate, color tags, audio format, duration.
2. Measure loudness (integrated LUFS and true peak) against the platform target.
3. Count flashes per second. This style relies on white flashes and impact inversions, so any second with more than three flashes is flagged with timestamps for the Editor (the WCAG and broadcast three-flash guideline).
4. Detect black, frozen or dropped frames, audio dropouts and the audio/video offset.
5. Check for leftover burn-ins, slates, temporary markers and unresolved QC flags.
6. Write the report, generate checksums and package the deliverables.

**Done when:** every check passes or you waive it explicitly.

### 15 · Librarian & R&D

**Mission.** The studio's memory and its improvement engine.

**Reads:** QC reports, render log, notes, post-mortems. **Writes:** playbooks, planning constants, experiment reports, post-mortems.

**Tasks**

1. After each dailies report, extract durable lessons (wording that worked or failed, model quirks, timings) with evidence in the form of take IDs.
2. Keep the VRAM record: peak per configuration, every halt with its configuration and log, and the safe-configuration table the Render Wrangler checks before each job.
3. Keep the editor record: for Resolve and for video-use, conforms that passed first time, render mismatches, failures and time spent. Finishing picks its route from this.
4. Maintain the playbooks (H3 prompting, Krea sheets, editing grammar, editor routes) and propose skill updates for your approval.
5. Keep the asset library and naming clean: broken references, duplicates, disk use.
6. Propose one-variable experiments for your next approved windows. First candidates: whether low-megapixel previews predict full renders, Krea keyframes as extra references, "match" against "max" reference size, the sysmem fallback setting, and flow-based motion metrics that reduce the need for Gemini.
7. Write the post-mortem: time per stage, retake causes, yield (usable shots per unit), GPU plan against actual. Update the planning constants from it.

**Tools:** read and write in the knowledge folders, Python for statistics, R&D job requests. **Done when:** each project ends with updated constants and playbooks.

## Data model: one folder, stable IDs, one tracker

Everything lives under a stable ID in one project folder on C:, and the tracker is the single source of truth. Agents pass each other paths and IDs, never pasted content.

**Levels and IDs**

| Level | Example ID (MAG for Magic) | What it is | Owner |
| --- | --- | --- | --- |
| Project | MAG | One film and its deliverables | Producer |
| Sequence | MAG\_SQ010 | A song section or story act | Storyboard & Layout |
| Generation unit | MAG\_SQ010\_U020 | One planned H3 clip of 10–15 s holding about 8–11 shots | Storyboard & Layout |
| Shot | MAG\_SQ010\_U020\_SH030 | One planned beat inside a unit, 0.9–1.8 s | Storyboard & Layout |
| Take | MAG\_SQ010\_U020\_v003 | One render of a unit: a prompt version, a seed and a configuration hash | Render Wrangler |
| Select | MAG\_SQ010\_U020\_SH030\_v003\_s1 | A usable frame range of one shot in one take, with its score | Dailies & QC |
| Asset | CHAR\_\<name>\_v002 | A reference sheet or single-item reference | Asset Designer |
| Run ticket | R-004 | A batch you approved, with its window | Producer |
| Note, decision, task | N-014, D-007, T-0123 | Your notes, recorded decisions, dispatched tasks | Producer |

The edit is built from selects, not from takes. That is what lets the studio keep seven good shots from a take and regenerate only the missing three.

**Folder layout**

```
C:\claude-video-agent-studio\
  .claude\            agents, skills, settings, hooks
  pipeline\           workflow manifests, config profiles, bridge, tools, playbooks, constants.json
  templates\          project template, editor templates
  projects\MAG\
    00_admin\         tracker.json, budget.json, run_tickets\, notes.md, decisions.md,
                      render_log.jsonl, vram_log.jsonl
    01_brief\         brief.md, project.yaml
    02_story\         song_map.json, concepts.md, treatment.md, beat_sheet.json
    03_art\           style_bible.md, prompt_blocks.json, assets\<asset>\v002\
    04_boards\        shotlist.json, keyframes\, animatic\
    05_prompts\       MAG_SQ010_U020_v003.txt, lint\
    06_dailies\       MAG_SQ010_U020_v003\ report.md, qc.json, sheets\
    07_edit\          edl_v004.json, previews\
    08_finish\        conform\, renders\
    09_delivery\
    10_wrap\
C:\CU\output\studio\MAG\units\   ComfyUI writes takes here; the tracker points to them
```

Nothing is ever read from or written to D:.

**Tracker.** One JSON file (or SQLite once it grows) with a record per task, unit, shot, take, select, asset, note and decision. Every record carries ID, status, owner, version, timestamps and links to its files.

**Unit statuses:** planned → boarded → prompt\_ready → awaiting\_run\_approval → queued → rendering → rendered or halted → in\_dailies → approved, approved\_with\_selects or retake\_requested → in\_edit → locked. A unit with retake\_requested stays in the edit with its current take. When you approve the retake it returns to prompt\_ready with its attempt count raised by one, and the new take replaces the old one only if it scores better.

**Task envelope.** Every dispatch from the Producer has the same shape, so any agent can be replaced without changing the others:

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

**Run ticket.** The Render Wrangler acts only on a ticket you approved. It lists the jobs, the configuration of each workflow and the window:

```json
{
  "run_id": "R-004",
  "approved_by": "you",
  "window": {"start": "2026-10-10T21:00+02:00", "end": "2026-10-11T00:00+02:00"},
  "jobs": [
    {"take": "MAG_SQ010_U020_v001", "workflow": "H3regenrunsTest", "config": "default", "est_min": 25},
    {"take": "MAG_SQ010_U030_v001", "workflow": "H3regenrunsTest", "config": "default", "est_min": 25},
    {"take": "MAG_SQ020_U010_v002", "workflow": "H3ultRefsTest2", "config": "yours-2026-10-10", "est_min": 33, "retake_of": "v001"}
  ],
  "config_changes": {"H3ultRefsTest2": {"ref_image_size": "max -> match"}},
  "est_total_min": 83,
  "vram_check": "every configuration has a recorded peak below the free VRAM"
}
```

## Quality system

Every take is measured, described blind and compared with the plan before anyone decides on it; retakes run only with your approval and never stop the edit, and every note goes to the cheapest stage that can fix it.

*[Diagram: Dailies and retake loop · 5 checks, 1 verdict, retakes on your approval — see the online version: https://claude.ai/code/artifact/6d7ced8e-9362-48e3-80fa-3e3c07aa075d]*

Every take reaches the Editor as selects straight away; a retake runs only if you approve it, and otherwise the take is used as it is.

**Shot rubric (scored 1–5 by Dailies & QC)**

| Criterion | A 5 means | Checked by |
| --- | --- | --- |
| Intent | The shot does the planned action on the planned beat | Compliance table against the shot list |
| Character fidelity | Face, eyes, costume and proportions match the sheet | Frames against the reference pack |
| Motion | Believable physics, no jitter or morphing, camera move as planned | Optical flow and jitter metrics, your playback for hero shots, Gemini only if needed |
| Composition and direction | Framing and screen direction as boarded | Frames, flow direction |
| Style | Matches the style bible and look test | Frames against the look test |
| Artifacts | Clean hands, limbs, edges; no stray text or flicker | Frames at native fps around the issue |

A shot is usable when no criterion scores below 3; hero shots also need Intent and Character fidelity of 4 or more. Each usable range becomes a select with its in and out frames and its scores.

**Retake rules**

1. Diagnose before changing anything. Sampling failure (one bad sample of a good prompt): new seed, same wording. Prompt failure (beats compressed, reordered or static): change the wording, keep the seed so the effect of the change is visible. Reference failure: fix the sheet first.
2. Change one variable per retake and record it, so each retake teaches something.
3. Agents request, you decide. Dailies & QC and the Editor file retake and pickup requests with the cause, the exact change and the GPU minutes; the Producer attaches them to the next run request.
4. The edit never waits. While a request is open, the Editor uses the take's best ranges, an alternative select or a post fix.
5. Not approved means used as is: the existing take stays in the cut. An approved retake replaces it only if it scores better.
6. Prefer partial reuse. When most shots in a take are good, request a small pickup unit for the rest rather than the whole unit.

**Coverage review (S6).** The Editor builds the assembly from selects, with the animatic keyframes still showing wherever footage is missing. With the Director, every gap or weak moment gets one action: an alternative select, a post fix, a pickup unit or a re-board. Pickup requests reach you together, attached to the next run request.

**Change tiers for your notes**

| Tier | Example | Route | Cost |
| --- | --- | --- | --- |
| T0 Edit | Trim, reorder, timing, swap a select | Editor | Minutes, no GPU |
| T1 Post | Grade, speed, zoom pulse, flash, overlay, title | Editor or Finishing | Minutes, no GPU |
| T2 Regenerate | A unit misses a beat: new seed or wording | Prompt Writer, Render Wrangler, Dailies & QC | 22–33 GPU-min per unit |
| T3 Re-board | New or changed shots in a sequence | Storyboard, then T2 for each new unit | Keyframes plus every unit in the sequence |
| T4 Redesign | Character, style block or story change | Art Director or Asset Designer, then T3 | Every unit that uses the asset, listed from the registry |

T0 and T1 are done directly and appear in the next cut. Everything from T2 up spends GPU time, so it waits for your approval and joins the next run request.

## Resource budgets: GPU and Gemini

GPU time is the scarcest resource: at the measured settings the RTX 5090 renders about two H3 units an hour, and an H3 job that overflows VRAM can halt the machine. The Producer plans every project against these numbers.

**Measured costs**

| Job | Settings | Measured | Notes |
| --- | --- | --- | --- |
| H3 unit, 1 reference | 0.98 MP (1344×768), 15 s, 28 steps | 22–28.5 min | H3regenrunsTest; two queued jobs run back to back without RAM trouble |
| H3 unit, 3 references | 1.5 MP (1664×928), 10 s, references at "max" | about 33 min | H3ultRefsTest; "match" reference size is the faster option |
| Krea 2 sheet or keyframe | turbo fp8, 8 steps plus refine pass | about 35–38 s per image | H3regensElements; re-measure at 1440p |
| Gemini review | one 15 s clip at 6 fps | about 25k tokens | up to 10 clips per request; free tier 5 requests/min, 20/day, 250k tokens/min; 503 outages have lasted over 1.5 h |

**Queue policy**

- Renders run only inside windows you approve, for example the next 3 hours. Jobs are fitted to the window by measured duration, and a job that cannot finish in time waits.
- One GPU job at a time, grouped by model; Krea jobs run as a block before the H3 jobs. Memory is freed between jobs and at the end of the window.
- No Resolve render, no second ComfyUI job and no other GPU-heavy program during an H3 window.
- Each H3 job starts only if free VRAM covers its configuration's recorded peak; the watchdog restarts ComfyUI when a job halts.
- Gemini only when needed: 8–10 takes per request at 2–3 fps. A failure is skipped, never waited on, and never blocks a stage.
- budget.json holds planned against used for each stage; the Producer escalates at 80% of any cap.

**Worked example: a 90 s music video** (each project's real numbers come from its song map). Yield and shot length are planning assumptions until the pilot measures them.

1. The cut needs about 60–70 shots at an average of 1.3–1.5 s.
2. A 15 s unit plans about 10 shots. Assuming 60% are usable on the first pass, that gives 6 selects per unit, so 11–12 units, plus about 30% for retakes and pickups: **about 15 units**.
3. H3 time at 0.98 MP: 15 × \~25 min ≈ **6.3 GPU-hours**, about three 3-hour windows plus approved retakes. With the 3-reference 1.5 MP setup (10 s units of 8 shots, \~33 min each) the same film needs about 18 units, **about 10 GPU-hours**.
4. Krea time: about 8 sheets × 4 seeds plus about 70 keyframes × 2 seeds ≈ 170 images ≈ **1.8 GPU-hours**.
5. Gemini: none planned. At most a few requests, only for questions that frames and flow cannot settle.

## Tool layer: adapters, scripts and guardrails

Agents never improvise against raw applications: each external system sits behind one adapter with typed operations, and each adapter belongs to exactly one agent.

| System | Adapter | Owner agent | Operations |
| --- | --- | --- | --- |
| ComfyUI in your browser (127.0.0.1:8188) | ComfyUI bridge: your ComfyUI tab through Claude Code's Chrome connection for converting and queuing; the HTTP API and nvidia-smi from the shell for monitoring | Render Wrangler | open saved workflow, read configuration, build prompt, queue, status, free memory, outputs, VRAM watch, restart |
| Video editor | Editor adapter interface with Resolve and video-use implementations | Finishing & Conform | session check, create project or timeline, import media, conform EDL, per-clip fit, markers, grade, post effect, render, export interchange |
| Gemini API | gemini-video-review skill, only when needed | Dailies & QC | narrow JSON questions in batch; a failure is skipped, never waited on; the key is read from a file and never printed |
| Audio, frames, files | Studio scripts (below) | Several | deterministic measurements |

**ComfyUI bridge.** ComfyUI stays open in your browser and its configuration is yours. For each job the Render Wrangler opens your saved workflow in that tab, converts it with the page's graphToPrompt (the recipe that works today), changes only the values the manifest marks as per-job, and queues it from the page, so every job shows in your queue. Monitoring runs from the shell, which keeps working if the browser extension's connection goes idle during a long window. The manifest names the per-job parameters and records defaults and measured costs:

```json
{
  "id": "h3_ref2va_15s_1ref",
  "workflow": "workflows/H3regenrunsTest.json",
  "per_job": {
    "prompt":        {"node": "138"},
    "ref_image_0":   {"node": "195"},
    "output_prefix": {"node": "92"}
  },
  "yours": "every other value, as you last saved it",
  "default_profile": {"duration_s": {"node": "132", "value": 15}, "megapixels": {"node": "192", "value": "0.98"}},
  "measured": {"minutes": [22, 28.5], "peak_vram_gb": "to be measured"},
  "rules": ["one GPU job at a time", "no ref_videos", "legacy decode", "free memory after each job"]
}
```

Node IDs are the ones in your H3regenrunsTest workflow; the Pipeline TD fills in input names, the seed node and value ranges when it writes the real manifest.

**ComfyUI restart procedure.** Interrupting a halted job rarely works on this machine, so the watchdog restarts ComfyUI instead, and only inside an approved window:

1. Detect a halt: no progress message from ComfyUI for 5 minutes while a job runs (about five steps at the measured 45–70 s per step), or no answer from the API for 2 minutes. Both are proposed defaults, tuned later from the VRAM log.
2. Record the job, its configuration hash, the last step reached and the VRAM curve in vram\_log.jsonl.
3. Close ComfyUI: end the process serving port 8188 together with the console window that started it, and nothing else.
4. Wait 15 seconds.
5. Check the GPU with nvidia-smi. If ComfyUI's memory has not been released, stop the window and alert you, since a reboot may be needed.
6. Reopen ComfyUI by running ComfyUI.bat from your desktop, so it starts with your launch arguments. The Pipeline TD records the file's exact path once.
7. Wait until the API answers. After 3 minutes without an answer, stop the window and alert you.
8. Hand back to the Render Wrangler, which reloads the ComfyUI tab and continues with the next job.
9. Limit: two restarts per window (proposed). A third halt ends the window and goes into the report.

**Editor adapter.** The Editor writes an editor-neutral EDL; only the adapter turns it into editor-specific actions, and each implementation declares what it can do. Finishing reads that list before planning.

- **DaVinci Resolve 21.0.4 free:** the samuelgursky MCP over the in-app bridge for placement, static transforms, markers, grades and renders, plus OTIO import for dissolves, constant retimes, keyframes and per-clip fit (render-verified on the Highscore test).
- **[video-use](https://github.com/browser-use/video-use):** the browser-use team's open-source editing skill for Claude Code. It edits with ffmpeg from a text description of the footage plus a few stills rather than by watching video, and its setup asks for an ElevenLabs key because it is built around transcripts, so how well it fits wordless music footage is something the pilot measures.
- **Resolve Studio 21.1+ (option):** native transitions, speed and fades, plus Blackmagic's own MCP server.
- **The choice is made per project** from the Librarian's success-rate record; both routes read the same EDL, so switching costs no re-editing.

**Studio scripts**

| Script | Used by | What it guarantees |
| --- | --- | --- |
| vram\_watch | Render Wrangler | Headroom check before each job; halt detection and the automatic ComfyUI restart during it; peak VRAM per configuration |
| song\_map | Music & Timing | Beat grid, sections, events and vocal timing |
| prompt\_lint | Prompt Writer | Format, word budget, banned patterns |
| shot\_detect and contact sheets | Dailies & QC | A cut list verified on frames |
| flow\_motion | Dailies & QC, Editor | Camera direction, push or pull, and jitter, from optical flow and phase correlation |
| flash\_scan | Dailies & QC, Delivery QC | Impact frames found; flashes counted per second |
| fit\_resolution | Editor, Finishing & Conform | Per-clip scale, crop and position from source size to timeline size, with upscale flags |
| budget\_calc | Producer | GPU minutes per run request and per window |
| preview\_render | Storyboard & Layout, Editor | Animatic and cut previews with ffmpeg at the timeline resolution |
| otio\_gen | Finishing & Conform | Resolve-shaped OTIO with dissolves, retimes, keyframes and per-clip fit |
| render\_diff | Finishing & Conform | The conform matches the preview frame for frame |

**Guardrails, enforced by hooks and adapters rather than by prompts**

- No ComfyUI job without an approved run ticket whose window is open; the bridge checks the clock before every submit.
- No change to your workflow configuration without your approval; every take records the configuration hash it used.
- One GPU job at a time, and no editor render during an H3 window. The restart script may close only the ComfyUI process and its console, only inside an approved window, and reopens ComfyUI only through your ComfyUI.bat.
- Any write to D:, or outside C:\\claude-video-agent-studio and C:\\CU\\output\\studio, is blocked before it runs.
- The Gemini key is read from its file by the script and never appears in chat, logs or project files.
- Lyrics are never written to any project file.
- No existing editor project is opened without a backup, and Resolve free is never updated past 21.0.x.

## Implementation

The studio runs in Claude Code on your PC, with the Producer as the session agent and the other 14 as project subagents. ComfyUI stays in your browser, where you watch the queue and change configurations; the Render Wrangler reaches it through Claude Code's Chrome connection and ComfyUI's local HTTP API.

Claude Code started with `claude --chrome` (or with Chrome enabled by default) drives your browser through the Claude in Chrome extension, on Windows as well; it works in Chrome and Edge but not under WSL. The extension's connection can go idle in long sessions, which is why only conversion and queuing use the browser and all monitoring runs from the shell ([Chrome docs](https://code.claude.com/docs/en/chrome)).

**How Claude Code maps onto the design** ([subagent docs](https://code.claude.com/docs/en/sub-agents))

- Each agent is a Markdown file with YAML frontmatter in `C:\claude-video-agent-studio\.claude\agents\`; the body becomes its system prompt.
- `claude --agent producer --chrome` runs the whole session as the Producer with the browser connected, and `tools: Agent(director, writer, …)` limits which agents it can start.
- Subagents can start their own subagents up to three levels deep by default. The studio stays flat: specialists get no Agent tool, so only the Producer delegates.
- `skills:` preloads playbooks (H3 prompting, Krea sheets, Resolve route, video-use) into the agents that need them.
- `mcpServers:` scopes the Resolve MCP to Finishing; the browser tools are used only by the Render Wrangler.
- `memory: project` gives each agent a persistent memory folder that it curates.
- `hooks:` with `PreToolUse` enforce the guardrails, including the run-ticket check before any ComfyUI submit. The watchdog is a background script the Render Wrangler starts, so a restart never waits on a permission prompt; on Windows the hook scripts are PowerShell.

**File layout**

```
C:\claude-video-agent-studio\CLAUDE.md          studio rules: C: only, no lyrics, no dialogue, run tickets, naming
C:\claude-video-agent-studio\.mcp.json          davinci-resolve
C:\claude-video-agent-studio\.claude\agents\    producer.md, director.md, writer.md, music-timing.md,
                             art-director.md, asset-designer.md, storyboard.md,
                             prompt-writer.md, render-wrangler.md, pipeline-td.md,
                             dailies-qc.md, editor.md, finishing.md, delivery-qc.md,
                             librarian.md
C:\claude-video-agent-studio\.claude\skills\    h3-prompting, krea-sheets, comfy-bridge, vram-watch,
                             gemini-video-review, resolve-music-video, resolve-edit,
                             video-use, studio-conventions
```

**Example agent file**

```markdown
---
name: render-wrangler
description: Submits, monitors and registers ComfyUI jobs (Krea, H3). The only agent that touches ComfyUI.
tools: Read, Write, Bash, mcp__comfyui
model: sonnet
mcpServers:
  - comfyui
skills:
  - comfy-ops
memory: project
maxTurns: 60
---
You are the studio's render wrangler. You receive job specs from the Producer...
```

**Build order**

1. **Foundation:** folder template, CLAUDE.md, tracker, run tickets and the approval flow, the ComfyUI bridge and VRAM watchdog with the restart procedure tested, manifests and default profiles for H3regenrunsTest, H3ultRefsTest2 and H3regensElements, and your four existing skills ported into `.claude\skills`.
2. **Core loop on the pilot:** Producer, Prompt Writer, Render Wrangler and Dailies & QC render two units of the pilot project in one approved window, with full dailies and a VRAM log.
3. **Pre-production on the pilot:** Music & Timing builds the timing map, then Writer, Art Director, Asset Designer and Storyboard & Layout produce the animatic.
4. **Production of the pilot:** all units in approved windows; retake requests come to you while the edit goes on.
5. **Post-production on the pilot:** Editor, Finishing & Conform and Delivery QC. Resolve and video-use both conform the first sequence, and the one with the better result finishes the video.
6. **Wrap and adjust:** the Librarian's post-mortem replaces the planning assumptions with measured constants, the safe-configuration table and the editor record, and the studio workflows are adjusted from it.
7. **Magic:** the Nhato "Magic" music video runs on the adjusted workflows.

The Director, Pipeline TD and Librarian join in step 2, so lessons and VRAM peaks are captured from the first takes. The pilot is a project you define later; it starts at S0 with a brief like any other.

## Decisions for you

Your decisions of 9 October are built into this version, and three items remain open.

| Topic | Decision |
| --- | --- |
| Approver | You, for everything, until the studio is fully developed |
| Where it runs | Claude Code on your PC; ComfyUI in your browser |
| ComfyUI configuration | Your saved workflows are the defaults; you can change them, and the studio never does without your approval |
| GPU runs | Only with your approval, inside a window you set, for example the next 3 hours |
| VRAM | Every H3 job runs alone, after a headroom check, under a watchdog; when a job halts, the studio closes ComfyUI, waits 15 s and reopens it with your ComfyUI.bat |
| Retakes | Agents may request them and you approve them; the pipeline continues with the existing footage, which is used if a retake is not approved |
| Editing | DaVinci Resolve or video-use, chosen by measured success rate; mixed source resolutions are handled in the edit |
| Gemini | Only when needed; never a dependency |
| Pilot | A project you define later. The Nhato "Magic" music video follows once the studio workflows are adjusted |

- [x] Pilot project: your brief, which opens the pilot at S0.
- [ ] Default deliverables: platforms, aspect ratios, resolution (it decides how much upscaling is needed) and loudness target.
- [ ] Editor comparison: let Resolve and video-use both conform the first pilot sequence, or start with Resolve only.

## Sources

- Measured timings, limits and rules: your skills h3-gacha-pipeline, resolve-music-video, gemini-video-review and resolve-edit, and the project notes resolve-setup-and-pipeline-test.md.
- Claude Code subagents: [Create custom subagents](https://code.claude.com/docs/en/sub-agents).
- Claude Code and the browser: [Use Claude Code with Chrome](https://code.claude.com/docs/en/chrome).
- video-use: [browser-use/video-use on GitHub](https://github.com/browser-use/video-use).
