# plan.json reference

`scripts/render.py plan.json` turns this file into the finished video. Relative paths are
relative to plan.json. On Windows write paths with forward slashes (`D:/Videos/a.mp4`).
Every key except `clips` is optional.

```json
{
  "output": "out/final.mp4",            // .mp4 (H.264/AAC) or .webm (VP9/Opus)
  "quality": "good",                    // draft-like "small" | "good" (crf 20) | "best" (crf 17, slow)
  "platform": "instagram_reels",       // sets canvas, safe zones, caption height, loudness (references/platforms.md)
  "variants": ["youtube", "instagram_reels"],  // optional: one output per platform (<output>_<platform>.mp4)
  "brand": "brand.json",               // optional brand kit: accent colours, fonts, logo watermark
  "canvas": {"preset": "reels", "fps": 30},   // or "reels" | {"w":1920,"h":1080}  (overrides platform size)
  "fit": "auto",                        // default reframing for all clips (see below)
  "clips": [ ... ],                     // the timeline, in order
  "stabilize": false,                   // true or 0..1 strength (vidstab, 2-pass)
  "grade": "cinematic",                 // preset name or object (see Grade)
  "letterbox": 2.39,                    // cinematic bars (landscape)
  "overlays": [ ... ],                  // text, images, video/graphics, blur regions
  "captions": { ... },                  // word-by-word subtitles
  "audio": { ... },                     // voice clean-up, music, SFX, bleeps, loudness
  "fade": {"in": 0.4, "out": 0.8}       // or a number for both
}
```

## Canvas presets
`youtube`/`1080p`/`landscape` 1920x1080, `720p`, `4k`, `reels`/`shorts`/`tiktok`/`vertical`/`story`
1080x1920, `square` 1080x1080, `portrait`/`instagram` 1080x1350. Omit to keep the first clip's
size. fps defaults to the source (max 60).

## Clips
```json
{"src": "raw.mp4", "in": 12.4, "out": 31.0,      // seconds in the source; out omitted = to the end
 "speed": 1.0,                                   // 0.25..4; audio pitch is kept (atempo)
 "smooth": false,                                // true = optical-flow slow motion (slow to render)
 "volume": 1.0, "mute": false,
 "fit": "auto",                                  // auto | crop | pad | blur | stretch
 "focus": "auto",                                // auto (face) | [x, y] 0..1 for crop position
 "zoom": 1.0, "zoom_center": [0.5, 0.5],         // punch-in, e.g. 1.15 on every 2nd jump cut
 "kenburns": false,                              // "in" | "out" | "left" | "right" slow move
 "dur": 4.0,                                     // wanted length; freezes the last frame if the source is shorter
 "vf": "hflip",                                  // extra raw ffmpeg video filters (advanced)
 "transition": {"type": "fade", "dur": 0.5}}     // transition INTO this clip; "cut" = none
```
Image clips: `{"src": "photo.jpg", "duration": 3, "kenburns": "in"}`.
Solid colour: `{"color": "#000000", "duration": 1}`.

`fit: auto` = crop when aspect ratios are close; when turning landscape into vertical it
crops around the detected face, or uses a blurred-background fill when there is no face.

Transitions: fade, dissolve, fadeblack, fadewhite, wipeleft/right/up/down,
slideleft/right/up/down, smoothleft/right/up/down, circleopen, circleclose, circlecrop,
rectcrop, radial, zoomin, pixelize, hblur, distance, squeezeh, squeezev, diagtl, diagtr.
Aliases: crossfade, whip, push, zoom, blur, black, white, flash. Each transition shortens
the timeline by its duration (clips overlap).

## Grade
Preset string, or an object that starts from a preset and overrides fields:
```json
{"preset": "cinematic", "brightness": 0.02, "contrast": 1.1, "saturation": 1.05, "gamma": 1.0,
 "temperature": 5600, "tint": 0.0, "teal_orange": 0.6, "vibrance": 0.2, "curve": "s",
 "fade": 0.04, "vignette": 0.4, "grain": 5, "sharpen": 0.3, "denoise": false,
 "lut": "looks/film.cube", "auto": false}
```
Presets: none, natural, auto (auto levels/white balance), cinematic, teal_orange, warm,
golden, cool, vintage, film, bw, moody, vibrant, bright, pastel, matte, neon.
`temperature` is the target in Kelvin (6500 neutral; lower = warmer, higher = cooler).
`brightness` -1..1 (small steps: ±0.03), `contrast`/`saturation` ~0.8..1.4,
`curve`: "s" or an ffmpeg curves preset (vintage, lighter, darker, increase_contrast,
strong_contrast, medium_contrast, cross_process). `lut` = any .cube file.

