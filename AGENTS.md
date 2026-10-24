# Everything-videoEditing - agent instructions

This repository is an **agent skill** for video editing. Any coding agent with a shell
(OpenAI Codex, Gemini CLI, Claude Code, Cursor, Copilot CLI, ...) can use it.

**When the user asks for anything involving editing or making a video** (reels, shorts,
YouTube edits, captions/subtitles, cutting pauses, colour, music, sound effects, voice-over,
ads/OVC, slideshows, compressing, converting, GIFs, restoring old videos), read and follow:

    skills/everything-video-editing/SKILL.md

Its scripts live in `skills/everything-video-editing/scripts/` and its guides in
`skills/everything-video-editing/references/`. Treat `SKILL_DIR` in SKILL.md as
`skills/everything-video-editing` (relative to this repo), or the installed copy
(`~/.codex/skills/everything-video-editing`, `~/.claude/skills/...`, `~/.gemini/skills/...`).

Quick start for the agent:
1. `python skills/everything-video-editing/scripts/doctor.py` - see what is installed.
   If tools are missing, ask the user before running
   `skills/everything-video-editing/setup/install_windows.ps1` or `.../install_unix.sh`.
2. `python skills/everything-video-editing/scripts/analyze.py <video> --out analysis.json`
   then ask the user the suggested questions (numbered list with lettered options if you
   have no question tool), build `plan.json`, and run `scripts/render.py plan.json --draft`.

Rules: never overwrite the user's originals; write outputs to an `edited/` folder; reply in
the user's language; check every render by probing it and looking at its contact sheet.
