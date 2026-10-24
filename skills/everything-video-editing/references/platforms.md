# Platforms: what each one needs

`scripts/platforms.py` holds the numbers (canvas, safe zones, caption height, limits,
thumbnail sizes). Set `"platform": "<name>"` in plan.json, or render several at once with
`render.py plan.json --variants youtube,instagram_reels,instagram_feed`. Limits change
often; check the app when a limit matters.

| platform key | canvas | keep text out of (top / bottom / sides) | length | notes |
|---|---|---|---|---|
| `youtube` | 1920x1080 | 5% / 8% / 5% | any; 8-20 min sweet spot | upload the `.srt` as CC; chapters in the description; thumbnail 1280x720 |
| `youtube_shorts` | 1080x1920 | 8% / 20% / right 14% | up to 3 min; 20-60 s best | loop-friendly ending; title text in the first second |
| `instagram_reels` | 1080x1920 | 14% / 35% / 6% | up to 3 min; 15-45 s best | cover 1080x1920 with key content in the centre 1080x1440 (grid crop) |
| `instagram_feed` | 1080x1350 | 5% / 8% / 5% | 15-60 s | 4:5 takes the most feed space |
| `instagram_story` | 1080x1920 | 14% / 20% / 6% | 60 s per story | stickers/links sit in the middle; leave room |
| `facebook_reels` | 1080x1920 | 14% / 35% / 6% | 15-60 s best | Facebook now treats most video as Reels |
| `facebook_feed` | 1080x1350 | 5% / 10% / 5% | 30 s-3 min | captions on: most people watch muted |
| `facebook_landscape` | 1920x1080 | 5% / 10% / 5% | long OK | lives, talks, long stories |
| `tiktok` | 1080x1920 | 7% / 25% / right 12% | up to 10 min; 15-60 s best | right-side buttons: no text there |
| `linkedin` | 1080x1350 | 5% / 10% / 5% | 30-90 s | professional tone, captions essential |
| `x` | 1920x1080 | 5% / 10% / 5% | 140 s (free accounts) | |
| `whatsapp_status` | 1080x1920 | 10% / 15% / 5% | 60 s per status | compress: `quick.py compress --mb 16` |
| `tv` | 1920x1080 | 10% all round (title safe) | 6/15/20/30/60 s | loudness -23 LUFS, no burned captions unless asked |
| `square` | 1080x1080 | 6% / 8% / 6% | | ads, carousels |

## Creator playbook (FB / IG / YT)
- **Hook in 1-2 s**: movement, a bold claim or question as a `hook` text overlay, or start
  mid-action. Never open on a logo for social (save the logo for the end or a watermark).
- **Captions always** for Reels/Shorts/TikTok/FB (most viewing is muted). One style per
  channel; keep it consistent across videos (save it in a brand.json).
- **Pacing**: Reels/Shorts cut every 1.5-3 s (jump cut + punch-in zoom 1.08-1.15 on every
  2nd cut). YouTube long-form: 4-8 s, B-roll over talking head every 20-40 s.
- **Retention beats**: pattern break every 5-8 s on short form (zoom, B-roll, text pop, SFX).
- **End**: short form loops: end on a line that leads back to the start; long form: EndCard
  (YouTube end screen, 5-20 s) + subscribe CTA where nobody talks.
- **One master, many exports**: edit once in the master aspect, then `--variants`.
  Render Remotion graphics per variant size. Check every variant with `safezone.py`.
- **Deliver with the video**: `.srt` (YouTube/Facebook CC), a thumbnail/cover from
  `thumbnail.py --platform`, and write a title, description (with chapters from the
  transcript timestamps in `.eve_work/final_words.json`) and 3-8 hashtags in the user's
  language.
- **Loudness** -14 LUFS, true peak under -1 dBFS (render does this).
- **Music rights**: only music the user owns/licensed, the generated beds, or the platform's
  own library added in-app. Say so if they ask for a famous song.

## Chapters (YouTube)
From the transcript, pick topic changes; first chapter must be `0:00`; at least 3 chapters,
each 10 s or longer. Format lines as `0:00 Intro` in the description.
