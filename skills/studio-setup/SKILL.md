---
name: studio-setup
description: Set up (or move to a new computer) the Explainer Studio video pipeline - interview the creator about their channel, create the synced project folder and the local studio folder, install Python 3.12 + Manim + faster-whisper + ffmpeg + FluidSynth + fonts, download the Whisper model and SoundFont, write studio.toml, CHANNEL.md and CLAUDE.md, build the channel's music library and intro sting, and verify everything with doctor.py. Use when the user installs the explainer-studio plugin, says "set up my studio / channel", wants to start their first episode without a studio, or moves the pipeline to another machine.
---

# Studio setup

Goal: a creator who may not code ends up with a working studio and a filled-in channel profile, ready for the
**explainer-episode** skill. Work in this order and **stop for confirmation** after the interview (step 1) and
before any large download.

The plugin's files are next to this skill: `<this skill's base directory>/../../studio/` (code and templates),
`../../channel-template/` (CHANNEL.md, CLAUDE.md, recording guide), `../../examples/` (a filled-in example).

## 1 · Interview (one message, then wait)
Ask, in the creator's language, and offer sensible defaults:
- Channel name, short name (2-3 letters for the badge fallback), tagline, website / socials / contact email.
- Topic area and audience (who, what level, which country / schooling - this decides terms and spelling).
- Narration language, subtitle languages (burned-in main + optional second SRT track), spelling standard.
- Presenter name and an honest one-line description for the name tag (no professional titles they don't hold).
- Colours (or "pick for me" -> propose 2-3 palettes as a swatch image), logo files if any.
- Hardware: OS, GPU (NVIDIA / Apple / Intel iGPU -> encoder choice), disk space (needs ~6 GB), camera / mic.
- Where the synced project folder should live (Google Drive / Dropbox / OneDrive / plain folder) and where the
  local studio folder should live (not synced: thousands of small render files slow syncing down).

## 2 · Folders
- Project (synced): `CHANNEL.md`, `CLAUDE.md`, `brand/{logo,fonts/static,music,sfx,templates}`, `episodes/`.
- Studio (local): copy the plugin's `studio/` contents in (`scripts/`, `templates/`, `extras/`,
  `requirements.txt`, `studio.example.toml`). Never copy over an existing studio without asking - on a move to a
  new computer, restore the user's `studio-code-backup/` instead and only add missing files.

## 3 · Install tools (ask before each download; say the size)
| Tool | Windows | macOS | Linux |
|---|---|---|---|
| uv (Python manager) | `winget install astral-sh.uv` | `brew install uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python 3.12 venv | `uv venv --python 3.12 <studio>/.venv` | same | same |
| packages | `uv pip install --python <venv python> -r <studio>/requirements.txt` | same | same |
| ffmpeg (full build, with libass) | `winget install Gyan.FFmpeg` | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| FluidSynth | release zip from github.com/FluidSynth/fluidsynth/releases into `<studio>/tools/fluidsynth` | `brew install fluid-synth` | `sudo apt install fluidsynth` |
| Manim system deps | none extra | `brew install pango pkg-config` if the wheel fails | `sudo apt install libpango1.0-dev` |

- New PATH entries are only seen by new shells: set `[paths] ffmpeg_bin` and `[music] fluidsynth` to absolute
  paths so scripts never depend on PATH.
- Whisper model (~3 GB): `<venv python> -c "from huggingface_hub import snapshot_download as d;
  d('Systran/faster-whisper-large-v3', local_dir=r'<studio>/models/faster-whisper-large-v3')"`.
  Smaller machines: `faster-whisper-medium` (worse with mixed-language narration). GPU: `[whisper] device = "cuda"`.
- SoundFont: GeneralUser GS by S. Christian Collins (free for music production, see its licence) from
  https://www.schristiancollins.com/generaluser.php -> `<studio>/soundfonts/GeneralUser-GS.sf2` (+ licence file).
- Fonts (all SIL OFL, from https://github.com/google/fonts/tree/main/ofl): the families named in `[fonts]`
  (defaults: Noto Sans SC, Noto Serif SC, Space Grotesk, Playfair Display, Manrope). Install them in the OS for
  the user (Windows: right-click -> Install; macOS: Font Book) and copy the static files named in
  `[fonts] subtitle_files` to `<project>/brand/fonts/static/` (for burned subtitles). For a non-CJK channel pick
  Latin fonts (e.g. Inter / Source Serif) and set `subtitle`, `subtitle_heavy`, `subtitle_files` to match.
- Known trap: faster-whisper's own decoder breaks with `av>=19`; `transcribe.py` already decodes with ffmpeg.

## 4 · Write the config files
- `<studio>/studio.toml` from `studio.example.toml`: paths, `[channel]`, `[language]` (pace stays 3.9 for
  Mandarin / ~2.5 words per second for English until measured on the first recording), `[palette]`, `[fonts]`,
  `[video] final_encoder` (test it with doctor.py), `[whisper]`, `[music]`.
- `<project>/CHANNEL.md` from `channel-template/CHANNEL.md`, filled in from the interview. Leave the
  "decisions log" empty; it grows episode by episode.
- `<project>/CLAUDE.md` from `channel-template/CLAUDE.md` with the real studio path.
- Optional `term_list` TOML (see `examples/terms-geoscience-zh.toml`) when the channel keeps technical terms in
  another language than the narration.

## 5 · Brand audio and intro
From `<studio>/scripts`: `python make_music.py` (loops, stings, SFX), `python ../templates/intro_audio.py`
(intro sting), render the intro once (`gs_episode.py` does it automatically, or
`manim -ql ../templates/intro.py Intro --media_dir ../render/intro`), then `python make_samples.py` and send the
30 s sample + intro preview. Offer to redesign `templates/intro.py` around the channel's logo and to change the
arrangements in `make_music.py` if the creator wants a different sound.

## 6 · Verify
`python doctor.py` must end with "all good" (warnings about optional items are fine). Then show the creator the
recording guide (`channel-template/RECORDING.md`, adapted to their camera and mains frequency) and suggest a
5-minute camera + voice test before the first episode. Tell them the next step: "start a new episode about ...".

## Branding changes (any time)
- **Logo**: put the file in `<project>/brand/logo/`; make a square watermark PNG (~256 px, transparent) and a round
  seal PNG (~2048 px) with Pillow (or from an SVG with cairosvg / a Manim render), set `logo_watermark` /
  `logo_seal` in `[channel]`, then rebuild the intro and render one end card to show it. Offer to redesign
  `templates/intro.py` so the intro animates the actual logo (keep the `INTRO_T` times or update
  `intro_audio.py` with them).
- **Colours**: propose palettes as a swatch image, then set `[palette]`; subtitles, end card, name tag, intro,
  thumbnails and the short follow automatically.
- **Fonts**: install the families in the OS, set `[fonts]` (+ the static files for burned subtitles), run
  doctor.py, render a chapter card and a subtitle frame to show them.
- **Music**: change arrangements in `make_music.py` / `gs_score.py`, re-run, send a 30 s sample.
- Record each choice in CHANNEL.md. For the website's look, use the **channel-website** skill.

## Moving to a new computer
Install the tools (step 3), copy `<project>/studio-code-backup/` back into a fresh studio folder (it includes
studio.toml - fix the paths), re-download the model and SoundFont, run doctor.py.
