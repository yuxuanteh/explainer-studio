"""Music tracks (a library you downloaded, or your own music) fitted to a video.

    edl.py:  TRACKS = [("S01", "Jomon Grove"), ("C3", "From Whence We Came")]     first shot of each music section, title
             SHORT_TRACKS = [("X01", "Cosy")]                                      the short: one track
    python gs_tracks.py "<title>" ...        length, tempo, bars of tracks in the library (also checks the used-list)

Files: <music library>/<title> - <artist>.mp3 (or .wav / .m4a / .flac), with the analysis (<same name>.json) beside it.
The library folder and the used-list are [paths] music_library / music_used in studio.toml.
How a track is fitted, so it starts, joins and ends like music and not like a cut: pieces are cut only on bar lines,
whole phrases preferred; the track's own ending lands at the end of its section; a track that is too long loses whole
phrases from its middle, one that is too short repeats a middle phrase; the next track eases in over the ring of the
last one. No added fade-out, no added hit. Every track is set to the same average level; the mix puts it under the
voice (gs_episode._mix).
The beat analysis needs librosa (the optional "music fitting" component of the studio setup).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 48000
import gs_env  # noqa: E402

LIBRARY = gs_env.MUSIC_LIBRARY
USED = gs_env.MUSIC_USED
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".flac", ".ogg")


def tracks():
    return sorted(p for p in LIBRARY.glob("*") if p.suffix.lower() in AUDIO_EXT) if LIBRARY.exists() else []
TARGET_RMS_DB = -19.0


def file_for(title):
    hits = [p for p in tracks() if p.stem.lower().startswith(title.lower() + " - ") or p.stem.lower() == title.lower()]
    if not hits:
        raise SystemExit(f"music: no file for '{title}' in {LIBRARY} (download or copy the track there)")
    return hits[0]


def decode(path):
    pcm = subprocess.run([gs_env.FFMPEG, "-v", "error", "-nostdin", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True, timeout=300).stdout
    return np.frombuffer(pcm, np.int16).reshape(-1, 2).astype(np.float32) / 32768


def _analyse_file(path):
    """Beats, bars, loudness per bar and where the music really ends (runs where librosa is installed)."""
    import librosa
    y, sr = librosa.load(str(path), sr=22050, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    beats = [float(b) for b in beats]
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    ot = librosa.times_like(onset, sr=sr)
    strength = [float(np.interp(b, ot, onset)) for b in beats]
    phase = max(range(4), key=lambda p: np.mean(strength[p::4]) if strength[p::4] else 0)
    bars = beats[phase::4]
    rms = librosa.feature.rms(y=y)[0]
    rt = librosa.times_like(rms, sr=sr)
    db = 20 * np.log10(rms + 1e-9)
    alive = rt[db > float(np.percentile(db, 90)) - 35]
    end = float(alive[-1]) if len(alive) else len(y) / sr
    bar_db = [float(np.mean(db[(rt >= a) & (rt < b)])) if np.any((rt >= a) & (rt < b)) else -90.0 for a, b in zip(bars, bars[1:] + [end])]
    title = path.stem.split(" - ")[0]
    return dict(title=title, file=path.name, dur=len(y) / sr, tempo=float(np.atleast_1d(tempo)[0]), beats=beats, bars=bars,
                bar_db=bar_db, end=end, first=bars[0] if bars else 0.0)


def analyse(title):
    path = file_for(title)
    cache = path.with_suffix(".json")
    if not (cache.exists() and cache.stat().st_mtime > path.stat().st_mtime):
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--analyse", str(path)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=900)
        if r.returncode or not cache.exists():
            raise SystemExit(f"music: could not analyse '{title}' (is the music-fitting component installed? it needs librosa):\n{r.stdout[-800:]}{r.stderr[-800:]}")
    return json.loads(cache.read_text(encoding="utf-8"))


def plan(a, length):
    """Pieces [(from, to)] of the track that make `length` seconds, keeping its start and its ending."""
    bars, bdb, end = a["bars"], a["bar_db"], a["end"]
    if end <= length + 0.5 or len(bars) < 12:
        if end >= length - 0.5:
            return [(max(0.0, end - length), end)]
        need, best = length - end, None                     # too short: play a middle stretch again, whole phrases
        for i in range(8, len(bars) - 4):
            for j in range(4, i):
                gain = bars[i] - bars[j]
                if (i - j) % 4 or gain <= 0:
                    continue
                rep = max(1, round(need / gain))
                err = abs(rep * gain - need) + 0.3 * abs(bdb[i] - bdb[j])
                if best is None or err < best[0]:
                    best = (err, i, j, rep)
        if best is None:
            return [(0.0, end)]
        _, i, j, rep = best
        return [(0.0, bars[i])] + [(bars[j], bars[i])] * (rep - 1) + [(bars[j], end)]
    if length < 40:                                         # a short section: the track's start up to bar i, then its last
        best = None                                         # phrases from bar j
        for i in range(0, len(bars) - 1):
            for j in range(i + 1, len(bars)):
                kept = bars[i] + (end - bars[j])
                if abs(kept - length) > (bars[1] - bars[0]):
                    continue
                err = (abs(kept - length) + 0.4 * abs(bdb[i] - bdb[j]) + (0 if i % 4 == 0 else 1.5)
                       + (0 if (len(bars) - j) % 4 == 0 else 1.5) + (0 if bars[i] >= 4 else 2.0))
                if best is None or err < best[0]:
                    best = (err, i, j)
        if best is not None:
            _, i, j = best
            return ([(0.0, bars[i])] if i > 0 else []) + [(bars[j], end)]
        s0 = bars[0] if bars[0] > 4 else 0.0
        k = min((k for k in range(1, len(bars)) if bars[k] > s0), key=lambda k: abs(bars[k] - s0 - length) + (0 if k % 4 == 0 else 1.0))
        return [(s0, bars[k])]
    cut, best = end - length, None                          # too long: whole phrases out of the middle
    for i in range(max(4, len(bars) // 5), len(bars) * 4 // 5):
        for j in range(i + 1, len(bars) - 4):
            removed = bars[j] - bars[i]
            if removed > cut + 4 * (bars[1] - bars[0]):
                break
            err = abs(removed - cut) + 0.4 * abs(bdb[i] - bdb[j]) + (0 if (j - i) % 4 == 0 else 2.0)
            if best is None or err < best[0]:
                best = (err, i, j)
    if best is None:
        return [(end - length, end)]
    _, i, j = best
    pieces = [(0.0, bars[i]), (bars[j], end)]
    over = sum(q - p for p, q in pieces) - length
    if over > 0:
        pieces[0] = (min(over, bars[i] - 1.0), bars[i])
    return pieces


def assemble(x, pieces):
    """Join the pieces of one track, each join over a quarter second (equal power)."""
    out = np.zeros((0, 2), np.float32)
    xf = int(0.25 * SR)
    for p, q in pieces:
        seg = x[int(p * SR):int(q * SR)].copy()
        if len(out) > xf and len(seg) > xf:
            t = np.linspace(0, np.pi / 2, xf)[:, None]
            out[-xf:] = out[-xf:] * np.cos(t) + seg[:xf] * np.sin(t)
            seg = seg[xf:]
        out = np.concatenate([out, seg])
    return out


def render(tracks, starts, end_at, total, report=None):
    """tracks: [(first shot id, title)]; starts: {shot id: start time}; music runs to end_at; returns (n, 2) at SR."""
    out = np.zeros((int(total * SR) + SR, 2), np.float32)
    for sid, _ in tracks:
        if sid not in starts:
            raise SystemExit(f"music: TRACKS names shot {sid}, which is not in the timeline")
    secs = sorted((starts[sid], title) for sid, title in tracks)
    for k, (t0, title) in enumerate(secs):
        t1 = secs[k + 1][0] if k + 1 < len(secs) else end_at
        a = analyse(title)
        x = decode(file_for(title))
        pieces = plan(a, t1 - t0)
        y = assemble(x, pieces)
        e_ = pieces[-1][1]
        y = np.concatenate([y, x[int(e_ * SR):int(min(a["dur"], e_ + 4) * SR)]])          # the last chord's ring
        body = max(1, min(len(y), int((t1 - t0) * SR)))
        y *= 10 ** (TARGET_RMS_DB / 20) / np.sqrt(np.mean(y[:body] ** 2) + 1e-12)
        if k == 0 and t0 > 0.05:
            r = min(len(y), int(0.4 * SR))
            y[:r] *= np.linspace(0, 1, r)[:, None]
        elif k > 0:                                          # the next track eases in while the last one rings out
            r = min(len(y), int(1.5 * SR))
            y[:r] *= np.sin(np.linspace(0, np.pi / 2, r))[:, None] ** 2
        if k + 1 < len(secs) and len(y) > body:
            y[body:] *= np.linspace(1, 0, len(y) - body)[:, None]
        i0 = int(t0 * SR)
        j = min(len(out), i0 + len(y))
        out[i0:j] += y[:j - i0]
        if report is not None:
            report.append(f"{title}: {t0:.1f}-{t1:.1f} s ({t1 - t0:.1f} s) from " + ", ".join(f"{p:.1f}-{q:.1f}" for p, q in pieces)
                          + f" of its {a['dur']:.0f} s, its own ending at {a['end']:.1f} s")
    return out[:int(total * SR)]


def used(title):
    """Lines of the shared used-list that mention this track (soft rule: not again within about three months)."""
    if not USED.exists():
        return []
    return [line.strip() for line in USED.read_text(encoding="utf-8").splitlines() if line.startswith("|") and title.lower() in line.lower()]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.argv[1:2] == ["--analyse"]:
        p = Path(sys.argv[2])
        p.with_suffix(".json").write_text(json.dumps(_analyse_file(p)), encoding="utf-8")
    else:
        titles = sys.argv[1:] or sorted(p.stem.split(" - ")[0] for p in tracks())
        for t in titles:
            a = analyse(t)
            u = used(t)
            print(f"{t}: {a['dur']:.0f} s, {a['tempo']:.0f} bpm, {len(a['bars'])} bars, ends {a['end']:.0f} s"
                  + (f"  | used: {u[0].split('|')[4].strip()} ({u[0].split('|')[5].strip()})" if u else "  | not used yet"))
