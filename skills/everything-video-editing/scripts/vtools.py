"""Shared helpers for the Everything-videoEditing scripts.

Finds the tools (ffmpeg, ffprobe, blender, python env) from a config file,
runs commands with readable errors, and probes media files.
Works on Windows, macOS and Linux.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
IS_WIN = platform.system() == "Windows"


# ---------------------------------------------------------------- config
def _config_candidates():
    env = os.environ.get("EVE_CONFIG")
    if env:
        yield Path(env)
    yield Path.home() / ".everything-video" / "config.json"
    if IS_WIN:
        yield Path(r"D:\video-tools\config.json")
        yield Path(r"C:\video-tools\config.json")


def load_config() -> dict:
    for p in _config_candidates():
        try:
            if p.is_file():
                txt = p.read_text(encoding="utf-8-sig")
                cfg = json.loads(txt)
                cfg["_path"] = str(p)
                return cfg
        except Exception:
            continue
    return {}


CFG = load_config()


def tool(name: str) -> str | None:
    """Absolute path of ffmpeg / ffprobe / blender / node, or None."""
    p = CFG.get(name)
    if p and Path(p).exists():
        return str(p)
    found = shutil.which(name)
    if found:
        return found
    if name == "blender":
        for c in (r"C:\Program Files\Blender Foundation", "/Applications/Blender.app/Contents/MacOS"):
            cp = Path(c)
            if cp.exists():
                hits = sorted(cp.rglob("blender.exe" if IS_WIN else "Blender"))
                if hits:
                    return str(hits[-1])
    return None


def need(name: str) -> str:
    p = tool(name)
    if not p:
        sys.exit(f"[eve] '{name}' not found. Run scripts/doctor.py, or install it (see setup/).")
    return p


FFMPEG = tool("ffmpeg")
FFPROBE = tool("ffprobe")


def setup_model_env():
    """Point model caches at the configured folder (keeps C: free on Windows)."""
    if CFG.get("hf_home"):
        os.environ.setdefault("HF_HOME", CFG["hf_home"])
    if CFG.get("torch_home"):
        os.environ.setdefault("TORCH_HOME", CFG["torch_home"])
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


# ---------------------------------------------------------------- running
def run(cmd: list, cwd=None, quiet: bool = True, check: bool = True, capture: bool = False):
    """Run a command. On failure print the tail of stderr and exit."""
    cmd = [str(c) for c in cmd]
    short = " ".join(Path(cmd[0]).name if i == 0 else c for i, c in enumerate(cmd))
    if len(short) > 400:
        short = short[:400] + " ..."
    if not Path(cmd[0]).name.startswith("ffprobe"):
        print(f"[eve] $ {short}", file=sys.stderr, flush=True)
    if cmd and Path(cmd[0]).name.startswith("ffmpeg") and quiet and not capture:
        cmd = [cmd[0], "-hide_banner", "-loglevel", "error", "-stats"] + cmd[1:]
    res = subprocess.run(
        cmd, cwd=cwd, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,
    )
    if check and res.returncode != 0:
        tail = "\n".join((res.stderr or "").strip().splitlines()[-40:])
        sys.stderr.write(f"[eve] command failed ({res.returncode}):\n{tail}\n")
        raise SystemExit(res.returncode)
    return res


def ffmpeg(args: list, cwd=None, quiet=True):
    return run([need("ffmpeg"), "-y"] + list(args), cwd=cwd, quiet=quiet)


# ---------------------------------------------------------------- probing
def ffprobe_json(path) -> dict:
    res = run([need("ffprobe"), "-v", "error", "-print_format", "json",
               "-show_format", "-show_streams", str(path)], capture=True)
    return json.loads(res.stdout or "{}")


def _fps(s: str | None) -> float:
    if not s or s in ("0/0",):
        return 0.0
    if "/" in s:
        a, b = s.split("/")
        return float(a) / float(b) if float(b) else 0.0
    return float(s)


IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wma"}


def media_info(path) -> dict:
    path = Path(path)
    j = ffprobe_json(path)
    info = {"path": str(path), "duration": 0.0, "has_video": False, "has_audio": False,
            "width": 0, "height": 0, "fps": 0.0, "rotation": 0, "is_image": path.suffix.lower() in IMAGE_EXT}
    try:
        info["duration"] = float(j.get("format", {}).get("duration") or 0)
    except ValueError:
        pass
    for s in j.get("streams", []):
        if s.get("codec_type") == "video" and not info["has_video"]:
            if s.get("disposition", {}).get("attached_pic"):
                continue
            info["has_video"] = True
            w, h = int(s.get("width", 0)), int(s.get("height", 0))
            rot = 0
            try:
                rot = int(s.get("tags", {}).get("rotate", 0))
            except ValueError:
                pass
            for sd in s.get("side_data_list", []) or []:
                if "rotation" in sd:
                    try:
                        rot = int(sd["rotation"])
                    except (TypeError, ValueError):
                        pass
            if abs(rot) % 180 == 90:
                w, h = h, w
            info.update(width=w, height=h, rotation=rot, vcodec=s.get("codec_name"),
                        fps=round(_fps(s.get("avg_frame_rate")) or _fps(s.get("r_frame_rate")), 3),
                        pix_fmt=s.get("pix_fmt"))
            if not info["duration"]:
                try:
                    info["duration"] = float(s.get("duration") or 0)
                except ValueError:
                    pass
        elif s.get("codec_type") == "audio" and not info["has_audio"]:
            info["has_audio"] = True
            info.update(acodec=s.get("codec_name"), sample_rate=int(s.get("sample_rate", 0) or 0),
                        channels=int(s.get("channels", 0) or 0))
    return info


# ---------------------------------------------------------------- misc
def even(n: float) -> int:
    n = int(round(n))
    return n if n % 2 == 0 else n + 1


def hash_obj(obj) -> str:
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]


def ensure_dir(p) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def copy_assets_to(workdir: Path):
    """Fonts and denoise model next to the ffmpeg cwd, so filters can use relative paths
    (Windows drive letters break ffmpeg filter arguments)."""
    fdst = ensure_dir(workdir / "fonts")
    for f in (ASSETS / "fonts").glob("*.ttf"):
        t = fdst / f.name
        if not t.exists():
            shutil.copy2(f, t)
    model = ASSETS / "denoise" / "std.rnnn"
    if model.exists() and not (workdir / "std.rnnn").exists():
        shutil.copy2(model, workdir / "std.rnnn")


_FF_MAJOR = None


def ffmpeg_major() -> int:
    global _FF_MAJOR
    if _FF_MAJOR is None:
        try:
            out = subprocess.run([need("ffmpeg"), "-version"], capture_output=True, text=True).stdout
            v = out.split("version", 1)[1].split()[0].lstrip("n")
            _FF_MAJOR = int(v.split(".")[0].split("-")[0])
        except Exception:
            _FF_MAJOR = 6
    return _FF_MAJOR


def filter_script_args(graph: str, workdir: Path, name: str) -> list:
    """Pass a (possibly huge) filtergraph through a file. Avoids the Windows
    command-line length limit. The path is relative: ffmpeg runs with cwd=workdir."""
    (Path(workdir) / name).write_text(graph, encoding="utf-8")
    if ffmpeg_major() >= 7:
        return ["-/filter_complex", name]
    return ["-filter_complex_script", name]


def has_filter(name: str) -> bool:
    if not FFMPEG:
        return False
    res = subprocess.run([FFMPEG, "-hide_banner", "-filters"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    return any(line.split()[1:2] == [name] for line in res.stdout.splitlines() if len(line.split()) > 1)


_CASCADE = None


def face_cascade():
    """(cv2, frontal-face Haar cascade) or (None, None). OpenCV 5 dropped the Haar API,
    so the installers pin opencv-python-headless<5."""
    global _CASCADE
    if _CASCADE is not None:
        return _CASCADE
    _CASCADE = (None, None)
    try:
        import cv2
        if hasattr(cv2, "CascadeClassifier"):
            _CASCADE = (cv2, cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml"))
        else:
            print("[eve] face detection off: OpenCV 5 has no Haar cascades. "
                  "Fix: pip install \"opencv-python-headless<5\"", file=sys.stderr)
    except Exception:
        pass
    return _CASCADE


def hex_to_rgb(c: str) -> tuple:
    c = c.strip().lstrip("#")
    named = {"white": "FFFFFF", "black": "000000", "yellow": "FFD400", "red": "FF3B30",
             "green": "34C759", "blue": "0A84FF", "orange": "FF9500", "pink": "FF2D92",
             "purple": "AF52DE", "cyan": "32D2FF", "gray": "8E8E93", "grey": "8E8E93"}
    c = named.get(c.lower(), c)
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def py_exe() -> str:
    """Python that has the ML packages (config env) or the current one."""
    p = CFG.get("python")
    if p and Path(p).exists():
        return p
    return sys.executable


if __name__ == "__main__":
    print(json.dumps({"config": CFG, "ffmpeg": FFMPEG, "ffprobe": FFPROBE,
                      "blender": tool("blender"), "python": py_exe()}, indent=2))
