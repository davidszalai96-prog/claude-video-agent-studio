"""Shared helpers for the studio tools: repo paths, schemas, YAML, hashing and path rules."""
from __future__ import annotations

import functools
import hashlib
import json
import ntpath
import re
from datetime import datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "pipeline" / "schemas"
PROJECTS = REPO / "projects"
TEMPLATE = REPO / "templates" / "project"
COMFY_OUTPUT = r"C:\CU\output"  # ComfyUI refuses to save outside it (folder_paths.py)

CODE_RE = re.compile(r"^[A-Z]{3}$")
SEQ_PREFIX_RE = re.compile(r"^([A-Z]{3})_SQ\d{3}")


# --- schemas -----------------------------------------------------------------

@functools.cache
def schemas() -> dict[str, dict]:
    """All schemas by short name, e.g. 'run_ticket' for run_ticket.schema.json."""
    return {p.name.removesuffix(".schema.json"): json.loads(p.read_text("utf-8"))
            for p in sorted(SCHEMAS.glob("*.schema.json"))}


@functools.cache
def registry() -> Registry:
    return Registry().with_resources(
        (s["$id"], Resource.from_contents(s)) for s in schemas().values())


def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(schemas()[name], registry=registry())


def schema_errors(name: str, data) -> list[str]:
    """Readable error lines, empty when data is valid."""
    errs = sorted(validator(name).iter_errors(data), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in errs]


# --- files -------------------------------------------------------------------

class _Loader(yaml.SafeLoader):
    """SafeLoader that keeps timestamps as strings, so they validate against the schema patterns."""


_Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:timestamp"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path: Path):
    return yaml.load(Path(path).read_text("utf-8"), Loader=_Loader)


def load_json(path: Path):
    return json.loads(Path(path).read_text("utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


# --- path rules (Windows semantics on any OS) ----------------------------------

def _norm(p: str) -> str:
    return ntpath.normcase(ntpath.normpath(str(p)))


def is_within(child: str, parent: str) -> bool:
    """True when child is strictly inside parent (case-insensitive, after resolving . and ..)."""
    c, p = _norm(child), _norm(parent).rstrip("\\")
    return c.startswith(p + "\\")


def on_d_drive(path: str) -> bool:
    return ntpath.splitdrive(str(path))[0].upper() == "D:"


def footage_folder_problem(path: str, output_root: str = COMFY_OUTPUT) -> str | None:
    """Why a footage folder is not allowed, or None when it is fine."""
    if on_d_drive(path):
        return "it is on D: (failing drive)"
    if not ntpath.isabs(str(path)) or not ntpath.splitdrive(str(path))[0]:
        return "it is not an absolute Windows path"
    if not is_within(path, output_root):
        return f"it is not inside {output_root}, where ComfyUI is allowed to save"
    return None
