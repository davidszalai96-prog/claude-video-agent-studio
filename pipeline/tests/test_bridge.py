import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import studio_lib as lib

sys.path.insert(0, str(lib.REPO / "pipeline" / "comfy"))
sys.path.insert(0, str(lib.REPO / "pipeline" / "comfy" / "bridge"))
import comfy_api  # noqa: E402
import manifest_tool  # noqa: E402
import receiver  # noqa: E402

MANIFEST = {"per_job": {"prompt": {"targets": [{"node": "138", "input": "value"}], "type": "text"},
                        "seed": {"targets": [{"node": "129", "input": "noise_seed"}], "type": "int"}}}
API = {"138": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": "a long prompt"}},
       "129": {"class_type": "RandomNoise", "inputs": {"noise_seed": 5}},
       "92": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "x", "video": ["130", 0]}}}


def test_strip_per_job_replaces_values_and_reports_missing_inputs():
    out, problems = manifest_tool.strip_per_job(API, MANIFEST)
    assert out["138"]["inputs"]["value"] == "<per_job:prompt>"
    assert out["129"]["inputs"]["noise_seed"] == "<per_job:seed>"
    assert API["138"]["inputs"]["value"] == "a long prompt"  # input untouched
    assert problems == []
    bad = {"per_job": {"x": {"targets": [{"node": "999", "input": "value"}], "type": "text"},
                       "y": {"targets": [{"node": "92", "input": "nope"}], "type": "text"}}}
    _, problems = manifest_tool.strip_per_job(API, bad)
    assert len(problems) == 2


def test_config_hash_ignores_key_order_and_per_job_values():
    a, _ = manifest_tool.strip_per_job(API, MANIFEST)
    other = json.loads(json.dumps(API))
    other["138"]["inputs"]["value"] = "a different prompt"
    other["129"]["inputs"]["noise_seed"] = 99
    b, _ = manifest_tool.strip_per_job(dict(reversed(list(other.items()))), MANIFEST)
    assert manifest_tool.config_hash(a) == manifest_tool.config_hash(b)
    other["92"]["inputs"]["filename_prefix"] = "changed config"
    c, _ = manifest_tool.strip_per_job(other, MANIFEST)
    assert manifest_tool.config_hash(a) != manifest_tool.config_hash(c)


def test_last_progress_reads_the_newest_bar():
    entries = [
        {"t": "2026-10-09T19:12:05", "m": "[INFO] Requested to load MiniMaxH3\n"},
        {"t": "2026-10-09T19:20:00", "m": "\r 43%|████▎     | 12/28 [10:40<14:13, 53.30s/it]"},
        {"t": "2026-10-09T19:21:00", "m": "\x1b[32m[INFO]\x1b[0m other line\n"},
    ]
    p = comfy_api.last_progress(entries)
    assert (p["step"], p["total"], p["t"]) == (12, 28, "2026-10-09T19:20:00")
    assert comfy_api.last_progress([{"t": "2026-10-09T19:21:00", "m": "nothing\n"}]) is None


def test_diff_env_lists_changes():
    old = {"comfyui_version": "0.37.0", "packages": {"a": "1"}, "custom_nodes": {"x": "abc"}}
    new = {"comfyui_version": "0.38.0", "packages": {"a": "2"}, "custom_nodes": {"x": "abc", "y": None}}
    d = comfy_api.diff_env(old, new)
    assert "comfyui_version: 0.37.0 -> 0.38.0" in d and "packages/a: 1 -> 2" in d and "custom_nodes/y: absent -> None" in d


@pytest.fixture
def server(tmp_path):
    state = {"count": 0, "max": 100}
    srv = receiver.ThreadingHTTPServer(("127.0.0.1", 0), receiver.make_handler(tmp_path, state))
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", tmp_path
    srv.shutdown()


def post(url, body: bytes, origin="http://127.0.0.1:8188"):
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "Origin": origin})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def test_receiver_accepts_only_the_comfy_page_and_safe_names(server):
    base, out = server
    assert post(f"{base}/put/ok.as_saved.json", b'{"a": 1}') == 200
    assert json.loads((out / "ok.as_saved.json").read_text("utf-8")) == {"a": 1}
    assert post(f"{base}/put/x.json", b'{"a": 1}', origin="https://evil.example") == 403
    assert post(f"{base}/put/x.json", b'{"a": 1}', origin="chrome-extension://abc") == 403
    assert post(f"{base}/put/..%5Cx.json", b'{"a": 1}') == 400
    assert post(f"{base}/put/x.txt", b'{"a": 1}') == 400
    assert post(f"{base}/put/x.json", b'[1, 2]') == 400
    assert post(f"{base}/put/x.json", b'not json') == 400
    assert sorted(p.name for p in out.iterdir()) == ["ok.as_saved.json"]


MANIFESTS = sorted((lib.REPO / "pipeline" / "comfy" / "manifests").glob("*.json"))


@pytest.mark.parametrize("path", MANIFESTS, ids=[p.stem for p in MANIFESTS])
def test_repo_manifests_are_valid(path):
    m = json.loads(path.read_text("utf-8"))
    assert lib.schema_errors("manifest", m) == []
    assert m["id"] == path.stem
    if m["kind"] == "h3":
        assert m["preview_node"] and "sol" in m["attention"]["profiles"]
        for prof in m["attention"]["profiles"].values():
            assert m["preview_node"] not in prof["modes"]  # the user's live preview is never toggled


@pytest.mark.skipif(not manifest_tool.WORKFLOWS.exists(), reason="ComfyUI workflows folder not on this machine")
@pytest.mark.parametrize("path", MANIFESTS, ids=[p.stem for p in MANIFESTS])
def test_repo_manifests_pass_their_checks(path, capsys):
    assert manifest_tool.main(["check", path.stem]) == 0, capsys.readouterr().out
