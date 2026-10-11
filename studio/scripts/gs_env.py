"""Shared studio environment: paths, ffmpeg location, channel settings from studio.toml.

Import this at the top of every script / Manim scene:
    import gs_env

The studio folder is the parent of this scripts/ folder. Settings come from <studio>/studio.toml
(or the file named by the STUDIO_CONFIG environment variable); copy studio.example.toml to start.
"""
import os
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
    p = Path(os.path.expandvars(os.path.expanduser(value)))
    return p if p.is_absolute() else base / p


PROJECT = _path(cfg("paths", "project", "."), STUDIO)   # synced: CHANNEL.md, brand assets, episodes, outputs
BRAND = PROJECT / "brand"
FONTS = BRAND / "fonts"
EPISODES = PROJECT / "episodes"
MODELS = _path(cfg("paths", "models", "models"), STUDIO)
RENDER = _path(cfg("paths", "render", "render"), STUDIO)
WHISPER_MODEL = _path(cfg("whisper", "model", "models/faster-whisper-large-v3"), STUDIO)

_ff_bin = cfg("paths", "ffmpeg_bin", "")
if _ff_bin:
    FFMPEG_BIN = _path(_ff_bin, STUDIO)
    _exe = ".exe" if os.name == "nt" else ""
    FFMPEG, FFPROBE = str(FFMPEG_BIN / f"ffmpeg{_exe}"), str(FFMPEG_BIN / f"ffprobe{_exe}")
    # make ffmpeg visible to Manim, pydub and subprocess calls regardless of the shell's PATH
    if str(FFMPEG_BIN) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(FFMPEG_BIN) + os.pathsep + os.environ.get("PATH", "")
else:
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
    FFPROBE = shutil.which("ffprobe") or "ffprobe"

CHANNEL = CFG.get("channel", {})
LANG = CFG.get("language", {})

# Fonts must be installed in the operating system, NOT registered with manimpango: private registration makes
# every Text() call re-scan the font files (25-55 s each). Use weights via Pango, e.g. weight=HEAVY.
