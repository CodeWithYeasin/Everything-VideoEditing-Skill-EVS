---
name: everything-video-editing
description: A-to-Z video editing from a plain-language brief, for creators (Facebook, Instagram, YouTube, TikTok), ads/OVC and any everyday edit. Analyses the footage, asks the user option-based questions, then cuts, reframes, colour grades, captions (incl. Bangla), adds music, SFX, voice-over, motion graphics (Remotion) and 3D titles (Blender), cleans voice (Demucs), transcribes (Whisper), finds music by description (CLAP) and exports per platform. Use whenever a video, clip, reel, short, ad, slideshow or footage edit is requested. Not for generating new footage from text.
---

# Everything-videoEditing

The user gives footage (video, photos, audio) and says what they want - or nothing more than
"edit this". You analyse it, ask a few sharp questions with options, edit with the scripts
here, show a draft, adjust, and deliver finished files. Reply in the user's language (Bangla
users: Bangla script, technical words may stay English). Keep tool talk out of replies.

`SKILL_DIR` = the folder containing this file. Scripts are `SKILL_DIR/scripts/*.py`
(run with the Python from `doctor.py`); guides are `SKILL_DIR/references/*.md`.

## Toolbox
| script | does |
|---|---|
| `analyze.py` | **start here**: findings + question rounds with options (interview mode) |
| `probe.py` | facts, loudness, pauses, scene cuts, colour hints + contact sheet image |
| `transcribe.py` | Whisper speech-to-text, word times, .srt (Bangla: `--language bn --model medium`) |
| `cutlist.py` | jump cuts: drop silences, um/uh, retakes |
| `render.py` | **engine**: plan.json → video. Cuts, speed, reframe (face-aware), transitions, grade, stabilise, overlays, safe-zone captions, voice clean-up, music ducking, SFX, bleeps, loudness, brand kit, `--variants` per platform, .srt export |
| `platforms.py` | FB/IG/YT/TikTok/LinkedIn/X/WhatsApp/TV presets: size, safe zones, limits |
| `safezone.py` | draws platform UI zones over frames to check text placement |
| `remotion_gfx.py` | motion graphics (alpha .mov): TitleCard, LowerThird, CallToAction, EndCard, KineticText, StatCounter, ProgressBar, Countdown, LogoReveal, EndSlate, OfferBadge, BeforeAfter, FeatureCallout, SocialFollow |
| `title3d.py` | Blender 3D animated title (Latin text) |
| `tts.py` | voice-over with word timings (Bangla/English neural voices, offline fallbacks) |
| `ovc_build.py` | ads/OVC from script.json: VO, scenes, supers, badges, end slate, music, versions × aspects, storyboard.html |
| `separate.py` | Demucs: vocals / no_vocals (remove music, isolate voice) |
| `clap_rank.py` | CLAP: pick music/SFX from a folder by description |
| `analyze_audio.py` | beat times (montage), loudest moments (highlights) |
| `sfx_synth.py` | royalty-free SFX pack + music beds |
| `thumbnail.py` | best-frame thumbnail/cover with bold text, per platform size |
| `quick.py` | one-command edits: compress to MB, gif, convert, audio, trim, speed, reverse, boomerang, rotate, resize, merge, stack (split screen), loop, frames, scenes, restore old video, subtitles, loudness, denoise, slideshow |
| `doctor.py` | what is installed; how to fix what is missing |

Guides: `plan_format.md` (every plan key), `recipes.md` (brief → decisions, 23 kinds of
video), `platforms.md` (creator playbook), `ovc.md` (ads), `interview.md` (question flow),
`tools.md` (per-tool notes, troubleshooting). Read plan_format + the relevant guide before
the first plan of a session.

## 1. Setup check (silent, once per session)
Run `python SKILL_DIR/scripts/doctor.py`. It reads `~/.everything-video/config.json`
(written by the installer: python env, ffmpeg, blender, model folders) and reports
capabilities. Use the `python` path it prints for every script (it has Whisper, Demucs,
CLAP). Missing pieces: run `SKILL_DIR/setup/install_windows.ps1` (Windows, PowerShell) or
`bash SKILL_DIR/setup/install_unix.sh` (Linux/macOS) - ask the user first, it downloads
~3-5 GB. Only FFmpeg + Python are strictly required; the rest switch features on.
- Windows PowerShell mangles inline JSON: write props/plans to .json files and pass paths.
- In JSON plans use forward slashes in paths (`D:/Videos/x.mp4`).
- Never overwrite originals; write to an `edited/` folder next to the source.
- Remote agents (e.g. Claude app with Desktop Commander on the user's PC): run the same
  commands through that shell; view images by reading the .jpg files.

## 2. Workflow (interview mode by default)
1. **Analyse**: `analyze.py <files> --out analysis.json`. Open `contact_sheet` and look.
   Tell the user what you found in 1-2 lines.
2. **Ask** round 1, then round 2 from `analysis.json` with AskUserQuestion (≤4 questions,
   2-4 options, recommended first) - details in `references/interview.md`. Skip what the
   user already said. "Just do it" → use recommended options and say so.
3. **Prepare**: transcribe → cutlist; separate (voice isolate / music removal); music via
   `clap_rank.py` from the user's folder or `sfx_synth.py bed`; SFX pack; graphics at the
   platform size (`remotion_gfx.py`, `--brand`); hook/lower third/CTA as needed.
4. **Plan** `plan.json` (`platform`, `clips`, `grade`, `overlays`, `captions`, `audio`, `brand`).
   Overlay/SFX times are output-timeline times: `render.py plan.json --pass1` gives
   `timeline.json` segment starts.
5. **Draft** `render.py plan.json --draft` → `probe.py` the draft → look at its contact sheet
   → `safezone.py` for vertical platforms → show the user key frames or the file → ask the
   feedback question. Loop until happy.
6. **Final**: `render.py plan.json [--variants ...]` → probe (≈ -14 LUFS, duration, no black
   frames) → thumbnail → write title/description/hashtags (+ YouTube chapters from
   `.eve_work/final_words.json`) in the user's language.
7. **Deliver**: files + .srt + thumbnail, 3-5 line summary, 2-3 concrete tweak offers.

Ads/OVC: `references/ovc.md` → brand.json + script.json → `ovc_build.py --storyboard-only`
(client approval) → `--draft` → final versions. Quick jobs ("compress", "make a gif",
"merge these"): `quick.py`, no interview needed.

## 3. Taste rules
- Hook in the first 1-2 s. Captions on for social. One caption style per video/channel.
- Cut on speech boundaries (0.06-0.1 s padding); vary jump cuts with zoom 1.08-1.15.
- Text inside platform safe zones (render does it for named positions; check with safezone.py).
- Grade gently, faces first; fix exposure/white balance before stylising.
- Music ducked under voice (-18 to -22 dB), -8 to -12 dB for montages; SFX sparingly.
- Graphics never cover faces or captions; CTA where nobody talks.
- Only music/clips the user has rights to, generated beds, or platform libraries.

## 4. Limits to state honestly
- Blender text can't shape Bangla/Hindi/Arabic → use Remotion or ASS text styles.
- CPU-only machines: Whisper medium ≈ real time, Demucs ≈ 1-3× real time, Blender slow;
  warn before long jobs and offer smaller models or a shorter section.
- Face tracking is a static crop per clip (not frame-by-frame).
- No generative video; editing, graphics, TTS and synthesis only.
