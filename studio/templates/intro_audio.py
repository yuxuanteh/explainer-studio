"""Intro sting audio, locked to INTRO_T in intro.py. Writes brand/music/intro-sting.wav.

Real instruments from GeneralUser GS (timpani + tubular bell impact, harp/celesta motif, string swell, strong low
end); the falling whoosh and the ground rumble are synthesised. Change the notes to give your channel its own sting.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))   # <studio>/scripts
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import gs_audio as A  # noqa: E402
import gs_env  # noqa: E402
from gs_sf import Score  # noqa: E402
from intro import INTRO_T as T  # noqa: E402

LENGTH = T["end"] + 0.6


def build():
    n = int(LENGTH * A.SR)

    # ---- sampled orchestra ----
    s = Score(humanize=0.003)
    s.chord("slowstrings", ["D2", "A2"], 0.0, T["impact"] + 0.3, 70)          # low bed under the fade-in
    s.swell("slowstrings", 0.0, T["impact"], 20, 90)
    s.note("timpani", "D2", T["impact"], 2.5, 127)                            # the strike
    s.hit("bassdrum", T["impact"], 115)
    s.note("tubular", "D5", T["impact"], 3.0, 112)                            # metallic 'golden' ring
    s.note("glock", "A6", T["impact"] + 0.02, 1.5, 70)
    s.hit("crash", T["impact"] + 0.01, 55)
    # theme on ring / title / tagline beats
    motif = [("A4", T["ring"] + 0.05), ("D5", T["ring"] + 0.25), ("F5", T["ring"] + 0.45),
             ("E5", T["title"]), ("D5", T["tagline"])]
    for note, at in motif:
        s.note("harp", note, at, 2.5, 100).note("celesta", note, at, 1.2, 62)
    s.chord("slowstrings", ["D3", "A3", "E4", "F4"], T["ring"], LENGTH - T["ring"], 100)
    s.swell("slowstrings", T["ring"], 0.8, 35, 115)
    s.note("contrabass", "D2", T["ring"], LENGTH - T["ring"], 85)
    s.chord("horn", ["D3", "A3"], T["title"], LENGTH - T["title"], 62)
    orch = s.render()
    orch = np.pad(orch, ((0, 0), (0, max(n - orch.shape[1], 0))))[:, :n]

    # ---- synthesised air / ground ----
    sfx = A.Track(LENGTH)
    sfx.place(A.whoosh(T["impact"] - T["fall"] + 0.02, f0=250, f1=6000, rise=0.95), T["fall"], db=-12)
    sfx.place(A.rumble(1.6), T["impact"], db=-5)
    synth = A.stereo(sfx.y[:n])

    orch = A.fx(orch, reverb=0.33, room=0.8)
    synth = A.fx(synth, reverb=0.15, room=0.5, comp=False)
    m = min(orch.shape[1], synth.shape[1])
    mix = orch[:, :m] / (np.abs(orch).max() + 1e-9) + 0.55 * synth[:, :m] / (np.abs(synth).max() + 1e-9)
    mix = A.fade(A.trim(mix, LENGTH), fout=0.7)
    return A.master(mix, lufs_like_db=-17)


if __name__ == "__main__":
    out = gs_env.BRAND / "music" / "intro-sting.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    A.write(out, build())
    print(out)
