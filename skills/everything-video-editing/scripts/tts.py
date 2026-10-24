"""Text-to-speech voice-over with word timings (for OVC scratch VO, explainers, captions).

  python tts.py --text "নতুন অফার, আজই অর্ডার করুন" --voice bn-BD-NabanitaNeural --out vo.wav
  python tts.py --file script.txt --voice en-US-AriaNeural --rate +5% --out vo.wav
  python tts.py --list bn            # voices for a language code

Writes vo.wav (48 kHz stereo) and vo.words.json (word start/end, usable as captions).
Engines (auto order): edge (Microsoft neural voices via the edge-tts package, needs
internet; Bangla bn-BD-NabanitaNeural / bn-BD-PradeepNeural, bn-IN-TanishaaNeural /
bn-IN-BashkarNeural, English en-US-AriaNeural / en-US-GuyNeural / en-GB-SoniaNeural,
Hindi hi-IN-SwaraNeural ...) -> sapi (Windows built-in, offline, English) -> say (macOS)
-> espeak-ng (Linux). For paid commercial work check the voice service's terms, or use a
human voice artist and keep the TTS as a timing guide.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import vtools as V

DEFAULT_VOICE = {"bn": "bn-BD-NabanitaNeural", "en": "en-US-AriaNeural", "hi": "hi-IN-SwaraNeural"}


def guess_lang(text: str) -> str:
    if re.search(r"[ঀ-৿]", text):
        return "bn"
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    return "en"


def to_wav(src: Path, dst: Path):
    V.ffmpeg(["-i", str(src), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(dst)])


def even_words(text: str, dur: float, lead: float = 0.05) -> list:
    toks = text.split()
    if not toks:
        return []
    weights = [max(1, len(t)) for t in toks]
    total = sum(weights)
    t, out = lead, []
    span = max(0.1, dur - lead - 0.1)
    for tok, w in zip(toks, weights):
        d = span * w / total
        out.append({"start": round(t, 3), "end": round(t + d * 0.92, 3), "word": tok})
        t += d
    return out


async def _edge(text, voice, rate, pitch, mp3: Path):
    import edge_tts
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    except TypeError:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    words = []
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                st = chunk["offset"] / 1e7
                words.append({"start": round(st, 3), "end": round(st + chunk["duration"] / 1e7, 3), "word": chunk["text"]})
    return words


def engine_edge(text, voice, rate, pitch, wav: Path):
    mp3 = wav.with_suffix(".tmp.mp3")
    words = asyncio.run(_edge(text, voice, rate, pitch, mp3))
    if not mp3.exists() or mp3.stat().st_size < 500:
        raise RuntimeError("edge-tts returned no audio")
    to_wav(mp3, wav)
    mp3.unlink(missing_ok=True)
    return words


def engine_sapi(text, voice, rate, pitch, wav: Path):
    if platform.system() != "Windows":
        raise RuntimeError("sapi is Windows-only")
    tmp = wav.with_suffix(".sapi.wav")
    r = 0
    m = re.match(r"([+-]\d+)%", rate or "")
    if m:
        r = max(-10, min(10, int(int(m.group(1)) / 10)))
    txt = Path(tempfile.mkstemp(suffix=".txt")[1])
    txt.write_text(text, encoding="utf-8")
    ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.Rate={r}; $s.SetOutputToWaveFile('{tmp}'); "
          f"$s.Speak([IO.File]::ReadAllText('{txt}')); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)
    txt.unlink(missing_ok=True)
    to_wav(tmp, wav)
    tmp.unlink(missing_ok=True)
    return None


def engine_say(text, voice, rate, pitch, wav: Path):
    if not shutil.which("say"):
        raise RuntimeError("no say")
    aiff = wav.with_suffix(".aiff")
    subprocess.run(["say", "-o", str(aiff), text], check=True)
    to_wav(aiff, wav)
    aiff.unlink(missing_ok=True)
    return None


def engine_espeak(text, voice, rate, pitch, wav: Path):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("no espeak")
    tmp = wav.with_suffix(".es.wav")
    lang = {"bn": "bn", "hi": "hi"}.get(guess_lang(text), "en")
    subprocess.run([exe, "-v", lang, "-w", str(tmp), text], check=True)
    to_wav(tmp, wav)
    tmp.unlink(missing_ok=True)
    return None


def engine_silent(text, voice, rate, pitch, wav: Path):
    """No speech: silence as long as the line would take to read (timing guide / scratch VO)."""
    n = len(text.split())
    dur = max(1.0, n / (2.3 if guess_lang(text) == "bn" else 2.6) + 0.3)
    V.ffmpeg(["-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=48000:cl=stereo", "-c:a", "pcm_s16le", str(wav)])
    return None


ENGINES = {"edge": engine_edge, "sapi": engine_sapi, "say": engine_say, "espeak": engine_espeak}
EXTRA = {"silent": engine_silent}


def synth(text: str, out: Path, voice: str | None = None, rate: str = "+0%", pitch: str = "+0Hz",
          engine: str = "auto") -> dict:
    out = Path(out).resolve()
    V.ensure_dir(out.parent)
    voice = voice or DEFAULT_VOICE[guess_lang(text)]
    order = list(ENGINES) if engine == "auto" else [engine]
    table = {**ENGINES, **EXTRA}
    errors = {}
    for name in order:
        try:
            words = table[name](text, voice, rate, pitch, out)
            dur = V.media_info(out)["duration"]
            if not words:
                words = even_words(text, dur)
            (out.with_suffix(".words.json")).write_text(
                json.dumps({"source": None, "text": text, "engine": name, "voice": voice if name == "edge" else name,
                            "words": words}, ensure_ascii=False, indent=1), encoding="utf-8")
            return {"out": str(out), "words": str(out.with_suffix(".words.json")), "engine": name,
                    "duration": round(dur, 3)}
        except Exception as e:  # try the next engine
            errors[name] = repr(e)[:200]
    raise SystemExit(f"[eve] no TTS engine worked: {json.dumps(errors)}\n"
                     "Install edge-tts (pip install edge-tts) and check internet, or record the VO.")


def list_voices(lang: str):
    try:
        import edge_tts
    except ImportError:
        sys.exit("pip install edge-tts")
    voices = asyncio.run(edge_tts.list_voices())
    sel = [v for v in voices if v["ShortName"].lower().startswith(lang.lower())]
    print(json.dumps([{"voice": v["ShortName"], "gender": v["Gender"]} for v in sel], indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--out", default="vo.wav")
    ap.add_argument("--voice")
    ap.add_argument("--rate", default="+0%", help="e.g. -10%% slower, +10%% faster")
    ap.add_argument("--pitch", default="+0Hz")
    ap.add_argument("--engine", default="auto", choices=["auto"] + list(ENGINES) + list(EXTRA),
                    help="silent = timing guide only (VO to be recorded later)")
    ap.add_argument("--list", metavar="LANG")
    a = ap.parse_args()
    if a.list:
        list_voices(a.list)
        return
    text = a.text or (Path(a.file).read_text(encoding="utf-8") if a.file else None)
    if not text:
        sys.exit("[eve] --text or --file needed")
    print(json.dumps(synth(text.strip(), Path(a.out), a.voice, a.rate, a.pitch, a.engine), ensure_ascii=False))


if __name__ == "__main__":
    main()
