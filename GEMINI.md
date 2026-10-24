# Everything-videoEditing (Gemini CLI)

You have a video-editing skill. When the user wants any video edited or made (reels,
shorts, YouTube, captions, cuts, colour, music, SFX, voice-over, ads/OVC, slideshows,
compress/convert/GIF, old-video restore), read `skills/everything-video-editing/SKILL.md`
in this extension/repository folder and follow it. `SKILL_DIR` = that skill folder.

- Start with `python <SKILL_DIR>/scripts/doctor.py`, then
  `python <SKILL_DIR>/scripts/analyze.py <video> --out analysis.json`.
- Ask the user the suggested questions as a short numbered list with lettered options
  (1a, 1b ...), recommended option first, in the user's language. Then edit.
- Render drafts with `scripts/render.py plan.json --draft`, check them (probe + contact
  sheet), then the final with `--variants` for every platform the user posts to.
- Never overwrite originals. Ask before running the installers in `setup/` (large download).

If Agent Skills are enabled in Gemini CLI (`/settings`), the installer also links the skill
into `~/.gemini/skills/everything-video-editing` so it loads automatically.
