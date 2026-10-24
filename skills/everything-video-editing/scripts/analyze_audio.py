"""Audio timing helpers for montages and highlight reels.

  python analyze_audio.py beats  music.mp3 [--every 2] [--out beats.json]
      tempo + beat times (+ downbeats every N beats) to cut clips on the beat
  python analyze_audio.py energy video.mp4 [--top 8] [--min-gap 6]
      loudest moments (cheering, laughter, action) as highlight candidates
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import vtools as V


def decode(path, sr=22050):
    import numpy as np
    raw = subprocess.run([V.need("ffmpeg"), "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32), sr


def beats(path, every=1):
    y, sr = decode(path)
    try:
        import librosa
        tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
        times = librosa.frames_to_time(frames, sr=sr).tolist()
        tempo = float(tempo if not hasattr(tempo, "__len__") else tempo[0])
    except ImportError:
        sys.exit("[eve] beat detection needs librosa: pip install librosa")
    return {"tempo": round(tempo, 1), "beats": [round(t, 3) for t in times],
            "cuts": [round(t, 3) for t in times[::max(1, every)]]}


def energy(path, top=8, min_gap=6.0):
    r = V.run([V.need("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
               "ebur128=framelog=verbose", "-f", "null", "-"], capture=True, check=False)
    pts = [(float(t), float(m)) for t, m in re.findall(r"t:\s*([\d.]+)\s+.*?M:\s*(-?[\d.]+)", r.stderr or "")]
    pts = [(t, m) for t, m in pts if m > -70]
    if not pts:
        return []
    ranked = sorted(pts, key=lambda x: -x[1])
    picked = []
    for t, m in ranked:
        if all(abs(t - p[0]) >= min_gap for p in picked):
            picked.append((t, m))
        if len(picked) >= top:
            break
    return [{"t": round(t, 2), "lufs_m": m} for t, m in sorted(picked)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["beats", "energy"])
    ap.add_argument("src")
    ap.add_argument("--every", type=int, default=1, help="cut every N beats")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--min-gap", type=float, default=6.0)
    ap.add_argument("--out")
    a = ap.parse_args()
    res = beats(a.src, a.every) if a.mode == "beats" else {"peaks": energy(a.src, a.top, a.min_gap)}
    txt = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
        summary = {k: (v if not isinstance(v, list) else f"{len(v)} items") for k, v in res.items()}
        print(json.dumps({"out": a.out, **summary}))
    else:
        print(txt)


if __name__ == "__main__":
    main()
