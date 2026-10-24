# Recipes: from a one-line brief to a plan

For creators (FB/IG/YT) read references/platforms.md too; for ads, references/ovc.md;
for the question flow, references/interview.md.

Pick the closest recipe, then adapt. Numbers are good defaults, not rules.

## Translate the brief
| The user says | Do this |
|---|---|
| "TikTok / Reels / Shorts", "vertical" | canvas `reels`; fit auto (face crop); captions `pop` or `bold`; hook text first 2 s; 15-60 s |
| "YouTube", "landscape" | canvas `youtube`; captions `clean` (or none if they have SRT); lower third on first appearance |
| "cinematic", "movie look", "film" | grade `cinematic` or `film`, `letterbox: 2.39` (landscape only), slower cuts, music gain -16, fade in/out 1 s |
| "warm", "golden hour" / "cool", "moody" / "vintage", "retro" / "black and white" | grade `warm`/`golden` / `cool`/`moody` / `vintage` / `bw` |
| "make the colours pop", "vibrant" | `vibrant`; if probe says desaturated add saturation 1.2 |
| "fix the colour", "too dark", "washed out" | follow probe colour hints: `auto` + brightness/contrast tweaks |
| "remove ums / dead air / pauses", "jump cuts" | transcribe --keep-fillers → cutlist --words → zoom 1.12 on every 2nd clip |
| "remove background noise", "make my voice clear" | `voice.enhance: true` (RNNoise); heavy noise or music behind voice → `mode: isolate` |
| "remove the music from my video", "vocals only", "karaoke" | separate.py; use vocals.wav or no_vocals.wav |
| "add music", "add a calm/upbeat song" | clap_rank.py over the user's music folder; none → sfx_synth.py bed --mood; duck under speech |
| "add sound effects" | sfx pack: whoosh on transitions, pop on text pops, impact on hook, ding on CTA |
| "add subtitles", "captions" | transcribe → captions; Bangla: `--language bn --model medium` |
| "English subtitles for my Bangla video" | transcribe bn → you translate each segment → write SRT with the same times → `captions.srt` |
| "add an intro / title" | Remotion TitleCard or KineticText (any script) / Blender title3d (Latin, 3D look) |
| "add my name", "lower third" | Remotion LowerThird (best) or text overlay `lower_third` |
| "subscribe button", "follow" | Remotion CallToAction near the end, where nobody is speaking |
| "end screen" | Remotion EndCard (8-20 s, YouTube) |
| "add my logo / watermark" | image overlay `top-right`, scale 0.10-0.14, opacity 0.85 |
| "slow motion" | speed 0.5 (+ `smooth: true` if source is ≤30 fps and it must look fluid) |
| "speed up the boring part", "timelapse" | split the clip; speed 2-8 on the middle part |
| "stabilise", "shaky" | `stabilize: 0.5` |
| "beat sync", "montage", "edit to the music" | analyze_audio beats → clip lengths = beat intervals (every 2 or 4 beats) |
| "highlights", "best moments", "make a short from my long video" | transcript + energy peaks → pick 3-8 strongest moments |
| "blur that face / number plate / screen" | `blur` or `pixelate` overlay with a rect (look at frames to place it) |
| "bleep the swear word" | find the word in words.json → `audio.bleeps` |
| "green screen" | video overlay with `chromakey` |
| "picture in picture", "reaction" | second video as overlay, scale 0.3, bottom-right |
| "thumbnail" | thumbnail.py --t auto --text (3-5 words) --platform ... |
| "post it everywhere", "FB, IG and YouTube" | one plan + `--variants youtube,instagram_reels,instagram_feed`; graphics per size; safezone.py each |
| "make it smaller", "WhatsApp can't send it" | `quick.py compress --mb 16` (WhatsApp), `--mb 25` (email) |
| "make a GIF" / "convert to mp3" / "rotate" / "reverse" / "boomerang" / "loop" | `quick.py gif|audio|rotate|reverse|boomerang|loop` |
| "merge these videos" / "split screen" / "side by side" | `quick.py merge` / `quick.py stack --layout h|v|grid` |
| "old video", "VHS", "family tape", "blurry old clip" | `quick.py restore` (deinterlace, denoise, stabilise, colour, upscale) |
| "split it into shots" / "get stills" | `quick.py scenes` / `quick.py frames --every 2` |
| "add this .srt" | `quick.py subs --srt x.srt` (selectable) or `--burn` |
| "ad", "OVC", "TVC", "promo", "commercial", "offer video" | references/ovc.md → brand.json + script.json → ovc_build.py |
| "voice-over", "narration", "read this script" | tts.py (Bangla/English neural voices) or the user's recording as `audio.voice.mode` |
| "price tag", "discount badge", "logo animation", "end slate/packshot" | remotion_gfx.py OfferBadge / LogoReveal / EndSlate (+ `--brand`) |

