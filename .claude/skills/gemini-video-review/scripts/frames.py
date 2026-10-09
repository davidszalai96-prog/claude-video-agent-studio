#!/usr/bin/env python3
"""Extract frames from a video and build labeled contact sheets so Claude can look
at the clip itself. Optionally detect hard cuts.

Needs ffmpeg (on PATH, or via the imageio-ffmpeg package). Pillow is optional; without
it you get the frames but no contact sheets.

Examples
  python frames.py clip.mp4 --out frames/            # 4 fps, sheets of 16
  python frames.py clip.mp4 --fps 12 --start 6 --end 9
  python frames.py clip.mp4 --times 1.5,4.9,6.3 --width 960
  python frames.py clip.mp4 --cuts                    # frames + likely cut times
  python frames.py clip.mp4 --cuts-only               # just the cut times
"""

import argparse, glob, json, os, re, shutil, subprocess, sys


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Install it, or: pip install imageio-ffmpeg")


def detect_cuts(ff, video, threshold):
    p = subprocess.run([ff, "-hide_banner", "-i", video, "-filter:v",
                        f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [round(float(t), 3) for t in re.findall(r"pts_time:([0-9.]+)", p.stderr)]


def extract(ff, video, out, fps, width, start, end, times):
    os.makedirs(out, exist_ok=True)
    for old in glob.glob(os.path.join(out, "f_*.jpg")):
        os.remove(old)
    frames = []
    if times:
        for i, t in enumerate(times):
            path = os.path.join(out, f"f_{i:04d}.jpg")
            subprocess.run([ff, "-v", "error", "-y", "-ss", str(t), "-i", video, "-frames:v", "1",
                            "-vf", f"scale={width}:-2", "-q:v", "3", path], check=True)
            frames.append((t, path))
        return frames
    cmd = [ff, "-v", "error", "-y"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", video]
    if end is not None:
        cmd += ["-t", str(end - (start or 0))]
    cmd += ["-vf", f"fps={fps},scale={width}:-2", "-q:v", "3", os.path.join(out, "f_%04d.jpg")]
    subprocess.run(cmd, check=True)
    for i, path in enumerate(sorted(glob.glob(os.path.join(out, "f_*.jpg")))):
        frames.append((round((start or 0) + i / fps, 3), path))
    return frames


def sheets(frames, out, cols, per_sheet):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed: frames extracted, no contact sheets.")
        return []
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except Exception:
            font = ImageFont.load_default()
    made = []
    for s in range(0, len(frames), per_sheet):
        chunk = frames[s:s + per_sheet]
        imgs = [Image.open(p).convert("RGB") for _, p in chunk]
        w, h = imgs[0].size
        rows = (len(imgs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w + (cols + 1) * 4, rows * h + (rows + 1) * 4), (20, 20, 20))
        d = ImageDraw.Draw(sheet)
        for i, ((t, _), im) in enumerate(zip(chunk, imgs)):
            x, y = 4 + (i % cols) * (w + 4), 4 + (i // cols) * (h + 4)
            sheet.paste(im, (x, y))
            label = f"{t:.2f}s"
            d.rectangle([x, y, x + 8 + 11 * len(label), y + 26], fill=(0, 0, 0))
            d.text((x + 4, y + 3), label, fill=(255, 230, 0), font=font)
        path = os.path.join(out, f"sheet_{s // per_sheet + 1:02d}_{chunk[0][0]:.2f}-{chunk[-1][0]:.2f}s.jpg")
        sheet.save(path, quality=85)
        made.append(path)
    return made


def main():
    ap = argparse.ArgumentParser(description="Frames, contact sheets and cut detection for a video.")
    ap.add_argument("video")
    ap.add_argument("--out", help="output folder (default: <video name>_frames next to this script's cwd)")
    ap.add_argument("--fps", type=float, default=4.0)
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--times", help="comma-separated timestamps instead of a fixed fps")
    ap.add_argument("--width", type=int, default=480, help="frame width in pixels")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--per-sheet", type=int, default=16)
    ap.add_argument("--cuts", action="store_true", help="also detect likely hard cuts")
    ap.add_argument("--cuts-only", action="store_true", help="only detect cuts, extract no frames")
    ap.add_argument("--cut-threshold", type=float, default=0.3)
    args = ap.parse_args()

    ff = find_ffmpeg()
    stem = os.path.splitext(os.path.basename(args.video))[0]
    out = args.out or os.path.join(os.getcwd(), f"{stem}_frames")
    result = {"video": os.path.abspath(args.video), "out": out}
    if args.cuts or args.cuts_only:
        result["cuts_s"] = detect_cuts(ff, args.video, args.cut_threshold)
        print("Likely cuts (s):", ", ".join(f"{t:.2f}" for t in result["cuts_s"]) or "none found")
        print("Note: fast whips, flashes and impact frames can register as cuts; check them on the sheets.")
    times = [float(t) for t in args.times.split(",")] if args.times else None
    if not args.cuts_only:
        frames = extract(ff, args.video, out, args.fps, args.width, args.start, args.end, times)
        result["frames"] = len(frames)
        result["sheets"] = sheets(frames, out, args.cols, args.per_sheet)
        print(f"{len(frames)} frames -> {out}")
        for s in result["sheets"]:
            print("sheet:", s)
    with open(os.path.join(out if os.path.isdir(out) else os.getcwd(), f"{stem}_frames.json"), "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
