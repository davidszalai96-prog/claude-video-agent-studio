import copy
import json

import pytest

import new_project
import studio_lib as lib
from test_schemas import POLICY, TICKET
from validate import validate_project


@pytest.fixture
def projects(tmp_path):
    return tmp_path / "projects"


@pytest.fixture
def mag(projects):
    return new_project.create("MAG", "Magic", "film", projects)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), "utf-8")


def record_policy_approval(project, policy, decision="approved"):
    """Simulates what the record-approval hook writes after the user's answer."""
    proposal = project / "00_admin" / "policy_proposal.json"
    write_json(proposal, policy)
    record = {
        "kind": "policy", "project": policy["project"], "subject": "00_admin/policy_proposal.json",
        "subject_sha256": lib.sha256_file(proposal), "decision": decision,
        "question": "Approve the project policy?", "answer": "Approve",
        "answered_at": "2026-10-09T22:00+02:00", "recorded_by": "hook:record-approval",
    }
    if decision == "approved":
        record["policy"] = policy
    write_json(project / "00_admin" / "approvals" / "policy.json", record)


def test_create_gives_a_valid_project_without_placeholders(mag):
    errors, warnings = validate_project(mag)
    assert errors == [] and warnings == []
    for f in mag.rglob("*"):
        if f.is_file():
            assert "{{" not in f.read_text("utf-8")
    meta = lib.load_yaml(mag / "01_brief" / "project.yaml")
    assert meta["code"] == "MAG" and meta["title"] == "Magic" and meta["status"] == "draft" and meta["kind"] == "film"
    assert (mag / "00_admin" / "approvals").is_dir()
    assert not (mag / "00_admin" / "approvals" / "policy.json").exists()


def test_create_refuses_existing_and_bad_codes(mag, projects):
    with pytest.raises(SystemExit):
        new_project.create("MAG", "Again", "film", projects)
    for bad in ("MA", "MAGI", "mag", "M4G"):
        with pytest.raises(SystemExit):
            new_project.create(bad, "x", "film", projects)


def test_footage_needs_a_recorded_approval(mag, projects):
    with pytest.raises(SystemExit, match="No recorded policy approval"):
        new_project.footage("MAG", projects, dry_run=True)


def test_footage_dry_run_with_approval(mag, projects, capsys):
    record_policy_approval(mag, POLICY)
    target = new_project.footage("MAG", projects, dry_run=True)
    assert str(target) == POLICY["footage_folder"]
    out = capsys.readouterr().out
    assert "units" in out and "stills" in out
    assert validate_project(mag) == ([], [])


def test_footage_refuses_a_policy_changed_after_approval(mag, projects):
    record_policy_approval(mag, POLICY)
    changed = copy.deepcopy(POLICY)
    changed["footage_folder"] = "C:\\CU\\output\\elsewhere"
    write_json(mag / "00_admin" / "policy_proposal.json", changed)
    with pytest.raises(SystemExit, match="no longer holds"):
        new_project.footage("MAG", projects, dry_run=True)
    errors, warnings = validate_project(mag)
    assert any("no longer holds" in w for w in warnings)


def test_footage_refuses_a_rejected_policy(mag, projects):
    record_policy_approval(mag, POLICY, decision="rejected")
    with pytest.raises(SystemExit, match="not an approval"):
        new_project.footage("MAG", projects, dry_run=True)


@pytest.mark.parametrize("path,ok", [
    (r"C:\CU\output\studio\MAG", True),
    (r"c:/cu/output/studio/MAG", True),
    (r"C:\CU\output", False),
    (r"C:\CU\output\..\input\MAG", False),
    (r"D:\CU\output\MAG", False),
    (r"E:\footage\MAG", False),
    (r"studio\MAG", False),
])
def test_footage_folder_rules(path, ok):
    assert (lib.footage_folder_problem(path) is None) == ok


def test_validate_catches_ticket_problems(mag):
    record_policy_approval(mag, POLICY)
    t = copy.deepcopy(TICKET)
    write_json(mag / "00_admin" / "run_tickets" / "R-005.json", t)  # name != run_id
    t2 = copy.deepcopy(TICKET)
    t2["run_id"] = "R-006"
    t2["window"] = {"start": "2026-10-11T00:00+02:00", "end": "2026-10-10T21:00+02:00"}
    write_json(mag / "00_admin" / "run_tickets" / "R-006.json", t2)
    errors, _ = validate_project(mag)
    joined = "\n".join(errors)
    assert "does not match the file name" in joined
    assert "window ends before it starts" in joined
    assert "H3ultRefsTest2" in joined and "approved templates" in joined


def test_validate_catches_foreign_ids_and_bad_logs(mag):
    tracker = lib.load_json(mag / "00_admin" / "tracker.json")
    tracker["units"].append({"id": "XYZ_SQ010_U010", "status": "planned", "owner": "storyboard", "attempt": 1,
                             "created": "2026-10-09T22:00+02:00", "updated": "2026-10-09T22:00+02:00"})
    write_json(mag / "00_admin" / "tracker.json", tracker)
    (mag / "00_admin" / "render_log.jsonl").write_text('{"ts": "nope"}\nnot json\n', "utf-8")
    errors, _ = validate_project(mag)
    joined = "\n".join(errors)
    assert "belongs to project XYZ" in joined
    assert "render_log.jsonl:1" in joined and "render_log.jsonl:2" in joined


def test_cli_validate_exit_codes(mag, capsys):
    import validate
    assert validate.main([str(mag)]) == 0
    (mag / "00_admin" / "budget.json").write_text("{}", "utf-8")
    assert validate.main([str(mag), "--quiet"]) == 1
