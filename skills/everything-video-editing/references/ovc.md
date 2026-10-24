# OVC / TVC / promo making

OVC = online video commercial (the web cousin of a TVC). Typical asks: a product ad, an
Eid/Puja/Boishakh offer, a restaurant or shop promo, an app explainer, a real-estate or
event teaser, a corporate brand film cut-down.

## Process
1. **Brief** (ask, max 4 questions per round with options): product/brand, the ONE message,
   audience, offer/price, call to action (call, visit, order on FB page, website), deadline,
   platforms + lengths, language (Bangla/English/both), tone (festive, premium, funny,
   emotional, energetic), assets they have (footage, product photos, logo, brand colours,
   fonts, music, VO artist or TTS).
2. **Concept + script**: write 2-3 short concepts (one line each) and let them pick. Then a
   script table: scene, visual, VO line, super (on-screen text), duration. Rules of thumb:
   - 2.3 Bangla words/sec, 2.6 English words/sec for VO. 30 s = about 60-70 words total.
   - Super = 3-6 words. Never repeat the VO word-for-word in the super.
   - Structure: hook (0-3 s) → problem/desire → product as the answer → proof/feature
     (callouts, before/after, numbers) → offer (badge/price) → CTA + end slate (logo,
     tagline, contact) → legal line.
   - Brand name or product visible by 3-5 s on social; logo at the end for 2-4 s.
3. **brand.json** (colours, logo, fonts, tagline, website, phone, handle). Reuse for every
   video of that brand.
4. **script.json** → `ovc_build.py script.json --storyboard-only` gives TTS timings and
   `storyboard.html` (thumbnails, VO, supers, timing) for client approval. Share it.
5. **Draft** `ovc_build.py script.json --draft`, review contact sheets, safezone checks.
6. **Finals**: all versions × aspects. Name files `<Brand>_<Title>_<len>_<aspect>.mp4`.
7. **QA**: brand colours/logo correct, price and phone number correct (read them back to the
   user), legal line present, spelling (Bangla too), loudness (-14 social, -23 TV),
   text inside safe zones, end slate long enough to read (2.5 s+).

## Versions and cut-downs
- Lengths: 60 s / 30 s (hero) / 15 s / 6 s bumper. The 15 s keeps hook + product + offer +
  end; the 6 s is product/offer + logo only (no story).
- Aspects: 16:9 (YouTube/TV), 9:16 (Reels/Stories/Shorts/TikTok), 1:1 or 4:5 (feed).
  `variants` in script.json renders each; graphics are rendered per size automatically.
- If a version runs long, the report warns: shorten VO, raise `voice.rate` (+10-20%), or drop
  a scene.

## Voice-over
- Best: the user's own VO artist (record per scene, set `vo_file`). Use TTS as scratch to lock
  timing, then replace.
- TTS: `tts.py` / `"voice"` in script.json. Bangla voices: bn-BD-NabanitaNeural (female),
  bn-BD-PradeepNeural (male), bn-IN-TanishaaNeural, bn-IN-BashkarNeural. English:
  en-US-AriaNeural, en-US-GuyNeural, en-GB-SoniaNeural, en-IN-NeerjaNeural. Engine "silent"
  makes timing-only silence when no voice is available yet.
- These neural voices come from Microsoft's online service (edge-tts); for paid broadcast work
  tell the user to check the terms or use a human voice.

## Graphics for ads (remotion_gfx.py, all take --brand brand.json)
LogoReveal (intro/outro), OfferBadge (price burst), FeatureCallout (pointers on product),
BeforeAfter (wipe compare), StatCounter (numbers), KineticText (punchy words),
EndSlate (packshot: product + logo + tagline + CTA + contact + disclaimer), CallToAction.
Text styles in plan overlays: `price` (with `old` struck through), `cta`, `disclaimer`.

## Music
Brand-safe only: user-supplied licensed tracks (pick by mood with CLAP from their library)
or a generated bed (`"music": {"mood": "uplifting", "bpm": 118}`). Cut scenes on the beat
when possible (`analyze_audio.py beats`). Duck under VO (automatic).

## script.json example
```json
{
  "title": "Eid Offer", "brand": "brand.json",
  "voice": {"voice": "bn-BD-NabanitaNeural", "rate": "+5%"},
  "music": {"mood": "uplifting", "bpm": 118},
  "captions": true, "disclaimer": "*শর্ত প্রযোজ্য",
  "variants": ["youtube", "instagram_reels", "instagram_feed"],
  "versions": [{"name": "30s"}, {"name": "15s", "scenes": [1, 2, "end"]}, {"name": "6s", "scenes": [2, "end"]}],
  "scenes": [
    {"card": {"comp": "LogoReveal", "props": {}}, "dur": 1.5},
    {"media": "shots/pour.mp4", "in": 2, "vo": "সকালের শুরু হোক এক কাপ তাজা চায়ে", "super": "প্রতিদিন তাজা", "transition": "fade"},
    {"media": "pack.png", "vo": "ঈদ উপলক্ষে সব প্যাকেটে পঞ্চাশ শতাংশ ছাড়",
     "badge": {"label": "৫০% ছাড়", "price": "৳২৪৯", "oldPrice": "৳৪৯৯"}, "transition": "slideleft"},
    {"media": "shots/family.mp4", "vo": "আজই অর্ডার করুন",
     "gfx": {"comp": "FeatureCallout", "props": {"items": [{"text": "১০০% প্রাকৃতিক", "x": 0.45, "y": 0.45}]}}}
  ],
  "end_slate": {"comp": "EndSlate", "props": {"product": "pack.png", "cta": "এখনই অর্ডার করুন"}, "dur": 3}
}
```
Scene keys: `media` (video/image), `in`, `speed`, `volume` (natural sound, default 0),
`zoom`, `kenburns`, `vo` or `vo_file`, `dur` (minimum), `super` (string or
{text, style, pos}), `badge`, `gfx`, `card` (full-frame graphic instead of media), `color`,
`transition`. Top level: `grade` (default vibrant), `fit` (default crop: centre-crops each shot to the aspect; "auto" = face-aware or blurred fill), `fps`, `size` (when no variants),
`loudness`, `caption_style`, `auto_sfx`, `output_dir`.
