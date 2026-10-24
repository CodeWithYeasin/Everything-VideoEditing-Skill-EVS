"""Check text/logo placement against a platform's UI: draws the unsafe areas (red) over
frames of the video so you can SEE whether captions, titles or logos would be covered by
buttons, captions or the profile bar.

  python safezone.py video.mp4 --platform instagram_reels [--times 1.5,4,8] [--out check.jpg]

Open the output image with the Read tool. Red = covered by app UI; keep text in the clear area.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import vtools as V
import platforms as PF


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--platform", required=True)
    ap.add_argument("--times", help="comma list of seconds (default: 4 evenly spaced)")
    ap.add_argument("--out")
    a = ap.parse_args()
    src = Path(a.src).resolve()
    p = PF.get(a.platform)
    if not p:
        raise SystemExit(f"[eve] unknown platform. Known: {', '.join(PF.PLATFORMS)}")
    info = V.media_info(src)
    W, H = info["width"], info["height"]
    times = [float(x) for x in a.times.split(",")] if a.times else [info["duration"] * k / 5 for k in (1, 2, 3, 4)]
    t, b, l, r = p["safe"]
    boxes = [f"drawbox=x=0:y=0:w=iw:h={int(t * H)}:color=red@0.35:t=fill",
             f"drawbox=x=0:y={int((1 - b) * H)}:w=iw:h={int(b * H)}:color=red@0.35:t=fill",
             f"drawbox=x=0:y=0:w={int(l * W)}:h=ih:color=red@0.35:t=fill",
             f"drawbox=x={int((1 - r) * W)}:y=0:w={int(r * W)}:h=ih:color=red@0.35:t=fill",
             f"drawbox=x={int(l * W)}:y={int(t * H)}:w={int((1 - l - r) * W)}:h={int((1 - t - b) * H)}:color=lime@0.9:t=4"]
    out = Path(a.out).resolve() if a.out else src.with_name(src.stem + f"_safe_{p['name']}.jpg")
    work = V.ensure_dir(out.parent / ".eve_work")
    tiles = []
    for i, tt in enumerate(times):
        f = work / f"_sz_{i}.jpg"
        V.ffmpeg(["-ss", f"{tt:.2f}", "-i", str(src), "-frames:v", "1", "-vf", ",".join(boxes) + ",scale=-2:720",
                  str(f)])
        tiles.append(f)
    args = []
    for f in tiles:
        args += ["-i", str(f)]
    graph = "".join(f"[{i}]" for i in range(len(tiles))) + f"hstack={len(tiles)}" if len(tiles) > 1 else "[0]null"
    V.ffmpeg(args + ["-filter_complex", graph, "-frames:v", "1", str(out)])
    for f in tiles:
        f.unlink(missing_ok=True)
    print(json.dumps({"out": str(out), "platform": p["label"], "times": [round(x, 2) for x in times],
                      "safe_px": PF.safe_px(p, W, H)}))


if __name__ == "__main__":
    main()
