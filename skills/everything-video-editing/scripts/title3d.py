"""Animated 3D title with Blender -> transparent .mov to overlay in plan.json.

  python title3d.py --text "EPISODE 1" --out title.mov [--size 1920x1080] [--dur 3]
         [--style glossy|metal|neon|clay|glass] [--anim pop|spin|rise|float]
         [--color "#FFD400"] [--bg transparent|#101014] [--font path.ttf] [--engine auto|eevee|cycles]

Latin text only: Blender does not shape Bangla/Hindi/Arabic, so use an ASS text
overlay (style "title") or a Remotion graphic for those scripts.
Then add to plan.json overlays: {"type": "video", "src": "title.mov", "pos": "full", "start": 0}
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import vtools as V

HERE = Path(__file__).resolve().parent
NON_LATIN = re.compile(r"[ऀ-෿؀-ۿ]")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--dur", type=float, default=3.0)
    ap.add_argument("--style", default="glossy", choices=["glossy", "metal", "neon", "clay", "glass"])
    ap.add_argument("--anim", default="pop", choices=["pop", "spin", "rise", "float"])
    ap.add_argument("--color", default="#FFD400")
    ap.add_argument("--bg", default="transparent")
    ap.add_argument("--font", default=str(V.ASSETS / "fonts" / "Anton-Regular.ttf"))
    ap.add_argument("--engine", default="auto", choices=["auto", "eevee", "cycles"])
    ap.add_argument("--samples", type=int, default=0)
    a = ap.parse_args()
    if NON_LATIN.search(a.text):
        sys.exit("[eve] Blender can't shape this script. Use an ASS 'title' overlay or Remotion instead.")
    w, h = map(int, a.size.lower().split("x"))
    out = Path(a.out).resolve()
    frames = V.ensure_dir(out.parent / ".eve_work" / f"blender_{out.stem}")
    for f in frames.glob("f_*.png"):
        f.unlink()
    args = {"text": a.text, "w": w, "h": h, "fps": a.fps, "dur": a.dur, "style": a.style, "anim": a.anim,
            "color": a.color, "bg": a.bg, "font": a.font, "frames_dir": str(frames)}
    blender = V.tool("blender")
    script = str(HERE / "blender_title.py")
    engines = ["eevee", "cycles"] if a.engine == "auto" else [a.engine]
    ok = False
    for eng in engines:
        args["engine"] = eng
        args["samples"] = a.samples or (32 if eng == "eevee" else 40)
        env = dict(os.environ, EVE_TITLE_ARGS=json.dumps(args))
        if blender:
            cmd = [blender, "-b", "--factory-startup", "-P", script]
        else:
            cmd = [V.py_exe(), "-c", f"import runpy; runpy.run_path(r'{script}')"]
        print(f"[eve] blender ({eng}) rendering {a.text!r} ...", file=sys.stderr, flush=True)
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        n = len(list(frames.glob("f_*.png")))
        if "EVE DONE" in (r.stdout or "") and n:
            ok = True
            break
        tail = "\n".join(((r.stdout or "") + (r.stderr or "")).splitlines()[-15:])
        print(f"[eve] {eng} failed ({n} frames):\n{tail}", file=sys.stderr)
    if not ok:
        sys.exit("[eve] Blender render failed. Is Blender installed? (scripts/doctor.py)")
    first = sorted(frames.glob("f_*.png"))[0].stem.split("_")[1]
    pattern = f"f_%0{len(first)}d.png"
    V.ffmpeg(["-framerate", str(a.fps), "-start_number", str(int(first)), "-i", pattern,
              "-c:v", "png", "-pix_fmt", "rgba", str(out)], cwd=frames)
    shutil.rmtree(frames, ignore_errors=True)
    print(json.dumps({"out": str(out), "frames": int(round(a.dur * a.fps)), "size": a.size}))


if __name__ == "__main__":
    main()
