"""Animated motion graphics with Remotion (React) -> overlay file for plan.json.

  python remotion_gfx.py TitleCard --props '{"title":"Episode 1","subtitle":"How I edit"}' \
         --out title.mov --size 1080x1920 --dur 3
  python remotion_gfx.py list                 # show compositions and their props

Compositions: TitleCard, LowerThird, CallToAction, EndCard, KineticText, StatCounter,
ProgressBar, Countdown (see graphics/remotion/src/comps.tsx). Bangla text works.
bg "transparent" (default) renders ProRes 4444 .mov with alpha; any other bg renders .mp4.
First run copies the template to a cache folder and runs `npm install` (needs Node 18+).
For a brand-new custom animation, copy the template, add a component, and pass --project.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import vtools as V

TEMPLATE = V.SKILL_DIR / "graphics" / "remotion"
COMPS = {
    "TitleCard": "title, subtitle, align(center|left), accent, textColor, bg, font",
    "LowerThird": "name, role, side(left|right), accent, bg",
    "CallToAction": "text, sub, icon(bell|like|none), accent, bg",
    "EndCard": "title, sub, slots(0-3), accent, bg(default gradient)",
    "KineticText": "words[], perWord(seconds), accent, bg",
    "StatCounter": "value, prefix, suffix, label, decimals, accent, bg",
    "ProgressBar": "accent, thickness, position(top|bottom)  (set --dur to the video length)",
    "Countdown": "from, accent, bg",
    "LogoReveal": "logo(image), name, tagline, accent, bg(default gradient)  -> opaque intro/outro",
    "EndSlate": "logo, product(image), tagline, cta, website, phone, handle, accent, bg  -> OVC packshot",
    "OfferBadge": "label, price, oldPrice, position(top-right|top-left|bottom-right|bottom-left|center), scale",
    "BeforeAfter": "before(image), after(image), beforeLabel, afterLabel, accent  -> opaque wipe compare",
    "FeatureCallout": "items[{text, x, y, side}] (x,y 0..1 on the frame), accent",
    "SocialFollow": "title, handles[{platform(youtube|instagram|facebook|tiktok|x|linkedin|website), handle}]",
    "Wordmark": "text, subtitle, accent, bg, size  -> animated name / channel intro",
}
OPAQUE = {"LogoReveal", "EndSlate", "BeforeAfter", "EndCard"}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".mp4", ".mov", ".webm", ".mp3", ".wav"}


def localize_media(obj, proj: Path, base: Path):
    """Copy local image/video files referenced in props into public/media and point to them."""
    if isinstance(obj, dict):
        return {k: localize_media(v, proj, base) for k, v in obj.items()}
    if isinstance(obj, list):
        return [localize_media(v, proj, base) for v in obj]
    if isinstance(obj, str) and Path(obj).suffix.lower() in MEDIA_EXT and not obj.startswith(("http:", "https:", "media/")):
        p = Path(obj) if Path(obj).is_absolute() else (base / obj)
        if p.exists():
            dst_dir = V.ensure_dir(proj / "public" / "media")
            h = hashlib.sha1(str(p.resolve()).encode()).hexdigest()[:8]
            dst = dst_dir / f"{h}_{p.name.replace(' ', '_')}"
            if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
                shutil.copy2(p, dst)
            return f"media/{dst.name}"
    return obj


def brand_props(path: str | None) -> dict:
    if not path:
        return {}
    bp = Path(path).resolve()
    b = json.loads(bp.read_text(encoding="utf-8"))
    c = b.get("colors", {})
    out = {"accent": c.get("accent") or c.get("primary"), "textColor": c.get("text"),
           "logo": b.get("logo"), "tagline": b.get("tagline"), "website": b.get("website"),
           "phone": b.get("phone"), "handle": b.get("handle"), "name": b.get("name")}
    if c.get("bg"):
        out["_brand_bg"] = c["bg"]
    for k in ("logo",):
        if out.get(k) and not Path(out[k]).is_absolute():
            out[k] = str((bp.parent / out[k]).resolve())
    return {k: v for k, v in out.items() if v}


def cache_dir() -> Path:
    root = V.CFG.get("root")
    base = Path(root) if root else Path.home() / ".everything-video"
    return V.ensure_dir(base / "remotion-graphics")


def tree_hash(p: Path) -> str:
    h = hashlib.sha1()
    for f in sorted(p.rglob("*")):
        if f.is_file() and "node_modules" not in f.parts and "public" not in f.parts and "out" not in f.parts:
            h.update(str(f.relative_to(p)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:12]


def prepare(project: Path | None) -> Path:
    if project:
        proj = project.resolve()
    else:
        proj = cache_dir()
        stamp = proj / ".template_hash"
        th = tree_hash(TEMPLATE)
        if not stamp.exists() or stamp.read_text() != th:
            for item in ("src", "package.json", "tsconfig.json", "remotion.config.ts"):
                s, d = TEMPLATE / item, proj / item
                if d.is_dir():
                    shutil.rmtree(d)
                (shutil.copytree if s.is_dir() else shutil.copy2)(s, d)
            stamp.write_text(th)
    fonts = V.ensure_dir(proj / "public" / "fonts")
    for f in (V.ASSETS / "fonts").glob("*.ttf"):
        if not (fonts / f.name).exists():
            shutil.copy2(f, fonts / f.name)
    if not (proj / "node_modules" / "@remotion" / "cli").exists():
        npm = shutil.which("npm")
        if not npm:
            sys.exit("[eve] Node.js/npm not found. Install Node 18+ (https://nodejs.org).")
        V.run([npm, "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=proj, quiet=False)
    return proj


def find_browser(proj: Path) -> str | None:
    """Remotion downloads its own headless Chrome. Where that host is blocked (some
    sandboxes), fall back to a system Chrome/Edge or the npm @sparticuz/chromium build."""
    if os.environ.get("EVE_BROWSER"):
        return os.environ["EVE_BROWSER"]
    if V.CFG.get("chrome"):
        return V.CFG["chrome"]
    return None


def system_browser() -> str | None:
    """Installed Chrome or Edge (Windows/macOS) - a fallback when Remotion's own headless
    Chrome can't be downloaded or started."""
    cands = []
    if platform.system() == "Windows":
        for base in (os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                     os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                     os.environ.get("LOCALAPPDATA", "")):
            cands += [Path(base) / "Google/Chrome/Application/chrome.exe",
                      Path(base) / "Microsoft/Edge/Application/msedge.exe"]
    elif platform.system() == "Darwin":
        cands += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                  Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")]
    for c in cands:
        if c.exists():
            return str(c)
    return None


