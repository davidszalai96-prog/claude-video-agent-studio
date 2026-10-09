"""Shot plan (source frames + beats) -> edit/plan.json, plus a lint of the drop rules."""
import json
import numpy as np

S = json.load(open("shots/shots.json"))["clips"]
C = json.load(open("shots/characters.json"))
SIM = json.load(open("shots/similarity.json"))
MOT = json.load(open("shots/motion.json"))
sidx = {i: k for k, i in enumerate(SIM["ids"])}
CHAR, LOOK = C["char"], C["look"]
K = {"aer": "Aerial_Wind_Sovereign1", "but": "Celestial_Butterfly_Oracle", "cin": "Cinematic_Fantasy_Animation",
     "kit": "Celestial_Flame_Kitsune", "pea": "Celestial_Peacock_Oracle", "scr": "Celestial_Scribe_Ascension",
     "chr": "Chronomancer_Elysia", "tw": "Time_Weaver_Cinematic", "cry": "Crystal_Veil_Archer_Showcase",
     "dag": "Elegant_Golden_Dagger_Dance", "nin": "Golden_Ninja_Showcase", "ld": "Lunar_Dream_Transformation",
     "le": "Lunar_Eclipse_Transformation", "rad": "Radiant_Aegis_Ascension", "ver": "Verdant_Genesis_Showcase",
     "ser": "White_Serpent_Transformation", "m07": "MiniMax_H3_00007", "m21": "MiniMax_H3_00021",
     "m22": "MiniMax_H3_00022", "m51": "MiniMax_H3_00051", "m356": "MiniMax_H3_00356",
     "cri": "MiniMax_H3_artcraftcrimson", "lov": "MiniMax_H3_celestiallovemessenger", "cyb": "MiniMax_H3_chatgptpull"}
