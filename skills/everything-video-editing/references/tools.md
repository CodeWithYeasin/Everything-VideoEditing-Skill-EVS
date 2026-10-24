# Tool notes

## Install / layout
- Windows: `setup/install_windows.ps1 [-Root D:\video-tools] [-Gpu]` → FFmpeg 9 (gyan full build),
  Python 3.11 env (conda or uv), torch CPU, Whisper (faster + openai), Demucs, transformers
  (CLAP), OpenCV, librosa, Blender 4.5 LTS portable, models; writes
  `%USERPROFILE%\.everything-video\config.json`. `-Gpu` only for NVIDIA cards with ≥4 GB.
- Linux/macOS: `setup/install_unix.sh [root]` (uv venv, bpy module for Blender).
- `config.json` keys: root, python, ffmpeg, ffprobe, blender, hf_home, torch_home,
  whisper_dir, device (cpu|cuda), optional chrome (browser for Remotion).
  `EVE_CONFIG=<path>` overrides where it is read from.
- Remotion needs Node 18+; first render runs `npm install` in `<root>\remotion-graphics`
  and downloads Chrome Headless Shell (~100 MB) once.

## Whisper (transcribe.py)
- Engines: faster-whisper (CTranslate2 int8, default) → openai-whisper fallback.
- CPU speed (4 cores, int8): small ≈ 3-5× faster than real time, medium ≈ 1×, large-v3 ≈ 0.4×.
- `--keep-fillers` adds a prompt that makes Whisper write "um/uh" so cutlist can remove them.
- `--prompt "BRAC, Dhaka, xv6"` fixes spelling of names and terms.
- Bangla: use `medium` (small mis-hears a lot). Whisper writes Bangla in Bangla script.
- Translation: Whisper can only translate to English; for other directions translate the
  segments yourself and write an SRT (keep each segment's start/end).

## Demucs (separate.py)
- `htdemucs` 2-stem: vocals / no_vocals. 4-stem: vocals, drums, bass, other. 6-stem adds
  guitar, piano (`htdemucs_6s`).
- CPU ≈ 1-2× the audio length; `--segment 5` lowers RAM on 8 GB machines.
- Use for: removing copyrighted background music, cleaning voice under loud noise
  (better than RNNoise for music), karaoke/instrumental, remixing.

## CLAP (clap_rank.py)
- Model laion/clap-htsat-unfused (~600 MB). Ranks audio files against text like
  "tense cinematic drums", "soft acoustic guitar, happy", "cartoon boing".
- Scores are cosine similarities (~0.2-0.6); compare within one query, not across queries.
- Listen-free sanity check: `--tag file.mp3` lists the top zero-shot tags.

## FFmpeg notes (render.py)
- Filter paths: ffmpeg runs with cwd = `.eve_work`; fonts, LUTs, RNNoise model and ASS files
  are copied there and referenced by relative name (Windows drive letters break filters).
- Filtergraphs go through a script file (`-/filter_complex` on FFmpeg ≥7) to avoid the
  Windows command-line length limit.
- Text uses the `ass` filter with `shaping=complex` (HarfBuzz) - needed for Bangla.
- Encoding: libx264 veryfast crf 20 (good), slow crf 17 (best); AAC 192k; +faststart.
- vidstab two-pass when available, else deshake.

## Blender (title3d.py / blender_title.py)
- Styles: glossy, metal, neon (emission + glare), clay, glass. Anims: pop, spin, rise, float.
- EEVEE first (fast on any GPU with OpenGL 4.3), Cycles CPU fallback (slow: ~5-6 s/frame at
  960x540, 12 samples, 2 cores). Keep titles 2-3 s and 1080p or less on CPU.
- For custom 3D scenes write your own bpy script and run
  `<blender> -b --factory-startup -P script.py`; render PNG RGBA frames, encode with ffmpeg
  `-c:v png` (alpha) or `-c:v libx264` (opaque).

## Remotion (remotion_gfx.py)
- Template: graphics/remotion (React 19, Remotion 4). Props set width/height/fps/duration.
- Transparent → ProRes 4444 .mov (yuva444p10le); opaque bg → H.264 .mp4.
- Custom graphic: copy the template folder, add a component to src/comps.tsx and a
  `<Composition>` in src/Root.tsx, then `remotion_gfx.py MyComp --project <folder>`.
  Use `useCurrentFrame`, `spring`, `interpolate`; no CSS animations (frames render
  independently). If the official Remotion skill is installed, follow it for advanced work.
- Browser: Remotion downloads its own. Where blocked, set `EVE_BROWSER` or config `chrome`
  to a Chrome/Edge path; on Linux the script falls back to npm `@sparticuz/chromium`.

## TTS (tts.py)
- edge engine = Microsoft neural voices through the `edge-tts` package (needs internet).
  Word timings come back exactly, so VO captions are in sync. `--list bn` shows voices.
- sapi (Windows, offline, English only), say (macOS), espeak-ng (Linux, robotic), silent
  (timing guide only). For paid commercial use check the voice service's terms.

## OpenCV
Face detection uses Haar cascades, which OpenCV 5 removed: keep `opencv-python-headless<5`
(the installers pin it). Without it, reframing falls back to blurred fill and thumbnails to a
1/3 frame; scripts print a warning.

## Troubleshooting
| symptom | fix |
|---|---|
| `'ffmpeg' not found` | run the installer or set config.ffmpeg |
| captions show boxes/wrong Bangla letters | font missing → `setup/fetch_assets.py`; never use the `subtitles` filter for Bangla |
| render fails "No such filter: arnndn/vidstab" | older FFmpeg; set `voice.denoise: "fft"`, stabilise falls back automatically |
| A/V drift after speed changes | keep speed between 0.25 and 4; re-run (pass 1 is rebuilt when clips change) |
| Whisper model download fails | network allowlist; or copy models into config.hf_home |
| out of memory in Demucs | `--segment 5`, close other apps, or split the audio |
| Remotion "Could not find browser" | set EVE_BROWSER to chrome.exe / msedge.exe (the script also tries installed Chrome/Edge) |
| Remotion "Timed out ... connect to the browser" | first launch from a slow disk; the script retries once |
| PowerShell breaks JSON arguments | write props/plans to .json files and pass the path |
| faces not found / reframe uses blur | `pip install "opencv-python-headless<5"` |
| CLAP error about torch.load | torch must be >= 2.6 |
