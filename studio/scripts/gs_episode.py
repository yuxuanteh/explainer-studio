"""Episode pipeline: one tool for every episode and short.

Each piece has a code folder  <studio>/episodes/<EPISODE>/  (shorts: <studio>/shorts/<id>/)  containing
    edl.py       data only: music tracks, subtitle translations, corrections (see template)
    edl_auto.py  the automatic first cut written by gs_cut.py (sources, shots, subtitle cues)
its animation modules in  <studio>/web/ep/<EPISODE>/  (gs_web.py), and a synced folder
<project>/episodes/<EPISODE>/  (raw, work, preview, publish).

CLI (run with the studio venv):
    python gs_episode.py <EPISODE> timeline            print the shot timeline and beats
    python gs_episode.py <EPISODE> check               check every cut lands in silence (not mid-word)
    python gs_episode.py <EPISODE> render preview|final [shot ids...]
    python gs_episode.py <EPISODE> build  preview|final
    python gs_episode.py <EPISODE> mix                 audio mix only (music / voice checks)
    python gs_episode.py <EPISODE> srt                 rewrite work/subtitles.<lang>_<COUNTRY>.srt (+ publish/short/short.*.srt), no render
    python gs_episode.py <EPISODE> short preview|final 9:16 short: built from SHORT_SHOTS (written short, its own
                                                       narration) when edl.py has them, else cut from the latest build
    python gs_episode.py <EPISODE> timeline short      / check short: the same for the short's own timeline

Standalone shorts: ids s001-<slug> / ss001-<slug>, folders <project>/shorts/<id> + <studio>/shorts/<id>
(gs_env.ep_dir / code_dir); their edl.py has no SHOTS, only SHORT_SHOTS / SHORT_CUES. Use render + short; timeline and
check show the short's timeline. SHORT_CTA sets the bottom line (default points to the full version).

Written short (hybrid format): edl.py may hold SHORT_SHOTS (same rows as SHOTS, ids X01, X02 ...)
and SHORT_CUES (same rows as CUES), optional SHORT_SFX / SHORT_SCORE. They never enter the long-form build;
`render` renders them together with the main shots.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pedalboard as pb
import soundfile as sf

import gs_audio as A
import gs_env

MUSIC, SFXD = gs_env.BRAND / "music", gs_env.BRAND / "sfx"
MOOD_FILE = {"tense": "loop-tense.wav", "curious": "loop-curious.wav", "calm": "loop-calm.wav",
             "epic": "loop-epic.wav"}
QUALITY = {"preview": ("", "", 854, 480), "final": ("", "", 1920, 1080)}
# vertical written short (edl.SHORT_VERTICAL): portrait renders of the X shots, full 9:16 frame, no letterbox band
VQUALITY = {"preview": ("", "", 480, 854), "final": ("", "", 1080, 1920)}
# no animation engine installed (or `gs_run.py ... --no-anim`): plain cards where animation would go, no CG on camera
NO_ANIM = os.environ.get("GS_NO_ANIM") == "1" or not gs_env.cfg("components", "animation", True)
DEFAULT_CAM_GRADE = "eq=brightness=0.04:gamma=1.15:saturation=1.05"
CAM_AUDIO = "highpass=f=100,afftdn=nf=-48,equalizer=f=250:t=q:w=1:g=-2"
FPS = int(gs_env.cfg("video", "fps", 30))
# encoder of the 1080p master: libx264 works everywhere; a hardware encoder ([video] final_encoder) is faster
FINAL_ENCODER = list(gs_env.cfg("video", "final_encoder", ["-c:v", "libx264", "-preset", "slow", "-crf", "18"]))
# subtitle languages: the narration, then up to two translations ([language] subtitle_main / _second / _third)
SUB_LANGS = [gs_env.LANG.get("subtitle_main", gs_env.LANG.get("narration", "zh")), gs_env.LANG.get("subtitle_second", "en"),
             gs_env.LANG.get("subtitle_third", "")]
_F = gs_env.CFG.get("fonts", {})
SUB_FONT = _F.get("subtitle", "Noto Sans SC Medium" if gs_env.CJK else "Noto Sans Medium")
SUB_FONT_HEAVY = _F.get("subtitle_heavy", "Noto Sans SC Black" if gs_env.CJK else "Noto Sans Black")
# punch-in zoom that hides a cut inside a camera shot (alternate pieces); centre as a fraction of the frame, chosen so
# the crop stays inside the picture at this zoom ([video] cam_zoom_centre; default: face slightly right of centre)
CAM_ZOOM, CAM_ZOOM_CENTRE = 1.12, tuple(gs_env.cfg("video", "cam_zoom_centre", [0.55, 0.45]))


# =============================================================================== loading

def load(episode):
    """Load an episode's edl.py and attach derived paths."""
    code = gs_env.code_dir(episode)
    spec = importlib.util.spec_from_file_location(f"edl_{episode.replace('-', '_')}", code / "edl.py")
    E = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E)
    E.CODE_DIR = code
    # the automatic first cut (gs_cut.py) is used while edl.py holds no cut of its own; a hand-filled
    # edl.py always wins. edl.CUE_TEXT = {"自动字幕": "改后的字幕"} corrects subtitle texts without touching times.
    auto = code / "edl_auto.py"
    if auto.exists() and not getattr(E, "SHOTS", []) and not getattr(E, "SHORT_SHOTS", []):
        aspec = importlib.util.spec_from_file_location(f"edl_auto_{episode.replace('-', '_')}", auto)
        AU = importlib.util.module_from_spec(aspec)
        aspec.loader.exec_module(AU)
        fix = getattr(E, "CUE_TEXT", {})
        for name in ("SOURCES", "SHOTS", "CUES", "SHORT_SHOTS", "SHORT_CUES"):
            setattr(E, name, getattr(AU, name))
        for name in ("CUES", "SHORT_CUES"):
            setattr(E, name, [(s, a, b, fix.get(zh, zh), en) for s, a, b, zh, en in getattr(E, name)])
        E.SQUEEZE = {**AU.SQUEEZE, **getattr(E, "SQUEEZE", {})}
        E.AUTO_CUT = True
    if not hasattr(E, "SOURCES"):                  # no cut yet (before gs_cut.py has run)
        E.SOURCES = {}
    E.EP_DIR = gs_env.ep_dir(E.EPISODE)
    E.RAW = E.EP_DIR / "raw"
    E.RENDER = gs_env.RENDER / E.EPISODE
    E.SRC = {k: E.RAW / v for k, v in E.SOURCES.items()}
    for name, default in [("SFX", []), ("GOLD_TERMS", []), ("CAM_GRADE", DEFAULT_CAM_GRADE), ("SHORT", None),
                          ("EXT_AUDIO", {}), ("SQUEEZE", {}), ("TAIL_EXPANDER", "light"), ("SHORT_SHOTS", []),
                          ("SHORT_CUES", []), ("SHORT_SFX", []), ("SHORT_SCORE", None), ("JA", []),
                          ("SHORT_JA", []), ("CAM_FRAME", {}), ("SHORT_VERTICAL", False), ("ZOOM", {}),
                          ("VOICE_GAIN", {}), ("SHOTS", []), ("CUES", []),
                          ("SHORT_CTA", gs_env.CHANNEL.get("short_cta", "")), ("SCREEN", {}), ("SHORT_SRC", {}),
                          ("FOOTAGE", {}), ("SUB_THEME", None)]:
        if not hasattr(E, name):
            setattr(E, name, default)
    # a 9:16 short's camera take is filmed with the camera turned on its side (recording.md) and many cameras write no
    # rotation: a landscape clip with no CAM_FRAME of its own is turned upright (head to the right -> transpose=2). If a clip comes out upside down, set CAM_FRAME = {"camX01": "transpose=1"} in edl.py.
    if getattr(E, "AUTO_CUT", False) and E.SHORT_VERTICAL:
        for row in E.SHORT_SHOTS:
            if row[1] == "cam" and row[2] not in E.CAM_FRAME and E.SRC[row[2]].exists():
                r = subprocess.run([gs_env.FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", str(E.SRC[row[2]])], capture_output=True, text=True)
                wh = r.stdout.strip().split(",")
                if len(wh) >= 2 and int(wh[0]) > int(wh[1]):
                    E.CAM_FRAME[row[2]] = "transpose=2"
    apply_edit(E)
    # translations (step 6) keyed on the final Chinese subtitle, so they survive re-cuts and "/" splits:
    # edl.CUE_EN = {"中文字幕": "English"}, edl.CUE_JA = {"中文字幕": "日本語"}
    en_map, ja_map = getattr(E, "CUE_EN", {}), getattr(E, "CUE_JA", {})
    if en_map or ja_map:
        for name, jname in (("CUES", "JA"), ("SHORT_CUES", "SHORT_JA")):
            rows = getattr(E, name)
            setattr(E, name, [(s, a, b, zh, en_map.get(zh.strip(), en)) for s, a, b, zh, en in rows])
            if ja_map:
                setattr(E, jname, [ja_map.get(zh.strip(), "") for *_, zh, _en in rows])
    return E


def apply_edit(E):
    """The director's own edits from the editing page (gs_review.py, /edit): <episode>/work/edit.json =
    {"shots": {id: {"in", "out", "cut": [[a, b], ...]}}, "text": {subtitle before: subtitle after}}.
    Applied last, so they win over the automatic cut and over edl.py; gs_cut.py never touches the file
    (what the director corrects by ear is final). E.BASE keeps the state before those edits, for the page."""
    E.BASE = {"shots": {r[0]: [r[3], r[4], [list(c) for c in E.SQUEEZE.get(r[0], [])]] for r in list(E.SHOTS) + list(E.SHORT_SHOTS)},
              "CUES": [c[3] for c in E.CUES], "SHORT_CUES": [c[3] for c in E.SHORT_CUES]}
    E.SPLIT = {"CUES": list(range(len(E.CUES))), "SHORT_CUES": list(range(len(E.SHORT_CUES)))}
    ej = E.EP_DIR / "work" / "edit.json"
    E.EDIT = json.loads(ej.read_text(encoding="utf-8")) if ej.exists() else {}
    if not E.EDIT:
        return
    sh, tx = E.EDIT.get("shots", {}), dict(E.EDIT.get("text", {}))
    nk = lambda s: s.strip().rstrip(",， ").strip()                    # noqa: E731  a saved key still matches after the
    tx.update({nk(k): v for k, v in list(tx.items()) if nk(k) not in tx})    # automatic text lost its trailing comma
    for name, cname in (("SHOTS", "CUES"), ("SHORT_SHOTS", "SHORT_CUES")):
        rows, cs = [], [list(c) for c in getattr(E, cname)]
        for r in getattr(E, name):
            o = sh.get(r[0])
            if o and r[2]:
                tin, tout = float(o.get("in", r[3])), float(o.get("out", r[4]))
                if "cut" in o:
                    E.SQUEEZE[r[0]] = [(float(a), float(b)) for a, b in o["cut"]]
                for c in cs:                          # this shot's subtitles stay inside it
                    if c[0] == r[2] and r[3] - 0.01 <= c[1] <= r[4]:
                        c[1], c[2] = min(max(c[1], tin), tout), min(max(c[2], tin), tout)
                r = (r[0], r[1], r[2], tin, tout, *r[5:])
            rows.append(r)
        keep = [k for k, c in enumerate(cs) if c[2] - c[1] >= 0.05]
        setattr(E, name, rows)
        # "/" in a corrected subtitle splits it into subtitles shown one after another, each timed to the words said
        # (editing page). E.SPLIT keeps which pieces came from one subtitle, so the page can show
        # them joined again as "前半/后半".
        out, base, grp = [], [], []
        for k in keep:
            src, a, b, zh, en = cs[k][0], cs[k][1], cs[k][2], tx.get(cs[k][3], cs[k][3]), cs[k][4]
            parts = [p.strip() for p in zh.split("/") if p.strip()] if "/" in zh else [zh]
            times = split_times(E, src, a, b, parts) if len(parts) > 1 else [a, b]
            for i, p in enumerate(parts or [zh]):
                out.append((src, times[i], times[i + 1], p, en if i == 0 else ""))
                base.append(E.BASE[cname][k])
                grp.append(k)
        setattr(E, cname, out)
        E.BASE[cname] = base
        E.SPLIT[cname] = grp


def split_times(E, src, a, b, parts):
    """Times for the pieces of a subtitle split with "/": [a, t1, ..., b], each boundary placed where the last word of
    the piece before it ends in the recording (no-prompt transcript); by character count when the words cannot be
    matched (Whisper heard other characters). Every piece stays at least 0.4 s."""
    import difflib
    from gs_text import char_times, load_words, norm
    stem = Path(E.SOURCES[src]).name.split(".")[0]
    js = next((f for f in (E.EP_DIR / "work" / "noprompt" / f"{stem}.json", E.EP_DIR / "work" / f"{stem}.whisper.json")
               if f.exists()), None)
    lens = [len(norm(p)) or 1 for p in parts]
    full = norm("".join(parts))
    cum = [sum(lens[:i + 1]) for i in range(len(parts) - 1)]
    prop = [a + (b - a) * c / sum(lens) for c in cum]
    bounds = list(prop)
    if js:
        words = [w for w in load_words(js) if a - 0.3 <= (w[0] + w[1]) / 2 <= b + 0.3]
        said, t0 = char_times(words)
        t1 = [e for s, e, w, _ in words for _ in norm(w)]
        if said:
            pos = {}
            for blk in difflib.SequenceMatcher(None, full, said, autojunk=False).get_matching_blocks():
                for d in range(blk.size):
                    pos[blk.a + d] = blk.b + d
            for i, c in enumerate(cum):
                left = [pos[j] for j in range(c - 1, max(c - 4, -1), -1) if j in pos]
                right = [pos[j] for j in range(c, min(c + 3, len(full))) if j in pos]
                if left and right and left[0] < right[0]:
                    bounds[i] = (t1[left[0]] + t0[right[0]]) / 2
    t = [a] + bounds + [b]
    if any(t[i + 1] - t[i] < 0.4 for i in range(len(t) - 1)):   # a piece would flash by: fall back to the share by length
        t = [a] + prop + [b]
    return [round(x, 2) for x in t]


def short_edl(E):
    """The written short as an episode of its own: SHORT_SHOTS / SHORT_CUES on their own timeline."""
    S = SimpleNamespace(**{k: v for k, v in vars(E).items() if not k.startswith("__")})
    S.SHOTS, S.CUES, S.SFX, S.SCORE, S.JA = E.SHORT_SHOTS, E.SHORT_CUES, E.SHORT_SFX, E.SHORT_SCORE, E.SHORT_JA
    S.TRACKS = getattr(E, "SHORT_TRACKS", None)
    return S


# =============================================================================== timeline

def timeline(E):
    """Shots in order with timeline start/end; beats converted to shot-local seconds.

    SHOTS rows: (id, kind, source, in, out, hold, mood, beats)
      kind  : anim (animation, voice-over) | cam (camera + CG overlay) | foot (own footage + voice-over, edl.FOOTAGE)
              | intro | chapter | card (end screen)
      source: key of SOURCES whose audio plays (None = no speech, e.g. intro or a silent chapter card)
      in/out: seconds in the source; for silent shots in=0, out=duration
      hold  : extra seconds after `out` (picture keeps going, no speech)
    SQUEEZE = {shot id: [(a, b), ...]}: source ranges removed inside a shot (long pauses, false starts).
      Shot-local time skips them; beats and cues are mapped through `local()`.
    """
    t, out = 0.0, []
    for sid, kind, src, tin, tout, hold, mood, beats in E.SHOTS:
        cut = sorted((max(a, tin), min(b, tout)) for a, b in E.SQUEEZE.get(sid, []) if b > tin and a < tout)
        dur = tout - tin - sum(b - a for a, b in cut) + hold
        s = {"id": sid, "kind": kind, "src": src, "in": tin, "out": tout, "hold": hold, "mood": mood, "cut": cut,
             "start": t, "end": t + dur, "dur": dur}
        s["beats"] = {k: local(s, v) for k, v in beats.items()}
        out.append(s)
        t += dur
    return out


def local(s, t_src):
    """Source time -> shot-local seconds, skipping SQUEEZE ranges (a time inside a cut maps to its start)."""
    x = t_src - s["in"]
    for a, b in s.get("cut", []):
        if t_src >= b:
            x -= b - a
        elif t_src > a:
            x -= t_src - a
    return x


def pieces(s):
    """Source (start, end) pieces that make up a shot's speech after SQUEEZE."""
    out, cur = [], s["in"]
    for a, b in s.get("cut", []):
        out.append((cur, a))
        cur = b
    out.append((cur, s["out"]))
    return [(a, b) for a, b in out if b - a > 1e-3]


def shot(E, sid):
    for tl in (timeline(E), timeline(short_edl(E)) if E.SHORT_SHOTS else []):   # written-short shots (X01 ...) too
        for s in tl:
            if s["id"] == sid:
                return s
    raise KeyError(f"shot {sid} not in SHOTS or SHORT_SHOTS")


def cues(E):
    """Subtitle cues on the timeline: (start, end, zh, en, ja). Held 0.15 s, never overlapping the next cue.
    ja comes from JA (written short: SHORT_JA), a list in the same order as CUES; "" when there is none."""
    tl = timeline(E)
    ja = list(E.JA) if E.JA else [""] * len(E.CUES)
    if len(ja) != len(E.CUES):
        raise SystemExit(f"JA has {len(ja)} lines but CUES has {len(E.CUES)} - they must match one to one")
    res = []
    for (src, a, b, zh, en), jp in zip(E.CUES, ja):
        sh = next(s for s in tl if s["src"] == src and s["in"] - 0.01 <= a <= s["out"])
        res.append((sh["start"] + local(sh, a), sh["start"] + local(sh, min(b, sh["out"])), zh, en, jp))
    # a subtitle whose words were cut away on the editing page has no time left: drop it. A cue that ends before it
    # starts makes libass drop other events too (a whole title line once vanished that way)
    res = sorted(r for r in res if r[1] - r[0] >= 0.05)
    out = []
    for k, (a, b, zh, en, jp) in enumerate(res):
        nxt = res[k + 1][0] if k + 1 < len(res) else b + 1
        out.append((a, min(b + 0.15, nxt - 0.02), zh, en, jp))
    return out


# =============================================================================== audio helpers

def ff(*args, cwd=None):
    subprocess.run([gs_env.FFMPEG, "-v", "error", "-y", *map(str, args)], check=True, cwd=cwd)


def decode(path, t0=None, dur=None, af=None, channels=1, sr=A.SR):
    args = [gs_env.FFMPEG, "-v", "error"]
    if t0 is not None:
        args += ["-ss", f"{t0:.3f}"]
    if dur is not None:
        args += ["-t", f"{dur:.3f}"]
    args += ["-i", str(path), "-map", "0:a:0", "-ac", str(channels), "-ar", str(sr)]
    if af:
        args += ["-af", af]
    args += ["-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(args, capture_output=True, check=True).stdout, np.float32)
    return x.reshape(-1, channels).T if channels > 1 else x


def loudnorm_linear(wav, target=-14.0, tp=-1.5):
    """Two-pass EBU R128: measure, then apply one constant gain (linear=true) - no dynamic pumping."""
    import json
    r = subprocess.run([gs_env.FFMPEG, "-hide_banner", "-nostats", "-i", str(wav), "-af",
                        f"loudnorm=I={target}:TP={tp}:LRA=20:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    # + a safety limiter at -2 dBFS after the constant gain: the mix is peak-normalised to 0 dBFS, and an encode can
    # still land a transient above the -1.5 dBTP master rule (seen: +0.8 dBTP in a 1080p master whose preview read -3.1).
    return (f"loudnorm=I={target}:TP={tp}:LRA=20:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
            f"aresample=48000,alimiter=limit=0.79:attack=1:release=50:level=false")


TAIL_PRESETS = {"off": None, "light": (10, 3.5, 10), "strong": (8, 4.0, 18)}   # (dB below speech, ratio, max cut dB)


def expand_tails(x, below=10, ratio=3.5, rng_db=10, att=0.003, rel=0.08):
    """Downward expander for the room tail at sentence ends. Loudness normalisation raises a quiet phone
    recording by ~7 dB and the room echo with it (director: 'reverb at the end of the sentence'); below
    (speech level - `below` dB) the level falls `ratio` x faster, at most `rng_db`. Speech itself is untouched."""
    win = int(0.01 * A.SR)
    edb = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(win) / win, "same")) + 1e-9)
    thr = np.percentile(edb[edb > -60], 90) - below
    gdb = np.where(edb < thr, np.maximum((edb - thr) * (ratio - 1), -rng_db), 0.0)
    # tails only, never onsets: a soft first syllable at the start of a sentence sits below the threshold
    # too and was pushed down, then the voice "swelled up". No cut where speech above the
    # threshold follows within `look` seconds (sliding max over the next window, computed in 10 ms blocks).
    look, blk = 0.35, win
    nb = len(edb) // blk + 1
    loud = np.zeros(nb, bool)
    above = edb >= thr
    for k in range(nb):
        loud[k] = above[k * blk:(k + 1) * blk].any()
    ahead = np.zeros(nb, bool)
    m = int(look / 0.01)
    for k in range(nb):
        ahead[k] = loud[k:k + m + 1].any()
    gdb[np.repeat(ahead, blk)[:len(gdb)]] = 0.0
    g = np.empty_like(gdb)
    aa, ar, cur = np.exp(-1 / (att * A.SR)), np.exp(-1 / (rel * A.SR)), 0.0
    for i, v in enumerate(gdb):
        a = aa if v > cur else ar
        cur = a * cur + (1 - a) * v
        g[i] = cur
    return (x * 10 ** (g / 20)).astype(np.float32)


def speech_src(E, s):
    """(audio file, offset) for a shot's speech. Camera shots may use a separately recorded phone track:
    EXT_AUDIO = {"camS01": ("cam-S01.m4a", 4.673)} - the phone started 4.673 s after the camera, so
    phone time = camera time - 4.673. Shot in/out stay in camera time."""
    ext = E.EXT_AUDIO.get(s["src"])
    if ext:
        return E.RAW / ext[0], ext[1]
    return E.SRC[s["src"]], 0.0


def voice_gain(E, sid, x, t_src):
    """edl.VOICE_GAIN = {shot: [(a, b, dB)]} (source time): lift / lower a phrase that was spoken softer or louder
    than the rest (one phrase about 8 dB quieter than the rest sounds suppressed).
    0.15 s ramps at both ends."""
    spans = E.VOICE_GAIN.get(sid)
    if not spans:
        return x
    t = t_src + np.arange(len(x)) / A.SR
    g = np.zeros(len(x))
    for a, b, db in spans:
        g = np.maximum(g, db * np.clip(np.minimum((t - a) / 0.15 + 1, (b - t) / 0.15 + 1), 0, 1)) if db > 0 else             np.minimum(g, db * np.clip(np.minimum((t - a) / 0.15 + 1, (b - t) / 0.15 + 1), 0, 1))
    return (x * 10 ** (g / 20)).astype(np.float32)


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-12))


