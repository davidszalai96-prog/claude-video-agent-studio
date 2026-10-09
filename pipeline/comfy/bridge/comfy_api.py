"""Read-only ComfyUI client for the shell side of the bridge (monitoring, environment pin, update checks).

    .venv\\Scripts\\python.exe pipeline\\comfy\\bridge\\comfy_api.py status
    ... comfy_api.py queue | history <prompt_id> | outputs <prompt_id> | wait <prompt_id> [--timeout 600]
    ... comfy_api.py logs [--tail 20] [--progress]
    ... comfy_api.py pin [--write]      # environment pin: versions, argv, custom nodes (git HEAD)
    ... comfy_api.py checks             # read-only checks before the studio queues anything

There is deliberately no submit command: jobs are queued from the studio's ComfyUI tab (comfy-bridge skill),
after the guardrail hooks have checked the project's recorded approval.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = "http://127.0.0.1:8188"
REPO = Path(__file__).resolve().parents[3]
PIN = REPO / "pipeline" / "comfy" / "env_pin.json"
MANIFESTS = REPO / "pipeline" / "comfy" / "manifests"
CUSTOM_NODES = Path(r"C:\CU\custom_nodes")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
PROGRESS = re.compile(r"(\d+)%\|.*?\|\s*(\d+)/(\d+)\s*\[([^\]<]*)<?([^\],]*)")


class ComfyDown(RuntimeError):
    pass


def get(path: str, timeout: float = 10):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise ComfyDown(f"ComfyUI API at {BASE} does not answer: {e}") from e


def system_stats() -> dict:
    return get("/api/system_stats")


def queue_counts() -> tuple[int, int]:
    q = get("/api/queue")
    return len(q["queue_running"]), len(q["queue_pending"])


def log_entries() -> list[dict]:
    return get("/internal/logs/raw")["entries"]


def last_progress(entries: list[dict] | None = None) -> dict | None:
    """The newest sampler progress line: step, total, its timestamp and age in seconds.

    ComfyUI keeps only the latest state of a progress bar and re-stamps it on every update,
    so the age of this entry is the time since the last sampler step.
    """
    entries = entries if entries is not None else log_entries()
    for e in reversed(entries):
        m = PROGRESS.search(ANSI.sub("", e["m"]))
        if m:
            t = datetime.fromisoformat(e["t"])
            return {"step": int(m.group(2)), "total": int(m.group(3)), "elapsed": m.group(4).strip(),
                    "t": e["t"], "age_s": round((datetime.now() - t).total_seconds(), 1)}
    return None


def history(prompt_id: str) -> dict | None:
    return get(f"/api/history/{prompt_id}").get(prompt_id)


def environment() -> dict:
    s = system_stats()["system"]
    nodes = {}
    if CUSTOM_NODES.is_dir():
        for d in sorted(CUSTOM_NODES.iterdir()):
            if d.is_dir() and not d.name.startswith((".", "__")) and not d.name.endswith(".disabled"):
                head = None
                if (d / ".git").exists():
                    r = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True)
                    head = r.stdout.strip() or None
                nodes[d.name] = head
    return {
        "comfyui_version": s["comfyui_version"],
        "packages": {p["name"]: p["installed"] for p in s.get("comfy_package_versions", [])},
        "python": s["python_version"].split()[0],
        "pytorch": s["pytorch_version"],
        "argv": s["argv"],
        "custom_nodes": nodes,
    }


def diff_env(old: dict, new: dict) -> list[str]:
    out = []
    for k in ("comfyui_version", "python", "pytorch", "argv"):
        if old.get(k) != new.get(k):
            out.append(f"{k}: {old.get(k)} -> {new.get(k)}")
    for group in ("packages", "custom_nodes"):
        o, n = old.get(group, {}), new.get(group, {})
        for name in sorted(set(o) | set(n)):
            if name not in o or name not in n or o[name] != n[name]:
                out.append(f"{group}/{name}: {o.get(name, 'absent')} -> {n.get(name, 'absent')}")
    return out


def manifest_classes() -> set[str]:
    classes = set()
    for f in MANIFESTS.glob("*.json"):
        m = json.loads(f.read_text("utf-8"))
        classes.update(m.get("required_classes", []))
    return classes


def checks() -> list[tuple[str, bool, str]]:
    """Read-only checks the bridge runs before the studio queues anything (plan E2)."""
    results = []
    try:
        s = system_stats()["system"]
        results.append(("api answers", True, f"ComfyUI {s['comfyui_version']}"))
    except ComfyDown as e:
        return [("api answers", False, str(e))]
    if PIN.exists():
        changes = diff_env(json.loads(PIN.read_text("utf-8"))["environment"], environment())
        results.append(("environment matches pin", not changes, "; ".join(changes[:8]) or "unchanged"))
    else:
        results.append(("environment matches pin", False, "no pin recorded yet (comfy_api.py pin --write)"))
    try:
        entries = log_entries()
        results.append(("console log feed", bool(entries), f"{len(entries)} entries"))
    except ComfyDown as e:
        results.append(("console log feed", False, str(e)))
    missing = []
    for c in sorted(manifest_classes()):
        try:
            if c not in get(f"/api/object_info/{urllib.request.quote(c)}"):
                missing.append(c)
        except ComfyDown:
            missing.append(c)
    results.append(("manifest node classes installed", not missing, ", ".join(missing) or "all present"))
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("queue")
    for name in ("history", "outputs"):
        sub.add_parser(name).add_argument("prompt_id")
    w = sub.add_parser("wait", help="block until the prompt finishes (at most --timeout seconds)")
    w.add_argument("prompt_id")
    w.add_argument("--timeout", type=float, default=600)
    w.add_argument("--every", type=float, default=30)
    lg = sub.add_parser("logs")
    lg.add_argument("--tail", type=int, default=20)
    lg.add_argument("--progress", action="store_true", help="only the latest sampler progress")
    p = sub.add_parser("pin")
    p.add_argument("--write", action="store_true")
    sub.add_parser("checks")
    a = ap.parse_args(argv)

    try:
        if a.cmd == "status":
            s = system_stats()
            running, pending = queue_counts()
            print(f"ComfyUI {s['system']['comfyui_version']}  argv: {' '.join(s['system']['argv'])}")
            for d in s.get("devices", []):
                print(f"{d['name']}: {d['vram_free'] / 2**30:.1f} of {d['vram_total'] / 2**30:.1f} GB free")
            print(f"queue: {running} running, {pending} pending")
            print(f"last progress: {last_progress()}")
        elif a.cmd == "queue":
            print(json.dumps(get("/api/queue"), indent=1)[:4000])
        elif a.cmd == "history":
            print(json.dumps(history(a.prompt_id), indent=1))
        elif a.cmd == "outputs":
            h = history(a.prompt_id) or {}
            print(json.dumps(h.get("outputs", {}), indent=1))
        elif a.cmd == "wait":
            end = time.monotonic() + a.timeout
            while True:
                h = history(a.prompt_id)
                if h and h.get("status", {}).get("completed") is not None:
                    print(json.dumps({"status": h["status"].get("status_str"), "outputs": list(h.get("outputs", {}))}))
                    return 0 if h["status"].get("status_str") == "success" else 2
                if time.monotonic() >= end:
                    print(json.dumps({"status": "still running", "progress": last_progress()}))
                    return 3
                time.sleep(min(a.every, max(1, end - time.monotonic())))
        elif a.cmd == "logs":
            if a.progress:
                print(json.dumps(last_progress()))
            else:
                for e in log_entries()[-a.tail:]:
                    m = ANSI.sub("", e["m"]).rstrip()
                    if m:
                        print(e["t"][11:19], m.replace("\r", "")[:200])
        elif a.cmd == "pin":
            env = environment()
            if PIN.exists():
                changes = diff_env(json.loads(PIN.read_text("utf-8"))["environment"], env)
                print("\n".join(changes) or "environment unchanged since the pin")
            if a.write:
                PIN.write_text(json.dumps({"recorded": datetime.now().astimezone().isoformat(timespec="seconds"),
                                           "environment": env}, indent=2) + "\n", "utf-8", newline="\n")
                print(f"wrote {PIN.relative_to(REPO)}: ComfyUI {env['comfyui_version']}, {len(env['custom_nodes'])} custom node packs")
        elif a.cmd == "checks":
            ok = True
            for name, passed, detail in checks():
                print(f"{'PASS' if passed else 'FAIL'}  {name}: {detail}")
                ok &= passed
            return 0 if ok else 1
    except ComfyDown as e:
        print(e)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
