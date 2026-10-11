"""Episode pipeline: one tool for every episode.

Each episode has a code folder  <studio>/episodes/<EPISODE>/  containing
    edl.py      data only: sources, shots, beats, subtitle cues, SFX, short-clip settings (see template)
    shots.py    full-screen Manim scenes, one class per shot id (anim / chapter / card)
    cam_cg.py   transparent CG overlays for camera shots, class "Cam<shot id>"
    thumbs.py   thumbnails / covers
and a synced folder  <project>/episodes/<EPISODE>/  (raw, work, preview, publish). Paths: studio.toml.

CLI (run with the studio venv):
    python gs_episode.py <EPISODE> timeline            print the shot timeline and beats
    python gs_episode.py <EPISODE> check               check every cut lands in silence (not mid-word)
    python gs_episode.py <EPISODE> render preview|final [shot ids...]
    python gs_episode.py <EPISODE> build  preview|final
    python gs_episode.py <EPISODE> mix                 audio mix only (music / voice checks)
    python gs_episode.py <EPISODE> srt                 rewrite the two SRT tracks from CUES (no render)
    python gs_episode.py <EPISODE> short               9:16 highlight from the latest build
"""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pedalboard as pb
import soundfile as sf

import gs_audio as A
import gs_env

STUDIO_EPISODES = gs_env.STUDIO / "episodes"
INTRO_DIR = gs_env.STUDIO / "templates"
MUSIC, SFXD = gs_env.BRAND / "music", gs_env.BRAND / "sfx"
MOOD_FILE = {"tense": "loop-tense.wav", "curious": "loop-curious.wav", "calm": "loop-calm.wav",
             "epic": "loop-epic.wav"}
QUALITY = {"preview": ("-ql", "480p15", 854, 480), "final": ("-qh", "1080p60", 1920, 1080)}
DEFAULT_CAM_GRADE = "eq=brightness=0.04:gamma=1.15:saturation=1.05"
CAM_AUDIO = "highpass=f=100,afftdn=nf=-48,equalizer=f=250:t=q:w=1:g=-2"
FPS = int(gs_env.cfg("video", "fps", 30))
FINAL_ENCODER = list(gs_env.cfg("video", "final_encoder", ["-c:v", "libx264", "-preset", "slow", "-crf", "18"]))
LANG_MAIN = gs_env.LANG.get("subtitle_main", "zh")
LANG_SECOND = gs_env.LANG.get("subtitle_second", "en")
_PAL = gs_env.CFG.get("palette", {})
_FONTS = gs_env.CFG.get("fonts", {})
SUB_FONT = _FONTS.get("subtitle", "Noto Sans SC Medium")
SUB_FONT_HEAVY = _FONTS.get("subtitle_heavy", "Noto Sans SC Black")
SUB_FONT_FILES = _FONTS.get("subtitle_files", ["NotoSansSC-Medium.ttf", "NotoSansSC-Black.ttf"])


def ass_colour(hex_rgb, alpha=0):
    """'#F2B90D' -> ASS '&H000DB9F2' (alpha byte first, then blue, green, red)."""
    h = hex_rgb.lstrip("#")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


ACCENT_ASS = ass_colour(_PAL.get("accent", "#F2B90D"))
TEXT_ASS = ass_colour(_PAL.get("text", "#F5F1E8"))
MUTED_ASS = ass_colour(_PAL.get("muted", "#CBBC90"))
BG_HEX = _PAL.get("bg_deep", "#131008")


# =============================================================================== loading

def load(episode):
    """Load an episode's edl.py and attach derived paths."""
    code = STUDIO_EPISODES / episode
    spec = importlib.util.spec_from_file_location(f"edl_{episode.replace('-', '_')}", code / "edl.py")
    E = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E)
    E.CODE_DIR = code
    E.EP_DIR = gs_env.EPISODES / E.EPISODE
    E.RAW = E.EP_DIR / "raw"
    E.RENDER = gs_env.RENDER / E.EPISODE
    E.SRC = {k: E.RAW / v for k, v in E.SOURCES.items()}
    for name, default in [("SFX", []), ("GOLD_TERMS", []), ("CAM_GRADE", DEFAULT_CAM_GRADE), ("SHORT", None),
                          ("EXT_AUDIO", {}), ("SQUEEZE", {}), ("TAIL_EXPANDER", "light")]:
        if not hasattr(E, name):
            setattr(E, name, default)
    return E