def db(x):
    return 20 * np.log10(rms(x) + 1e-9)


def duck_curve(speech, depth_db=-11, attack=0.03, release=0.45, rate=1000):
    """Music gain under speech. Envelope follower runs at `rate` Hz and is interpolated (fast for long videos)."""
    hop = A.SR // rate
    n = len(speech) // hop
    env = np.abs(speech[:n * hop]).reshape(n, hop).mean(1)
    env = np.convolve(env, np.ones(20) / 20, mode="same")
    on = (env > 0.01).astype(np.float64)
    a_up, a_dn = np.exp(-1 / (attack * rate)), np.exp(-1 / (release * rate))
    g, y = np.empty(n), 0.0
    for k in range(n):
        c = a_up if on[k] > y else a_dn
        y = c * y + (1 - c) * on[k]
        g[k] = y
    full = np.interp(np.arange(len(speech)) / hop, np.arange(n), g)
    return (10 ** (depth_db * full / 20)).astype(np.float32)


# =============================================================================== checks

def check_cuts(E, speech_db=-35.0):
    """Report cuts where speech is still going (Whisper often ends words early)."""
    problems = []
    cache = {}
    for s in timeline(E):
        if not s["src"]:
            continue
        path, lag = speech_src(E, s)
        x = cache.setdefault(s["src"], decode(path, channels=1, sr=16000))
        lvl = lambda t: db(x[int(max(t - lag, 0) * 16000):int(max(t - lag + 0.1, 0) * 16000)])  # noqa: E731
        head, tail = lvl(s["in"]), max(lvl(s["out"]), lvl(s["out"] + 0.1))
        flag, note = [], ""
        mine = s["id"] in getattr(E, "EDIT", {}).get("shots", {})
        before = db(x[int(max(s["in"] - lag - 0.06, 0) * 16000):int(max(s["in"] - lag, 0) * 16000)])
        if head > speech_db and mine and before <= speech_db - 10:
            # the director's own start on the editing page, set tight on the first word but still before it (often
            # 0.02-0.07 s before the voice): their ear decides, so only a warning
            note = f"  ~ your start sits right on the first word (quiet just before: {before:.0f} dB): listen that it is not clipped"
        elif head > speech_db:
            flag.append(f"in {s['in']:.2f}s cuts into speech ({head:.0f} dB)")
        if tail > speech_db:
            flag.append(f"out {s['out']:.2f}s cuts speech off ({tail:.0f} dB) -> move later")
        print(f"{s['id']:8s} in {s['in']:7.2f} ({head:5.1f} dB)  out {s['out']:7.2f} (after {tail:5.1f} dB)  "
              + ("  !! " + "; ".join(flag) if flag else "ok" + note))
        problems += flag
    return problems