## Overlays
Times are on the OUTPUT timeline (after cuts). Text uses libass with HarfBuzz shaping
(Bangla OK, bundled fonts: Anton, Poppins, Hind Siliguri, Noto Sans Bengali).
```json
{"type": "text", "style": "title|hook|subtitle|lower_third|label|text|price|cta|disclaimer", "text": "Hello",
 "old": "৳1200 (price style: struck-through old price)",
 "sub": "second line (lower_third)", "start": 1, "end": 4,
 "pos": "center|top|bottom|top-left|top-right|bottom-left|bottom-right|upper-third|lower-third" or [x, y],
 "size": 0.06, "color": "#FFFFFF", "accent": "#FFD400", "box": true, "box_color": "#000000",
 "anim": "pop|fade|slide|rise|typewriter", "fade": 0.25, "upper": true, "font": "Anton"}

{"type": "image", "src": "logo.png", "start": 0, "end": null, "pos": "top-right",
 "scale": 0.12, "opacity": 0.85, "fade": 0.3}

{"type": "video", "src": "title.mov", "start": 0, "pos": "full"}          // Remotion/Blender graphic with alpha
{"type": "video", "src": "cam.mp4", "start": 5, "end": 20, "pos": "bottom-right",
 "scale": 0.3, "use_audio": false, "volume": 1.0, "loop": false}           // picture-in-picture
{"type": "video", "src": "greenscreen.mp4", "chromakey": "#00FF00", "similarity": 0.12, "pos": "full"}

{"type": "blur", "rect": [0.6, 0.1, 0.3, 0.2], "start": 3, "end": 9, "strength": 20}  // hide a region
{"type": "pixelate", "rect": [x, y, w, h], "start": 0, "end": 5, "strength": 16}
```
`scale` is a fraction of the canvas width. `pos: "full"` fits the overlay to the canvas.
Named positions stay inside the platform safe zone automatically (no text under app buttons).
Defaults: `price` upper third, `cta` above the bottom line, `disclaimer` small at the bottom;
captions move up when a disclaimer is on screen.

## Captions
```json
"captions": {"words": "words.json",           // from transcribe.py (or "srt": "subs.srt")
             "style": "pop",                  // clean | pop | bold | karaoke | box | minimal
             "highlight": "#FFD400", "color": "#FFFFFF", "pos": 0.70,   // pos = 0..1 from top
             "per_line": 3, "size": 0.07, "upper": true, "font": "Poppins ExtraBold",
             "drop_fillers": true, "max_chars": 22,
             "export_srt": true,              // also writes <output>.srt (default true)
             "burn": true}                    // false = only the .srt (YouTube/Facebook CC upload)
"captions": {"auto": true, "language": "bn", "model": "medium", "style": "clean"}   // transcribe the cut
```
A transcript of the RAW file is remapped through the cuts automatically (words that were
cut out disappear). A translated SRT written by you works the same way.

## Audio
```json
"audio": {
  "voice": {"mode": "original|isolate|mute|path/to/voiceover.wav",
            "enhance": true,           // high-pass, RNNoise, EQ, compressor, de-esser
            "denoise": "rnn|fft|false", "gain_db": 0},
  "music": {"src": "song.mp3", "gain_db": -18, "duck": true, "duck_amount": 0.6,
            "start": 0, "end": null, "offset": 30, "loop": true, "fade_in": 1, "fade_out": 2},
  "sfx": [{"src": "sfx/whoosh.wav", "at": 3.2, "gain_db": -6}],
  "bleeps": [{"start": 12.3, "end": 12.7}],
  "loudness": -14                       // LUFS; -14 social/YouTube, -16 podcasts, -23 TV (platform tv), null = off
}
```
`isolate` runs Demucs on the cut and keeps only the voice (removes background music/noise).
`offset` starts the song N seconds in (skip a slow intro). Music is ducked under speech.

## Commands
```
python render.py plan.json            # final
python render.py plan.json --draft    # half-res, fast: check timing first
python render.py plan.json --pass1    # assemble only; prints the cut path (to transcribe it)
python render.py plan.json --variants youtube,instagram_reels,instagram_feed   # all platforms
```
Pass 1 (the cut) is cached in `.eve_work/`; changing grade/overlays/captions/audio only
re-runs pass 2.

## brand.json
```json
{"name": "Cha Bari", "colors": {"primary": "#E63946", "accent": "#FFB703", "text": "#FFFFFF", "bg": "#1D3557"},
 "logo": "logo.png", "product": "pack.png", "tagline": "প্রতিদিন তাজা", "website": "chabari.com.bd",
 "phone": "01700-000000", "handle": "@chabari",
 "font_files": ["fonts/MyBrand-Bold.ttf"], "font_heading": "MyBrand", "font_body": "Poppins",
 "watermark": true, "watermark_pos": "top-right", "watermark_scale": 0.11, "watermark_opacity": 0.85}
```
Used by render.py (`"brand"`), remotion_gfx.py (`--brand`) and ovc_build.py. `font_heading`
must be the font's family name (as the OS shows it).

## Outputs next to the video
`<output>.mp4`, `<output>.srt` (when captions), `.eve_work/final_words.json` (final-timeline
words: use for chapters/titles), `.eve_work/timeline.json` (segment start times).
