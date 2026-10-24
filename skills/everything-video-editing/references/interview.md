# Interview mode: ask, then edit

When the user hands over footage, do not guess the whole edit. Analyse, then ask a few
sharp multiple-choice questions built from what the footage actually contains, then edit,
then ask again on the draft. Use the AskUserQuestion tool (1-4 questions per call, 2-4
options each; an "Other" free-text choice is added automatically). Put the recommended
option first and add "(Recommended)" to its label. Write questions and labels in the
user's language (Bangla users: Bangla script, technical words can stay English).

## Loop
1. `analyze.py <files> --out analysis.json` (add `--fast` for many files or a slow PC).
   Read `found` (one-line findings) and open `contact_sheet` to see the footage.
2. Tell the user in 1-2 lines what you see ("৩ মিনিটের কথা বলা ভিডিও, বাংলায়, ২৫টা বিরতি,
   পেছনে হালকা নয়েজ").
3. **Round 1** = `rounds[0]` (platform, length, style, captions/music). Ask it.
4. Merge the chosen options' `patch` objects into your edit decisions. Keys starting with
   `_` are instructions for you (e.g. `_target_s`, `_jumpcuts`, `_music_mood`, `_hook`,
   `_lower_third`, `_cta`, `_thumbnail`, `_beat_sync`, `_highlights`, `_translate_to`).
5. **Round 2** = `rounds[1]` (cuts, voice clean-up, music, colour, stabilise, extras). Skip
   questions already answered by round 1 or by the user's first message. If the answers
   need inputs (their name for a lower third, their music folder, brand colours, a hook
   line), ask for those in the same round as free-text via "Other" or one short message.
6. Build: transcribe/cutlist/graphics → plan.json → `render.py --draft`.
7. Show the draft: probe it, look at the contact sheet, send 2-4 key frames (or the draft
   file), then ask `feedback_question` (Looks good / Pacing / Captions / Music). Follow-ups
   are short targeted questions with options again ("Faster" / "Slower" / "Only the intro").
8. Repeat 6-7 until "Looks good", then render final (+ `--variants` + srt + thumbnail).

## Rules
- Max 2 question rounds before the first draft; a draft answers more than questions do.
- Never ask what the analysis already knows (orientation, language, length).
- If the user says "just do it", "তুমি ঠিক করো" or gives a complete brief, skip to the
  draft with the recommended options and say which you chose in one line.
- No AskUserQuestion tool (some agents/CLIs): ask the same questions as a short numbered list
  with lettered options (1a/1b/...) and accept replies like "1b 2a 3c".
- Unattended / scheduled runs: take the recommended options, render, report choices.

## Extra question bank (pick when relevant)
- Hook text: offer 3 hook lines written from the transcript (options) + Other.
- Thumbnail text: 3 options of 2-4 words.
- Caption look: Pop (yellow word highlight) / Clean white / Karaoke / Boxed.
- Highlight colour: Yellow / Green / Brand colour / White only.
- Music mood: Calm / Uplifting / Cinematic / Festive (Eid, wedding) / From my folder.
- Pace: Fast (cut every 1-2 s) / Medium / Relaxed.
- Language of captions: same as speech / English / both (two lines).
- Branding: Logo watermark / Lower third / Brand colours on text / None.
- For OVC: Length set (60/30/15/6), aspects, VO (my recording / Bangla female TTS / Bangla
  male TTS / English), offer details, CTA type (call / FB page / website / visit shop).
