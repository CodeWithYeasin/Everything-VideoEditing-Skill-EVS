"""Check which editing powers are available here, and how to get the missing ones.

  python doctor.py          # human summary + JSON
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys

import vtools as V


def py_has(mod: str) -> bool:
    exe = V.py_exe()
    if exe == sys.executable:
        return importlib.util.find_spec(mod) is not None
    r = subprocess.run([exe, "-c", f"import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('{mod}') else 1)"],
                       capture_output=True)
    return r.returncode == 0


def face_ok() -> bool:
    exe = V.py_exe()
    r = subprocess.run([exe, "-c", "import cv2,sys; sys.exit(0 if hasattr(cv2,'CascadeClassifier') else 1)"],
                       capture_output=True)
    return r.returncode == 0


def main():
    rep = {"config": V.CFG.get("_path"), "python": V.py_exe(), "ffmpeg": V.FFMPEG, "blender": V.tool("blender"),
           "node": shutil.which("node"), "npm": shutil.which("npm")}
    if V.FFMPEG:
        out = subprocess.run([V.FFMPEG, "-version"], capture_output=True, text=True).stdout.splitlines()[0]
        rep["ffmpeg_version"] = out
        rep["ffmpeg_filters"] = {f: V.has_filter(f) for f in
                                 ("ass", "arnndn", "vidstabdetect", "lut3d", "xfade", "loudnorm", "sidechaincompress",
                                  "zoompan", "chromakey", "cas", "minterpolate")}
    mods = {"faster_whisper": "Whisper (fast)", "whisper": "Whisper (openai)", "demucs": "Demucs stems",
            "transformers": "CLAP music search", "torch": "PyTorch", "librosa": "beat detection",
            "cv2": "face-aware reframing / thumbnails", "numpy": "SFX synth", "edge_tts": "neural voice-over"}
    rep["python_packages"] = {m: py_has(m) for m in mods}
    caps = {
        "cut/trim/speed/transitions/reframe/grade/overlays/captions burn": bool(V.FFMPEG),
        "auto transcription + captions + filler/silence cuts": rep["python_packages"]["faster_whisper"] or rep["python_packages"]["whisper"],
        "voice isolation / music removal (Demucs)": rep["python_packages"]["demucs"],
        "describe-to-find music & SFX (CLAP)": rep["python_packages"]["transformers"] and rep["python_packages"]["torch"],
        "3D titles (Blender)": bool(rep["blender"]),
        "motion graphics (Remotion)": bool(rep["node"]),
        "beat-synced montage": rep["python_packages"]["librosa"],
        "voice-over TTS (neural voices)": rep["python_packages"]["edge_tts"],
        "face tracking (OpenCV < 5)": face_ok(),
    }
    rep["capabilities"] = caps
    missing = [k for k, v in caps.items() if not v]
    rep["fix"] = ("All set." if not missing else
                  "Missing: " + "; ".join(missing) + ". Run setup/install_windows.ps1 (Windows) or "
                  "setup/install_unix.sh (Linux/macOS). Model downloads need access to huggingface.co, "
                  "dl.fbaipublicfiles.com and openaipublic.azureedge.net.")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
