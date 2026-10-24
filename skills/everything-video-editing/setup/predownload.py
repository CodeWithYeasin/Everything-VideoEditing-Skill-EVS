"""Download the AI models once so later edits run offline.
   python predownload.py [--whisper small,medium] [--no-clap] [--no-demucs]"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import vtools as V  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--whisper", default="small,medium")
ap.add_argument("--no-clap", action="store_true")
ap.add_argument("--no-demucs", action="store_true")
a = ap.parse_args()
V.setup_model_env()


def step(name, fn):
    try:
        fn()
        print("OK  ", name, flush=True)
    except Exception as e:  # keep going; doctor.py will show what's missing
        print("FAIL", name, repr(e)[:300], flush=True)


for size in [s for s in a.whisper.split(",") if s]:
    def fw(size=size):
        from faster_whisper import WhisperModel
        WhisperModel(size, device="cpu", compute_type="int8")
    step(f"faster-whisper {size}", fw)

if not a.no_demucs:
    def dm():
        from demucs.pretrained import get_model
        get_model("htdemucs")
    step("demucs htdemucs", dm)

if not a.no_clap:
    def cl():
        from transformers import ClapModel, ClapProcessor
        ClapModel.from_pretrained("laion/clap-htsat-unfused")
        ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
    step("CLAP laion/clap-htsat-unfused", cl)