def sparticuz(proj: Path) -> str | None:
    if platform.system() != "Linux":
        return None
    try:
        if not (proj / "node_modules" / "@sparticuz" / "chromium").exists():
            V.run([shutil.which("npm"), "install", "--no-save", "--no-audit", "--no-fund", "@sparticuz/chromium"], cwd=proj)
        out = subprocess.run([shutil.which("node"), "-e",
                              "const c=require('@sparticuz/chromium');(c.default||c).executablePath().then(p=>console.log(p))"],
                             cwd=proj, capture_output=True, text=True).stdout.strip()
        return out.splitlines()[-1] if out else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comp", help="composition id, or 'list'")
    ap.add_argument("--props", default="{}", help="JSON string or path to a .json file")
    ap.add_argument("--out")
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--dur", type=float)
    ap.add_argument("--project", help="custom Remotion project folder (entry src/index.ts)")
    ap.add_argument("--concurrency", type=int, default=0)
    ap.add_argument("--brand", help="brand.json: fills accent, logo, tagline, website ... when not given")
    a = ap.parse_args()
    if a.comp == "list":
        print(json.dumps(COMPS, indent=1))
        return
    props = json.loads(Path(a.props).read_text(encoding="utf-8")) if a.props.endswith(".json") else json.loads(a.props)
    w, h = map(int, a.size.lower().split("x"))
    props.setdefault("width", w)
    props.setdefault("height", h)
    props.setdefault("fps", a.fps)
    if a.dur:
        props["duration"] = a.dur
    bprops = brand_props(a.brand)
    brand_bg = bprops.pop("_brand_bg", None)
    for k, v in bprops.items():
        props.setdefault(k, v)
    if a.comp in OPAQUE:
        props.setdefault("bg", brand_bg or "gradient")
    props.setdefault("bg", "transparent")
    transparent = props["bg"] == "transparent"
    out = Path(a.out or f"{a.comp}.{'mov' if transparent else 'mp4'}").resolve()
    if transparent and out.suffix.lower() != ".mov":
        out = out.with_suffix(".mov")
    proj = prepare(Path(a.project) if a.project else None)
    props = localize_media(props, proj, Path(a.props).resolve().parent if a.props.endswith(".json") else Path.cwd())
    pfile = proj / f"props_{os.getpid()}.json"
    pfile.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    node = shutil.which("node")
    cli = proj / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    cmd = [node, str(cli), "render", "src/index.ts", a.comp, str(out), f"--props={pfile.name}"]
    if transparent:
        cmd += ["--codec=prores", "--prores-profile=4444", "--pixel-format=yuva444p10le", "--image-format=png"]
    else:
        cmd += ["--codec=h264", "--crf=16"]
    if a.concurrency:
        cmd.append(f"--concurrency={a.concurrency}")
    br = find_browser(proj)
    if br:
        cmd.append(f"--browser-executable={br}")
    print(f"[eve] remotion render {a.comp} -> {out.name}", file=sys.stderr, flush=True)

    def attempt(extra):
        return subprocess.run(cmd + extra, cwd=proj, text=True, encoding="utf-8", errors="replace",
                              capture_output=True)

    r = attempt([])
    if r.returncode != 0 and not br:
        log = r.stderr + r.stdout
        fallbacks = []
        if "connect to the browser" in log or "Timed out" in log:
            fallbacks.append([])  # first Chrome launch from a slow disk: just retry once
        sysb = system_browser()
        if sysb:
            fallbacks.append([f"--browser-executable={sysb}"])
        if "remotion.media" in log or "browser" in log.lower():
            sb = sparticuz(proj)
            if sb:
                fallbacks.append([f"--browser-executable={sb}"])
        for extra in fallbacks:
            print(f"[eve] retrying {extra or '(same browser)'}", file=sys.stderr, flush=True)
            r = attempt(extra)
            if r.returncode == 0:
                break
    pfile.unlink(missing_ok=True)
    if r.returncode != 0:
        sys.stderr.write("\n".join((r.stdout + "\n" + r.stderr).strip().splitlines()[-25:]) + "\n")
        sys.exit("[eve] Remotion render failed")
    print(json.dumps({"out": str(out), "comp": a.comp, "size": f"{w}x{h}", "duration": props.get("duration", 3),
                      "alpha": transparent}))


if __name__ == "__main__":
    main()
