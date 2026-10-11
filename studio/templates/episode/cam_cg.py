"""CG overlays for full-screen camera shots · {{EPISODE}} (transparent; class Cam<shot id>).

Before writing CG: grab a frame (ffmpeg -ss T -i raw/cam-XX.mp4 -frames:v 1 frame.png) and note
  - where the presenter is (CG must never cross the face or body),
  - clean areas (walls) for labels,
  - real surfaces for CG that "stands" on them: measure perspective from a real object there
    (a box seen corner-on: shallow V, thin top face, verticals stay vertical) -> DeskPlane(near, A, B).
The first appearance of the presenter shows gs.name_tag() for 3-5 s.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))   # <studio>/scripts
from gs_shotkit import *  # noqa: E402,F403

CamClocked.E = here(__file__)

# DESK = DeskPlane(near=(x, y), A=(-0.72, -0.10), B=(0.62, -0.085))   # measure per framing

# class CamS05(CamClocked):
#     def construct(self):
#         tag = gs.name_tag().move_to(at(300, 860))
#         self.show(tag, 0.15, 0.4, t_out=4.0, shift=LEFT * px(40))
#         self.add(tag, gs.watermark())
#         self.run()
