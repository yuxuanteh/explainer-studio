"""Through-composed episode score (instead of repeating one mood loop).

edl.py declares sections by the shot where they start and a style:
    SCORE = [("S01", "mystery"), ("C1", "curious"), ("C2", "pulse"), ("S09", "discovery"), ("S12", "reflective"),
             ("C3", "tension"), ("S17", "investigate"), ("S21", "epic"), ("S22", "resolve"), ("END0", None)]
A section runs until the next one starts; None = no score (the end card keeps its outro sting + calm tail).
Every style is a function writing notes into one gs_sf.Score for [t0, t0 + dur): different instruments, keys and
tempi per section, a string swell into each new section and a soft cymbal on chapter cards. Rendered once
(FluidSynth + GeneralUser GS, the timbre the director chose), with reverb, then mastered like the loop library.
"""
import numpy as np

import gs_audio as A
from gs_sf import Score

NOTES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def tr(note, semis):
    """Transpose 'A4' by semitones."""
    name, octv = note[:-1], int(note[-1])
    i = NOTES.index({"Db": "C#", "D#": "Eb", "Gb": "F#", "G#": "Ab", "A#": "Bb"}.get(name, name)) + semis
    return f"{NOTES[i % 12]}{octv + i // 12}"


def triad(root, minor=False, octave=3):
    r = f"{root}{octave}"
    return [r, tr(r, 3 if minor else 4), tr(r, 7)]


def bars(t0, dur, bpm):
    beat = 60 / bpm
    n = int(np.ceil(dur / (4 * beat)))
    return [(t0 + i * 4 * beat, i) for i in range(n)], beat


def clip(s, inst, note, at, d, vel, t_end):
    if at < t_end - 0.05:
        s.note(inst, note, at, min(d, t_end - at), vel)


# ------------------------------------------------------------------ styles  (s, t0, dur)

def mystery(s, t0, dur):
    """Hook: dark, sparse. Low cello pedal in D minor, harp harmonics, a soft timpani pulse."""
    t1 = t0 + dur
    prog = [("D", True), ("Bb", False), ("G", True), ("A", False)]
    for at, i in bars(t0, dur, 72)[0]:
        root, mi = prog[i % 4]
        clip(s, "cello", f"{root}2", at, 3.2, 72, t1)
        s_chord = triad(root, mi, 3)
        for n in s_chord:
            clip(s, "slowstrings", n, at, 3.3, 48, t1)
        clip(s, "timpani", "D2", at, 1.0, 70, t1)
        for k, n in enumerate(triad(root, mi, 5)):
            clip(s, "harp", n, at + 0.9 + k * 0.35, 1.5, 44, t1)


def curious(s, t0, dur):
    """Basics: light pizzicato + harp arpeggios in F major, warm string bed."""
    t1 = t0 + dur
    prog = [("F", False), ("C", False), ("D", True), ("Bb", False)]
    pat = [0, 1, 2, 1, 3, 2, 1, 2]
    bl, beat = bars(t0, dur, 96)
    for at, i in bl:
        root, mi = prog[i % 4]
        tt = triad(root, mi, 4) + [f"{root}5"]
        for k, p in enumerate(pat):
            clip(s, "pizz", tt[p], at + k * beat / 2, beat * 0.45, 86 if k % 2 == 0 else 70, t1)
        for n in triad(root, mi, 3):
            clip(s, "slowstrings", n, at, 4 * beat, 54, t1)
        clip(s, "contrabass", f"{root}2", at, beat * 1.8, 74, t1)
        if i % 2 == 1:
            clip(s, "celesta", tr(tt[2], 12), at + 3.5 * beat, beat, 62, t1)


def pulse(s, t0, dur):
    """How it's found: marimba ostinato + pizz bass in C major, a little faster - things are moving."""
    t1 = t0 + dur
    prog = [("C", False), ("A", True), ("F", False), ("G", False)]
    bl, beat = bars(t0, dur, 104)
    for at, i in bl:
        root, mi = prog[i % 4]
        tt = triad(root, mi, 4)
        for k in range(8):
            clip(s, "marimba", tt[[0, 2, 1, 2, 0, 2, 1, 2][k]], at + k * beat / 2, beat * 0.4, 78 if k % 4 == 0 else 62, t1)
        clip(s, "pizz", f"{root}2", at, beat, 82, t1)
        clip(s, "pizz", f"{root}3", at + 2 * beat, beat, 70, t1)
        for n in triad(root, mi, 3):
            clip(s, "slowstrings", n, at, 4 * beat, 46, t1)


