"""Build styled ASS subtitle files: word-by-word captions and text overlays.

ASS is rendered by ffmpeg's libass with HarfBuzz shaping, so Bangla, Arabic,
Hindi and emoji-free Latin text all render correctly with the bundled fonts.

CLI:
  python captions.py words.json --out captions.ass --size 1080x1920 --style pop
  python captions.py subs.srt  --out captions.ass --size 1920x1080 --style clean
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from vtools import hex_to_rgb

BANGLA = re.compile(r"[ঀ-৿]")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
ARABIC = re.compile(r"[؀-ۿ]")

FILLERS = {"um", "uh", "uhm", "umm", "uhh", "erm", "er", "ah", "ahh", "hmm", "mm", "mhm",
           "উম", "উমম", "আম", "অ্যা", "এ্যা"}


def ass_color(c: str, alpha: int = 0) -> str:
    r, g, b = hex_to_rgb(c)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def esc(text: str) -> str:
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def pick_font(text: str, latin_font: str) -> str:
    if BANGLA.search(text):
        return "Hind Siliguri"
    if DEVANAGARI.search(text) or ARABIC.search(text):
        return "Noto Sans"  # system fallback; libass falls back via fontconfig
    return latin_font


# Caption style presets. Sizes are fractions of canvas height (portrait) or
# width-scaled for landscape; see _size().
STYLES = {
    "clean":   dict(font="Poppins", bold=True, size=0.050, color="#FFFFFF", outline_c="#000000",
                    outline=0.0040, shadow=0.0, pos=0.90, per_line=7, upper=False, highlight=None, box=False),
    "pop":     dict(font="Poppins ExtraBold", bold=False, size=0.070, color="#FFFFFF", outline_c="#000000",
                    outline=0.0070, shadow=0.002, pos=0.70, per_line=3, upper=True, highlight="#FFD400", box=False),
    "bold":    dict(font="Anton", bold=False, size=0.080, color="#FFFFFF", outline_c="#000000",
                    outline=0.0060, shadow=0.0, pos=0.62, per_line=2, upper=True, highlight="#39FF14", box=False),
    "karaoke": dict(font="Poppins", bold=True, size=0.055, color="#FFFFFF", outline_c="#000000",
                    outline=0.0040, shadow=0.0, pos=0.85, per_line=6, upper=False, highlight="#00D1FF", box=False),
    "box":     dict(font="Poppins", bold=True, size=0.045, color="#FFFFFF", outline_c="#000000",
                    outline=0.0100, shadow=0.0, pos=0.88, per_line=7, upper=False, highlight=None, box=True),
    "minimal": dict(font="Poppins", bold=False, size=0.038, color="#FFFFFF", outline_c="#000000",
                    outline=0.0025, shadow=0.0015, pos=0.92, per_line=8, upper=False, highlight=None, box=False),
}


def _size(frac: float, w: int, h: int) -> int:
    # portrait: relative to height-ish; landscape: relative to width so text isn't huge
    base = h if h >= w else w * 0.5625
    return max(12, int(round(frac * base)))


class AssDoc:
    def __init__(self, w: int, h: int, safe=None, cap_pos=None):
        self.w, self.h = w, h
        # platform UI safe zone as fractions (top, bottom, left, right)
        self.safe = tuple(safe) if safe else ((0.10, 0.22, 0.06, 0.08) if h > w * 1.3 else (0.05, 0.08, 0.05, 0.05))
        self.cap_pos = cap_pos
        self.styles: list[str] = []
        self.events: list[str] = []

    def style(self, name, font, size, color="#FFFFFF", outline_c="#000000", outline=3, shadow=0,
              bold=False, align=2, margin_v=40, margin_lr=60, box=False, back_c="#000000", back_alpha=0x60):
        border_style = 3 if box else 1
        back = ass_color(back_c if box else "#000000", back_alpha if box else 0x80)
        self.styles.append(
            f"Style: {name},{font},{size},{ass_color(color)},{ass_color(color)},{ass_color(outline_c)},"
            f"{back},{-1 if bold else 0},0,0,0,100,100,0,0,{border_style},{outline},{shadow},{align},"
            f"{margin_lr},{margin_lr},{margin_v},1")

    def event(self, start, end, style, text, layer=0):
        if end - start < 0.04:
            return
        self.events.append(f"Dialogue: {layer},{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}")

    def write(self, path):
        head = (
            "[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
            f"PlayResX: {self.w}\nPlayResY: {self.h}\nYCbCr Matrix: TV.709\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
            "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            + "\n".join(self.styles) +
            "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            + "\n".join(self.events) + "\n")
        Path(path).write_text(head, encoding="utf-8")


# ---------------------------------------------------------------- word captions
def group_words(words, max_words=3, max_chars=28, max_gap=0.6):
    lines, cur = [], []
    for w in words:
        txt = w["word"].strip()
        if not txt:
            continue
        if cur:
            gap = w["start"] - cur[-1]["end"]
            chars = sum(len(x["word"]) + 1 for x in cur) + len(txt)
            ends_sentence = re.search(r"[.!?।,;:]$", cur[-1]["word"].strip())
            if len(cur) >= max_words or chars > max_chars or gap > max_gap or ends_sentence or w.get("brk"):
                lines.append(cur)
                cur = []
        cur.append({**w, "word": txt})
    if cur:
        lines.append(cur)
    return lines


def add_word_captions(doc: AssDoc, words: list, cfg: dict):
    st = dict(STYLES.get(cfg.get("style", "clean"), STYLES["clean"]))
    for k in ("font", "color", "highlight", "upper", "per_line", "pos", "box"):
        if k in cfg:
            st[k] = cfg[k]
    if "size" in cfg:
        st["size"] = cfg["size"] if cfg["size"] < 1 else cfg["size"] / doc.h
    if "pos" not in cfg:
        limit = doc.cap_pos if doc.cap_pos else 1 - doc.safe[1] - 0.02
        st["pos"] = min(st["pos"], limit)
    if cfg.get("drop_fillers", True):
        words = [w for w in words if re.sub(r"[^\wঀ-৿]", "", w["word"].lower()) not in FILLERS]
    sample = " ".join(w["word"] for w in words[:50])
    font = pick_font(sample, st["font"])
    is_bn = font == "Hind Siliguri"
    size = _size(st["size"] * (0.9 if is_bn else 1.0), doc.w, doc.h)
    outline = max(1, round(st["outline"] * (doc.h if doc.h >= doc.w else doc.w * 0.5625), 1))
    shadow = round(st["shadow"] * doc.h, 1)
    margin_v = int(doc.h * (1 - st["pos"]))
    margin_lr = int(doc.w * max(0.08, doc.safe[2] + 0.02, doc.safe[3] + 0.02))
    doc.style("Cap", font, size, st["color"], st["outline_c"], outline, shadow,
              bold=st["bold"] or is_bn, align=2, margin_v=margin_v, margin_lr=margin_lr, box=st["box"])
    max_chars = int(cfg.get("max_chars", 34 if doc.w > doc.h else 22))
    lines = group_words(words, int(st["per_line"]), max_chars, float(cfg.get("max_gap", 0.6)))
    hl = st.get("highlight")
    style_name = cfg.get("style", "clean")
    upper = st["upper"] and not is_bn
    for li, line in enumerate(lines):
        start = line[0]["start"]
        nxt = lines[li + 1][0]["start"] if li + 1 < len(lines) else line[-1]["end"] + 0.4
        end = min(line[-1]["end"] + 0.35, nxt)
        toks = [esc(w["word"].upper() if upper else w["word"]) for w in line]
        if style_name == "karaoke":
            parts = []
            for i, w in enumerate(line):
                dur_cs = max(1, int(round((w["end"] - w["start"]) * 100)))
                parts.append(f"{{\\kf{dur_cs}}}{toks[i]}")
            lead = max(0, int(round((line[0]["start"] - start) * 100)))
            text = (f"{{\\k{lead}}}" if lead else "") + " ".join(parts)
            doc.events.append(
                f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,"
                f"{{\\1c{ass_color(hl or '#00D1FF')}\\2c{ass_color(st['color'])}}}{text}")
            continue
        if hl:
            # one event per word: whole line visible, current word coloured + popped
            for i, w in enumerate(line):
                ws = w["start"] if i else start
                we = line[i + 1]["start"] if i + 1 < len(line) else end
                parts = []
                for j, t in enumerate(toks):
                    if j == i:
                        pop = "\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)" if style_name in ("pop", "bold") else ""
                        parts.append(f"{{\\1c{ass_color(hl)}{pop}}}{t}{{\\1c{ass_color(st['color'])}\\fscx100\\fscy100}}")
                    else:
                        parts.append(t)
                intro = "{\\fad(60,0)}" if i == 0 else ""
                doc.event(ws, we, "Cap", intro + " ".join(parts))
        else:
            doc.event(start, end, "Cap", "{\\fad(80,80)}" + " ".join(toks))


# ---------------------------------------------------------------- text overlays
def positions(safe) -> dict:
    """Named anchor points (x, y, ass alignment) kept inside the platform safe zone."""
    t, b, l, r = safe
    top, bot = t + 0.02, 1 - b - 0.015
    left, right = l + 0.02, 1 - r - 0.02
    return {
        "center": (0.5, 0.5, 5), "top": (0.5, top, 8), "bottom": (0.5, bot, 2),
        "top-left": (left, top, 7), "top-right": (right, top, 9),
        "bottom-left": (left, bot, 1), "bottom-right": (right, bot, 3),
        "upper-third": (0.5, max(0.30, t + 0.08), 5),
        "lower-third": (left, min(0.80, bot - 0.02), 1),
    }


POS = positions((0.05, 0.08, 0.05, 0.05))


def add_text_overlay(doc: AssDoc, ov: dict, idx: int):
    text = str(ov.get("text", ""))
    kind = ov.get("style", "text")
    start, end = float(ov.get("start", 0)), float(ov.get("end", ov.get("start", 0) + 3))
    color = ov.get("color", "#FFFFFF")
    accent = ov.get("accent", "#FFD400")
    defaults = {
        "title":    dict(font="Anton", size=0.11, pos="center", box=False, outline=0.004),
        "hook":     dict(font="Poppins ExtraBold", size=0.065, pos="upper-third", box=True, outline=0.012),
        "subtitle": dict(font="Poppins", size=0.045, pos="bottom", box=False, outline=0.003),
        "lower_third": dict(font="Poppins", size=0.042, pos="lower-third", box=True, outline=0.010),
        "label":    dict(font="Poppins", size=0.035, pos="top-left", box=True, outline=0.008),
        "text":     dict(font="Poppins", size=0.05, pos="center", box=False, outline=0.003),
        "disclaimer": dict(font="Poppins", size=0.022, pos="bottom", box=False, outline=0.0015),
        "price":    dict(font="Anton", size=0.09, pos="upper-third", box=True, outline=0.012),
        "cta":      dict(font="Poppins ExtraBold", size=0.055, pos="bottom", box=True, outline=0.012),
    }.get(kind, {})
    font = pick_font(text, ov.get("font", defaults.get("font", "Poppins")))
    frac = ov.get("size", defaults.get("size", 0.05))
    size = _size(frac if frac < 1 else frac / doc.h, doc.w, doc.h)
    pos = ov.get("pos", defaults.get("pos", "center"))
    if isinstance(pos, (list, tuple)):
        x, y, al = float(pos[0]), float(pos[1]), int(ov.get("align", 5))
    else:
        anchors = positions(doc.safe)
        x, y, al = anchors.get(pos, anchors["center"])
    px, py = int(x * doc.w), int(y * doc.h)
    if kind == "cta" and pos == "bottom":  # leave the bottom line for captions / disclaimer
        py -= int(0.08 * doc.h)
    box = ov.get("box", defaults.get("box", False))
    outline = max(1, round(defaults.get("outline", 0.004) * doc.h, 1)) if not box else max(4, int(size * 0.28))
    name = f"T{idx}"
    if kind == "cta" and "box_color" not in ov:
        ov = dict(ov, box_color=accent)
    doc.style(name, font, size, color, ov.get("box_color", "#000000") if box else ov.get("outline_color", "#000000"),
              outline, 0, bold=kind != "disclaimer", align=al, box=box, back_c=ov.get("box_color", "#000000"),
              back_alpha=int(ov.get("box_alpha", 0x30)))
    fade_ms = int(float(ov.get("fade", 0.25)) * 1000)
    anim = ov.get("anim", {"title": "pop", "hook": "pop", "price": "pop", "cta": "pop",
                           "lower_third": "slide"}.get(kind, "fade"))
    body = esc(text if not ov.get("upper", kind in ("title", "hook", "price", "cta")) or BANGLA.search(text)
               else text.upper())
    if kind == "price" and ov.get("old"):  # "<s>৳1,200</s> ৳899"
        body = f"{{\\fs{int(size * 0.5)}\\s1\\alpha&H40&}}{esc(str(ov['old']))}{{\\s0\\alpha&H00&\\fs{size}}} " + body
    if kind == "disclaimer":
        body = "{\\alpha&H30&}" + body
    if kind == "lower_third" and ov.get("sub"):
        sub_size = int(size * 0.68)
        body += f"\\N{{\\fs{sub_size}\\b0\\1c{ass_color(accent)}}}{esc(str(ov['sub']))}"
    tags = f"\\pos({px},{py})\\fad({fade_ms},{fade_ms})"
    if anim == "pop":
        tags += "\\fscx70\\fscy70\\t(0,220,\\fscx108\\fscy108)\\t(220,360,\\fscx100\\fscy100)"
    elif anim == "slide":
        off = int(doc.w * 0.25) * (1 if x < 0.5 else -1)
        tags = f"\\move({px - off},{py},{px},{py},0,350)\\fad({fade_ms},{fade_ms})"
    elif anim == "rise":
        tags = f"\\move({px},{py + int(doc.h * 0.05)},{px},{py},0,400)\\fad({fade_ms},{fade_ms})"
    elif anim == "typewriter":
        n = max(1, len(body))
        step = max(1, int(min(60, 1000 * min(1.5, (end - start) * 0.5) / n)))
        body = "".join(f"{{\\alpha&HFF&\\t({i * step},{i * step + 1},\\alpha&H00&)}}{esc(ch)}" for i, ch in enumerate(text))
        tags = f"\\pos({px},{py})"
    doc.event(start, end, name, f"{{{tags}}}{body}", layer=5)


def build_ass(path, w, h, words=None, captions_cfg=None, overlays=None, safe=None, cap_pos=None):
    doc = AssDoc(w, h, safe, cap_pos)
    if any(o.get("style") == "disclaimer" for o in overlays or []):  # keep captions above the legal line
        doc.cap_pos = (doc.cap_pos or 1 - doc.safe[1] - 0.02) - 0.035
    if words:
        add_word_captions(doc, words, captions_cfg or {})
    for i, ov in enumerate(overlays or []):
        add_text_overlay(doc, ov, i)
    doc.write(path)
    return path


def _srt_t(t: float) -> str:
    ms = int(round(max(0.0, t) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def words_to_srt(words: list, path, max_chars: int = 42, drop_fillers: bool = True):
    """Closed-caption file (upload to YouTube/Facebook instead of, or as well as, burning in)."""
    if drop_fillers:
        words = [w for w in words if re.sub(r"[^\wঀ-৿]", "", w["word"].lower()) not in FILLERS]
    lines = group_words(words, max_words=12, max_chars=max_chars, max_gap=0.9)
    out = []
    for i, line in enumerate(lines, 1):
        out.append(f"{i}\n{_srt_t(line[0]['start'])} --> {_srt_t(line[-1]['end'] + 0.2)}\n"
                   + " ".join(w["word"] for w in line) + "\n")
    Path(path).write_text("\n".join(out), encoding="utf-8")
    return path


# ---------------------------------------------------------------- loaders
def load_words(path) -> list:
    p = Path(path)
    if p.suffix.lower() == ".srt":
        return srt_to_words(p.read_text(encoding="utf-8-sig"))
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if data.get("words"):
        return data["words"]
    out = []
    for seg in data.get("segments", []):
        out.extend(seg.get("words") or [{"start": seg["start"], "end": seg["end"], "word": seg["text"]}])
    return out


def srt_to_words(txt: str) -> list:
    """Spread each SRT cue's words evenly across its time span."""
    out = []
    for block in re.split(r"\n\s*\n", txt.strip()):
        lines = [l for l in block.strip().splitlines() if l.strip()]
        tl = next((l for l in lines if "-->" in l), None)
        if not tl:
            continue
        a, b = [x.strip().replace(",", ".") for x in tl.split("-->")]

        def sec(s):
            hh, mm, ss = s.split(":")
            return int(hh) * 3600 + int(mm) * 60 + float(ss)
        s, e = sec(a), sec(b.split()[0])
        text = " ".join(lines[lines.index(tl) + 1:])
        toks = text.split()
        if not toks:
            continue
        step = (e - s) / len(toks)
        out += [{"start": s + i * step, "end": s + (i + 1) * step, "word": t} for i, t in enumerate(toks)]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", help="words.json from transcribe.py, or an .srt file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1920x1080", help="WxH of the video")
    ap.add_argument("--style", default="clean", choices=list(STYLES))
    ap.add_argument("--highlight")
    ap.add_argument("--pos", type=float, help="vertical position 0..1 (0.9 = near bottom)")
    a = ap.parse_args()
    w, h = map(int, a.size.lower().split("x"))
    cfg = {"style": a.style}
    if a.highlight:
        cfg["highlight"] = a.highlight
    if a.pos:
        cfg["pos"] = a.pos
    build_ass(a.out, w, h, load_words(a.words), cfg)
    print(a.out)
