"""Create a studio project from templates/project, and create its footage folder once the user has approved it.

    .venv\\Scripts\\python.exe pipeline\\tools\\new_project.py create MAG --title "Magic" [--kind film]
    .venv\\Scripts\\python.exe pipeline\\tools\\new_project.py footage MAG [--dry-run]

`create` copies the template and fills in the code, title, kind and creation time. It never writes approvals.
`footage` reads 00_admin/approvals/policy.json (written by the record-approval hook from the user's answer),
checks that the approval still matches 00_admin/policy_proposal.json, and creates <footage>/units and
<footage>/stills inside C:\\CU\\output.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import studio_lib as lib
from validate import validate_project

TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".yaml", ".yml", ".txt"}
KINDS = ("film", "rerun_batch", "test")


def create(code: str, title: str, kind: str, projects_dir: Path) -> Path:
    if not lib.CODE_RE.match(code):
        raise SystemExit(f"Project code must be 3 uppercase letters, got {code!r}.")
    dest = projects_dir / code
    if dest.exists():
        raise SystemExit(f"{dest} already exists; nothing was changed.")
    values = {"{{CODE}}": code, "{{TITLE}}": title.replace('"', "'"), "{{KIND}}": kind, "{{CREATED}}": lib.now_iso()}
    shutil.copytree(lib.TEMPLATE, dest)
    for f in dest.rglob("*"):
        if f.is_file() and f.suffix in TEXT_SUFFIXES:
            text = f.read_text("utf-8")
            for k, v in values.items():
                text = text.replace(k, v)
            f.write_text(text, "utf-8", newline="\n")
    errors, _ = validate_project(dest)
    if errors:
        shutil.rmtree(dest)
        raise SystemExit("Template produced an invalid project (removed):\n  " + "\n  ".join(errors))
    return dest


def approved_footage_folder(project: Path) -> str:
    """The footage folder from the user's recorded approval, or exit with the reason."""
    record_path = project / "00_admin" / "approvals" / "policy.json"
    if not record_path.exists():
        raise SystemExit("No recorded policy approval yet (00_admin/approvals/policy.json). Ask the user to approve the policy first.")
    record = lib.load_json(record_path)
    errs = lib.schema_errors("approval", record)
    if errs:
        raise SystemExit("Policy approval record is invalid:\n  " + "\n  ".join(errs))
    if record["kind"] != "policy" or record["decision"] != "approved":
        raise SystemExit("The recorded policy decision is not an approval.")
    proposal = project / record["subject"]
    if not proposal.exists() or lib.sha256_file(proposal) != record["subject_sha256"]:
        raise SystemExit("policy_proposal.json changed after the user approved it; the approval no longer holds. Ask again.")
    return record["policy"]["footage_folder"]


def footage(code: str, projects_dir: Path, dry_run: bool, output_root: str = lib.COMFY_OUTPUT) -> Path:
    project = projects_dir / code
    if not project.is_dir():
        raise SystemExit(f"No project {code} in {projects_dir}.")
    folder = approved_footage_folder(project)
    problem = lib.footage_folder_problem(folder, output_root)
    if problem:
        raise SystemExit(f"Footage folder {folder} is not allowed: {problem}.")
    target = Path(folder)
    for sub in ("units", "stills"):
        if dry_run:
            print(f"would create {target / sub}")
        else:
            (target / sub).mkdir(parents=True, exist_ok=True)
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projects-dir", type=Path, default=lib.PROJECTS, help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create", help="create projects/<CODE> from the template")
    c.add_argument("code")
    c.add_argument("--title", required=True)
    c.add_argument("--kind", choices=KINDS, default="film")
    f = sub.add_parser("footage", help="create the approved footage folder")
    f.add_argument("code")
    f.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "create":
        print(create(a.code, a.title, a.kind, a.projects_dir))
    else:
        print(footage(a.code, a.projects_dir, a.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
