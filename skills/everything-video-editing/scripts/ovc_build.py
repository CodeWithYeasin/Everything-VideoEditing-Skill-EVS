"""Build an OVC (online video commercial) / promo from a scene script.

  python ovc_build.py script.json [--draft] [--storyboard-only] [--only 30s]

script.json (paths relative to the file):
{
  "title": "Eid Offer", "brand": "brand.json",
  "voice": {"voice": "bn-BD-NabanitaNeural", "rate": "+0%", "engine": "auto"},   // TTS for scene "vo"
  "music": {"src": "track.mp3", "gain_db": -16} | {"dir": "D:/Music", "query": "festive upbeat"} | {"mood": "uplifting", "bpm": 118},
  "captions": false,                         // true = burn the VO as captions (from TTS word timings)
  "auto_sfx": true,                          // whoosh on transitions, pop on supers/badges
  "disclaimer": "*Terms apply.",
  "variants": ["youtube", "instagram_reels", "instagram_feed"],     // aspect versions
  "versions": [{"name": "30s"}, {"name": "15s", "scenes": [0, 2, "end"]}],   // cut-downs
  "scenes": [
    {"media": "shots/pour.mp4", "in": 2.0, "vo": "...", "super": "Fresh every day",
     "super_style": "hook", "dur": 3.0, "transition": "fade", "kenburns": "in",
     "badge": {"label": "50% OFF", "price": "৳499", "oldPrice": "৳999"},
     "gfx": {"comp": "FeatureCallout", "props": {...}},            // alpha overlay on this scene
     "card": {"comp": "LogoReveal", "props": {...}}},              // full-frame graphic AS the scene
    ...
  ],
  "end_slate": {"comp": "EndSlate", "props": {"product": "pack.png", "cta": "Order now"}, "dur": 3.5, "vo": "..."}
}
Scene length = max(dur, VO length + 0.6 s). A video shorter than its scene freezes on the
last frame; images get a slow Ken Burns move. Outputs per version x variant:
<Brand>_<Title>_<version>_<variant>.mp4, plus storyboard.html (thumbnails, VO, supers,
timing) for client approval and ovc_report.json.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

import vtools as V
import platforms as PF

HERE = Path(__file__).resolve().parent


def py(script, args, quiet=False):
    return V.run([V.py_exe(), str(HERE / script)] + [str(a) for a in args], capture=quiet)


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9\u0980-\u09FF]+", "-", s).strip("-")[:40] or "ovc"


class Builder:
    def __init__(self, path: Path, draft: bool):
        self.path = path.resolve()
        self.base = self.path.parent
        self.s = json.loads(self.path.read_text(encoding="utf-8"))
        self.draft = draft
        self.out = V.ensure_dir(self.base / self.s.get("output_dir", "ovc_out"))
        self.work = V.ensure_dir(self.out / ".ovc_work")
        self.brand = {}
        if self.s.get("brand"):
            bp = self.res(self.s["brand"])
            self.brand = json.loads(bp.read_text(encoding="utf-8"))
            self.brand_path = bp
        self.accent = (self.brand.get("colors", {}) or {}).get("accent", "#FFB703")

    def res(self, p) -> Path:
        q = Path(str(p))
        return q if q.is_absolute() else (self.base / q).resolve()

    # ------------------------------------------------------------- voice
    def tts(self, text: str, key: str) -> tuple[Path, list, float]:
        v = self.s.get("voice", {}) or {}
        h = hashlib.sha1(json.dumps([text, v], ensure_ascii=False).encode()).hexdigest()[:10]
        wav = self.work / f"vo_{key}_{h}.wav"
        wj = wav.with_suffix(".words.json")
        if not wav.exists() or not wj.exists():
            sys.path.insert(0, str(HERE))
            import tts as T
            T.synth(text, wav, v.get("voice"), v.get("rate", "+0%"), v.get("pitch", "+0Hz"), v.get("engine", "auto"))
        words = json.loads(wj.read_text(encoding="utf-8"))["words"]
        return wav, words, V.media_info(wav)["duration"]

    # ------------------------------------------------------------- graphics
    def gfx(self, comp: str, props: dict, size: tuple, dur: float, tag: str) -> Path:
        props = dict(props or {})
        h = hashlib.sha1(json.dumps([comp, props, size, dur], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:10]
        pj = self.work / f"props_{tag}_{h}.json"
        # resolve local media relative to the script
        for k, val in list(props.items()):
            if isinstance(val, str) and Path(val).suffix and (self.base / val).exists():
                props[k] = str((self.base / val).resolve())
        pj.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        alpha = comp not in ("LogoReveal", "EndSlate", "BeforeAfter", "EndCard") and props.get("bg", "transparent") == "transparent"
        out = self.work / f"gfx_{tag}_{h}_{size[0]}x{size[1]}.{'mov' if alpha else 'mp4'}"
        if not out.exists():
            args = [comp, "--props", pj, "--size", f"{size[0]}x{size[1]}", "--dur", f"{dur:.2f}", "--out", out]
            if self.brand:
                args += ["--brand", self.brand_path]
            py("remotion_gfx.py", args)
        return out

    # ------------------------------------------------------------- music
    def music(self, total: float) -> dict | None:
        m = self.s.get("music")
        if not m:
            return None
        if m.get("src"):
            return {"src": str(self.res(m["src"])), "gain_db": m.get("gain_db", -16), "duck": True,
                    "offset": m.get("offset", 0)}
        if m.get("dir") and m.get("query"):
            r = py("clap_rank.py", ["--dir", self.res(m["dir"]), "--query", m["query"], "--top", "1"], quiet=True)
            try:
                best = json.loads(r.stdout)[m["query"]][0]["file"]
                return {"src": best, "gain_db": m.get("gain_db", -16), "duck": True}
            except Exception:
                print("[eve] CLAP pick failed, using a synth bed", file=sys.stderr)
        bed = self.work / f"bed_{m.get('mood', 'uplifting')}_{int(total)}.wav"
        if not bed.exists():
            py("sfx_synth.py", ["bed", "--mood", m.get("mood", "uplifting"), "--bpm", m.get("bpm", 110),
                                "--dur", f"{total + 1:.1f}", "--out", bed], quiet=True)
        return {"src": str(bed), "gain_db": m.get("gain_db", -14), "duck": True}

    def sfx(self) -> dict:
        d = self.work / "sfx"
        if not (d / "whoosh.wav").exists():
            py("sfx_synth.py", ["all", "--out-dir", d], quiet=True)
        return {k: str(d / f"{k}.wav") for k in ("whoosh", "pop", "impact", "ding", "sparkle")}

    # ------------------------------------------------------------- one version x variant
    def scene_list(self, version: dict) -> list:
        scenes = list(self.s.get("scenes", []))
        end = self.s.get("end_slate")
        pick = version.get("scenes")
        out = []
        if pick:
            for k in pick:
                if k == "end":
                    if end:
                        out.append(dict(end, _end=True))
                else:
                    out.append(scenes[int(k)])
        else:
            out = scenes + ([dict(end, _end=True)] if end else [])
        return out

    def build(self, version: dict, variant: str | None):
        plat = PF.get(variant) if variant else None
        size = plat["size"] if plat else tuple(self.s.get("size", (1920, 1080)))
        scenes = self.scene_list(version)
        # 1) durations from VO
        lead = 0.25
        prepared = []
        for i, sc in enumerate(scenes):
            vo = sc.get("vo")
            vow, words, vodur = (None, [], 0.0)
            if sc.get("vo_file"):
                vow = self.res(sc["vo_file"])
                vodur = V.media_info(vow)["duration"]
            elif vo:
                vow, words, vodur = self.tts(vo, f"s{i}")
            d = max(float(sc.get("dur", 0) or 0), vodur + lead + 0.35 if vodur else 0, 1.2)
            prepared.append(dict(sc=sc, vo=vow, words=words, vodur=vodur, d=d))
        # 2) timeline starts (same overlap rule as render.py transitions)
        L, starts = 0.0, []
        for i, p in enumerate(prepared):
            t = p["sc"].get("transition") if i else None
            td = 0.0
            if t and (t if isinstance(t, str) else t.get("type", "cut")) != "cut":
                td = float((t.get("dur") if isinstance(t, dict) else None) or 0.4)
                td = min(td, prepared[i - 1]["d"] * 0.45, p["d"] * 0.45)
            st = max(0.0, L - td)
            starts.append(st)
            L = st + p["d"]
        total = L
        # 3) clips, overlays, voice track, captions
        clips, overlays, sfx_list, cap_words = [], [], [], []
        sx = self.sfx() if self.s.get("auto_sfx", True) else {}
        for i, (p, st) in enumerate(zip(prepared, starts)):
            sc, d = p["sc"], p["d"]
            clip: dict = {}
            if sc.get("card") or sc.get("_end"):
                g = sc.get("card") or sc
                comp = g.get("comp", "EndSlate")
                props = dict(g.get("props", {}))
                if comp == "EndSlate" and self.s.get("disclaimer"):
                    props.setdefault("disclaimer", self.s["disclaimer"])
                clip = {"src": str(self.gfx(comp, props, size, d, f"card{i}")), "mute": True}
            elif sc.get("media"):
                m = self.res(sc["media"])
                info = V.media_info(m)
                if info["is_image"]:
                    clip = {"src": str(m), "duration": d, "kenburns": sc.get("kenburns", ["in", "out", "left", "right"][i % 4])}
                else:
                    cin = float(sc.get("in", 0))
                    clip = {"src": str(m), "in": cin, "out": min(info["duration"], cin + d * float(sc.get("speed", 1))),
                            "dur": d, "speed": float(sc.get("speed", 1)), "volume": float(sc.get("volume", 0.0))}
                    if sc.get("zoom"):
                        clip["zoom"] = sc["zoom"]
            else:
                clip = {"color": sc.get("color", (self.brand.get("colors", {}) or {}).get("bg", "#111111")), "duration": d}
            if i and sc.get("transition"):
                clip["transition"] = sc["transition"]
                if sx and (sc["transition"] if isinstance(sc["transition"], str) else sc["transition"].get("type")) != "cut":
                    sfx_list.append({"src": sx["whoosh"], "at": max(0, st - 0.25), "gain_db": -10})
            clips.append(clip)
            if sc.get("super"):
                sup = sc["super"] if isinstance(sc["super"], dict) else {"text": sc["super"]}
                overlays.append({"type": "text", "style": sup.get("style", sc.get("super_style", "hook")),
                                 "text": sup["text"], "pos": sup.get("pos", "upper-third"),
                                 "start": st + 0.2, "end": st + d - 0.15, **{k: v for k, v in sup.items()
                                                                            if k not in ("text", "style", "pos")}})
                if sx:
                    sfx_list.append({"src": sx["pop"], "at": st + 0.2, "gain_db": -12})
            if sc.get("badge"):
                g = self.gfx("OfferBadge", sc["badge"], size, d - 0.1, f"badge{i}")
                overlays.append({"type": "video", "src": str(g), "pos": "full", "start": st + 0.1, "fade": 0})
                if sx:
                    sfx_list.append({"src": sx["impact"], "at": st + 0.1, "gain_db": -9})
            if sc.get("gfx"):
                g = self.gfx(sc["gfx"]["comp"], sc["gfx"].get("props", {}), size, d - 0.1, f"gfx{i}")
                overlays.append({"type": "video", "src": str(g), "pos": "full", "start": st + 0.05, "fade": 0})
            if sc.get("_end") and sx:
                sfx_list.append({"src": sx["sparkle"], "at": st + 0.2, "gain_db": -12})
            if p["words"]:
                cap_words += [{**w, "start": w["start"] + st + lead, "end": w["end"] + st + lead, "brk": k == 0}
                              for k, w in enumerate(p["words"])]
        # voice track: each scene's VO at its start (+lead)
        vo_parts = [(p["vo"], st + lead) for p, st in zip(prepared, starts) if p["vo"]]
        vo_track = None
        if vo_parts:
            vo_track = self.work / f"vo_track_{hashlib.sha1(json.dumps([str(v) + str(t) for v, t in vo_parts]).encode()).hexdigest()[:8]}.wav"
            if not vo_track.exists():
                args, fc = [], []
                for k, (wv, t) in enumerate(vo_parts):
                    args += ["-i", str(wv)]
                    ms = int(t * 1000)
                    fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{k}]")
                fc.append("".join(f"[v{k}]" for k in range(len(vo_parts))) +
                          f"amix=inputs={len(vo_parts)}:normalize=0:duration=longest,apad=whole_dur={total:.3f},"
                          f"atrim=0:{total:.3f}[vo]")
                V.ffmpeg(args + ["-filter_complex", ";".join(fc), "-map", "[vo]", "-c:a", "pcm_s16le", str(vo_track)])
        if self.s.get("disclaimer"):  # on live-action scenes; cards/end slate carry their own layout
            for p, st in zip(prepared, starts):
                if not (p["sc"].get("card") or p["sc"].get("_end")):
                    overlays.append({"type": "text", "style": "disclaimer", "text": self.s["disclaimer"],
                                     "start": st, "end": st + p["d"]})
        name = "_".join(x for x in [slug(self.brand.get("name", "")), slug(self.s.get("title", "OVC")),
                                    version.get("name", ""), (plat or {}).get("name", "")] if x)
        plan = {"output": str(self.out / f"{name}.mp4"), "clips": clips, "overlays": overlays,
                "grade": self.s.get("grade", "vibrant"), "fit": self.s.get("fit", "crop"),
                "audio": {"voice": {"mode": str(vo_track) if vo_track else "mute", "enhance": bool(vo_track)},
                          "sfx": sfx_list, "loudness": self.s.get("loudness", -23 if variant == "tv" else -14)},
                "fade": {"in": 0.15, "out": 0.3}, "quality": "best" if not self.draft else "good"}
        if plat:
            plan["platform"] = plat["name"]
        else:
            plan["canvas"] = {"w": size[0], "h": size[1], "fps": self.s.get("fps", 30)}
        if self.s.get("brand"):
            plan["brand"] = str(self.brand_path)
        mus = self.music(total)
        if mus:
            plan["audio"]["music"] = mus
        if self.s.get("captions") and cap_words:
            wj = self.work / f"cap_{name}.json"
            wj.write_text(json.dumps({"words": cap_words}, ensure_ascii=False), encoding="utf-8")
            plan["captions"] = {"words": str(wj), "style": self.s.get("caption_style", "clean")}
        pj = self.out / f"{name}.plan.json"
        pj.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        return pj, total, prepared, starts

    # ------------------------------------------------------------- storyboard
    def storyboard(self, prepared, starts, size) -> Path:
        rows = []
        for i, (p, st) in enumerate(zip(prepared, starts)):
            sc = p["sc"]
            thumb = ""
            src = sc.get("media")
            if src and self.res(src).exists():
                info = V.media_info(self.res(src))
                t = 0 if info["is_image"] else float(sc.get("in", 0)) + min(1.0, p["d"] / 2)
                jpg = self.work / f"sb_{i}.jpg"
                subprocess.run([V.need("ffmpeg"), "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(self.res(src)),
                                "-frames:v", "1", "-vf", "scale=360:-2", str(jpg)], check=False)
                if jpg.exists():
                    thumb = f'<img src="data:image/jpeg;base64,{base64.b64encode(jpg.read_bytes()).decode()}">'
            label = "END SLATE" if sc.get("_end") else (sc.get("card", {}) or {}).get("comp", "")
            sup = sc.get("super")
            sup = sup.get("text") if isinstance(sup, dict) else sup
            rows.append(f"<tr><td>{i + 1}</td><td>{thumb or html.escape(label or 'colour')}</td>"
                        f"<td>{st:.1f}s - {st + p['d']:.1f}s<br><small>{p['d']:.1f}s</small></td>"
                        f"<td>{html.escape(sc.get('vo', '') or '')}</td><td>{html.escape(sup or '')}</td>"
                        f"<td>{html.escape(', '.join(k for k in ('badge', 'gfx', 'card') if sc.get(k)))}</td></tr>")
        title = html.escape(self.s.get("title", "OVC"))
        doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>{title} storyboard</title>
<style>body{{font-family:'Hind Siliguri','Noto Sans Bengali',system-ui,sans-serif;margin:24px;color:#222}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px;vertical-align:top}}
th{{background:{self.accent};color:#111;text-align:left}}img{{width:220px;border-radius:6px}}</style></head>
<body><h1>{title}</h1><p>{html.escape(self.brand.get('name', ''))} · {size[0]}x{size[1]} · approx
{starts[-1] + prepared[-1]['d']:.1f}s</p><table><tr><th>#</th><th>Frame</th><th>Time</th><th>VO</th>
<th>Super</th><th>Graphics</th></tr>{''.join(rows)}</table></body></html>"""
        out = self.out / "storyboard.html"
        out.write_text(doc, encoding="utf-8")
        return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--storyboard-only", action="store_true", help="TTS + timing + storyboard.html, no render")
    ap.add_argument("--only", help="build just this version name")
    a = ap.parse_args()
    b = Builder(Path(a.script), a.draft)
    versions = b.s.get("versions") or [{"name": ""}]
    if a.only:
        versions = [v for v in versions if v.get("name") == a.only]
    variants = b.s.get("variants") or [None]
    report = {"outputs": []}
    sb = None
    for ver in versions:
        for var in variants:
            pj, total, prepared, starts = b.build(ver, var)
            if sb is None:
                size = PF.get(var)["size"] if var and PF.get(var) else tuple(b.s.get("size", (1920, 1080)))
                sb = b.storyboard(prepared, starts, size)
                report["storyboard"] = str(sb)
            if a.storyboard_only:
                report["outputs"].append({"plan": str(pj), "duration": round(total, 2)})
                continue
            args = [pj] + (["--draft"] if a.draft else [])
            r = py("render.py", args, quiet=True)
            try:
                res = json.loads(r.stdout[r.stdout.index("{"):])
            except Exception:
                res = {"plan": str(pj)}
            res["version"], res["variant"] = ver.get("name", ""), var or ""
            m = re.fullmatch(r"(\d+(?:\.\d+)?)s", ver.get("name", "") or "")
            if m and total > float(m.group(1)) + 0.3:
                res["warning"] = (f"{total:.1f}s is longer than the {m.group(0)} target: shorten VO lines, "
                                  f"raise voice rate (e.g. +15%) or drop a scene")
            report["outputs"].append(res)
            print(json.dumps(res, ensure_ascii=False), flush=True)
    (b.out / "ovc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
