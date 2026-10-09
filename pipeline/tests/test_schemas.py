import copy

import pytest
from jsonschema import Draft202012Validator

import studio_lib as lib

ENVELOPE = {  # the design's example (Data model)
    "task_id": "T-0123",
    "agent": "prompt-writer",
    "objective": "Write the ref2va prompt for MAG_SQ010_U020 from shot list v002",
    "inputs": ["04_boards/shotlist.json#MAG_SQ010_U020", "03_art/prompt_blocks.json"],
    "outputs": ["05_prompts/MAG_SQ010_U020_v001.txt", "05_prompts/lint/MAG_SQ010_U020_v001.json"],
    "acceptance": ["lint passes", "11 shots in slot order", "60-65 words per second"],
    "budget": {"gpu_min": 0, "gemini_requests": 0, "max_turns": 30},
    "due": "before the next run request",
    "escalate_if": "a shot cannot fit the word budget",
}

TICKET = {  # the design's example, without approved_by (approval lives in its own record)
    "run_id": "R-004",
    "project": "MAG",
    "status": "proposed",
    "created": "2026-10-10T18:00+02:00",
    "window": {"start": "2026-10-10T21:00+02:00", "end": "2026-10-11T00:00+02:00"},
    "jobs": [
        {"output_id": "MAG_SQ010_U020_v001", "kind": "h3", "template": "H3regenrunsTest", "config": "default", "attention_profile": "sol", "est_min": 25},
        {"output_id": "MAG_SQ010_U030_v001", "kind": "h3", "template": "H3regenrunsTest", "config": "default", "attention_profile": "sol", "est_min": 25},
        {"output_id": "MAG_SQ020_U010_v002", "kind": "h3", "template": "H3ultRefsTest2", "config": "yours-2026-10-10", "attention_profile": "chunked", "est_min": 33, "retake_of": "v001"},
    ],
    "config_changes": {"H3ultRefsTest2": {"ref_image_size": "max -> match"}},
    "est_total_min": 83,
    "vram_check": "every configuration has a recorded peak below the free VRAM",
}

POLICY = {
    "project": "MAG",
    "approvals": {
        "h3": {"mode": "batch_window", "auto_retakes_per_unit": 1},
        "stills": {"mode": "none", "max_retakes": 3, "only_when_idle": True, "user_choice": "async_agent_fallback"},
        "other": {"mode": "batch_window"},
    },
    "workflow_templates": [
        {"role": "h3", "name": "H3regenrunsTest", "default_attention_profile": "sol"},
        {"role": "krea", "name": "H3regensElements"},
    ],
    "footage_folder": "C:\\CU\\output\\studio\\MAG",
}

JOB = {
    "output_id": "MAG_SQ010_U020_v001",
    "project": "MAG",
    "kind": "h3",
    "template": "H3regenrunsTest",
    "attention_profile": "sol",
    "params": {
        "prompt_file": "05_prompts/MAG_SQ010_U020_v001.txt",
        "seed": 831837948015784,
        "duration_s": 15,
        "megapixels": 0.98,
        "references": [{"picture": 1, "asset": "CHAR_nyxara_v002", "file": "studio/MAG/CHAR_nyxara_v002.png", "input": "ref_image_0"}],
        "output_prefix": "studio/MAG/units/MAG_SQ010_U020_v001/MAG_SQ010_U020_v001",
    },
    "created": "2026-10-10T18:00+02:00",
    "author": "prompt-writer",
}


def errors(name, data):
    return lib.schema_errors(name, data)


@pytest.mark.parametrize("name", sorted(lib.schemas()))
def test_schema_is_valid_draft_2020_12(name):
    Draft202012Validator.check_schema(lib.schemas()[name])


def test_all_schema_ids_are_unique_and_named_after_their_file():
    ids = [s["$id"] for s in lib.schemas().values()]
    assert len(ids) == len(set(ids))
    for name, s in lib.schemas().items():
        assert s["$id"].endswith(f"/{name}.schema.json")


def test_design_examples_validate():
    assert errors("task_envelope", ENVELOPE) == []
    assert errors("run_ticket", TICKET) == []
    assert errors("policy", POLICY) == []
    assert errors("job_spec", JOB) == []


def test_ticket_cannot_carry_its_own_approval():
    t = copy.deepcopy(TICKET)
    t["approved_by"] = "you"
    assert errors("run_ticket", t)
    t = copy.deepcopy(TICKET)
    t["status"] = "approved"
    assert errors("run_ticket", t)


@pytest.mark.parametrize("bad", ["MAG_SQ10_U020_v001", "MAG_SQ010_U020_v1", "mag_SQ010_U020_v001", "MAG_SQ010_U020"])
def test_bad_take_ids_are_rejected(bad):
    t = copy.deepcopy(TICKET)
    t["jobs"][0]["output_id"] = bad
    assert errors("run_ticket", t)