# =============================================================================== render

def is_web(E):
    """Every piece is drawn by the web engine (render(t) pages, gs_web.py)."""
    return True


def anim_src(E, sid, folder, mode):
    """Rendered picture of a full-screen shot (anim / chapter / card)."""
    import gs_web
    return gs_web.out(E, mode, sid)


def anim_in(E, s, folder, mode, W, H):
    """ffmpeg input of a full-screen shot: its rendered animation, or (NO_ANIM) a plain card with the words said."""
    if not NO_ANIM:
        return ["-i", anim_src(E, s["id"], folder, mode)]
    import gs_cut
    import gs_voicecut
    d = E.RENDER / "cards"
    d.mkdir(parents=True, exist_ok=True)
    png = d / f"{s['id']}-{W}x{H}.png"
    words = {sid: " ".join(lines) for sid, _, lines in gs_cut.script(E.EPISODE)}
    gs_voicecut.card(png, W, H, s["id"], s["kind"], words.get(s["id"], ""))
    return ["-loop", "1", "-framerate", FPS, "-t", f"{s['dur'] + 1:.3f}", "-i", png]


def cg_overlay(E, sid, folder, mode, W, H, first=1):
    """Camera CG as ffmpeg inputs + a filter chain ending in [cg] + the overlay alpha option.
    A colour pass rendered on black (= premultiplied) + a white-on-black matte."""
    tail = f"scale={W}:{H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration=2"
    if NO_ANIM:
        return [], f"color=c=black@0.0:s={W}x{H}:r={FPS},format=rgba[cg]", ""
    import gs_web
    return (["-i", gs_web.out(E, mode, sid), "-i", gs_web.out(E, mode, sid, matte=True)],
                f"[{first}:v]{tail},format=rgba[cgc];[{first + 1}:v]{tail},format=gray[cgm];[cgc][cgm]alphamerge[cg]",
                ":alpha=premultiplied")


