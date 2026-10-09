"""edit/cut_sheet.md: one line per section + the frame-exact beatmap table."""
import json

E = json.load(open("edl.json"))
P, START = 0.46875, 109.8791
SECTIONS = [
    (0, 4, "Build I", "bar 0",
     "One 4-beat wide push-in over the clouds while the bass is filtered out: calm, cool and slow, so the build has somewhere to go."),
    (4, 12, "Build II", "bars 1-2",
     "Cut rate doubles as the riser climbs (2+2, then 2+1+1): eyes igniting, praying hands, light gathering. Close-ups and glows, no fx."),
    (12, 18, "Build III", "bar 3 - 4.2",
     "1-beat cuts of rising glow, wings and bursts on the sub swell; the two bass hits get the golem stomp with a light punch."),
    (18, 20, "Calm piano", "4.3-4.4",
     "The only still moment: one half-speed close-up of glowing eyes, so the drop lands as hard as possible."),
    (20, 32, "Drop entry", "bars 5-7",
     "Hard cut to a crimson explosion (white flash + 1.18 punch), then real-speed 1-beat cuts with half-beat bursts where the bass filter-sweeps (5.4, 6.3, 7.4)."),
    (32, 51, "Drop body", "bars 8 - 12.3",
     "Cut density follows the bass stem: 2-beat pulsed holds on sustained growls, half-beat chops where the bass gates, downward/upward motion on pitch dives/rises."),
    (51, 56, "Mid-drop dip", "12.4 - 13.4",
     "Sustained drone with weak drums: one flowing 3-beat lance run, two rising half-beats, then a punch + flash re-entry on 13.4."),
    (56, 68, "Drop peak", "bars 14-16",
     "Busiest wobbles: 1-beat cuts with punches on the loudest kicks, then six half-beat stutters across six different characters."),
    (68, 83, "Climax", "bars 17 - 20.3",
     "Chopped bass and zaps: half-beat chops, a white flash on the 17.2 bass gap, and a red/blue quarter-beat strobe on the heaviest stutter (19.3-19.4)."),
    (83, 86, "Break", "20.4 - 21.2",
     "Energy drops out: half-speed whale and moon, then a frozen crimson frame with a flash where the bass cuts."),
    (86, 88, "End hit", "21.3 - 21.4",
     "The next section's hit gets a teal crystal explosion (flash + punch), ending on the peacock fan; 0.4 s audio fade."),
]
starts = [0] + E["cut_frames"]
L = ["# Cut sheet - Nhato - Magic (1:49.879-2:31.129)", "",
     f"41.25 s, 990 frames @ 24 fps, 1280x720, {len(E['ranges'])} shots, 128.00 BPM. Output 0:00 = song 1:49.879 (the downbeat nearest 1:50); the drop hits at 0:09.375 (song 1:59.254).",
     "", "## Sections", "",
     "| section | bars (song) | output time | song time | shots | cut rate | why |", "|---|---|---|---|---|---|---|"]
for b0, b1, name, bars, why in SECTIONS:
    t0, t1 = b0 * P, b1 * P
    f0, f1 = round(t0 * 24 - 1e-6), round(t1 * 24 - 1e-6)
    n = sum(1 for s in starts if f0 <= s < f1)
    rate = (b1 - b0) / n if n else 0
    mm = lambda t: f"{int(t // 60)}:{t % 60:06.3f}"
    L.append(f"| {name} | {bars} | {mm(t0)}-{mm(t1)} | {mm(START + t0)}-{mm(START + t1)} | {n} | {rate:.2f} beats/shot | {why} |")
L += ["", "## Global decisions", "",
      "- **Watermark:** each Dola clip is pre-cropped to its top 1166x656 (bottom edge 7 px above the 'Dola AI' box at x1121-1249, y663-690) and scaled back to 1280x720. A persistent-edge test on the render finds no trace.",
      "- **Variety in the drop:** a lint enforces no character back to back, at most 2 appearances of a character per 8 beats, no same look group back to back, CLIP ViT-H similarity < 0.84 between neighbours, and motion >= the pool median (the strobe and freeze are deliberate exceptions).",
      "- **Music analysis:** the grid is 128.00 BPM (verified against beat_this); the bass/drums/other stems from HDemucs set each beat's cut density.",
      "- **Grade:** light contrast/saturation lift with a gentle S-curve on every shot. Clip audio is dropped.",
      "- **Audio:** the song's MP3 master is clipped hot (+1.2 dBFS sample peak), and ffmpeg's AAC encoder distorts it (+3.2 dBTP, -0.7 LU). A -3.5 dB pre-gain gives a clean encode: -9.3 LUFS, -1.1 dBTP.",
      "", "## Shot by shot (frame-exact, from beatmap.md)", ""]
L += open("beatmap.md", encoding="utf-8").read().splitlines()[3:]
open("cut_sheet.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[:22]))
