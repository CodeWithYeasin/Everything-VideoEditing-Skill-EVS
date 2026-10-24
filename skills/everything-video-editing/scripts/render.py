"""Render an edit plan (JSON) into a finished video.

  python render.py plan.json            full quality
  python render.py plan.json --draft    fast half-resolution preview
  python render.py plan.json --pass1    only assemble the cut (for transcribing the edit)

Pass 1 assembles the timeline (cuts, speed, reframing, zoom, Ken Burns,
transitions). Pass 2 adds colour grade, stabilisation, overlays, graphics,
captions/titles, voice clean-up, music with ducking, SFX and loudness.
Pass 1 is cached, so changing only the look/audio/text re-renders fast.
See references/plan_format.md for every field.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import vtools as V
import platforms as PF
from captions import build_ass, load_words, words_to_srt

PRESETS = {
    "youtube": (1920, 1080), "1080p": (1920, 1080), "landscape": (1920, 1080), "720p": (1280, 720),
    "4k": (3840, 2160), "reels": (1080, 1920), "shorts": (1080, 1920), "tiktok": (1080, 1920),
    "vertical": (1080, 1920), "story": (1080, 1920), "square": (1080, 1080), "portrait": (1080, 1350),
    "instagram": (1080, 1350),
}
XFADES = {"fade", "dissolve", "fadeblack", "fadewhite", "wipeleft", "wiperight", "wipeup", "wipedown",
          "slideleft", "slideright", "slideup", "slidedown", "smoothleft", "smoothright", "smoothup",
          "smoothdown", "circleopen", "circleclose", "circlecrop", "rectcrop", "radial", "zoomin",
          "pixelize", "hblur", "distance", "squeezeh", "squeezev", "diagtl", "diagtr", "hlslice", "hrslice"}
XFADE_ALIAS = {"crossfade": "fade", "whip": "smoothleft", "push": "slideleft", "zoom": "zoomin",
               "blur": "hblur", "black": "fadeblack", "white": "fadewhite", "flash": "fadewhite"}

GRADES = {
    "none": {},
    "natural": dict(contrast=1.04, saturation=1.08, sharpen=0.25),
    "auto": dict(auto=True, contrast=1.03, saturation=1.06, sharpen=0.25),
    "cinematic": dict(contrast=1.10, saturation=0.95, teal_orange=0.6, curve="s", vignette=0.4, sharpen=0.2),
    "teal_orange": dict(contrast=1.08, saturation=1.05, teal_orange=1.0, curve="s"),
    "warm": dict(temperature=5200, contrast=1.04, saturation=1.08),
    "golden": dict(temperature=4700, contrast=1.06, saturation=1.12, brightness=0.02, vignette=0.25),
    "cool": dict(temperature=8200, contrast=1.05, saturation=0.98),
    "vintage": dict(curve="vintage", saturation=0.85, grain=6, vignette=0.5, fade=0.05, temperature=5600),
    "film": dict(curve="s", fade=0.04, grain=5, vignette=0.3, saturation=0.92, contrast=1.05),
    "bw": dict(saturation=0.0, contrast=1.18, grain=4, curve="s"),
    "moody": dict(brightness=-0.04, contrast=1.12, saturation=0.78, teal_orange=0.35, vignette=0.5),
    "vibrant": dict(vibrance=0.35, contrast=1.06, saturation=1.12, sharpen=0.35),
    "bright": dict(brightness=0.05, gamma=1.06, saturation=1.06, contrast=1.02),
    "pastel": dict(brightness=0.04, contrast=0.92, saturation=0.85, fade=0.06),
    "matte": dict(fade=0.08, contrast=0.95, saturation=0.9),
    "neon": dict(contrast=1.15, saturation=1.35, vibrance=0.3, vignette=0.35, temperature=8000),
}


def fnum(x) -> str:
    return f"{float(x):.4f}".rstrip("0").rstrip(".") or "0"


class Plan:
    def __init__(self, path: Path, draft: bool, data: dict | None = None, suffix: str = ""):
        self.path = path.resolve()
        self.base = self.path.parent
        self.p = data if data is not None else json.loads(self.path.read_text(encoding="utf-8"))
        self.draft = draft
        out = self.p.get("output", "edited.mp4")
        self.output = self.res(out)
        if suffix:
            self.output = self.output.with_name(self.output.stem + "_" + suffix + self.output.suffix)
        if draft:
            self.output = self.output.with_name(self.output.stem + "_draft" + self.output.suffix)
        self.work = V.ensure_dir(self.res(self.p.get("workdir", str(self.output.parent / ".eve_work"))))
        V.copy_assets_to(self.work)
        self.platform = PF.get(self.p.get("platform"))
        self.brand = self.load_brand(self.p.get("brand"))

    def res(self, p) -> Path:
        q = Path(os.path.expandvars(os.path.expanduser(str(p))))
        return q if q.is_absolute() else (self.base / q).resolve()

    def load_brand(self, b) -> dict:
        """brand.json: colors{primary,accent,text,bg}, logo, font_files[], font_heading, font_body,
        tagline, website, phone, handle, watermark(bool)."""
        if not b:
            return {}
        if isinstance(b, str):
            bp = self.res(b)
            b = json.loads(bp.read_text(encoding="utf-8"))
            base = bp.parent
        else:
            base = self.base
        b = dict(b)
        for k in ("logo", "product"):
            if b.get(k) and not Path(b[k]).is_absolute():
                b[k] = str((base / b[k]).resolve())
        for f in b.get("font_files", []) or []:
            fp = Path(f) if Path(f).is_absolute() else base / f
            if fp.exists():
                shutil.copy2(fp, self.work / "fonts" / fp.name)
        return b


# ======================================================================== canvas
def decide_canvas(plan: Plan, first_info: dict):
    c = plan.p.get("canvas", {})
    if isinstance(c, str):
        c = {"preset": c}
    preset = c.get("preset") or plan.p.get("preset")
    if plan.platform and not (c.get("w") or c.get("preset")):
        w, h = plan.platform["size"]
    elif preset and preset in PRESETS:
        w, h = PRESETS[preset]
    elif preset and PF.get(preset):
        plan.platform = plan.platform or PF.get(preset)
        w, h = PF.get(preset)["size"]
    elif c.get("w") and c.get("h"):
        w, h = int(c["w"]), int(c["h"])
    else:
        w, h = first_info.get("width") or 1920, first_info.get("height") or 1080
        if max(w, h) > 3840:
            s = 3840 / max(w, h)
            w, h = w * s, h * s
    fps = float(c.get("fps") or plan.p.get("fps") or first_info.get("fps") or 30)
    if fps > 60:
        fps = 60
    if fps <= 0:
        fps = 30
    if abs(fps - round(fps)) < 0.02:
        fps = round(fps)
    w, h = V.even(w), V.even(h)
    if plan.draft:
        w, h = V.even(w / 2), V.even(h / 2)
    return w, h, fps


# ======================================================================== face focus
def face_focus(src: str, t0: float, t1: float, work: Path) -> float | None:
    """Median horizontal face centre (0..1) over a few frames, or None."""
    cv2, casc = V.face_cascade()
    if casc is None:
        return None
    xs = []
    n = 6
    for k in range(n):
        t = t0 + (t1 - t0) * (k + 0.5) / n
        img = work / f"_face_{k}.jpg"
        subprocess.run([V.need("ffmpeg"), "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src,
                        "-frames:v", "1", "-vf", "scale=640:-2", str(img)], check=False)
        fr = cv2.imread(str(img))
        if fr is None:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        faces = casc.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            xs.append((x + w / 2) / fr.shape[1])
        img.unlink(missing_ok=True)
    if not xs:
        return None
    xs.sort()
    return xs[len(xs) // 2]


# ======================================================================== pass 1
def atempo_chain(speed: float) -> list:
    out, s = [], speed
    while s > 2.0:
        out.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        out.append("atempo=0.5")
        s /= 0.5
    if abs(s - 1) > 1e-3:
        out.append(f"atempo={fnum(s)}")
    return out


def fit_filters(i, mode, sw, sh, W, H, fx=0.5, fy=0.5):
    """Return (filter_text_prefix, needs_graph) — graph text uses labels when needed."""
    if mode == "stretch":
        return f"scale={W}:{H}", False
    if mode == "pad":
        return f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black", False
    if mode == "blur":
        bw, bh = V.even(W / 4), V.even(H / 4)
        g = (f"split=2[bg{i}][fg{i}];[bg{i}]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},"
             f"gblur=sigma=10,scale={W}:{H},eq=brightness=-0.07:saturation=0.9[bgb{i}];"
             f"[fg{i}]scale={W}:{H}:force_original_aspect_ratio=decrease[fgs{i}];"
             f"[bgb{i}][fgs{i}]overlay=(W-w)/2:(H-h)/2")
        return g, True
    # crop (fill)
    return (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}:(iw-{W})*{fnum(fx)}:(ih-{H})*{fnum(fy)}"), False


def kenburns_filter(kb, W, H, fps, frames):
    if kb is True:
        kb = "in"
    kb = str(kb)
    n = max(1, frames)
    zmax = 1.15
    rate = (zmax - 1) / n
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if kb == "out":
        z = f"max({fnum(zmax)}-{rate:.6f}*on,1)"
    elif kb in ("left", "right"):
        z = "1.12"
        cx = f"(iw-iw/zoom)*on/{n}" if kb == "right" else f"(iw-iw/zoom)*(1-on/{n})"
    else:
        z = f"min(1+{rate:.6f}*on,{fnum(zmax)})"
    return f"zoompan=z='{z}':x='{cx}':y='{cy}':d=1:s={W}x{H}:fps={fnum(fps)}"


def pass1(plan: Plan, W, H, fps, clips: list, infos: list):
    inputs, fc, segs = [], [], []
    idx = 0
    for i, (c, info) in enumerate(zip(clips, infos)):
        typ = c["_type"]
        speed = float(c.get("speed", 1.0)) if typ == "video" else 1.0
        vol = float(c.get("volume", 1.0))
        if typ == "video":
            cin = max(0.0, float(c.get("in", 0)))
            cout = c.get("out")
            cout = info["duration"] if cout is None else min(float(cout), info["duration"] or float(cout))
            dsrc = max(0.05, cout - cin)
            dout = dsrc / speed
            hold = 0.0
            if c.get("dur"):  # wanted output length: freeze the last frame if the source is shorter
                hold = max(0.0, float(c["dur"]) - dout)
                dout = float(c["dur"]) if hold else dout
            inputs += ["-ss", f"{cin:.3f}", "-t", f"{dsrc:.3f}", "-i", c["_src"]]
        elif typ == "image":
            hold = 0.0
            cin, cout = 0.0, float(c.get("duration", c.get("dur", 3)))
            dout = cout
            if c.get("kenburns"):
                inputs += ["-loop", "1", "-framerate", fnum(fps), "-t", f"{dout:.3f}", "-i", c["_src"]]
            else:
                inputs += ["-loop", "1", "-framerate", fnum(fps), "-t", f"{dout:.3f}", "-i", c["_src"]]
        else:  # color
            hold = 0.0
            cin, cout = 0.0, float(c.get("duration", c.get("dur", 2)))
            dout = cout
            r, g, b = V.hex_to_rgb(c.get("color", "#000000"))
            inputs += ["-f", "lavfi", "-t", f"{dout:.3f}", "-i",
                       f"color=c=0x{r:02X}{g:02X}{b:02X}:s={W}x{H}:r={fnum(fps)}"]
        vi = idx
        idx += 1
        has_a = typ == "video" and info.get("has_audio") and not c.get("mute")
        if has_a:
            ai = vi
        else:
            inputs += ["-f", "lavfi", "-t", f"{dout:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            ai = idx
            idx += 1

        # ---- video chain
        pre = []
        if typ == "video":
            pre.append(f"setpts=(PTS-STARTPTS)/{fnum(speed)}")
            if speed < 1 and c.get("smooth"):
                pre.append(f"minterpolate=fps={fnum(fps)}:mi_mode=mci:mc_mode=aobmc:vsbmc=1")
        pre.append(f"fps={fnum(fps)}")
        mode = c.get("fit", plan.p.get("fit", "auto"))
        sw, sh = info.get("width") or W, info.get("height") or H
        fx, fy = 0.5, 0.5
        focus = c.get("focus", plan.p.get("focus", "auto"))
        if isinstance(focus, (list, tuple)):
            fx, fy = float(focus[0]), float(focus[1])
        ar_s, ar_c = sw / max(1, sh), W / H
        if mode == "auto":
            if abs(ar_s - ar_c) / ar_c < 0.2:
                mode = "crop"
            elif typ == "video" and ar_s > ar_c:
                f = face_focus(c["_src"], cin, cout, plan.work) if focus == "auto" else None
                if f is not None:
                    mode, fx = "crop", f
                else:
                    mode = "blur"
            else:
                mode = "blur"
        elif mode == "crop" and focus == "auto" and typ == "video" and ar_s > ar_c * 1.2:
            f = face_focus(c["_src"], cin, cout, plan.work)
            if f is not None:
                fx = f
        fit, graph = fit_filters(i, mode, sw, sh, W, H, fx, fy)
        post = []
        z = float(c.get("zoom", 1.0))
        if abs(z - 1) > 1e-3:
            zx, zy = c.get("zoom_center", [0.5, 0.5])
            post += [f"scale={V.even(W * z)}:{V.even(H * z)}", f"crop={W}:{H}:(iw-{W})*{fnum(zx)}:(ih-{H})*{fnum(zy)}"]
        if c.get("kenburns"):
            post.append(kenburns_filter(c["kenburns"], W, H, fps, int(round(dout * fps))))
        if c.get("vf"):
            post.append(str(c["vf"]))
        if typ == "video" and hold > 0:
            post.append(f"tpad=stop_mode=clone:stop_duration={hold + 0.1:.3f}")
        post += [f"trim=duration={dout:.3f}", "setpts=PTS-STARTPTS", "setsar=1", "format=yuv420p", "settb=AVTB"]
        chain = ",".join(pre)
        if graph:
            fc.append(f"[{vi}:v]{chain},{fit}[vf{i}]")
            fc.append(f"[vf{i}]{','.join(post)}[v{i}]")
        else:
            fc.append(f"[{vi}:v]{chain},{fit},{','.join(post)}[v{i}]")

        # ---- audio chain
        ach = ["asetpts=PTS-STARTPTS"] + (atempo_chain(speed) if has_a else []) + [
            "aresample=48000", "aformat=sample_fmts=fltp:channel_layouts=stereo", f"volume={fnum(vol)}",
            f"apad=whole_dur={dout:.3f}", f"atrim=0:{dout:.3f}",
            "afade=t=in:d=0.012", f"afade=t=out:st={max(0, dout - 0.012):.3f}:d=0.012"]
        fc.append(f"[{ai}:a]{','.join(ach)}[a{i}]")
        segs.append({"src": c.get("_src"), "type": typ, "in": cin, "out": cout, "speed": speed, "dur": dout})

    # ---- join
    cur_v, cur_a = "v0", "a0"
    L = segs[0]["dur"]
    segs[0]["start"] = 0.0
    for i in range(1, len(segs)):
        t = clips[i].get("transition")
        if isinstance(t, str):
            t = {"type": t}
        ttype = (t or {}).get("type", "cut")
        ttype = XFADE_ALIAS.get(ttype, ttype)
        d_i = segs[i]["dur"]
        if ttype != "cut" and ttype in XFADES:
            td = min(float(t.get("dur", 0.5)), segs[i - 1]["dur"] * 0.45, d_i * 0.45)
            off = L - td
            fc.append(f"[{cur_v}][v{i}]xfade=transition={ttype}:duration={td:.3f}:offset={off:.3f}[vx{i}]")
            fc.append(f"[{cur_a}][a{i}]acrossfade=d={td:.3f}:c1=tri:c2=tri[ax{i}]")
            segs[i]["start"] = off
            L = off + d_i
        else:
            fc.append(f"[{cur_v}][{cur_a}][v{i}][a{i}]concat=n=2:v=1:a=1[vx{i}][ax{i}]")
            segs[i]["start"] = L
            L += d_i
        cur_v, cur_a = f"vx{i}", f"ax{i}"

    key = V.hash_obj([clips, W, H, fps, plan.draft, plan.p.get("fit"), plan.p.get("focus")])
    out = plan.work / f"assembled_{key}.mkv"
    if not out.exists():
        crf, preset = ("26", "ultrafast") if plan.draft else ("14", "veryfast")
        tmp = out.with_suffix(".tmp.mkv")
        V.ffmpeg(inputs + V.filter_script_args(";\n".join(fc), plan.work, f"pass1_{key}.txt") + [
                           "-map", f"[{cur_v}]", "-map", f"[{cur_a}]",
                           "-c:v", "libx264", "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p",
                           "-r", fnum(fps), "-c:a", "pcm_s16le", "-ar", "48000", str(tmp)], cwd=plan.work)
        tmp.replace(out)
    else:
        print(f"[eve] pass 1 cached: {out.name}")
    (plan.work / "timeline.json").write_text(json.dumps({"total": L, "segments": segs}, indent=2), encoding="utf-8")
    return out, segs, L


# ======================================================================== stabilise
def stabilize(src: Path, work: Path, strength: float) -> Path:
    out = work / (src.stem + f"_stab{int(strength * 100)}.mkv")
    if out.exists():
        return out
    smooth = int(10 + 30 * strength)
    if V.has_filter("vidstabdetect"):
        trf = "stab.trf"
        V.ffmpeg(["-i", str(src), "-vf", f"vidstabdetect=shakiness=6:accuracy=15:result={trf}", "-f", "null", "-"], cwd=work)
        vf = f"vidstabtransform=input={trf}:smoothing={smooth}:zoom=4:optzoom=0:interpol=bicubic,unsharp=5:5:0.6"
    else:
        vf = "deshake=rx=32:ry=32,crop=iw*0.96:ih*0.96,scale=iw/0.96:ih/0.96"
    V.ffmpeg(["-i", str(src), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
              "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)], cwd=work)
    return out


# ======================================================================== grade
def grade_filters(g, work: Path, base_res) -> list:
    if not g:
        return []
    if isinstance(g, str):
        g = {"preset": g}
    s = dict(GRADES.get(g.get("preset", "none"), {}))
    s.update({k: v for k, v in g.items() if k != "preset"})
    f = []
    if s.get("auto"):
        f.append("normalize=blackpt=black:whitept=white:smoothing=24:independence=0.2:strength=0.55")
    if s.get("temperature"):
        f.append(f"colortemperature=temperature={int(s['temperature'])}:mix=0.6:pl=0.6")
    eq = []
    for k, d in (("brightness", 0), ("contrast", 1), ("saturation", 1), ("gamma", 1)):
        if k in s and abs(float(s[k]) - d) > 1e-4:
            eq.append(f"{k}={fnum(s[k])}")
    if eq:
        f.append("eq=" + ":".join(eq))
    k = float(s.get("teal_orange", 0))
    if k:
        f.append(f"colorbalance=rs={-0.07 * k:.3f}:gs={-0.01 * k:.3f}:bs={0.09 * k:.3f}:"
                 f"rh={0.08 * k:.3f}:gh={0.02 * k:.3f}:bh={-0.08 * k:.3f}")
    if s.get("tint"):
        t = float(s["tint"])
        f.append(f"colorbalance=gm={-0.05 * t:.3f}:rm={0.025 * t:.3f}:bm={0.025 * t:.3f}")
    curve = s.get("curve")
    if curve == "s":
        f.append("curves=m='0/0 0.25/0.21 0.5/0.5 0.75/0.8 1/1'")
    elif curve in ("vintage", "lighter", "darker", "increase_contrast", "strong_contrast",
                   "medium_contrast", "cross_process", "negative", "color_negative"):
        f.append(f"curves=preset={curve}")
    if s.get("fade"):
        lift = float(s["fade"])
        f.append(f"curves=all='0/{lift:.3f} 1/{1 - lift * 0.4:.3f}'")
    if s.get("lut"):
        lut = Path(base_res(s["lut"]))
        dst = work / ("lut_" + lut.name.replace(" ", "_"))
        shutil.copy2(lut, dst)
        f.append(f"lut3d=file={dst.name}:interp=tetrahedral")
    if s.get("vibrance"):
        f.append(f"vibrance=intensity={fnum(s['vibrance'])}")
    if s.get("denoise"):
        f.append("hqdn3d=3:3:6:6")
    if s.get("vignette"):
        f.append(f"vignette=angle={0.25 + 0.45 * float(s['vignette']):.3f}")
    if s.get("grain"):
        f.append(f"noise=alls={int(s['grain'])}:allf=t")
    if s.get("sharpen"):
        f.append(f"cas=strength={fnum(min(1, float(s['sharpen'])))}")
    return f


# ======================================================================== pass 2
POSX = {
    "center": ("(W-w)/2", "(H-h)/2"), "top": ("(W-w)/2", "{m}"), "bottom": ("(W-w)/2", "H-h-{m}"),
    "top-left": ("{m}", "{m}"), "top-right": ("W-w-{m}", "{m}"),
    "bottom-left": ("{m}", "H-h-{m}"), "bottom-right": ("W-w-{m}", "H-h-{m}"),
    "full": ("0", "0"),
}


def overlay_xy(pos, W, H, safe=None):
    t, b, l, r = safe or PF.default_safe(W, H)
    mt, mb, ml, mr = int(t * H) + 8, int(b * H) + 8, int(l * W) + 8, int(r * W) + 8
    if isinstance(pos, (list, tuple)):
        return f"{float(pos[0]) * W:.0f}-w/2", f"{float(pos[1]) * H:.0f}-h/2"
    table = {
        "center": ("(W-w)/2", "(H-h)/2"), "top": ("(W-w)/2", f"{mt}"), "bottom": ("(W-w)/2", f"H-h-{mb}"),
        "top-left": (f"{ml}", f"{mt}"), "top-right": (f"W-w-{mr}", f"{mt}"),
        "bottom-left": (f"{ml}", f"H-h-{mb}"), "bottom-right": (f"W-w-{mr}", f"H-h-{mb}"),
        "full": ("(W-w)/2", "(H-h)/2"),
    }
    return table.get(pos or "center", table["center"])


def run_helper(script: str, args: list):
    V.run([V.py_exe(), str(Path(__file__).parent / script)] + [str(a) for a in args])


def plan_safe(plan: Plan, W, H):
    return plan.platform["safe"] if plan.platform else PF.default_safe(W, H)


def apply_brand(plan: Plan, D: float):
    """Brand kit defaults: accent colours/fonts on text and captions, optional logo watermark."""
    b = plan.brand
    if not b:
        return
    colors = b.get("colors", {})
    accent = colors.get("accent") or colors.get("primary")
    ovs = plan.p.setdefault("overlays", [])
    for o in ovs:
        if o.get("type", "text") == "text":
            if accent:
                o.setdefault("accent", accent)
            if b.get("font_heading") and o.get("style") in ("title", "hook", "price", "cta"):
                o.setdefault("font", b["font_heading"])
            elif b.get("font_body"):
                o.setdefault("font", b["font_body"])
            if o.get("style") == "cta" and colors.get("primary"):
                o.setdefault("box_color", colors["primary"])
    cap = plan.p.get("captions")
    if isinstance(cap, dict):
        if accent:
            cap.setdefault("highlight", accent)
        if b.get("font_body"):
            cap.setdefault("font", b["font_body"])
    if b.get("watermark") and b.get("logo") and not any(o.get("_wm") for o in ovs):
        ovs.append({"type": "image", "src": b["logo"], "pos": b.get("watermark_pos", "top-right"),
                    "scale": float(b.get("watermark_scale", 0.11)), "opacity": float(b.get("watermark_opacity", 0.85)),
                    "start": 0, "end": D, "fade": 0, "_wm": True})


def pass2(plan: Plan, W, H, fps, assembled: Path, segs: list, D: float):
    apply_brand(plan, D)
    p = plan.p
    inputs = ["-i", str(assembled)]
    idx = 1
    fc = []

    # ---------- video: grade -> media overlays -> text/captions -> fades
    vf = grade_filters(p.get("grade"), plan.work, plan.res)
    if p.get("letterbox"):  # cinematic bars under every overlay, e.g. "letterbox": 2.39
        bar = int((H - W / float(p["letterbox"])) / 2)
        if bar > 0:
            vf += [f"drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill",
                   f"drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill"]
    vchain = ",".join(vf) if vf else "null"
    fc.append(f"[0:v]{vchain}[g0]")
    cur = "g0"
    media_ovs = [o for o in p.get("overlays", []) if o.get("type", "text") in ("image", "video", "gfx")]
    text_ovs = [o for o in p.get("overlays", []) if o.get("type", "text") == "text"]
    audio_from_ovs = []
    for k, o in enumerate(media_ovs):
        src = str(plan.res(o["src"]))
        st = float(o.get("start", 0))
        info = V.media_info(src)
        is_img = info["is_image"] or (info["duration"] or 0) < 0.05
        if o.get("end") is not None:
            en = float(o["end"])
        elif is_img:
            en = D
        else:
            en = min(D, st + float(o.get("dur", info["duration"] or (D - st))))
        dur = max(0.05, en - st)
        if is_img:
            inputs += ["-loop", "1", "-framerate", fnum(fps), "-t", f"{dur:.3f}", "-i", src]
        else:
            if o.get("loop"):
                inputs += ["-stream_loop", "-1"]
            inputs += ["-t", f"{dur:.3f}", "-i", src]
        ii = idx
        idx += 1
        scale = o.get("scale", 1.0 if o.get("pos") == "full" else 0.25)
        ch = [f"fps={fnum(fps)}", "format=rgba"]
        if o.get("chromakey"):
            r, g, b = V.hex_to_rgb(o["chromakey"])
            ch.append(f"chromakey=0x{r:02X}{g:02X}{b:02X}:{fnum(o.get('similarity', 0.12))}:{fnum(o.get('blend', 0.08))}")
        if o.get("pos") == "full":
            ch.append(f"scale={W}:{H}:force_original_aspect_ratio=decrease")
        else:
            ch.append(f"scale={V.even(W * float(scale))}:-2")
        if o.get("round"):
            ch.append("format=rgba")
        op = float(o.get("opacity", 1.0))
        if op < 1:
            ch.append(f"colorchannelmixer=aa={fnum(op)}")
        fade = float(o.get("fade", 0.3))
        if fade > 0:
            ch.append(f"fade=t=in:st=0:d={fade:.2f}:alpha=1")
            ch.append(f"fade=t=out:st={max(0, dur - fade):.2f}:d={fade:.2f}:alpha=1")
        ch.append(f"setpts=PTS-STARTPTS+{st:.3f}/TB")
        fc.append(f"[{ii}:v]{','.join(ch)}[ov{k}]")
        x, y = overlay_xy(o.get("pos", "center"), W, H, plan_safe(plan, W, H))
        fc.append(f"[{cur}][ov{k}]overlay=x={x}:y={y}:eof_action=pass:enable='between(t,{st:.3f},{en:.3f})'[o{k}]")
        cur = f"o{k}"
        if not is_img and o.get("use_audio") and info["has_audio"]:
            audio_from_ovs.append((ii, st, float(o.get("volume", 1.0))))

    # blurred / pixelated regions (faces, plates, screens): rect = [x, y, w, h] as 0..1 fractions
    for k, b in enumerate([o for o in p.get("overlays", []) if o.get("type") in ("blur", "pixelate")]):
        rx, ry, rw, rh = b.get("rect", [0.35, 0.3, 0.3, 0.4])
        bx, by = V.even(rx * W), V.even(ry * H)
        bw, bh = max(4, V.even(rw * W)), max(4, V.even(rh * H))
        bw, bh = min(bw, W - bx), min(bh, H - by)
        st, en = float(b.get("start", 0)), float(b.get("end", D))
        if b.get("type") == "pixelate":
            px = max(2, int(b.get("strength", 16)))
            eff = f"scale={max(1, bw // px)}:{max(1, bh // px)}:flags=area,scale={bw}:{bh}:flags=neighbor"
        else:
            eff = f"boxblur={int(b.get('strength', 20))}:3"
        fc.append(f"[{cur}]split=2[bm{k}][bs{k}]")
        fc.append(f"[bs{k}]crop={bw}:{bh}:{bx}:{by},{eff}[bb{k}]")
        fc.append(f"[bm{k}][bb{k}]overlay={bx}:{by}:enable='between(t,{st:.3f},{en:.3f})'[bl{k}]")
        cur = f"bl{k}"

    # captions + text overlays as one ASS file
    words = None
    cap = p.get("captions")
    if cap:
        if isinstance(cap, str):
            cap = {"style": cap, "auto": True}
        if cap.get("auto") and not cap.get("words"):
            wj = plan.work / f"auto_words_{assembled.stem}.json"
            if not wj.exists():
                args = [str(assembled), "--out", str(wj), "--model", cap.get("model", "small")]
                if cap.get("language"):
                    args += ["--language", cap["language"]]
                run_helper("transcribe.py", args)
            words = load_words(wj)
        elif cap.get("words") or cap.get("srt"):
            wp = plan.res(cap.get("words") or cap.get("srt"))
            words = load_words(wp)
            words = remap_words(words, wp, segs)
    if words:
        (plan.work / "final_words.json").write_text(json.dumps({"words": words}, ensure_ascii=False), encoding="utf-8")
        if (cap or {}).get("export_srt", True) and not plan.draft:
            words_to_srt(words, plan.output.with_suffix(".srt"))
        if (cap or {}).get("burn", True) is False:
            words = None
    if words or text_ovs:
        ass = plan.work / "overlay_text.ass"
        build_ass(ass, W, H, words, cap or {}, text_ovs, safe=plan_safe(plan, W, H),
                  cap_pos=plan.platform["cap"] if plan.platform else None)
        fc.append(f"[{cur}]ass=filename={ass.name}:fontsdir=fonts:shaping=complex[txt]")
        cur = "txt"
    fade = p.get("fade", {})
    if isinstance(fade, (int, float)):
        fade = {"in": fade, "out": fade}
    vfade = []
    if fade.get("in"):
        vfade.append(f"fade=t=in:st=0:d={float(fade['in']):.2f}")
    if fade.get("out"):
        vfade.append(f"fade=t=out:st={max(0, D - float(fade['out'])):.2f}:d={float(fade['out']):.2f}")
    fc.append(f"[{cur}]{','.join(vfade + ['format=yuv420p'])}[vout]")

    # ---------- audio
    a = p.get("audio", {}) or {}
    fmt = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    voice = a.get("voice", "original")
    if isinstance(voice, str):
        voice = {"mode": voice}
    mode = voice.get("mode", "original")
    if voice.get("isolate") or mode == "isolate":
        sep = plan.work / f"stems_{assembled.stem}"
        if not (sep / "vocals.wav").exists():
            run_helper("separate.py", [str(assembled), "--out-dir", str(sep)])
        inputs += ["-i", str(sep / "vocals.wav")]
        vsrc = f"{idx}:a"
        idx += 1
    elif mode in ("mute", "none"):
        inputs += ["-f", "lavfi", "-t", f"{D:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        vsrc = f"{idx}:a"
        idx += 1
    elif mode not in ("original",) and Path(str(plan.res(mode))).exists():
        inputs += ["-i", str(plan.res(mode))]  # a replacement voice-over file
        vsrc = f"{idx}:a"
        idx += 1
    else:
        vsrc = "0:a"
    vch = [fmt]
    if voice.get("enhance") or voice.get("denoise"):
        vch.append("highpass=f=75")
        dn = voice.get("denoise", "rnn")
        if dn in (True, "rnn") and (plan.work / "std.rnnn").exists() and V.has_filter("arnndn"):
            vch.append("arnndn=m=std.rnnn:mix=0.85")
        elif dn:
            vch.append("afftdn=nr=12:nf=-35:tn=1")
    if voice.get("enhance"):
        vch += ["equalizer=f=180:t=q:w=1.2:g=-1.5", "equalizer=f=3500:t=q:w=1.4:g=2.5",
                "acompressor=threshold=0.1:ratio=3:attack=8:release=180:makeup=1.6", "deesser=i=0.3"]
    if voice.get("gain_db"):
        vch.append(f"volume={fnum(voice['gain_db'])}dB")
    bleeps = a.get("bleeps") or []
    for bp in bleeps:  # mute the voice under each bleep
        vch.append(f"volume=0:enable='between(t,{float(bp['start']):.3f},{float(bp['end']):.3f})'")
    vch += [f"apad=whole_dur={D:.3f}", f"atrim=0:{D:.3f}"]
    fc.append(f"[{vsrc}]{','.join(vch)}[voice]")
    mix = ["voice"]
    if bleeps:
        inputs += ["-f", "lavfi", "-t", f"{D:.3f}", "-i", "sine=f=1000:r=48000"]
        bi = idx
        idx += 1
        inside = "+".join(f"between(t,{float(bp['start']):.3f},{float(bp['end']):.3f})" for bp in bleeps)
        fc.append(f"[{bi}:a]{fmt},volume=0.22,volume=0:enable='not({inside})'[bleep]")
        mix.append("bleep")

    music = a.get("music")
    if isinstance(music, str):
        music = {"src": music}
    if music and music.get("src"):
        mst = float(music.get("start", 0))
        mlen = max(0.1, float(music.get("end", D)) - mst)
        if music.get("loop", True):
            inputs += ["-stream_loop", "-1"]
        inputs += ["-ss", f"{float(music.get('offset', 0)):.3f}", "-i", str(plan.res(music["src"]))]
        mi = idx
        idx += 1
        fin, fout = float(music.get("fade_in", 1.0)), float(music.get("fade_out", 2.0))
        mch = [fmt, f"atrim=0:{mlen:.3f}", "asetpts=PTS-STARTPTS", f"volume={fnum(music.get('gain_db', -16))}dB"]
        if fin:
            mch.append(f"afade=t=in:d={fin:.2f}")
        if fout:
            mch.append(f"afade=t=out:st={max(0, mlen - fout):.2f}:d={fout:.2f}")
        if mst > 0:
            ms = int(mst * 1000)
            mch.append(f"adelay={ms}|{ms}")
        fc.append(f"[{mi}:a]{','.join(mch)}[mus]")
        if music.get("duck", True) and mode not in ("mute", "none"):
            fc.append("[voice]asplit=2[voice_m][voice_sc]")
            amt = float(music.get("duck_amount", 0.6))
            ratio = 4 + 16 * amt
            fc.append(f"[mus][voice_sc]sidechaincompress=threshold=0.025:ratio={ratio:.1f}:attack=20:"
                      f"release=450:makeup=1[musd]")
            mix = ["voice_m", "musd"] + [m for m in mix if m != "voice"]
        else:
            mix.append("mus")

    for k, s in enumerate(a.get("sfx", []) or []):
        inputs += ["-i", str(plan.res(s["src"]))]
        si = idx
        idx += 1
        ms = int(float(s.get("at", 0)) * 1000)
        fc.append(f"[{si}:a]{fmt},volume={fnum(s.get('gain_db', -6))}dB,adelay={ms}|{ms}[sfx{k}]")
        mix.append(f"sfx{k}")
    for k, (ii, st, vol) in enumerate(audio_from_ovs):
        ms = int(st * 1000)
        fc.append(f"[{ii}:a]{fmt},volume={fnum(vol)},adelay={ms}|{ms}[ova{k}]")
        mix.append(f"ova{k}")

    master = []
    if len(mix) > 1:
        fc.append("".join(f"[{m}]" for m in mix) +
                  f"amix=inputs={len(mix)}:duration=first:normalize=0:dropout_transition=0[mixed]")
        msrc = "mixed"
    else:
        msrc = mix[0]
    lufs = a.get("loudness", -23 if plan.platform and plan.platform["name"] == "tv" else -14)
    if lufs is not None and lufs is not False:
        master.append(f"loudnorm=I={fnum(lufs)}:TP=-1.5:LRA=11")
    master += ["aresample=48000", f"atrim=0:{D:.3f}"]
    if fade.get("in"):
        master.append(f"afade=t=in:d={float(fade['in']):.2f}")
    if fade.get("out"):
        master.append(f"afade=t=out:st={max(0, D - float(fade['out'])):.2f}:d={float(fade['out']):.2f}")
    fc.append(f"[{msrc}]{','.join(master)}[aout]")

    # ---------- encode
    out = plan.output
    V.ensure_dir(out.parent)
    q = p.get("quality", "good")
    if plan.draft:
        crf, preset = "30", "ultrafast"
    elif q == "best":
        crf, preset = "17", "slow"
    elif q == "small":
        crf, preset = "26", "veryfast"
    else:
        crf, preset = "20", "veryfast"
    if out.suffix.lower() == ".webm":
        venc = ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-row-mt", "1", "-c:a", "libopus", "-b:a", "160k"]
    else:
        venc = ["-c:v", "libx264", "-preset", preset, "-crf", crf, "-profile:v", "high", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k"]
    tmp = out.with_name(out.stem + ".part" + out.suffix)
    V.ffmpeg(inputs + V.filter_script_args(";\n".join(fc), plan.work, "pass2_filtergraph.txt") + [
                       "-map", "[vout]", "-map", "[aout]",
                       "-r", fnum(fps), "-t", f"{D:.3f}"] + venc + ["-ar", "48000", str(tmp)], cwd=plan.work)
    tmp.replace(out)
    return out


def remap_words(words, words_path: Path, segs: list):
    """Words timed on a source file -> output timeline (drops cut-out words).
    If the transcript is of the assembled/final video, it is returned unchanged."""
    try:
        meta = json.loads(Path(words_path).read_text(encoding="utf-8"))
        src = meta.get("source") if isinstance(meta, dict) else None
    except Exception:
        src = None
    if not src:
        return words
    norm = lambda s: os.path.normcase(os.path.abspath(s)) if s else ""
    srcn = norm(src)
    if not any(norm(s["src"]) == srcn for s in segs if s.get("src")):
        return words
    out = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        for s in segs:
            if s.get("src") and norm(s["src"]) == srcn and s["in"] <= mid < s["out"]:
                st = s["start"] + (max(w["start"], s["in"]) - s["in"]) / s["speed"]
                en = s["start"] + (min(w["end"], s["out"]) - s["in"]) / s["speed"]
                out.append({**w, "start": st, "end": en})
                break
    return out


# ======================================================================== main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--draft", action="store_true", help="fast half-res preview")
    ap.add_argument("--pass1", action="store_true", help="only assemble the cut; print its path")
    ap.add_argument("--variants", help="comma list of platforms/presets, one output each, "
                                       "e.g. youtube,instagram_reels,instagram_feed")
    a = ap.parse_args()
    base = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    variants = [v.strip() for v in (a.variants or "").split(",") if v.strip()] or base.get("variants") or [None]
    results = []
    for v in variants:
        data = copy.deepcopy(base)
        if v:
            data.pop("canvas", None)
            data["platform"] = v
        results.append(render_one(Path(a.plan), data, a.draft, a.pass1, v or ""))
    if len(results) > 1:
        print(json.dumps({"variants": results}, indent=2))


def render_one(plan_path: Path, data: dict, draft: bool, only_pass1: bool, suffix: str):
    plan = Plan(plan_path, draft, data, suffix)
    clips = plan.p.get("clips") or []
    if not clips and plan.p.get("src"):
        clips = [{"src": plan.p["src"]}]
    if not clips:
        sys.exit("[eve] plan has no clips")
    infos = []
    for c in clips:
        if c.get("color") and not c.get("src"):
            c["_type"] = "color"
            infos.append({})
            continue
        src = plan.res(c["src"])
        if not src.exists():
            sys.exit(f"[eve] missing file: {src}")
        c["_src"] = str(src)
        info = V.media_info(src)
        c["_type"] = "image" if info["is_image"] or not info["has_video"] and src.suffix.lower() in V.IMAGE_EXT else "video"
        if c["_type"] == "video" and not info["has_video"]:
            sys.exit(f"[eve] no video stream in {src} (audio files go in audio.music / audio.voice)")
        infos.append(info)
    first = next((i for i in infos if i.get("width")), {})
    W, H, fps = decide_canvas(plan, first)
    print(f"[eve] canvas {W}x{H} @ {fnum(fps)} fps, {len(clips)} clip(s)")
    assembled, segs, D = pass1(plan, W, H, fps, clips, infos)
    if only_pass1:
        r = {"assembled": str(assembled), "duration": round(D, 3), "timeline": str(plan.work / "timeline.json")}
        print(json.dumps(r, indent=2))
        return r
    stab = plan.p.get("stabilize") or (isinstance(plan.p.get("grade"), dict) and plan.p["grade"].get("stabilize"))
    if stab:
        assembled = stabilize(assembled, plan.work, 0.5 if stab is True else float(stab))
    out = pass2(plan, W, H, fps, assembled, segs, D)
    info = V.media_info(out)
    r = {"output": str(out), "duration": round(info["duration"], 2), "size": f"{info['width']}x{info['height']}",
         "fps": info["fps"], "mb": round(out.stat().st_size / 1e6, 1)}
    if plan.output.with_suffix(".srt").exists() and not draft:
        r["srt"] = str(plan.output.with_suffix(".srt"))
    if plan.platform and plan.platform.get("max_s") and info["duration"] > plan.platform["max_s"]:
        r["warning"] = f"longer than {plan.platform['label']} limit ({plan.platform['max_s']} s)"
    print(json.dumps(r, indent=2))
    return r


if __name__ == "__main__":
    main()
