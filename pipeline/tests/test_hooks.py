"""Runs the real PowerShell hooks with synthetic hook input against a temporary repo copy of the projects."""
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta

import pytest

import new_project
import studio_lib as lib
from test_project_tools import record_policy_approval, write_json
from test_schemas import POLICY, TICKET

pytestmark = pytest.mark.skipif(shutil.which("powershell.exe") is None, reason="Windows PowerShell not available")
HOOKS = lib.REPO / ".claude" / "hooks"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "projects").mkdir(parents=True)
    return root


def run_hook(script, payload, repo, queue="empty"):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo), "STUDIO_GUARD_TEST_QUEUE": queue}
    p = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(HOOKS / script)],
                       input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
    return p.returncode, p.stdout, p.stderr


def guard(repo, tool, tool_input, agent=None, queue="empty"):
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input,
               "scratchpad_dir": str(repo.parent / "scratch")}
    if agent:
        payload["agent_type"] = agent
    return run_hook("guard.ps1", payload, repo, queue)


# --- file tools ------------------------------------------------------------------------------

def test_writes_inside_the_repo_and_scratch_are_allowed(repo):
    assert guard(repo, "Write", {"file_path": str(repo / "projects" / "x.md"), "content": "x"})[0] == 0
    assert guard(repo, "Write", {"file_path": str(repo.parent / "scratch" / "y.txt"), "content": "x"})[0] == 0
    mem = os.path.join(os.environ["USERPROFILE"], ".claude", "projects", "C--claude-video-agent-studio", "memory", "m.md")
    assert guard(repo, "Edit", {"file_path": mem, "old_string": "a", "new_string": "b"})[0] == 0


@pytest.mark.parametrize("path", [r"D:\x\y.txt", r"C:\Windows\Temp\x.txt", r"C:\CU\output\video\x.txt", r"C:\CU\user\default\workflows\x.json"])
def test_writes_outside_the_roots_are_blocked(repo, path):
    code, _, err = guard(repo, "Write", {"file_path": path, "content": "x"})
    assert code == 2 and "Blocked by studio guardrail" in err


def test_footage_folder_becomes_writable_only_after_approval(repo):
    mag = new_project.create("MAG", "Magic", "film", repo / "projects")
    target = r"C:\CU\output\studio\MAG\units\x.txt"
    assert guard(repo, "Write", {"file_path": target, "content": "x"})[0] == 2
    record_policy_approval(mag, POLICY)
    assert guard(repo, "Write", {"file_path": target, "content": "x"})[0] == 0
    p = json.loads((mag / "00_admin" / "policy_proposal.json").read_text("utf-8"))
    p["footage_folder"] = r"C:\CU\output\other"
    write_json(mag / "00_admin" / "policy_proposal.json", p)  # stale approval: no longer a root
    assert guard(repo, "Write", {"file_path": target, "content": "x"})[0] == 2


def test_approvals_and_secrets_are_never_written_by_tools(repo):
    assert guard(repo, "Write", {"file_path": str(repo / "projects" / "MAG" / "00_admin" / "approvals" / "R-001.json"), "content": "{}"})[0] == 2
    assert guard(repo, "Write", {"file_path": str(repo / ".env"), "content": "K=1"})[0] == 2


def test_studio_agents_cannot_edit_guardrails_but_the_build_session_can(repo):
    path = str(repo / ".claude" / "hooks" / "guard.ps1")
    assert guard(repo, "Edit", {"file_path": path, "old_string": "a", "new_string": "b"}, agent="pipeline-td")[0] == 2
    assert guard(repo, "Edit", {"file_path": str(repo / ".claude" / "settings.json"), "old_string": "a", "new_string": "b"}, agent="producer")[0] == 2
    assert guard(repo, "Edit", {"file_path": path, "old_string": "a", "new_string": "b"})[0] == 0


# --- shell commands --------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "ls D:\\", "dir D:/projects", "cat /d/notes.txt", "cd D:", "robocopy C:\\x D:\\y",
    "cat C:/CU/output/video/geminiapi.txt", "Get-Content C:\\CU\\output\\video\\geminiapi.txt",
    "python gemini_video.py a.mp4 --key-file C:/CU/output/video/geminiapi.txt | tee log.txt",
    "cat ~/.claude/skills/video-use/.env", "source .env",
    "echo {} > projects/MAG/00_admin/approvals/R-001.json",
    "python -c \"open('projects/MAG/00_admin/approvals/R-001.json','w').write('{}')\"",
    ".venv/Scripts/python.exe pipeline/tools/ticket.py approve MAG R-001",
    "powershell -File pipeline/watchdog/restart_comfyui.ps1",
    "taskkill /IM python.exe /F", "Stop-Process -Name python", "taskkill /PID 19488 /T /F # ComfyUI",
    "echo hi > C:\\Windows\\Temp\\x.txt", "Set-Content -Path C:\\Users\\david\\Desktop\\x.txt -Value 1",
    "cp projects/x.json C:/CU/user/default/workflows/x.json",
    "curl -X POST http://127.0.0.1:8188/interrupt",
    "curl -X POST http://127.0.0.1:8188/api/queue -d '{\"clear\": true}'",
])
def test_blocked_commands(repo, cmd):
    code, _, err = guard(repo, "Bash", {"command": cmd})
    assert code == 2, f"not blocked: {cmd}"
    assert "Blocked by studio guardrail" in err


