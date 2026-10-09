"""Rows of 'clip:frame' items, each showing frames f-2..f+3. usage: cands.py out.jpg path:frame ..."""
import sys, cv2
from PIL import Image, ImageDraw, ImageFont
out, items = sys.argv[1], sys.argv[2:]
TW = 170; font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)
rows = []
for it in items:
    p, f = it.rsplit(":", 1); f = int(f)
    cap = cv2.VideoCapture(p); cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, f - 2)); imgs = []
    for k in range(6):
        ok, fr = cap.read()
        if not ok: break
        h, w = fr.shape[:2]; imgs.append((f - 2 + k, cv2.cvtColor(cv2.resize(fr, (TW, int(h * TW / w))), cv2.COLOR_BGR2RGB)))
    rows.append((p.replace("\\", "/").split("/")[-1][:22] + f" @{f}", imgs))
th = max(im.shape[0] for _, ims in rows for _, im in ims)
img = Image.new("RGB", (180 + 6 * (TW + 3), len(rows) * (th + 16) + 4), (20, 20, 20)); d = ImageDraw.Draw(img)
for r, (name, ims) in enumerate(rows):
    y = 4 + r * (th + 16); d.text((2, y + th // 2), name, fill=(220, 220, 220), font=font)
    for j, (fi, im) in enumerate(ims):
        img.paste(Image.fromarray(im), (180 + j * (TW + 3), y)); d.text((180 + j * (TW + 3), y + th), f"f{fi}", fill=(255, 220, 120), font=font)
img.save(out, quality=85); print("saved", out)
