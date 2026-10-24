"""One-command everyday edits (no plan needed).

  python quick.py compress in.mp4 --mb 16            # fit a size limit (WhatsApp/email/upload)
  python quick.py gif in.mp4 --start 3 --dur 4 --width 480 --fps 12
  python quick.py convert in.mov --to mp4|webm|mov|mp3|wav|m4a
  python quick.py audio in.mp4 [--to mp3]           # extract audio
  python quick.py mute in.mp4
  python quick.py trim in.mp4 --start 0:12 --end 0:45 [--fast]
  python quick.py speed in.mp4 --x 2                 # 0.25..4, pitch kept
  python quick.py reverse in.mp4
  python quick.py boomerang in.mp4 --start 2 --dur 1.5
  python quick.py rotate in.mp4 --deg 90|180|270 | --flip h|v
  python quick.py resize in.mp4 --size 1080x1920 [--fit blur|crop|pad]
  python quick.py merge a.mp4 b.mp4 c.mp4 [--size 1920x1080]
  python quick.py stack a.mp4 b.mp4 [--layout h|v|grid]   # split screen / reaction / compare
  python quick.py loop in.mp4 --times 3 | --to 30
  python quick.py frames in.mp4 --every 1           # stills (jpg) every N seconds
  python quick.py frame in.mp4 --t 12.5             # one still
  python quick.py scenes in.mp4                      # split into one file per shot
  python quick.py restore old.mp4                    # old/family video: deinterlace, denoise, stabilise, colour, upscale
  python quick.py subs in.mp4 --srt subs.srt [--burn]  # soft (selectable) or burned subtitles
  python quick.py loudness in.mp4 [--lufs -14]       # fix volume only
  python quick.py denoise in.mp4                     # clean voice only
  python quick.py slideshow photos_folder --sec 3 [--music song.mp3] [--size 1080x1920]
Output goes next to the input as <name>_<op>.<ext> unless --out is given.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import vtools as V


def outpath(src: Path, tag: str, ext: str | None = None, out: str | None = None) -> Path:
    if out:
        return Path(out).resolve()
    return src.with_name(f"{src.stem}_{tag}{ext or src.suffix}")


def ts(v) -> float:
    if v is None:
        return 0.0
    t = 0.0
    for part in str(v).split(":"):
        t = t * 60 + float(part)
    return t


ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
       "-c:a", "aac", "-b:a", "160k"]


def fit_vf(w, h, mode):
    if mode == "pad":
        return f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    if mode == "crop":
        return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    return (f"split[a][b];[a]scale={w // 4}:{h // 4}:force_original_aspect_ratio=increase,crop={w // 4}:{h // 4},"
            f"gblur=sigma=10,scale={w}:{h}[bg];[b]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("op")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out")
    ap.add_argument("--mb", type=float)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--dur", type=float)
    ap.add_argument("--width", type=int, default=480)
    ap.add_argument("--fps", type=float, default=12)
    ap.add_argument("--to", default=None)
    ap.add_argument("--x", type=float, default=2.0)
    ap.add_argument("--deg", type=int)
    ap.add_argument("--flip", choices=["h", "v"])
    ap.add_argument("--size")
    ap.add_argument("--fit", default="blur", choices=["blur", "crop", "pad"])
    ap.add_argument("--layout", default="h", choices=["h", "v", "grid"])
    ap.add_argument("--times", type=int)
    ap.add_argument("--every", type=float, default=1.0)
    ap.add_argument("--t", type=float, default=0.0)
    ap.add_argument("--srt")
    ap.add_argument("--burn", action="store_true")
    ap.add_argument("--fast", action="store_true", help="stream copy (cuts on keyframes)")
    ap.add_argument("--lufs", type=float, default=-14)
    ap.add_argument("--sec", type=float, default=3.0)
    ap.add_argument("--music")
    a = ap.parse_args()
    src = Path(a.inputs[0]).resolve()
    op = a.op
    res = {}

    if op == "compress":
        info = V.media_info(src)
        target_kbit = (a.mb or 16) * 8 * 1024 * 0.96
        abr = 96 if a.mb and a.mb < 20 else 128
        vbr = max(150, int(target_kbit / max(1, info["duration"]) - abr))
        w, h = info["width"], info["height"]
        scale = []
        long = max(w, h)
        cap = 1920 if vbr > 4000 else 1280 if vbr > 1500 else 854 if vbr > 600 else 640
        if long > cap:
            scale = ["-vf", f"scale='if(gt(iw,ih),{cap},-2)':'if(gt(iw,ih),-2,{cap})'"]
        out = outpath(src, f"{int(a.mb or 16)}MB", ".mp4", a.out)
        work = V.ensure_dir(out.parent / ".eve_work")
        common = ["-i", str(src)] + scale + ["-c:v", "libx264", "-preset", "medium", "-b:v", f"{vbr}k",
                                             "-pix_fmt", "yuv420p"]
        V.ffmpeg(common + ["-pass", "1", "-passlogfile", "x264pass", "-an", "-f", "mp4", "NUL" if V.IS_WIN else "/dev/null"],
                 cwd=work)
        V.ffmpeg(common + ["-pass", "2", "-passlogfile", "x264pass", "-c:a", "aac", "-b:a", f"{abr}k",
                           "-movflags", "+faststart", str(out)], cwd=work)
        res = {"out": str(out), "mb": round(out.stat().st_size / 1048576, 2), "video_kbps": vbr}

    elif op == "gif":
        out = outpath(src, "clip", ".gif", a.out)
        rng = ["-ss", str(ts(a.start)), "-t", str(a.dur or 4)]
        f = f"fps={a.fps},scale={a.width}:-2:flags=lanczos"
        V.ffmpeg(rng + ["-i", str(src), "-vf", f"{f},split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];"
                        f"[s1][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle", "-loop", "0", str(out)])
        res = {"out": str(out), "mb": round(out.stat().st_size / 1048576, 2)}

    elif op in ("convert", "audio"):
        to = (a.to or ("mp3" if op == "audio" else "mp4")).lstrip(".")
        out = outpath(src, "conv" if op == "convert" else "audio", "." + to, a.out)
        codec = {"mp4": ENC, "mov": ["-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac"],
                 "webm": ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-row-mt", "1", "-c:a", "libopus"],
                 "mp3": ["-vn", "-c:a", "libmp3lame", "-q:a", "2"], "wav": ["-vn", "-c:a", "pcm_s16le"],
                 "m4a": ["-vn", "-c:a", "aac", "-b:a", "192k"]}.get(to)
        if codec is None:
            sys.exit(f"[eve] unknown format {to}")
        V.ffmpeg(["-i", str(src)] + codec + [str(out)])
        res = {"out": str(out)}

    elif op == "mute":
        out = outpath(src, "muted", None, a.out)
        V.ffmpeg(["-i", str(src), "-c:v", "copy", "-an", str(out)])
        res = {"out": str(out)}

    elif op == "trim":
        out = outpath(src, "trim", None, a.out)
        s, e = ts(a.start), ts(a.end) if a.end else None
        rng = ["-ss", f"{s:.3f}"] + (["-to", f"{e:.3f}"] if e else [])
        if a.fast:
            V.ffmpeg(rng + ["-i", str(src), "-c", "copy", "-avoid_negative_ts", "make_zero", str(out)])
        else:
            V.ffmpeg(["-i", str(src)] + rng + ENC + [str(out)])
        res = {"out": str(out)}

    elif op == "speed":
        out = outpath(src, f"{a.x:g}x", None, a.out)
        at, x = [], a.x
        while x > 2:
            at.append("atempo=2")
            x /= 2
        while x < 0.5:
            at.append("atempo=0.5")
            x /= 0.5
        at.append(f"atempo={x:.4f}")
        V.ffmpeg(["-i", str(src), "-filter_complex", f"[0:v]setpts=PTS/{a.x}[v];[0:a]{','.join(at)}[a]",
                  "-map", "[v]", "-map", "[a]?"] + ENC + [str(out)])
        res = {"out": str(out)}

    elif op == "reverse":
        out = outpath(src, "reversed", None, a.out)
        info = V.media_info(src)
        maps = ["-vf", "reverse"] + (["-af", "areverse"] if info["has_audio"] else [])
        V.ffmpeg(["-i", str(src)] + maps + ENC + [str(out)])
        res = {"out": str(out)}

    elif op == "boomerang":
        out = outpath(src, "boomerang", ".mp4", a.out)
        V.ffmpeg(["-ss", str(ts(a.start)), "-t", str(a.dur or 1.5), "-i", str(src), "-filter_complex",
                  "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0,split[c][d];[c][d]concat=n=2:v=1:a=0[v]",
                  "-map", "[v]", "-an"] + ENC[:-4] + [str(out)])
        res = {"out": str(out)}

    elif op == "rotate":
        out = outpath(src, "rotated", None, a.out)
        vf = {90: "transpose=1", 180: "transpose=1,transpose=1", 270: "transpose=2"}.get(a.deg or 0, "")
        if a.flip:
            vf = ",".join(x for x in [vf, "hflip" if a.flip == "h" else "vflip"] if x)
        V.ffmpeg(["-i", str(src), "-vf", vf or "null"] + ENC + [str(out)])
        res = {"out": str(out)}

    elif op == "resize":
        w, h = map(int, (a.size or "1080x1920").lower().split("x"))
        out = outpath(src, f"{w}x{h}", ".mp4", a.out)
        vf = fit_vf(w, h, a.fit)
        V.ffmpeg(["-i", str(src), "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "0:a?"] + ENC + [str(out)])
        res = {"out": str(out)}

    elif op in ("merge", "stack"):
        files = [Path(f).resolve() for f in a.inputs]
        infos = [V.media_info(f) for f in files]
        out = outpath(src, op, ".mp4", a.out)
        args, fc = [], []
        for f in files:
            args += ["-i", str(f)]
        if op == "merge":
            w, h = map(int, (a.size or f"{infos[0]['width']}x{infos[0]['height']}").lower().split("x"))
            w, h = V.even(w), V.even(h)
            for i, inf in enumerate(infos):
                fc.append(f"[{i}:v]{fit_vf(w, h, 'pad').replace('split[a][b];', '')},fps=30,format=yuv420p[v{i}]")
                if inf["has_audio"]:
                    fc.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]")
                else:
                    fc.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{inf['duration']:.3f}[a{i}]")
            fc.append("".join(f"[v{i}][a{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=1:a=1[v][a]")
        else:
            n = len(files)
            cell = (960, 1080) if a.layout == "h" else (1080, 960) if a.layout == "v" else (960, 540)
            for i in range(n):
                fc.append(f"[{i}:v]scale={cell[0]}:{cell[1]}:force_original_aspect_ratio=increase,"
                          f"crop={cell[0]}:{cell[1]},setsar=1,fps=30[v{i}]")
            ins = "".join(f"[v{i}]" for i in range(n))
            if a.layout == "h":
                fc.append(f"{ins}hstack=inputs={n}:shortest=1[v]")
            elif a.layout == "v":
                fc.append(f"{ins}vstack=inputs={n}:shortest=1[v]")
            else:
                pos = ["0_0", "w0_0", "0_h0", "w0_h0"][:n]
                fc.append(f"{ins}xstack=inputs={n}:layout={'|'.join(pos)}:fill=black:shortest=1[v]")
            fc.append("[0:a]anull[a]" if infos[0]["has_audio"] else "anullsrc=r=48000:cl=stereo[a]")
        V.ffmpeg(args + ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-shortest"] + ENC + [str(out)])
        res = {"out": str(out)}

    elif op == "loop":
        info = V.media_info(src)
        times = a.times or max(1, int(-(-float(a.to or 30) // info["duration"])))
        out = outpath(src, f"loop{times}", None, a.out)
        args = ["-stream_loop", str(times - 1), "-i", str(src)] + (["-t", str(ts(a.to))] if a.to else [])
        V.ffmpeg(args + ENC + [str(out)])
        res = {"out": str(out)}

    elif op in ("frames", "frame"):
        outdir = V.ensure_dir(Path(a.out) if a.out else src.with_name(src.stem + "_frames"))
        if op == "frame":
            o = outdir / f"{src.stem}_{a.t:.2f}s.jpg"
            V.ffmpeg(["-ss", str(a.t), "-i", str(src), "-frames:v", "1", "-q:v", "2", str(o)])
            res = {"out": str(o)}
        else:
            V.ffmpeg(["-i", str(src), "-vf", f"fps=1/{a.every}", "-q:v", "2", str(outdir / "frame_%04d.jpg")])
            res = {"out_dir": str(outdir), "count": len(list(outdir.glob("frame_*.jpg")))}

    elif op == "scenes":
        r = V.run([V.need("ffmpeg"), "-hide_banner", "-nostats", "-i", str(src), "-an", "-vf",
                   "scale=320:-2,select='gt(scene,0.32)',showinfo", "-f", "null", "-"], capture=True, check=False)
        cuts = [0.0] + [float(x) for x in re.findall(r"pts_time:([\d.]+)", r.stderr or "")]
        dur = V.media_info(src)["duration"]
        cuts.append(dur)
        outdir = V.ensure_dir(Path(a.out) if a.out else src.with_name(src.stem + "_scenes"))
        files = []
        for i in range(len(cuts) - 1):
            s, e = cuts[i], cuts[i + 1]
            if e - s < 0.4:
                continue
            o = outdir / f"scene_{i + 1:03d}.mp4"
            V.ffmpeg(["-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", str(src)] + ENC + [str(o)])
            files.append({"file": str(o), "start": round(s, 2), "end": round(e, 2)})
        res = {"out_dir": str(outdir), "scenes": files}

    elif op == "restore":
        info = V.media_info(src)
        out = outpath(src, "restored", ".mp4", a.out)
        work = V.ensure_dir(out.parent / ".eve_work")
        short = min(info["width"], info["height"])
        up = min(2.0, 1080 / short) if short < 1080 else 1.0
        tw, th = V.even(info["width"] * up), V.even(info["height"] * up)
        vf = ["bwdif=mode=send_field:deint=interlaced", "hqdn3d=4:3:6:4.5",
              "normalize=blackpt=black:whitept=white:smoothing=30:strength=0.6",
              f"scale={tw}:{th}:flags=lanczos", "cas=strength=0.45", "eq=saturation=1.08"]
        stab = []
        if V.has_filter("vidstabdetect"):
            V.ffmpeg(["-i", str(src), "-vf", "vidstabdetect=shakiness=5:result=rst.trf", "-f", "null", "-"], cwd=work)
            stab = ["vidstabtransform=input=rst.trf:smoothing=20:zoom=3"]
        af = ["highpass=f=70", "afftdn=nr=14:nf=-35", "loudnorm=I=-16:TP=-1.5"]
        V.ffmpeg(["-i", str(src), "-vf", ",".join(stab + vf), "-af", ",".join(af)] + ENC + [str(out)], cwd=work)
        res = {"out": str(out)}

    elif op == "subs":
        if not a.srt:
            sys.exit("[eve] --srt needed")
        srt = Path(a.srt).resolve()
        out = outpath(src, "subbed", ".mp4", a.out)
        if a.burn:
            work = V.ensure_dir(out.parent / ".eve_work")
            V.copy_assets_to(work)
            from captions import build_ass, load_words
            info = V.media_info(src)
            build_ass(work / "subs.ass", info["width"], info["height"], load_words(srt), {"style": "box"})
            V.ffmpeg(["-i", str(src), "-vf", "ass=filename=subs.ass:fontsdir=fonts:shaping=complex"] + ENC + [str(out)],
                     cwd=work)
        else:
            V.ffmpeg(["-i", str(src), "-i", str(srt), "-map", "0", "-map", "1", "-c", "copy", "-c:s", "mov_text",
                      "-metadata:s:s:0", "language=und", str(out)])
        res = {"out": str(out)}

    elif op in ("loudness", "denoise"):
        out = outpath(src, op, None, a.out)
        work = V.ensure_dir(out.parent / ".eve_work")
        V.copy_assets_to(work)
        if op == "loudness":
            af = f"loudnorm=I={a.lufs}:TP=-1.5:LRA=11"
        else:
            af = "highpass=f=75,arnndn=m=std.rnnn:mix=0.85,acompressor=threshold=0.1:ratio=2.5:makeup=1.3" \
                if V.has_filter("arnndn") else "highpass=f=75,afftdn=nr=12:nf=-35"
        vcopy = ["-c:v", "copy"] if V.media_info(src)["has_video"] else ["-vn"]
        V.ffmpeg(["-i", str(src), "-af", af] + vcopy + ["-c:a", "aac", "-b:a", "192k", str(out)], cwd=work)
        res = {"out": str(out)}

    elif op == "slideshow":
        folder = src
        imgs = sorted([p for p in folder.iterdir() if p.suffix.lower() in V.IMAGE_EXT])
        if not imgs:
            sys.exit("[eve] no images in folder")
        moves = ["in", "out", "left", "right"]
        plan = {"output": str(Path(a.out).resolve() if a.out else folder / "slideshow.mp4"),
                "canvas": {"w": int((a.size or "1920x1080").split("x")[0]), "h": int((a.size or "1920x1080").split("x")[1]),
                           "fps": 30},
                "clips": [{"src": str(p), "duration": a.sec, "kenburns": moves[i % 4],
                           **({"transition": {"type": "dissolve", "dur": 0.8}} if i else {})} for i, p in enumerate(imgs)],
                "grade": "warm", "fade": {"in": 1.0, "out": 1.5}, "audio": {"voice": "mute"}}
        if a.music:
            plan["audio"]["music"] = {"src": str(Path(a.music).resolve()), "gain_db": -10, "duck": False}
        pj = folder / "slideshow_plan.json"
        pj.write_text(json.dumps(plan, indent=1), encoding="utf-8")
        V.run([V.py_exe(), str(Path(__file__).parent / "render.py"), str(pj)])
        res = {"out": plan["output"], "plan": str(pj), "photos": len(imgs)}
    else:
        sys.exit(f"[eve] unknown op '{op}'. See: python quick.py -h")
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