def discovery(s, t0, dur):
    """Circles on the map: shimmering celesta / vibes arpeggios rising, A minor -> C major."""
    t1 = t0 + dur
    prog = [("A", True), ("F", False), ("C", False), ("G", False)]
    bl, beat = bars(t0, dur, 92)
    for at, i in bl:
        root, mi = prog[i % 4]
        tt = triad(root, mi, 4) + triad(root, mi, 5)
        for k, n in enumerate(tt):
            clip(s, "celesta" if k % 2 == 0 else "vibes", n, at + k * beat / 2, beat * 1.2, 60, t1)
        for n in triad(root, mi, 3):
            clip(s, "slowstrings", n, at, 4 * beat, 52, t1)
        clip(s, "contrabass", f"{root}2", at, 4 * beat, 60, t1)
        clip(s, "harp", f"{root}5", at + 3 * beat, beat * 2, 56, t1)


def reflective(s, t0, dur):
    """Depth classes: piano over slow strings, D minor -> F."""
    t1 = t0 + dur
    prog = [("D", True), ("Bb", False), ("F", False), ("C", False)]
    bl, beat = bars(t0, dur, 76)
    for at, i in bl:
        root, mi = prog[i % 4]
        tt = triad(root, mi, 4)
        for n in triad(root, mi, 3):
            clip(s, "slowstrings", n, at, 4 * beat, 58, t1)
        clip(s, "contrabass", f"{root}2", at, 4 * beat, 52, t1)
        clip(s, "piano", tt[0], at, 2 * beat, 66, t1)
        clip(s, "piano", tt[2], at + beat, beat, 56, t1)
        clip(s, "piano", tr(tt[1], 12), at + 2 * beat, 2 * beat, 62, t1)
        clip(s, "piano", tt[2], at + 3 * beat, beat, 52, t1)


def tension(s, t0, dur):
    """Real quakes: low string ostinato + timpani heartbeat in D minor; grows a little each 4 bars."""
    t1 = t0 + dur
    prog = [("D", True), ("D", True), ("Bb", False), ("A", False)]
    bl, beat = bars(t0, dur, 88)
    for at, i in bl:
        root, mi = prog[i % 4]
        grow = min(i // 4, 3) * 6
        for k in range(16):
            clip(s, "strings", f"{root}3" if k % 8 != 6 else f"{root}4", at + k * beat / 4, beat / 4 * 0.6,
                 (90 if k % 4 == 0 else 64) + grow, t1)
        clip(s, "cello", f"{root}2", at, 4 * beat, 66 + grow, t1)
        clip(s, "timpani", "D2", at, beat, 92, t1)
        clip(s, "timpani", "D2", at + 0.75 * beat, beat, 70, t1)
        if i % 4 == 3:
            clip(s, "choir", tr(f"{root}4", 0), at, 4 * beat, 50, t1)


def investigate(s, t0, dur):
    """The 10 km question: tremolo strings + ticking woodblock (a clock), E minor, unresolved."""
    t1 = t0 + dur
    prog = [("E", True), ("C", False), ("A", True), ("B", False)]
    bl, beat = bars(t0, dur, 84)
    for at, i in bl:
        root, mi = prog[i % 4]
        for n in triad(root, mi, 3):
            clip(s, "tremolo", n, at, 4 * beat, 52, t1)
        clip(s, "contrabass", f"{root}2", at, 4 * beat, 58, t1)
        for k in range(4):
            if at + k * beat < t1:
                s.hit("woodblock", at + k * beat, 34 if k % 2 else 44)
        clip(s, "glock", tr(f"{root}5", 7), at + 2.5 * beat, beat, 46, t1)


def epic(s, t0, dur):
    """2004 rupture: string 16ths, horns, choir, timpani - crescendo across the section."""
    t1 = t0 + dur
    prog = [("D", True), ("Bb", False), ("F", False), ("C", False)]
    bl, beat = bars(t0, dur, 96)
    for at, i in bl:
        root, mi = prog[i % 4]
        k_ = (at - t0) / max(dur, 1)
        v = int(70 + 35 * k_)
        tt = triad(root, mi, 3) + triad(root, mi, 4)
        for k in range(16):
            clip(s, "strings", tt[[0, 1, 2, 3, 2, 1, 4, 2][k % 8]], at + k * beat / 4, beat / 4 * 0.7,
                 v + (10 if k % 4 == 0 else 0), t1)
        for n in triad(root, mi, 3):
            clip(s, "horn", n, at, 4 * beat, v, t1)
        for n in triad(root, mi, 4):
            clip(s, "choir", n, at, 4 * beat, v - 15, t1)
        clip(s, "contrabass", f"{root}2", at, 4 * beat, v + 10, t1)
        for k in range(4):
            clip(s, "timpani", f"{root}2", at + k * beat, beat, v + (20 if k % 2 == 0 else 0), t1)
        if i % 4 == 0 and at < t1:
            s.hit("crash", at, 70)


def resolve(s, t0, dur):
    """Closing line: gentle piano + strings in F major, settling."""
    t1 = t0 + dur
    prog = [("F", False), ("Bb", False), ("D", True), ("C", False)]
    bl, beat = bars(t0, dur, 70)
    for at, i in bl:
        root, mi = prog[i % 4]
        tt = triad(root, mi, 4)
        for n in triad(root, mi, 3):
            clip(s, "slowstrings", n, at, 4 * beat, 56, t1)
        for k, n in enumerate(tt + [tr(tt[0], 12)]):
            clip(s, "piano", n, at + k * beat, beat * 1.5, 60 - k * 4, t1)
        clip(s, "harp", tr(tt[2], 12), at + 3.5 * beat, beat, 48, t1)


STYLES = {f.__name__: f for f in (mystery, curious, pulse, discovery, reflective, tension, investigate, epic, resolve)}


def riser(seconds=2.4, seed=3):
    """Noise + sine sweep that builds into a section change (peak at the end)."""
    import pedalboard as pb
    n = int(seconds * A.SR)
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, n).astype(np.float32)
    out = np.zeros(n, np.float32)
    chunks = 48
    for k in range(chunks):                       # band-limited noise climbing in pitch
        a, b = k * n // chunks, (k + 1) * n // chunks
        f = 200 * (12000 / 200) ** (k / chunks)
        seg = pb.Pedalboard([pb.HighpassFilter(cutoff_frequency_hz=f * 0.7),
                             pb.LowpassFilter(cutoff_frequency_hz=min(f * 2.5, 18000))])(noise[a:b][None], A.SR)[0]
        out[a:b] = seg
    tt = np.arange(n) / A.SR
    sweep = np.sin(2 * np.pi * np.cumsum(150 * (8 ** (tt / seconds))) / A.SR) * 0.35
    env = (tt / seconds) ** 2.6
    y = (out * 0.6 + sweep) * env
    y = pb.Pedalboard([pb.Reverb(room_size=0.6, wet_level=0.25)])(np.vstack([y, y]).astype(np.float32), A.SR)
    return y / (np.abs(y).max() + 1e-9)


