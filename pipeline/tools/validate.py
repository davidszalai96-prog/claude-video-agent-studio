"""Validate a studio project against pipeline/schemas plus the cross-file rules the schemas can't express.

    .venv\\Scripts\\python.exe pipeline\\tools\\validate.py projects\\MAG [projects\\XYZ ...]

Exit code 0 when there are no errors (warnings are printed but don't fail).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import studio_lib as lib


def _check(name: str, data, where: str, errors: list[str]) -> bool:
    errs = lib.schema_errors(name, data)
    errors.extend(f"{where}: {e}" for e in errs)
    return not errs


def _load(path: Path, where: str, errors: list[str]):
    try:
        return lib.load_yaml(path) if path.suffix in (".yaml", ".yml") else lib.load_json(path)
    except (ValueError, OSError) as e:
        errors.append(f"{where}: cannot read: {e}")
    except Exception as e:  # YAML errors
        errors.append(f"{where}: cannot parse: {e}")
    return None


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk_strings(v)


def validate_project(project: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    code = project.name

    def rel(p: Path) -> str:
        return p.relative_to(project).as_posix()

    if not lib.CODE_RE.match(code):
        errors.append(f"{project}: folder name must be the 3-letter project code")

    # Leftover template placeholders anywhere.
    for f in project.rglob("*"):
        if f.is_file() and f.suffix in (".json", ".jsonl", ".md", ".yaml", ".yml") and "{{" in f.read_text("utf-8", errors="replace"):
            errors.append(f"{rel(f)}: unfilled template placeholder")

    # Single files: (path, schema, required)
    singles = [
        ("01_brief/project.yaml", "project", True),
        ("00_admin/tracker.json", "tracker", True),
        ("00_admin/budget.json", "budget", True),
        ("00_admin/policy_proposal.json", "policy", False),
        ("06_dailies/selects.json", "selects", False),
    ]
    loaded = {}
    for path, schema, required in singles:
        f = project / path
        if not f.exists():
            if required:
                errors.append(f"{path}: missing")
            continue
        data = _load(f, path, errors)
        if data is not None and _check(schema, data, path, errors):
            loaded[path] = data
            pc = data.get("code", data.get("project"))
            if pc != code:
                errors.append(f"{path}: project code {pc!r} does not match folder {code!r}")

    # Per-ID files whose name must equal their ID field.
    groups = [
        ("00_admin/run_tickets", "R-*.json", "run_ticket", "run_id"),
        ("00_admin/tasks", "T-*.json", "task_envelope", "task_id"),
        ("05_prompts/jobs", "*.json", "job_spec", "output_id"),
        ("07_edit", "edl_v*.json", "edl", "version"),
    ]
    tickets = {}
    for folder, pattern, schema, id_field in groups:
        for f in sorted((project / folder).glob(pattern)):
            data = _load(f, rel(f), errors)
            if data is None or not _check(schema, data, rel(f), errors):
                continue
            if data.get(id_field) != f.stem:
                errors.append(f"{rel(f)}: {id_field} {data.get(id_field)!r} does not match the file name")
            if schema == "run_ticket":
                tickets[f.stem] = (f, data)

    for d in sorted((project / "06_dailies").glob("*/qc.json")):
        data = _load(d, rel(d), errors)
        if data is not None and _check("qc_report", data, rel(d), errors) and data["take"] != d.parent.name:
            errors.append(f"{rel(d)}: take {data['take']!r} does not match its folder")

    # Approvals: written only by the hook; check binding to the approved file.
    approved_policy = None
    for f in sorted((project / "00_admin" / "approvals").glob("*.json")):
        data = _load(f, rel(f), errors)
        if data is None or not _check("approval", data, rel(f), errors):
            continue
        subject = project / data["subject"]
        if not subject.exists():
            warnings.append(f"{rel(f)}: approved file {data['subject']} no longer exists")
        elif lib.sha256_file(subject) != data["subject_sha256"]:
            warnings.append(f"{rel(f)}: {data['subject']} changed after approval; the approval no longer holds")
        if data["kind"] == "policy" and f.name != "policy.json":
            errors.append(f"{rel(f)}: a policy approval must be named policy.json")
        if data["kind"] == "run_ticket" and data.get("run_id") and data["run_id"] != f.stem:
            errors.append(f"{rel(f)}: run_id does not match the file name")
        if data["kind"] == "policy" and data["decision"] == "approved":
            approved_policy = data["policy"]
            problem = lib.footage_folder_problem(approved_policy["footage_folder"])
            if problem:
                errors.append(f"{rel(f)}: footage folder not allowed: {problem}")

    # Ticket rules the schema can't express.
    for run_id, (f, t) in tickets.items():
        try:
            if lib.parse_ts(t["window"]["end"]) <= lib.parse_ts(t["window"]["start"]):
                errors.append(f"{rel(f)}: window ends before it starts")
        except ValueError as e:
            errors.append(f"{rel(f)}: bad window timestamp: {e}")
        total = sum(j["est_min"] for j in t["jobs"])
        if abs(total - t["est_total_min"]) > 0.5:
            warnings.append(f"{rel(f)}: est_total_min {t['est_total_min']} != sum of jobs {total:g}")
        if approved_policy:
            names = {w["name"] for w in approved_policy["workflow_templates"]}
            for j in t["jobs"]:
                if j["template"] not in names:
                    errors.append(f"{rel(f)}: job {j['output_id']} uses template {j['template']!r}, not one of the project's approved templates")
            if approved_policy["approvals"]["h3"]["mode"] == "per_job" and sum(j["kind"] == "h3" for j in t["jobs"]) > 1:
                errors.append(f"{rel(f)}: policy is per_job, but the ticket holds more than one H3 job")

    # Append-only logs.
    for name, schema in (("render_log.jsonl", "render_log_entry"), ("vram_log.jsonl", "vram_log_entry")):
        f = project / "00_admin" / name
        if not f.exists():
            errors.append(f"00_admin/{name}: missing")
            continue
        for n, line in enumerate(f.read_text("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                _check(schema, json.loads(line), f"00_admin/{name}:{n}", errors)
            except json.JSONDecodeError as e:
                errors.append(f"00_admin/{name}:{n}: not JSON: {e}")

    # Every sequence-based ID must belong to this project.
    for path, data in loaded.items():
        for s in _walk_strings(data):
            m = lib.SEQ_PREFIX_RE.match(s)
            if m and m.group(1) != code:
                errors.append(f"{path}: ID {s!r} belongs to project {m.group(1)}, not {code}")

    return errors, warnings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("projects", nargs="+", type=Path)
    ap.add_argument("--quiet", action="store_true", help="print only errors")
    a = ap.parse_args(argv)
    failed = False
    for p in a.projects:
        if not p.is_dir():
            print(f"{p}: not a folder")
            failed = True
            continue
        errors, warnings = validate_project(p)
        for e in errors:
            print(f"ERROR   {p.name}/{e}")
        if not a.quiet:
            for w in warnings:
                print(f"warning {p.name}/{w}")
            print(f"{p.name}: {len(errors)} error(s), {len(warnings)} warning(s)")
        failed |= bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
