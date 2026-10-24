"""Make a jump-cut clip list: remove silences, filler words and retakes.

  python cutlist.py video.mp4 --out clips.json [--words words.json] [--min-silence 0.45]
                    [--pad 0.08] [--noise -35] [--no-fillers] [--remove "0:12-0:19,1:03-1:07"]

With --words (from transcribe.py) cuts follow speech exactly and drop um/uh.
Without it, ffmpeg silencedetect is used. Paste the "clips" array into plan.json.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import vtools as V
from captions import FILLERS


def parse_ts(s: str) -> float:
    parts = [float(p) for p in s.strip().split(":")]
    t = 0.0
    for p in parts:
        t = t * 60 + p
    return t


def silences(src: str, noise_db: float, min_d: float):
    res = V.run([V.need("ffmpeg"), "-hide_banner", "-nostats", "-i", src, "-vn", "-af",
                 f"silencedetect=noise={noise_db}dB:d={min_d}", "-f", "null", "-"], capture=True, check=False)
    out, start = [], None
    for line in (res.stderr or "").splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            start = float(m.group(1))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            out.append((start, float(m.group(1))))
            start = None
    if start is not None:
        out.append((start, 1e9))
    return out


def merge(spans, gap=0.0):
    spans = sorted(spans)
    out = []
    for s, e in spans:
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--words")
    ap.add_argument("--min-silence", type=float, default=0.45, help="pauses longer than this are cut")
    ap.add_argument("--pad", type=float, default=0.08, help="breathing room kept around speech")
    ap.add_argument("--noise", type=float, default=-35, help="silence threshold dB (no --words)")
    ap.add_argument("--no-fillers", action="store_true", help="keep filler words")
    ap.add_argument("--remove", help="extra ranges to cut, e.g. '0:12-0:19,63-67.5'")
    ap.add_argument("--min-clip", type=float, default=0.25)
    a = ap.parse_args()
    src = str(Path(a.src).resolve())
    dur = V.media_info(src)["duration"]
    if a.words:
        data = json.loads(Path(a.words).read_text(encoding="utf-8"))
        words = data["words"] if isinstance(data, dict) else data
        keep = []
        for w in words:
            tok = re.sub(r"[^\wঀ-৿']", "", w["word"].lower())
            if not a.no_fillers and tok in FILLERS:
                continue
            keep.append((w["start"] - a.pad, w["end"] + a.pad))
        keep = merge(keep, gap=a.min_silence)
    else:
        sil = silences(src, a.noise, a.min_silence)
        keep, t = [], 0.0
        for s, e in sil:
            if s - t > 0:
                keep.append([max(0, t - a.pad), min(dur, s + a.pad)])
            t = e
        if t < dur:
            keep.append([max(0, t - a.pad), dur])
        keep = merge(keep)
    if a.remove:
        for r in a.remove.split(","):
            x, y = (parse_ts(p) for p in r.split("-"))
            new = []
            for s, e in keep:
                if e <= x or s >= y:
                    new.append([s, e])
                    continue
                if s < x:
                    new.append([s, x])
                if e > y:
                    new.append([y, e])
            keep = new
    clips = [{"src": src, "in": round(max(0, s), 3), "out": round(min(dur, e), 3)}
             for s, e in keep if min(dur, e) - max(0, s) >= a.min_clip]
    kept = sum(c["out"] - c["in"] for c in clips)
    Path(a.out).write_text(json.dumps({"clips": clips}, indent=1), encoding="utf-8")
    print(json.dumps({"out": a.out, "clips": len(clips), "original_s": round(dur, 2),
                      "kept_s": round(kept, 2), "removed_s": round(dur - kept, 2)}))


if __name__ == "__main__":
    main()
