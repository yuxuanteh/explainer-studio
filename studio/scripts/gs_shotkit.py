"""Reusable Manim building blocks for episodes.

In an episode's shots.py / cam_cg.py:
    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from gs_shotkit import *            # Manim + gs_style as gs + helpers below
    Clocked.E = here(__file__)          # bind this episode's edl.py once

    class S3(Clocked):                  # class name = shot id in edl.SHOTS
        def construct(self):
            title = self.fade_at(gs.title("P-wave"), self.beats["p"])   # appears exactly on the word
            self.add(title, gs.watermark())
            self.run()

Coordinates: at(x, y) takes 1080p pixels (origin top-left). Keep labels above y = 880 (subtitle band).
"""
import numpy as np
from manim import *  # noqa: F401,F403

import gs_style as gs
from gs_episode import here, shot  # noqa: F401
from gs_style import px

SUBTITLE_SAFE_Y = 880


def at(x, y):
    """1080p pixel coords (origin top-left, y down) -> Manim point."""
    return np.array([(x - 960) * px(1), (540 - y) * px(1), 0])


def ramp(t, t0, d=0.4):
    """0 -> 1 smoothly between t0 and t0 + d."""
    a = np.clip((t - t0) / d, 0, 1)
    return a * a * (3 - 2 * a)


# =============================================================================== time-driven scenes

class _Timed:
    E = None
    SHOT = None          # defaults to the class name

    def _bind(self):
        s = shot(self.E, self.SHOT or type(self).__name__.removeprefix("Cam"))
        self.dur, self.beats = s["dur"], s["beats"]
        self.clock = ValueTracker(0)

    def t(self):
        return self.clock.get_value()

    def fade_at(self, mob, t_in, d=0.4, t_out=None, shift=None):
        """Hidden until t_in, then fades (and optionally slides) in; optional fade-out at t_out.
        The position is captured when playback starts, so moving `mob` after this call is fine."""
        state = {}

        def upd(m):
            if "target" not in state:
                state["target"] = m.copy().clear_updaters()
            tgt = state["target"]
            a = ramp(self.t(), t_in, d) * (1 - (ramp(self.t(), t_out, d) if t_out is not None else 0))
            m.become(tgt.copy())
            if shift is not None:
                m.shift(shift * (1 - a))
            if a < 1:
                for sm, ts in zip(m.family_members_with_points(), tgt.family_members_with_points()):
                    sm.set_fill(opacity=ts.get_fill_opacity() * a)
                    sm.set_stroke(opacity=ts.get_stroke_opacity() * a, family=False)
        mob.add_updater(upd)
        return mob

    show = fade_at

    def fade_each(self, group, *args, **kw):
        """fade_at on every member of `group`. Use this when the members are added to the scene individually:
        an updater on a wrapper VGroup that is never added does nothing, so the members would show at t=0."""
        for m in group:
            self.fade_at(m, *args, **kw)
        return group

    def run(self):
        self.play(self.clock.animate.set_value(self.dur), run_time=self.dur, rate_func=linear)


class Clocked(_Timed, Scene):
    """Full-screen shot. Draw state as a function of self.t(); beats come from edl.py word timestamps."""

    def setup(self):
        gs.setup(self)
        self._bind()


class CamClocked(_Timed, Scene):
    """Transparent CG overlay for a camera shot (render with -t). Class name: Cam<shot id>."""

    def setup(self):
        self._bind()


# =============================================================================== labels & icons

def label_chip(text_mob, color=gs.DARKER, opacity=0.75, buff=12):
    return VGroup(BackgroundRectangle(text_mob, color=color, fill_opacity=opacity, buff=px(buff)), text_mob)


def mixed(en, zh, size=30, color=gs.TEXT, zh_color=gs.TEXT):
    """Latin label font + CJK body font side by side. Latin-only fonts have no CJK glyphs -> never mix in one Text."""
    return VGroup(gs.text(en, gs.EN_LABEL, size, weight=BOLD, color=color),
                  gs.text(zh, gs.ZH_SANS, size, weight=BOLD, color=zh_color)).arrange(RIGHT, buff=px(size * 0.35))


