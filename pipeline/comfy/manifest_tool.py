"""Make, ingest and check workflow manifests for the user's saved ComfyUI workflows (project templates).

    .venv\\Scripts\\python.exe pipeline\\comfy\\manifest_tool.py list
    ... manifest_tool.py inspect <template>                 # nodes, MODEL chain, per-job candidates (from disk)
    ... manifest_tool.py init <template> --kind h3          # draft manifest; H3 fields are detected
    ... manifest_tool.py modes <id> <sol|chunked|sage>      # node modes to apply in the page before conversion
    ... manifest_tool.py ingest <id> <page_output.json>     # snapshot + default profile from a studio-tab conversion
    ... manifest_tool.py check <id>                         # manifest vs saved file, snapshot and profile

Reads the user's workflow files; never writes them. Writes only under pipeline/comfy/.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import studio_lib as lib  # noqa: E402

WORKFLOWS = Path(r"C:\CU\user\default\workflows")
COMFY = lib.REPO / "pipeline" / "comfy"
MANIFESTS, PROFILES, SNAPSHOTS = COMFY / "manifests", COMFY / "profiles", COMFY / "snapshots"
PIN = COMFY / "env_pin.json"
API = "http://127.0.0.1:8188"

ATTENTION_ROLES = {
    "ModelAttentionBackend": "kitchen",
    "PathchSageAttentionKJ": "sage_kj",
    "MiniMaxChunkFeedForward": "chunk_ff",
    "MiniMaxLowVRAMAttention": "low_vram",
    "MiniMaxH3MemoryEfficientSageAttentionPatch": "mem_eff_sage",
    "BlockSparseAttention": "sol",
    "SolAttnPatch": "sol",
    "SolAttnMiniMax": "sol",
}
PROFILE_ON = {"sol": {"kitchen", "sol"}, "chunked": {"kitchen", "chunk_ff", "low_vram"}, "sage": {"sage_kj", "mem_eff_sage"}}
MODE = {0: "on", 2: "muted", 4: "bypass"}


# --- saved workflow (UI format) ------------------------------------------------

class UIWorkflow:
    def __init__(self, template: str):
        self.template = template
        self.path = WORKFLOWS / f"{template}.json"
        self.raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(self.raw).hexdigest()
        self.data = json.loads(self.raw)
        self.nodes = {str(n["id"]): n for n in self.data["nodes"]}
        self.links = {l[0]: l for l in self.data.get("links", [])}  # id: [id, from, from_slot, to, to_slot, type]
        self.subgraphs = {sg["id"]: sg for sg in (self.data.get("definitions") or {}).get("subgraphs", [])}

    def api_ids(self) -> dict[str, dict]:
        """Every node under the ID graphToPrompt uses: top level, and 'parent:child' inside subgraphs."""
        out = {}

        def walk(nodes, prefix):
            for n in nodes:
                nid = f"{prefix}{n['id']}"
                out[nid] = n
                if n["type"] in self.subgraphs:
                    walk(self.subgraphs[n["type"]].get("nodes", []), f"{nid}:")
        walk(self.data["nodes"], "")
        return out

    def upstream(self, node_id: str, input_name: str) -> str | None:
        n = self.nodes.get(node_id)
        for i in (n or {}).get("inputs", []):
            if i.get("name") == input_name and i.get("link") is not None:
                link = self.links.get(i["link"])
                return str(link[1]) if link else None
        return None

    def active(self, cls: str) -> list[str]:
        return [i for i, n in self.nodes.items() if n["type"] == cls and n.get("mode", 0) == 0]

    def model_chain(self) -> list[str]:
        out = {}
        for l in self.links.values():
            if l[5] == "MODEL":
                out.setdefault(str(l[1]), []).append(str(l[3]))
        starts = [i for i, n in self.nodes.items() if n["type"] in ("UNETLoader", "UnetLoaderGGUF", "CheckpointLoaderSimple")]
        chain, cur, seen = [], (starts[0] if starts else None), set()
        while cur and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            nxt = out.get(cur, [])
            cur = nxt[0] if len(nxt) == 1 else None
        return chain


# --- helpers -------------------------------------------------------------------

def object_info(cls: str) -> dict | None:
    try:
        with urllib.request.urlopen(f"{API}/api/object_info/{urllib.parse.quote(cls)}", timeout=10) as r:
            return json.loads(r.read()).get(cls)
    except OSError:
        return None


def widget_input(cls: str) -> str | None:
    """The single value input of a primitive-like node (e.g. PrimitiveFloat -> value, Float -> Number)."""
    info = object_info(cls)
    if not info:
        return None
    req = list(info["input"].get("required", {}))
    return req[0] if len(req) == 1 else None


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def config_hash(api_prompt: dict) -> str:
    return hashlib.sha256(canonical(api_prompt).encode()).hexdigest()


def strip_per_job(api_prompt: dict, manifest: dict) -> tuple[dict, list[str]]:
    """Replace per-job values with placeholders, so the snapshot and hash describe configuration only."""
    out, problems = copy.deepcopy(api_prompt), []
    for name, spec in manifest["per_job"].items():
        for t in spec["targets"]:
            node = out.get(t["node"])
            if node is None:
                problems.append(f"per_job {name}: node {t['node']} not in the converted prompt")
            elif t["input"] not in node.get("inputs", {}):
                problems.append(f"per_job {name}: node {t['node']} ({node.get('class_type')}) has no input {t['input']!r}")
            else:
                node["inputs"][t["input"]] = f"<per_job:{name}>"
    return out, problems


def load_manifest(mid: str) -> dict:
    p = MANIFESTS / f"{mid}.json"
    if not p.exists():
        raise SystemExit(f"No manifest {p.relative_to(lib.REPO)}")
    return json.loads(p.read_text("utf-8"))


def save(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", "utf-8", newline="\n")


def rel(p: Path) -> str:
    return p.relative_to(lib.REPO).as_posix()


def comfy_version() -> str | None:
    return json.loads(PIN.read_text("utf-8"))["environment"]["comfyui_version"] if PIN.exists() else None


# --- commands ------------------------------------------------------------------

def cmd_list(_a):
    files = sorted(WORKFLOWS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    have = {p.stem for p in MANIFESTS.glob("*.json")}
    for p in files:
        if p.name.startswith("."):
            continue
        t = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"{t}  {p.stat().st_size // 1024:5d} KB  {'manifest ' if p.stem in have else '         '} {p.stem}")


def cmd_inspect(a):
    ui = UIWorkflow(a.template)
    print(f"{a.template}: {len(ui.nodes)} top-level nodes, {len(ui.subgraphs)} subgraphs, sha256 {ui.sha256[:16]}…")
    print("\nMODEL chain:")
    for i in ui.model_chain():
        n = ui.nodes[i]
        role = ATTENTION_ROLES.get(n["type"], "")
        print(f"  {i:>5} {MODE.get(n.get('mode', 0), n.get('mode')):6} {n['type']}" + (f"  [{role}]" if role else ""))
    interesting = ("LoadImage", "SaveVideo", "Image Saver", "SaveImage", "PrimitiveString", "PrimitiveFloat", "PrimitiveInt",
                   "RandomNoise", "Seed", "Float", "Anything Everywhere", "ResolutionMaster", "ResolutionSelector",
                   "MiniMaxH3ReferenceToVideo", "ModelPreviewOverrideKJ", "EmptyLatent", "ComfySwitchNode")
    print("\nPer-job candidates and notable nodes (API IDs):")
    for nid, n in ui.api_ids().items():
        if any(k in n["type"] for k in interesting):
            wv = json.dumps(n.get("widgets_values"), ensure_ascii=False)
            print(f"  {nid:>8} {MODE.get(n.get('mode', 0), n.get('mode')):6} {n['type'][:32]:32} {(n.get('title') or '')[:20]:20} {wv[:70]}")


def detect_h3(ui: UIWorkflow) -> dict:
    gen = ui.active("MiniMaxH3ReferenceToVideo")
    if len(gen) != 1:
        raise SystemExit(f"expected one active MiniMaxH3ReferenceToVideo, found {gen}")
    g = gen[0]
    per_job = {}
    p = ui.upstream(g, "prompt")
    if p:
        per_job["prompt"] = {"targets": [{"node": p, "input": widget_input(ui.nodes[p]["type"]) or "value"}], "type": "text"}
    for inp in ui.nodes[g].get("inputs", []):
        name = inp.get("name", "")
        if name.startswith("ref_images.ref_image_") and inp.get("link") is not None:
            src = ui.upstream(g, name)
            per_job[name.split(".")[-1]] = {"targets": [{"node": src, "input": "image"}], "type": "image"}
    seeds = ui.active("RandomNoise")
    if seeds:
        per_job["seed"] = {"targets": [{"node": s, "input": "noise_seed"} for s in seeds], "type": "int"}
    durations = ui.active("PrimitiveFloat")
    if len(durations) == 1:
        per_job["duration_s"] = {"targets": [{"node": durations[0], "input": "value"}], "type": "float"}
    for rs in ui.active("ResolutionSelector"):
        mp = ui.upstream(rs, "megapixels")
        if mp:
            cls = ui.nodes[mp]["type"]
            per_job["megapixels"] = {"targets": [{"node": mp, "input": widget_input(cls) or "value"}],
                                     "type": "float_string" if cls == "Float" else "float"}
    saves = ui.active("SaveVideo")
    if saves:
        per_job["output_prefix"] = {"targets": [{"node": s, "input": "filename_prefix"} for s in saves], "type": "save_prefix"}

    chain = ui.model_chain()
    nodes = {}
    for i in chain:
        role = ATTENTION_ROLES.get(ui.nodes[i]["type"])
        if role:
            nodes[role] = {"node": i, "class": ui.nodes[i]["type"]}
    profiles = {}
    for prof, on in PROFILE_ON.items():
        if prof == "sage" and not ({"sage_kj", "mem_eff_sage"} & set(nodes)):
            continue
        profiles[prof] = {"modes": {v["node"]: (0 if role in on else 4) for role, v in nodes.items()}}
    saved = {v["node"]: ui.nodes[v["node"]].get("mode", 0) for v in nodes.values()}
    saved_profile = next((p for p, spec in profiles.items() if spec["modes"] == saved), "other")
    preview = ui.active("ModelPreviewOverrideKJ")
    return {
        "per_job": per_job,
        "attention": {"chain": chain, "nodes": nodes, "profiles": profiles, "saved_profile": saved_profile},
        "preview_node": preview[0] if preview else None,
        "outputs": [{"node": s, "class": "SaveVideo", "kind": "video"} for s in saves],
    }


def cmd_init(a):
    ui = UIWorkflow(a.template)
    mid = a.id or a.template
    path = MANIFESTS / f"{mid}.json"
    if path.exists() and not a.force:
        raise SystemExit(f"{rel(path)} exists (use --force to redo the draft)")
    m = {"id": mid, "template": a.template, "kind": a.kind, "file": f"workflows/{a.template}.json",
         "ui_sha256": ui.sha256, "status": "draft", "comfy_version": comfy_version(), "updated": lib.now_iso(),
         "per_job": {}, "outputs": [], "rules": ["one GPU job at a time", "never use video references",
                                                 "change only per_job values; forced and wiring entries name their source"]}
    if a.kind == "h3":
        m.update({k: v for k, v in detect_h3(ui).items() if v is not None})
        m["rules"] += ["legacy decode as saved", "free memory after each job", "attention profile sol by default, chunked as fallback"]
        m["measured"] = {p: {"status": "unmeasured"} for p in m["attention"]["profiles"]}
    save(path, m)
    print(f"wrote draft {rel(path)}")
    for e in lib.schema_errors("manifest", m):
        print(f"  to fill in: {e}")


def cmd_modes(a):
    m = load_manifest(a.id)
    prof = (m.get("attention") or {}).get("profiles", {}).get(a.profile)
    if not prof:
        raise SystemExit(f"{a.id} has no attention profile {a.profile!r}")
    print(json.dumps(prof["modes"]))


def cmd_ingest(a):
    m = load_manifest(a.id)
    page = json.loads(Path(a.page_output).read_text("utf-8"))
    if page.get("template") != m["template"]:
        raise SystemExit(f"page output is for {page.get('template')!r}, manifest is for {m['template']!r}")
    api = page["api_prompt"]
    ui = UIWorkflow(m["template"])
    problems = []
    if ui.sha256 != m["ui_sha256"]:
        problems.append("the saved workflow changed since the manifest was drafted (ui_sha256)")
    stripped, p = strip_per_job(api, m)
    problems += p
    for f in m.get("forced", []):
        node = api.get(f["node"])
        if node is None or f["input"] not in node.get("inputs", {}):
            problems.append(f"forced {f['node']}.{f['input']}: not in the converted prompt")
    for w in m.get("wiring", []):
        if w["node"] not in api:
            problems.append(f"wiring {w['node']}.{w['input']}: node not in the converted prompt")
        if w["from"][0] not in api:
            problems.append(f"wiring {w['node']}.{w['input']}: source node {w['from'][0]} not in the converted prompt")
    label = page.get("label", "as_saved")
    if label != "as_saved":
        modes = page.get("profile") or {}
        for nid, mode in modes.items():
            present = nid in api
            if mode == 4 and present:
                problems.append(f"profile {label}: bypassed node {nid} is still in the prompt")
            if mode == 0 and not present:
                problems.append(f"profile {label}: node {nid} is on but missing from the prompt")
    h = config_hash(stripped)
    day = datetime.now().strftime("%Y%m%d")
    snap = SNAPSHOTS / m["id"] / f"{day}_{label}_{h[:12]}.api.json"
    save(snap, {"template": m["template"], "label": label, "profile": page.get("profile"),
                "ui_sha256": ui.sha256, "comfy_version": comfy_version(), "frontend_version": page.get("frontend_version"),
                "converted_at": page.get("converted_at"), "config_hash": h, "nodes": len(api), "api_prompt": stripped})
    print(f"wrote {rel(snap)}  ({len(api)} API nodes, config hash {h[:12]})")
    if label == "as_saved" and not problems:
        values = {nid: {"class": n.get("class_type"),
                        "inputs": {k: v for k, v in n.get("inputs", {}).items() if not isinstance(v, list)}}
                  for nid, n in stripped.items()}
        prof_path = PROFILES / f"{m['id']}.default.json"
        save(prof_path, {"template": m["template"], "ui_sha256": ui.sha256, "config_hash": h, "created": lib.now_iso(),
                         "note": "Every value as the user saved it; per-job values are placeholders. Run requests show changes as a diff against this file.",
                         "ui_modes": page.get("ui_modes"), "values": values})
        m.update({"default_profile": rel(prof_path), "snapshot": rel(snap), "frontend_version": page.get("frontend_version"),
                  "required_classes": sorted({n.get("class_type") for n in api.values()}),
                  "comfy_version": comfy_version(), "updated": lib.now_iso(), "status": "checked"})
        print(f"wrote {rel(prof_path)}")
    att = m.get("attention") or {}
    # The as-saved conversion also verifies the profile the template was saved in.
    verifies = att.get("saved_profile") if label == "as_saved" else label
    if verifies in att.get("profiles", {}) and not problems:
        att["profiles"][verifies]["verified"] = rel(snap)
        m["updated"] = lib.now_iso()
    save(MANIFESTS / f"{m['id']}.json", m)
    for pr in problems:
        print(f"PROBLEM {pr}")
    return 1 if problems else 0


def cmd_check(a):
    m = load_manifest(a.id)
    results = [("manifest schema", not lib.schema_errors("manifest", m), "; ".join(lib.schema_errors("manifest", m)[:3]))]
    ui = UIWorkflow(m["template"])
    results.append(("saved workflow unchanged", ui.sha256 == m["ui_sha256"], ui.sha256[:12]))
    ids = ui.api_ids()
    att = m.get("attention")
    if att:
        bad = [f"{r}:{v['node']}" for r, v in att["nodes"].items() if ids.get(v["node"], {}).get("type") != v["class"]]
        results.append(("attention nodes present with their classes", not bad, ", ".join(bad) or "ok"))
        unverified = [p for p in ("sol", "chunked") if not att["profiles"].get(p, {}).get("verified")]
        results.append(("sol and chunked conversions verified", not unverified, ", ".join(unverified) or "ok"))
    snap_ok = bool(m.get("snapshot")) and (lib.REPO / m["snapshot"]).exists()
    results.append(("as-saved snapshot", snap_ok, m.get("snapshot", "none")))
    if snap_ok:
        snap = json.loads((lib.REPO / m["snapshot"]).read_text("utf-8"))["api_prompt"]
        missing = [f"{n}.{t['input']}" for n, s in m["per_job"].items() for t in s["targets"]
                   if snap.get(t["node"], {}).get("inputs", {}).get(t["input"]) != f"<per_job:{n}>"]
        results.append(("per-job inputs found in the snapshot", not missing, ", ".join(missing) or "ok"))
    prof_ok = bool(m.get("default_profile")) and (lib.REPO / m["default_profile"]).exists()
    results.append(("default profile", prof_ok, m.get("default_profile", "none")))
    ok = True
    for name, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'}  {name}: {detail}")
        ok &= passed
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("inspect").add_argument("template")
    i = sub.add_parser("init")
    i.add_argument("template")
    i.add_argument("--kind", choices=["h3", "krea", "other"], required=True)
    i.add_argument("--id")
    i.add_argument("--force", action="store_true")
    mo = sub.add_parser("modes")
    mo.add_argument("id")
    mo.add_argument("profile")
    g = sub.add_parser("ingest")
    g.add_argument("id")
    g.add_argument("page_output")
    sub.add_parser("check").add_argument("id")
    a = ap.parse_args(argv)
    return {"list": cmd_list, "inspect": cmd_inspect, "init": cmd_init, "modes": cmd_modes,
            "ingest": cmd_ingest, "check": cmd_check}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
