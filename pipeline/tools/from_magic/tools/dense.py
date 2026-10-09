"""Dense sheets: every STEP frames, 10 per row, label f# and shot id; 2 clips per image -> edit/verify/dense_XX.jpg"""
import json, cv2, sys
from PIL import Image, ImageDraw, ImageFont
STEP = 8; TW = 150; COLS = 10
S = json.load(open("shots/shots.json"))["clips"]
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 11); big = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 14)
def clip_img(key, c):
    cap = cv2.VideoCapture(c["path"]); n = c["frames"]; thumbs = []
    sid = {f: s["id"].split("_")[-1] for s in c["shots"] for f in range(s["start_frame"], s["end_frame"])}
    want = set(range(0, n, STEP)) | {s["start_frame"] for s in c["shots"]}
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        if i in want:
            h, w = fr.shape[:2]; thumbs.append((i, cv2.cvtColor(cv2.resize(fr, (TW, int(h * TW / w))), cv2.COLOR_BGR2RGB)))
        i += 1
    th = thumbs[0][1].shape[0]; rows = -(-len(thumbs) // COLS)
    img = Image.new("RGB", (COLS * (TW + 2), 20 + rows * (th + 14)), (18, 18, 18)); d = ImageDraw.Draw(img)
    d.text((2, 2), f"{key}  {c['frames']}f @{c['fps']:g}", fill=(255, 255, 255), font=big)
    starts = {s["start_frame"] for s in c["shots"]}
    for k, (fi, t) in enumerate(thumbs):
        x, y = (k % COLS) * (TW + 2), 20 + (k // COLS) * (th + 14)
        img.paste(Image.fromarray(t), (x, y))
        d.text((x + 1, y + th), f"f{fi} {sid.get(fi,'')}", fill=(255, 120, 120) if fi in starts else (200, 200, 140), font=font)
    return img
keys = list(S.keys())
for gi in range(0, len(keys), 2):
    ims = [clip_img(k, S[k]) for k in keys[gi:gi + 2]]
    W = max(i.width for i in ims); H = sum(i.height for i in ims) + 6
    out = Image.new("RGB", (W, H), (0, 0, 0)); y = 0
    for i in ims: out.paste(i, (0, y)); y += i.height + 6
    out.save(f"verify/dense_{gi // 2:02d}.jpg", quality=80)
print("done", -(-len(keys) // 2), "sheets")
