"""Full-screen shots · {{EPISODE}}. One class per shot id in edl.SHOTS (anim / chapter / card).

Each scene draws its state as a function of self.t() (seconds into the shot) and uses self.beats
(word timestamps from edl.py) so things happen exactly when the word is said.
    python scripts/gs_episode.py {{EPISODE}} render preview [S03 S04]

Rules: keep labels above y = 880 (subtitles); source note top-right for any fact/number;
episode palette may differ from the channel palette (only intro / end card / logo / name tag are fixed).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))   # <studio>/scripts
from gs_shotkit import *  # noqa: E402,F403

Clocked.E = here(__file__)

# Episode palette (pick per topic; defaults to the channel colours)
C1_ = gs.CYAN
C2_ = gs.GOLD


class S01(Clocked):
    """Hook. Replace with the real animation."""

    def construct(self):
        q = gs.title("Hook", 90).move_to(at(960, 420))
        self.fade_at(q, 0.2, 0.5, shift=UP * px(30))
        self.add(q, gs.kicker("WHY?", size=24).to_corner(UL, buff=px(60)), gs.watermark())
        self.run()


class C1(ChapterCard):
    NUMBER, TITLE, EN = 1, "The basics", "picture it first"


class END(EndCard):
    NEXT_LINES = ("Next episode, line one", "line two?")
    SERIES = "Series: XXX · coming soon"
    FRAME_LABELS = ("Watch next", "XXX series")