def render(E, mode, only=()):
    """Render the shots (one MP4 each) with the web engine."""
    if NO_ANIM:
        return print("no animation engine: nothing to render")
    import gs_web
    return gs_web.render(E, mode, only)


# =============================================================================== build

def build(E, mode, audio_only=False, B=None, finish=True):
    q, folder, W, H = QUALITY[mode]
    folder = folder if mode == "preview" else "1080p30"
    B = B or E.RENDER / f"build-{mode}"
    (B / "fonts").mkdir(parents=True, exist_ok=True)
    for f in theme_fonts(E):
        shutil.copy(gs_env.FONTS / f, B / "fonts")
    tl = timeline(E)

    # ---- video: one normalised clip per shot, then concat
    if audio_only:                                 # `mix` command: rebuild only mix.wav (fast checks of music / voice)
        return _mix(E, B, tl)
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an"]
    norm = f"scale={W}:{H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration=2"
    clips = []
    for s in tl:
        out, dur = B / f"{s['id']}.mp4", f"{s['dur']:.3f}"
        if s["kind"] in ("anim", "chapter", "card"):
            ff(*anim_in(E, s, folder, mode, W, H), "-vf", norm, "-t", dur, *enc, out)
        elif s["kind"] == "intro":
            ff(*anim_in(E, s, folder, mode, W, H), "-vf", norm, "-t", dur, *enc, out)
        elif s["kind"] == "foot":
            # the director's own footage under a voice-over: edl.FOOTAGE = {shot: (file, start, filters)}.
            # No CAM_GRADE: it is not the studio camera, and the director's footage gets no extra colour work.
            f, t0, extra = E.FOOTAGE[s["id"]]
            ff("-ss", f"{t0:.3f}", "-i", f, "-vf",
               f"{extra + ',' if extra else ''}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
               f"fps={FPS},tpad=stop_mode=clone:stop_duration=30", "-t", dur, *enc, out)
        elif s["kind"] == "cam":
            cg_in, cg_chain, cg_alpha = cg_overlay(E, s["id"], folder, mode, W, H)
            # CAM_FRAME: ffmpeg filters run first on a clip shot another way, e.g. a phone-style portrait take stored
            # sideways: {"camX01": "transpose=2,crop=1080:608:0:300"} (rotate upright, crop a 16:9 window on the face)
            pre = E.CAM_FRAME.get(s["src"], "")
            src_in = ["-ss", f"{s['in']:.3f}", "-t", dur, "-i", E.SRC[s["src"]]]
            if s["cut"] or s["id"] in E.ZOOM:
                # cuts inside a camera shot (pauses the director asked out): punch-in zoom so the jump reads as an
                # intentional zoom (zoom is robust in ffmpeg,
                # morph-style keyframing is not). Default: every other piece zoomed. edl.ZOOM = {shot: [(a, b, z)]}
                # (source time) sets the zoomed spans explicitly, e.g. zoom in at the cut and back out on a later
                # phrase; a cut inside a span changes the zoom level instead.
                spans = E.ZOOM.get(s["id"])
                sub = []
                for k, (a, b) in enumerate(pieces(s)):
                    if spans is None:
                        sub.append((a, b, CAM_ZOOM if k % 2 else 1.0))
                        continue
                    edges = sorted({a, b, *[t for x, y, _ in spans for t in (x, y) if a < t < b]})
                    for p, q in zip(edges[:-1], edges[1:]):
                        m = (p + q) / 2
                        sub.append((p, q, next((z_ for x, y, z_ in spans if x <= m < y), 1.0)))
                parts = []
                for k, (a, b, z) in enumerate(sub):
                    zf = (f",crop=iw/{z}:ih/{z}:iw*{CAM_ZOOM_CENTRE[0]}-iw/{z}/2:ih*{CAM_ZOOM_CENTRE[1]}-ih/{z}/2"
                          if z != 1.0 else "")
                    pf = B / f"{s['id']}-p{k}.mp4"
                    ff("-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", E.SRC[s["src"]], "-vf",
                       f"{pre + ',' if pre else ''}{E.CAM_GRADE}{zf},scale={W}:{H}:flags=lanczos,fps={FPS}",
                       *enc, pf)
                    parts.append(pf)
                (B / f"{s['id']}-parts.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in parts),
                                                        encoding="utf-8")
                ff("-f", "concat", "-safe", "0", "-i", B / f"{s['id']}-parts.txt", "-c", "copy", B / f"{s['id']}-cam.mp4")
                src_in, pre_chain = ["-i", B / f"{s['id']}-cam.mp4"], "null"
            else:
                pre_chain = f"{pre + ',' if pre else ''}{E.CAM_GRADE},scale={W}:{H}:flags=lanczos,fps={FPS}"
            ff(*src_in, *cg_in, "-filter_complex",
               f"[0:v]{pre_chain}[cam];{cg_chain};"
               f"[cam][cg]overlay=0:0:shortest=0{cg_alpha}[v]", "-map", "[v]", "-t", dur, *enc, out)
        clips.append(out)
    (B / "concat.txt").write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    ff("-f", "concat", "-safe", "0", "-i", B / "concat.txt", "-c", "copy", B / "video.mp4")
    _mix(E, B, tl)
    if finish:
        _finish(E, B, tl, mode, W, H)


