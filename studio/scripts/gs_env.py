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


# Subtitle files are named <name>.<language>_<COUNTRY>.srt (subtitles.en_GB.srt, short.zh_CN.srt): Facebook accepts
# no other shape, and only these language and country pairs (its help page "What is the naming convention for SubRip
# (.srt) files?", read 2026-11-18). YouTube takes the same files. [language] subtitle_locales = {en = "en_IN"} overrides.
FB_LOCALES = ("en_GB en_US af_ZA ar_AR ay_BO az_AZ be_BY bg_BG bn_IN bs_BA ca_ES ck_US cs_CZ cx_PH cy_GB da_DK de_DE el_GR en_IN eo_EO es_CL es_CO es_ES es_LA es_MX es_VE et_EE eu_ES fa_IR fi_FI fo_FO fr_CA fr_FR fy_NL ga_IE gl_ES gn_PY gu_IN gx_GR he_IL hi_IN hr_HR hu_HU hy_AM id_ID is_IS it_IT ja_JP jv_ID ka_GE kk_KZ km_KH kn_IN ko_KR ku_TR la_VA li_NL lt_LT lv_LV mg_MG mk_MK ml_IN mn_MN mr_IN ms_MY mt_MT nb_NO ne_NP nl_BE nl_NL nn_NO pa_IN pl_PL ps_AF pt_BR pt_PT qu_PE rm_CH ro_RO ru_RU sa_IN se_NO sk_SK sl_SI so_SO sq_AL sr_RS sv_SE sw_KE sy_SY ta_IN te_IN tg_TJ th_TH tl_PH tr_TR tt_RU uk_UA ur_PK uz_UZ vi_VN xh_ZA yi_DE zh_CN zh_HK zh_TW zu_ZA").split()
_FIRST = {"en": "en_US", "es": "es_ES", "fr": "fr_FR", "nl": "nl_NL", "pt": "pt_BR", "zh": "zh_CN"}


def locale(lang):
    """A language code as the locale subtitle files are named with: en -> en_US (en_GB with British spelling)."""
    own = LANG.get("subtitle_locales", {})
    if lang in own:
        return own[lang]
    lang = lang.replace("-", "_")
    if "_" in lang:
        a, b = lang.split("_", 1)
        return f"{a.lower()}_{b.upper()}"
    if lang == "en" and LANG.get("british_spelling"):
        return "en_GB"
    return _FIRST.get(lang) or next((c for c in FB_LOCALES if c.startswith(lang + "_")), f"{lang}_{lang.upper()}")


def srt_name(lang, short=False):
    return f"{'short' if short else 'subtitles'}.{locale(lang)}.srt"


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