B, D = "build", "drop"
# (clip, first source frame, beats, options)
SEQ = [
    # BUILD bars 0-4.2: slowed 0.8, cut rate accelerates 4 -> 2 -> 1 beats
    ("aer", 12, 4, dict(sec=B, note="opener: floating isle over clouds, slow push-in")),
    ("kit", 4, 2, dict(sec=B, note="eyes open and ignite")),
    ("rad", 4, 2, dict(sec=B, note="praying hands, gold light lines")),
    ("but", 102, 2, dict(sec=B, note="staff raised, light gathers")),
    ("scr", 8, 1, dict(sec=B, note="glowing book")),
    ("ser", 84, 1, dict(sec=B, note="serpent spirit rises")),
    ("chr", 176, 1, dict(sec=B, note="sub swell: gold rays burst")),
    ("lov", 125, 1, dict(sec=B, note="sub swell: wings open")),
    ("cry", 224, 1, dict(sec=B, note="sub swell: crystal wings unfold")),
    ("nin", 214, 1, dict(sec=B, note="riser sweep up: golden burst")),
    ("pea", 186, 1, dict(sec=B, note="energy rings expand")),
    ("cin", 145, 1, dict(punch=1.08, sec=B, note="bass hit: golem stomp")),
    # PIANO 4.3-4.4
    ("le", 170, 2, dict(speed=0.5, sec="piano", note="calm piano: eyes open at half speed")),
    # DROP 5.1 ->
    ("cri", 213, 1, dict(punch=1.18, flash=0.8, sec=D, note="DROP: crimson explosion")),
    ("m07", 262, 1, dict(punch=1.08, sec=D, note="pitch dive: beam strikes down")),
    ("pea", 140, 1, dict(sec=D, note="sparks vs ninjas")),
    ("m21", 248, 0.5, dict(sec=D, note="filter wobble: lance flash")),
    ("nin", 108, 0.5, dict(sec=D, note="dagger hits post")),
    ("m356", 80, 1, dict(punch=1.12, sec=D, note="hex shield impact")),
    ("scr", 176, 1, dict(sec=D, note="blue magic blast")),
    ("kit", 109, 0.5, dict(sec=D, note="gated lead: fox spirit")),
    ("m51", 226, 0.5, dict(sec=D, note="crystal burst")),
    ("aer", 144, 1, dict(sec=D, note="wind blast")),
    ("cry", 138, 1, dict(punch=1.12, sec=D, note="bright attack: ice explosion")),
    ("le", 203, 1, dict(sec=D, note="scythe arc")),
    ("rad", 116, 1, dict(sec=D, note="lead swell: transformation flash")),
    ("cri", 74, 0.5, dict(sec=D, note="stutter: spin slash")),
    ("m07", 84, 0.5, dict(sec=D, note="stutter: overhead spin")),
    ("m356", 170, 1, dict(punch=1.12, sec=D, note="fire vs ice")),
    ("ser", 204, 1, dict(sec=D, note="fan swirl")),
    ("aer", 104, 2, dict(pulse="beats", sec=D, note="growl hold: wind magic swirls up")),
    ("cyb", 117, 1, dict(sec=D, note="choppy: city dive")),
    ("dag", 156, 1, dict(sec=D, note="blade sweep")),
    ("but", 182, 0.5, dict(sec=D, note="chop: wing flash")),
    ("kit", 206, 0.5, dict(sec=D, note="chop: fire swirl")),
    ("m51", 268, 1, dict(pulse="beats", sec=D, note="bass solo: golem face")),
    ("cri", 161, 0.5, dict(sec=D, note="chop: red eyes")),
    ("m21", 85, 0.5, dict(sec=D, note="chop: lance strike")),
    ("ver", 142, 1, dict(sec=D, note="vine whip")),
    ("m07", 151, 0.5, dict(sec=D, note="bright attack: gold sun burst")),
    ("cyb", 140, 0.5, dict(sec=D, note="city dive")),
    ("ld", 176, 1, dict(sec=D, note="whoosh sweep")),
    ("m356", 200, 2, dict(pulse="beats", sec=D, note="darkest growl: ice dragon rises")),
    ("scr", 20, 1, dict(sec=D, note="pitch dive: tilt down")),
    ("aer", 184, 1, dict(sec=D, note="pitch rise: tornado")),
    ("cin", 187, 1, dict(punch=1.15, flash=0.3, sec=D, note="kick: purple blast charges")),
    ("kit", 184, 0.5, dict(sec=D, note="quick cut: fire")),
    ("nin", 150, 0.5, dict(sec=D, note="quick cut: golden rings")),
    ("m21", 214, 1, dict(sec=D, note="circle slash")),
    ("m07", 104, 3, dict(sec=D, note="drone dip: flowing lance run through digital space")),
    ("rad", 211, 0.5, dict(sec=D, note="rise: sword swing")),
    ("ver", 120, 0.5, dict(sec=D, note="rise: vines")),
    ("m07", 286, 1, dict(punch=1.15, flash=0.3, sec=D, note="re-entry: light beam")),
    ("but", 160, 1, dict(sec=D, note="wings spread")),
    ("m356", 330, 1, dict(punch=1.12, sec=D, note="kick: avatar clash")),
    ("kit", 150, 1, dict(sec=D, note="fire fan")),
    ("dag", 176, 1, dict(sec=D, note="dagger vortex")),
    ("m51", 205, 1, dict(sec=D, note="blue blast")),
    ("scr", 150, 0.5, dict(sec=D, note="chop: pages fan")),
    ("cri", 176, 0.5, dict(sec=D, note="chop: slash arc")),
    ("cry", 94, 1, dict(punch=1.12, sec=D, note="kick: arrow release")),
    ("m21", 114, 0.5, dict(sec=D, note="stutter: spin")),
    ("aer", 160, 0.5, dict(sec=D, note="stutter: wind")),
    ("pea", 126, 0.5, dict(sec=D, note="chop: blue slash")),
    ("chr", 84, 0.5, dict(sec=D, note="chop: spin trails")),
    ("ver", 104, 0.5, dict(sec=D, note="stutter: vines")),
    ("ser", 176, 0.5, dict(sec=D, note="stutter: serpent swirl")),
    ("cyb", 190, 0.5, dict(sec=D, note="stutter: city fly")),
    ("ld", 150, 0.5, dict(sec=D, note="stutter: whale")),
    ("m07", 212, 1, dict(sec=D, note="gold rings run")),
    ("lov", 236, 1, dict(sec=D, note="rising: letters swirl")),
    ("kit", 100, 0.5, dict(sec=D, note="bass: fox spirit")),
    ("dag", 226, 0.5, dict(sec=D, note="zap gap: white flash")),
    ("m22", 83, 1, dict(sec=D, note="chop: blue explosion")),
    ("scr", 210, 1, dict(punch=1.1, sec=D, note="kick: magic vortex")),
    ("chr", 90, 0.5, dict(sec=D, note="chop: spin trails")),
    ("m356", 186, 0.5, dict(sec=D, note="chop: umbrella spin")),
    ("cry", 106, 0.5, dict(sec=D, note="chop: ice crystals")),
    ("cin", 165, 0.5, dict(sec=D, note="chop: sprint")),
    ("cri", 128, 0.5, dict(sec=D, note="chop: hair whip")),
    ("aer", 176, 0.5, dict(sec=D, note="chop: wind")),
    ("le", 186, 0.5, dict(sec=D, note="chop + rise")),
    ("m07", 230, 0.5, dict(sec=D, note="chop + rise: gold ring")),
    ("ser", 160, 1, dict(sec=D, note="fan dance")),
    ("chr", 124, 1, dict(sec=D, note="bass stops: rings")),
    # 19.3-19.4 heavy chop + zaps: justified red/blue A/B strobe
    ("cri", 104, 0.5, dict(sec=D, ab=True, note="strobe A: crimson collage")),
    ("scr", 160, 0.25, dict(sec=D, ab=True, note="strobe B: blue-white page burst")),
    ("cri", 110, 0.25, dict(sec=D, ab=True, note="strobe A")),
    ("scr", 163, 0.25, dict(sec=D, ab=True, note="strobe B")),
    ("cri", 113, 0.25, dict(sec=D, ab=True, note="strobe A")),
    ("scr", 166, 0.25, dict(sec=D, ab=True, note="strobe B")),
    ("cri", 116, 0.25, dict(sec=D, ab=True, note="strobe A")),
    ("kit", 120, 1, dict(punch=1.1, sec=D, note="kick: fire wings")),
    ("nin", 138, 1, dict(sec=D, note="golden rings")),
    ("m356", 240, 1, dict(punch=1.12, sec=D, note="fire vs ice beams")),
    # BREAK + END
    ("ld", 200, 2, dict(speed=0.5, sec="break", note="drone break: whale and moon, half speed")),
    ("cri", 168, 1, dict(freeze=True, flash=0.4, sec="break", note="bass gap: frozen red-eyed gaze")),
    ("m51", 188, 1, dict(punch=1.15, flash=0.6, sec="end", note="end hit: teal crystal explosion")),
    ("pea", 216, 1, dict(sec="end", note="final image: peacock fan opens")),
]