@pytest.mark.parametrize("cmd", [
    "git status", "ls projects", "cd /d C:\\CU && dir",
    ".venv/Scripts/python.exe .claude/skills/gemini-video-review/scripts/gemini_video.py C:/CU/output/video/a.mp4 --key-file \"C:/CU/output/video/geminiapi.txt\" --out projects/MAG/06_dailies/x",
    "powershell -NoProfile -File pipeline/watchdog/restart_comfyui.ps1 -DryRun",
    "cat projects/MAG/00_admin/approvals/R-001.json",
    "echo hi > projects/notes.txt", "python x.py 2>/dev/null", "cp C:/CU/output/video/a.mp4 projects/MAG/x.mp4",
    "curl http://127.0.0.1:8188/api/queue", ".venv/Scripts/python.exe pipeline/comfy/bridge/comfy_api.py status",
    "curl -s https://example.com/d/file",
])
def test_allowed_commands(repo, cmd):
    code, _, err = guard(repo, "Bash", {"command": cmd})
    assert code == 0, f"blocked: {cmd}: {err}"


def test_studio_agent_cannot_change_guardrails_through_the_shell(repo):
    assert guard(repo, "Bash", {"command": "sed -i s/a/b/ .claude/hooks/guard.ps1"}, agent="librarian")[0] == 2
    assert guard(repo, "PowerShell", {"command": "Set-Content .claude/settings.json '{}'"}, agent="producer")[0] == 2


# --- ComfyUI submits ---------------------------------------------------------------------------

def approved_run(repo, start_offset_min=-10, end_offset_min=60, edit_after=False):
    mag = repo / "projects" / "MAG"
    if not mag.exists():
        new_project.create("MAG", "Magic", "film", repo / "projects")
    now = datetime.now().astimezone()
    t = json.loads(json.dumps(TICKET))
    t["window"] = {"start": (now + timedelta(minutes=start_offset_min)).isoformat(timespec="minutes"),
                   "end": (now + timedelta(minutes=end_offset_min)).isoformat(timespec="minutes")}
    tpath = mag / "00_admin" / "run_tickets" / "R-004.json"
    write_json(tpath, t)
    rec = {"kind": "run_ticket", "project": "MAG", "subject": "00_admin/run_tickets/R-004.json",
           "subject_sha256": lib.sha256_file(tpath), "decision": "approved", "question": "q", "answer": "Approve",
           "answered_at": now.isoformat(timespec="seconds"), "recorded_by": "hook:record-approval",
           "run_id": "R-004", "window": t["window"]}
    write_json(mag / "00_admin" / "approvals" / "R-004.json", rec)
    if edit_after:
        t["est_total_min"] = 1
        write_json(tpath, t)
    return mag


SUBMIT = "// studio-run: MAG R-004 MAG_SQ010_U020_v001\nawait app.api.queuePrompt(0, p)"


def js(repo, text, agent="render-wrangler", queue="empty"):
    return guard(repo, "mcp__claude-in-chrome__javascript_tool", {"action": "javascript_exec", "tabId": 1, "text": text}, agent, queue)


def test_submit_inside_an_approved_open_window_is_allowed(repo):
    approved_run(repo)
    code, _, err = js(repo, SUBMIT)
    assert code == 0, err


@pytest.mark.parametrize("case,expect", [
    ("no_marker", "must carry its marker"),
    ("no_approval", "no recorded approval"),
    ("window_not_open", "is not open"),
    ("ticket_edited", "changed after the user approved"),
    ("not_in_ticket", "is not a job of"),
    ("queue_busy", "queue is not empty"),
    ("wrong_agent", "only the Render Wrangler"),
])
def test_submit_refusals(repo, case, expect):
    text, agent, queue = SUBMIT, "render-wrangler", "empty"
    if case == "no_marker":
        approved_run(repo)
        text = "await app.api.queuePrompt(0, p)"
    elif case == "no_approval":
        new_project.create("MAG", "Magic", "film", repo / "projects")
    elif case == "window_not_open":
        approved_run(repo, start_offset_min=30, end_offset_min=90)
    elif case == "ticket_edited":
        approved_run(repo, edit_after=True)
    elif case == "not_in_ticket":
        approved_run(repo)
        text = SUBMIT.replace("MAG_SQ010_U020_v001", "MAG_SQ099_U010_v001")
    elif case == "queue_busy":
        approved_run(repo)
        queue = "busy"
    elif case == "wrong_agent":
        approved_run(repo)
        agent = "prompt-writer"
    code, _, err = js(repo, text, agent=agent, queue=queue)
    assert code == 2 and expect in err, err


