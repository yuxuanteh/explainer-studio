"""Audio synthesis toolkit: instruments, SFX, mixing helpers.

Everything is numpy float32 mono/stereo at SR. Build music by placing notes on a
timeline with `place()`, then `master()` it.
"""
import numpy as np
import pedalboard as pb
import soundfile as sf
from scipy import signal

SR = 48000
RNG = np.random.default_rng(7)

# ---------------------------------------------------------------- basics

NOTE_INDEX = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
              "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def hz(note):
    """'A4' -> 440.0, 'Bb2' -> 116.5"""
    name, octave = note[:-1], int(note[-1])
    midi = 12 * (octave + 1) + NOTE_INDEX[name]
    return 440.0 * 2 ** ((midi - 69) / 12)


def secs(n):
    return np.arange(int(n * SR)) / SR


def env_adsr(n, a=0.01, d=0.1, s=0.7, r=0.2):
    n = int(n)
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(n - a_n - d_n - r_n, 0)
    e = np.concatenate([np.linspace(0, 1, a_n, endpoint=False), np.linspace(1, s, d_n, endpoint=False),
                        np.full(s_n, s), np.linspace(s, 0, r_n)])
    return np.pad(e, (0, max(n - len(e), 0)))[:n]


def env_exp(n, tau):
    return np.exp(-np.arange(int(n)) / (tau * SR))


def lowpass(x, cutoff, order=2):
    sos = signal.butter(order, cutoff, "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def highpass(x, cutoff, order=2):
    sos = signal.butter(order, cutoff, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], "band", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def sweep_lowpass(x, f0, f1, chunk=512):
    """Time-varying low-pass from f0 to f1 (Hz), exponential sweep."""
    out = np.zeros_like(x)
    n_chunks = int(np.ceil(len(x) / chunk))
    zi = None
    for i in range(n_chunks):
        f = f0 * (f1 / f0) ** (i / max(n_chunks - 1, 1))
        sos = signal.butter(2, min(f, SR / 2 - 100), "low", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        seg = x[i * chunk:(i + 1) * chunk]
        out[i * chunk:(i + 1) * chunk], zi = signal.sosfilt(sos, seg, zi=zi)
    return out


# ---------------------------------------------------------------- instruments

def pluck(freq, dur=1.5, bright=0.6, decay=0.996):
    """Karplus-Strong plucked string (harp / nylon guitar-like). Block-vectorised."""
    n = int(dur * SR)
    period = int(SR / freq)
    buf = lowpass(RNG.uniform(-1, 1, period), 1500 + 9000 * bright, order=1)
    out = np.zeros(n + period)
    out[:period] = buf
    out[period] = decay * 0.5 * buf[0]
    # y[k] = decay * mean(y[k-P], y[k-P-1]); a block of <= P samples only reads the previous block
    i = period + 1
    while i < n + period:
        j = min(i + period, n + period)
        out[i:j] = decay * 0.5 * (out[i - period:j - period] + out[i - period - 1:j - period - 1])
        i = j
    y = out[period:period + n]
    y *= env_adsr(n, a=0.002, d=0.05, s=1.0, r=0.08)
    return y / (np.abs(y).max() + 1e-9)


def pad(freqs, dur, cutoff=1800, detune=0.006, attack=0.8, release=1.2, voices=3):
    """Warm detuned-saw pad, low-passed."""
    t = secs(dur)
    y = np.zeros_like(t)
    for f in freqs:
        for v in range(voices):
            fv = f * (1 + detune * (v - (voices - 1) / 2))
            ph = RNG.uniform(0, 1)
            y += signal.sawtooth(2 * np.pi * (fv * t + ph))
    y = lowpass(y, cutoff, order=2)
    y *= env_adsr(len(t), a=attack, d=0.3, s=0.85, r=release)
    return y / (np.abs(y).max() + 1e-9)


def bass(freq, dur, drive=1.5):
    t = secs(dur)
    y = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t)
    y = np.tanh(drive * y)
    y *= env_adsr(len(t), a=0.01, d=0.15, s=0.6, r=0.15)
    return y / (np.abs(y).max() + 1e-9)


def bell(freq, dur=2.5):
    """Soft bell / glockenspiel: inharmonic partials."""
    t = secs(dur)
    y = np.zeros_like(t)
    for ratio, amp, tau in [(1, 1, 1.2), (2.0, 0.35, 0.7), (2.76, 0.25, 0.5), (5.4, 0.1, 0.25)]:
        y += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t / tau)
    y *= env_adsr(len(t), a=0.003, d=0.0, s=1.0, r=0.05)
    return y / (np.abs(y).max() + 1e-9)