def shot_at(key, f):
    for s in S[key]["shots"]:
        if s["start_frame"] <= f < s["end_frame"]:
            return s
    raise SystemExit(f"no shot at {key} f{f}")


plan_seq, rows = [], []
for clip, f, beats, x in SEQ:
    key = K[clip]
    s = shot_at(key, f)
    fps = S[key]["fps"]
    it = {"shot": s["id"], "beats": beats, "align": round((f - s["start_frame"]) / fps + 1e-4, 4), "note": x["note"]}
    for k in ("speed", "punch", "flash", "pulse", "freeze"):
        if k in x:
            it[k] = x[k]
    plan_seq.append(it)
    rows.append((key, s, f, beats, x))
plan = {"song": "../Nhato - Magic.mp3", "start_bar": 58, "fps": 24, "output": {"width": 1280, "height": 720},
        "grade": "eq=contrast=1.06:saturation=1.05,curves=master='0/0 0.25/0.23 0.75/0.77 1/1'",
        "music": {"fade_in": 0.08, "fade_out": 0.4, "gain_db": -3.5}, "pulse_zoom": {"downbeat": 1.10, "kick": 1.07, "other": 1.05},
        "sequence": plan_seq}
json.dump(plan, open("plan.json", "w"), indent=1)
tot = sum(r[3] for r in rows)
print(f"{len(rows)} items, {tot:g} beats (need 88)")