## 1. Talking head → Reels/Shorts/TikTok (most common)
1. `transcribe.py raw.mp4 --out words.json --keep-fillers` (Bangla: `--language bn --model medium`)
2. `cutlist.py raw.mp4 --words words.json --out clips.json --min-silence 0.35`
3. Read words.json; if longer than the target, choose the strongest 30-60 s (keep the hook
   sentence first) and drop clips outside it.
4. Plan: canvas `reels`, clips from cutlist, `zoom: 1.12` on every 2nd clip (alternate
   `zoom_center` slightly), grade `natural` or per probe hints,
   overlays: hook text (style `hook`, 0-2.5 s, 3-6 words that tease the payoff),
   captions `pop` (words.json, remapped automatically), audio: voice enhance, music bed at
   -20 dB ducked, whoosh on any transition, pop when the hook appears, CTA graphic in the last
   2-3 s if requested. fade out 0.4.
5. `--draft`, look at 6 frames, final.

## 2. YouTube talking head / tutorial (landscape)
Jump cuts with min-silence 0.5 (less aggressive), canvas `youtube`, zoom 1.08 on some cuts,
LowerThird at the first appearance (2-5 s), captions `clean` or `box` (or none), music
-22 dB ducked, chapter titles as `title` text overlays or KineticText between sections,
EndCard for the last 10-15 s, thumbnail.

## 3. Screen recording / coding tutorial
No face crop (fit `pad` for vertical). Remove silences with cutlist (no words needed:
`--min-silence 0.8`), speed 1.5-2 on long typing sections, zoom + zoom_center on the area
being discussed (look at frames), captions `box`, voice enhance, no grain/vignette.

## 4. Vlog / travel montage
Many clips: probe each (contact sheets), pick the best 2-4 s from each, order for story
(arrival → activity → peak moment → calm end). Beat sync: `analyze_audio.py beats song.mp3
--every 2`; clip durations = intervals between cut times. Transitions mostly cuts; a few
`whip`/`smoothleft`; first clip fades from black. Grade `golden` (day) or `teal_orange`.
Music full level (gain -8 to -12) with `voice.mode: mute` unless someone speaks; keep
natural sound on 1-2 key moments with `volume`.

## 5. Photo slideshow / memorial / birthday
Image clips 3-4 s each, `kenburns` alternating in/out/left/right, `fade`/`dissolve`
transitions 0.8 s, grade `warm` or `film`, TitleCard at start (names, date), calm music,
fade in/out 1.5 s, no captions.

## 6. Podcast / interview clip
Pick the 30-90 s with one complete idea (from transcript). Vertical: fit auto crops each
speaker by face; for two people split the clip at speaker changes so each part centres on
the speaker. Captions `pop` or `karaoke`, LowerThird with guest name, voice enhance,
loudness -14, waveform not needed.

## 7. Product promo / ad (15-30 s)
Structure: hook (problem) → product reveal (StatCounter or TitleCard) → 3 benefits (text
`hook` style, one per shot) → CTA. Fast cuts (0.8-1.5 s), `vibrant` grade, upbeat bed
(`--mood uplifting --bpm 120`) or library track, impact on reveal, whoosh between shots.

## 8. Gaming / sports highlights
`analyze_audio.py energy match.mp4 --top 10` + transcript laughs/shouts → 3-6 s windows
around peaks (start 2 s before). Speed 0.5 replay of the best one, `zoom` punch, impact
SFX, captions `bold`, `neon` or `vibrant` grade.