# ---------------------------------------------------------------- drums & sfx

def kick(dur=0.45, f0=110, f1=42):
    t = secs(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.04)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18)
    return y / np.abs(y).max()


def shaker(dur=0.09):
    n = int(dur * SR)
    y = highpass(RNG.uniform(-1, 1, n), 6000) * env_exp(n, 0.02)
    return y / (np.abs(y).max() + 1e-9)


def tick(freq=2400, dur=0.05):
    t = secs(dur)
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.008)
    return y / np.abs(y).max()


def whoosh(dur=0.8, f0=300, f1=6000, rise=0.75):
    """Air whoosh: noise through a sweeping low-pass, swelling up then cut."""
    n = int(dur * SR)
    noise = RNG.uniform(-1, 1, n)
    y = sweep_lowpass(noise, f0, f1)
    e = np.concatenate([np.linspace(0, 1, int(n * rise)) ** 2, np.linspace(1, 0, n - int(n * rise)) ** 0.5])
    y = y * e
    return y / (np.abs(y).max() + 1e-9)


def impact(dur=2.5):
    """Spike strike: sub thump + metallic ring (the 'golden spike' hit)."""
    t = secs(dur)
    thump = np.sin(2 * np.pi * np.cumsum(38 + 80 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.35)
    ring = np.zeros_like(t)
    for f, amp, tau in [(1318, 0.5, 0.9), (1318 * 2.41, 0.25, 0.5), (1318 * 3.87, 0.15, 0.3), (659, 0.3, 1.2)]:
        ring += amp * np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
    click = highpass(RNG.uniform(-1, 1, len(t)), 2000) * np.exp(-t / 0.004)
    y = 1.0 * thump + 0.45 * ring + 0.5 * click
    return y / np.abs(y).max()


def rumble(dur=2.0, cutoff=90):
    n = int(dur * SR)
    brown = np.cumsum(RNG.uniform(-1, 1, n))
    brown = highpass(brown, 20)
    y = lowpass(brown, cutoff, order=4)
    y *= env_adsr(n, a=0.05, d=0.3, s=0.6, r=dur * 0.6)
    return y / (np.abs(y).max() + 1e-9)


def shimmer(dur=1.2, f0=900):
    """Rising glassy shimmer for the seismic ripple."""
    t = secs(dur)
    f = f0 * (1 + 0.5 * t / dur)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    y *= np.sin(np.pi * t / dur) ** 2 * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t))
    return y / np.abs(y).max()


# ---------------------------------------------------------------- arranging & mixing

class Track:
    """A mono timeline. place(sound, at_seconds, gain_db)."""

    def __init__(self, length):
        self.y = np.zeros(int(length * SR) + SR * 4)

    def place(self, x, at, db=0.0):
        i = int(at * SR)
        x = x * 10 ** (db / 20)
        j = min(i + len(x), len(self.y))
        self.y[i:j] += x[:j - i]
        return self


def stereo(x, pan=0.0):
    """pan -1 (left) .. +1 (right), constant-power."""
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=0)


def fx(x, reverb=0.25, room=0.6, width=1.0, comp=True):
    board = pb.Pedalboard([pb.Reverb(room_size=room, wet_level=reverb, dry_level=1.0 - reverb * 0.5, width=width)])
    if comp:
        board.append(pb.Compressor(threshold_db=-18, ratio=2.5, attack_ms=10, release_ms=150))
    x = np.atleast_2d(x).astype(np.float32)
    return board(x, SR)


def master(x, target_peak_db=-1.0, lufs_like_db=-16.0):
    """Glue compressor + limiter, normalise to approx loudness then peak-limit."""
    x = np.atleast_2d(x).astype(np.float32)
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    x = x * (10 ** (lufs_like_db / 20) / rms)
    board = pb.Pedalboard([pb.Compressor(threshold_db=-14, ratio=2, attack_ms=20, release_ms=200),
                           pb.Limiter(threshold_db=target_peak_db, release_ms=80)])
    y = board(x, SR)
    ceiling = 10 ** (target_peak_db / 20)
    peak = np.abs(y).max()
    return y * (ceiling / peak) if peak > ceiling else y  # the limiter can overshoot slightly


def trim(x, seconds):
    return x[..., :int(seconds * SR)]


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    n = x.shape[-1]
    if fin:
        k = int(fin * SR)
        x[..., :k] *= np.linspace(0, 1, k)
    if fout:
        k = int(fout * SR)
        x[..., n - k:] *= np.linspace(1, 0, k)
    return x


def write(path, x):
    x = np.atleast_2d(x)
    sf.write(str(path), x.T, SR, subtype="PCM_24")
