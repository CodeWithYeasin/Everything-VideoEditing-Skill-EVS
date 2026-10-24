"""Generate royalty-free sound effects and simple music beds (pure numpy, no downloads).

  python sfx_synth.py whoosh --out whoosh.wav [--dur 0.6]
  python sfx_synth.py all --out-dir sfx/            # the whole pack
  python sfx_synth.py bed --out bed.wav --dur 60 --mood calm|uplifting|dark|lofi --bpm 90

Effects: whoosh riser impact boom pop click ding notify shutter glitch typing swipe
bass_drop sparkle. Use them on cuts, title pops and transitions (audio.sfx in plan.json).
The beds are simple chord pads with a soft beat: fine under speech, not a hit song.
For real music use the user's library with clap_rank.py.
"""
from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def t(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.01, r=0.2, curve=3.0):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    if nr < n:
        e[-nr:] = np.linspace(1, 0, nr) ** curve
    return e


def lowpass(x, cut):
    # one-pole low-pass with time-varying cutoff (array or float)
    cut = np.broadcast_to(np.asarray(cut, dtype=float), x.shape)
    a = np.exp(-2 * np.pi * cut / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def bandnoise(d, f0, f1):
    n = rng.standard_normal(int(SR * d))
    sweep = np.geomspace(f0, f1, len(n))
    hi = lowpass(n, sweep * 1.6)
    lo = lowpass(n, sweep * 0.6)
    return hi - lo


def norm(x, peak=0.89):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def stereo(x, width=0.0):
    if width:
        d = int(SR * 0.004 * width)
        r = np.concatenate([np.zeros(d), x[:-d]]) if d else x
        return np.stack([x, r], 1)
    return np.stack([x, x], 1)


def fx_whoosh(d=0.7):
    x = bandnoise(d, 300, 4000) * np.sin(np.pi * np.linspace(0, 1, int(SR * d))) ** 1.5
    return stereo(norm(x, 0.8), 1.0)


def fx_riser(d=2.0):
    tt = t(d)
    f = np.geomspace(120, 1800, len(tt))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4
    noise = bandnoise(d, 500, 8000) * 0.6
    return stereo(norm((tone + noise) * np.linspace(0, 1, len(tt)) ** 2, 0.8), 1.0)


def fx_impact(d=1.2):
    tt = t(d)
    f = 55 + 120 * np.exp(-tt * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4)
    crack = rng.standard_normal(len(tt)) * np.exp(-tt * 40) * 0.5
    return stereo(norm(body + crack))


def fx_boom(d=2.0):
    tt = t(d)
    f = 40 + 60 * np.exp(-tt * 6)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.8)
    x += lowpass(rng.standard_normal(len(tt)), 300) * np.exp(-tt * 3) * 2
    return stereo(norm(np.tanh(x * 2)))


def fx_pop(d=0.15):
    tt = t(d)
    f = 900 * np.exp(-tt * 30) + 250
    return stereo(norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 35), 0.7))


def fx_click(d=0.05):
    tt = t(d)
    return stereo(norm(np.sin(2 * np.pi * 2500 * tt) * np.exp(-tt * 180) + rng.standard_normal(len(tt)) * np.exp(-tt * 400) * 0.3, 0.6))


def fx_ding(d=1.2):
    tt = t(d)
    x = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * k) for f, a, k in
            [(1568, 1, 3), (3136, 0.4, 5), (4704, 0.2, 7), (2093, 0.3, 4)])
    return stereo(norm(x * env(len(tt), 0.002, 0.3), 0.6))


def fx_notify(d=0.5):
    a, b = t(0.18), t(0.32)
    x = np.concatenate([np.sin(2 * np.pi * 988 * a) * np.exp(-a * 12), np.sin(2 * np.pi * 1319 * b) * np.exp(-b * 8)])
    return stereo(norm(x, 0.6))


def fx_shutter(d=0.25):
    c1 = rng.standard_normal(int(SR * 0.03)) * np.exp(-t(0.03) * 120)
    gap = np.zeros(int(SR * 0.07))
    c2 = rng.standard_normal(int(SR * 0.06)) * np.exp(-t(0.06) * 70)
    return stereo(norm(lowpass(np.concatenate([c1, gap, c2]), 5000), 0.7))


def fx_glitch(d=0.5):
    n = int(SR * d)
    x = np.zeros(n)
    pos = 0
    while pos < n:
        seg = int(SR * rng.uniform(0.01, 0.05))
        kind = rng.integers(3)
        tt = t(seg / SR)
        x[pos:pos + seg] = (np.sign(np.sin(2 * np.pi * rng.uniform(80, 1200) * tt)) if kind == 0 else
                            rng.standard_normal(seg) if kind == 1 else np.zeros(seg))[: n - pos]
        pos += seg
    return stereo(norm(x, 0.5), 0.5)


