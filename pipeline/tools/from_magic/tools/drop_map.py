"""Beat-by-beat map of the cut window from the stems -> edit/music/drop_map.{md,json}"""
import json, numpy as np, soundfile as sf, librosa
T0 = 100.0           # stems start at song 100 s
START = 109.8791     # output t=0 (grid beat 234)
FPS = 24
B = json.load(open("music/Nhato - Magic.beats.json")); P = B["beat_period"]; a0 = B["grid_start"]
def load(n):
    y, sr = sf.read(f"music/stems/{n}.wav"); return y.mean(1).astype(np.float32), sr
bass, sr = load("bass"); drums, _ = load("drums"); other, _ = load("other")
H = 64; dt = H / sr
def env_db(y):
    r = librosa.feature.rms(y=y, frame_length=512, hop_length=H)[0]; return 20 * np.log10(r + 1e-6)
bE, dE, oE = env_db(bass), env_db(drums), env_db(other)
Sb = np.abs(librosa.stft(bass, n_fft=2048, hop_length=H))
cent = librosa.feature.spectral_centroid(S=Sb, sr=sr)[0]
f0, vflag, _ = librosa.pyin(bass, fmin=30, fmax=400, sr=sr, frame_length=2048, hop_length=H)
d_on = librosa.onset.onset_strength(y=drums, sr=sr, hop_length=H); d_on /= np.percentile(d_on, 99.5)
o_on = librosa.onset.onset_strength(y=other, sr=sr, hop_length=H); o_on /= np.percentile(o_on, 99.5)
def idx(t): return int(round((t - T0) / dt))
def peak(arr, t, r=4):
    i = idx(t); return float(arr[max(0, i - r):i + r + 1].max())
rows = []
for k in range(234, 322):
    t0 = a0 + k * P; t1 = t0 + P
    i0, i1 = idx(t0), idx(t1)
    e = bE[i0:i1]; es = np.convolve(e, np.ones(7) / 7, mode="same")
    depth = float(np.percentile(es, 92) - np.percentile(es, 8))
    # LFO rate: prominent envelope peaks per beat
    pk = 0
    w = max(3, int(len(es) / 16))
    for j in range(1, len(es) - 1):
        lo, hi = max(0, j - w), min(len(es), j + w + 1)
        if es[j] == es[lo:hi].max() and es[j] - es[lo:hi].min() >= 5: pk += 1
    lvl = float(np.mean(e)); low_frac = float(np.mean(e < -38))
    ff = f0[i0:i1]; ff = ff[~np.isnan(ff)]
    semis = float(12 * np.log2(np.percentile(ff, 90) / np.percentile(ff, 10))) if len(ff) > 10 else 0.0
    slope = float(12 * np.log2(np.median(ff[-max(1, len(ff)//4):]) / np.median(ff[:max(1, len(ff)//4)]))) if len(ff) > 10 else 0.0
    c = float(np.mean(cent[i0:i1])); csw = float(np.mean(cent[i0 + (i1 - i0)//2:i1]) - np.mean(cent[i0:i0 + (i1 - i0)//2]))
    acc = max(peak(d_on, t0), 0.0); oacc = peak(o_on, t0)
    acc8 = peak(d_on, t0 + P / 2)
    if lvl < -40 or low_frac > 0.5: cls = "gap"
    elif pk >= 4 and depth >= 8: cls = "stutter"
    elif pk >= 2 and depth >= 6: cls = "wobble"
    else: cls = "growl"
    move = ""
    if slope <= -4 or csw < -250: move = "dive"
    elif slope >= 4 or csw > 250: move = "rise"
    bar = (k - 2) // 4 - 58; b = (k - 2) % 4 + 1
    rows.append(dict(beat=k, song_t=round(t0, 3), out_t=round(t0 - START, 3), out_f=int(round((t0 - START) * FPS)),
                     pos=f"{bar}.{b}", bass_db=round(lvl, 1), depth=round(depth, 1), lfo_peaks=pk, pitch_range_st=round(semis, 1),
                     pitch_slope_st=round(slope, 1), centroid=round(c), cent_sweep=round(csw), drum_acc=round(acc, 2),
                     drum_off8=round(acc8, 2), other_acc=round(oacc, 2), cls=cls, move=move))
json.dump(rows, open("music/drop_map.json", "w"), indent=1)
L = ["# Drop map — per beat, from HDemucs stems (bass/drums/other)",
     "out_t/out_f = output timeline (0 = song 1:49.879). class from bass envelope: stutter (>=4 LFO peaks/beat, depth>=8 dB), wobble (2-3 peaks, depth>=6), growl (sustained), gap (bass absent).",
     "move: dive/rise = bass pitch or brightness sweeping down/up inside the beat. drum = kick/transient strength on the beat (off8 = on the 'and').", "",
     "| beat | pos | out_t | out_f | bass dB | depth | LFO pk | pitch range st | slope st | centroid | sweep | drum | off8 | other | class | move |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    L.append(f"| {r['beat']} | {r['pos']} | {r['out_t']:.3f} | {r['out_f']} | {r['bass_db']} | {r['depth']} | {r['lfo_peaks']} | {r['pitch_range_st']} | {r['pitch_slope_st']} | {r['centroid']} | {r['cent_sweep']} | {r['drum_acc']} | {r['drum_off8']} | {r['other_acc']} | {r['cls']} | {r['move']} |")
open("music/drop_map.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[5:]))
