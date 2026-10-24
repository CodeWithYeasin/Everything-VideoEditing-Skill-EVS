"""Speech to text with word timestamps (Whisper).

  python transcribe.py video.mp4 --out words.json [--srt subs.srt] [--model small]
                       [--language bn] [--keep-fillers] [--engine faster|openai]

Writes {"source", "language", "duration", "segments":[...], "words":[{start,end,word,prob}]}.
Models: tiny, base, small (default, good for English), medium (better for Bangla/Hindi),
large-v3 (best, slow on CPU). faster-whisper is used when installed (4x faster on CPU),
otherwise openai-whisper.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import vtools as V

FILLER_PROMPT = "Umm, let me think, like, hmm... Okay, uh, here's what I was, like, thinking."


def extract_wav(src: Path, work: Path) -> Path:
    wav = work / (src.stem + "_16k.wav")
    if not wav.exists() or wav.stat().st_mtime < src.stat().st_mtime:
        V.ffmpeg(["-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)])
    return wav


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments, path: Path, max_chars=42):
    lines, n = [], 1
    for seg in segments:
        words = seg.get("words") or []
        chunk, cs = [], None
        for w in words + [None]:
            if w is not None and (not chunk or len(" ".join(x["word"] for x in chunk)) + len(w["word"]) < max_chars):
                chunk.append(w)
                continue
            if chunk:
                text = " ".join(x["word"].strip() for x in chunk)
                lines.append(f"{n}\n{srt_time(chunk[0]['start'])} --> {srt_time(chunk[-1]['end'])}\n{text}\n")
                n += 1
            chunk = [w] if w is not None else []
        if not words and seg.get("text"):
            lines.append(f"{n}\n{srt_time(seg['start'])} --> {srt_time(seg['end'])}\n{seg['text'].strip()}\n")
            n += 1
    path.write_text("\n".join(lines), encoding="utf-8")


def run_faster(wav, model, language, prompt, device):
    from faster_whisper import WhisperModel
    compute = "int8" if device == "cpu" else "float16"
    m = WhisperModel(model, device=device, compute_type=compute,
                     cpu_threads=max(1, (os.cpu_count() or 2)))
    segs, info = m.transcribe(str(wav), language=language, word_timestamps=True, vad_filter=True,
                              beam_size=5, initial_prompt=prompt, condition_on_previous_text=False)
    out = []
    for s in segs:
        out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                    "words": [{"start": w.start, "end": w.end, "word": w.word.strip(), "prob": round(w.probability, 3)}
                              for w in (s.words or [])]})
        print(f"  [{s.start:7.2f}] {s.text.strip()}", flush=True)
    return out, info.language


def run_openai(wav, model, language, prompt, device):
    import whisper
    m = whisper.load_model(model, device=device, download_root=V.CFG.get("whisper_dir"))
    r = m.transcribe(str(wav), language=language, word_timestamps=True, initial_prompt=prompt,
                     condition_on_previous_text=False, fp16=device != "cpu", verbose=False)
    out = []
    for s in r["segments"]:
        out.append({"start": s["start"], "end": s["end"], "text": s["text"].strip(),
                    "words": [{"start": w["start"], "end": w["end"], "word": w["word"].strip(),
                               "prob": round(w.get("probability", 1.0), 3)} for w in s.get("words", [])]})
    return out, r.get("language")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--srt")
    ap.add_argument("--model", default="small")
    ap.add_argument("--language", default=None, help="en, bn, hi, ... (auto when omitted)")
    ap.add_argument("--keep-fillers", action="store_true", help="bias Whisper to write um/uh so they can be cut")
    ap.add_argument("--prompt", help="names/terms to spell correctly, e.g. 'BRAC, xv6, Remotion'")
    ap.add_argument("--engine", choices=["auto", "faster", "openai"], default="auto")
    a = ap.parse_args()
    V.setup_model_env()
    src = Path(a.src).resolve()
    work = V.ensure_dir(Path(a.out).resolve().parent / ".eve_work")
    wav = extract_wav(src, work)
    prompt = " ".join(x for x in [FILLER_PROMPT if a.keep_fillers else None, a.prompt] if x) or None
    device = V.CFG.get("device", "cpu")
    if device != "cpu":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"
    engines = ["faster", "openai"] if a.engine == "auto" else [a.engine]
    last = None
    for eng in engines:
        try:
            print(f"[eve] whisper ({eng}, {a.model}, {device}) ...", flush=True)
            segs, lang = (run_faster if eng == "faster" else run_openai)(wav, a.model, a.language, prompt, device)
            break
        except ImportError as e:
            last = e
            continue
    else:
        sys.exit(f"[eve] no Whisper engine available ({last}). pip install faster-whisper")
    words = [w for s in segs for w in s["words"]]
    data = {"source": str(src), "language": lang, "model": a.model,
            "duration": V.media_info(src)["duration"], "segments": segs, "words": words}
    Path(a.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.srt:
        write_srt(segs, Path(a.srt))
    print(json.dumps({"out": a.out, "language": lang, "segments": len(segs), "words": len(words)}))


if __name__ == "__main__":
    main()