def test_still_ids():
    ok = ["CHAR_nyxara_v002_c01", "VFX_crystal_wing_v001_c12", "MAG_SQ010_U020_SH030_kf_v001", "MAG_SQ010_U020_SH030_kf_v001_c02"]
    bad = ["CHAR_nyxara_v002", "CHAR_Nyxara_v002_c01", "MAG_SQ010_U020_SH030_v001"]
    still = Draft202012Validator({"$ref": "#/$defs/still_id", "$defs": lib.schemas()["common"]["$defs"]})
    for s in ok:
        assert not list(still.iter_errors(s)), s
    for s in bad:
        assert list(still.iter_errors(s)), s


def test_krea_jobs_never_carry_an_attention_profile_and_h3_jobs_always_do():
    t = copy.deepcopy(TICKET)
    t["jobs"][0]["kind"] = "krea"
    assert errors("run_ticket", t)  # krea with attention_profile
    t = copy.deepcopy(TICKET)
    del t["jobs"][0]["attention_profile"]
    assert errors("run_ticket", t)  # h3 without
    j = copy.deepcopy(JOB)
    del j["attention_profile"]
    assert errors("job_spec", j)


@pytest.mark.parametrize("folder", ["D:\\CU\\output\\x", "C:\\Users\\david\\Videos\\x", "E:\\footage", "studio\\MAG"])
def test_policy_footage_folder_must_be_inside_comfy_output(folder):
    p = copy.deepcopy(POLICY)
    p["footage_folder"] = folder
    assert errors("policy", p)


def test_policy_h3_template_needs_attention_profile_and_krea_must_not_have_one():
    p = copy.deepcopy(POLICY)
    del p["workflow_templates"][0]["default_attention_profile"]
    assert errors("policy", p)
    p = copy.deepcopy(POLICY)
    p["workflow_templates"][1]["default_attention_profile"] = "sol"
    assert errors("policy", p)
    p = copy.deepcopy(POLICY)
    p["workflow_templates"] = []
    assert errors("policy", p)


def test_approval_records():
    base = {
        "kind": "run_ticket", "project": "MAG", "subject": "00_admin/run_tickets/R-004.json",
        "subject_sha256": "a" * 64, "decision": "approved", "question": "Approve R-004 for 21:00-00:00?",
        "answer": "Approve", "answered_at": "2026-10-10T18:05+02:00", "recorded_by": "hook:record-approval",
        "run_id": "R-004", "window": {"start": "2026-10-10T21:00+02:00", "end": "2026-10-11T00:00+02:00"},
    }
    assert errors("approval", base) == []
    for missing in ("window", "run_id"):
        b = copy.deepcopy(base)
        del b[missing]
        assert errors("approval", b), missing
    forged = copy.deepcopy(base)
    forged["recorded_by"] = "producer"
    assert errors("approval", forged)
    pol = {**{k: v for k, v in base.items() if k not in ("run_id", "window")}, "kind": "policy",
           "subject": "00_admin/policy_proposal.json"}
    assert errors("approval", pol)  # approved policy must embed the policy
    pol["policy"] = POLICY
    assert errors("approval", pol) == []


def test_project_paths_reject_absolute_and_parent_paths():
    e = copy.deepcopy(ENVELOPE)
    for bad in ["C:\\x.json", "/etc/x", "../other/x.json", "a\\b.json"]:
        e["outputs"] = [bad]
        assert errors("task_envelope", e), bad


def test_qc_rules():
    qc = {
        "take": "MAG_SQ010_U020_v001", "project": "MAG", "reviewed_at": "2026-10-11T09:00+02:00",
        "technical": {"duration_s": 15.083, "fps": 24, "frames": 362, "width": 1504, "height": 832},
        "cuts": {"detector": "AdaptiveDetector", "detected": [80, 133], "verified": [80, 133]},
        "blind_pass": {"path": "06_dailies/MAG_SQ010_U020_v001/blind.md", "written_before_prompt": True},
        "shots": [{"planned_shot": "MAG_SQ010_U020_SH010", "frames": {"in": 0, "out": 80}, "status": "done",
                   "scores": {"intent": 5, "character_fidelity": 4, "motion": 4, "composition": 4, "style": 5, "artifacts": 4},
                   "usable": True}],
        "verdict": "approved",
    }
    assert errors("qc_report", qc) == []
    q = copy.deepcopy(qc)
    q["verdict"] = "retake_requested"
    assert errors("qc_report", q)
    q["retake_request"] = {"cause": "sampling", "variable": "seed", "change": "new seed, same wording", "gpu_min_est": 25}
    assert errors("qc_report", q) == []
    q = copy.deepcopy(qc)
    q["blind_pass"]["written_before_prompt"] = False
    assert errors("qc_report", q)
    q = copy.deepcopy(qc)
    q["shots"][0]["scores"]["motion"] = 6
    assert errors("qc_report", q)
