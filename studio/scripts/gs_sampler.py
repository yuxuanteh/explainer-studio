"""A small multi-sample player for the VSCO 2 CE (CC0) orchestra samples.

Same API as gs_sf.Score:
    s = Score()
    s.note("harp", "A4", at=1.0, dur=1.5, vel=90)
    s.strings(["D3", "A3", "F4"], at=0, dur=4, vel=70, art="sus")   # auto-splits across sections
    x = s.render()                                                   # float32 stereo (2, n), dry
Samples are matched by nearest pitch (then pitch-shifted), velocity layer and round-robin.
"""
import re
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

import gs_audio as A
import gs_env

ROOT = gs_env.STUDIO / gs_env.cfg("music", "vsco_samples", "samples/VSCO-2-CE")
NOTE_RE = re.compile(r"^([A-G])([#b]?)(-?\d)$")


def midi_of(name):
    m = NOTE_RE.match(name)
    if not m:
        return None
    letter, acc, octv = m.groups()
    n = 12 * (int(octv) + 1) + A.NOTE_INDEX[letter]
    return n + (1 if acc == "#" else -1 if acc == "b" else 0)


def midi(note):
    return note if isinstance(note, int) else midi_of(note)


def detect_pitch(x, sr, fmin=50, fmax=400):
    """Fundamental of a drum hit via the strongest spectral peak in [fmin, fmax] after the attack."""
    seg = x[int(0.05 * sr):int(1.0 * sr)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=1 << 18))
    f = np.fft.rfftfreq(1 << 18, 1 / sr)
    band = (f > fmin) & (f < fmax)
    f0 = f[band][np.argmax(spec[band])]
    return 69 + 12 * np.log2(f0 / 440)


# ------------------------------------------------------------------ instrument maps

def scan(folder, pattern="*.wav", key=None, vel=None, rr=None, fixed_note=None, pitched=True):
    """Return list of dicts {path, note(float midi), vel_layer, rr}."""
    out = []
    for p in sorted((ROOT / folder).glob(pattern)):
        parts = p.stem.split("_")
        note = None
        if fixed_note is not None:
            note = fixed_note
        elif key:
            note = key(p)
        else:
            for t in parts:
                n = midi_of(t)
                if n is not None:
                    note = n
        v = vel(p) if vel else next((int(t[1:]) for t in parts if re.fullmatch(r"v\d+", t)), 1)
        r = rr(p) if rr else next((int(re.sub(r"\D", "", t)) for t in parts if re.fullmatch(r"(?i)rr\d+", t)), 1)
        out.append({"path": p, "note": note, "vel": v, "rr": r})
    if pitched and any(o["note"] is None for o in out):
        for o in out:
            x, sr = sf.read(str(o["path"]), dtype="float32", always_2d=True)
            o["note"] = detect_pitch(x.mean(1), sr)
    return out


def _piano():
    chart = (ROOT / "Keys/Upright Piano/MappingChart.txt").read_text().splitlines()
    piano_map = {k: int(v) for k, v in (ln.split("=") for ln in chart if re.fullmatch(r"\d{3}=\d+", ln.strip()))}

    def key(p):
        return piano_map[p.stem.split("_")[-1]]
    return scan("Keys/Upright Piano", "Player_*.wav", key=key,
                vel=lambda p: int(re.search(r"dyn(\d)", p.stem).group(1)),
                rr=lambda p: int(re.search(r"rr(\d)", p.stem).group(1)))


def _timpani():
    """Five drums, unlabelled pitch: detect per hit, then use each drum's median so all its hits agree."""
    zs = scan("Percussion/Timpani", "Timpani*_Hit_*.wav")
    for drum in {z["path"].stem.split("_")[0] for z in zs}:
        group = [z for z in zs if z["path"].stem.startswith(drum + "_")]
        med = float(np.median([z["note"] for z in group]))
        for z in group:
            z["note"] = med
    return zs


