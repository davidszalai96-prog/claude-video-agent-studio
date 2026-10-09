import json
import shutil
import subprocess
import sys

import pytest

import new_project
import studio_lib as lib
from test_project_tools import write_json
from test_schemas import TICKET

sys.path.insert(0, str(lib.REPO / "pipeline" / "watchdog"))
import vram_watch as vw  # noqa: E402


def events(wd, name):
    return [e for e in wd.events if e["event"] == name]


def test_normal_job_is_never_halted():
    wd = vw.run_scenario("normal")
    assert wd.status == "watching" and wd.restarts == 0
    assert not events(wd, "halt_detected")
    assert events(wd, "peak")[0]["peak_gb"] == 24.0


def test_stall_after_progress_restarts_once():
    wd = vw.run_scenario("stall")
    halts = events(wd, "halt_detected")
    assert len(halts) == 1 and halts[0]["reason"] == "no_progress" and halts[0]["step"] == 9
    assert wd.restarts == 1 and wd.status == "watching"


def test_api_down_for_two_minutes_restarts():
    wd = vw.run_scenario("api_down")
    assert events(wd, "halt_detected")[0]["reason"] == "api_down"
    assert wd.restarts == 1 and wd.status == "watching"


def test_memory_not_released_stops_and_alerts():
    wd = vw.run_scenario("not_released")
    assert wd.status == "stopped_alert" and wd.restarts == 0
    assert "memory_not_released" in events(wd, "restart_failed")[0]["detail"]


def test_third_halt_ends_the_window_without_restart():
    wd = vw.run_scenario("three_halts")
    assert len(events(wd, "halt_detected")) == 3 and wd.restarts == 2
    assert wd.status == "stopped_alert"
    assert "restart limit" in events(wd, "restart_failed")[-1]["detail"]


def test_no_restart_after_the_window_ends():
    wd = vw.run_scenario("after_window")
    assert wd.restarts == 0 and wd.status == "stopped_alert"
    assert "window has ended" in events(wd, "restart_failed")[0]["detail"]


def test_dry_run_never_calls_the_restart_script():
    calls = []
    wd = vw.Watchdog(cfg=vw.CONFIG, window_end_t=1e12, dry_run=True, restart=lambda: calls.append(1) or {"status": "restarted"})
    for o, _ in zip(vw.scenario_obs("stall", 0.0)[0], range(1000)):
        wd.step(o)
    assert calls == [] and "would close" in events(wd, "restart")[0]["detail"]


def test_old_progress_lines_do_not_count_for_a_new_job():
    # The newest progress line is from a previous job (stamped before this job started): wait for the startup timeout.
    wd = vw.Watchdog(cfg=vw.CONFIG, window_end_t=1e12, restart=lambda: {"status": "restarted"})
    for i in range(0, 41):
        wd.step(vw.Obs(t=1000.0 + i * 15, api_ok=True, running="p9", progress_t=500.0, progress_step=28, progress_total=28))
    halts = events(wd, "halt_detected")
    assert len(halts) == 1 and halts[0]["reason"] == "no_first_step"
    assert halts[0]["t"] - 1000.0 >= vw.CONFIG["startup_timeout_s"]


def test_log_entries_match_the_vram_log_schema():
    wd = vw.run_scenario("three_halts")
    for e in wd.events:
        entry = vw.to_log_entry(e, {"project": "MAG", "run_id": "R-004", "output_id": "MAG_SQ010_U020_v001"})
        assert lib.schema_errors("vram_log_entry", entry) == [], entry


def test_bat_python_args(tmp_path):
    bat = tmp_path / "x.bat"
    bat.write_text('@echo off\ncall "C:\\CUVenv\\Scripts\\activate.bat"\ncd /d "C:\\CU"\npython main.py --cuda-device 0 --a\n', "utf-8")
    assert vw.bat_python_args(str(bat)) == ["main.py", "--cuda-device", "0", "--a"]


# --- approved windows (shared with the step 8 hooks) -----------------------------------

@pytest.fixture
def mag(tmp_path):
    return new_project.create("MAG", "Magic", "film", tmp_path / "projects")


def record_ticket_approval(project, ticket, window, decision="approved"):
    tpath = project / "00_admin" / "run_tickets" / f"{ticket['run_id']}.json"
    write_json(tpath, ticket)
    rec = {"kind": "run_ticket", "project": "MAG", "subject": f"00_admin/run_tickets/{ticket['run_id']}.json",
           "subject_sha256": lib.sha256_file(tpath), "decision": decision, "question": "Approve?", "answer": "Approve",
           "answered_at": "2026-10-10T18:05+02:00", "recorded_by": "hook:record-approval", "run_id": ticket["run_id"]}
    if decision == "approved":
        rec["window"] = window
    write_json(project / "00_admin" / "approvals" / f"{ticket['run_id']}.json", rec)
    return tpath


WINDOW = {"start": "2026-10-10T21:00+02:00", "end": "2026-10-11T00:00+02:00"}


def test_approved_window_holds_only_for_an_unchanged_approved_ticket(mag):
    assert lib.approved_window(mag, "R-004") == (None, "no recorded approval for R-004")
    tpath = record_ticket_approval(mag, TICKET, WINDOW)
    assert lib.approved_window(mag, "R-004") == (WINDOW, None)
    t = json.loads(tpath.read_text("utf-8"))
    t["est_total_min"] = 999
    write_json(tpath, t)
    window, why = lib.approved_window(mag, "R-004")
    assert window is None and "changed after the user approved it" in why


def test_rejected_ticket_has_no_window(mag):
    record_ticket_approval(mag, TICKET, WINDOW, decision="rejected")
    window, why = lib.approved_window(mag, "R-004")
    assert window is None and "not approved" in why


def test_window_state():
    from datetime import datetime
    tz = lib.parse_ts(WINDOW["start"]).tzinfo
    assert lib.window_state(WINDOW, datetime(2026, 10, 10, 20, 59, tzinfo=tz)) == "before"
    assert lib.window_state(WINDOW, datetime(2026, 10, 10, 21, 0, tzinfo=tz)) == "open"
    assert lib.window_state(WINDOW, datetime(2026, 10, 11, 0, 0, tzinfo=tz)) == "ended"


def test_real_watch_refuses_without_an_approval(mag, capsys):
    assert vw.main(["watch", "--project", str(mag), "--run-id", "R-004"]) == 2
    assert "refused" in capsys.readouterr().out
    assert vw.main(["watch"]) == 2


@pytest.mark.skipif(shutil.which("powershell.exe") is None, reason="Windows PowerShell not available")
def test_restart_script_dry_run_only_reports(tmp_path):
    p = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(vw.RESTART_PS1), "-DryRun"],
                       capture_output=True, text=True, timeout=60)
    res = json.loads(p.stdout.strip().splitlines()[-1])
    assert p.returncode == 0 and res["status"] == "dry_run"
    assert res["relaunch"].startswith("explorer.exe")
    if res["found"]:  # ComfyUI is running: the console is the ComfyUI.bat cmd.exe
        assert res["found"][-1]["name"] == "cmd.exe" and res["console_launcher_matches"] is True
