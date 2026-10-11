"""Channel intro sting (~4 s): accent bar drops -> impact shake -> wave -> badge ring -> channel title -> tagline.

A neutral starting point - redesign it around your own logo. Timing lives in INTRO_T and is shared with the audio
(templates/intro_audio.py), so change times in one place only.
Render:  manim -ql intro.py Intro   (preview)   |   manim -qh --fps 30 intro.py Intro  (final)
gs_episode.py renders it automatically the first time an episode needs it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))   # <studio>/scripts
import numpy as np  # noqa: E402
from manim import *  # noqa: E402,F403

import gs_style as gs  # noqa: E402
from gs_style import px  # noqa: E402

INTRO_T = {
    "strata_in": 0.0,   # background layers fade in
    "fall": 0.30,       # the bar starts dropping
    "impact": 0.90,     # it lands                    (audio: impact + rumble)
    "wave_end": 1.45,   # wave fully drawn             (audio: shimmer)
    "ring": 1.40,       # badge ring draws in          (audio: theme chord)
    "title": 2.10,      # channel title
    "tagline": 2.40,
    "end": 4.00,
}

R = px(200)                    # badge radius
CENTER = UP * px(110)


class Intro(MovingCameraScene):
    def construct(self):
        gs.setup(self)
        T = INTRO_T
        layers = VGroup(*[Rectangle(width=2 * R, height=px(h), fill_color=c, fill_opacity=1, stroke_width=0)
                          for h, c in [(70, gs.CARD), (50, gs.LINE), (90, gs.CARD)]]).arrange(DOWN, buff=0)
        layers.move_to(CENTER + DOWN * px(50))
        clip = Circle(radius=R * 0.92).move_to(CENTER)
        strata = VGroup(*[Intersection(m, clip, fill_color=m.get_fill_color(), fill_opacity=1, stroke_width=0)
                          for m in layers])
        ground_y = layers[0].get_bottom()[1]
        bar = RoundedRectangle(width=px(34), height=px(150), corner_radius=px(8), fill_color=gs.GOLD,
                               fill_opacity=1, stroke_width=0).move_to([CENTER[0], ground_y + px(75), 0])

        self.play(FadeIn(strata), run_time=T["fall"] - T["strata_in"])
        bar.shift(UP * px(700))
        self.add(bar)
        self.play(bar.animate.shift(DOWN * px(700)), rate_func=rush_into, run_time=T["impact"] - T["fall"])

        # impact: camera shake + wave + ripples
        frame = self.camera.frame
        base = frame.get_center()

        def shake(m, a):
            amp = px(14) * np.exp(-6 * a)
            m.move_to(base + np.array([amp * np.sin(2 * np.pi * 7 * a), amp * np.sin(2 * np.pi * 9 * a + 1), 0]))

        x0, x1 = CENTER[0], CENTER[0] + R * 0.9
        xs = np.linspace(x0, x1, 60)
        wave = VMobject(stroke_color=gs.CYAN, stroke_width=6).set_points_smoothly(
            [[x, ground_y + px(40) * np.sin((x - x0) / px(18)) * np.exp(-(x - x0) / (R * 0.4)), 0] for x in xs])
        ripples = VGroup(*[Circle(radius=px(4), stroke_color=gs.CYAN, stroke_width=4).move_to([x0, ground_y, 0])
                           for _ in range(3)])
        anims = [Succession(Wait(0.12 * i), r.animate(rate_func=rate_functions.ease_out_cubic).scale(28 - 6 * i)
                            .set_stroke(opacity=0)) for i, r in enumerate(ripples)]
        self.add(ripples)
        self.play(UpdateFromAlphaFunc(frame, shake), Create(wave), *anims, run_time=T["wave_end"] - T["impact"],
                  rate_func=linear)
        frame.move_to(base)
        self.remove(ripples)

        outer = Circle(radius=R, stroke_color=gs.GOLD, stroke_width=6).move_to(CENTER)
        inner = Circle(radius=R * 0.92, stroke_color=gs.GOLD, stroke_width=3).move_to(CENTER)
        title = gs.title(gs.CH.get("intro_title") or gs.CH.get("name", ""), 76).next_to(outer, DOWN, buff=px(56))
        tag = gs.tagline(size=36).next_to(title, DOWN, buff=px(22))
        self.play(Create(outer), Create(inner), run_time=T["title"] - T["wave_end"], rate_func=smooth)
        self.play(FadeIn(title, shift=UP * px(20)), run_time=T["tagline"] - T["title"])
        self.play(FadeIn(tag, shift=UP * px(12)), run_time=0.5)
        self.wait(T["end"] - T["tagline"] - 0.5)
