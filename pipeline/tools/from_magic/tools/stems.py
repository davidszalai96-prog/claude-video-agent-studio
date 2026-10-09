"""HDemucs (torchaudio HDEMUCS_HIGH_MUSDB_PLUS) stems for song 100-160 s -> edit/music/stems/*.wav"""
import subprocess, sys, numpy as np, torch, soundfile as sf
from pathlib import Path
from torchaudio.pipelines import HDEMUCS_HIGH_MUSDB_PLUS as BUNDLE
from torchaudio.transforms import Fade
song, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
T0, DUR = 100.0, 60.0
sr = BUNDLE.sample_rate
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(song), "-ss", str(T0), "-t", str(DUR), "-vn", "-ac", "2",
                      "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
wav = torch.from_numpy(np.frombuffer(raw, np.float32).reshape(-1, 2).T.copy())
dev = "cuda"
model = BUNDLE.get_model().to(dev).eval()
ref = wav.mean(0)
x = ((wav - ref.mean()) / ref.std())[None].to(dev)
seg, ovl = int(sr * 10.0), int(sr * 0.1)
fade = Fade(fade_in_len=0, fade_out_len=ovl, fade_shape="linear")
n = x.shape[-1]
final = torch.zeros(1, len(model.sources), 2, n, device=dev)
start, end = 0, seg + ovl
with torch.inference_mode():
    while start < n - ovl:
        chunk = x[:, :, start:end]
        y = fade(model(chunk))
        final[:, :, :, start:end] += y
        if start == 0:
            fade.fade_in_len = ovl
            start += seg - ovl
        else:
            start += seg
        end += seg
        if end >= n:
            fade.fade_out_len = 0
final = final[0] * ref.std() + ref.mean()
for name, s in zip(model.sources, final.cpu().numpy()):
    sf.write(out / f"{name}.wav", s.T, sr)
    print(name, f"rms {20*np.log10(np.sqrt((s**2).mean())+1e-9):.1f} dBFS")
print("stems start at song", T0, "s")
