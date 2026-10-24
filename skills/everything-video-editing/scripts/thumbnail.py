"""Make a click-worthy thumbnail from a video.

  python thumbnail.py video.mp4 --text "I QUIT MY JOB" --out thumb.jpg
         [--t 12.5 | --t auto] [--size 1280x720] [--grade vibrant] [--accent "#FFD400"]
         [--sub "small second line"] [--pos left|right|center|bottom]

--platform youtube|instagram_reels|facebook_feed|tiktok ... picks the right size
(IG Reels cover: 1080x1920, keep text in the centre 1080x1440 for the profile grid).
--t auto picks the sharpest frame with a clear face (OpenCV) from ~40 candidates.
Text uses the bundled fonts through libass, so Bangla works too.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import vtools as V
from captions import AssDoc, ass_color, esc, pick_font
from render import grade_filters
import platforms as PF


def best_frame(src: str, work: Path, n=40):
    dur = V.media_info(src)["duration"]
    cv2, casc = V.face_cascade()
    if casc is None:
        return dur * 0.33
    best, best_t = -1.0, dur * 0.33
    for k in range(n):
        t = dur * (0.05 + 0.9 * k / max(1, n - 1))
        img = work / "_cand.jpg"
        subprocess.run([V.need("ffmpeg"), "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src,
                        "-frames:v", "1", "-vf", "scale=640:-2", str(img)], check=False)
        fr = cv2.imread(str(img))
        if fr is None:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        sharp = cv2.Laplacian(g, cv2.CV_64F).var()
        faces = casc.detectMultiScale(g, 1.1, 5, minSize=(50, 50))
        face = max((w * h for x, y, w, h in faces), default=0) / (g.shape[0] * g.shape[1])
        bright = g.mean() / 255
        score = sharp * (1 + 6 * min(face, 0.25)) * (0.4 + min(bright, 0.6))
        if score > best:
            best, best_t = score, t
    return best_t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--text", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--t", default="auto")
    ap.add_argument("--size", default=None, help="default 1280x720, or the platform's thumbnail/cover size")
    ap.add_argument("--platform", help="youtube, instagram_reels, facebook_feed ... sets the size")
    ap.add_argument("--grade", default="vibrant")
    ap.add_argument("--accent", default="#FFD400")
    ap.add_argument("--pos", default="left", choices=["left", "right", "center", "bottom"])
    a = ap.parse_args()
    src = str(Path(a.src).resolve())
    out = Path(a.out).resolve()
    work = V.ensure_dir(out.parent / ".eve_work")
    V.copy_assets_to(work)
    t = best_frame(src, work) if a.t == "auto" else float(a.t)
    plat = PF.get(a.platform)
    size = a.size or (f"{plat['thumb'][0]}x{plat['thumb'][1]}" if plat else "1280x720")
    a.size = size
    W, H = map(int, size.lower().split("x"))
    vf = [f"scale={W}:{H}:force_original_aspect_ratio=increase", f"crop={W}:{H}"]
    vf += grade_filters(a.grade, work, lambda p: p)
    if a.text:
        doc = AssDoc(W, H)
        font = pick_font(a.text, "Anton")
        base = H if W >= H else W * 0.9
        size = int(base * (0.16 if len(a.text) < 14 else 0.12))
        x, al = {"left": (int(W * 0.05), 4), "right": (int(W * 0.95), 6), "center": (W // 2, 5),
                 "bottom": (W // 2, 2)}[a.pos]
        y = H // 2 if a.pos != "bottom" else int(H * 0.93)
        doc.style("Big", font, size, "#FFFFFF", "#000000", max(4, size // 11), size // 18, bold=False, align=al)
        words = a.text.split()
        body = " ".join(esc(w) if i != len(words) - 1 else f"{{\\1c{ass_color(a.accent)}}}{esc(w)}"
                        for i, w in enumerate(words))
        if a.sub:
            body += f"\\N{{\\fs{int(size * 0.38)}\\1c&HFFFFFF&}}{esc(a.sub)}"
        if a.pos in ("left", "right"):
            doc.events.append(f"Dialogue: 0,0:00:00.00,0:00:10.00,Big,,0,0,0,,{{\\pos({x},{y})\\q1}}{body}")
        else:
            doc.events.append(f"Dialogue: 0,0:00:00.00,0:00:10.00,Big,,0,0,0,,{{\\pos({x},{y})}}{body}")
        doc.write(work / "thumb.ass")
        vf.append("ass=filename=thumb.ass:fontsdir=fonts:shaping=complex")
    V.ffmpeg(["-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", "-vf", ",".join(vf), "-q:v", "2", str(out)], cwd=work)
    print(json.dumps({"out": str(out), "t": round(t, 2), "size": a.size}))


if __name__ == "__main__":
    main()