def test_shell_submit_needs_the_same_approval(repo):
    cmd = "curl -X POST http://127.0.0.1:8188/api/prompt -d @job.json"
    assert guard(repo, "Bash", {"command": cmd})[0] == 2
    approved_run(repo)
    assert guard(repo, "Bash", {"command": cmd + "  # studio-run: MAG R-004 MAG_SQ010_U020_v001"})[0] == 0


def test_stills_follow_the_project_policy(repo):
    mag = new_project.create("MAG", "Magic", "film", repo / "projects")
    text = "// studio-still: MAG CHAR_nyxara_v002_c01\nawait app.api.queuePrompt(0, p)"
    assert js(repo, text)[0] == 2  # no approved policy yet
    record_policy_approval(mag, POLICY)  # stills mode none, Krea template H3regensElements
    assert js(repo, text)[0] == 2  # no job spec yet
    spec = {"output_id": "CHAR_nyxara_v002_c01", "project": "MAG", "kind": "krea", "template": "H3regensElements",
            "params": {"prompt_file": "05_prompts/CHAR_nyxara_v002_c01.txt", "seed": 1,
                       "output_prefix": "studio/MAG/stills/CHAR_nyxara_v002_c01"},
            "created": "2026-10-10T10:00+02:00", "author": "asset-designer"}
    write_json(mag / "00_admin" / ".." / "05_prompts" / "jobs" / "CHAR_nyxara_v002_c01.json", spec)
    assert js(repo, text)[0] == 0
    assert js(repo, text, queue="busy")[0] == 2  # only when idle
    spec["template"] = "H3regenrunsTest"
    write_json(mag / "05_prompts" / "jobs" / "CHAR_nyxara_v002_c01.json", spec)
    assert js(repo, text)[0] == 2  # not a Krea template


# --- record-approval -----------------------------------------------------------------------------

def ask_payload(question, answer, shape="input"):
    q = {"question": question, "header": "Approval", "multiSelect": False,
         "options": [{"label": "Approve as proposed", "description": "x"}, {"label": "Reject", "description": "y"}]}
    payload = {"hook_event_name": "PostToolUse", "tool_name": "AskUserQuestion", "tool_input": {"questions": [q]}}
    if shape == "input":
        payload["tool_input"]["answers"] = {question: answer}
        payload["tool_response"] = "User has answered your questions"
    else:
        payload["tool_response"] = {"questions": [q], "answers": {question: answer}}
    return payload


@pytest.mark.parametrize("shape", ["input", "response"])
def test_record_approval_writes_a_valid_bound_record(repo, shape):
    mag = approved_run(repo)
    (mag / "00_admin" / "approvals" / "R-004.json").unlink()
    sha = lib.sha256_file(mag / "00_admin" / "run_tickets" / "R-004.json")
    q = f"Approve R-004 for tonight? [studio-approve MAG R-004 sha256={sha}]"
    code, out, err = run_hook("record-approval.ps1", ask_payload(q, "Approve as proposed", shape), repo)
    assert code == 0, err
    rec = lib.load_json(mag / "00_admin" / "approvals" / "R-004.json")
    assert lib.schema_errors("approval", rec) == []
    assert rec["decision"] == "approved" and rec["subject_sha256"] == sha and rec["recorded_by"] == "hook:record-approval"
    assert lib.approved_window(mag, "R-004")[0] == rec["window"]
    assert "Recorded" in out


def test_record_approval_policy_rejection_and_stale_and_free_text(repo):
    mag = new_project.create("MAG", "Magic", "film", repo / "projects")
    write_json(mag / "00_admin" / "policy_proposal.json", POLICY)
    sha = lib.sha256_file(mag / "00_admin" / "policy_proposal.json")
    q = f"Approve the MAG policy? [studio-approve MAG policy sha256={sha}]"
    run_hook("record-approval.ps1", ask_payload(q, "Approve"), repo)
    rec = lib.load_json(mag / "00_admin" / "approvals" / "policy.json")
    assert rec["decision"] == "approved" and rec["policy"]["footage_folder"] == POLICY["footage_folder"]
    assert lib.schema_errors("approval", rec) == []
    run_hook("record-approval.ps1", ask_payload(q, "Reject"), repo)
    assert lib.load_json(mag / "00_admin" / "approvals" / "policy.json")["decision"] == "rejected"
    assert len(list((mag / "00_admin" / "approvals" / "history").glob("policy.*.json"))) == 1
    _, out, _ = run_hook("record-approval.ps1", ask_payload(q, "Change the footage folder to X"), repo)
    assert "neither an approval nor a rejection" in out
    stale = q.replace(sha, "0" * 64)
    _, out, _ = run_hook("record-approval.ps1", ask_payload(stale, "Approve"), repo)
    assert "changed since the question was written" in out
    assert lib.load_json(mag / "00_admin" / "approvals" / "policy.json")["decision"] == "rejected"