def warn_icon(size=30, color=gs.DARK):
    tri = Triangle(stroke_color=color, stroke_width=4, fill_opacity=0).scale(px(size) / 2)
    bang = gs.text("!", gs.EN_LABEL, size * 0.6, weight=BOLD, color=color).move_to(tri.get_center() + DOWN * px(size * 0.08))
    return VGroup(tri, bang)


def pause_icon(size=26, color=gs.GOLD):
    return VGroup(*[Rectangle(width=px(size * 0.28), height=px(size), fill_color=color, fill_opacity=1, stroke_width=0)
                    for _ in range(2)]).arrange(RIGHT, buff=px(size * 0.22))


def play_icon(size=26, color=gs.GOLD):
    return Triangle(fill_color=color, fill_opacity=1, stroke_width=0).scale(px(size) * 0.6).rotate(-PI / 2)


# =============================================================================== example drawings (geoscience;
# add your own topic's reusable drawings here)

def house(size=240, color=gs.TEXT, width=6):
    w = px(size)
    body = Rectangle(width=w, height=w * 0.8, stroke_color=color, stroke_width=width, fill_color=gs.CARD, fill_opacity=1)
    roof = Polygon(body.get_corner(UL) + LEFT * w * 0.08, body.get_corner(UR) + RIGHT * w * 0.08,
                   body.get_top() + UP * w * 0.45, stroke_color=color, stroke_width=width, fill_color=gs.CARD,
                   fill_opacity=1)
    door = Rectangle(width=w * 0.22, height=w * 0.38, stroke_color=color, stroke_width=width * 0.85).align_to(body, DOWN)
    win = Square(side_length=w * 0.2, stroke_color=gs.GOLD, stroke_width=width * 0.85).move_to(
        body.get_center() + w * np.array([0.25, 0.12, 0]))
    return VGroup(roof, body, door, win)


def quake_signal(t, tP, tS, ampP=0.25, ampS=1.0, noise=0.03, seed=0):
    """Synthetic seismogram: noise, small P arrival at tP, large S arrival at tS. Returns (total, p, s)."""
    rng = np.random.default_rng(seed)
    n = noise * np.sin(2 * np.pi * 13.7 * t + rng.uniform(0, 6)) * np.sin(2 * np.pi * 3.1 * t)
    p = np.where(t > tP, ampP * np.sin(2 * np.pi * 6 * (t - tP)) * np.exp(-(t - tP) / 0.6), 0)
    s = np.where(t > tS, ampS * np.sin(2 * np.pi * 3.2 * (t - tS)) * (1 - np.exp(-(t - tS) / 0.12))
                 * np.exp(-np.clip(t - tS, 0, None) / 1.6), 0)
    return n + p + s, p, s


def natural_earth_map(lon0, lat0, scale, cx=960, cy=540, bbox=None, min_area=0.02, decimate=2,
                      fill=gs.CARD, stroke=gs.MUTED):
    """Land polygons (Natural Earth 50m, public domain) in an equirectangular projection.
    scale = px per degree latitude. Polygons clipped by `bbox` (lon0, lat0, lon1, lat1) are skipped,
    so pick a bbox that contains whole islands / coastlines you want. Returns (VGroup, P(lon, lat) -> point)."""
    import cartopy.io.shapereader as shpreader
    from shapely.geometry import box
    coslat = np.cos(np.radians(lat0))

    def P(lon, lat):
        return at(cx + (lon - lon0) * scale * coslat, cy - (lat - lat0) * scale)
    land = VGroup()
    b = bbox or (lon0 - 960 / scale / coslat, lat0 - 540 / scale, lon0 + 960 / scale / coslat, lat0 + 540 / scale)
    path = shpreader.natural_earth(resolution="50m", category="physical", name="land")
    for g in shpreader.Reader(path).geometries():
        if not g.intersects(box(*b)):
            continue
        for poly in getattr(g, "geoms", [g]):
            x0, y0, x1, y1 = poly.bounds
            if poly.area < min_area or x0 < b[0] or x1 > b[2] or y0 < b[1] or y1 > b[3]:
                continue
            xy = np.array(poly.exterior.coords)[::decimate]
            land.add(Polygon(*[P(x, y) for x, y in xy], fill_color=fill, fill_opacity=1, stroke_color=stroke,
                             stroke_width=2))
    return land, P


