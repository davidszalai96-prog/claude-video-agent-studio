"""Per-frame motion energy + luma per shot -> edit/shots/motion.json (impact/flash peaks for align)."""
import json, cv2, numpy as np
S = json.load(open("shots/shots.json"))["clips"]
out = {}
for key, c in S.items():
    cap = cv2.VideoCapture(c["path"]); prev = None; diff, luma, flow = [], [], []
    pg = None
    while True:
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(cv2.resize(fr, (192, 108), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        diff.append(0.0 if prev is None else float(np.abs(g.astype(np.float32) - prev).mean()))
        if pg is not None:
            f = cv2.calcOpticalFlowFarneback(pg, g, None, 0.5, 3, 13, 3, 5, 1.1, 0)
            flow.append(float(np.hypot(f[..., 0], f[..., 1]).mean()))
        else:
            flow.append(0.0)
        luma.append(float(g.mean() / 255)); prev = g.astype(np.float32); pg = g
    diff, luma, flow = np.array(diff), np.array(luma), np.array(flow)
    for s in c["shots"]:
        a, b = s["start_frame"], s["end_frame"]
        if b - a < 3: continue
        d = diff[a + 1:b]; fl = flow[a + 1:b]; L = luma[a:b]
        m = 0.5 * fl + 0.05 * d  # motion score: flow (px/frame @192w) + a little raw change
        peaks = []
        for i in range(1, len(m) - 1):
            lo, hi = max(0, i - 6), min(len(m), i + 7)
            if m[i] == m[lo:hi].max() and m[i] > 1.4 * np.median(m) and m[i] > 0.6: peaks.append([a + 1 + i, round(float(m[i]), 2)])
        flashes = [[a + i, round(float(L[i] - L[i - 1]), 3)] for i in range(1, len(L)) if L[i] - L[i - 1] > 0.06]
        out[s["id"]] = {"start": a, "end": b, "motion_mean": round(float(m.mean()), 2), "motion_p80": round(float(np.percentile(m, 80)), 2),
                        "curve": [round(float(x), 2) for x in m], "peaks": sorted(peaks, key=lambda p: -p[1])[:6], "flashes": flashes[:6],
                        "luma_mean": round(float(L.mean()), 3)}
json.dump(out, open("shots/motion.json", "w"), indent=1)
vals = sorted(v["motion_mean"] for v in out.values())
print("shots", len(out), "motion_mean median", vals[len(vals)//2], "p25", vals[len(vals)//4], "p75", vals[3*len(vals)//4])
for k, v in sorted(out.items(), key=lambda kv: kv[1]["motion_mean"]):
    print(f"{k:42s} {v['end']-v['start']:4d}f  motion {v['motion_mean']:5.2f}  p80 {v['motion_p80']:5.2f}  peaks {v['peaks'][:3]}  flashes {v['flashes'][:2]}")