def _mix(E, B, tl):
    # ---- audio
    n = int((tl[-1]["end"] + 0.5) * A.SR)
    speech = np.zeros(n, np.float32)
    voice_ref = None
    for s in tl:
        if not s["src"]:
            continue
        is_cam = s["kind"] == "cam"
        path, lag = speech_src(E, s)
        phone = s["src"] in E.EXT_AUDIO
        af = CAM_AUDIO if is_cam and not phone else "highpass=f=80"   # phone tracks are clean: voice filter only
        x = np.concatenate([A.fade(voice_gain(E, s["id"], decode(path, a - lag, b - a, af=af), a)[None],
                                   fin=0.015, fout=0.03)[0] for a, b in pieces(s)])
        x = A.fade(x[None], fin=0.02, fout=0.06)[0]
        if is_cam:
            s["_raw"] = x
        elif voice_ref is None:
            voice_ref = rms(x[np.abs(x) > 0.02])
        i = int(s["start"] * A.SR)
        speech[i:i + len(x)] += x[:n - i]
    for s in tl:                                   # camera mic level-matched to the voice recording
        if "_raw" in s and voice_ref:
            i, j = int(s["start"] * A.SR), int(s["end"] * A.SR)
            seg = speech[i:j]
            speech[i:j] = seg * (voice_ref / rms(seg[np.abs(seg) > 0.02]))
    preset = TAIL_PRESETS[E.TAIL_EXPANDER]
    if preset:
        speech = expand_tails(speech, *preset)
    # gentle voice chain (the old 3:1 compressor + master compressor + dynamic loudnorm made
    # the room echo and breaths pump up - "hard and painful"): one light compressor, a touch less 6.5 kHz edge
    speech = pb.Pedalboard([pb.Compressor(threshold_db=-20, ratio=1.6, attack_ms=15, release_ms=150),
                            pb.HighShelfFilter(cutoff_frequency_hz=6500, gain_db=-2.0)])(speech[None], A.SR)[0]
    duck = duck_curve(speech)

    bed = np.zeros((2, n), np.float32)
    runs = []
    # mood loops and stings belong to the programmed score ([music] mode = "score", made by make_music.py)
    legacy = gs_env.cfg("music", "mode", "library") == "score" and (MUSIC / "intro-sting.wav").exists()
    for s in (tl if legacy else []):
        if s["mood"] in MOOD_FILE and runs and runs[-1][0] == s["mood"] and abs(runs[-1][2] - s["start"]) < 1e-6:
            runs[-1][2] = s["end"]
        elif s["mood"] in MOOD_FILE:
            runs.append([s["mood"], s["start"], s["end"]])
    if getattr(E, "SCORE", None):                  # through-composed score per section (gs_score.py)
        import gs_score
        bed += gs_score.render(E.SCORE, tl, n)
        runs = []
    for mood, a, b in runs:
        loop = sf.read(str(MUSIC / MOOD_FILE[mood]))[0].T
        length = int((b - a + 0.8) * A.SR)
        tiled = A.fade(np.tile(loop, (1, length // loop.shape[1] + 2))[:, :length], fin=0.4, fout=0.8)
        i = int(max(a - 0.2, 0) * A.SR)
        j = min(i + tiled.shape[1], n)
        bed[:, i:j] += tiled[:, :j - i]
    if not getattr(E, "MUSIC", True):              # edl.MUSIC = False: animation preview before the score is approved
        bed[:] = 0
    bed *= 10 ** (-9 / 20) * duck
    # library tracks (audio.md): edl.TRACKS = [(first shot, "Title"), ...] replaces the programmed
    # score and the stings. Music sits 18 dB under the speech level while someone talks and rises 7 dB in pauses.
    tracks = None if getattr(E, "VOICECUT", False) else getattr(E, "TRACKS", None)
    if tracks:
        import gs_tracks
        rep = []
        m = gs_tracks.render(tracks, {s["id"]: s["start"] for s in tl}, tl[-1]["end"], n / A.SR, report=rep)
        m = np.pad(m, ((0, max(0, n - len(m))), (0, 0)))[:n].T
        v0 = speech[np.abs(speech) > 0.01]
        s_db = 20 * np.log10(np.sqrt(np.mean(v0 ** 2)) + 1e-9) if v0.size else -19.0
        bed = (m * 10 ** ((s_db - 11.0 - gs_tracks.TARGET_RMS_DB) / 20) * duck_curve(speech, depth_db=-7)).astype(np.float32)
        (B / "music-plan.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")
        A.write(B / "music-only.wav", bed)
        print("music:", "; ".join(rep))

    def place(buf, wav, t, gain_db, ducked=False):
        x = sf.read(str(wav))[0].T
        i = int(t * A.SR)
        k = min(x.shape[1], n - i)
        g = 10 ** (gain_db / 20) * (duck[i:i + k] if ducked else 1)
        buf[:, i:i + k] += x[:, :k] * g

    stings = np.zeros((2, n), np.float32)
    for s in (tl if legacy and getattr(E, "MUSIC", True) and not getattr(E, "VOICECUT", False) and not tracks else []):
        if s["kind"] == "intro":
            place(stings, MUSIC / "intro-sting.wav", s["start"], -3)
        if s["kind"] == "card":                    # end screen: outro sting, then a soft calm bed fading out
            place(stings, MUSIC / "outro-sting.wav", s["start"], -10, ducked=True)
            calm = sf.read(str(MUSIC / "loop-calm.wav"))[0].T
            j0 = int((s["start"] + 4.5) * A.SR)
            j1 = int(s["end"] * A.SR)
            tail = A.fade(np.tile(calm, (1, (j1 - j0) // calm.shape[1] + 2))[:, :j1 - j0], fin=1.5, fout=2.5)
            stings[:, j0:j1] += tail * 10 ** (-14 / 20) * duck[j0:j1]
    fx = np.zeros((2, n), np.float32)
    for sid, when, name, gain in E.SFX:
        s = next(q for q in tl if q["id"] == sid)
        place(fx, (E.EP_DIR / name) if "/" in name else SFXD / f"{name}.wav", s["start"] + (s["beats"][when] if isinstance(when, str) else when), gain)
    mix = np.vstack([speech, speech]) + bed + stings + fx            # no glue compressor on the speech
    voiced = speech[np.abs(speech) > 0.01]
    if voiced.size:                                # no speech at all (a short with no narration): keep the music level
        mix = mix * (10 ** (-19 / 20) / (np.sqrt(np.mean(voiced ** 2)) + 1e-9))   # speech ~ -19 dBFS RMS
    mix = pb.Pedalboard([pb.Limiter(threshold_db=-4.0, release_ms=60)])(mix.astype(np.float32), A.SR)
    # (peaks only; the final two-pass linear loudnorm then adds one constant gain to -14 LUFS)
    A.write(B / "mix.wav", mix)
    return B / "mix.wav"


def _finish(E, B, tl, mode, W, H):
    # ---- subtitles (A on animation, B on camera footage) + SRTs
    cam_spans = [(s["start"], s["end"]) for s in tl if s["kind"] in ("cam", "foot")]   # style B on any footage
    head = themed(E, ass_head())
    lines = []
    cs = cues(E)
    for a, b, zh, *_ in cs:
        if any(x <= a < y for x, y in cam_spans):
            # style B = text on a translucent box. libass draws one box per colour run, so a gold term next to
            # white text left a darker overlap bar. Box on layer 0 from the plain line
            # (one run, glyphs invisible), coloured text on layer 1 without a box.
            lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},B,,0,0,0,,{{\\1a&HFF&}}{zh}")
            lines.append(f"Dialogue: 1,{ass_time(a)},{ass_time(b)},Btext,,0,0,0,,{gold(E, zh)}")
        else:
            lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},A,,0,0,0,,{gold(E, zh)}")
    head = head.rstrip() + "\n"
    if "Style: Btext" not in head:            # B's text without the box, same font / size / position
        bline = next(x for x in head.splitlines() if x.startswith("Style: B,"))
        f = bline.split(",")
        f[0], f[15], f[16], f[17] = "Style: Btext", "1", "0", "0"      # BorderStyle 1, no outline, no shadow
        head = head.replace(bline, bline + "\n" + ",".join(f))
    (B / "subs.ass").write_text(head + "\n".join(lines) + "\n", encoding="utf-8")
    write_srts(E, cs)

    # ---- final mux
    outdir = E.EP_DIR / ("preview" if mode == "preview" else "publish")
    outdir.mkdir(exist_ok=True)
    out = outdir / (f"{E.EPISODE}-rough-480p.mp4" if mode == "preview" else f"{E.EPISODE}-1080p.mp4")
    venc = ["-c:v", "libx264", "-preset", "medium", "-crf", "20"] if mode == "preview" else \
        FINAL_ENCODER
    ff("-i", "video.mp4", "-i", "mix.wav", "-vf", "subtitles=subs.ass:fontsdir=fonts", *venc, "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-af", loudnorm_linear(B / "mix.wav", -14), "-shortest", "-movflags", "+faststart",
       out, cwd=B)
    if mode == "preview":
        review_timeline(E, f"{E.EPISODE}-480p", out, tl, cs, False)
    print(out)
    return out


def review_timeline(E, name, video, tl, cs, vertical):
    """work/review/<name>.timeline.json: lists this video on the review page with its shots and subtitles, so notes
    left on the 480p carry the shot and the line (the voice cut writes the same file)."""
    rv = E.EP_DIR / "work" / "review"
    rv.mkdir(parents=True, exist_ok=True)
    (rv / f"{name}.timeline.json").write_text(json.dumps({
        "id": E.EPISODE, "name": name, "file": Path(video).name, "total": round(tl[-1]["end"], 3), "vertical": vertical,
        "shots": [{"id": s["id"], "kind": s["kind"], "t": round(s["start"], 3), "d": round(s["dur"], 3), "src": s["src"],
                   "in": s["in"], "out": s["out"], "cut": s["cut"]} for s in tl],
        "subs": [{"s": round(a, 3), "e": round(b, 3), "text": zh} for a, b, zh, *_ in cs]}, ensure_ascii=False, indent=1),
        encoding="utf-8")


def write_srts(E, cs=None, folder=None, prefix=""):
    """work/subtitles.<lang>_<COUNTRY>.srt, one per subtitle language (gs_env.srt_name), from CUES (also `gs_episode.py <EP> srt`: subtitle text
    changes need no re-render). The short uses folder=publish/short, prefix="short-"."""
    cs = cues(E) if cs is None else cs
    folder = folder or E.EP_DIR / "work"
    folder.mkdir(parents=True, exist_ok=True)
    for lang, k in [(SUB_LANGS[0], 2), (SUB_LANGS[1], 3), (SUB_LANGS[2], 4)]:
        if not lang or not any(c[k] for c in cs):
            continue
        srt = "\n".join(f"{i}\n{srt_time(c[0])} --> {srt_time(c[1])}\n{c[k]}\n" for i, c in enumerate(cs, 1))
        (folder / gs_env.srt_name(lang, short=bool(prefix))).write_text(srt, encoding="utf-8")


def gold(E, text):
    colour = sub_theme(E).get("term", "&H0DB9F2&")
    for term in E.GOLD_TERMS:
        text = text.replace(term, "{\\c" + colour + "}" + term + "{\\r}")
    return text


# Subtitles follow the animation style: edl.SUB_THEME = "<style id>" picks
# brand/templates/subtitles/<id>.json, which overrides fields of the ASS style lines (long video A / B, short Sub /
# Title / Title2 / Src / CTA) and the English-term colour. No theme = the channel default look, unchanged.
ASS_FIELDS = ["Name", "Fontname", "Fontsize", "PrimaryColour", "SecondaryColour", "OutlineColour", "BackColour", "Bold",
              "Italic", "Underline", "StrikeOut", "ScaleX", "ScaleY", "Spacing", "Angle", "BorderStyle", "Outline",
              "Shadow", "Alignment", "MarginL", "MarginR", "MarginV", "Encoding"]


def _ass(hex_, alpha=0):
    """#RRGGBB -> ASS &HAABBGGRR."""
    h = hex_.lstrip("#")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper().replace("&H", "&H")


def sub_theme(E):
    """The subtitle look of a piece's house style: a hand-made <style>.json (the channel's brand/subtitles/ or the
    studio's templates/subtitles/), else derived from the style's colours in web/kit/themes.json; {} = default look."""
    sid = getattr(E, "SUB_THEME", None) or getattr(E, "CARD_THEME", None) or gs_env.cfg("style", "house", "")
    if not sid:
        return {}
    for f in (gs_env.BRAND / "subtitles" / f"{sid}.json", gs_env.STUDIO / "templates" / "subtitles" / f"{sid}.json"):
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    tf = gs_env.WEB / "kit" / "themes.json"
    T = (json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else {}).get(sid)
    if not isinstance(T, dict):
        return {}
    text, back, acc, muted = T["text"], T["bg2"], T["accent"], T["muted"]
    lum = sum(int(back.lstrip("#")[k:k + 2], 16) * w for k, w in ((0, 0.299), (2, 0.587), (4, 0.114))) / 255
    edge = 4 if lum < 0.5 else 9                       # a light ground needs a wide light backing behind dark text
    line = {"PrimaryColour": _ass(text), "SecondaryColour": _ass(text), "OutlineColour": _ass(back), "BackColour": _ass(back, 0x14),
            "BorderStyle": 1, "Outline": edge, "Shadow": 0}
    box = {**line, "OutlineColour": _ass(back, 0x14), "BorderStyle": 3, "Outline": 12}
    head = {"PrimaryColour": _ass(text), "SecondaryColour": _ass(text), "OutlineColour": _ass(back), "BackColour": _ass(back)}
    return {"term": _ass(acc) + "&", "styles": {
        "A": line, "B": box, "Sub": line, "Title": head,
        "Title2": {**head, "PrimaryColour": _ass(acc), "SecondaryColour": _ass(acc)},
        "CTA": {**head, "PrimaryColour": _ass(muted), "SecondaryColour": _ass(muted)},
        "Src": {**head, "PrimaryColour": _ass(muted), "SecondaryColour": _ass(muted), "BackColour": _ass(back, 0x80)}}}


def themed(E, head):
    """Apply the style's subtitle theme to an ASS header (style lines only)."""
    styles = sub_theme(E).get("styles", {})
    out = []
    for line in head.splitlines():
        if line.startswith("Style: "):
            f = line[7:].split(",")
            for k, v in styles.get(f[0], {}).items():
                f[ASS_FIELDS.index(k)] = str(v)
            line = "Style: " + ",".join(f)
        out.append(line)
    return "\n".join(out) + "\n"


def theme_fonts(E):
    return gs_env.subtitle_fonts() + sub_theme(E).get("fonts", [])


def ass_head():
    """The long video's subtitle styles: <project>/brand/subtitle-styles.ass when the channel has its own, else the
    studio template; the font names come from studio.toml."""
    f = next((p for p in (gs_env.BRAND / "subtitle-styles.ass", gs_env.STUDIO / "templates" / "subtitle-styles.ass") if p.exists()))
    return f.read_text(encoding="utf-8").replace("{{SUB_FONT}}", SUB_FONT).replace("{{SUB_FONT_HEAVY}}", SUB_FONT_HEAVY)


def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# =============================================================================== 9:16 short

SHORT_ASS_HEAD = ("""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Noto Sans SC Black,96,&H00E8F1F5,&H00E8F1F5,&H00081013,&H00081013,0,0,0,0,100,100,2,0,1,5,0,8,60,60,0,1
Style: Title2,Noto Sans SC Black,84,&H000DB9F2,&H000DB9F2,&H00081013,&H00081013,0,0,0,0,100,100,2,0,1,5,0,8,60,60,0,1
Style: Sub,Noto Sans SC Medium,66,&H00E8F1F5,&H00E8F1F5,&H00081013,&H80081013,0,0,0,0,100,100,1,0,1,4,2,8,70,70,0,1
Style: CTA,Noto Sans SC Medium,44,&H0090BCCB,&H0090BCCB,&H00081013,&H00081013,0,0,0,0,100,100,1,0,1,2,0,2,60,60,150,1
Style: Src,Noto Sans SC Medium,26,&H00B2A3C2,&H00B2A3C2,&H00081013,&H80081013,0,0,0,0,100,100,0,0,1,2,0,5,40,40,0,1
Style: Sim,Noto Sans SC Black,150,&H00FFFFFF,&H00FFFFFF,&H000000C8,&H000000C8,-1,0,0,0,100,100,6,0,3,22,0,5,40,40,0,1
Style: Sim2,Noto Sans SC Black,62,&H00FFFFFF,&H00FFFFFF,&H000000C8,&H000000C8,-1,0,0,0,100,100,2,0,3,14,0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""").replace("Noto Sans SC Black", SUB_FONT_HEAVY).replace("Noto Sans SC Medium", SUB_FONT)


def short_segments(E):
    """Timeline (start, end) ranges of the backup short cut from the long video (SHORT["segments"])."""
    def at(ref, edge):           # "S03" -> shot start / end; "S01@18.75" -> 18.75 s into S01 (cut inside a shot)
        sid, _, sec = ref.partition("@")
        return shot(E, sid)["start"] + float(sec) if sec else shot(E, sid)[edge]
    return [(at(a, "start"), at(b, "end")) for a, b in E.SHORT["segments"]]


def short_cues(E, segs, cs):
    """Long-video cues re-timed onto the cut short (for its own SRT tracks)."""
    out, off = [], 0.0
    for a, b in segs:
        out += [(off + ca - a, off + min(cb, b) - a, *rest) for ca, cb, *rest in cs if a - 0.01 <= ca < b]
        off += b - a
    return out


def short(E, mode="preview"):
    """Title band on top, the 16:9 video in the middle, big subtitles under it, channel CTA at the bottom.

    With SHORT_SHOTS (written short): builds the short's own 16:9 video + mix in build-short-<mode>/ and uses all of
    it. Both ways write publish/short/short.<lang>_<COUNTRY>.srt for the subtitle tracks.
    Without: cuts SHORT["segments"] out of the latest long-form build (old way, kept as a backup)."""
    cfg = E.SHORT
    out = E.EP_DIR / "publish" / "short"
    out.mkdir(parents=True, exist_ok=True)
    if E.SHORT_SHOTS and E.SHORT_VERTICAL:
        return short_vertical(E, mode, out)
    if E.SHORT_SHOTS:
        S = short_edl(E)
        B = E.RENDER / f"build-short-{mode}"
        build(S, mode, B=B, finish=False)          # video.mp4 + mix.wav (and fonts/) in B, no 16:9 master
        segs = [(0.0, timeline(S)[-1]["end"])]
        cs = cues(S)
        write_srts(S, cs, folder=out, prefix="short-")
    else:
        B = E.RENDER / f"build-{mode}"
        segs = short_segments(E)
        cs = cues(E)
        write_srts(E, short_cues(E, segs, cs), folder=out, prefix="short-")
    total = sum(b - a for a, b in segs)
    ev = [f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title,,0,0,0,,{{\\pos(540,230)}}{cfg['title'][0]}",
          f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title2,,0,0,0,,{{\\pos(540,360)}}{cfg['title'][1]}",
          f"Dialogue: 0,{ass_time(0)},{ass_time(total)},CTA,,0,0,0,,{E.SHORT_CTA}"]
    off = 0.0
    for a, b in segs:
        for ca, cb, zh, *_ in cs:
            if a - 0.01 <= ca < b:
                ev.append(f"Dialogue: 0,{ass_time(off + ca - a)},{ass_time(off + min(cb, b) - a)},Sub,,0,0,0,,"
                          f"{{\\pos(540,1330)}}{gold(E, zh)}")
        off += b - a
    (B / "short.ass").write_text(themed(E, SHORT_ASS_HEAD) + "\n".join(ev) + "\n", encoding="utf-8")
    x, sr = sf.read(str(B / "mix.wav"))
    y = np.concatenate([A.fade(x[int(a * sr):int(b * sr)].T, fin=0.05, fout=0.08) for a, b in segs], axis=1)
    A.write(B / "short.wav", A.fade(y, fout=0.8))
    # one input per segment: video.mp4 comes from the concat demuxer and trim= in a filtergraph drops segment 1
    inputs = []
    for a, b in segs:
        inputs += ["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", "video.mp4"]
    k = len(segs)
    logo = gs_env.PROJECT / gs_env.CHANNEL.get("logo_watermark", "brand/logo/watermark.png")
    band = gs_env.CFG.get("palette", {}).get("bg_deep", "#131008").lstrip("#")
    ff(*inputs, "-i", "short.wav", *(["-i", logo] if logo.exists() else []), "-filter_complex",
       "".join(f"[{i}:v]" for i in range(k)) + f"concat=n={k}:v=1:a=0[cv];"
       f"[cv]scale=1080:608:flags=lanczos,pad=1080:1920:0:560:color=0x{band}[pv];"
       + (f"[{k + 1}:v]scale=110:110[lg];[pv][lg]overlay=485:1480[lv];" if logo.exists() else "[pv]null[lv];")
       + "[lv]subtitles=short.ass:fontsdir=fonts[v]",
       "-map", "[v]", "-map", f"{k}:a", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-af", loudnorm_linear(B / "short.wav", -14), "-shortest", "-movflags", "+faststart",
       short_file(E, out, mode), cwd=B)
    print(short_file(E, out, mode), f"({total:.1f}s)")


def short_file(E, out, mode):
    """The 480p preview lives in preview/, only the final in publish/short. SRTs stay in out."""
    return (E.EP_DIR / "preview" if mode == "preview" else out) / f"short-9x16-{mode}.mp4"


def short_vertical(E, mode, out):
    """Written short shot for 9:16 ("I already shot it vertically, don't crop it"): every X shot
    fills the 1080x1920 frame - camera takes rotated upright (CAM_FRAME) and scaled, animations rendered in portrait.
    Title at the top, subtitles in the lower third, channel CTA at the bottom; no 16:9 band."""
    cfg = E.SHORT
    S = short_edl(E)
    _, vfolder, W, H = VQUALITY[mode]
    B = E.RENDER / f"build-short-{mode}"
    (B / "fonts").mkdir(parents=True, exist_ok=True)
    for f in theme_fonts(E):
        shutil.copy(gs_env.FONTS / f, B / "fonts")
    tl = timeline(S)
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an"]
    norm = f"scale={W}:{H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration=2"
    clips = []
    for s in tl:
        o, dur = B / f"v-{s['id']}.mp4", f"{s['dur']:.3f}"
        if s["kind"] in ("anim", "chapter", "card"):
            ff(*anim_in(E, s, vfolder, mode, W, H), "-vf", norm, "-t", dur, *enc, o)
        elif s["kind"] == "screen":       # phone screen recording (edl.SCREEN[id] = (file in raw/, start s, crop))
            f, t0, crop = E.SCREEN[s["id"]]
            ff("-ss", f"{t0:.3f}", "-t", dur, "-i", E.RAW / f, "-vf",
               f"crop={crop},scale={W}:-2:flags=lanczos,pad={W}:{H}:0:(oh-ih)/2+{int(H * 0.04)}:color=0x0B0B0D,"
               f"fps={FPS},tpad=stop_mode=clone:stop_duration=2", "-t", dur, *enc, o)
        elif s["kind"] == "cam":
            cg_in, cg_chain, cg_alpha = cg_overlay(E, s["id"], vfolder, mode, W, H)
            pre = E.CAM_FRAME.get(s["src"], "")
            ff("-ss", f"{s['in']:.3f}", "-t", dur, "-i", E.SRC[s["src"]], *cg_in, "-filter_complex",
               f"[0:v]{pre + ',' if pre else ''}{E.CAM_GRADE},scale={W}:{H}:force_original_aspect_ratio=increase,"
               f"crop={W}:{H},fps={FPS}[cam];{cg_chain};"
               f"[cam][cg]overlay=0:0:shortest=0{cg_alpha}[v]", "-map", "[v]", "-t", dur, *enc, o)
        clips.append(o)
    (B / "concat.txt").write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    ff("-f", "concat", "-safe", "0", "-i", B / "concat.txt", "-c", "copy", B / "video.mp4")
    _mix(S, B, tl)
    cs = cues(S)
    write_srts(S, cs, folder=out, prefix="short-")
    total = tl[-1]["end"]
    # a title line wider than the frame is dropped by libass: shrink it to fit 940 px instead
    def fit(s, size):
        w = sum(size * 1.06 if ord(c) > 0x2E80 else size * 0.58 for c in s)
        return f"\\fscx{int(100 * 860 / w)}\\fscy{int(100 * 860 / w)}" if w > 860 else ""
    ev = [f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title,,0,0,0,,{{\\pos(540,150){fit(cfg['title'][0], 100)}}}{cfg['title'][0]}",
          f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title2,,0,0,0,,{{\\pos(540,270){fit(cfg['title'][1], 88)}}}{cfg['title'][1]}",
          f"Dialogue: 0,{ass_time(0)},{ass_time(total)},CTA,,0,0,0,,{E.SHORT_CTA}"]
    for ca, cb, zh, *_ in cs:
        ev.append(f"Dialogue: 0,{ass_time(ca)},{ass_time(cb)},Sub,,0,0,0,,{{\\pos(540,1380)}}{gold(E, zh)}")
    for s in tl:                     # source line per shot (small, above the subtitles), edl.SHORT_SRC = {id: text}
        if s["id"] in E.SHORT_SRC:
            ev.append(f"Dialogue: 0,{ass_time(s['start'])},{ass_time(s['end'])},Src,,0,0,0,,{{\\pos(540,1336)}}"
                      f"{E.SHORT_SRC[s['id']]}")
    for s in tl:                     # simulated alerts: permanent SIMULATION label for the whole screen shot
        if s["kind"] == "screen":
            ev += [f"Dialogue: 1,{ass_time(s['start'])},{ass_time(s['end'])},Sim,,0,0,0,,{{\\pos(540,1010)}}SIMULATION",
                   f"Dialogue: 1,{ass_time(s['start'])},{ass_time(s['end'])},Sim2,,0,0,0,,{{\\pos(540,1150)}}"
                   + gs_env.tr("Simulated screen · not a real alert", "模拟画面 · 不是真的警报")]
    (B / "short.ass").write_text(themed(E, SHORT_ASS_HEAD) + "\n".join(ev) + "\n", encoding="utf-8")
    x, sr = sf.read(str(B / "mix.wav"))
    A.write(B / "short.wav", A.fade(x.T, fin=0.05, fout=0.8))
    dst = short_file(E, out, mode)
    ff("-i", "video.mp4", "-i", "short.wav", "-filter_complex", "[0:v]subtitles=short.ass:fontsdir=fonts[v]",
       "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-af", loudnorm_linear(B / "short.wav", getattr(E, "SHORT_LUFS", -14)), "-shortest",
       "-movflags", "+faststart", dst, cwd=B)
    if mode == "preview":
        review_timeline(S, "short-480p", dst, tl, cs, True)
    print(dst, f"({total:.1f}s)")


# =============================================================================== CLI

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    E = load(sys.argv[1])
    cmd = sys.argv[2]
    if cmd in ("timeline", "check") and (sys.argv[3:4] == ["short"] or not E.SHOTS):   # standalone: no long video
        E = short_edl(E)
    mode = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] in QUALITY else "preview"
    if cmd == "timeline":
        for s in timeline(E):
            print(f'{s["id"]:8s} {s["kind"]:7s} {s["start"]:7.2f}-{s["end"]:7.2f} ({s["dur"]:5.2f}s) {s["mood"]:8s} '
                  + " ".join(f"{k}@{v:.2f}" for k, v in s["beats"].items()))
        print(f"total {timeline(E)[-1]['end']:.1f}s, {len(E.CUES)} cues")
    elif cmd == "check":
        p = check_cuts(E)
        print("all cuts land in silence" if not p else f"{len(p)} cut problem(s)")
    elif cmd == "render":
        render(E, mode, only=tuple(sys.argv[4:]))
    elif cmd == "build":
        build(E, mode)
    elif cmd == "mix":
        print(build(E, mode, audio_only=True))
    elif cmd == "srt":
        if E.SHOTS:
            write_srts(E)
            print(E.EP_DIR / "work" / gs_env.srt_name(SUB_LANGS[0]))
        out = E.EP_DIR / "publish" / "short"
        if E.SHORT_SHOTS:
            write_srts(short_edl(E), folder=out, prefix="short-")
        elif E.SHORT:
            write_srts(E, short_cues(E, short_segments(E), cues(E)), folder=out, prefix="short-")
        print(out / gs_env.srt_name(SUB_LANGS[0], short=True))
    elif cmd == "short":
        short(E, mode)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