# =============================================================================== CG on camera footage

class DeskPlane:
    """Perspective for CG standing on a real surface in a static camera shot.

    Measure from a real object on that surface (a box seen corner-on works best):
      near : (x, y) px of the floor point nearest the camera
      A, B : image px per world px along the two horizontal axes (shallow V when a corner faces the camera)
    Verticals stay vertical. F(a, b, h) -> Manim point (h = height above the surface).
    """

    def __init__(self, near, A, B):
        self.near, self.A, self.B = np.array(near, float), np.array(A, float), np.array(B, float)

    def F(self, a, b=0.0, h=0.0):
        q = self.near + a * self.A + b * self.B + np.array([0, -h])
        return at(*q)

    def box_top(self, L, D, H, color=gs.TEXT):
        F = self.F
        return Polygon(F(0, 0, H), F(L, 0, H), F(L, D, H), F(0, D, H), stroke_color=color, stroke_width=3,
                       fill_color=color, fill_opacity=0.22)

    def table(self, L, D, H, color=gs.TEXT):
        F = self.F
        legs = VGroup()
        for la, lb in [(L - 6, D - 6), (L - 6, 6), (6, D - 6), (6, 6)]:      # far legs first, near corner last
            far = (la, lb) == (L - 6, D - 6)
            legs.add(Line(F(la, lb, H), F(la, lb, 0), stroke_color=color, stroke_width=3 if far else 5,
                          stroke_opacity=0.45 if far else 1))
        near_edges = VGroup(Line(F(L, 0, H), F(0, 0, H), stroke_color=color, stroke_width=6),
                            Line(F(0, 0, H), F(0, D, H), stroke_color=color, stroke_width=6))
        return VGroup(self.box_top(L, D, H, color), legs, near_edges)

    def shadow(self, L, D):
        F = self.F
        return Polygon(F(-4, -4), F(L + 6, -4), F(L + 6, D + 6), F(-4, D + 6), fill_color=BLACK, fill_opacity=0.35,
                       stroke_width=0)


# stick figure poses: (along-axis px, height px) per joint, relative to the figure's floor point
POSES = {
    "stand": {"head": (0, 76), "neck": (0, 64), "hip": (0, 34), "kneeL": (-6, 17), "kneeR": (6, 17),
              "footL": (-10, 0), "footR": (10, 0), "handL": (-17, 44), "handR": (17, 44)},
    "cover": {"head": (22, 24), "neck": (10, 30), "hip": (-20, 22), "kneeL": (2, 3), "kneeR": (4, 3),   # drop-cover-hold
              "footL": (-26, 3), "footR": (-24, 3), "handL": (24, 38), "handR": (58, 30)},
}
BONES = [("neck", "hip"), ("hip", "kneeL"), ("kneeL", "footL"), ("hip", "kneeR"), ("kneeR", "footR"),
         ("neck", "handL"), ("neck", "handR")]


def stick_figure(P, pose="stand", color=gs.GOLD, width=6, head_r=8):
    """P(da, dh) -> Manim point maps pose offsets into the scene (e.g. lambda da, dh: plane.F(a0 - da, b0, dh))."""
    J = {k: P(da, dh) for k, (da, dh) in POSES[pose].items()}
    bones = VGroup(*[Line(J[x], J[y], stroke_color=color, stroke_width=width) for x, y in BONES])
    for ln in bones:
        ln.cap_style = CapStyleType.ROUND
    return VGroup(Circle(radius=px(head_r), fill_color=color, fill_opacity=1, stroke_width=0).move_to(J["head"]), bones)


# =============================================================================== chapter & end cards

