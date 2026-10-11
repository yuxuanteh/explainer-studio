"""Thumbnails (1280x720) and social covers · {{EPISODE}}. Replace the texts and drawings per episode
(the drawings below are the original channel's seismogram example; keep the Layered structure).

Each thumbnail is rendered in four layers so it can be rebuilt in Canva:
  <Name>Full   everything                     manim -s -r 1280,720
  <Name>Bg     background only (no text)      manim -s -r 1280,720
  <Name>Text   text only, transparent         manim -s -t -r 1280,720
  <Name>El     graphic elements, transparent  manim -s -t -r 1280,720
  IgCover      Instagram 1080x1350            manim -s -r 1080,1350
Export the PNGs into publish/ with:  python scripts/gs_thumbs.py <EPISODE>
Coordinates are 1920x1080 px (scaled automatically).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))   # <studio>/scripts
from gs_shotkit import *  # noqa: E402,F403

PUB = str(here(__file__).EP_DIR / "publish")


def big(s, size, color=gs.TEXT, font=gs.ZH_SANS, weight=HEAVY):
    t = gs.text(s, font, size, weight=weight, color=color)
    # dark outline so the text survives YouTube's small sizes and any background
    return t.set_stroke(gs.DARKER, width=px(14) / px(1) * 0.9, background=True)


def seismo(x0, x1, yc, amp, p_at=0.32, s_at=0.58, width=6):
    xs = np.linspace(0, 1, 700)
    p = np.where(xs > p_at, 0.22 * np.sin(2 * np.pi * 60 * (xs - p_at)) * np.exp(-(xs - p_at) / 0.06), 0)
    s = np.where(xs > s_at, np.sin(2 * np.pi * 28 * (xs - s_at)) * (1 - np.exp(-(xs - s_at) / 0.01)) *
                 np.exp(-(xs - s_at) / 0.16), 0)
    pts = [at(x0 + (x1 - x0) * x, yc - amp * (pp + ss)) for x, pp, ss in zip(xs, p, s)]
    return VMobject(stroke_color=gs.TEXT, stroke_width=width).set_points_as_corners(pts), \
        (x0 + (x1 - x0) * p_at, x0 + (x1 - x0) * s_at)


def house(size, color=gs.TEXT, width=10):
    w = px(size)
    body = Rectangle(width=w, height=w * 0.8, stroke_color=color, stroke_width=width, fill_color=gs.CARD, fill_opacity=1)
    roof = Polygon(body.get_corner(UL) + LEFT * w * 0.08, body.get_corner(UR) + RIGHT * w * 0.08,
                   body.get_top() + UP * w * 0.45, stroke_color=color, stroke_width=width, fill_color=gs.CARD,
                   fill_opacity=1)
    door = Rectangle(width=w * 0.22, height=w * 0.38, stroke_color=color, stroke_width=width * 0.8).align_to(body, DOWN)
    win = Square(side_length=w * 0.2, stroke_color=gs.GOLD, stroke_width=width * 0.8).move_to(
        body.get_center() + w * np.array([0.25, 0.12, 0]))
    return VGroup(roof, body, door, win)


class Layered(Scene):
    LAYER = "full"

    def setup(self):
        self.camera.background_color = gs.DARKER if self.LAYER in ("full", "bg") else BLACK

    def put(self, bg=(), el=(), text=()):
        groups = {"bg": bg, "el": el, "text": text}
        show = {"full": ["bg", "el", "text"], "bg": ["bg", "el"], "text": ["text"], "el": ["el"]}[self.LAYER]
        for k in show:
            for m in groups[k]:
                self.add(m)


# ------------------------------------------------------------------ A: presenter + question

class ThumbA(Layered):
    def construct(self):
        photo = Group()                          # presenter photo: python gs_thumbs.py <EP> photo <cam source> <s>
        if Path(PUB + "/thumbnails/photo-presenter.png").exists():
            photo = ImageMobject(PUB + "/thumbnails/photo-presenter.png").set(height=config.frame_height)
            photo.to_edge(RIGHT, buff=0)
        glow = Circle(radius=px(520), fill_color="#3A2E14", fill_opacity=0.35, stroke_width=0).move_to(at(380, 560))
        trace, (xp, xs) = seismo(70, 900, 900, 120, width=7)
        trace.set_stroke(gs.CYAN)
        tags = VGroup(gs.text("P", gs.EN_LABEL, 46, weight=BOLD, color=gs.CYAN).move_to(at(xp, 790)),
                      gs.text("S", gs.EN_LABEL, 46, weight=BOLD, color=gs.GOLD).move_to(at(xs, 750)))
        l1 = big("Big hook", 190).move_to(at(470, 330))
        l2 = big("question?", 190, color=gs.GOLD).move_to(at(500, 580))
        chip_t = gs.text("P-wave vs S-wave", gs.EN_LABEL, 46, weight=BOLD, color=gs.DARK)
        chip = VGroup(RoundedRectangle(width=chip_t.width + px(44), height=chip_t.height + px(30), corner_radius=px(12),
                                       fill_color=gs.CYAN, fill_opacity=1, stroke_width=0), chip_t).move_to(at(330, 110))
        chip[1].move_to(chip[0])
        self.put(bg=[photo, glow], el=[trace, tags], text=[l1, l2, chip])


# ------------------------------------------------------------------ B: shaking house

class ThumbB(Layered):
    def construct(self):
        glow = Circle(radius=px(600), fill_color="#3A2E14", fill_opacity=0.45, stroke_width=0).move_to(at(560, 520))
        ground = Line(at(120, 760), at(1000, 760), stroke_color=gs.MUTED, stroke_width=10)
        h = house(400).move_to(at(560, 760) + UP * px(1) * 0)
        h.next_to(ground, UP, buff=0).shift(RIGHT * px(0))
        ghosts = VGroup(h.copy().set_stroke(gs.CYAN, opacity=0.5).set_fill(opacity=0).shift(UP * px(40)),
                        h.copy().set_stroke(gs.GOLD, opacity=0.6).set_fill(opacity=0).shift(LEFT * px(70)),
                        h.copy().set_stroke(gs.GOLD, opacity=0.6).set_fill(opacity=0).shift(RIGHT * px(70)))
        up = DoubleArrow(at(160, 470), at(160, 270), color=gs.CYAN, stroke_width=14, buff=0, tip_length=px(46))
        lr = DoubleArrow(at(330, 880), at(790, 880), color=gs.GOLD, stroke_width=14, buff=0, tip_length=px(46))
        nums = VGroup(gs.text("1", gs.EN_LABEL, 70, weight=BOLD, color=gs.CYAN).next_to(up, RIGHT, buff=px(16)),
                      gs.text("2", gs.EN_LABEL, 70, weight=BOLD, color=gs.GOLD).next_to(lr, RIGHT, buff=px(20)))
        l1 = big("Why does it", 150).move_to(at(1430, 380))
        l2 = big("twice?", 220, color=gs.GOLD).move_to(at(1430, 640))
        self.put(bg=[glow, ground], el=[ghosts, h, up, lr, nums], text=[l1, l2])


# ------------------------------------------------------------------ C: 1 second = 8 km

class ThumbC(Layered):
    def construct(self):
        glow = Circle(radius=px(700), fill_color="#3A2E14", fill_opacity=0.35, stroke_width=0).move_to(at(960, 760))
        trace, (xp, xs) = seismo(90, 1830, 800, 190, p_at=0.28, s_at=0.55, width=8)
        picks = VGroup(DashedLine(at(xp, 560), at(xp, 1000), color=gs.CYAN, stroke_width=8, dash_length=px(22)),
                       DashedLine(at(xs, 560), at(xs, 1000), color=gs.GOLD, stroke_width=8, dash_length=px(22)),
                       gs.text("P", gs.EN_LABEL, 70, weight=BOLD, color=gs.CYAN).move_to(at(xp - 50, 600)),
                       gs.text("S", gs.EN_LABEL, 70, weight=BOLD, color=gs.GOLD).move_to(at(xs + 50, 600)))
        arrow = DoubleArrow(at(xp, 1010), at(xs, 1010), color=gs.TEXT, stroke_width=12, buff=0, tip_length=px(40))
        l1 = big("1 second", 190).move_to(at(560, 250))
        l2 = big("= 8 km", 190, color=gs.GOLD).next_to(l1, RIGHT, buff=px(50))
        VGroup(l1, l2).move_to(at(960, 230))
        sub = big("the key number, in one line", 66, color=gs.MUTED, weight=BOLD).move_to(at(960, 420))
        self.put(bg=[glow], el=[trace, picks, arrow], text=[l1, l2, sub])


# layer variants
for _n in ("ThumbA", "ThumbB", "ThumbC"):
    _base = globals()[_n]
    for _layer, _suffix in [("full", "Full"), ("bg", "Bg"), ("text", "Text"), ("el", "El")]:
        globals()[_n + _suffix] = type(_n + _suffix, (_base,), {"LAYER": _layer})


# ------------------------------------------------------------------ Instagram cover 1080x1350

class IgCover(Scene):
    """Render with -r 1080,1350. Positions are relative to the frame edges."""

    def construct(self):
        self.camera.background_color = gs.DARKER
        # with a portrait -r, Manim keeps frame_width (14.2) and the visible height grows; config.frame_height
        # still reads 8, so derive the real height from the pixel aspect
        fw = config.frame_width
        fh = fw * config.pixel_height / config.pixel_width
        photo = Group()
        if Path(PUB + "/social/photo-presenter-portrait.png").exists():
            photo = ImageMobject(PUB + "/social/photo-presenter-portrait.png").set(width=fw)
            photo.move_to(UP * (fh / 2 - photo.height / 2))   # to_edge() would use the stale frame_height
        s = fw / 1080                             # 1 px of the 1080-wide canvas
        def T(t, size, color=gs.TEXT, weight=HEAVY, font=gs.ZH_SANS):
            m = Text(t, font=font, weight=weight, color=color, font_size=48)
            return m.scale(size * s / Text("国H", font=font, weight=weight, font_size=48).height).set_stroke(
                gs.DARKER, width=10, background=True)
        l1 = T("Hook line one", 120).move_to(UP * (fh / 2 - 930 * s))
        l2 = T("line two?", 92, color=gs.GOLD).next_to(l1, DOWN, buff=30 * s)
        chip_t = Text("P-wave vs S-wave", font=gs.EN_LABEL, weight=BOLD, color=gs.DARK, font_size=48)
        chip_t.scale(44 * s / chip_t.height)
        chip = VGroup(RoundedRectangle(width=chip_t.width + 40 * s, height=chip_t.height + 28 * s, corner_radius=10 * s,
                                       fill_color=gs.CYAN, fill_opacity=1, stroke_width=0), chip_t)
        chip[1].move_to(chip[0])
        chip.next_to(l2, DOWN, buff=44 * s)
        brand = Text(gs.CH.get("name", ""), font=gs.ZH_SERIF, weight=HEAVY, color=gs.MUTED, font_size=48)
        brand.scale(34 * s / brand.height)
        brand.move_to(DOWN * (fh / 2 - 60 * s - brand.height / 2))
        self.add(photo, l1, l2, chip, brand)
