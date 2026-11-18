"""Install, check and remove the studio's parts, one at a time. Nothing here asks questions: the setup skill asks the
person whether they need a part BEFORE it runs `install`, so nobody downloads gigabytes they will not use.

    python setup_studio.py list                      every part: what it is for, who can skip it, download size
    python setup_studio.py status                    what is installed, what is missing, disk space used
    python setup_studio.py install <part> [options]  core | fonts | whisper | animation | music_fit | score
        whisper:  --model large-v3 | medium | small          (default large-v3)
        fonts:    --script latin | sc | tc | jp | kr         (default: from [language] narration)
    python setup_studio.py remove <part>             frees the space again (models, browser, packages)
    python setup_studio.py set <section> <key> <value>       write one value into studio.toml (value as TOML)

Runs with any Python 3.11+ (it does not need the studio's own packages). The studio's Python lives in <studio>/.venv
and is made by `install core` with uv (https://docs.astral.sh/uv/), or with `python -m venv` when uv is not there.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent
VENV = STUDIO / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
CONFIG = Path(os.environ.get("STUDIO_CONFIG", STUDIO / "studio.toml"))
WIN, MAC = os.name == "nt", sys.platform == "darwin"

PARTS = {
    "core": dict(size="about 350 MB", need="everyone",
                 what="The studio's own Python with the audio and picture packages (numpy, scipy, soundfile, pedalboard, "
                      "pillow), and ffmpeg, which cuts, mixes and encodes every video."),
    "fonts": dict(size="3 MB (Latin) to 45 MB (Chinese / Japanese / Korean)", need="everyone",
                  what="Free fonts (SIL Open Font Licence) for burned subtitles and for the text inside animations."),
    "whisper": dict(size="3.1 GB with the large-v3 model, 1.7 GB with medium, 0.7 GB with small", need="anyone who records a voice",
                    what="Speech recognition on your own computer. It finds every word's time in your recordings: the automatic "
                         "first cut, the subtitle timing and the sorting of a recording session all stand on it. Skip it only "
                         "if your videos have no spoken voice. A smaller model is faster and lighter but mishears more."),
    "animation": dict(size="about 500 MB (a headless browser) + the free motion-showreel plugin", need="videos with animated shots, cards or on-screen labels",
                      what="Draws the animated shots, chapter and end cards, the intro and the labels over camera shots, frame "
                           "by frame in a headless browser. Skip it if you only want your camera footage cut, subtitled and "
                           "mixed: animation shots then become plain text cards."),
    "music_fit": dict(size="about 300 MB", need="music from a library, or your own tracks",
                      what="Finds the beats and bars of a music track (librosa) so a track is shortened or lengthened on bar "
                           "lines and ends on its own ending. Skip it for videos without music, or with the programmed score."),
    "score": dict(size="about 40 MB + the FluidSynth program", need="only the programmed score",
                  what="Music composed by Claude note by note and played through a SoundFont (GeneralUser GS). Needs no "
                       "downloads of tracks and no licences to check, but sounds simpler than recorded library music."),
}
WHISPER = {"large-v3": ("Systran/faster-whisper-large-v3", "2.9 GB"), "medium": ("Systran/faster-whisper-medium", "1.5 GB"),
           "small": ("Systran/faster-whisper-small", "0.5 GB")}
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
# (url, file kept in web/fonts, static weights to cut from a variable font: {file: weight})
FONTS_COMMON = [
    (GF + "spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf", "SpaceGrotesk-VF.ttf", {}),
    (GF + "ibmplexmono/IBMPlexMono-Regular.ttf", "IBMPlexMono-Regular.ttf", {}),
    (GF + "ibmplexmono/IBMPlexMono-Bold.ttf", "IBMPlexMono-Bold.ttf", {}),
    (GF + "caveat/Caveat%5Bwght%5D.ttf", "Caveat-VF.ttf", {}),
]
FONTS_SCRIPT = {
    "latin": ("Noto Sans", (GF + "notosans/NotoSans%5Bwdth%2Cwght%5D.ttf", "NotoSans-VF.ttf", {"NotoSans-Medium.ttf": 500, "NotoSans-Bold.ttf": 700, "NotoSans-Black.ttf": 900})),
    "sc": ("Noto Sans SC", (GF + "notosanssc/NotoSansSC%5Bwght%5D.ttf", "NotoSansSC-VF.ttf", {"NotoSansSC-Medium.ttf": 500, "NotoSansSC-Bold.ttf": 700, "NotoSansSC-Black.ttf": 900})),
    "tc": ("Noto Sans TC", (GF + "notosanstc/NotoSansTC%5Bwght%5D.ttf", "NotoSansTC-VF.ttf", {"NotoSansTC-Medium.ttf": 500, "NotoSansTC-Bold.ttf": 700, "NotoSansTC-Black.ttf": 900})),
    "jp": ("Noto Sans JP", (GF + "notosansjp/NotoSansJP%5Bwght%5D.ttf", "NotoSansJP-VF.ttf", {"NotoSansJP-Medium.ttf": 500, "NotoSansJP-Bold.ttf": 700, "NotoSansJP-Black.ttf": 900})),
    "kr": ("Noto Sans KR", (GF + "notosanskr/NotoSansKR%5Bwght%5D.ttf", "NotoSansKR-VF.ttf", {"NotoSansKR-Medium.ttf": 500, "NotoSansKR-Bold.ttf": 700, "NotoSansKR-Black.ttf": 900})),
}
SOUNDFONT = "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main/GeneralUser-GS.sf2"


def say(s=""):
    print(s, flush=True)


def run(cmd, **kw):
    say("  $ " + " ".join("<script>" if "\n" in str(c) else str(c) for c in cmd))
    return subprocess.run(list(map(str, cmd)), **kw)


def cfg():
    import tomllib
    return tomllib.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}


def set_value(section, key, value):
    """Write one `key = value` line into [section] of studio.toml, keeping every other line and comment."""
    if not CONFIG.exists():
        shutil.copy(STUDIO / "studio.example.toml", CONFIG)
    lines = CONFIG.read_text(encoding="utf-8").splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip().startswith(f"[{section}]")), None)
    if start is None:
        lines += ["", f"[{section}]", f"{key} = {value}"]
    else:
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"\s*\[", lines[i])), len(lines))
        hit = next((i for i in range(start + 1, end) if re.match(rf"\s*{re.escape(key)}\s*=", lines[i])), None)
        if hit is None:
            lines.insert(start + 1, f"{key} = {value}")
        else:
            m = re.match(r"(.*?=\s*)(\"(?:[^\"\\]|\\.)*\"|\[[^\]]*\]|[^#]*?)(\s*#.*)?$", lines[hit])
            lines[hit] = f"{key} = {value}" + (m.group(3) if m and m.group(3) else "")
    CONFIG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def pip(*args):
    uv = shutil.which("uv")
    cmd = [uv, "pip", *args[:1], "--python", PY, *args[1:]] if uv else [PY, "-m", "pip", *args]
    if run(cmd).returncode:
        raise SystemExit("FAILED: the package step above did not finish (see its message)")


def need_core():
    if not PY.exists():
        raise SystemExit("install `core` first (the studio's own Python)")


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        return
    say(f"  downloading {dest.name}")
    req = urllib.request.Request(url, headers={"User-Agent": "explainer-studio-setup"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def size(path):
    path = Path(path)
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def mb(n):
    return f"{n / 1e9:.1f} GB" if n > 1e9 else f"{n / 1e6:.0f} MB"


def which_hint(tool):
    hint = {"ffmpeg": ("winget install Gyan.FFmpeg", "brew install ffmpeg", "sudo apt install ffmpeg"),
            "node": ("winget install OpenJS.NodeJS.LTS", "brew install node", "sudo apt install nodejs npm"),
            "fluidsynth": ("winget install FluidSynth.FluidSynth  (or download from github.com/FluidSynth/fluidsynth/releases)",
                           "brew install fluid-synth", "sudo apt install fluidsynth"),
            "uv": ("winget install astral-sh.uv", "brew install uv", "curl -LsSf https://astral.sh/uv/install.sh | sh")}[tool]
    return hint[0] if WIN else hint[1] if MAC else hint[2]


def ffmpeg_path():
    b = cfg().get("paths", {}).get("ffmpeg_bin", "")
    if b:
        f = Path(b) / ("ffmpeg.exe" if WIN else "ffmpeg")
        return str(f) if f.exists() else None
    return shutil.which("ffmpeg")


# ------------------------------------------------------------------------------------------------ install

def install_core():
    uv = shutil.which("uv")
    if not PY.exists():
        if uv:
            if run([uv, "venv", VENV, "--python", "3.12"]).returncode:
                raise SystemExit("FAILED: uv could not make the Python environment")
        else:
            say(f"  uv is not installed ({which_hint('uv')}); using this Python's venv instead")
            if sys.version_info < (3, 11):
                raise SystemExit("this Python is older than 3.11: install uv, which brings its own Python")
            run([sys.executable, "-m", "venv", VENV], check=True)
    pip("install", "-r", STUDIO / "requirements" / "core.txt")
    if cfg().get("language", {}).get("narration", "") == "zh":
        pip("install", "-r", STUDIO / "requirements" / "zh.txt")
    for d in ("models", "render", "episodes", "shorts", "web/fonts", "web/brand", "web/ep"):
        (STUDIO / d).mkdir(parents=True, exist_ok=True)
    if not ffmpeg_path():
        say(f"MISSING ffmpeg: install it, then run `status` again:\n    {which_hint('ffmpeg')}\n"
            "  (or put its folder in [paths] ffmpeg_bin of studio.toml)")
    say("core: done")


def install_fonts(script=None):
    need_core()
    lang = cfg().get("language", {}).get("narration", "en")
    script = script or {"zh": "sc", "zh-tw": "tc", "ja": "jp", "ko": "kr"}.get(lang, "latin")
    family, main = FONTS_SCRIPT[script]
    fonts = STUDIO / "web" / "fonts"
    for url, name, cuts in FONTS_COMMON + [main]:
        download(url, fonts / name)
        for out, weight in cuts.items():
            if not (fonts / out).exists():
                say(f"  cutting {out} from {name}")
                code = ("import sys; from fontTools.ttLib import TTFont; from fontTools.varLib import instancer\n"
                        "f = TTFont(sys.argv[1]); axes = {a.axisTag for a in f['fvar'].axes}\n"
                        "loc = {'wght': float(sys.argv[3])}\n"
                        "if 'wdth' in axes: loc['wdth'] = 100.0\n"
                        "instancer.instantiateVariableFont(f, loc, inplace=True, updateFontNames=True); f.save(sys.argv[2])\n")
                if run([PY, "-c", code, fonts / name, fonts / out, weight]).returncode:
                    raise SystemExit(f"FAILED: could not make {out}")
    cuts = list(main[2])
    css = [f"/* Written by setup_studio.py install fonts ({script}). Fonts: SIL Open Font Licence. */"]
    for out, weight in main[2].items():
        css.append(f'@font-face {{ font-family: "K Sans"; src: url(../fonts/{out}); font-weight: {weight}; }}')
    css += ['@font-face { font-family: "K Label"; src: url(../fonts/SpaceGrotesk-VF.ttf); font-weight: 300 700; }',
            '@font-face { font-family: "K Mono"; src: url(../fonts/IBMPlexMono-Regular.ttf); font-weight: 400; }',
            '@font-face { font-family: "K Mono"; src: url(../fonts/IBMPlexMono-Bold.ttf); font-weight: 700; }',
            '@font-face { font-family: "K Hand"; src: url(../fonts/Caveat-VF.ttf); font-weight: 400 700; }',
            "html, body { margin: 0; background: #000; overflow: hidden; }", "canvas { display: block; }"]
    (STUDIO / "web" / "kit" / "fonts.css").write_text("\n".join(css) + "\n", encoding="utf-8")
    set_value("fonts", "subtitle", json.dumps(f"{family} Medium"))
    set_value("fonts", "subtitle_heavy", json.dumps(f"{family} Black"))
    set_value("fonts", "subtitle_files", json.dumps([cuts[0], cuts[2]]))
    say(f"fonts: done ({family}; {mb(size(fonts))} in web/fonts)")


def install_whisper(model="large-v3"):
    need_core()
    if model not in WHISPER:
        raise SystemExit(f"model must be one of {', '.join(WHISPER)}")
    pip("install", "-r", STUDIO / "requirements" / "whisper.txt")
    repo, sz = WHISPER[model]
    dest = STUDIO / "models" / f"faster-whisper-{model}"
    if not (dest / "model.bin").exists():
        say(f"  downloading the {model} model ({sz}); this is the long part")
        code = ("import sys; from huggingface_hub import snapshot_download\n"
                "snapshot_download(sys.argv[1], local_dir=sys.argv[2])\n")
        if run([PY, "-c", code, repo, dest]).returncode:
            raise SystemExit("FAILED: the model download did not finish; run the same command again to resume")
    set_value("whisper", "model", json.dumps(f"models/faster-whisper-{model}"))
    set_value("components", "whisper", "true")
    say(f"whisper: done ({model}, {mb(size(dest))})")


def install_animation():
    need_core()
    if not shutil.which("node"):
        raise SystemExit(f"MISSING Node.js 18+: install it, then run this again:\n    {which_hint('node')}")
    web = STUDIO / "web"
    npm = shutil.which("npm") or "npm"
    if not (web / "package.json").exists():
        (web / "package.json").write_text('{\n  "name": "explainer-studio-web",\n  "private": true,\n  "type": "module"\n}\n', encoding="utf-8")
    if run([npm, "install", "--no-audit", "--no-fund", "--loglevel=error", "-D", "playwright", "tone@15.1.22"], cwd=web).returncode:
        raise SystemExit("FAILED: npm install")
    npx = shutil.which("npx") or "npx"
    if run([npx, "--yes", "playwright", "install", "chromium"], cwd=web).returncode:
        say("WARN the browser download failed; the renderer falls back to an installed Chrome / Edge when it finds one")
    set_value("components", "animation", "true")
    found = [p for r in (Path.home() / ".claude" / "plugins", Path.home() / ".claude" / "skills") if r.exists()
             for p in r.rglob("scripts/render.mjs") if "motion-showreel" in p.as_posix()]
    if not found:
        say("MISSING the motion-showreel plugin (the renderer; free, MIT). Install it (ask the person first):\n"
            "    claude plugin marketplace add ConardLi/garden-skills\n"
            "    claude plugin install motion-showreel-skills@garden-skills\n"
            "  (inside Claude Code the same two lines start with /plugin instead of claude plugin)")
    say("animation: done" + ("" if found else " (plugin still to install)"))


def install_music_fit():
    need_core()
    pip("install", "-r", STUDIO / "requirements" / "music_fit.txt")
    set_value("components", "music_fit", "true")
    say("music_fit: done")


def install_score():
    need_core()
    pip("install", "-r", STUDIO / "requirements" / "score.txt")
    download(SOUNDFONT, STUDIO / "soundfonts" / "GeneralUser-GS.sf2")
    set_value("components", "score", "true")
    if not shutil.which(cfg().get("music", {}).get("fluidsynth", "fluidsynth")):
        say(f"MISSING the FluidSynth program: install it, then run `status` again:\n    {which_hint('fluidsynth')}")
    say("score: done")


# ------------------------------------------------------------------------------------------------ remove / status

def remove(part):
    c = cfg()
    if part == "whisper":
        for d in (STUDIO / "models").glob("faster-whisper-*"):
            shutil.rmtree(d)
        if PY.exists():
            pip("uninstall", "faster-whisper", "ctranslate2", "onnxruntime", "tokenizers", "av", "huggingface_hub")
        set_value("components", "whisper", "false")
    elif part == "animation":
        shutil.rmtree(STUDIO / "web" / "node_modules", ignore_errors=True)
        say("  the browser itself lives in Playwright's shared cache; to delete it too:  npx playwright uninstall --all")
        set_value("components", "animation", "false")
    elif part == "music_fit":
        pip("uninstall", "librosa", "numba", "llvmlite", "scikit-learn")
        set_value("components", "music_fit", "false")
    elif part == "score":
        shutil.rmtree(STUDIO / "soundfonts", ignore_errors=True)
        pip("uninstall", "mido")
        set_value("components", "score", "false")
    elif part == "fonts":
        for f in (STUDIO / "web" / "fonts").glob("*.ttf"):
            f.unlink()
    elif part == "core":
        raise SystemExit("to remove everything, delete the studio folder itself (your project folder is separate and is not touched)")
    else:
        raise SystemExit(f"unknown part {part}")
    _ = c
    say(f"{part}: removed")


def has_pkg(name):
    if not PY.exists():
        return False
    return subprocess.run([str(PY), "-c", f"import {name}"], capture_output=True).returncode == 0


def status():
    c = cfg()
    rows = []
    ff = ffmpeg_path()
    rows.append(("core", PY.exists() and has_pkg("pedalboard") and bool(ff), size(VENV),
                 "" if ff else f"ffmpeg missing ({which_hint('ffmpeg')})"))
    fonts = STUDIO / "web" / "fonts"
    want = c.get("fonts", {}).get("subtitle_files", [])
    rows.append(("fonts", bool(want) and all((fonts / f).exists() for f in want), size(fonts), ""))
    model = STUDIO / c.get("whisper", {}).get("model", "models/faster-whisper-large-v3")
    rows.append(("whisper", has_pkg("faster_whisper") and (model / "model.bin").exists(), size(STUDIO / "models"), model.name))
    plugin = [p for r in (Path.home() / ".claude" / "plugins", Path.home() / ".claude" / "skills") if r.exists()
              for p in r.rglob("scripts/render.mjs") if "motion-showreel" in p.as_posix()]
    nm = STUDIO / "web" / "node_modules"
    rows.append(("animation", (nm / "playwright").exists() and bool(shutil.which("node")) and bool(plugin), size(nm),
                 "" if plugin else "motion-showreel plugin not found" if (nm / "playwright").exists() else ""))
    rows.append(("music_fit", has_pkg("librosa"), 0, ""))
    fs = shutil.which(c.get("music", {}).get("fluidsynth", "fluidsynth"))
    rows.append(("score", has_pkg("mido") and (STUDIO / "soundfonts" / "GeneralUser-GS.sf2").exists() and bool(fs),
                 size(STUDIO / "soundfonts"), "" if fs or not has_pkg("mido") else "FluidSynth program missing"))
    say(f"studio: {STUDIO}\nconfig: {CONFIG}{'' if CONFIG.exists() else '  (not written yet)'}\n")
    for name, ok, sz, note in rows:
        chosen = c.get("components", {}).get(name, True) if name in ("whisper", "animation", "music_fit", "score") else True
        state = "installed" if ok else ("not installed" if chosen else "skipped (not needed)")
        say(f"  {name:10s} {state:22s} {mb(sz) if sz else '':>8s}  {note}")
    say(f"\n  render cache: {mb(size(STUDIO / 'render'))} (safe to delete)   whole studio folder: {mb(size(STUDIO))}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    opt = {a[i]: a[i + 1] for i in range(len(a) - 1) if a[i].startswith("--")}
    if not a or a[0] == "list":
        for name, p in PARTS.items():
            say(f"{name}\n  for: {p['need']}\n  download: {p['size']}\n  {p['what']}\n")
    elif a[0] == "status":
        status()
    elif a[0] == "set" and len(a) == 4:
        set_value(a[1], a[2], a[3])
    elif a[0] == "install" and len(a) >= 2:
        {"core": install_core, "fonts": lambda: install_fonts(opt.get("--script")),
         "whisper": lambda: install_whisper(opt.get("--model", "large-v3")), "animation": install_animation,
         "music_fit": install_music_fit, "score": install_score}[a[1]]()
    elif a[0] == "remove" and len(a) == 2:
        remove(a[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
