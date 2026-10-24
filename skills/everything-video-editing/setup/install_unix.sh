#!/usr/bin/env bash
# Everything-videoEditing installer for Linux / macOS (no root needed).
#   bash install_unix.sh [ROOT]        default ROOT=~/.everything-video
# Creates a Python 3.11 env (via uv) with Whisper, Demucs, CLAP, OpenCV, librosa and
# Blender as the `bpy` module. FFmpeg comes from the system (apt/brew) when present,
# otherwise a static build from PyPI (imageio-ffmpeg; no libass captions there).
set -u
ROOT="${1:-$HOME/.everything-video}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$ROOT/models"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$ROOT/install.log"; }

if ! command -v uv >/dev/null; then
  python3 -m pip install --user -q uv 2>/dev/null || python3 -m pip install --break-system-packages -q uv
  export PATH="$HOME/.local/bin:$PATH"
fi
[ -x "$ROOT/env/bin/python" ] || uv venv --python 3.11 "$ROOT/env" >>"$ROOT/install.log" 2>&1
PY="$ROOT/env/bin/python"
log "python: $($PY --version 2>&1)"

if [ "$(uname)" = "Linux" ]; then IDX="--index-url https://download.pytorch.org/whl/cpu"; else IDX=""; fi
$PY -c "import torch" 2>/dev/null || uv pip install --python "$PY" -q torch==2.6.0 torchaudio==2.6.0 $IDX >>"$ROOT/install.log" 2>&1 \
  || uv pip install --python "$PY" -q torch==2.6.0 torchaudio==2.6.0 >>"$ROOT/install.log" 2>&1
log "pip: whisper demucs clap opencv librosa"
uv pip install --python "$PY" -q demucs openai-whisper faster-whisper "transformers>=4.40,<5" librosa soundfile \
  "opencv-python-headless<5" pillow numpy edge-tts >>"$ROOT/install.log" 2>&1
log "pip: bpy (Blender as a module)"
uv pip install --python "$PY" -q "bpy>=4.5,<4.6" >>"$ROOT/install.log" 2>&1 || log "bpy not available here (3D titles disabled)"

FF="$(command -v ffmpeg || true)"; FP="$(command -v ffprobe || true)"
if [ -z "$FF" ]; then
  if command -v brew >/dev/null; then brew install ffmpeg >/dev/null && FF="$(command -v ffmpeg)" && FP="$(command -v ffprobe)"; fi
fi
BL="$(command -v blender || true)"
cat > "$ROOT/config.json" <<EOF
{"root": "$ROOT", "python": "$PY", "ffmpeg": "${FF}", "ffprobe": "${FP}", "blender": "${BL}",
 "hf_home": "$ROOT/models/hf", "torch_home": "$ROOT/models/torch", "whisper_dir": "$ROOT/models/whisper", "device": "cpu"}
EOF
mkdir -p "$HOME/.everything-video"; [ "$ROOT/config.json" -ef "$HOME/.everything-video/config.json" ] || cp "$ROOT/config.json" "$HOME/.everything-video/config.json"
log "models (needs huggingface.co, dl.fbaipublicfiles.com)"
HF_HOME="$ROOT/models/hf" TORCH_HOME="$ROOT/models/torch" $PY "$HERE/predownload.py" --whisper small 2>&1 | tee -a "$ROOT/install.log"
log "ALL DONE. Check: $PY $(dirname "$HERE")/scripts/doctor.py"
