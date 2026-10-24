"""Look at a video before editing: facts, loudness, pauses, scene cuts, colour
stats and a contact sheet image (open it with the Read tool to actually see the video).

  python probe.py video.mp4 [--out-dir probe_out] [--frames 12] [--no-scenes]

Prints JSON. Colour hints tell you whether the footage is dark, flat, desaturated
or tinted, which decides the grade. Loudness is integrated LUFS (target -14 for
YouTube/Reels/TikTok).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

import vtools as V


def loudness(src):
    r = V.run([V.need("ffmpeg"), "-hide_banner", "-nostats", "-i", src, "-vn", "-af",
               "ebur128=framelog=quiet:peak=true", "-f", "null", "-"], capture=True, check=False)
    txt = r.stderr or ""
    def grab(key):
        m = re.findall(rf"{key}:\s+(-?[\d.]+)", txt)
        return float(m[-1]) if m else None
    return {"lufs": grab("I"), "lra": grab("LRA"), "true_peak_dbfs": grab("Peak")}


def silences(src, noise=-35, d=0.5):
    r = V.run([V.need("ffmpeg"), "-hide_banner", "-nostats", "-i", src, "-vn", "-af",
               f"silencedetect=noise={noise}dB:d={d}", "-f", "null", "-"], capture=True, check=False)
    st, out = None, []
    for line in (r.stderr or "").splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            st = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and st is not None:
            out.append([round(st, 2), round(float(m.group(1)), 2)])
            st = None
    return out


def scenes(src, thr=0.32, scale=320):
    r = V.run([V.need("ffmpeg"), "-hide_banner", "-nostats", "-i", src, "-an", "-vf",
               f"scale={scale}:-2,select='gt(scene,{thr})',showinfo", "-f", "null", "-"], capture=True, check=False)
    return [round(float(x), 2) for x in re.findall(r"pts_time:([\d.]+)", r.stderr or "")]


def color_stats(src, dur, n=10):
    step = max(dur / n, 0.5)
    r = V.run([V.need("ffmpeg"), "-hide_banner", "-nostats", "-i", src, "-an", "-vf",
               f"fps=1/{step:.3f},scale=320:-2,signalstats,metadata=print:file=-", "-f", "null", "-"],
              capture=True, check=False)
    vals = {}
    for k, v in re.findall(r"lavfi\.signalstats\.(\w+)=([\d.]+)", r.stdout or ""):
        vals.setdefault(k, []).append(float(v))
    med = {k: round(statistics.median(v), 1) for k, v in vals.items() if v}
    if not med:
        return {}
    bit = 1023 if med.get("YMAX", 0) > 255 else 255
    s = {k: med.get(k) for k in ("YAVG", "YLOW", "YHIGH", "SATAVG", "UAVG", "VAVG")}
    hints = []
    y = med.get("YAVG", 128) / bit
    if y < 0.30:
        hints.append("dark: raise brightness/gamma or use 'auto'/'bright'")
    elif y > 0.70:
        hints.append("bright/overexposed: lower brightness slightly")
    rng = (med.get("YHIGH", bit) - med.get("YLOW", 0)) / bit
    if rng < 0.55:
        hints.append("flat/low contrast (log or hazy): contrast 1.1-1.25 or 'auto'")
    sat = med.get("SATAVG", 40) / (bit / 255)
    if sat < 18:
        hints.append("desaturated: saturation 1.15-1.3 or 'vibrant'")
    elif sat > 70:
        hints.append("very saturated: keep saturation <= 1.0")
    u, v = med.get("UAVG", bit / 2) / bit, med.get("VAVG", bit / 2) / bit
    if v - u > 0.04:
        hints.append("warm/orange cast: temperature 7000-7800 to neutralise, or lean into 'golden'")
    elif u - v > 0.04:
        hints.append("cool/blue cast: temperature 5200-5800 to neutralise")
    s["hints"] = hints or ["balanced exposure and colour"]
    return s


def contact_sheet(src, dur, out_dir: Path, frames=12):
    V.copy_assets_to(out_dir)
    cols = 4 if frames > 6 else frames
    rows = -(-frames // cols)
    step = dur / frames
    sheet = out_dir / "contact_sheet.jpg"
    vf = (f"fps=1/{step:.4f},scale=480:-2,"
          f"drawtext=fontfile=fonts/Poppins-Bold.ttf:text='%{{pts\\:hms\\:{step / 2:.3f}}}':x=8:y=8:fontsize=22:"
          f"fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=6,tile={cols}x{rows}:padding=4:margin=4")
    V.ffmpeg(["-ss", f"{step / 2:.3f}", "-i", str(src), "-an", "-vf", vf, "-frames:v", "1", "-q:v", "3", sheet.name],
             cwd=out_dir)
    return str(sheet), [round(step / 2 + i * step, 2) for i in range(frames)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out-dir")
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--no-scenes", action="store_true")
    a = ap.parse_args()
    src = str(Path(a.src).resolve())
    info = V.media_info(src)
    out_dir = V.ensure_dir(Path(a.out_dir).resolve() if a.out_dir else Path(src).parent / ".eve_work" / ("probe_" + Path(src).stem))
    rep = {"info": info}
    if info["has_audio"]:
        rep["loudness"] = loudness(src)
        sil = silences(src)
        rep["silences"] = {"count": len(sil), "total_s": round(sum(e - s for s, e in sil if e < 1e8), 1),
                           "first_10": sil[:10]}
    if info["has_video"] and not info["is_image"]:
        if not a.no_scenes:
            sc = scenes(src)
            rep["scene_cuts"] = {"count": len(sc), "times": sc[:60]}
        rep["color"] = color_stats(src, info["duration"])
        sheet, times = contact_sheet(src, info["duration"], out_dir, a.frames)
        rep["contact_sheet"] = sheet
        rep["sheet_times"] = times
    print(json.dumps(rep, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