# lint
med = float(np.median([v["motion_mean"] for v in MOT.values()]))
thr, soft = 0.84, 0.80  # same-character median vs different-look p90 of this pool
problems, used, hist, softs = [], {}, [], []
beat = 0.0
for i, (key, s, f, beats, x) in enumerate(rows):
    ch, sec = CHAR[key], x["sec"]
    sp = x.get("speed", 1.0)
    n_src = 1 if x.get("freeze") else max(1, int(round(beats * 11.25 * sp * S[key]["fps"] / 24)))
    m = MOT.get(s["id"])
    seg = m["curve"][max(0, f - m["start"] - 1): f - m["start"] - 1 + n_src] if m else []
    mot = float(np.mean(seg)) if seg else 0.0
    if f + n_src > s["end_frame"]:
        problems.append(f"#{i+1} {s['id']} f{f}+{n_src} runs past shot end {s['end_frame']} (beatmap shifts it earlier)")
    if sec in (D, "end") and not x.get("freeze") and not x.get("ab") and mot < med * 0.9:
        problems.append(f"#{i+1} {s['id']} f{f}: low motion {mot:.2f} < median {med:.2f}")
    for (a, b) in used.get(s["id"], []):
        if f < b and f + n_src > a and not x.get("ab"):
            problems.append(f"#{i+1} {s['id']} f{f}-{f+n_src} overlaps an earlier use f{a}-{b}")
    used.setdefault(s["id"], []).append((f, f + n_src))
    if i and sec in (D, "end", "break"):
        pkey, ps, px = rows[i - 1][0], rows[i - 1][1], rows[i - 1][4]
        ab = x.get("ab") or px.get("ab")
        if CHAR[pkey] == ch and not ab:
            problems.append(f"#{i+1} same character {ch} back to back")
        if LOOK[CHAR[pkey]] == LOOK[ch] and not ab:
            problems.append(f"#{i+1} same look '{LOOK[ch]}' back to back ({CHAR[pkey]}->{ch})")
        if ps["id"] in sidx and s["id"] in sidx:
            sv = SIM["sim"][sidx[ps["id"]]][sidx[s["id"]]]
            if sv >= thr and not ab:
                problems.append(f"#{i+1} CLIP sim {sv:.2f} >= {thr} ({ps['id']} -> {s['id']})")
            elif sv >= soft and not ab:
                softs.append(f"#{i+1} {sv:.2f} {CHAR[pkey]}->{ch}")
    if sec == D and not x.get("ab"):
        recent = [c for (bb, c) in hist if beat - bb < 8]
        if recent.count(ch) >= 2:
            problems.append(f"#{i+1} {ch} a 3rd time within 8 beats")
    hist.append((beat, ch))
    beat += beats
    print(f"{i+1:3d} n{beat-beats:5.2f} {sec:5s} {ch} {s['id']:38s} f{f:<4d} {beats:<5g} sp{sp:<4g} mot {mot:5.2f}  {x['note']}")
print("\nLINT:", "clean" if not problems else f"{len(problems)} problem(s)")
for p in problems:
    print("  " + p)