## 9. Wedding / cinematic event
Slow (3-6 s shots), `dissolve` transitions, `film` grade + letterbox 2.39, music full with
vows audio segments (voice isolate if noisy), TitleCard with names in serif-free bold,
fade in/out 2 s.

## 10. Music removal / re-scoring a video
`separate.py video --out-dir stems` → plan with `voice.mode: stems/vocals.wav` (replacement
voice) + new music, or keep `no_vocals.wav` as the music for a karaoke/instrumental cut.

## 11. Wedding / holud / reception highlight (Bangladesh style)
Order: getting ready → holud colours → baraat/arrival → stage → emotional moments (bidaay) →
couple portraits → dance. 3-5 min film + 60 s Reel. `film`/`golden` grade, dissolves on slow
parts, cuts on the beat for dance, vows/speech audio isolated (`voice.mode: isolate`), names +
date TitleCard, letterbox 2.39 on the film (not the Reel).

## 12. Birthday / anniversary / kids' school event
Warm/vibrant grade, KineticText intro ("Happy Birthday Ayaan"), photo + clip mix, upbeat bed,
sparkle SFX on title, short Reel version, thumbnail with the child's best smile (t auto).

## 13. Memorial / tribute
Photos and old clips (`quick.py restore` old footage first), slow Ken Burns, dissolves 1 s,
`film` or `bw`, gentle music, names and years TitleCard, no SFX, fade from/to black 2 s.

## 14. Corporate / training / company profile
Clean grade, LowerThird for each speaker, StatCounter for numbers, screen recordings with
zoom, captions `box`, logo watermark via brand.json, -16 LUFS for presentations, chapters.

## 15. Education / lecture / course / waz-mahfil
Remove long silences only (`cutlist --min-silence 1.0`), voice enhance, captions in the
spoken language (`--model medium` for Bangla), chapter titles as `title` text overlays,
split into short clips (`_multi_clips`) for Reels with the best 30-60 s ideas.

## 16. Real estate / hotel / restaurant tour
Stabilise, bright/warm grade, smooth slow pans (speed 0.8), FeatureCallout for features
("3 bed", "Lake view"), price/address lower third, EndSlate with phone, 60 s + 15 s Reel.

## 17. Food / recipe
Overhead shots fast (speed 1.5-2 on stirring), close-ups slow, ingredient text pops (`label`
style), sizzle sound kept (`volume`), vibrant grade, captions for steps, final hero shot.

## 18. Fitness / sports training
Beat-synced cuts, rep counter (StatCounter or text), speed ramps (split clip: 1x → 0.5x on
the key rep), `bold` captions, impact SFX, high contrast grade.

## 19. Unboxing / product review
Hook = the product reveal or verdict first; jump cuts; FeatureCallout on details; pros/cons
as text; rating StatCounter; EndCard/CTA; thumbnail with the product + face.

## 20. News / explainer / documentary
Clean grade, lower thirds for names/places, captions `clean`, B-roll over narration, map or
photo Ken Burns, blur faces/plates when asked (`blur` overlay), no flashy SFX.

## 21. Reaction / commentary / duet
`quick.py stack` or PiP overlay (scale 0.3, bottom-right), your voice over their clip at
lower volume (only content the user has the right to use), pop captions.

## 22. Music video / lyric video
Cut on beats/bars, performance shots + B-roll, KineticText for lyric lines the user owns,
neon/teal_orange grade, no voice processing (`voice.mode: original`).

## 23. Long video → many shorts
Transcript → find 3-8 self-contained 20-60 s ideas (strong first sentence) → one plan per clip
(vertical, pop captions, hook text = the idea in 5 words) → batch render → thumbnails.

## Quality bar (check before delivering)
- First 2 seconds: something moves or a hook text is on screen.
- Captions: ≤ 2 lines, never under a lower third/CTA, inside the safe area (vertical: keep
  important text between 12% and 80% of the height; TikTok/Reels UI covers the bottom 20%
  and right edge).
- Loudness -14 LUFS ±1, true peak < -1 dBFS, music never louder than speech.
- No black frames or frozen frames at joins (look at the contact sheet of the output).
- Colour: skin looks natural; do not push saturation above 1.3 on faces.