INSTRUMENTS = {
    # name: (loader, release_s, gain_db)
    "violins": (lambda: scan("Strings/Violin Section/susVib"), 0.5, 0),
    "violas": (lambda: scan("Strings/Viola Section/susvib"), 0.5, 0),
    "cellos": (lambda: scan("Strings/Cello Section/susvib"), 0.5, 0),
    "basses": (lambda: scan("Strings/Solo Contrabass/SusVib"), 0.5, 0),
    "violins_spic": (lambda: scan("Strings/Violin Section/Spic"), 0.15, 0),
    "violas_spic": (lambda: scan("Strings/Viola Section/spic"), 0.15, 0),
    "cellos_spic": (lambda: scan("Strings/Cello Section/spic"), 0.15, 0),
    "basses_spic": (lambda: scan("Strings/Solo Contrabass/Spic"), 0.15, 0),
    "violins_pizz": (lambda: scan("Strings/Violin Section/Pizz"), 0.3, 0),
    "violas_pizz": (lambda: scan("Strings/Viola Section/pizz"), 0.3, 0),
    "cellos_pizz": (lambda: scan("Strings/Cello Section/pizzT"), 0.3, 0),
    "basses_pizz": (lambda: scan("Strings/Solo Contrabass/Pizz"), 0.3, 0),
    "harp": (lambda: scan("Strings/Harp"), 1.5, 0),
    "piano": (_piano, 0.6, 0),
    "horn": (lambda: scan("Brass/F Horn/sus"), 0.5, 0),
    "glock": (lambda: scan("Percussion/Glock"), 2.0, -4),
    "timpani": (lambda: _timpani(), 3.0, 0),
    "tubular": (lambda: scan("Percussion", "TB_hit_*.wav"), 4.0, 0),
    # unpitched (played as recorded; 'note' ignored)
    "crash": (lambda: scan("Percussion", "cymbal-crash1_*.wav", fixed_note=60,
                           vel=lambda p: ["pp", "mp", "mf", "ff"].index(p.stem.split("_")[1]) + 1), 4.0, 0),
    "suscymb_swell": (lambda: scan("Percussion", "susCymb1-cresc-*.wav", fixed_note=60, vel=lambda p: 1), 1.0, 0),
    "gong": (lambda: scan("Percussion", "gongHit_*.wav", fixed_note=60,
                          vel=lambda p: ["p", "mf", "f", "fff"].index(p.stem.split("_")[1]) + 1), 6.0, 0),
    "bassdrum": (lambda: scan("Percussion", "BDrumNewhit_*.wav", fixed_note=60), 2.0, 0),
    "triangle": (lambda: scan("Percussion", "Triangle3-Hit_*.wav", fixed_note=60), 3.0, -6),
}
UNPITCHED = {"crash", "suscymb_swell", "gong", "bassdrum", "triangle"}

# string-section ranges for auto split (midi): lower bound of each section
SECTION_SPLIT = [("basses", 0), ("cellos", 43), ("violas", 50), ("violins", 57)]   # G2, D3, A3


@lru_cache(maxsize=None)
def zones(inst):
    return INSTRUMENTS[inst][0]()


@lru_cache(maxsize=4096)
def load(path):
    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.T
    if x.shape[0] == 1:
        x = np.vstack([x, x])
    return x[:2], sr


@lru_cache(maxsize=4096)
def pitched(path, shift_semitones, sr_out):
    """Load a sample, pitch-shift by resampling, convert to sr_out."""
    x, sr = load(path)
    ratio = Fraction(sr_out / sr / (2 ** (shift_semitones / 12))).limit_denominator(2000)
    if ratio == 1:
        return x
    return signal.resample_poly(x, ratio.numerator, ratio.denominator, axis=1).astype(np.float32)


