"""Platform presets: canvas, safe zones, caption height, loudness, length limits, thumbnail size.

Safe zones are fractions of the frame that platform UI (buttons, captions, profile bar)
covers; keep text and logos inside. Meta Reels values follow Meta's ad guidance
(top 14%, bottom 35%, sides 6%), the strictest vertical placement. Platforms change
limits often: treat max_s as a guide and check the app when it matters.

  python platforms.py            # print the table
"""
from __future__ import annotations

import json

V916 = (1080, 1920)

PLATFORMS = {
    # name: canvas, safe(top,bottom,left,right), caption bottom edge (0..1 from top),
    #       max seconds (None = very long), sweet spot seconds, thumbnail size, label
    "youtube":          dict(size=(1920, 1080), safe=(0.05, 0.08, 0.05, 0.05), cap=0.90, max_s=None,
                             sweet=(480, 1200), thumb=(1280, 720), label="YouTube video"),
    "youtube_shorts":   dict(size=V916, safe=(0.08, 0.20, 0.05, 0.14), cap=0.72, max_s=180,
                             sweet=(20, 60), thumb=V916, label="YouTube Shorts"),
    "instagram_reels":  dict(size=V916, safe=(0.14, 0.35, 0.06, 0.06), cap=0.64, max_s=180,
                             sweet=(15, 45), thumb=V916, cover_grid=(1080, 1440), label="Instagram Reels"),
    "instagram_feed":   dict(size=(1080, 1350), safe=(0.05, 0.08, 0.05, 0.05), cap=0.86, max_s=3600,
                             sweet=(15, 60), thumb=(1080, 1350), label="Instagram feed (4:5)"),
    "instagram_story":  dict(size=V916, safe=(0.14, 0.20, 0.06, 0.06), cap=0.76, max_s=60,
                             sweet=(5, 15), thumb=V916, label="Instagram Story"),
    "facebook_reels":   dict(size=V916, safe=(0.14, 0.35, 0.06, 0.06), cap=0.64, max_s=None,
                             sweet=(15, 60), thumb=V916, label="Facebook Reels / video"),
    "facebook_feed":    dict(size=(1080, 1350), safe=(0.05, 0.10, 0.05, 0.05), cap=0.86, max_s=None,
                             sweet=(30, 180), thumb=(1080, 1350), label="Facebook feed (4:5)"),
    "facebook_story":   dict(size=V916, safe=(0.14, 0.20, 0.06, 0.06), cap=0.76, max_s=60,
                             sweet=(5, 15), thumb=V916, label="Facebook Story"),
    "facebook_landscape": dict(size=(1920, 1080), safe=(0.05, 0.10, 0.05, 0.05), cap=0.88, max_s=None,
                             sweet=(60, 600), thumb=(1280, 720), label="Facebook landscape video"),
    "tiktok":           dict(size=V916, safe=(0.07, 0.25, 0.04, 0.12), cap=0.70, max_s=600,
                             sweet=(15, 60), thumb=V916, label="TikTok"),
    "linkedin":         dict(size=(1080, 1350), safe=(0.05, 0.10, 0.05, 0.05), cap=0.86, max_s=600,
                             sweet=(30, 90), thumb=(1080, 1350), label="LinkedIn (4:5)"),
    "x":                dict(size=(1920, 1080), safe=(0.05, 0.10, 0.05, 0.05), cap=0.88, max_s=140,
                             sweet=(15, 60), thumb=(1280, 720), label="X / Twitter"),
    "whatsapp_status":  dict(size=V916, safe=(0.10, 0.15, 0.05, 0.05), cap=0.78, max_s=60,
                             sweet=(10, 30), thumb=V916, label="WhatsApp Status"),
    "tv":               dict(size=(1920, 1080), safe=(0.10, 0.10, 0.10, 0.10), cap=0.86, max_s=None,
                             sweet=(15, 60), thumb=(1920, 1080), label="TV / OVC 16:9 (title-safe 90%)"),
    "square":           dict(size=(1080, 1080), safe=(0.06, 0.08, 0.06, 0.06), cap=0.86, max_s=None,
                             sweet=(15, 60), thumb=(1080, 1080), label="Square 1:1"),
}

ALIASES = {
    "yt": "youtube", "shorts": "youtube_shorts", "yt_shorts": "youtube_shorts",
    "reels": "instagram_reels", "ig": "instagram_reels", "ig_reels": "instagram_reels",
    "instagram": "instagram_reels", "ig_feed": "instagram_feed", "ig_story": "instagram_story",
    "fb": "facebook_reels", "facebook": "facebook_reels", "fb_reels": "facebook_reels",
    "fb_feed": "facebook_feed", "fb_story": "facebook_story", "fb_landscape": "facebook_landscape",
    "twitter": "x", "whatsapp": "whatsapp_status", "ovc": "tv", "tvc": "tv",
    "vertical": "instagram_reels", "story": "instagram_story", "landscape": "youtube",
}


def get(name: str | None) -> dict | None:
    if not name:
        return None
    key = ALIASES.get(str(name).lower(), str(name).lower())
    p = PLATFORMS.get(key)
    if p:
        p = dict(p, name=key)
    return p


def safe_px(p: dict, w: int, h: int) -> dict:
    t, b, l, r = p["safe"]
    return {"top": int(t * h), "bottom": int(b * h), "left": int(l * w), "right": int(r * w)}


def default_safe(w: int, h: int) -> tuple:
    return (0.12, 0.25, 0.06, 0.10) if h > w * 1.3 else (0.05, 0.08, 0.05, 0.05)


if __name__ == "__main__":
    print(json.dumps({k: {"size": f"{v['size'][0]}x{v['size'][1]}", "safe_tblr": v["safe"],
                          "caption_bottom": v["cap"], "max_s": v["max_s"], "sweet_s": v["sweet"],
                          "thumb": f"{v['thumb'][0]}x{v['thumb'][1]}", "label": v["label"]}
                      for k, v in PLATFORMS.items()}, indent=1))
