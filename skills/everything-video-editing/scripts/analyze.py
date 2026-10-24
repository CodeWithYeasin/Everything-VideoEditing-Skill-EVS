"""Analyse the user's footage and propose the questions to ask them (interview mode).

  python analyze.py video.mp4 [more.mp4 | photos_folder ...] [--fast] [--out analysis.json]

Looks at: length, orientation, speech (how much, which language), pauses, fillers,
loudness, background noise, music under the voice (CLAP), faces and where they sit,
shot changes, camera shake, motion, exposure/colour, screen-recording look.
Then guesses the content type and writes question rounds for AskUserQuestion:
each question has <= 4 options, the first is the recommended one for THIS footage, and
every option carries a `patch` (what it changes in plan.json; keys starting with "_" are
notes for you, e.g. "_target_s"). Translate questions/labels to the user's language.
--fast skips the ML parts (Whisper language id, CLAP music check).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

import vtools as V
import probe as P

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".mts", ".3gp", ".wmv", ".flv"}


# ----------------------------------------------------------------- measurements
def sample_frames(src: str, dur: float, n: int, width: int = 320):
    import numpy as np
    step = max(dur / (n + 1), 0.04)
    raw = subprocess.run([V.need("ffmpeg"), "-v", "error", "-i", src, "-vf",
                          f"fps=1/{step:.4f},scale={width}:-2,format=gray", "-frames:v", str(n),
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    info = V.media_info(src)
    h = int(round(info["height"] * width / max(1, info["width"]) / 2) * 2)
    if not raw or h <= 0:
        return []
    frame = width * h
    k = len(raw) // frame
    return [np.frombuffer(raw[i * frame:(i + 1) * frame], dtype=np.uint8).reshape(h, width) for i in range(k)]


def faces_and_screen(src: str, dur: float) -> dict:
    try:
        import cv2
    except Exception:
        return {}
    _, casc = V.face_cascade()
    frames = sample_frames(src, dur, 12, 480)
    if not frames:
        return {}
    hits, xs, sizes, edges = 0, [], [], []
    for g in frames:
        f = casc.detectMultiScale(g, 1.1, 5, minSize=(30, 30)) if casc is not None else []
        if len(f):
            hits += 1
            x, y, w, h = max(f, key=lambda r: r[2] * r[3])
            xs.append((x + w / 2) / g.shape[1])
            sizes.append(w * h / (g.shape[0] * g.shape[1]))
        e = cv2.Canny(g, 80, 160)
        edges.append(float((e > 0).mean()))
    return {"face_frames": round(hits / len(frames), 2) if casc is not None else None,
            "face_x": round(statistics.median(xs), 2) if xs else None,
            "face_size": round(statistics.median(sizes), 3) if sizes else None,
            "edge_density": round(statistics.median(edges), 3)}


def motion_and_shake(src: str, dur: float) -> dict:
    """Global motion between consecutive frames (phase correlation) over a ~12 s window."""
    try:
        import cv2
        import numpy as np
    except Exception:
        return {}
    start = max(0.0, dur / 2 - 6)
    raw = subprocess.run([V.need("ffmpeg"), "-v", "error", "-ss", f"{start:.2f}", "-t", "12", "-i", src, "-vf",
                          "fps=10,scale=256:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    info = V.media_info(src)
    h = int(round(info["height"] * 256 / max(1, info["width"]) / 2) * 2)
    if not raw or h <= 0:
        return {}
    n = len(raw) // (256 * h)
    fr = [np.frombuffer(raw[i * 256 * h:(i + 1) * 256 * h], dtype=np.uint8).reshape(h, 256).astype(np.float32)
          for i in range(n)]
    if len(fr) < 6:
        return {}
    win = cv2.createHanningWindow((256, h), cv2.CV_32F)
    dx, dy, diff = [], [], []
    for a, b in zip(fr, fr[1:]):
        (sx, sy), _ = cv2.phaseCorrelate(a, b, win)
        dx.append(sx)
        dy.append(sy)
        diff.append(float(np.abs(a - b).mean()))
    dx, dy = np.array(dx), np.array(dy)
    k = np.ones(5) / 5
    jit = np.hypot(dx - np.convolve(dx, k, "same"), dy - np.convolve(dy, k, "same"))
    shake = float(np.median(jit[2:-2])) / 256 if len(jit) > 4 else 0.0
    return {"shake": round(shake, 4), "shaky": shake > 0.0035, "motion": round(float(np.median(diff)), 2)}


def noise_floor(src: str) -> float | None:
    r = V.run([V.need("ffmpeg"), "-hide_banner", "-nostats", "-i", src, "-vn", "-af",
               "astats=metadata=1:reset=0:measure_overall=Noise_floor+RMS_level", "-f", "null", "-"],
              capture=True, check=False)
    m = re.findall(r"Noise floor dB:\s*(-?[\d.]+|-inf)", r.stderr or "")
    vals = [float(x) for x in m if x != "-inf"]
    return round(statistics.median(vals), 1) if vals else None


def whisper_language(src: str) -> dict:
    try:
        from faster_whisper import WhisperModel
        from faster_whisper.audio import decode_audio
    except Exception:
        return {}
    V.setup_model_env()
    try:
        audio = decode_audio(src, sampling_rate=16000)
        clip = audio[: 16000 * 30]
        m = WhisperModel("small", device="cpu", compute_type="int8")
        segs, info = m.transcribe(clip, beam_size=1, vad_filter=True, without_timestamps=True)
        text = " ".join(s.text for s in segs).strip()
        return {"language": info.language, "lang_prob": round(info.language_probability, 2),
                "sample_text": text[:160]}
    except Exception as e:
        return {"lang_error": repr(e)[:120]}


def clap_audio_tags(src: str, dur: float) -> dict:
    try:
        import numpy as np
        sys.path.insert(0, str(Path(__file__).parent))
        from clap_rank import Clap
    except Exception:
        return {}
    labels = ["people talking", "speech with background music", "music", "singing", "silence",
              "crowd cheering", "wind noise", "traffic noise", "nature sounds", "video game sounds"]
    try:
        clap = Clap()
        arrays = []
        for k in (0.2, 0.5, 0.8):
            st = max(0.0, dur * k - 5)
            raw = subprocess.run([V.need("ffmpeg"), "-v", "error", "-ss", f"{st:.2f}", "-t", "10", "-i", src, "-vn",
                                  "-ac", "1", "-ar", "48000", "-f", "f32le", "-"], capture_output=True).stdout
            arrays.append(np.frombuffer(raw, dtype=np.float32) if raw else np.zeros(48000, dtype=np.float32))
        av = clap.audio(arrays)
        tv = clap.text(labels)
        score = {lab: round(sum(sum(a * b for a, b in zip(x, t)) for x in av) / len(av), 3) for lab, t in zip(labels, tv)}
        top = sorted(score.items(), key=lambda kv: -kv[1])[:3]
        return {"audio_tags": [k for k, _ in top],
                "music_under": "speech with background music" in [k for k, _ in top[:2]]
                or top[0][0] in ("music", "singing")}
    except Exception as e:
        return {"clap_error": repr(e)[:120]}


# ----------------------------------------------------------------- one file
def analyze_file(src: str, fast: bool) -> dict:
    info = V.media_info(src)
    r = {"file": src, "duration": round(info["duration"], 2), "width": info["width"], "height": info["height"],
         "fps": info["fps"], "has_audio": info["has_audio"],
         "orientation": "vertical" if info["height"] > info["width"] * 1.1 else
         "square" if abs(info["height"] - info["width"]) < 0.1 * info["width"] else "landscape"}
    if info["is_image"]:
        r["image"] = True
        return r
    dur = info["duration"]
    if info["has_audio"]:
        r["loudness"] = P.loudness(src)
        sil = P.silences(src, -35, 0.5)
        sil_total = sum(min(e, dur) - s for s, e in sil)
        r["silence_s"] = round(sil_total, 1)
        r["pauses_over_0_5s"] = len(sil)
        r["sound_ratio"] = round(1 - sil_total / max(dur, 0.1), 2)
        r["noise_floor_db"] = noise_floor(src)
    r.update(motion_and_shake(src, dur))
    r.update(faces_and_screen(src, dur))
    sc = P.scenes(src)
    r["shot_changes"] = len(sc)
    r["avg_shot_s"] = round(dur / (len(sc) + 1), 1)
    r["color"] = P.color_stats(src, dur)
    if info["has_audio"] and not fast:
        r.update(whisper_language(src))
        r.update(clap_audio_tags(src, dur))
    return r


def guess_type(f: dict) -> str:
    talky = len(f.get("sample_text", "") or "") > 40  # Whisper heard real sentences
    speech = talky or bool(f.get("language")) or (f.get("sound_ratio", 0) > 0.55 and f.get("pauses_over_0_5s", 0) >= 2)
    tags = f.get("audio_tags", [])
    face = (f.get("face_frames") or 0) >= 0.5
    if f.get("image"):
        return "photos"
    if (f.get("edge_density") or 0) > 0.09 and (f.get("motion") or 99) < 4 and not face:
        return "screen_recording"
    if tags and tags[0] in ("music", "singing") and not face and not talky:
        return "music_or_performance"
    if tags and tags[0] == "video game sounds" and not talky:
        return "gaming"
    if talky and not face:
        return "narrated_broll"
    if face and speech and f.get("avg_shot_s", 0) > 8:
        return "talking_head"
    if speech and face:
        return "vlog_or_interview"
    if "crowd cheering" in tags[:2]:
        return "event_or_sports"
    if f.get("shot_changes", 0) >= 3 or (f.get("motion") or 0) > 8:
        return "broll_montage"
    return "talking_head" if speech else "broll_montage"


# ----------------------------------------------------------------- questions
def Q(qid, header, question, options, multi=False):
    return {"id": qid, "header": header, "question": question, "multiSelect": multi, "options": options[:4]}


def O(label, description, patch):
    return {"label": label, "description": description, "patch": patch}


def build_questions(s: dict) -> list:
    """Round 1 = the big decisions, round 2 = details that depend on what we found."""
    total, orient, ctype = s["total_s"], s["orientation"], s["content_type"]
    lang = s.get("language")
    speech = s["speech"]
    r1, r2 = [], []

    # platform
    vertical = [O("Reels (IG + FB)", "9:16, captions above the app buttons", {"platform": "instagram_reels"}),
                O("YouTube Shorts", "9:16, up to 3 min", {"platform": "youtube_shorts"}),
                O("TikTok", "9:16", {"platform": "tiktok"}),
                O("All platforms", "one edit, exported for Reels, Shorts, TikTok and a 4:5 feed version",
                  {"variants": ["instagram_reels", "youtube_shorts", "tiktok", "instagram_feed"]})]
    landscape = [O("YouTube video", "16:9, chapters + subtitles file", {"platform": "youtube"}),
                 O("Facebook video", "16:9 or 4:5 feed", {"platform": "facebook_landscape"}),
                 O("Reels / Shorts", "turn it vertical (face-tracked crop or blurred fill)", {"platform": "instagram_reels"}),
                 O("All platforms", "YouTube 16:9 + Reels/Shorts 9:16 + 4:5 feed",
                   {"variants": ["youtube", "instagram_reels", "instagram_feed"]})]
    r1.append(Q("platform", "Platform", "Where will this video be posted?", vertical if orient == "vertical" else landscape))

    # length
    if total > 180:
        opts = [O("Short highlight (30-60 s)", "best moments only, for Reels/Shorts", {"_target_s": 45}),
                O("Medium (2-3 min)", "the main story, no slow parts", {"_target_s": 150}),
                O("Keep it long, tighten it", "remove pauses/mistakes, keep everything else", {"_target_s": None, "_tighten": True}),
                O("Several shorts", "cut 3-5 separate clips from it", {"_multi_clips": 4})]
    elif total > 60:
        opts = [O("Under 60 s", "tight cut for Reels/Shorts", {"_target_s": 55}),
                O("About 30 s", "fast and punchy", {"_target_s": 30}),
                O("Keep full length", "only tidy it up", {"_target_s": None, "_tighten": True})]
    else:
        opts = [O("Keep length", f"about {int(total)} s, just polish", {"_target_s": None}),
                O("Make it shorter", "about 15 s", {"_target_s": 15})]
    r1.append(Q("length", "Length", f"The footage is {int(total // 60)}:{int(total % 60):02d} long. How long should the final video be?", opts))

    # style
    styles = {
        "talking_head": [O("Energetic creator", "word-pop captions, punch-in zooms, SFX", {"captions": {"style": "pop"}, "_zooms": True, "_sfx": True, "grade": "vibrant"}),
                         O("Clean & professional", "simple captions, light colour fix", {"captions": {"style": "clean"}, "grade": "natural"}),
                         O("Cinematic", "film look, slower pace, music bed", {"grade": "cinematic", "captions": {"style": "minimal"}}),
                         O("Minimal", "just cut and fix audio", {"grade": "natural"})],
        "vlog_or_interview": [O("Fun vlog", "fast cuts, pop captions, music", {"captions": {"style": "pop"}, "grade": "vibrant", "_sfx": True}),
                              O("Cinematic vlog", "film grade, music-led", {"grade": "cinematic"}),
                              O("Documentary / interview", "clean captions, lower third names", {"captions": {"style": "clean"}, "grade": "natural", "_lower_third": True}),
                              O("Aesthetic & calm", "soft colours, slow transitions", {"grade": "pastel"})],
        "broll_montage": [O("Cinematic montage", "beat-synced cuts, film grade", {"grade": "cinematic", "_beat_sync": True}),
                          O("Fast & energetic", "quick cuts, whoosh transitions", {"grade": "vibrant", "_beat_sync": True, "_sfx": True}),
                          O("Warm memories", "golden look, gentle dissolves", {"grade": "golden", "_transitions": "dissolve"}),
                          O("Moody", "dark, desaturated look", {"grade": "moody"})],
        "screen_recording": [O("Tutorial, tight", "remove waits, zoom on the action, captions", {"captions": {"style": "box"}, "_speed_up_idle": True}),
                             O("Keep everything", "only fix audio and add captions", {"captions": {"style": "box"}}),
                             O("Short demo clip", "best 30-60 s for social", {"_target_s": 45})],
        "music_or_performance": [O("Keep the music, cinematic", "film grade, no voice changes", {"grade": "cinematic", "audio": {"voice": {"mode": "original"}}}),
                                 O("Lyric/caption video", "big kinetic words on beat", {"_kinetic_text": True}),
                                 O("Highlight reel", "best moments on the beat", {"_beat_sync": True})],
        "narrated_broll": [O("Captions-first social cut", "pop captions, quick cuts, music bed", {"captions": {"style": "pop"}, "grade": "vibrant", "_sfx": True}),
                           O("Clean explainer", "clean captions, calm pace", {"captions": {"style": "clean"}, "grade": "natural"}),
                           O("Cinematic story", "film grade, music-led", {"grade": "cinematic", "captions": {"style": "minimal"}}),
                           O("Minimal", "just cut and fix audio", {"grade": "natural"})],
        "gaming": [O("Highlight reel", "loudest/best moments, zoom + impact SFX", {"grade": "neon", "_highlights": True, "_sfx": True}),
                   O("Full video, tightened", "remove dead time", {"_tighten": True}),
                   O("Facecam + captions", "pop captions on your commentary", {"captions": {"style": "bold"}})],
        "event_or_sports": [O("Highlight reel", "peak moments, slow-mo replays", {"_highlights": True, "_slowmo": True}),
                            O("Cinematic recap", "music-led, film grade", {"grade": "cinematic", "_beat_sync": True}),
                            O("Full event, cleaned", "trim, stabilise, fix audio", {"_tighten": True})],
        "photos": [O("Slideshow with music", "Ken Burns moves, dissolves", {"_slideshow": True}),
                   O("Fast beat-synced", "photos change on the beat", {"_beat_sync": True}),
                   O("Memorial / tribute", "slow, warm, gentle music", {"grade": "film", "_transitions": "dissolve"})],
    }
    r1.append(Q("style", "Style", "What feel do you want?", styles.get(ctype, styles["broll_montage"])))

    # captions
    if speech:
        ln = {"bn": "Bangla", "en": "English", "hi": "Hindi"}.get(lang or "", (lang or "spoken").upper())
        r1.append(Q("captions", "Captions", f"Add captions? (speech detected: {ln})", [
            O(f"Yes, {ln} captions", "word-by-word, burned in + .srt file", {"captions": {"auto": True, "language": lang} if lang else {"auto": True}}),
            O("English subtitles", "translated, burned in", {"_translate_to": "en"}),
            O("Only a .srt file", "upload as CC on YouTube/Facebook, nothing burned in", {"captions": {"auto": True, "burn": False}}),
            O("No captions", "", {"captions": None})]))
    else:
        r1.append(Q("music", "Music", "There is no speech. What audio should it have?", [
            O("Music bed", "from your music folder (matched to the mood) or a generated bed", {"_music": "auto"}),
            O("Keep original sound", "natural sound only", {"audio": {"voice": {"mode": "original"}}}),
            O("Music + original sound", "music with the real sound mixed lower", {"_music": "auto", "_keep_natural": True})]))

    # ---- round 2 (depends on findings)
    if speech and s.get("filler_or_pause_heavy"):
        r2.append(Q("cuts", "Cuts", f"I found {s['pauses']} pauses ({s['silence_s']} s of silence). Remove them?", [
            O("Tight jump cuts", "remove pauses and um/uh, zoom between cuts", {"_jumpcuts": "tight"}),
            O("Light trim", "only pauses longer than 1 s", {"_jumpcuts": "light"}),
            O("No cuts", "keep the natural pace", {"_jumpcuts": None})]))
    if speech and (s.get("noisy") or s.get("music_under")):
        why = "background music under the voice" if s.get("music_under") else "background noise"
        r2.append(Q("voice", "Voice", f"I can hear {why}. Clean it?", [
            O("Isolate the voice", "remove music/noise completely (Demucs)", {"audio": {"voice": {"mode": "isolate", "enhance": True}}}),
            O("Reduce noise", "lighter clean-up, keeps room tone", {"audio": {"voice": {"enhance": True}}}),
            O("Leave it", "", {})]))
    if speech:
        r2.append(Q("music", "Music", "Background music under the voice?", [
            O("Soft music bed", "ducked under speech", {"_music": "auto", "_music_mood": "calm"}),
            O("Upbeat", "more energy", {"_music": "auto", "_music_mood": "uplifting"}),
            O("From my music folder", "tell me the folder; I'll pick by mood with CLAP", {"_music": "folder"}),
            O("No music", "", {"_music": None})]))
    hints = (s.get("color") or {}).get("hints", [])
    if hints and hints != ["balanced exposure and colour"]:
        r2.append(Q("color", "Colour", "The footage looks " + "; ".join(h.split(":")[0] for h in hints) + ". Fix it?", [
            O("Auto-fix", "correct exposure and white balance", {"grade": {"preset": "auto"}}),
            O("Fix + warm look", "", {"grade": {"preset": "warm"}}),
            O("Fix + cinematic", "", {"grade": {"preset": "cinematic"}}),
            O("Leave colours", "", {})]))
    if s.get("shaky"):
        r2.append(Q("stabilize", "Stabilise", "Some shots are shaky. Stabilise?", [
            O("Yes, stabilise", "smooth (crops edges ~4%)", {"stabilize": 0.6}),
            O("Keep handheld feel", "", {"stabilize": False})]))
    r2.append(Q("extras", "Extras", "Anything else to add?", [
        O("Hook title at the start", "a 3-5 word teaser in the first 2 s", {"_hook": True}),
        O("Name lower third", "your name/brand when you first appear", {"_lower_third": True}),
        O("Follow/subscribe end", "CTA graphic in the last seconds", {"_cta": True}),
        O("Thumbnail / cover", "made from the best frame", {"_thumbnail": True})], multi=True))
    return [{"round": 1, "questions": r1}, {"round": 2, "questions": r2[:4]}] + \
        ([{"round": 3, "questions": r2[4:]}] if len(r2) > 4 else [])


FEEDBACK = Q("feedback", "Changes", "Here is the draft. What should I change?", [
    O("Looks good, export", "final quality + all platform versions", {"_final": True}),
    O("Pacing", "faster or slower cuts", {"_ask": "faster or slower?"}),
    O("Captions / text", "style, colour, size or position", {"_ask": "which caption change?"}),
    O("Music / sound", "louder, quieter, different track", {"_ask": "what about the sound?"})])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    files = []
    for x in a.inputs:
        p = Path(x).resolve()
        if p.is_dir():
            files += sorted(str(f) for f in p.iterdir() if f.suffix.lower() in VIDEO_EXT | V.IMAGE_EXT)
        else:
            files.append(str(p))
    if not files:
        sys.exit("[eve] no media found")
    per = []
    for f in files[:40]:
        print(f"[eve] analysing {Path(f).name}", file=sys.stderr, flush=True)
        per.append(analyze_file(f, a.fast or len(files) > 6))
    vids = [f for f in per if not f.get("image")]
    main_f = max(vids, key=lambda f: f["duration"]) if vids else per[0]
    total = sum(f["duration"] for f in vids)
    langs = [f.get("language") for f in vids if f.get("language")]
    s = {
        "files": len(per), "videos": len(vids), "photos": len(per) - len(vids),
        "total_s": round(total, 1), "orientation": main_f["orientation"],
        "content_type": "photos" if not vids else guess_type(main_f),
        "speech": bool(langs) or any(f.get("sound_ratio", 0) > 0.55 and f.get("pauses_over_0_5s", 0) >= 2 for f in vids),
        "language": max(set(langs), key=langs.count) if langs else None,
        "silence_s": round(sum(f.get("silence_s", 0) for f in vids), 1),
        "pauses": sum(f.get("pauses_over_0_5s", 0) for f in vids),
        "noisy": any((f.get("noise_floor_db") or -90) > -50 for f in vids),
        "music_under": any(f.get("music_under") for f in vids),
        "shaky": any(f.get("shaky") for f in vids),
        "faces": main_f.get("face_frames"),
        "face_x": main_f.get("face_x"),
        "color": main_f.get("color", {}),
    }
    s["filler_or_pause_heavy"] = s["pauses"] >= max(3, total / 20) or s["silence_s"] > total * 0.12
    found = [f"{s['videos']} video(s), {s['photos']} photo(s), {int(total // 60)}:{int(total % 60):02d} total, {s['orientation']}",
             f"looks like: {s['content_type'].replace('_', ' ')}"]
    if s["speech"]:
        found.append(f"speech{' in ' + s['language'] if s['language'] else ''}, {s['pauses']} pauses / {s['silence_s']} s silence")
    if s["noisy"]:
        found.append("background noise")
    if s["music_under"]:
        found.append("music under the voice")
    if s["shaky"]:
        found.append("shaky camera")
    hints = s["color"].get("hints") if s["color"] else None
    if hints and hints != ["balanced exposure and colour"]:
        found.append("colour: " + "; ".join(h.split(":")[0] for h in hints))
    s["found"] = found
    s["rounds"] = build_questions(s)
    s["feedback_question"] = FEEDBACK
    s["per_file"] = per
    if vids:
        try:
            out_dir = Path(a.out).resolve().parent if a.out else Path(main_f["file"]).parent / ".eve_work"
            sheet, _ = P.contact_sheet(main_f["file"], main_f["duration"], V.ensure_dir(out_dir / "analysis_sheet"), 12)
            s["contact_sheet"] = sheet
        except SystemExit:
            pass
    txt = json.dumps(s, indent=1, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
