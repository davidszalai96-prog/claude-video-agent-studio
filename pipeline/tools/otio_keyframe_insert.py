# Author a Resolve-importable OTIO "insert" timeline with a cross dissolve, a constant retime and
# keyframed zoom/opacity (Resolve_OTIO effect metadata). Measured working on Resolve 21.0.4.5 free
# (2026-09-29): import via timeline.import_timeline_checked(importSourceClips=True, sourceClipsPath=<media dir>),
# then place the new timeline's pool item with media_pool.append_to_timeline (record_frame relative to timeline start).
# Keys are clip-relative RECORD frames (0 = clip's first frame; negatives cover transition pre-roll).
# Source frames are timecode-absolute (these H3 clips start at 00:00:00:00, so 0-based).
import json, copy, math
FPS = 24.0
MEDIA = r"C:\CU\output\video\MiniMax_H3_00295_.mp4"
NAME = "MiniMax_H3_00295_.mp4"

def rt(v): return {"OTIO_SCHEMA": "RationalTime.1", "rate": FPS, "value": float(v)}
def trange(s, d): return {"OTIO_SCHEMA": "TimeRange.1", "duration": rt(d), "start_time": rt(s)}

# ---- the plan (insert-timeline frames t = 0..51, one bar of 110 BPM at 24 fps) ----
BEATS = [(0, 0.15), (13, 0.06), (26, 0.10), (39, 0.06)]   # frame, zoom excess (kick beats 1+3 bigger)
DECAY = 0.6
def zoom(t):
    z = 1.0
    for b, a in BEATS:
        if t >= b:
            z = 1.0 + a * DECAY ** (t - b)
    return round(z, 4) if z - 1.0 > 0.002 else 1.0
A_SRC, A_DUR = 206, 26          # 100% speed, beats 1-2
B_SRC, B_DUR, B_SPEED = 219, 26, 0.5   # 50% slow-mo replay of src 219-232, beats 3-4
X_IN, X_OUT = 3, 3              # 6-frame cross dissolve centred on beat 3 (t=26)
FADE_IN = {0: 15.0, 1: 40.0, 2: 65.0, 3: 85.0, 4: 100.0}            # t -> opacity
FADE_OUT = {45: 100.0, 46: 85.0, 47: 70.0, 48: 55.0, 49: 40.0, 50: 25.0, 51: 10.0}

def zoom_keys(t0, t1, offset):
    """Keys for insert frames t0..t1 (inclusive) at clip-relative frame r = t - offset.
    Keep every frame where the curve moves, plus the flat-segment ends so linear interpolation reproduces it."""
    ts = list(range(t0, t1 + 1))
    keys = {}
    for i, t in enumerate(ts):
        z = zoom(t)
        prev = zoom(t - 1) if i > 0 else None
        nxt = zoom(t + 1) if i < len(ts) - 1 else None
        if prev is None or nxt is None or z != prev or z != nxt:
            keys[t - offset] = z
    return keys

def kf_param(pid, keys, default, value, lo, hi):
    return {"Default Parameter Value": default,
            "Key Frames": {str(k): {"Value": v, "Variant Type": "Double"} for k, v in sorted(keys.items())},
            "Parameter ID": pid, "Parameter Value": value, "Variant Type": "Double",
            "maxValue": hi, "minValue": lo}

def transform_fx(keys):
    return {"OTIO_SCHEMA": "Effect.1", "metadata": {"Resolve_OTIO": {
        "Display Type": 1, "Effect Name": "Transform", "Enabled": True, "Name": "Transform",
        "Parameters": [kf_param("transformationZoomX", keys, 1.0, 1.0, 0.0, 100.0),
                       kf_param("transformationZoomY", keys, 1.0, 1.0, 0.0, 100.0)], "Type": 2}},
        "name": "", "effect_name": "Resolve Effect"}

def composite_fx(keys):
    return {"OTIO_SCHEMA": "Effect.1", "metadata": {"Resolve_OTIO": {
        "Display Type": 1, "Effect Name": "Composite", "Enabled": True, "Name": "Composite",
        "Parameters": [kf_param("opacity", keys, 100.0, 100.0, 0.0, 100.0)], "Type": 1}},
        "name": "", "effect_name": "Resolve Effect"}

def clip(src, dur, effects):
    return {"OTIO_SCHEMA": "Clip.2", "metadata": {"Resolve_OTIO": {}}, "name": NAME,
            "source_range": trange(src, dur), "effects": effects, "markers": [], "enabled": True,
            "media_references": {"DEFAULT_MEDIA": {"OTIO_SCHEMA": "ExternalReference.1", "metadata": {}, "name": NAME,
                                                   "available_range": trange(0, 362), "available_image_bounds": None,
                                                   "target_url": MEDIA}},
            "active_media_reference_key": "DEFAULT_MEDIA"}

def build(name, with_fx=True):
    # A is visible t=0..(A_DUR-1+X_OUT) (tail handle during the dissolve); B from t=A_DUR-X_IN, r = t - A_DUR
    a_fx = [transform_fx(zoom_keys(0, A_DUR - 1 + X_OUT, 0)), composite_fx(FADE_IN)] if with_fx else []
    b_fx = [{"OTIO_SCHEMA": "LinearTimeWarp.1", "metadata": {}, "name": "", "effect_name": "", "time_scalar": B_SPEED}]
    if with_fx:
        b_fx += [transform_fx(zoom_keys(A_DUR - X_IN, A_DUR + B_DUR - 1, A_DUR)),
                 composite_fx({t - A_DUR: v for t, v in FADE_OUT.items()})]
    a = clip(A_SRC, A_DUR, a_fx)
    b = clip(B_SRC, B_DUR, b_fx)
    x = {"OTIO_SCHEMA": "Transition.1", "metadata": {}, "name": "Cross Dissolve", "transition_type": "SMPTE_Dissolve",
         "in_offset": rt(X_IN), "out_offset": rt(X_OUT)}
    track = {"OTIO_SCHEMA": "Track.1", "metadata": {"Resolve_OTIO": {"Locked": False}}, "name": "Video 1",
             "source_range": None, "effects": [], "markers": [], "enabled": True, "children": [a, x, b], "kind": "Video"}
    return {"OTIO_SCHEMA": "Timeline.1", "metadata": {"Resolve_OTIO": {"Resolve OTIO Meta Version": "1.0"}},
            "name": name, "global_start_time": rt(86400),
            "tracks": {"OTIO_SCHEMA": "Stack.1", "metadata": {}, "name": "", "source_range": None,
                       "effects": [], "markers": [], "enabled": True, "children": [track]}}

if __name__ == "__main__":
    import sys
    doc = build("Pulse insert 0156 (Claude)")
    out = sys.argv[1] if len(sys.argv) > 1 else "pulse_insert_0156.otio"
    json.dump(doc, open(out, "w"), indent=4)
    print("zoom curve:", [zoom(t) for t in range(52)])
    tr = doc["tracks"]["children"][0]["children"]
    for c in (tr[0], tr[2]):
        for e in c["effects"]:
            m = e["metadata"].get("Resolve_OTIO")
            if m:
                print(m["Effect Name"], {p["Parameter ID"]: list(p["Key Frames"].items())[:3] + ["..."] for p in m["Parameters"][:1]})
                print("   keys:", {k: v["Value"] for k, v in m["Parameters"][0]["Key Frames"].items()})
