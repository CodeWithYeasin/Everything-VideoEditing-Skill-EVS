"""Find the right music / sound effect by describing it (LAION CLAP).

  # rank a library against a description
  python clap_rank.py --dir "D:/Music" --query "calm lo-fi piano for a study vlog" --top 5
  # several queries at once (e.g. one per scene)
  python clap_rank.py --dir sfx/ --query "whoosh transition" --query "camera shutter" --top 3
  # describe what a clip sounds like (zero-shot tags)
  python clap_rank.py --tag song.mp3

Embeddings are cached in <dir>/.clap_cache.json, so the second search is instant.
Decoding uses ffmpeg, so mp3/m4a/aac/flac/ogg/wav and even videos work.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import vtools as V

MODEL = "laion/clap-htsat-unfused"
TAGS = ["upbeat energetic pop", "calm ambient", "lo-fi hip hop beat", "cinematic orchestral epic",
        "sad emotional piano", "happy acoustic guitar", "electronic dance music", "rock with electric guitar",
        "corporate inspiring", "suspense tension", "funny quirky", "romantic", "traditional Bengali folk music",
        "hip hop rap", "jazz", "classical", "speech talking", "nature sounds", "crowd noise",
        "whoosh swoosh transition", "impact boom hit", "click pop UI sound", "notification ding",
        "applause", "laughter", "silence"]
EXTS = V.AUDIO_EXT | {".mp4", ".mov", ".mkv", ".webm"}


def load_clip(path: Path, seconds: float = 12.0):
    import numpy as np
    info = V.media_info(path)
    d = info["duration"] or seconds
    start = max(0.0, min(d * 0.3, d - seconds)) if d > seconds else 0.0
    raw = subprocess.run([V.need("ffmpeg"), "-v", "error", "-ss", f"{start:.2f}", "-t", f"{seconds:.2f}",
                          "-i", str(path), "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    return a if a.size else np.zeros(48000, dtype=np.float32)


class Clap:
    def __init__(self):
        V.setup_model_env()
        from transformers import ClapModel, ClapProcessor
        import torch
        self.torch = torch
        self.model = ClapModel.from_pretrained(MODEL).eval()
        self.proc = ClapProcessor.from_pretrained(MODEL)

    def audio(self, arrays):
        with self.torch.no_grad():
            try:
                inp = self.proc(audio=arrays, sampling_rate=48000, return_tensors="pt", padding=True)
            except (TypeError, ValueError):
                inp = self.proc(audios=arrays, sampling_rate=48000, return_tensors="pt", padding=True)
            e = self.model.get_audio_features(**inp)
        return (e / e.norm(dim=-1, keepdim=True)).tolist()

    def text(self, texts):
        with self.torch.no_grad():
            inp = self.proc(text=texts, return_tensors="pt", padding=True)
            e = self.model.get_text_features(**inp)
        return (e / e.norm(dim=-1, keepdim=True)).tolist()


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", action="append", default=[], help="folder(s) to search (recursive)")
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--tag", help="describe one audio file instead of searching")
    a = ap.parse_args()
    try:
        clap = Clap()
    except Exception as e:
        sys.exit(f"[eve] CLAP unavailable ({e}). Needs: pip install transformers torch; model download access.")
    if a.tag:
        emb = clap.audio([load_clip(Path(a.tag))])[0]
        tv = clap.text(TAGS)
        scored = sorted(((dot(emb, t), tag) for t, tag in zip(tv, TAGS)), reverse=True)[:6]
        print(json.dumps([{"tag": t, "score": round(s, 3)} for s, t in scored], indent=1))
        return
    files = [Path(f).resolve() for f in a.files]
    caches = {}
    for d in a.dir:
        d = Path(d).resolve()
        files += [p for p in d.rglob("*") if p.suffix.lower() in EXTS and not p.name.startswith(".")]
        cp = d / ".clap_cache.json"
        try:
            caches[d] = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {}
        except Exception:
            caches[d] = {}
    if not files or not a.query:
        sys.exit("[eve] need --dir/--files and at least one --query")
    allcache = {k: v for c in caches.values() for k, v in c.items()}
    embs, todo = {}, []
    for f in files:
        key = f"{f}|{int(f.stat().st_mtime)}"
        if key in allcache:
            embs[str(f)] = allcache[key]
        else:
            todo.append((f, key))
    print(f"[eve] embedding {len(todo)} new file(s), {len(embs)} cached", file=sys.stderr)
    for i in range(0, len(todo), 8):
        batch = todo[i:i + 8]
        vecs = clap.audio([load_clip(f) for f, _ in batch])
        for (f, key), v in zip(batch, vecs):
            embs[str(f)] = v
            for d in caches:
                if str(f).startswith(str(d)):
                    caches[d][key] = v
    for d, c in caches.items():
        try:
            (d / ".clap_cache.json").write_text(json.dumps(c), encoding="utf-8")
        except OSError:
            pass
    tv = clap.text(a.query)
    out = {}
    for q, t in zip(a.query, tv):
        ranked = sorted(((dot(e, t), f) for f, e in embs.items()), reverse=True)[:a.top]
        out[q] = [{"file": f, "score": round(s, 3)} for s, f in ranked]
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