def here(file):
    """For Manim scene files: load the edl.py that sits next to `file`."""
    return load(Path(file).resolve().parent.name)


# =============================================================================== timeline

def timeline(E):
    """Shots in order with timeline start/end; beats converted to shot-local seconds.

    SHOTS rows: (id, kind, source, in, out, hold, mood, beats)
      kind  : anim (Manim, voice-over) | cam (camera + CG overlay) | intro | chapter | card (end screen)
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
    return next(s for s in timeline(E) if s["id"] == sid)


def cues(E):
    """Subtitle cues on the timeline: (start, end, zh, en). Held 0.15 s, never overlapping the next cue."""
    tl = timeline(E)
    res = []
    for src, a, b, zh, en in E.CUES:
        sh = next(s for s in tl if s["src"] == src and s["in"] - 0.01 <= a <= s["out"])
        res.append((sh["start"] + local(sh, a), sh["start"] + local(sh, min(b, sh["out"])), zh, en))
    res.sort()
    out = []
    for k, (a, b, zh, en) in enumerate(res):
        nxt = res[k + 1][0] if k + 1 < len(res) else b + 1
        out.append((a, min(b + 0.15, nxt - 0.02), zh, en))
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
    return (f"loudnorm=I={target}:TP={tp}:LRA=20:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")


TAIL_PRESETS = {"off": None, "light": (10, 3.5, 10), "strong": (8, 4.0, 18)}   # (dB below speech, ratio, max cut dB)


def expand_tails(x, below=10, ratio=3.5, rng_db=10, att=0.003, rel=0.08):
    """Downward expander for the room tail at sentence ends. Loudness normalisation raises a quiet phone
    recording by ~7 dB and the room echo with it (director: 'reverb at the end of the sentence'); below
    (speech level - `below` dB) the level falls `ratio` x faster, at most `rng_db`. Speech itself is untouched."""
    win = int(0.01 * A.SR)
    edb = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(win) / win, "same")) + 1e-9)
    thr = np.percentile(edb[edb > -60], 90) - below
    gdb = np.where(edb < thr, np.maximum((edb - thr) * (ratio - 1), -rng_db), 0.0)
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
        flag = []
        if head > speech_db:
            flag.append(f"in {s['in']:.2f}s cuts into speech ({head:.0f} dB)")
        if tail > speech_db:
            flag.append(f"out {s['out']:.2f}s cuts speech off ({tail:.0f} dB) -> move later")
        print(f"{s['id']:8s} in {s['in']:7.2f} ({head:5.1f} dB)  out {s['out']:7.2f} (after {tail:5.1f} dB)  "
              + ("  !! " + "; ".join(flag) if flag else "ok"))
        problems += flag
    return problems


# =============================================================================== render

def manim(file, scene, mode, transparent=False, cwd=None):
    q = QUALITY[mode][0]
    args = [sys.executable, "-m", "manim", q, "--fps", str(FPS)] if mode == "final" else [sys.executable, "-m", "manim", q]
    if transparent:
        args.append("-t")
    args += ["--media_dir", str(Path(cwd).parent.parent / "render" / Path(cwd).name), file, scene]
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"render failed: {file} {scene}")


def render(E, mode, only=()):
    """Render shots one at a time (parallel Manim runs corrupt the shared text cache)."""
    folder = QUALITY[mode][1] if mode == "preview" else "1080p30"
    intro = INTRO_DIR / ".." / "render" / "intro" / "videos" / "intro" / folder / "Intro.mp4"
    if not intro.resolve().exists():
        subprocess.run([sys.executable, "-m", "manim", QUALITY[mode][0], *(["--fps", "30"] if mode == "final" else []),
                        "--media_dir", str(gs_env.RENDER / "intro"), "intro.py", "Intro"], cwd=INTRO_DIR, check=True)
    for s in timeline(E):
        if only and s["id"] not in only:
            continue
        if s["kind"] in ("anim", "chapter", "card"):
            manim("shots.py", s["id"], mode, cwd=E.CODE_DIR)
        elif s["kind"] == "cam":
            manim("cam_cg.py", "Cam" + s["id"], mode, transparent=True, cwd=E.CODE_DIR)
        else:
            continue
        print("rendered", s["id"])


# =============================================================================== build

def build(E, mode, audio_only=False):
    q, folder, W, H = QUALITY[mode]
    folder = folder if mode == "preview" else "1080p30"
    B = E.RENDER / f"build-{mode}"
    (B / "fonts").mkdir(parents=True, exist_ok=True)
    for f in SUB_FONT_FILES:
        if (gs_env.FONTS / "static" / f).exists():
            shutil.copy(gs_env.FONTS / "static" / f, B / "fonts")
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
            ff("-i", E.RENDER / "videos" / "shots" / folder / f"{s['id']}.mp4", "-vf", norm, "-t", dur, *enc, out)
        elif s["kind"] == "intro":
            ff("-i", gs_env.RENDER / "intro" / "videos" / "intro" / folder / "Intro.mp4", "-vf", norm, "-t", dur,
               *enc, out)
        elif s["kind"] == "cam":
            cg = E.RENDER / "videos" / "cam_cg" / folder / f"Cam{s['id']}.mov"
            ff("-ss", f"{s['in']:.3f}", "-t", dur, "-i", E.SRC[s["src"]], "-i", cg, "-filter_complex",
               f"[0:v]{E.CAM_GRADE},scale={W}:{H}:flags=lanczos,fps={FPS}[cam];"
               f"[1:v]scale={W}:{H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration=2[cg];"
               f"[cam][cg]overlay=0:0:shortest=0[v]", "-map", "[v]", "-t", dur, *enc, out)
        clips.append(out)
    (B / "concat.txt").write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    ff("-f", "concat", "-safe", "0", "-i", B / "concat.txt", "-c", "copy", B / "video.mp4")
    _mix(E, B, tl)
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
        x = np.concatenate([A.fade(decode(path, a - lag, b - a, af=af)[None], fin=0.015, fout=0.03)[0]
                            for a, b in pieces(s)])
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
    # gentle voice chain (lesson from the original channel: the old 3:1 compressor + master compressor + dynamic loudnorm made
    # the room echo and breaths pump up - "hard and painful"): one light compressor, a touch less 6.5 kHz edge
    speech = pb.Pedalboard([pb.Compressor(threshold_db=-20, ratio=1.6, attack_ms=15, release_ms=150),
                            pb.HighShelfFilter(cutoff_frequency_hz=6500, gain_db=-2.0)])(speech[None], A.SR)[0]
    duck = duck_curve(speech)

    bed = np.zeros((2, n), np.float32)
    runs = []
    for s in tl:
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
    bed *= 10 ** (-9 / 20) * duck

    def place(buf, wav, t, gain_db, ducked=False):
        x = sf.read(str(wav))[0].T
        i = int(t * A.SR)
        k = min(x.shape[1], n - i)
        g = 10 ** (gain_db / 20) * (duck[i:i + k] if ducked else 1)
        buf[:, i:i + k] += x[:, :k] * g

    stings = np.zeros((2, n), np.float32)
    for s in tl:
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
        place(fx, SFXD / f"{name}.wav", s["start"] + (s["beats"][when] if isinstance(when, str) else when), gain)
    mix = np.vstack([speech, speech]) + bed + stings + fx            # no glue compressor on the speech
    voiced = speech[np.abs(speech) > 0.01]
    mix = mix * (10 ** (-19 / 20) / (np.sqrt(np.mean(voiced ** 2)) + 1e-9))   # speech ~ -19 dBFS RMS
    mix = pb.Pedalboard([pb.Limiter(threshold_db=-4.0, release_ms=60)])(mix.astype(np.float32), A.SR)
    # (peaks only; the final two-pass linear loudnorm then adds one constant gain to -14 LUFS)
    A.write(B / "mix.wav", mix)
    return B / "mix.wav"


def _finish(E, B, tl, mode, W, H):
    # ---- subtitles (A on animation, B on camera footage) + SRTs
    cam_spans = [(s["start"], s["end"]) for s in tl if s["kind"] == "cam"]
    head = subtitle_head()
    lines = []
    cs = cues(E)
    for a, b, zh, _ in cs:
        style = "B" if any(x <= a < y for x, y in cam_spans) else "A"
        lines.append(f"Dialogue: 0,{ass_time(a)},{ass_time(b)},{style},,0,0,0,,{gold(E, zh)}")
    (B / "subs.ass").write_text(head.rstrip() + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    write_srts(E, cs)

    # ---- final mux (encoder for the 1080p master: [video] final_encoder in studio.toml)
    outdir = E.EP_DIR / ("preview" if mode == "preview" else "publish")
    outdir.mkdir(exist_ok=True)
    out = outdir / (f"{E.EPISODE}-rough-480p.mp4" if mode == "preview" else f"{E.EPISODE}-1080p.mp4")
    venc = ["-c:v", "libx264", "-preset", "medium", "-crf", "20"] if mode == "preview" else FINAL_ENCODER
    ff("-i", "video.mp4", "-i", "mix.wav", "-vf", "subtitles=subs.ass:fontsdir=fonts", *venc, "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-af", loudnorm_linear(B / "mix.wav", -14), "-shortest", "-movflags", "+faststart",
       out, cwd=B)
    print(out)
    return out


def subtitle_head():
    """ASS header: <project>/brand/templates/subtitle-styles.ass if the channel has its own, else built from
    studio.toml (A = text + dark outline for animation, B = text on a translucent box for camera footage)."""
    own = gs_env.BRAND / "templates" / "subtitle-styles.ass"
    if own.exists():
        return own.read_text(encoding="utf-8")
    dark, box = ass_colour(BG_HEX), ass_colour(BG_HEX, 0x38)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: A,{SUB_FONT},58,{TEXT_ASS},{TEXT_ASS},{dark},{ass_colour(BG_HEX, 0x80)},0,0,0,0,100,100,1,0,1,3.5,2,2,240,240,58,1
Style: B,{SUB_FONT},54,{TEXT_ASS},{TEXT_ASS},{box},{box},0,0,0,0,100,100,1,0,3,14,0,2,240,240,62,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_srts(E, cs=None):
    """work/<main>.srt + work/<second>.srt from CUES (also `gs_episode.py <EP> srt`: no re-render needed)."""
    cs = cues(E) if cs is None else cs
    (E.EP_DIR / "work").mkdir(exist_ok=True)
    for lang, k in [(LANG_MAIN, 2), (LANG_SECOND, 3)]:
        if not lang:
            continue
        srt = "\n".join(f"{i}\n{srt_time(c[0])} --> {srt_time(c[1])}\n{c[k]}\n" for i, c in enumerate(cs, 1))
        (E.EP_DIR / "work" / f"{lang}.srt").write_text(srt, encoding="utf-8")


def gold(E, text):
    for term in E.GOLD_TERMS:
        text = text.replace(term, "{\\c" + ACCENT_ASS[:2] + ACCENT_ASS[4:] + "&}" + term + "{\\r}")
    return text


def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# =============================================================================== 9:16 short

def short_head():
    dark = ass_colour(BG_HEX)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{SUB_FONT_HEAVY},96,{TEXT_ASS},{TEXT_ASS},{dark},{dark},0,0,0,0,100,100,2,0,1,5,0,8,60,60,0,1
Style: Title2,{SUB_FONT_HEAVY},84,{ACCENT_ASS},{ACCENT_ASS},{dark},{dark},0,0,0,0,100,100,2,0,1,5,0,8,60,60,0,1
Style: Sub,{SUB_FONT},66,{TEXT_ASS},{TEXT_ASS},{dark},{ass_colour(BG_HEX, 0x80)},0,0,0,0,100,100,1,0,1,4,2,8,70,70,0,1
Style: CTA,{SUB_FONT},44,{MUTED_ASS},{MUTED_ASS},{dark},{dark},0,0,0,0,100,100,1,0,1,2,0,2,60,60,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def short(E, mode="preview"):
    """Title band on top, the 16:9 video in the middle, big subtitles under it, channel CTA at the bottom."""
    B = E.RENDER / f"build-{mode}"
    cfg = E.SHORT
    def at(ref, edge):           # "S03" -> shot start / end; "S01@18.75" -> 18.75 s into S01 (cut inside a shot)
        sid, _, sec = ref.partition("@")
        return shot(E, sid)["start"] + float(sec) if sec else shot(E, sid)[edge]
    segs = [(at(a, "start"), at(b, "end")) for a, b in cfg["segments"]]
    total = sum(b - a for a, b in segs)
    ev = [f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title,,0,0,0,,{{\\pos(540,230)}}{cfg['title'][0]}",
          f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title2,,0,0,0,,{{\\pos(540,360)}}{cfg['title'][1]}",
          f"Dialogue: 0,{ass_time(0)},{ass_time(total)},CTA,,0,0,0,,{gs_env.CHANNEL.get('short_cta', '')}"]
    off = 0.0
    for a, b in segs:
        for ca, cb, zh, _ in cues(E):
            if a - 0.01 <= ca < b:
                ev.append(f"Dialogue: 0,{ass_time(off + ca - a)},{ass_time(off + min(cb, b) - a)},Sub,,0,0,0,,"
                          f"{{\\pos(540,1330)}}{gold(E, zh)}")
        off += b - a
    (B / "short.ass").write_text(short_head() + "\n".join(ev) + "\n", encoding="utf-8")
    x, sr = sf.read(str(B / "mix.wav"))
    y = np.concatenate([A.fade(x[int(a * sr):int(b * sr)].T, fin=0.05, fout=0.08) for a, b in segs], axis=1)
    A.write(B / "short.wav", A.fade(y, fout=0.8))
    # one input per segment: video.mp4 comes from the concat demuxer and trim= in a filtergraph drops segment 1
    inputs = []
    for a, b in segs:
        inputs += ["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", "video.mp4"]
    k = len(segs)
    out = E.EP_DIR / "publish" / "short"
    out.mkdir(parents=True, exist_ok=True)
    import gs_style                                # logo between subtitles and CTA (skipped without a logo file)
    logo = gs_style.WATERMARK if gs_style.WATERMARK.exists() else None
    pad = f"[cv]scale=1080:608:flags=lanczos,pad=1080:1920:0:560:color=0x{BG_HEX.lstrip('#')}[pv];"
    graph = ("".join(f"[{i}:v]" for i in range(k)) + f"concat=n={k}:v=1:a=0[cv];" + pad +
             (f"[{k + 1}:v]scale=110:110[lg];[pv][lg]overlay=485:1480[lv];[lv]" if logo else "[pv]") +
             "subtitles=short.ass:fontsdir=fonts[v]")
    ff(*inputs, "-i", "short.wav", *(["-i", logo] if logo else []), "-filter_complex", graph,
       "-map", "[v]", "-map", f"{k}:a", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-af", loudnorm_linear(B / "short.wav", -14), "-shortest", "-movflags", "+faststart",
       out / f"short-9x16-{mode}.mp4", cwd=B)
    print(out / f"short-9x16-{mode}.mp4", f"({total:.1f}s)")


# =============================================================================== CLI

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    E = load(sys.argv[1])
    cmd = sys.argv[2]
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
        write_srts(E)
        print(E.EP_DIR / "work")
    elif cmd == "short":
        short(E, mode)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