class Score:
    def __init__(self, humanize=0.008, seed=1):
        self.events = []      # (inst, midi, at, dur, vel)
        self.autom = {}       # inst -> list of (t, gain 0..1)
        self.rng = np.random.default_rng(seed)
        self.humanize = humanize
        self.rr_counter = {}

    # --- API compatible with gs_sf.Score ---
    def note(self, inst, note, at, dur, vel=90):
        jitter = self.rng.normal(0, self.humanize) if self.humanize else 0
        v = int(np.clip(vel + self.rng.normal(0, 4), 1, 127))
        self.events.append((inst, 60 if inst in UNPITCHED else midi(note), max(at + jitter, 0), dur, v))
        return self

    def chord(self, inst, notes, at, dur, vel=80):
        for n in notes:
            self.note(inst, n, at, dur, vel)
        return self

    def hit(self, inst, at, vel=90):
        return self.note(inst, None, at, 0.0, vel)

    def swell(self, inst, at, dur, v0=30, v1=120, steps=24):
        insts = [inst] if inst in INSTRUMENTS else [s for s, _ in SECTION_SPLIT]
        for i in insts:
            pts = self.autom.setdefault(i, [])
            pts += [(at + dur * k / steps, (v0 + (v1 - v0) * k / steps) / 127) for k in range(steps + 1)]
        return self

    # --- strings helper ---
    def strings(self, notes, at, dur, vel=80, art="sus"):
        suffix = {"sus": "", "spic": "_spic", "pizz": "_pizz"}[art]
        for n in notes:
            m = midi(n)
            section = [s for s, lo in SECTION_SPLIT if m >= lo][-1]
            self.note(section + suffix, m, at, dur, vel)
        return self

    # --- rendering ---
    def _pick(self, inst, m, vel):
        zs = zones(inst)
        best = min(abs(z["note"] - m) for z in zs)
        cands = [z for z in zs if abs(z["note"] - m) - best < 0.01]
        layers = sorted({z["vel"] for z in cands})
        layer = layers[min(int(vel / 128 * len(layers)), len(layers) - 1)]
        cands = [z for z in cands if z["vel"] == layer]
        k = (inst, cands[0]["note"], layer)
        self.rr_counter[k] = self.rr_counter.get(k, -1) + 1
        z = sorted(cands, key=lambda z: z["rr"])[self.rr_counter[k] % len(cands)]
        return z, len(layers), layers.index(layer)

    def render(self):
        end = max((at + dur + INSTRUMENTS[i][1] + 6 for i, _m, at, dur, _v in self.events), default=1)
        buses = {}
        for inst, m, at, dur, vel in self.events:
            z, n_layers, li = self._pick(inst, m, vel)
            shift = 0.0 if inst in UNPITCHED else m - z["note"]
            x = pitched(z["path"], round(shift, 3), A.SR)
            release = INSTRUMENTS[inst][1]
            hold = dur if dur > 0 else x.shape[1] / A.SR
            n = min(x.shape[1], int((hold + release) * A.SR))
            env = np.ones(n, dtype=np.float32)
            r0 = int(hold * A.SR)
            if r0 < n:
                env[r0:] = np.linspace(1, 0, n - r0) ** 2
            # velocity within a layer: +-6 dB around the layer's own loudness
            lo, hi = li / n_layers * 127, (li + 1) / n_layers * 127
            g = 10 ** ((INSTRUMENTS[inst][2] + 6 * ((vel - lo) / max(hi - lo, 1) - 0.5) * 2 - 6) / 20)
            bus = buses.setdefault(inst, np.zeros((2, int(end * A.SR)), dtype=np.float32))
            i0 = int(at * A.SR)
            j = min(i0 + n, bus.shape[1])
            bus[:, i0:j] += x[:, :j - i0] * env[:j - i0] * g
        mix = np.zeros((2, int(end * A.SR)), dtype=np.float32)
        for inst, bus in buses.items():
            if inst in self.autom:
                pts = sorted(self.autom[inst])
                t = np.arange(bus.shape[1]) / A.SR
                curve = np.interp(t, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)
                bus = bus * curve
            mix += bus
        last = np.max(np.nonzero(np.abs(mix).max(0) > 1e-5)[0], initial=0)
        return mix[:, :last + 1]