# final chord per style for endings that ring out (root, minor, big)
FINAL = {"mystery": ("D", True, False), "curious": ("F", False, False), "pulse": ("C", False, False),
         "discovery": ("C", False, False), "reflective": ("F", False, False), "tension": ("D", True, True),
         "investigate": ("E", True, False), "epic": ("D", True, True), "resolve": ("F", False, False)}


def _final_chord(s, style, at, length):
    """A last chord that is held and allowed to decay naturally (no fade-out cut)."""
    root, minor, big = FINAL[style]
    notes = triad(root, minor, 3) + [f"{root}4"]
    if big:                                       # climax: full orchestra hit
        for n in notes:
            s.note("strings", n, at, length, 112).note("horn", n, at, length, 100)
        for n in triad(root, minor, 4):
            s.note("choir", n, at, length, 90)
        s.note("timpani", f"{root}2", at, 1.2, 120).note("contrabass", f"{root}2", at, length, 112)
        s.hit("crash", at, 85)
    else:                                         # gentle: piano + strings
        for n in notes:
            s.note("slowstrings", n, at, length, 70)
        for n in triad(root, minor, 4):
            s.note("piano", n, at, length, 64)
        s.note("contrabass", f"{root}2", at, length, 60)


def _section(style, dur, button=False, ring_at=None, ring_len=3.0):
    """Render one section on its own (so transitions can treat it separately). Returns stereo incl. reverb tail.
    ring_at: the style stops there and a final chord rings out instead (endings 'drop' / 'ringout')."""
    s = Score(humanize=0.006, seed=hash(style) % 97)
    STYLES[style](s, 0.0, ring_at if ring_at is not None else dur)
    if ring_at is not None:
        _final_chord(s, style, ring_at, ring_len)
    if button:                                    # clean ending chord ("button") just before the change
        at = max(dur - 0.45, 0)
        for n in ("D3", "A3", "D4", "F4"):
            s.note("strings", n, at, 0.35, 110)
        s.note("timpani", "D2", at, 0.6, 115)
        s.note("contrabass", "D2", at, 0.5, 110)
    dry = s.render()
    tail = int((ring_len + 2.0 if ring_at is not None else 2.5) * A.SR)
    dry = np.pad(dry, ((0, 0), (0, max(int(dur * A.SR) + tail - dry.shape[1], 0))))[:, :int(dur * A.SR) + tail]
    return A.fx(dry, reverb=0.28, room=0.75)


def _ramp(n, a, b):
    return np.linspace(a, b, max(n, 1))[None]