def test_questions_without_a_marker_record_nothing(repo):
    new_project.create("MAG", "Magic", "film", repo / "projects")
    code, out, _ = run_hook("record-approval.ps1", ask_payload("Which color?", "Approve"), repo)
    assert code == 0 and out.strip() == ""
    assert not list((repo / "projects" / "MAG" / "00_admin" / "approvals").glob("*.json"))


# --- regressions: words glued to dots or dashes are not commands -----------------------------------

@pytest.mark.parametrize("cmd", [
    "cat >> notes.txt <<'E'\nsee CLAUDE.md and C:/x.drp\nE",
    "grep -n copy README.md C:/CU/output/video/list.txt",
    "python tool.py --copy C:/CU/output/video/a.mp4",
])
def test_md_and_py_extensions_are_not_write_verbs(repo, cmd):
    code, _, err = guard(repo, "Bash", {"command": cmd})
    assert code == 0, err


def test_executable_paths_still_count_as_writers(repo):
    cmd = ".venv/Scripts/python.exe -c \"open('projects/MAG/00_admin/approvals/R-001.json','w')\""
    assert guard(repo, "Bash", {"command": cmd})[0] == 2


# --- DaVinci Resolve (CLAUDE.md rule 7) ----------------------------------------------------------

def resolve(repo, tool, action, params=None, session="s1", agent="finishing"):
    payload = {"hook_event_name": "PreToolUse", "tool_name": f"mcp__davinci-resolve__{tool}", "session_id": session,
               "tool_input": {"action": action, "params": params}, "agent_type": agent}
    return run_hook("guard.ps1", payload, repo)


def test_resolve_read_only_and_control_calls_are_allowed(repo):
    assert resolve(repo, "resolve_control", "get_version")[0] == 0
    assert resolve(repo, "project_manager", "list")[0] == 0
    assert resolve(repo, "project_manager", "get_current")[0] == 0
    assert resolve(repo, "project_manager_database", "get_current")[0] == 0
    assert resolve(repo, "project_manager_folders", "list")[0] == 0


@pytest.mark.parametrize("tool,action,params,expect", [
    ("project_manager", "load", {"name": "Highscore"}, "never an existing project"),
    ("project_manager", "create", {"name": "My Film"}, "STUDIO_"),
    ("project_manager", "delete", {"name": "STUDIO_TEST"}, "never deletes"),
    ("project_manager", "export_project", {"name": "Highscore", "path": "C:/x.drp"}, "only its own STUDIO_"),
    ("project_manager_database", "set_current", {"db_info": {"DbType": "Disk", "DbName": "x"}}, "databases"),
    ("project_manager_cloud", "load", {}, "cloud"),
    ("project_manager_folders", "delete", {"name": "x"}, "folders"),
    ("timeline", "list", None, "first create or load a STUDIO_ project"),
    ("render", "start", None, "first create or load a STUDIO_ project"),
])
def test_resolve_refusals(repo, tool, action, params, expect):
    code, _, err = resolve(repo, tool, action, params)
    assert code == 2 and expect in err, err


def test_resolve_edits_need_a_studio_project_from_this_session(repo):
    assert resolve(repo, "timeline", "list")[0] == 2
    assert resolve(repo, "project_manager", "create", {"name": "STUDIO_TEST_20261010"})[0] == 0
    assert resolve(repo, "timeline", "list")[0] == 0
    assert resolve(repo, "render", "add_job")[0] == 0
    assert resolve(repo, "timeline", "list", session="other-session")[0] == 2  # a new session starts closed
    assert resolve(repo, "project_manager", "load", '{"name": "STUDIO_MAG"}', session="s2")[0] == 0  # params as a JSON string
    assert resolve(repo, "timeline", "list", session="s2")[0] == 0


def test_resolve_export_paths_stay_inside_the_roots(repo):
    ok = resolve(repo, "project_manager", "export_project", {"name": "STUDIO_MAG", "path": str(repo / "projects" / "x.drp")})
    assert ok[0] == 0
    bad = resolve(repo, "project_manager", "export_project", {"name": "STUDIO_MAG", "path": r"C:\Users\david\Desktop\x.drp"})
    assert bad[0] == 2
