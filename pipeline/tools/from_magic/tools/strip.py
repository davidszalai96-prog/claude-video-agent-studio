"""Grid of thumbnails: rows = clips, columns = given frame numbers. usage: strip.py out.jpg "f1,f2,..." clip1 [clip2 ...]"""
import sys, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
out, frames, clips = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], sys.argv[3:]
TW = 150; font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)
rows = []
for c in clips:
    cap = cv2.VideoCapture(c); imgs = {}
    i = 0; mx = max(frames)
    while i <= mx:
        ok, fr = cap.read()
        if not ok: break
        if i in frames:
            h, w = fr.shape[:2]; imgs[i] = cv2.cvtColor(cv2.resize(fr, (TW, int(h * TW / w))), cv2.COLOR_BGR2RGB)
        i += 1
    rows.append((c, imgs))
th = next(iter(rows[0][1].values())).shape[0]
W = 170 + len(frames) * (TW + 3); H = 18 + len(rows) * (th + 16)
img = Image.new("RGB", (W, H), (20, 20, 20)); d = ImageDraw.Draw(img)
for j, f in enumerate(frames): d.text((170 + j * (TW + 3), 2), f"f{f}", fill=(255, 220, 120), font=font)
for r, (c, imgs) in enumerate(rows):
    y = 18 + r * (th + 16)
    d.text((2, y + th // 2), c.replace("\\", "/").split("/")[-1][:24], fill=(220, 220, 220), font=font)
    for j, f in enumerate(frames):
        if f in imgs: img.paste(Image.fromarray(imgs[f]), (170 + j * (TW + 3), y))
img.save(out, quality=85); print("saved", out)
