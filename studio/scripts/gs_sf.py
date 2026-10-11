"""Render real-instrument music from note lists via FluidSynth + GeneralUser GS soundfont.

    s = Score()
    s.note("harp", "A4", at=1.0, dur=1.5, vel=90)
    stereo = s.render()          # float32 (2, n) at gs_audio.SR, dry (add reverb with gs_audio.fx)
"""
import subprocess
import tempfile
from pathlib import Path

import mido
import numpy as np
import soundfile as sf

import gs_audio as A
import gs_env
from gs_audio import NOTE_INDEX


def _tool(key, default):
    v = gs_env.cfg("music", key, default)
    p = Path(v)
    return str(p if p.is_absolute() or "/" not in v and "\\" not in v else gs_env.STUDIO / p)


FLUIDSYNTH = _tool("fluidsynth", "tools/fluidsynth/bin/fluidsynth.exe")   # a bare "fluidsynth" uses PATH
SOUNDFONT = _tool("soundfont", "soundfonts/GeneralUser-GS.sf2")

# General MIDI programs (0-based)
PROGRAMS = {
    "piano": 0, "celesta": 8, "glock": 9, "vibes": 11, "marimba": 12, "tubular": 14,
    "nylon": 24, "cello": 42, "contrabass": 43, "tremolo": 44, "pizz": 45, "harp": 46, "timpani": 47,
    "strings": 48, "slowstrings": 49, "choir": 52, "orchhit": 55, "horn": 60, "flute": 73,
}
DRUMS = {"bassdrum": 35, "kick": 36, "crash": 49, "ride": 51, "splash": 55, "maracas": 70, "cabasa": 69,
         "triangle": 81, "triangle_mute": 80, "woodblock": 76, "lowtom": 41}
DRUM_CH = 9

TPB = 480                 # ticks per beat
TEMPO = 500000            # 120 bpm -> 1 beat = 0.5 s, so 1 s = 960 ticks
TICKS_PER_SEC = TPB * 1_000_000 / TEMPO


def midi_num(note):
    if isinstance(note, int):
        return note
    name, octave = note[:-1], int(note[-1])
    return 12 * (octave + 1) + NOTE_INDEX[name]


class Score:
    def __init__(self, humanize=0.008, seed=1):
        self.events = []          # (channel, program, midi, start_s, dur_s, vel)
        self.channels = {}        # instrument -> channel
        self.cc = []              # (channel, at_s, cc, value)
        self.rng = np.random.default_rng(seed)
        self.humanize = humanize

    def _ch(self, inst):
        if inst in DRUMS:
            return DRUM_CH
        if inst not in self.channels:
            free = [c for c in range(16) if c != DRUM_CH and c not in self.channels.values()]
            self.channels[inst] = free[0]
        return self.channels[inst]

    def note(self, inst, note, at, dur, vel=90):
        ch = self._ch(inst)
        jitter = self.rng.normal(0, self.humanize) if self.humanize else 0
        v = int(np.clip(vel + self.rng.normal(0, 4), 1, 127))
        m = DRUMS[inst] if inst in DRUMS else midi_num(note)
        self.events.append((ch, PROGRAMS.get(inst, 0), m, max(at + jitter, 0), dur, v))
        return self

    def chord(self, inst, notes, at, dur, vel=80):
        for n in notes:
            self.note(inst, n, at, dur, vel)
        return self

    def hit(self, drum, at, vel=90):
        return self.note(drum, None, at, 0.5, vel)

    def expression(self, inst, at, value):
        """CC11 expression (0-127) for swells."""
        self.cc.append((self._ch(inst), at, 11, int(value)))
        return self

    def swell(self, inst, at, dur, v0=30, v1=120, steps=24):
        for i in range(steps + 1):
            self.expression(inst, at + dur * i / steps, v0 + (v1 - v0) * i / steps)
        return self

    def to_midi(self, path):
        mid = mido.MidiFile(ticks_per_beat=TPB)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage("set_tempo", tempo=TEMPO, time=0))
        msgs = []
        for inst, ch in self.channels.items():
            msgs.append((0, 0, mido.Message("program_change", channel=ch, program=PROGRAMS[inst])))
            msgs.append((0, 0, mido.Message("control_change", channel=ch, control=11, value=127)))
            msgs.append((0, 0, mido.Message("control_change", channel=ch, control=91, value=0)))   # reverb off
            msgs.append((0, 0, mido.Message("control_change", channel=ch, control=93, value=0)))   # chorus off
        for ch, at, cc, val in self.cc:
            msgs.append((int(at * TICKS_PER_SEC), 1, mido.Message("control_change", channel=ch, control=cc, value=val)))
        for ch, _prog, m, at, dur, v in self.events:
            msgs.append((int(at * TICKS_PER_SEC), 2, mido.Message("note_on", channel=ch, note=m, velocity=v)))
            msgs.append((int((at + dur) * TICKS_PER_SEC), 0, mido.Message("note_off", channel=ch, note=m, velocity=0)))
        msgs.sort(key=lambda x: (x[0], x[1]))
        last = 0
        for tick, _o, msg in msgs:
            track.append(msg.copy(time=tick - last))
            last = tick
        mid.save(path)

    def render(self, gain=0.5):
        with tempfile.TemporaryDirectory() as td:
            mpath, wpath = Path(td) / "s.mid", Path(td) / "s.wav"
            self.to_midi(mpath)
            subprocess.run([FLUIDSYNTH, "-ni", "-q", "-R", "0", "-C", "0", "-g", str(gain), "-r", str(A.SR),
                            "-F", str(wpath), SOUNDFONT, str(mpath)], check=True, capture_output=True)
            x, sr = sf.read(str(wpath), dtype="float32")
        assert sr == A.SR
        return x.T