def fx_typing(d=1.5):
    n = int(SR * d)
    x = np.zeros(n)
    pos = 0
    while pos < n - 2000:
        c = fx_click()[:, 0] * rng.uniform(0.5, 1.0)
        x[pos:pos + len(c)] += c[: n - pos]
        pos += int(SR * rng.uniform(0.07, 0.16))
    return stereo(norm(x, 0.6))


def fx_swipe(d=0.35):
    return stereo(norm(bandnoise(d, 2000, 600) * np.sin(np.pi * np.linspace(0, 1, int(SR * d))), 0.6), 1.0)


def fx_bass_drop(d=1.6):
    tt = t(d)
    f = 30 + 170 * np.exp(-tt * 3)
    return stereo(norm(np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(len(tt), 0.005, 0.6)))


def fx_sparkle(d=1.0):
    n = int(SR * d)
    x = np.zeros(n)
    for _ in range(14):
        s = int(rng.uniform(0, n - 6000))
        tt = t(0.12)
        x[s:s + len(tt)] += np.sin(2 * np.pi * rng.uniform(2500, 6000) * tt) * np.exp(-tt * 40) * rng.uniform(0.3, 1)
    return stereo(norm(x, 0.55), 1.0)


EFFECTS = {k[3:]: v for k, v in globals().items() if k.startswith("fx_")}

CHORDS = {
    "calm": [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]],
    "uplifting": [[48, 52, 55, 60], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]],
    "dark": [[45, 48, 52, 55], [41, 45, 48, 52], [43, 46, 50, 53], [40, 44, 47, 50]],
    "lofi": [[50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59], [57, 60, 64, 67]],
}


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def bed(dur=60.0, mood="calm", bpm=90):
    n = int(SR * dur)
    out = np.zeros((n, 2))
    bar = 4 * 60 / bpm
    prog = CHORDS.get(mood, CHORDS["calm"])
    k = 0
    pos = 0.0
    while pos < dur:
        notes = prog[k % len(prog)]
        L = min(bar, dur - pos)
        tt = t(L)
        pad = sum(np.sin(2 * np.pi * midi(m) * tt + 0.3 * np.sin(2 * np.pi * 0.2 * tt)) * (0.9 ** i)
                  for i, m in enumerate(notes))
        pad *= env(len(tt), min(0.4, L / 3), min(0.5, L / 3), 1.5) * 0.18
        bass = np.sin(2 * np.pi * midi(notes[0] - 12) * tt) * env(len(tt), 0.02, 0.3) * 0.22
        s = int(pos * SR)
        seg = pad + bass
        out[s:s + len(seg), 0] += seg[: n - s]
        out[s:s + len(seg), 1] += np.roll(seg, 120)[: n - s]
        if mood in ("lofi", "uplifting"):
            beat = 60 / bpm
            for b in range(4):
                bt = pos + b * beat
                if bt >= dur:
                    break
                kick = fx_impact(0.25)[:, 0] * 0.35 if b % 2 == 0 else fx_click(0.08)[:, 0] * 0.25
                hs = int(bt * SR)
                out[hs:hs + len(kick), :] += kick[: n - hs, None]
        pos += bar
        k += 1
    if mood == "lofi":
        out += lowpass(rng.standard_normal(n), 3000)[:, None] * 0.004
    fade = int(SR * min(2, dur / 4))
    out[:fade] *= np.linspace(0, 1, fade)[:, None]
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return norm(out, 0.7)


def save(x, path):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=sorted(EFFECTS) + ["all", "bed"])
    ap.add_argument("--out")
    ap.add_argument("--out-dir")
    ap.add_argument("--dur", type=float)
    ap.add_argument("--mood", default="calm", choices=list(CHORDS))
    ap.add_argument("--bpm", type=int, default=90)
    a = ap.parse_args()
    made = {}
    if a.kind == "all":
        d = Path(a.out_dir or "sfx")
        d.mkdir(parents=True, exist_ok=True)
        for k, f in EFFECTS.items():
            p = d / f"{k}.wav"
            save(f(), p)
            made[k] = str(p)
    elif a.kind == "bed":
        p = Path(a.out or f"bed_{a.mood}.wav")
        save(bed(a.dur or 60, a.mood, a.bpm), p)
        made["bed"] = str(p)
    else:
        p = Path(a.out or f"{a.kind}.wav")
        f = EFFECTS[a.kind]
        save(f(a.dur) if a.dur else f(), p)
        made[a.kind] = str(p)
    print(json.dumps(made, indent=1))


if __name__ == "__main__":
    main()
