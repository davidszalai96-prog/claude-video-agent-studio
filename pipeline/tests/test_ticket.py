import re

import pytest

import new_project
import studio_lib as lib
import ticket
from test_project_tools import write_json
from test_schemas import POLICY, TICKET


@pytest.fixture
def mag(tmp_path):
    p = new_project.create("MAG", "Magic", "film", tmp_path / "projects")
    write_json(p / "00_admin" / "run_tickets" / "R-004.json", TICKET)
    write_json(p / "00_admin" / "policy_proposal.json", POLICY)
    return p


def test_marker_binds_the_current_file_hash(mag):
    m = ticket.marker(mag, "R-004")
    sha = lib.sha256_file(mag / "00_admin" / "run_tickets" / "R-004.json")
    assert m == f"[studio-approve MAG R-004 sha256={sha}]"
    # The exact pattern record-approval.ps1 looks for.
    assert re.search(r"\[studio-approve\s+([A-Z]{3})\s+(policy|R-\d{3,})\s+sha256=([0-9a-f]{64})\]", m)
    assert ticket.marker(mag, "policy").startswith("[studio-approve MAG policy sha256=")


def test_summary_states_what_the_user_approves(mag):
    s = ticket.summary(mag, "R-004")
    assert "3 jobs" in s and "83 GPU-min" in s and "2026-10-10T21:00+02:00" in s and "H3ultRefsTest2 [chunked]" in s
    p = ticket.summary(mag, "policy")
    assert r"C:\CU\output\studio\MAG" in p and "H3regensElements (krea)" in p


def test_invalid_subject_cannot_be_asked(mag):
    write_json(mag / "00_admin" / "run_tickets" / "R-005.json", {"run_id": "R-005"})
    with pytest.raises(SystemExit, match="not valid"):
        ticket.marker(mag, "R-005")


def test_status_and_terminal_approve_refuses_without_a_terminal(mag, capsys, monkeypatch):
    assert "R-004: no recorded approval" in ticket.status(mag, None)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert ticket.approve(mag, "R-004") == 2
    assert "interactive terminal" in capsys.readouterr().out
    assert not (mag / "00_admin" / "approvals" / "R-004.json").exists()
