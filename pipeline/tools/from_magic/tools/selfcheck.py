"""Self-eval of a render against edl.json: cut accuracy, stray jumps, watermark region, audio offset, segment grid.
usage: selfcheck.py <video> <tag>"""
import json
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

video, tag = sys.argv[1], sys.argv[2]
E = json.load(open("edl.json"))
cuts = E["cut_frames"]
starts = [0] + cuts
dola = {k for k, p in E["sources"].items() if "\\clean\\" in p or "/clean/" in p}

cap = cv2.VideoCapture(video)
diffs, mids, wm = [], {}, []
seg_of = np.zeros(sum(r["frames"] for r in E["ranges"]), int)
for i, r in enumerate(E["ranges"]):
    seg_of[starts[i]:starts[i] + r["frames"]] = i
prev, i = None, 0
gx_acc = None
while True:
    ok, fr = cap.read()
    if not ok:
        break
    g = cv2.cvtColor(cv2.resize(fr, (160, 90), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
    diffs.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
    prev = g
    si = seg_of[min(i, len(seg_of) - 1)]
    r = E["ranges"][si]
    if i == starts[si] + r["frames"] // 2:
        mids[si] = cv2.cvtColor(cv2.resize(fr, (192, 108)), cv2.COLOR_BGR2RGB)
    if r["source"] in dola:
        roi = cv2.cvtColor(fr[655:700, 1100:1270], cv2.COLOR_BGR2GRAY).astype(np.float32)
        gm = np.hypot(cv2.Sobel(roi, cv2.CV_32F, 1, 0), cv2.Sobel(roi, cv2.CV_32F, 0, 1))
        wm.append(gm)
    i += 1
n = i
d = np.array(diffs)
print(f"frames {n} (EDL {len(seg_of)})")
weak = []
for c in cuts:
    nb = max(d[c - 1] if c - 1 >= 0 else 0, d[c + 1] if c + 1 < n else 0)
    if d[c] < 1.15 * nb or d[c] < 6:
        weak.append((c, round(d[c], 1), round(nb, 1)))
cutset = set(cuts)
stray = [(k, round(d[k], 1)) for k in range(1, n) if k not in cutset and d[k] > 25 and d[k] > 2.0 * np.median(d[max(1, k - 6):k + 7])]
print(f"cuts {len(cuts)}; weak/ambiguous cut frames (diff not a clear peak): {len(weak)} {weak[:30]}")
print(f"stray big jumps not on a cut: {len(stray)} {stray[:30]}")
if wm:
    m = np.min(np.array(wm), axis=0)
    med = np.median(np.array(wm), axis=0)
    print(f"watermark region over {len(wm)} Dola frames: persistent-edge max(min)={m.max():.1f} p99(median)={np.percentile(med, 99):.1f} (Dola text edge in sources was > 400)")
# audio offset vs the song
SR = 8000
def pcm(args):
    raw = subprocess.run(["ffmpeg", "-v", "error", *args, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)
a = pcm(["-i", video, "-t", "20"])
b = pcm(["-ss", f"{E['music']['start'] - 0.5:.4f}", "-i", "../Nhato - Magic.mp3", "-t", "21"])
corr = np.correlate(b[:len(a) + SR], a[:SR * 15], "valid")
lag = (int(np.argmax(corr)) - SR // 2) / SR
print(f"audio offset vs song @ {E['music']['start']:.3f}s: {lag * 1000:+.1f} ms")
# segment grid
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 11)
cols, tw, th = 11, 192, 108
rows = -(-len(E["ranges"]) // cols)
img = Image.new("RGB", (cols * (tw + 2), rows * (th + 26)), (16, 16, 16))
dr = ImageDraw.Draw(img)
for si, r in enumerate(E["ranges"]):
    x, y = (si % cols) * (tw + 2), (si // cols) * (th + 26)
    if si in mids:
        img.paste(Image.fromarray(mids[si]), (x, y))
    dr.text((x + 2, y + th + 1), f"{si + 1} {r['source'][:16]}", fill=(230, 230, 230), font=font)
    dr.text((x + 2, y + th + 13), f"{starts[si]}f {r['frames']}f {r['beat'][:14]}", fill=(200, 200, 120), font=font)
img.save(f"verify/segments_{tag}.jpg", quality=82)
print(f"saved verify/segments_{tag}.jpg")
