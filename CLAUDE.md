# Everything-videoEditing

This repo is a Claude Code plugin / Agent Skill. The skill is
`skills/everything-video-editing/SKILL.md` - follow it whenever the user asks for video work.

Developing the skill itself:
- Scripts: `skills/everything-video-editing/scripts/` (Python 3.10+, FFmpeg). Shared helpers
  in `vtools.py`; `render.py` is the engine; keep every script runnable on Windows
  (cwd-relative filter paths, no inline JSON in PowerShell).
- Remotion graphics: `skills/everything-video-editing/graphics/remotion/src/` (React 19,
  Remotion 4). Register new compositions in `Root.tsx` and list them in
  `scripts/remotion_gfx.py` (`COMPS`).
- Test a change by rendering something small and looking at frames
  (`scripts/probe.py out.mp4` → contact sheet).
