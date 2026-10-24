"""Download the binary assets (fonts, RNNoise voice model) into the skill folder.
Used when the skill's text files were copied somewhere without them (e.g. to a PC).
   python fetch_assets.py"""
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "assets"
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FILES = {
    "fonts/Anton-Regular.ttf": GF + "anton/Anton-Regular.ttf",
    "fonts/OFL.txt": GF + "anton/OFL.txt",
    "fonts/Poppins-Bold.ttf": GF + "poppins/Poppins-Bold.ttf",
    "fonts/Poppins-ExtraBold.ttf": GF + "poppins/Poppins-ExtraBold.ttf",
    "fonts/HindSiliguri-Bold.ttf": GF + "hindsiliguri/HindSiliguri-Bold.ttf",
    "fonts/NotoSansBengali.ttf": GF + "notosansbengali/NotoSansBengali%5Bwdth,wght%5D.ttf",
    "denoise/std.rnnn": "https://raw.githubusercontent.com/richardpl/arnndn-models/master/std.rnnn",
}
ok = True
for rel, url in FILES.items():
    dst = ROOT / rel
    if dst.exists() and dst.stat().st_size > 1000:
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, dst)
        print("got", rel)
    except Exception as e:
        ok = False
        print("FAILED", rel, e)
sys.exit(0 if ok else 1)