class ChapterCard(Clocked):
    """Chapter title card (also a YouTube chapter). Subclass and set NUMBER, TITLE, EN (english subtitle)."""
    NUMBER, TITLE, EN = 1, "Chapter title", "subtitle line"

    def construct(self):
        num = gs.text(f"{self.NUMBER:02d}", gs.EN_LABEL, 160, weight=BOLD, color=gs.GOLD_DEEP)
        k = gs.kicker(f"CHAPTER {self.NUMBER}", size=26)
        t = gs.title(self.TITLE, 84)
        en = gs.text(self.EN, gs.EN_TAG, 36, weight=BOLD, slant=ITALIC, color=gs.MUTED)
        rule = Line(LEFT * px(260), RIGHT * px(260), stroke_color=gs.GOLD, stroke_width=3)
        right = VGroup(k, t, rule, en).arrange(DOWN, aligned_edge=LEFT, buff=px(22))
        rule.align_to(right, LEFT)
        grp = VGroup(num, right).arrange(RIGHT, buff=px(60)).move_to(ORIGIN)
        self.fade_at(num, 0.0, 0.4, shift=LEFT * px(30))
        self.fade_at(right, 0.2, 0.5, shift=RIGHT * px(30))
        self.add(grp, gs.watermark())
        self.run()


class EndCard(Clocked):
    """Next-episode card that doubles as the YouTube end screen (keep the shot 12 s long).

    Reserved areas (1080p px) for YouTube Studio end-screen elements:
      video A  x 1220-1820, y 140-478 ("Watch next")   video B  x 1220-1820, y 540-878 (series playlist)
      subscribe circle centred (300, 640), d = 220 (on the seal). Bottom band stays free for subtitles.
    Subclass and set NEXT_LINES (1-2 title lines), SERIES, FRAME_LABELS.
    """
    NEXT_LINES = ("Next episode title",)
    SERIES = "Series: ... · coming soon"
    FRAME_LABELS = ("Watch next", "The series")

    def setup(self):
        super().setup()
        self.camera.background_color = gs.DARKER

    def construct(self):
        k = gs.kicker("NEXT EPISODE", zh=gs.CH.get("next_label") or None, size=28)
        lines = [gs.title(x, 60) for x in self.NEXT_LINES]
        sub = gs.text(self.SERIES, gs.ZH_SANS, 30, color=gs.MUTED)
        left = VGroup(k, *lines, sub).arrange(DOWN, aligned_edge=LEFT, buff=px(22)).move_to(at(560, 300))
        self.fade_at(k, 0.0, 0.4, shift=LEFT * px(30))
        self.fade_at(VGroup(*lines), 0.3, 0.5, shift=LEFT * px(30))
        self.fade_at(sub, 0.7, 0.5)
        seal = gs.seal(220).move_to(at(300, 640))
        btn = RoundedRectangle(width=px(260), height=px(66), corner_radius=px(10), fill_color=gs.GOLD,
                               fill_opacity=1, stroke_width=0)
        cta = VGroup(btn, gs.text(gs.CH.get("subscribe_label", "Subscribe"), gs.ZH_SANS, 28, weight=BOLD,
                                  color=gs.DARK).move_to(btn))
        site = gs.CH.get("website", "")
        web = gs.text(site, gs.EN_LABEL, 22, weight=MEDIUM, color=gs.MUTED) if site else VGroup()
        side = VGroup(cta, web).arrange(DOWN, aligned_edge=LEFT, buff=px(18)).next_to(seal, RIGHT, buff=px(44))
        self.fade_at(side, 1.0, 0.5)
        frames = VGroup()
        for (cx, cy), lab in zip([(1520, 309), (1520, 709)], self.FRAME_LABELS):
            box = RoundedRectangle(width=px(600), height=px(338), corner_radius=px(12), fill_color=gs.CARD,
                                   fill_opacity=1, stroke_color=gs.GOLD, stroke_width=3).move_to(at(cx, cy))
            tri = play_icon(56, gs.LINE).move_to(box)
            tag = gs.text(lab, gs.ZH_SANS, 24, weight=BOLD, color=gs.GOLD).next_to(box, UP, buff=px(10)).align_to(box, LEFT)
            frames.add(VGroup(box, tri, tag))
        self.fade_at(frames[0], 1.2, 0.5, shift=RIGHT * px(30))
        self.fade_at(frames[1], 1.5, 0.5, shift=RIGHT * px(30))
        self.add(seal, left, side, frames)
        self.run()
