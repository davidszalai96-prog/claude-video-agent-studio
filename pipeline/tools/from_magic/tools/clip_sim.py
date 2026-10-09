"""CLIP ViT-H-14 (local HF-format safetensors) image embeddings per shot -> edit/shots/similarity.json"""
import json, sys, numpy as np, torch, cv2, open_clip
from safetensors.torch import load_file
from transformers import CLIPConfig, CLIPModel
W = r"C:\CU\models\clip_vision\clip-vit-h-15-laion2b-s32B-b79k.safetensors"
cfg = CLIPConfig(text_config=dict(vocab_size=49408, hidden_size=1024, intermediate_size=4096, num_hidden_layers=24,
                                  num_attention_heads=16, max_position_embeddings=77, hidden_act="gelu", projection_dim=1024),
                 vision_config=dict(hidden_size=1280, intermediate_size=5120, num_hidden_layers=32, num_attention_heads=16,
                                    image_size=224, patch_size=14, hidden_act="gelu", projection_dim=1024),
                 projection_dim=1024)
model = CLIPModel(cfg)
missing, unexpected = model.load_state_dict(load_file(W), strict=False)
print("missing", [m for m in missing if "position_ids" not in m][:5], "unexpected", unexpected[:5])
model = model.half().cuda().eval()
MEAN = np.array([0.48145466, 0.4578275, 0.40821073]); STD = np.array([0.26862954, 0.26130258, 0.27577711])
def prep(rgb, mode):
    h, w = rgb.shape[:2]
    if mode == "center":
        s = min(h, w); y0, x0 = (h - s) // 2, (w - s) // 2; sq = rgb[y0:y0 + s, x0:x0 + s]
    else:
        s = max(h, w); sq = np.zeros((s, s, 3), np.uint8); sq[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = rgb
    sq = cv2.resize(sq, (224, 224), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
    return ((sq - MEAN) / STD).transpose(2, 0, 1)
S = json.load(open("shots/shots.json"))["clips"]
skip = set(json.load(open(sys.argv[1]))) if len(sys.argv) > 1 else set()
ids, batch = [], []
for key, c in S.items():
    cap = cv2.VideoCapture(c["path"])
    for s in c["shots"]:
        if s["id"] in skip or s["frames"] < 5: continue
        a, b = s["start_frame"], s["end_frame"]
        for fi in (a + (b - a) * 0.2, a + (b - a) * 0.5, a + (b - a) * 0.8):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi)); ok, fr = cap.read()
            rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
            batch += [prep(rgb, "full"), prep(rgb, "center")]
        ids.append(s["id"])
X = torch.tensor(np.array(batch), dtype=torch.float16).cuda()
with torch.no_grad():
    E = torch.cat([model.visual_projection(model.vision_model(pixel_values=X[i:i + 48]).pooler_output) for i in range(0, len(X), 48)]).float()
E = torch.nn.functional.normalize(E, dim=-1).reshape(len(ids), 6, -1).mean(1)
E = torch.nn.functional.normalize(E, dim=-1)
sim = (E @ E.T).cpu().numpy()
# zero-shot hints
tags = {"hair": ["white or silver hair", "blonde hair", "red hair", "purple or lavender hair", "black hair", "brown hair", "teal hair"],
        "palette": ["golden warm colors", "blue colors", "red and crimson colors", "purple colors", "green colors", "pink colors", "cyan and teal colors", "dark black colors"],
        "content": ["a close-up of a face", "a full-body character", "a wide landscape", "a stone golem", "a giant crystal monster", "an explosion of light", "a character reference sheet", "a collage grid of images", "a city at night", "an office", "a magic circle"]}
tok = open_clip.get_tokenizer("ViT-H-14")
hint = {i: {} for i in ids}
with torch.no_grad():
    for g, labels in tags.items():
        T = model.text_projection(model.text_model(input_ids=tok([f"an anime illustration with {l}" if g != "content" else f"anime art: {l}" for l in labels]).cuda()).pooler_output).float()
        T = torch.nn.functional.normalize(T, dim=-1)
        P = (100 * E @ T.T).softmax(-1).cpu().numpy()
        for k, i in enumerate(ids):
            j = int(P[k].argmax()); hint[i][g] = f"{labels[j]} ({P[k, j]:.2f})"
# clusters: agglomerative, average linkage on cosine distance
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
D = np.clip(1 - sim, 0, 2); np.fill_diagonal(D, 0)
Z = linkage(squareform(D, checks=False), "average")
cl = fcluster(Z, t=0.18, criterion="distance")
off = sim[np.triu_indices(len(ids), 1)]
out = {"ids": ids, "sim": np.round(sim, 3).tolist(), "cluster": {i: int(c) for i, c in zip(ids, cl)}, "hints": hint,
       "pctl": {p: round(float(np.percentile(off, p)), 3) for p in (50, 60, 70, 80, 90, 95)}}
json.dump(out, open("shots/similarity.json", "w"), indent=1)
print("shots", len(ids), "pair-sim percentiles", out["pctl"])
groups = {}
for i, c in zip(ids, cl): groups.setdefault(int(c), []).append(i)
for c, m in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    print(f"cluster {c} ({len(m)}): " + ", ".join(m))
