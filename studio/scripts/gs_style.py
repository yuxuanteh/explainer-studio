"""Channel visual style for Manim: colours, fonts, and reusable pieces (values from studio.toml).

    import gs_env, gs_style as gs
    from manim import *
    class S(Scene):
        def construct(self):
            gs.setup(self)
            self.add(gs.watermark(), gs.source_note("资料来源：USGS"))
"""
from manim import (BOLD, DOWN, HEAVY, ITALIC, LEFT, MEDIUM, NORMAL, ORIGIN, RIGHT, UL, UR, UP, DL,
                   Group, ImageMobject, Line, Rectangle, RoundedRectangle, Text, VGroup, config)

import gs_env

# ---- palette ([palette] in studio.toml; the old names stay as aliases: GOLD = accent, CYAN = accent2) ----
_P = gs_env.CFG.get("palette", {})
ACCENT = GOLD = _P.get("accent", "#F2B90D")
ACCENT_HI = GOLD_HI = _P.get("accent_hi", "#FFD95C")
ACCENT_DEEP = GOLD_DEEP = _P.get("accent_deep", "#8A6400")
ACCENT2 = CYAN = _P.get("accent2", "#00C8D2")
DARK = _P.get("bg", "#1A160C")
DARKER = _P.get("bg_deep", "#131008")
CARD = _P.get("card", "#231E10")
LINE = _P.get("line", "#493F22")
TEXT = _P.get("text", "#F5F1E8")
MUTED = _P.get("muted", "#CBBC90")

# ---- fonts ([fonts] in studio.toml; installed in the OS, see the gs_env note) ----
_F = gs_env.CFG.get("fonts", {})
ZH_SERIF = _F.get("title", "Noto Serif SC")      # titles, weight=HEAVY / BOLD
ZH_SANS = _F.get("body", "Noto Sans SC")         # captions, labels
EN_LABEL = _F.get("label", "Space Grotesk")      # Latin kickers / labels, weight=BOLD / MEDIUM
EN_TAG = _F.get("tagline", "Playfair Display")   # tagline, weight=BOLD, slant=ITALIC
EN_BODY = _F.get("body_latin", "Manrope")

CH = gs_env.CHANNEL
WATERMARK = gs_env.PROJECT / CH.get("logo_watermark", "brand/logo/watermark.png")
SEAL = gs_env.PROJECT / CH.get("logo_seal", "brand/logo/seal.png")
PX = config.frame_width / 1920   # 1 px of a 1080p frame, in Manim units


def px(n):
    return n * PX


_ref_height = {}


def text(s, font=ZH_SANS, size=40, weight=NORMAL, color=TEXT, slant=NORMAL):
    """Text whose CJK glyph height is `size` px on a 1080p frame, whatever the string."""
    key = (font, weight, slant)
    if key not in _ref_height:
        _ref_height[key] = Text("国H", font=font, weight=weight, slant=slant, font_size=48).height
    t = Text(s, font=font, weight=weight, slant=slant, color=color, font_size=48)
    return t.scale(px(size) / _ref_height[key])


def setup(scene, bg=DARK):
    scene.camera.background_color = bg


def watermark(opacity=0.7, size=60):
    """Logo top-right (or the channel short name when there is no logo file)."""
    if WATERMARK.exists():
        m = ImageMobject(str(WATERMARK)).set(height=px(size)).set_opacity(opacity)
    else:
        m = text(CH.get("short_name", "TV"), EN_LABEL, size * 0.42, weight=BOLD, color=GOLD).set_opacity(opacity)
    return m.to_corner(UR, buff=px(36))


def source_note(s):
    """Data source credit: top-right, left of the watermark (bottom is reserved for subtitles)."""
    t = text(s, ZH_SANS, 18, color=MUTED).set_opacity(0.85)
    return t.to_corner(UR, buff=px(36)).shift(LEFT * px(84) + DOWN * px(20))


def label(zh, en, color=GOLD):
    """Rock / feature label: gold bar + Chinese name + English name."""
    zh_t = text(zh, ZH_SANS, 34, weight=BOLD)
    en_t = text(en, EN_LABEL, 24, weight=MEDIUM, color=color)
    words = VGroup(zh_t, en_t).arrange(DOWN, aligned_edge=LEFT, buff=px(8))
    bar = Rectangle(width=px(6), height=words.height, fill_color=color, fill_opacity=1, stroke_width=0)
    bar.next_to(words, LEFT, buff=px(14))
    return VGroup(bar, words)


def name_tag(name=None, zh=None):
    """Presenter lower-third: accent bar + name + one-line description (show 3-5 s at first appearance)."""
    name = name or CH.get("presenter", "Presenter")
    zh = zh or CH.get("presenter_title", "")
    lines = VGroup(text(name, ZH_SERIF, 30, weight=HEAVY),
                   text(zh, ZH_SANS, 20, weight=MEDIUM, color=MUTED)).arrange(DOWN, aligned_edge=LEFT, buff=px(8))
    bg = Rectangle(width=lines.width + px(40), height=lines.height + px(28), fill_color=DARKER,
                   fill_opacity=0.85, stroke_width=0)
    lines.move_to(bg)
    bar = Rectangle(width=px(6), height=bg.height, fill_color=GOLD, fill_opacity=1, stroke_width=0)
    bar.next_to(bg, LEFT, buff=0)
    return VGroup(bar, bg, lines)


def seal(size=420):
    """Round channel badge (logo_seal), or a ring with the short name when there is no file."""
    if SEAL.exists():
        return ImageMobject(str(SEAL)).set(height=px(size))
    from manim import Circle
    ring = Circle(radius=px(size) / 2, stroke_color=GOLD, stroke_width=6, fill_color=DARKER, fill_opacity=1)
    inner = Circle(radius=px(size) * 0.42, stroke_color=GOLD, stroke_width=2)
    name = text(CH.get("short_name", "TV"), ZH_SERIF, size * 0.22, weight=HEAVY, color=GOLD)
    return VGroup(ring, inner, name)


def kicker(s, zh=None, color=GOLD, size=24):
    """English kicker in Space Grotesk; optional Chinese part set in Noto Sans SC."""
    k = text(s, EN_LABEL, size, weight=BOLD, color=color)
    if zh:
        z = text(zh, ZH_SANS, size, weight=BOLD, color=color)
        k = VGroup(k, z).arrange(RIGHT, buff=px(size * 0.6), aligned_edge=DOWN)
    return k


def title(s, size=72, color=TEXT):
    return text(s, ZH_SERIF, size, weight=HEAVY, color=color)


def tagline(s=None, size=34, color=MUTED):
    s = s or CH.get("tagline", "")
    return text(s, EN_TAG, size, weight=BOLD, slant=ITALIC, color=color)
