"""Build SHOTS + CUES + SQUEEZE for edl.py from Whisper word timings · {{EPISODE}} (template from episode 01).

    python make_edl.py            -> prints SHOTS / CUES python blocks to paste into edl.py

Each take is given as (shot id, kind, source key, from, to, mood, cues) where from/to bracket the words of the take in
SOURCE time (camera time for cam shots). Cut points go into the silence before the first word / after the last
word. Cue boundaries are placed in the inter-word gap closest to where the text proportion says they should be,
preferring longer pauses. Cue text = what was said (script corrected), with the second-language translation.
Written for CJK narration (cue boundaries are matched character by character); for word-based languages adapt
`cjk()` / `spoken()` to match words.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))   # <studio>/scripts
import gs_env  # noqa: E402

WORK = gs_env.EPISODES / "{{EPISODE}}" / "work"
LAG = {}            # camera key -> phone lag (s), same as edl.EXT_AUDIO
JSON = {"voice": "voice", **{k: "cam-" + k[3:] for k in LAG}}


def words(src):
    d = json.loads((WORK / f"{JSON[src]}.whisper.json").read_text(encoding="utf-8"))
    lag = LAG.get(src, 0.0)
    return [(w["start"] + lag, w["end"] + lag, w["word"]) for s in d["segments"] for w in s["words"]
            if w["end"] - w["start"] > 0.005]


RAW = WORK.parent / "raw"
AUDIO = {"voice": "voice.m4a", **{k: "cam-" + k[3:] + ".m4a" for k in LAG}}
_pcm = {}


def pcm(src):
    if src not in _pcm:
        raw = subprocess.run([gs_env.FFMPEG, "-v", "error", "-i", str(RAW / AUDIO[src]), "-ac", "1", "-ar", "16000",
                              "-f", "s16le", "-"], capture_output=True, check=True).stdout
        _pcm[src] = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    return _pcm[src]


def quietest(src, lo, hi, win=0.08):
    """Centre of the quietest `win` window in [lo, hi] (source time; phone tracks shifted by LAG)."""
    x, lag, sr = pcm(src), LAG.get(src, 0.0), 16000
    best, bt = 1e9, (lo + hi) / 2
    t = lo
    while t + win <= hi:
        a, b = int((t - lag) * sr), int((t - lag + win) * sr)
        if a >= 0:
            e = float(np.sqrt(np.mean(x[a:b] ** 2)) + 1e-9)
            if e < best:
                best, bt = e, t + win / 2
        t += 0.01
    return bt


FR = 0.02          # loudness frame (s)
SIL_DB, SPEECH_DB = -48.0, -45.0


def level(src, t0, t1):
    """dB per 20 ms frame between source times t0..t1."""
    x, lag, sr = pcm(src), LAG.get(src, 0.0), 16000
    out = []
    t = t0
    while t < t1:
        a, b = int((t - lag) * sr), int((t - lag + FR) * sr)
        seg = x[max(a, 0):max(b, 0)]
        out.append(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9) if len(seg) else -120.0)
        t += FR
    return np.array(out)


def onset(src, t_from, fwd=4.0):
    """First real speech (> -38 dB) after the bracket start t_from. If t_from is still inside the previous line's
    tail, wait for a short gap (>= 0.1 s below -44 dB) first."""
    t0 = t_from - 0.15
    lv = level(src, t0, t_from + fwd)
    i = 0
    if lv[0] > -44:                       # starts inside speech -> skip to the next gap
        while i < len(lv) - 5 and not (lv[i:i + 5] < -44).all():
            i += 1
    while i < len(lv) - 8:
        if lv[i] > -38 and (lv[i:i + 8] > -38).sum() >= 5:     # sustained >= ~0.1 s: ignores lip clicks
            return t0 + i * FR
        i += 1
    return None


def offset(src, t_last_word, fwd=3.0, quiet=0.25):
    """Start of the first silence (>= `quiet` s) after the last word began."""
    lv = level(src, t_last_word, t_last_word + fwd)
    q = int(quiet / FR)
    for i in range(len(lv) - q):
        if (lv[i:i + q] < SIL_DB).all():
            return t_last_word + i * FR
    return None


def pauses(src, tin, tout, min_len=0.75, keep=0.2):
    """Long silences inside a take -> source ranges to squeeze out (leaving `keep` s on each side)."""
    lv = level(src, tin, tout)
    cuts, i = [], 0
    while i < len(lv):
        if lv[i] < SIL_DB:
            j = i
            while j < len(lv) and lv[j] < SIL_DB:
                j += 1
            a, b = tin + i * FR, tin + j * FR
            if b - a >= min_len and a > tin + 0.3 and b < tout - 0.3:
                cuts.append((round(a + keep, 2), round(b - keep, 2)))
            i = j
        i += 1
    return cuts


def spoken(s):
    return len(re.findall(r"[一-鿿]", s)) + 1.5 * len(re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]*", s))


# Pause sweet spot (found on the original channel's rough cuts):
#   Whisper edges left 1-3 s between lines -> too long. Loudness cuts with 0.12 s head + 0.15 s tail (~0.3 s)
#   -> fine when the next line continues the thought, "a bit too short" when it opens a new idea, a question or
#   a contrast. So: ~0.3 s inside a thought, ~0.6 s before a new idea (head pad 0.45 s instead of 0.12 s).
HEAD, HEAD_NEW_IDEA, TAIL = 0.12, 0.45, 0.15
NEW_IDEA_START = tuple(gs_env.LANG.get("new_idea_words", []))   # [language] new_idea_words in studio.toml
NEW_IDEA = set()      # shots the director flagged as "a bit too short"; the rule below finds the rest


def new_idea(sid, cues):
    first = cues[0][0]
    return sid in NEW_IDEA or first.startswith(NEW_IDEA_START) or "?" in first


def take(src, a, b, cues, lead=0.25, tail=0.35, head=HEAD):
    allw = words(src)
    ws = [w for w in allw if a - 0.05 <= w[0] < b]
    i0 = allw.index(ws[0])
    i1 = allw.index(ws[-1])
    prev_end = allw[i0 - 1][1] if i0 > 0 else 0.0
    next_start = allw[i1 + 1][0] if i1 + 1 < len(allw) else ws[-1][1] + 1.0
    tin = max(ws[0][0] - lead, (prev_end + ws[0][0]) / 2)
    tout = min(ws[-1][1] + tail, (ws[-1][1] + next_start) / 2)
    # Whisper's word edges are approximate (often glued between lines): snap cuts to real silence
    # cut points from loudness (Whisper word edges are off by up to ~1 s where lines run together):
    # in = 0.12 s before the voice starts after a silence; out = 0.15 s into the silence after the last word
    on = onset(src, a)
    off = offset(src, max(ws[-1][0], b - 0.6))
    tin = on - head if on is not None else quietest(src, max(tin - 0.45, prev_end - 0.05, 0.0), ws[0][0] + 0.12)
    tout = off + TAIL if off is not None else quietest(src, ws[-1][1] - 0.12, ws[-1][1] + 0.5)
    # cue boundaries: match the Chinese characters of the cue text to Whisper's words (English terms are often
    # misheard, Chinese characters mostly right); fall back to the nearest pause for unmatched boundaries
    import difflib
    cjk = lambda s: re.findall(r"[一-鿿0-9]", s)  # noqa: E731
    wchars, wmap = [], []
    for k, (_, _, w) in enumerate(ws):
        for ch in cjk(w):
            wchars.append(ch)
            wmap.append(k)
    starts, n = [], 0
    for zh, _ in cues:
        starts.append(n)
        n += len(cjk(zh))
    cchars = [ch for zh, _ in cues for ch in cjk(zh)]
    sm = difflib.SequenceMatcher(None, cchars, wchars, autojunk=False)
    c2w = {}
    for a0, b0, size in sm.get_matching_blocks():
        for q in range(size):
            c2w[a0 + q] = wmap[b0 + q]
    first_word = [0]
    for ci, s0 in enumerate(starts[1:], 1):
        cand = [c2w[q] for q in range(s0, starts[ci + 1] if ci + 1 < len(starts) else len(cchars)) if q in c2w]
        prev = [c2w[q] for q in range(starts[ci - 1], s0) if q in c2w]
        k = cand[0] if cand else (max(prev) + 1 if prev else first_word[-1] + 1)   # all-English cue
        # step back over English words that precede the first Chinese character of the cue
        lead_en = re.match(r"\s*([A-Za-z][A-Za-z0-9 .,\-]*?)\s*[一-鿿0-9]", cues[ci][0])
        if lead_en:
            while k - 1 > first_word[-1] and not cjk(ws[k - 1][2]):
                k -= 1
        first_word.append(max(k, first_word[-1] + 1))
    times = []
    for ci, k in enumerate(first_word):
        k_end = first_word[ci + 1] - 1 if ci + 1 < len(first_word) else len(ws) - 1
        times.append((ws[k][0], ws[k_end][1]))
    return tin, tout, [(src, s, e, zh, en) for (s, e), (zh, en) in zip(times, cues)]


# (id, kind, src, from, to, mood, cues)   from/to in source time (camera time for cam shots)
TAKES = [
    # ("S01", "cam", "camS01", 10.5, 33.5, "tense", [("main subtitle, as actually said", "translation"), ...]),
    # ("S02", "anim", "voice", 27.5, 40.2, "curious", [...]),
]

INSERT_BEFORE = {"S02": [("INTRO", "intro", None, 0.0, 4.20, 0.0, "intro"), ("C1", "chapter", None, 0.0, 3.0, 0.0, "curious")]}
END_TOTAL = 12.0   # END card length incl. hold

# cue times fixed by hand where Whisper aligned the text to a dropped first attempt: {shot: {cue index: (src, a, b)}}
CUE_FIX = {}

# cut points pinned by hand after checking the loudness profile: {shot: (in or None, out or None)}
PIN = {}

# false starts inside a take (source ranges cut out; verified by re-transcribing the window on its own)
MANUAL_CUTS = {}


# beats: name -> anchor text (Chinese characters / digits, or an English word) -> start time of that word
BEATS = {
    # "S02": {"crack": "裂开", "hypo": "叫做"},
}


def find_beats(src, tin, tout, spec):
    ws = [w for w in words(src) if tin - 0.6 <= w[0] < tout]     # Whisper starts can be ~0.5 s early
    toks = []                       # (normalised token, word start)
    for s, e, w in ws:
        chars = re.findall(r"[一-鿿0-9]", w)
        if chars:
            toks += [(c, s) for c in chars]
        else:
            toks.append((re.sub(r"[^a-z]", "", w.lower()), s))
    out = {}
    for name, anchor in spec.items():
        a = re.findall(r"[一-鿿0-9]", anchor) or [anchor.lower()]
        hit = None
        for i in range(len(toks) - len(a) + 1):
            if all(toks[i + k][0].startswith(a[k]) if not re.match(r"[一-鿿0-9]", a[k]) else toks[i + k][0] == a[k]
                   for k in range(len(a))):
                hit = toks[i][1]
                break
        if hit is None:
            print(f"# !! beat {name!r} ({anchor}) not found in {src} {tin:.2f}-{tout:.2f} -> shot start")
            out[name] = round(tin + 0.2, 2)
        else:
            out[name] = round(max(hit, tin), 2)
    return out


def main():
    shots, cues, squeeze = [], [], {}
    for sid, kind, src, a, b, mood, cs in TAKES:
        for row in INSERT_BEFORE.get(sid) or []:
            shots.append((*row, {}))
        tin, tout, cc = take(src, a, b, cs, head=HEAD_NEW_IDEA if new_idea(sid, cs) else HEAD)
        p_in, p_out = PIN.get(sid, (None, None))
        tin, tout = p_in if p_in is not None else tin, p_out if p_out is not None else tout
        cc = [(s, max(x, tin), min(y, tout), zh, en) for s, x, y, zh, en in cc]
        for k, (s_, x, y) in CUE_FIX.get(sid, {}).items():
            cc[k] = (cc[k][0], x, y, cc[k][3], cc[k][4])
        for k in range(len(cc)):                     # every cue readable for >= 0.9 s, never past the next one
            nxt = cc[k + 1][1] - 0.02 if k + 1 < len(cc) else tout
            s_, x, y, zh_, en_ = cc[k]
            cc[k] = (s_, x, max(y, min(x + 0.9, nxt)), zh_, en_)
        cuts = MANUAL_CUTS.get(sid, []) + (pauses(src, tin, tout) if kind == "anim" else [])
        cuts = sorted(c for c in cuts if not any(m[0] <= c[0] <= m[1] for m in MANUAL_CUTS.get(sid, []) if m != c))
        if cuts:
            squeeze[sid] = cuts
        hold = round(max(END_TOTAL - (tout - tin), 0.0), 2) if sid == "END" else 0.0
        shots.append((sid, kind, src, round(tin, 2), round(tout, 2), hold, mood,
                      find_beats(src, tin, tout, BEATS.get(sid, {}))))
        cues += [(s, round(x, 2), round(y, 2), zh, en) for s, x, y, zh, en in cc]
    print("SHOTS = [")
    for r in shots:
        print(f"    {r!r},")
    print("]\n\nCUES = [")
    for c in cues:
        print(f"    {c!r},")
    print("]\n\n# long pauses / false starts removed inside shots (source time)\nSQUEEZE = {")
    for k, v in squeeze.items():
        print(f"    {k!r}: {v!r},")
    print("}")


if __name__ == "__main__":
    main()