def render(sections, tl, n_samples):
    """sections: [(first shot id, style or None[, transition into this section])] -> stereo bed (2, n_samples).
    Transitions (vary them, don't overuse risers):
      fade    1.2 s crossfade (default)          button  outgoing ends on a chord hit, next starts on the cut
      filter  outgoing low-pass sweep + fade      riser   noise/sine build peaking on the cut + cymbal
      drop    big final chord ~2 s before the cut that decays into silence (lets an important line land)
      ringout final chord just before the cut, decays naturally over the next shot (end of the score)"""
    import pedalboard as pb
    start = {s["id"]: s["start"] for s in tl}
    kinds = {s["id"]: s["kind"] for s in tl}
    total = tl[-1]["end"]
    secs = [(x[0], x[1], x[2] if len(x) > 2 else "fade") for x in sections]
    spans = []
    for k, (sid, style, tr_in) in enumerate(secs):
        t0 = start[sid]
        t1 = start[secs[k + 1][0]] if k + 1 < len(secs) else total
        tr_out = secs[k + 1][2] if k + 1 < len(secs) else "fade"
        spans.append((sid, style, t0, t1, tr_in, tr_out))
    bed = np.zeros((2, n_samples), np.float32)
    sr = A.SR
    for sid, style, t0, t1, tr_in, tr_out in spans:
        if not style:
            continue
        span = t1 - t0
        if tr_out == "drop":                      # big last chord ~2 s before the cut, decays into silence
            x = _section(style, span, ring_at=max(span - 2.2, 0.5), ring_len=1.4)
        elif tr_out == "ringout":                 # last chord just before the cut, rings on over the next shot
            x = _section(style, span, ring_at=max(span - 0.5, 0.5), ring_len=3.5)
        else:
            x = _section(style, span + (1.2 if tr_out == "fade" else 0), button=(tr_out == "button"))
        L = x.shape[1]
        cut = int((t1 - t0) * sr)                 # where the next section starts (relative)
        # ---- entry
        if tr_in in ("fade", "filter"):
            k = int(1.0 * sr)
            x[:, :k] *= _ramp(k, 0, 1)
        elif tr_in == "riser":
            x[:, :int(0.05 * sr)] *= _ramp(int(0.05 * sr), 0, 1)
        # ---- exit
        if tr_out == "fade":
            k = int(1.2 * sr)
            x[:, cut:cut + k] *= _ramp(min(k, L - cut), 1, 0)[:, :max(min(k, L - cut), 0)]
            x[:, cut + k:] = 0
        elif tr_out == "filter":
            k = int(2.0 * sr)
            a = max(cut - k, 0)
            low = pb.Pedalboard([pb.LowpassFilter(cutoff_frequency_hz=500)])(x[:, a:cut].copy(), sr)
            m = _ramp(cut - a, 0, 1)
            x[:, a:cut] = x[:, a:cut] * (1 - m) + low * m * _ramp(cut - a, 1, 0.15)
            x[:, cut:] = 0
        elif tr_out == "button":
            x[:, cut:cut + int(0.8 * sr)] *= _ramp(min(int(0.8 * sr), L - cut), 1, 0)[:, :max(min(int(0.8 * sr), L - cut), 0)]
            x[:, cut + int(0.8 * sr):] = 0
        elif tr_out == "riser":
            k = int(2.4 * sr)
            a = max(cut - k, 0)
            x[:, a:cut] *= _ramp(cut - a, 1, 0.25)
            x[:, cut:] = 0
        elif tr_out == "drop":                    # the chord's own decay; just make sure nothing leaks past the cut
            k = int(0.3 * sr)
            x[:, max(cut - k, 0):cut] *= _ramp(min(k, cut), 1, 0)
            x[:, cut:] = 0
        # "ringout": keep everything (the final chord decays naturally after the cut)
        i0 = int(t0 * sr)
        j = min(i0 + L, n_samples)
        bed[:, i0:j] += x[:, :j - i0]
    bed = A.master(bed, lufs_like_db=-18)
    # risers and cymbals on top (after mastering, so they keep their shape)
    extra = np.zeros_like(bed)
    for sid, style, t0, t1, tr_in, tr_out in spans:
        i = int(t0 * sr)
        if tr_in == "riser" and style:
            r = riser()
            a = max(i - r.shape[1], 0)
            extra[:, a:i] += r[:, r.shape[1] - (i - a):] * 10 ** (-12 / 20)
            hit = Score().hit("crash", 0.0, 90).note("timpani", "D2", 0.0, 1.0, 110).render()
            k = min(hit.shape[1], n_samples - i)
            extra[:, i:i + k] += hit[:, :k] * 10 ** (-8 / 20)
        if kinds.get(sid) == "chapter" and tr_in != "riser" and t0 > 0:
            h = Score().hit("splash", 0.0, 45).render()
            k = min(h.shape[1], n_samples - i)
            extra[:, i:i + k] += h[:, :k] * 10 ** (-14 / 20)
    return bed + extra
