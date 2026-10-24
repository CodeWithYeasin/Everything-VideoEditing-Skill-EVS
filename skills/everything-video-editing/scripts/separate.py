"""Split audio into stems with Demucs (Meta's source separation).

  python separate.py video_or_audio --out-dir stems [--stems 2|4|6] [--model htdemucs]

--stems 2 (default) -> vocals.wav + no_vocals.wav  (clean voice / remove music, karaoke)
--stems 4           -> vocals, drums, bass, other   (remix, beat-only)
--stems 6           -> htdemucs_6s adds guitar, piano
Uses the CPU unless a CUDA GPU with enough memory is present. ~1-2x real time on CPU.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import vtools as V


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--stems", type=int, default=2, choices=[2, 4, 6])
    ap.add_argument("--model")
    ap.add_argument("--segment", type=int, default=7, help="smaller uses less RAM")
    a = ap.parse_args()
    V.setup_model_env()
    src = Path(a.src).resolve()
    out = V.ensure_dir(Path(a.out_dir).resolve())
    wav = out / "_input.wav"
    V.ffmpeg(["-i", str(src), "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(wav)])
    model = a.model or ("htdemucs_6s" if a.stems == 6 else "htdemucs")
    device = "cpu"
    try:
        import torch
        if V.CFG.get("device", "cpu") != "cpu" and torch.cuda.is_available() \
                and torch.cuda.get_device_properties(0).total_memory > 3.5e9:
            device = "cuda"
    except ImportError:
        sys.exit("[eve] demucs/torch not installed. Run setup, or: pip install demucs")
    args = [V.py_exe(), "-m", "demucs", "-n", model, "-d", device, "--segment", str(a.segment),
            "-o", str(out / "_demucs"), str(wav)]
    if a.stems == 2:
        args[3:3] = ["--two-stems", "vocals"]
    V.run(args, quiet=False)
    produced = list((out / "_demucs" / model / "_input").glob("*.wav"))
    if not produced:
        sys.exit("[eve] demucs produced no files")
    res = {}
    for f in produced:
        dst = out / f.name
        shutil.move(str(f), dst)
        res[f.stem] = str(dst)
    shutil.rmtree(out / "_demucs", ignore_errors=True)
    wav.unlink(missing_ok=True)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
