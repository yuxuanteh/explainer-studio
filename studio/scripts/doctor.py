"""Check that the studio is ready: config, folders, ffmpeg + encoder, fonts, Whisper model, music tools.

    python doctor.py

Prints one line per check (ok / MISSING / WARN) and what to do about it. Run it after setup and on a new computer.
"""
import subprocess
import sys

import gs_env

problems = 0


def report(ok, what, fix=""):
    global problems
    if ok is True:
        print(f"  ok       {what}")
    elif ok is None:
        print(f"  WARN     {what}" + (f"\n           -> {fix}" if fix else ""))
    else:
        problems += 1
        print(f"  MISSING  {what}" + (f"\n           -> {fix}" if fix else ""))


def installed_font_files():
    import os
    from pathlib import Path
    dirs = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
            Path(os.environ.get("LOCALAPPDATA", "~")) / "Microsoft" / "Windows" / "Fonts",
            Path("~/Library/Fonts").expanduser(), Path("/Library/Fonts"), Path("~/.local/share/fonts").expanduser(),
            Path("~/.fonts").expanduser(), Path("/usr/share/fonts")]
    out = set()
    for d in dirs:
        if d.is_dir():
            out |= {p.name.replace(" ", "").replace("-", "").lower() for p in d.rglob("*") if p.suffix.lower() in
                    (".ttf", ".otf", ".ttc")}
    return out


def main():
    print(f"config   {gs_env.CONFIG_FILE}")
    print(f"studio   {gs_env.STUDIO}\nproject  {gs_env.PROJECT}\n")
    report(sys.version_info[:2] >= (3, 11), f"Python {sys.version.split()[0]}", "use Python 3.12 (uv python install 3.12)")
    report(gs_env.PROJECT.exists(), "project folder", "create it or fix [paths] project in studio.toml")
    report((gs_env.PROJECT / "CHANNEL.md").exists(), "CHANNEL.md (style bible)",
           "copy channel-template/CHANNEL.md from the plugin and fill it in")
    for d in ("episodes", "brand"):
        report((gs_env.PROJECT / d).exists(), f"project/{d}/", "created by the studio-setup skill")

    try:
        v = subprocess.run([gs_env.FFMPEG, "-version"], capture_output=True, text=True, check=True).stdout.split("\n")[0]
        report(True, v[:60])
        enc = gs_env.cfg("video", "final_encoder", ["-c:v", "libx264"])
        codec = enc[enc.index("-c:v") + 1] if "-c:v" in enc else "libx264"
        r = subprocess.run([gs_env.FFMPEG, "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x144:d=0.2",
                            "-c:v", codec, "-f", "null", "-"], capture_output=True, text=True)
        report(r.returncode == 0, f"final encoder {codec}",
               "this machine cannot use it: set [video] final_encoder to libx264 in studio.toml")
        r = subprocess.run([gs_env.FFMPEG, "-hide_banner", "-filters"], capture_output=True, text=True)
        report("subtitles" in r.stdout, "ffmpeg subtitles filter (libass)", "install a full ffmpeg build")
    except (OSError, subprocess.CalledProcessError):
        report(False, "ffmpeg", "install ffmpeg (winget install Gyan.FFmpeg / brew install ffmpeg / apt install ffmpeg)"
                                " or set [paths] ffmpeg_bin")

    try:
        import manimpango
        fonts = set(manimpango.list_fonts())
        files = installed_font_files()   # Pango's list misses per-user fonts on Windows; look at the files too
        for key, fam in gs_env.CFG.get("fonts", {}).items():
            if isinstance(fam, str) and key not in ("subtitle", "subtitle_heavy"):
                found = fam in fonts or any(f.startswith(fam.replace(" ", "").lower()) for f in files)
                report(found, f"font {fam}", "install it (double-click the .ttf -> Install); fonts.google.com, OFL")
    except ImportError:
        report(False, "manim / manimpango", "pip install -r requirements.txt into the studio venv")
    for f in gs_env.CFG.get("fonts", {}).get("subtitle_files", []):
        report(True if (gs_env.FONTS / "static" / f).exists() else None, f"subtitle font file brand/fonts/static/{f}",
               "copy the static .ttf there so burned subtitles use it")

    report((gs_env.WHISPER_MODEL / "model.bin").exists(), f"Whisper model {gs_env.WHISPER_MODEL.name}",
           "download Systran/faster-whisper-large-v3 from Hugging Face into [whisper] model")
    for mod in ("faster_whisper", "pedalboard", "soundfile", "mido", "cartopy"):
        try:
            __import__(mod)
            report(True, f"python package {mod}")
        except ImportError:
            report(False, f"python package {mod}", "pip install -r requirements.txt")

    import gs_sf
    try:
        subprocess.run([gs_sf.FLUIDSYNTH, "--version"], capture_output=True, check=True)
        report(True, "FluidSynth")
    except (OSError, subprocess.CalledProcessError):
        report(False, "FluidSynth", "install it and set [music] fluidsynth")
    from pathlib import Path
    report(Path(gs_sf.SOUNDFONT).exists(), "SoundFont", "download GeneralUser GS and set [music] soundfont")
    music = gs_env.BRAND / "music"
    need = ["intro-sting.wav", "outro-sting.wav", "loop-curious.wav", "loop-tense.wav", "loop-calm.wav", "loop-epic.wav"]
    report(all((music / f).exists() for f in need) or None, "music library brand/music/",
           "run make_music.py and ../templates/intro_audio.py once")
    print("\nall good" if not problems else f"\n{problems} thing(s) to fix")


if __name__ == "__main__":
    main()
