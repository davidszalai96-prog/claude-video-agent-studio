"""VRAM watchdog: headroom check before each H3 job, halt detection during an approved window, automatic restart.

    .venv\\Scripts\\python.exe pipeline\\watchdog\\vram_watch.py headroom --required-gb 24 [--project MAG]
    ... vram_watch.py launch-check
    ... vram_watch.py watch --project MAG --run-id R-004            # real: only inside the approved window
    ... vram_watch.py watch --dry-run [--project MAG --run-id R-004 | --window-minutes 5]
    ... vram_watch.py simulate [scenario|all]                        # state machine on scripted observations

Design: docs/studio-design.md, Tool layer -> ComfyUI restart procedure. The watchdog never queues anything.
It follows ComfyUI's console log (progress age), queue and API, and nvidia-smi / NVML. When a job halts inside
the approved window it runs restart_comfyui.ps1 by itself, at most max_restarts_per_window times; outside the
window, or past the limit, it stops and reports instead. --dry-run never ends or starts a process.

Runtime files (ignored by git) in pipeline/watchdog/runtime/:
  state.json        written by the watchdog: status, restarts, last event (the Render Wrangler reads it)
  current_job.json  written by the Render Wrangler when it queues: project, run_id, output_id, prompt_id,
                    config_hash, attention_profile, required_gb
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "tools"))
sys.path.insert(0, str(HERE.parents[0] / "comfy" / "bridge"))
import studio_lib as lib  # noqa: E402

CONFIG = json.loads((HERE / "config.json").read_text("utf-8"))
LAUNCH = json.loads((HERE / "comfyui_launch.json").read_text("utf-8"))
RUNTIME = HERE / "runtime"
RESTART_PS1 = HERE / "restart_comfyui.ps1"


# --- observations ------------------------------------------------------------------

@dataclass
class Obs:
    t: float                          # epoch seconds
    api_ok: bool
    running: str | None = None        # prompt_id of the running job
    pending: int = 0
    progress_t: float | None = None   # epoch time of the newest sampler progress line
    progress_step: int | None = None
    progress_total: int | None = None
    vram_used_gb: float | None = None
    vram_total_gb: float | None = None


def gpu_memory() -> tuple[float | None, float | None]:
    try:
        import pynvml
        pynvml.nvmlInit()
        m = pynvml.nvmlDeviceGetMemoryInfo(pynvml.nvmlDeviceGetHandleByIndex(0))
        return round(m.used / 2**30, 2), round(m.total / 2**30, 2)
    except Exception:
        return None, None


def observe_live() -> Obs:
    import comfy_api
    used, total = gpu_memory()
    now = time.time()
    try:
        comfy_api.system_stats()
        q = comfy_api.get("/api/queue")
        running = q["queue_running"][0][1] if q["queue_running"] else None
        prog = comfy_api.last_progress()
    except comfy_api.ComfyDown:
        return Obs(t=now, api_ok=False, vram_used_gb=used, vram_total_gb=total)
    p_t = datetime.fromisoformat(prog["t"]).timestamp() if prog else None
    return Obs(t=now, api_ok=True, running=running, pending=len(q["queue_pending"]),
               progress_t=p_t, progress_step=prog["step"] if prog else None,
               progress_total=prog["total"] if prog else None, vram_used_gb=used, vram_total_gb=total)


# --- the state machine ---------------------------------------------------------------

@dataclass
class Job:
    prompt_id: str
    start_t: float
    last_progress_t: float | None = None
    last_step: int | None = None
    total: int | None = None
    peak_gb: float = 0.0
    last_sample_t: float = 0.0


@dataclass
class Watchdog:
    cfg: dict
    window_end_t: float
    restart: callable                 # () -> dict with "status" ("restarted" on success)
    dry_run: bool = False
    restarts: int = 0
    status: str = "watching"
    last_api_ok_t: float | None = None
    job: Job | None = None
    suppressed: set = field(default_factory=set)  # prompt_ids already handled as halted
    events: list = field(default_factory=list)

    def _event(self, t: float, event: str, **kw) -> dict:
        e = {"t": t, "event": event, **{k: v for k, v in kw.items() if v is not None}}
        self.events.append(e)
        return e

    @property
    def stopped(self) -> bool:
        return self.status in ("window_end", "stopped_alert")

    def step(self, o: Obs) -> list[dict]:
        start = len(self.events)
        if self.stopped:
            return []
        if self.last_api_ok_t is None:
            self.last_api_ok_t = o.t
        if o.api_ok:
            self.last_api_ok_t = o.t
            self._track_job(o)
        elif o.t - self.last_api_ok_t >= self.cfg["api_timeout_s"]:
            self._halt(o, "api_down", f"no API answer for {int(o.t - self.last_api_ok_t)} s")
        if not self.stopped and o.t >= self.window_end_t and self.job is None:
            self.status = "window_end"
            self._event(o.t, "window_end", restart_count=self.restarts)
        return self.events[start:]

    def _track_job(self, o: Obs):
        if self.job and self.job.prompt_id != o.running:
            self._event(o.t, "peak", peak_gb=self.job.peak_gb, detail=f"job {self.job.prompt_id} left the queue")
            self.job = None
        if o.running is None or o.running in self.suppressed:
            return
        if self.job is None:
            self.job = Job(prompt_id=o.running, start_t=o.t, last_sample_t=o.t)
        j = self.job
        if o.vram_used_gb is not None:
            j.peak_gb = max(j.peak_gb, o.vram_used_gb)
        # A progress line counts only if it was stamped after this job started.
        if o.progress_t is not None and o.progress_t >= j.start_t - 1:
            if j.last_progress_t is None or o.progress_t > j.last_progress_t:
                j.last_progress_t, j.last_step, j.total = o.progress_t, o.progress_step, o.progress_total
        if o.t - j.last_sample_t >= self.cfg["sample_every_s"]:
            j.last_sample_t = o.t
            self._event(o.t, "sample", used_gb=o.vram_used_gb, total_gb=o.vram_total_gb, step=j.last_step,
                        total_steps=j.total, seconds_since_progress=None if j.last_progress_t is None
                        else round(o.t - j.last_progress_t, 1))
        if j.last_progress_t is not None:
            if o.t - j.last_progress_t >= self.cfg["progress_timeout_s"]:
                self._halt(o, "no_progress", f"no sampler step for {int(o.t - j.last_progress_t)} s "
                                             f"(last {j.last_step}/{j.total})")
        elif o.t - j.start_t >= self.cfg["startup_timeout_s"]:
            self._halt(o, "no_first_step", f"no sampler step {int(o.t - j.start_t)} s after the job started")

    def _halt(self, o: Obs, reason: str, detail: str):
        j = self.job
        self._event(o.t, "halt_detected", reason=reason, detail=detail, step=j.last_step if j else None,
                    total_steps=j.total if j else None, peak_gb=j.peak_gb if j else None,
                    prompt_id=j.prompt_id if j else None)
        if j:
            self.suppressed.add(j.prompt_id)
        self.job = None
        if o.t >= self.window_end_t:
            self.status = "stopped_alert"
            self._event(o.t, "restart_failed", detail="window has ended: no restart; tell the user")
            return
        if self.restarts >= self.cfg["max_restarts_per_window"]:
            self.status = "stopped_alert"
            self._event(o.t, "restart_failed", detail=f"restart limit ({self.cfg['max_restarts_per_window']}) "
                                                     "reached: window ends; tell the user")
            return
        if self.dry_run:
            self._event(o.t, "restart", detail="dry run: would close and reopen ComfyUI now", restart_count=self.restarts)
            self.last_api_ok_t = o.t
            return
        result = self.restart()
        if result.get("status") == "restarted":
            self.restarts += 1
            self.last_api_ok_t = o.t
            self._event(o.t, "restart", restart_count=self.restarts, detail=json.dumps(result)[:400])
        else:
            self.status = "stopped_alert"
            self._event(o.t, "restart_failed", detail=json.dumps(result)[:400])


# --- actions and logging ------------------------------------------------------------

def run_restart(cfg: dict, dry_run: bool) -> dict:
    args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(RESTART_PS1),
            "-Launcher", LAUNCH["launcher"], "-Port", str(cfg["port"]), "-WaitSeconds", str(cfg["restart_wait_s"]),
            "-StartTimeoutSeconds", str(cfg["start_timeout_s"]), "-ReleasedMaxUsedGB", str(cfg["released_max_used_gb"])]
    if dry_run:
        args.append("-DryRun")
    p = subprocess.run(args, capture_output=True, text=True, timeout=cfg["start_timeout_s"] + 120)
    last = (p.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        return {"status": "script_error", "exit": p.returncode, "stderr": p.stderr[-400:]}


def to_log_entry(e: dict, ctx: dict) -> dict:
    ts = datetime.fromtimestamp(e["t"]).astimezone().isoformat(timespec="seconds")
    out = {"ts": ts, "event": e["event"]}
    for k in ("project", "run_id", "output_id", "config_hash", "attention_profile"):
        if ctx.get(k):
            out[k] = ctx[k]
    for k in ("used_gb", "total_gb", "peak_gb", "step", "total_steps", "seconds_since_progress", "restart_count"):
        if e.get(k) is not None:
            out[k] = e[k]
    detail = " | ".join(str(e[k]) for k in ("reason", "detail", "prompt_id") if e.get(k))
    if detail:
        out["detail"] = detail
    return out


def current_job() -> dict:
    p = RUNTIME / "current_job.json"
    try:
        return json.loads(p.read_text("utf-8")) if p.exists() else {}
    except ValueError:
        return {}


def write_state(wd: Watchdog, ctx: dict, last: dict | None):
    RUNTIME.mkdir(exist_ok=True)
    (RUNTIME / "state.json").write_text(json.dumps({
        "status": wd.status, "dry_run": wd.dry_run, "restarts": wd.restarts,
        "window_end": datetime.fromtimestamp(wd.window_end_t).astimezone().isoformat(timespec="seconds"),
        "job": wd.job.__dict__ if wd.job else None, "last_event": last, "project": ctx.get("project"),
        "run_id": ctx.get("run_id"), "updated": lib.now_iso()}, indent=1), "utf-8")


# --- commands -----------------------------------------------------------------------

def other_gpu_users() -> list[str]:
    import psutil
    blockers = []
    heavy = {n.lower() for n in CONFIG["gpu_heavy_processes"]}
    listener = None
    for c in psutil.net_connections(kind="tcp"):
        if c.laddr and c.laddr.port == CONFIG["port"] and c.status == psutil.CONN_LISTEN:
            listener = c.pid
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        name = (p.info["name"] or "").lower()
        if name in heavy:
            blockers.append(f"{p.info['name']} (pid {p.info['pid']}) is running")
        cmd = " ".join(p.info["cmdline"] or [])
        if name == "python.exe" and "main.py" in cmd and p.info["pid"] != listener:
            try:
                if p.parent() and p.parent().pid == listener or listener in [c.pid for c in p.children()]:
                    continue
            except psutil.Error:
                pass
            if "--port" in cmd and str(CONFIG["port"]) not in cmd:
                blockers.append(f"another ComfyUI instance (pid {p.info['pid']}): {cmd[:80]}")
    return blockers


def cmd_headroom(a) -> int:
    import comfy_api
    used, total = gpu_memory()
    free = None if used is None else round(total - used, 2)
    blockers = []
    if free is None:
        blockers.append("cannot read GPU memory")
    elif free < a.required_gb + a.margin_gb:
        blockers.append(f"free VRAM {free} GB < recorded peak {a.required_gb} GB + margin {a.margin_gb} GB")
    try:
        running, pending = comfy_api.queue_counts()
        if running or pending:
            blockers.append(f"ComfyUI queue busy: {running} running, {pending} pending")
    except comfy_api.ComfyDown as e:
        blockers.append(str(e))
    blockers += other_gpu_users()
    res = {"ok": not blockers, "free_gb": free, "used_gb": used, "total_gb": total,
           "required_gb": a.required_gb, "margin_gb": a.margin_gb, "blockers": blockers}
    print(json.dumps(res))
    if a.project:
        entry = {"ts": lib.now_iso(), "event": "headroom_check", "project": Path(a.project).name,
                 "free_gb": free or 0, "used_gb": used or 0, "total_gb": total or 0, "required_gb": a.required_gb,
                 "detail": "ok" if not blockers else "; ".join(blockers)}
        with open(Path(a.project) / "00_admin" / "vram_log.jsonl", "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entry) + "\n")
    return 0 if not blockers else 1


def bat_python_args(path: str) -> list[str]:
    for line in Path(path).read_text("utf-8", errors="replace").splitlines():
        s = line.strip()
        if s.lower().startswith("python "):
            return s.split()[1:]
    return []


def running_comfy_args() -> tuple[list[str] | None, str | None]:
    import psutil
    for c in psutil.net_connections(kind="tcp"):
        if c.laddr and c.laddr.port == CONFIG["port"] and c.status == psutil.CONN_LISTEN:
            p = psutil.Process(c.pid)
            cmd = p.cmdline()
            i = next((k for k, v in enumerate(cmd) if v.endswith("main.py")), None)
            console = None
            for anc in p.parents():
                if anc.name().lower() == "cmd.exe":
                    console = " ".join(anc.cmdline())
                    break
            return (cmd[i:] if i is not None else cmd), console
    return None, None


def cmd_launch_check(_a) -> int:
    expected = bat_python_args(LAUNCH["launcher"])
    running, console = running_comfy_args()
    ok = running == expected and console is not None and LAUNCH["launcher"].lower() in console.lower()
    print(json.dumps({"ok": ok, "launcher": LAUNCH["launcher"], "expected": expected, "running": running,
                      "console": console,
                      "note": None if ok else "ComfyUI was not started by ComfyUI.bat with its arguments; "
                                              "a restart would reopen it with ComfyUI.bat. Tell the user before the window."}))
    return 0 if ok else 1


def cmd_watch(a) -> int:
    ctx = {}
    if a.project and a.run_id:
        window, why = lib.approved_window(Path(a.project), a.run_id)
        if window is None:
            print(f"refused: {why}")
            return 2
        state = lib.window_state(window)
        if state != "open" and not a.dry_run:
            print(f"refused: the approved window is {state} ({window['start']} - {window['end']})")
            return 2
        end_t = lib.parse_ts(window["end"]).timestamp()
        ctx = {"project": Path(a.project).name, "run_id": a.run_id}
    elif a.dry_run:
        end_t = time.time() + a.window_minutes * 60
    else:
        print("refused: a real watch needs --project and --run-id with a recorded approval")
        return 2
    wd = Watchdog(cfg=CONFIG, window_end_t=end_t, dry_run=a.dry_run, restart=lambda: run_restart(CONFIG, a.dry_run))
    log_path = Path(a.project) / "00_admin" / "vram_log.jsonl" if ctx else None
    stop_at = time.time() + a.max_minutes * 60 if a.max_minutes else None

    def emit(e):
        entry = to_log_entry(e, {**ctx, **{k: v for k, v in current_job().items() if k in ("output_id", "config_hash", "attention_profile")}})
        print(json.dumps(entry), flush=True)
        if log_path:
            with open(log_path, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(entry) + "\n")

    launch = json.loads(subprocess.run([sys.executable, __file__, "launch-check"], capture_output=True, text=True).stdout or "{}")
    emit(wd._event(time.time(), "window_start", detail=("dry run; " if a.dry_run else "") +
                   ("launcher ok" if launch.get("ok") else f"launcher mismatch: {launch.get('running')}")))
    last = None
    while not wd.stopped and (stop_at is None or time.time() < stop_at):
        for e in wd.step(observe_live()):
            emit(e)
            last = e
        write_state(wd, ctx, last)
        if not wd.stopped:
            time.sleep(a.poll_s or CONFIG["poll_s"])
    write_state(wd, ctx, last)
    print(json.dumps({"watchdog": wd.status, "restarts": wd.restarts}), flush=True)
    return 0 if wd.status in ("window_end", "watching") else 1


# --- scripted scenarios (dry run of the state machine) -----------------------------------

def scenario_obs(name: str, t0: float) -> tuple[list[Obs], list[dict], float]:
    """Observations every 15 s, scripted restart results, and the window end."""
    obs, results = [], []
    step = 15
    mk = lambda i, **kw: Obs(t=t0 + i * step, **kw)  # noqa: E731
    if name == "normal":       # 28 steps at ~50 s, then decode, then the queue empties
        for i in range(0, 120):
            t = t0 + i * step
            done = i >= 100
            obs.append(Obs(t=t, api_ok=True, running=None if done else "p1",
                           progress_t=t0 + 30 + 50 * min(27, max(0, (i * step - 30) // 50)) if i * step >= 30 else None,
                           progress_step=min(28, max(0, (i * step - 30) // 50 + 1)), progress_total=28, vram_used_gb=24.0))
        return obs, results, t0 + 3600
    if name == "stall":        # progress until step 9, then nothing for > 5 min; restart succeeds
        for i in range(0, 70):     # last step at +450 s; the halt is due at +750 s
            t = t0 + i * step
            last = t0 + min(i * step, 450)
            obs.append(Obs(t=t, api_ok=True, running="p1", progress_t=last,
                           progress_step=min(9, i), progress_total=28, vram_used_gb=31.5))
        return obs, [{"status": "restarted", "api_back_after_s": 40}], t0 + 3600
    if name == "api_down":     # ComfyUI stops answering; restart succeeds
        for i in range(0, 24):     # no answer from +60 s; restart at +165 s; the API is back from +225 s
            up = i < 4 or i >= 15
            obs.append(mk(i, api_ok=up, running="p1" if i < 4 else None, progress_t=t0 + i * step if i < 4 else None,
                          progress_step=i, progress_total=28))
        return obs, [{"status": "restarted", "api_back_after_s": 55}], t0 + 3600
    if name == "not_released":  # stall, but GPU memory is not released after closing
        for i in range(0, 40):
            obs.append(mk(i, api_ok=True, running="p1", progress_t=t0, progress_step=1, progress_total=28, vram_used_gb=31.8))
        return obs, [{"status": "memory_not_released", "gpu_used_gb_after_close": 30.9}], t0 + 3600
    if name == "three_halts":   # three stalled jobs in one window: two restarts, then the window ends
        for k, pid in enumerate(["p1", "p2", "p3"]):
            base = k * 40
            for i in range(0, 40):
                obs.append(Obs(t=t0 + (base + i) * step, api_ok=True, running=pid, progress_t=t0 + base * step,
                               progress_step=1, progress_total=28))
        return obs, [{"status": "restarted"}, {"status": "restarted"}], t0 + 7200
    if name == "after_window":  # the window ended while a job runs; then it stalls: no restart
        for i in range(0, 40):
            obs.append(mk(i, api_ok=True, running="p1", progress_t=t0, progress_step=1, progress_total=28))
        return obs, [], t0 + 60
    raise SystemExit(f"unknown scenario {name}")


SCENARIOS = ["normal", "stall", "api_down", "not_released", "three_halts", "after_window"]


def run_scenario(name: str, dry_run: bool = False) -> Watchdog:
    t0 = 1_760_000_000.0
    obs, results, end = scenario_obs(name, t0)
    calls = iter(results)
    wd = Watchdog(cfg=CONFIG, window_end_t=end, dry_run=dry_run, restart=lambda: next(calls, {"status": "script_error"}))
    for o in obs:
        wd.step(o)
        if wd.stopped:
            break
    return wd


def cmd_simulate(a) -> int:
    for name in (SCENARIOS if a.scenario == "all" else [a.scenario]):
        wd = run_scenario(name, dry_run=a.dry_run)
        t0 = 1_760_000_000.0
        print(f"== {name}: status {wd.status}, restarts {wd.restarts}")
        for e in wd.events:
            if e["event"] == "sample":
                continue
            rest = {k: v for k, v in e.items() if k not in ("t", "event")}
            print(f"   +{int(e['t'] - t0):5d}s  {e['event']:14s} {json.dumps(rest)[:160]}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("headroom")
    h.add_argument("--required-gb", type=float, required=True)
    h.add_argument("--margin-gb", type=float, default=CONFIG["headroom_margin_gb"])
    h.add_argument("--project")
    sub.add_parser("launch-check")
    w = sub.add_parser("watch")
    w.add_argument("--project")
    w.add_argument("--run-id")
    w.add_argument("--dry-run", action="store_true")
    w.add_argument("--window-minutes", type=float, default=5)
    w.add_argument("--max-minutes", type=float)
    w.add_argument("--poll-s", type=float)
    s = sub.add_parser("simulate")
    s.add_argument("scenario", nargs="?", default="all")
    s.add_argument("--dry-run", action="store_true", help="simulate the watchdog's own dry-run mode")
    a = ap.parse_args(argv)
    return {"headroom": cmd_headroom, "launch-check": cmd_launch_check, "watch": cmd_watch,
            "simulate": cmd_simulate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
