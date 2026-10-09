#!/usr/bin/env python3
"""Send video files to the Google Gemini API for analysis and save JSON reports.

Standard library only (Python 3.8+). Works on Windows, macOS and Linux.

The API key is looked up locally and is NEVER printed, logged or written to disk.
Lookup order: --key-file, GEMINI_API_KEY / GOOGLE_API_KEY (or any environment
variable holding a Gemini-style key), the Windows user environment in the
registry, then *.txt files in each video's own folder (disable with --no-key-scan).

Examples
  python gemini_video.py clip.mp4
  python gemini_video.py --list "C:/CU/output/video"
  python gemini_video.py clip.mp4 --mode compare --gen-prompt prompt.txt
  python gemini_video.py a.mp4 b.mp4 c.mp4 --batch --fps 6
  python gemini_video.py clip.mp4 --start 6 --end 12 --extra "Focus on what holds the sword."
"""

import argparse, base64, datetime, glob, json, os, re, shutil, struct, subprocess, sys, time, traceback
import urllib.request, urllib.error

VERSION = "1.0"
API_BASE = os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com")
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
VIDEO_EXTS = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".mpeg", ".mpg", ".wmv", ".3gp", ".flv")
MIME = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
        ".mkv": "video/x-matroska", ".avi": "video/x-msvideo", ".mpeg": "video/mpeg", ".mpg": "video/mpeg",
        ".wmv": "video/x-ms-wmv", ".3gp": "video/3gpp", ".flv": "video/x-flv"}
