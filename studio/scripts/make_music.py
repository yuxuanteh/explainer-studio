"""Build the channel music library (brand/music/) and SFX set (brand/sfx/).

Instruments: GeneralUser GS via FluidSynth (gs_sf.py); noise-type SFX are synthesised.
(The original channel also tried the VSCO 2 CE samples via gs_sampler.py and found the strings too bright / thin.)
Loops are seamless: rendered with a reverb tail that is folded back onto the start.
Run from <studio>/scripts with the studio venv:  python make_music.py
"""
import numpy as np

import gs_audio as A
import gs_env
from gs_sf import Score

MUSIC = gs_env.BRAND / "music"
SFX = gs_env.BRAND / "sfx"

CHORDS = {
    "F": ["F", "A", "C"], "C": ["C", "E", "G"], "Dm": ["D", "F", "A"], "Bb": ["Bb", "D", "F"],
    "A": ["A", "C#", "E"], "Gm": ["G", "Bb", "D"], "Am": ["A", "C", "E"],
}


def tones(chord, octave):
    """Chord tones as note names ascending from `octave`."""
    out, prev = [], -1
    for n in CHORDS[chord]:
        o = octave
        while A.hz(f"{n}{o}") <= prev:
            o += 1
        out.append(f"{n}{o}")
        prev = A.hz(f"{n}{o}")
    return out


def up(note, octaves=1):
    return note[:-1] + str(int(note[-1]) + octaves)


def loop_render(build, bars, bpm, reverb=0.28, room=0.75, tail=3.5):
    beat = 60 / bpm
    length = bars * 4 * beat
    s = Score()
    build(s, beat)
    dry = s.render()
    need = int((length + tail) * A.SR)
    dry = np.pad(dry, ((0, 0), (0, max(need - dry.shape[1], 0))))[:, :need]
    wet = A.fx(dry, reverb=reverb, room=room)
    n, t = int(length * A.SR), int(tail * A.SR)
    looped = wet[:, :n].copy()
    looped[:, :t] += wet[:, n:n + t]
    return A.master(looped, lufs_like_db=-18), length


# ------------------------------------------------------------------ moods

def curious(s, beat):
    """Light, inquisitive: pizzicato + harp arpeggios over I-V-vi-IV in F, soft string bed."""
    prog = ["F", "C", "Dm", "Bb"] * 2
    pattern = [0, 1, 2, 1, 3, 2, 1, 2]
    for b, ch in enumerate(prog):
        t0 = b * 4 * beat
        tt = tones(ch, 4) + [up(tones(ch, 4)[0])]
        for i, p in enumerate(pattern):
            s.note("pizz", tt[p], t0 + i * beat / 2, beat * 0.45, 92 if i % 2 == 0 else 74)
        for i in (0, 3, 5):
            s.note("harp", up(tt[pattern[i]]), t0 + i * beat / 2, beat * 2, 62)
        s.chord("slowstrings", tones(ch, 3), t0, 4 * beat, 58)
        root = CHORDS[ch][0] + "2"
        s.note("contrabass", root, t0, beat * 1.8, 80).note("contrabass", root, t0 + 2 * beat, beat * 1.5, 70)
        for i in range(8):
            s.hit("maracas", t0 + i * beat / 2, 40 if i % 2 == 0 else 55)
        if b % 2 == 1:
            s.note("celesta", up(tt[2]), t0 + 3.5 * beat, beat, 70)


def tense(s, beat):
    """Suspense: low string ostinato, timpani heartbeat, dark sustained strings."""
    prog = ["Dm", "Dm", "Bb", "A"] * 2
    for b, ch in enumerate(prog):
        t0 = b * 4 * beat
        root = CHORDS[ch][0]
        for i in range(16):
            n = f"{root}3" if i % 8 != 6 else f"{root}4"
            s.note("strings", n, t0 + i * beat / 4, beat / 4 * 0.6, 100 if i % 4 == 0 else 72)
        s.note("cello", f"{root}2", t0, 4 * beat, 70)
        s.chord("slowstrings", tones(ch, 3), t0, 4 * beat, 52)
        s.note("timpani", "D2", t0, beat, 105).note("timpani", "D2", t0 + 0.75 * beat, beat, 80)
        for i in range(4):
            s.hit("triangle_mute", t0 + i * beat + beat / 2, 35)
        if b % 4 == 3:
            s.hit("splash", t0 + 3.5 * beat, 45)


def calm(s, beat):
    """Reflective: piano over slow strings, a little harp."""
    prog = ["Dm", "Bb", "F", "C"] * 2
    for b, ch in enumerate(prog):
        t0 = b * 4 * beat
        tt = tones(ch, 4)
        s.chord("slowstrings", tones(ch, 3) + [tt[1]], t0, 4 * beat, 62)
        s.note("contrabass", CHORDS[ch][0] + "2", t0, 4 * beat, 55)
        s.note("piano", tt[0], t0, 2 * beat, 70).note("piano", tt[2], t0 + beat, beat, 58)
        s.note("piano", up(tt[1]), t0 + 2 * beat, 2 * beat, 66).note("piano", tt[2], t0 + 3 * beat, beat, 55)
        if b % 2 == 1:
            for i, n in enumerate(tt + [up(tt[0])]):
                s.note("harp", up(n), t0 + 3 * beat + i * 0.09, 2.0, 50)


