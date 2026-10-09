"""Run tickets and the project policy: the approval marker, a summary for the question, status, and the
user's terminal fallback.

    .venv\\Scripts\\python.exe pipeline\\tools\\ticket.py marker  <CODE> <R-###|policy>   # put this in the question
    ... ticket.py summary <CODE> <R-###|policy>                                          # what the question shows
    ... ticket.py status  <CODE> [R-###]                                                  # recorded approvals, windows
    ... ticket.py approve <CODE> <R-###|policy>      # ONLY in the user's own terminal (asks for typed confirmation)

The Producer asks with AskUserQuestion; the question text must contain the marker and the options must start
with "Approve" or "Reject". The record-approval hook then writes 00_admin/approvals/<R-###|policy>.json.
`approve` is the fallback when that route is unavailable: it refuses to run without an interactive terminal,
and the guard hook blocks agents from calling it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import studio_lib as lib


def subject_path(project: Path, what: str) -> Path:
    if what == "policy":
        return project / "00_admin" / "policy_proposal.json"
    if not what.startswith("R-"):
        raise SystemExit("expected R-### or policy")
    return project / "00_admin" / "run_tickets" / f"{what}.json"


def load_subject(project: Path, what: str) -> tuple[Path, dict]:
    p = subject_path(project, what)
    if not p.exists():
        raise SystemExit(f"{p.relative_to(project).as_posix()} does not exist")
    data = lib.load_json(p)
    errs = lib.schema_errors("policy" if what == "policy" else "run_ticket", data)
    if errs:
        raise SystemExit("not valid, fix it before asking:\n  " + "\n  ".join(errs))
    return p, data


def marker(project: Path, what: str) -> str:
    p, _ = load_subject(project, what)
    return f"[studio-approve {project.name} {what} sha256={lib.sha256_file(p)}]"


def summary(project: Path, what: str) -> str:
    _, d = load_subject(project, what)
    if what == "policy":
        a = d["approvals"]
        lines = [
            f"H3: {a['h3']['mode']}, automatic retakes per unit: {a['h3']['auto_retakes_per_unit']}",
            f"Krea stills: {a['stills']['mode']}, up to {a['stills']['max_retakes']} retakes, "
            f"only when idle: {a['stills']['only_when_idle']}, choice: {a['stills']['user_choice']}",
            f"Other workflows: {a['other']['mode']}",
            "Templates: " + ", ".join(f"{t['name']} ({t['role']}" + (f", {t['default_attention_profile']})" if t.get('default_attention_profile') else ")")
                                      for t in d["workflow_templates"]),
            f"Footage folder: {d['footage_folder']}",
        ]
    else:
        jobs = d["jobs"]
        kinds = {}
        for j in jobs:
            kinds[j["kind"]] = kinds.get(j["kind"], 0) + 1
        lines = [
            f"{what}: {len(jobs)} jobs (" + ", ".join(f"{n} {k}" for k, n in kinds.items()) + f"), about {d['est_total_min']:g} GPU-min",
            f"Window: {d['window']['start']} to {d['window']['end']}",
            "Templates: " + ", ".join(sorted({f"{j['template']}" + (f" [{j['attention_profile']}]" if j.get('attention_profile') else "") for j in jobs})),
            f"VRAM: {d['vram_check']}",
        ]
        if d.get("config_changes"):
            lines.append("Config changes: " + json.dumps(d["config_changes"]))
        if d.get("gpu_cap_min"):
            lines.append(f"Retake cap inside this ticket: {d['gpu_cap_min']:g} GPU-min")
    return "\n".join(lines)


def status(project: Path, run_id: str | None) -> str:
    out = []
    pol = project / "00_admin" / "approvals" / "policy.json"
    if pol.exists():
        rec = lib.load_json(pol)
        stale = (project / rec["subject"]).exists() and lib.sha256_file(project / rec["subject"]) != rec["subject_sha256"]
        out.append(f"policy: {rec['decision']} ({rec['answered_at']}){' - STALE, proposal changed since' if stale else ''}")
    else:
        out.append("policy: not recorded")
    ids = [run_id] if run_id else sorted(p.stem for p in (project / "00_admin" / "run_tickets").glob("R-*.json"))
    for rid in ids:
        window, why = lib.approved_window(project, rid)
        out.append(f"{rid}: {why}" if window is None else f"{rid}: approved, window {window['start']} - {window['end']} ({lib.window_state(window)})")
    return "\n".join(out)


def approve(project: Path, what: str) -> int:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("refused: run this yourself in an interactive terminal; it is the user's approval, not an agent's.")
        return 2
    p, data = load_subject(project, what)
    sha = lib.sha256_file(p)
    print(summary(project, what))
    typed = input(f"\nType APPROVE to approve {project.name} {what}, or REJECT: ").strip().upper()
    if typed not in ("APPROVE", "REJECT"):
        print("nothing recorded")
        return 1
    rec = {"kind": "policy" if what == "policy" else "run_ticket", "project": project.name,
           "subject": p.relative_to(project).as_posix(), "subject_sha256": sha,
           "decision": "approved" if typed == "APPROVE" else "rejected",
           "question": f"terminal: approve {project.name} {what}?", "answer": typed,
           "answered_at": lib.now_iso(), "recorded_by": "user:terminal"}
    if what != "policy":
        rec["run_id"] = what
        if typed == "APPROVE":
            rec["window"] = data["window"]
    elif typed == "APPROVE":
        rec["policy"] = data
    errs = lib.schema_errors("approval", rec)
    if errs:
        raise SystemExit("\n".join(errs))
    d = project / "00_admin" / "approvals"
    target = d / ("policy.json" if what == "policy" else f"{what}.json")
    if target.exists():
        (d / "history").mkdir(exist_ok=True)
        target.rename(d / "history" / f"{target.stem}.{lib.now_iso().replace(':', '')[:17]}.json")
    target.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", "utf-8", newline="\n")
    print(f"recorded {rec['decision']} in {target}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projects-dir", type=Path, default=lib.PROJECTS, help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("marker", "summary", "approve"):
        s = sub.add_parser(name)
        s.add_argument("code")
        s.add_argument("what", help="R-### or policy")
    st = sub.add_parser("status")
    st.add_argument("code")
    st.add_argument("run_id", nargs="?")
    a = ap.parse_args(argv)
    project = a.projects_dir / a.code
    if not project.is_dir():
        raise SystemExit(f"no project {a.code}")
    if a.cmd == "marker":
        print(marker(project, a.what))
    elif a.cmd == "summary":
        print(summary(project, a.what))
    elif a.cmd == "status":
        print(status(project, a.run_id))
    else:
        return approve(project, a.what)
    return 0


if __name__ == "__main__":
    sys.exit(main())
