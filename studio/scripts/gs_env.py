"""Shared studio environment: paths, ffmpeg location, channel settings from studio.toml.

Import this at the top of every script:
    import gs_env

The studio folder is the parent of this scripts/ folder. Settings come from <studio>/studio.toml
(or the file named by the STUDIO_CONFIG environment variable); copy studio.example.toml to start.
"""
import os
import re
import shutil
import tomllib
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent   # local, not synced: venv, models, render cache, code
CONFIG_FILE = Path(os.environ.get("STUDIO_CONFIG", STUDIO / "studio.toml"))
if not CONFIG_FILE.exists():
    raise SystemExit(f"studio config not found: {CONFIG_FILE}\n"
                     f"copy {STUDIO / 'studio.example.toml'} to studio.toml and fill in [paths] and [channel]")
CFG = tomllib.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def cfg(section, key, default=None):
    return CFG.get(section, {}).get(key, default)


def _path(value, base):
    p = Path(os.path.expandvars(os.path.expanduser(str(value))))
    return p if p.is_absolute() else base / p


PROJECT = _path(cfg("paths", "project", "."), STUDIO)   # synced: CHANNEL.md, brand assets, episodes, outputs
BRAND = PROJECT / "brand"
EPISODES = PROJECT / "episodes"
SHORTS = PROJECT / "shorts"       # standalone shorts, ids s001-<slug> (in a batch) / ss001-<slug> (outside one)
BATCHES = PROJECT / "batches"     # several pieces recorded in one session, ids b01, b02 ...
MODELS = _path(cfg("paths", "models", "models"), STUDIO)
RENDER = _path(cfg("paths", "render", "render"), STUDIO)
WEB = STUDIO / "web"              # animation engine: kit/, ep/<id>/, fonts/, brand/
FONTS = WEB / "fonts"             # font files for the animation pages and for burned subtitles
WHISPER_MODEL = _path(cfg("whisper", "model", "models/faster-whisper-large-v3"), STUDIO)
MUSIC_LIBRARY = _path(cfg("paths", "music_library", "") or PROJECT / "music", STUDIO)
MUSIC_USED = _path(cfg("paths", "music_used", "") or PROJECT / "music-used.md", STUDIO)

_ff_bin = cfg("paths", "ffmpeg_bin", "")
if _ff_bin:
    FFMPEG_BIN = _path(_ff_bin, STUDIO)
    _exe = ".exe" if os.name == "nt" else ""
    FFMPEG, FFPROBE = str(FFMPEG_BIN / f"ffmpeg{_exe}"), str(FFMPEG_BIN / f"ffprobe{_exe}")
    # make ffmpeg visible to the animation renderer and subprocess calls regardless of the shell's PATH
    if str(FFMPEG_BIN) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(FFMPEG_BIN) + os.pathsep + os.environ.get("PATH", "")
else:
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
    FFPROBE = shutil.which("ffprobe") or "ffprobe"

CHANNEL = CFG.get("channel", {})
LANG = CFG.get("language", {})
CJK = LANG.get("length_unit", "cjk") == "cjk"        # narration counted in characters (zh / ja) or in words
UI = cfg("ui", "language", "en")                     # language of the review / editing pages and the reports


def tr(en, zh):
    """A line of a report or a page in the studio's own language ([ui] language = "en" | "zh")."""
    return zh if UI == "zh" else en


def is_short(ep):
    """Standalone short (s001-..., ss001-...) rather than an episode (02-magnitude)."""
    return re.match(r"s{1,2}\d{3}-", ep) is not None


def ep_dir(ep):
    """Synced folder (raw, work, preview, publish) of an episode or a standalone short."""
    return (SHORTS if is_short(ep) else EPISODES) / ep


def code_dir(ep):
    """Local code folder (edl.py, edl_auto.py)."""
    return STUDIO / ("shorts" if is_short(ep) else "episodes") / ep


def subtitle_fonts():
    """Font files (in web/fonts) that ffmpeg needs to burn subtitles."""
    return list(cfg("fonts", "subtitle_files", ["NotoSansSC-Medium.ttf", "NotoSansSC-Black.ttf"] if CJK
                    else ["NotoSans-Medium.ttf", "NotoSans-Black.ttf"]))


def kill_tree(names=("ffmpeg",)):
    """Stop stray processes after a stalled step (Windows: taskkill, elsewhere: pkill)."""
    import subprocess
    for n in names:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/IM", f"{n}.exe"], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", n], capture_output=True)


def pid_alive(pid):
    import subprocess
    if os.name == "nt":
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