def epic(s, beat):
    """Grand: string 16ths, horns, timpani, choir, contrabass."""
    prog = ["Dm", "Bb", "F", "C"] * 2
    for b, ch in enumerate(prog):
        t0 = b * 4 * beat
        tt = tones(ch, 3) + tones(ch, 4)
        for i in range(16):
            s.note("strings", tt[[0, 1, 2, 3, 2, 1, 4, 2][i % 8]], t0 + i * beat / 4, beat / 4 * 0.7,
                   105 if i % 4 == 0 else 80)
        s.chord("horn", tones(ch, 3), t0, 4 * beat, 88)
        s.chord("choir", tones(ch, 4), t0, 4 * beat, 70)
        s.note("contrabass", CHORDS[ch][0] + "2", t0, 4 * beat, 95)
        for i in range(4):
            s.note("timpani", CHORDS[ch][0] + "2", t0 + i * beat, beat, 110 if i % 2 == 0 else 85)
        if b % 4 == 0:
            s.hit("crash", t0, 80)


def outro_sting():
    """End-card / next-episode sting: theme motif resolving to F major."""
    L = 6.0
    s = Score(humanize=0.004)
    for note, at in [("A4", 0.0), ("D5", 0.2), ("F5", 0.4), ("E5", 0.75), ("A5", 1.1)]:
        s.note("harp", note, at, 3.0, 96).note("celesta", note, at, 1.5, 60)
    s.note("glock", "A6", 1.1, 2.0, 70)
    s.chord("slowstrings", ["F3", "C4", "A4", "E5"], 0.5, L - 1.0, 85)
    s.swell("slowstrings", 0.5, 1.2, 40, 115)
    s.note("contrabass", "F2", 1.1, 3.5, 85).note("horn", "C4", 1.1, 3.5, 60).note("horn", "F3", 1.1, 3.5, 60)
    x = s.render()
    x = np.pad(x, ((0, 0), (0, max(int(L * A.SR) - x.shape[1], 0))))
    st = A.fx(x, reverb=0.32, room=0.85)
    return A.master(A.fade(A.trim(st, L), fout=1.5), lufs_like_db=-18)


# ------------------------------------------------------------------ sfx

def sampled(inst_notes, length):
    s = Score(humanize=0)
    for inst, note, at, dur, vel in inst_notes:
        if note is None:
            s.hit(inst, at, vel)
        else:
            s.note(inst, note, at, dur, vel)
    x = s.render()
    return np.pad(x, ((0, 0), (0, max(int(length * A.SR) - x.shape[1], 0))))[:, :int(length * A.SR)]


def sfx_set():
    out = {
        # synthesised noise-type effects
        "whoosh": A.stereo(A.whoosh(0.7)), "whoosh-long": A.stereo(A.whoosh(1.2, f0=200, f1=5000, rise=0.6)),
        "rumble": A.stereo(A.rumble(3.0)), "rumble-short": A.stereo(A.rumble(1.2)),
        "swish": A.stereo(A.bandpass(A.RNG.uniform(-1, 1, int(0.35 * A.SR)), 800, 5000) * np.hanning(int(0.35 * A.SR))),
        # sampled
        "ding": sampled([("glock", "A5", 0, 1.0, 100), ("celesta", "A5", 0, 1.0, 70)], 2.0),
        "tick": sampled([("woodblock", None, 0, 0.1, 100)], 0.4),
        "alert": sampled([("vibes", "A5", 0, 0.35, 105), ("vibes", "D6", 0.35, 0.8, 110)], 1.8),
        "spring": sampled([("pizz", "D3", 0, 0.3, 110), ("pizz", "A3", 0.08, 0.3, 90)], 0.8),
        "impact": sampled([("timpani", "D2", 0, 2.0, 127), ("bassdrum", None, 0, 0, 120), ("tubular", "D5", 0, 2.5, 110)], 3.0),
        "boom": sampled([("timpani", "D2", 0, 2.0, 127), ("bassdrum", None, 0, 0, 127), ("crash", None, 0, 0, 90)], 3.0),
    }
    # crack: rock fracture = noisy clicks + low thud
    t = A.secs(1.0)
    clicks = np.zeros_like(t)
    for at in A.RNG.uniform(0, 0.25, 14):
        i = int(at * A.SR)
        clicks[i:i + 400] += A.RNG.uniform(-1, 1, 400) * np.exp(-np.arange(400) / 60)
    out["crack"] = A.stereo(A.highpass(clicks, 1500) + 0.6 * A.kick(1.0, 80, 35)[:len(t)])
    res = {}
    for k, x in out.items():
        x = np.asarray(x, dtype=np.float64)
        x = x / (np.abs(x).max() + 1e-9)
        res[k] = A.master(A.fx(x, reverb=0.15, room=0.5, comp=False), lufs_like_db=-16)
    return res


def main():
    MUSIC.mkdir(parents=True, exist_ok=True)
    SFX.mkdir(parents=True, exist_ok=True)
    for name, fn, bpm in [("curious", curious, 92), ("tense", tense, 92), ("calm", calm, 70), ("epic", epic, 96)]:
        x, length = loop_render(fn, 8, bpm)
        A.write(MUSIC / f"loop-{name}.wav", x)
        print(f"loop-{name}.wav  {length:.1f}s  ({bpm} bpm, 8 bars)")
    A.write(MUSIC / "outro-sting.wav", outro_sting())
    print("outro-sting.wav")
    for k, x in sfx_set().items():
        A.write(SFX / f"{k}.wav", x)
    print("sfx:", ", ".join(sorted(p.stem for p in SFX.glob("*.wav"))))


if __name__ == "__main__":
    main()
