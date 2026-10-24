# Examples

- `plan_reels.json` - a talking-head edit for Reels/Shorts/feed (replace `raw.mp4`, `words.json`,
  music and graphics with your own files). Render:
  `python ../skills/everything-video-editing/scripts/render.py plan_reels.json`
- `brand.json` - brand kit used by render.py, remotion_gfx.py (`--brand`) and ovc_build.py.
- `script_ovc.json` - the 30/15/6 s offer ad from the README GIF, with generated sample footage
  (`bg2.mp4`, `shot_pack.mp4`, `pack.png`, `logo.png`). Build:
  `python ../skills/everything-video-editing/scripts/ovc_build.py script_ovc.json --storyboard-only`
  then again without the flag. The voice uses edge-tts (internet); set
  `"voice": {"engine": "silent"}` to build without speech.