KEY_RE = re.compile(r"AIza[0-9A-Za-z_\-]{35}")
INLINE_TOTAL_LIMIT = int(os.environ.get("GEMINI_INLINE_LIMIT", str(45 * 1024 * 1024)))  # raw bytes per request
PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
MAX_BATCH = 10


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- video info
def mp4_duration(path):
    """Duration in seconds from the MP4/MOV mvhd box, without external tools."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            pos = 0
            while pos + 8 <= size:
                f.seek(pos)
                box_size, typ = struct.unpack(">I4s", f.read(8))
                hlen = 8
                if box_size == 1:
                    box_size = struct.unpack(">Q", f.read(8))[0]
                    hlen = 16
                elif box_size == 0:
                    box_size = size - pos
                if box_size < 8:
                    return None
                if typ == b"moov":
                    p, end = pos + hlen, pos + box_size
                    while p + 8 <= end:
                        f.seek(p)
                        s, t = struct.unpack(">I4s", f.read(8))
                        if t == b"mvhd":
                            ver = f.read(1)[0]
                            f.read(3)
                            if ver == 1:
                                f.read(16)
                                ts, dur = struct.unpack(">IQ", f.read(12))
                            else:
                                f.read(8)
                                ts, dur = struct.unpack(">II", f.read(8))
                            return round(dur / ts, 3) if ts else None
                        if s < 8:
                            break
                        p += s
                pos += box_size
    except Exception:
        return None
    return None


def video_duration(path):
    d = mp4_duration(path) if path.lower().endswith((".mp4", ".mov", ".m4v", ".3gp")) else None
    if d is None and shutil.which("ffprobe"):
        try:
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                  "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, timeout=30)
            d = round(float(out.stdout.strip()), 3)
        except Exception:
            d = None
    return d


def list_videos(folder):
    files = [p for p in glob.glob(os.path.join(folder, "*"))
             if os.path.isfile(p) and p.lower().endswith(VIDEO_EXTS)]
    return sorted(files, key=os.path.getmtime, reverse=True)


def describe(path):
    return {"name": os.path.basename(path), "path": os.path.abspath(path),
            "size_mb": round(os.path.getsize(path) / 1e6, 2),
            "modified": datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds"),
            "duration_s": video_duration(path)}


# ---------------------------------------------------------------- API key
def find_api_key(key_file, video_dirs, scan_txt):
    if key_file:
        with open(key_file, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
        m = KEY_RE.search(txt)
        if m:
            return m.group(0), f"key file ({os.path.basename(key_file)})"
        line = next((l.strip() for l in txt.splitlines() if l.strip()), "")
        if line and " " not in line:
            return line, f"key file ({os.path.basename(key_file)}, first line)"
        raise RuntimeError(f"No API key found in {os.path.basename(key_file)}")
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = os.environ.get(name, "").strip()
        if v:
            return v, f"environment variable {name}"
    for name, v in os.environ.items():
        m = KEY_RE.search(v or "")
        if m:
            return m.group(0), f"environment variable {name}"
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                i = 0
                while True:
                    try:
                        name, v, _ = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    i += 1
                    m = KEY_RE.search(str(v))
                    if m:
                        return m.group(0), f"user environment variable {name} (registry)"
        except Exception:
            pass
    if scan_txt:
        for d in dict.fromkeys(video_dirs):
            for p in sorted(glob.glob(os.path.join(d, "*.txt"))):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        m = KEY_RE.search(f.read())
                    if m:
                        return m.group(0), f"text file {os.path.basename(p)} in the video folder"
                except Exception:
                    pass
    raise RuntimeError("No Gemini API key found. Set GEMINI_API_KEY, or pass --key-file PATH "
                       "(a text file containing the key). Do not paste the key into chat.")


# ---------------------------------------------------------------- HTTP
class Api:
    def __init__(self, key, timeout):
        self.key, self.timeout = key, timeout

    def scrub(self, text):
        return (text or "").replace(self.key, "[KEY]") if self.key else (text or "")

    def call(self, method, url, body=None, headers=None, timeout=None):
        h = {"x-goog-api-key": self.key}
        h.update(headers or {})
        req = urllib.request.Request(url, data=body, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
                return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read()
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error reaching {url.split('/v1')[0]}: {e.reason}. "
                               "If this runs in a sandbox, generativelanguage.googleapis.com may need "
                               "to be added to the allowed domains.")

    HINTS = {400: "bad request: check the model supports video and the options used (fps, offsets, --low-res)",
             403: "the key was rejected or lacks access to this API",
             404: "model or file not found: run --list-models to see what this key can use",
             413: "request too large: the video should go through the Files API (lower GEMINI_INLINE_LIMIT)",
             429: "quota or rate limit hit: wait, or batch several videos into one request with --batch",
             503: "Gemini is over capacity: wait 10+ minutes and retry the same request"}

    def err(self, what, st, body):
        text = body.decode("utf-8", "ignore")
        hint = ("the API key is invalid or revoked: check the key file / variable (don't paste it in chat)"
                if "API_KEY_INVALID" in text else self.HINTS.get(st))
        return RuntimeError(f"{what}: HTTP {st}{' (' + hint + ')' if hint else ''}: "
                            f"{self.scrub(text)[:1200]}")

    def upload(self, path, mime):
        size = os.path.getsize(path)
        st, hd, body = self.call("POST", f"{API_BASE}/upload/v1beta/files",
                                 json.dumps({"file": {"display_name": os.path.basename(path)}}).encode(),
                                 {"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                                  "X-Goog-Upload-Header-Content-Length": str(size),
                                  "X-Goog-Upload-Header-Content-Type": mime,
                                  "Content-Type": "application/json"}, timeout=120)
        url = hd.get("x-goog-upload-url")
        if st != 200 or not url:
            raise self.err("Upload start failed", st, body)
        with open(path, "rb") as f:
            data = f.read()
        st, hd, body = self.call("POST", url, data, {"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                                                     "X-Goog-Upload-Command": "upload, finalize"})
        if st != 200:
            raise self.err("Upload failed", st, body)
        info = json.loads(body)["file"]
        deadline = time.time() + 600
        while info.get("state") != "ACTIVE":
            if info.get("state") == "FAILED":
                raise RuntimeError(f"Gemini could not process {os.path.basename(path)}")
            if time.time() > deadline:
                raise RuntimeError("Timed out waiting for the uploaded video to become ACTIVE")
            time.sleep(4)
            st, hd, body = self.call("GET", f"{API_BASE}/v1beta/{info['name']}", timeout=60)
            if st == 200:
                info = json.loads(body)
        return info["name"], info["uri"]

    def delete(self, name):
        try:
            self.call("DELETE", f"{API_BASE}/v1beta/{name}", timeout=60)
        except Exception:
            pass

    def generate(self, model, parts, gen_config, retries):
        payload = json.dumps({"contents": [{"role": "user", "parts": parts}],
                              "generationConfig": gen_config}).encode()
        url = f"{API_BASE}/v1beta/models/{model}:generateContent"
        for attempt in range(retries + 1):
            st, hd, body = self.call("POST", url, payload, {"Content-Type": "application/json"})
            if st == 200:
                return json.loads(body)
            e = self.err("generateContent failed", st, body)
            if st in (500, 503) and attempt < retries:
                wait = 30 * (attempt + 1)
                log(f"  HTTP {st} (server busy); retrying in {wait} s...")
                time.sleep(wait)
                continue
            raise e

    def models(self):
        st, hd, body = self.call("GET", f"{API_BASE}/v1beta/models?pageSize=200", timeout=60)
        if st != 200:
            raise self.err("Listing models failed", st, body)
        return [m for m in json.loads(body).get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])]


# ---------------------------------------------------------------- prompts
def build_prompt(args):
    if args.mode == "custom":
        if not args.prompt_file:
            raise RuntimeError("--mode custom needs --prompt-file")
        with open(args.prompt_file, encoding="utf-8") as f:
            text = f.read()
    else:
        with open(os.path.join(PROMPT_DIR, f"{args.mode}.md"), encoding="utf-8") as f:
            text = f.read()
        if args.mode == "compare":
            if not args.gen_prompt:
                raise RuntimeError("--mode compare needs --gen-prompt FILE (the prompt used to make the video)")
            with open(args.gen_prompt, encoding="utf-8") as f:
                text = text.replace("{GEN_PROMPT}", f.read().strip())
    if args.start is not None or args.end is not None:
        text += (f"\n\nOnly the segment from {args.start or 0} s to {args.end if args.end is not None else 'the end'}"
                 " of the video is provided; report timestamps relative to the full video.")
    if args.extra:
        text += "\n\nAdditional instructions: " + args.extra
    return text


def batch_wrap(prompt, names):
    listing = "\n".join(f"- {n}" for n in names)
    return (f"You will receive {len(names)} separate videos. Each video part is preceded by a text part "
            f"'VIDEO: <filename>'. Analyze each one independently; never mix details between them.\n"
            f"Videos:\n{listing}\n\nReturn ONE JSON object whose keys are exactly these filenames and whose "
            f"values each follow the schema below.\n\n{prompt}")


# ---------------------------------------------------------------- main work
def resolve_videos(args):
    paths = []
    for v in args.videos:
        hits = glob.glob(v) if any(c in v for c in "*?[") else [v]
        for h in hits:
            if os.path.isdir(h):
                raise RuntimeError(f"{h} is a folder. Use --list to see its videos, then pass a file path.")
            if not os.path.isfile(h):
                raise RuntimeError(f"Video not found: {h}")
            paths.append(h)
    if args.newest:
        vids = list_videos(args.newest)
        if not vids:
            raise RuntimeError(f"No videos in {args.newest}")
        paths.append(vids[0])
    if not paths:
        raise RuntimeError("No video given. Pass one or more paths, or use --list DIR to choose.")
    return list(dict.fromkeys(os.path.abspath(p) for p in paths))


def estimate_tokens(duration, fps, low_res, start, end):
    if not duration:
        return None
    seg = max(0.0, (end if end is not None else duration) - (start or 0))
    return int(seg * fps * (66 if low_res else 258) + seg * 32)


def report_path(video, out_dir, mode, suffix=""):
    stem = os.path.splitext(os.path.basename(video))[0]
    d = out_dir or os.path.dirname(video)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    name = f"{stem}.gemini-{mode}{suffix}.json"
    if not os.access(d, os.W_OK):
        d = os.getcwd()
    return os.path.join(d, name)


def video_part(api, path, fps, start, end, inline):
    mime = MIME.get(os.path.splitext(path)[1].lower(), "video/mp4")
    meta = {"fps": fps}
    if start is not None:
        meta["startOffset"] = f"{start}s"
    if end is not None:
        meta["endOffset"] = f"{end}s"
    if inline:
        with open(path, "rb") as f:
            return {"inlineData": {"mimeType": mime, "data": base64.b64encode(f.read()).decode()},
                    "videoMetadata": meta}, None
    log(f"  uploading {os.path.basename(path)} via the Files API...")
    name, uri = api.upload(path, mime)
    return {"fileData": {"mimeType": mime, "fileUri": uri}, "videoMetadata": meta}, name


def run(args):
    videos = resolve_videos(args)
    if args.batch and len(videos) > MAX_BATCH:
        raise RuntimeError(f"--batch takes at most {MAX_BATCH} videos per request")
    groups = [videos] if args.batch else [[v] for v in videos]
    infos = {v: describe(v) for v in videos}
    prompt = build_prompt(args)
    key, key_src = find_api_key(args.key_file, [os.path.dirname(v) for v in videos], not args.no_key_scan)
    log(f"API key: found in {key_src} (not shown)")
    api = Api(key, args.timeout)

    gen_config = {"temperature": args.temperature, "maxOutputTokens": args.max_output_tokens}
    if args.mode != "custom" or args.json:
        gen_config["responseMimeType"] = "application/json"
    if args.low_res:
        gen_config["mediaResolution"] = "MEDIA_RESOLUTION_LOW"

    written, failed = [], 0
    for group in groups:
        total_est = sum(estimate_tokens(infos[v]["duration_s"], args.fps, args.low_res, args.start, args.end) or 0
                        for v in group)
        for v in group:
            i = infos[v]
            log(f"Video: {i['name']}  {i['size_mb']} MB  {i['duration_s']} s  modified {i['modified']}")
        log(f"Model {args.model}, {args.fps} fps, mode {args.mode}; estimated input ~{total_est:,} tokens")
        if args.dry_run:
            continue

        result = {"tool": f"gemini-video-review {VERSION}", "status": "error", "model": args.model,
                  "mode": args.mode, "fps": args.fps, "segment": [args.start, args.end],
                  "low_res": args.low_res, "videos": [infos[v] for v in group], "key_source": key_src,
                  "extra_instructions": args.extra,
                  "started": datetime.datetime.now().isoformat(timespec="seconds")}
        uploaded = []
        try:
            parts, running = [], 0
            for v in group:
                size = os.path.getsize(v)
                inline = running + size <= INLINE_TOTAL_LIMIT
                running += size if inline else 0
                vp, fname = video_part(api, v, args.fps, args.start, args.end, inline)
                if fname:
                    uploaded.append(fname)
                if len(group) > 1:
                    parts.append({"text": f"VIDEO: {os.path.basename(v)}"})
                parts.append(vp)
            parts.append({"text": batch_wrap(prompt, [os.path.basename(v) for v in group]) if len(group) > 1 else prompt})
            result["transport"] = "files_api" if uploaded else "inline"
            log("Waiting for Gemini (usually under a few minutes)...")
            t0 = time.time()
            resp = api.generate(args.model, parts, gen_config, args.retries)
            result["seconds"] = round(time.time() - t0, 1)
            result["usage"] = resp.get("usageMetadata", {})
            cand = (resp.get("candidates") or [{}])[0]
            result["finish_reason"] = cand.get("finishReason")
            if not cand.get("content"):
                result["prompt_feedback"] = resp.get("promptFeedback")
            text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", [])
                           if not p.get("thought"))
            try:
                parsed = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip()))
            except Exception:
                parsed = None
            if parsed is None:
                result["analysis_raw"] = text
            elif len(group) > 1 and isinstance(parsed, dict):
                result["analysis_by_video"] = parsed
            else:
                result["analysis"] = parsed
            result["status"] = "ok" if text else "empty"
            log(f"Done in {result['seconds']} s; tokens: {result['usage'].get('totalTokenCount', '?')}; "
                f"finish: {result['finish_reason']}")
        except Exception as e:
            result["error"] = api.scrub(f"{type(e).__name__}: {e}")
            result["trace"] = api.scrub(traceback.format_exc()[-1500:])
            log(f"FAILED: {result['error']}")
            failed += 1
        finally:
            for n in uploaded:
                api.delete(n)
        result["finished"] = datetime.datetime.now().isoformat(timespec="seconds")

        targets = []
        if len(group) > 1 and "analysis_by_video" in result:
            by = result.pop("analysis_by_video")
            for v in group:
                r = dict(result, videos=[infos[v]], batch_of=[infos[x]["name"] for x in group],
                         analysis=by.get(infos[v]["name"], by.get(os.path.splitext(infos[v]["name"])[0])))
                targets.append((report_path(v, args.out, args.mode), r))
        else:
            suffix = "-batch" if len(group) > 1 else ""
            targets.append((report_path(group[0], args.out, args.mode, suffix), result))
        for path, r in targets:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2)
            written.append(path)
            log(f"Report: {path}")
    return written, failed


def main():
    ap = argparse.ArgumentParser(description="Analyze videos with Google Gemini and save JSON reports.")
    ap.add_argument("videos", nargs="*", help="video file paths (globs allowed)")
    ap.add_argument("--list", metavar="DIR", help="list videos in DIR, newest first, then exit")
    ap.add_argument("--newest", metavar="DIR", help="also analyze the newest video in DIR (only when asked for)")
    ap.add_argument("--mode", choices=["shots", "compare", "custom"], default="shots")
    ap.add_argument("--gen-prompt", metavar="FILE", help="prompt/storyboard used to make the video (compare mode)")
    ap.add_argument("--prompt-file", metavar="FILE", help="your own instructions (custom mode)")
    ap.add_argument("--json", action="store_true", help="custom mode: ask for JSON output")
    ap.add_argument("--extra", help="extra instructions appended to the prompt")
    ap.add_argument("--fps", type=float, default=12.0, help="frames per second Gemini samples (default 12)")
    ap.add_argument("--start", type=float, help="analyze from this second")
    ap.add_argument("--end", type=float, help="analyze up to this second")
    ap.add_argument("--low-res", action="store_true", help="low media resolution: ~4x fewer tokens per frame")
    ap.add_argument("--batch", action="store_true", help=f"send all videos in ONE request (max {MAX_BATCH})")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--list-models", action="store_true", help="list models this key can use, then exit")
    ap.add_argument("--out", metavar="DIR", help="folder for reports (default: next to each video)")
    ap.add_argument("--key-file", metavar="FILE", help="text file containing the API key")
    ap.add_argument("--no-key-scan", action="store_true", help="don't look for the key in *.txt next to the video")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--max-output-tokens", type=int, default=16384)
    ap.add_argument("--retries", type=int, default=2, help="retries on HTTP 500/503")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--dry-run", action="store_true", help="check inputs, key and token estimate; no API call")
    args = ap.parse_args()

    try:
        if args.list:
            vids = list_videos(args.list)
            if not vids:
                log(f"No videos in {args.list}")
            for p in vids:
                i = describe(p)
                log(f"{i['modified']}  {i['duration_s'] or '?':>7} s  {i['size_mb']:>8} MB  {i['name']}")
            return 0
        if args.list_models:
            key, src = find_api_key(args.key_file, [os.getcwd()], not args.no_key_scan)
            for m in Api(key, 60).models():
                log(f"{m['name'].split('/')[-1]:40s} {m.get('displayName', '')}")
            return 0
        written, failed = run(args)
        return 1 if failed else 0
    except Exception as e:
        log(f"ERROR: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
