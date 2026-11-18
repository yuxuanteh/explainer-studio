---
name: studio-setup
description: Set up, update, move or uninstall the Explainer Studio video pipeline. Checks the computer first and says about how long each pipeline step will take on it, explains what every tool is for and asks whether the person needs it BEFORE installing it (so unneeded parts are skipped and disk space is saved), interviews the creator about their channel, lets them choose a house style from side-by-side pictures (three examples next to the look they have now), asks how they want music, carries over the settings of an older Explainer Studio (v0.1) and runs a try-it sample. Use when the user installs the explainer-studio plugin, says "set up my studio / channel", wants to start a first episode without a studio, wants to add or remove a part (speech model, animation engine, music), asks how long things will take on their computer, updates the plugin, moves to another machine, or wants to uninstall.
---

# Studio setup

The person may not code. You do every command; they answer questions and look at pictures. Speak their language,
short sentences, everyday comparisons for technical things.

**Three rules that hold for the whole setup**
1. **Nothing is downloaded or installed before the person has said yes to that part**, knowing what it is for, who can
   skip it and how big it is. One question per part (AskUserQuestion when available). A "no" is respected and
   recorded; it can be installed later with one sentence.
2. **Measure before promising.** Run the hardware probe first and tell them what their computer will take per
   step, in plain words, before they choose parts.
3. **Never overwrite what exists.** An existing studio, project folder, `studio.toml`, `CHANNEL.md` or house style
   is read, compared and kept unless the person chooses the change.

The plugin's files sit next to this skill: `<this skill's base directory>/../../studio/` (tools, templates, kit),
`../../channel-template/`, `../../examples/`. Below, `<plugin>` means `<this skill's base directory>/../..`.

## 0 · What is already here?
Before asking anything, look:
- an existing studio folder (a `studio.toml` beside `scripts/`), a project folder with `CHANNEL.md`;
- an **older Explainer Studio (v0.1)**: `studio.toml` with a full `[palette]` and `[fonts] title = ...`, a
  `scripts/gs_shotkit.py` or `templates/episode/shots.py` (Manim), `[music] soundfont`, episodes with `shots.py`;
- which Claude Code plugins are installed (`motion-showreel` for animation).

Then say in two or three lines what you found and which of the three paths this is: **new set-up**, **update of an
existing studio** (section 9), or **upgrade from v0.1** (section 8).

## 1 · The computer: what it is and how long things will take
Run the probe from the plugin copy; it needs only Python (use `uv run --python 3.12 --no-project python`, or any
`python` 3.11+; if neither exists, install uv first: ask, it is about 30 MB):

```
python <plugin>/studio/scripts/probe.py --minutes <their usual video length, default 6> --short 1
```

Tell the person, in their language and in a small table:
- what the computer is (processor, memory, graphics card, free disk space);
- its speed against the reference laptop (the probe prints percentages);
- **about how long each step takes** for a video of their length: writing down the recording (speech
  recognition), the automatic cut and voice cut, the 480p animation build, the 1080p master, and the total;
- everything under "WORTH KNOWING" (little memory → a smaller speech model; an NVIDIA card → speech recognition on
  it; a hardware encoder; low disk space).

Be honest about the estimate: it is rough (half to double), the computer's own time only, spread over days of work,
and their own reviewing comes on top. Offer `--model medium` / `small` numbers if the large model looks slow
(over ~20 minutes for one video) or memory is under 8 GB. Run the probe again after `core` is installed: with ffmpeg
present it also measures a real video encode and finds hardware encoders.

## 2 · Interview (one message, then wait)
Ask, offering defaults:
- Channel name, short name (2–3 letters, used where there is no logo), tagline, website.
- Topic and audience (who, what level, which country: this decides examples, terms and spelling).
- Narration language; subtitle languages (burned-in = the narration; up to two translated subtitle files).
- Presenter name and an honest one-line description for the name tag (never a title they do not hold).
- What they make: long videos with a teaser short, standalone shorts, both; on camera, voice only, or both.
- Where the **project folder** lives (their scripts, recordings and finished videos; may be a synced folder such as
  Google Drive / Dropbox / OneDrive) and where the **studio folder** lives (tools, speech model, render cache: on a
  local disk, not synced, because it holds thousands of small files).
- Logo files if they have any (a square mark for the corner, a round badge for the intro).

## 3 · The parts: explain, ask, then install
`python <plugin>/studio/scripts/setup_studio.py list` prints every part. For each one, tell the person **what it
does for them, who can skip it, how big it is and how long the download takes on their connection**, then ask.
Recommend from the interview (a voice-only channel without on-screen graphics does not need the animation part; a
channel without music needs neither music part).

| Part | What it gives | Skip it when | Size |
|---|---|---|---|
| `core` | the studio's own Python + ffmpeg: cutting, mixing, subtitles, encoding | never | about 350 MB |
| `fonts` | free fonts for subtitles and on-screen text | never | 3 MB (Latin) – 45 MB (Chinese / Japanese / Korean) |
| `whisper` | speech recognition on their own computer: the automatic first cut, subtitle timing, sorting a recording session | their videos have no spoken voice | 3.1 GB (large-v3) · 1.7 GB (medium) · 0.7 GB (small) |
| `animation` | animated shots, chapter and end cards, the intro, labels over camera shots; also the style comparison pictures | they only want camera footage cut, subtitled and mixed (animation shots become plain text cards) | about 500 MB + the free `motion-showreel` plugin |
| `music_fit` | fits a music track to the cut on bar lines, ending on the track's own ending | no music, or the programmed score | about 300 MB |
| `score` | music composed by Claude note by note, played through a SoundFont | they use library tracks, their own music, or none | about 40 MB + FluidSynth |

For `whisper`, ask which model with the probe's time estimates side by side: **large-v3** hears best, also with a
second language mixed in; **medium** is half the size and about twice as fast; **small** is for old or small
computers and mishears names and technical terms more often.

Order once choices are made (each command only after its yes):
1. Copy the plugin's `studio/` folder to the studio location (never over an existing studio: see section 9), then
   `cp studio.example.toml studio.toml` and set `[paths] project`.
2. `python scripts/setup_studio.py install core` (makes `<studio>/.venv`; from here on use that Python:
   `.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere). If it prints `MISSING ffmpeg`, show the
   one-line install command it gives, ask, run it, and set `[paths] ffmpeg_bin` to the folder when ffmpeg is not on
   PATH in a new shell.
3. `install fonts` (after the narration language is in `studio.toml`; `--script sc|tc|jp|kr|latin` to override).
4. `install whisper --model <choice>` · `install animation` · `install music_fit` · `install score`: only the ones
   chosen. For every part they declined, record it: `setup_studio.py set components <part> false`.
5. `animation` needs the **motion-showreel** plugin (free, MIT, by ConardLi): its scripts render the frames. If the
   installer says it is missing, say what it is, ask, then run in the terminal
   `claude plugin marketplace add ConardLi/garden-skills` and
   `claude plugin install motion-showreel-skills@garden-skills` (the person can type the same with `/plugin` inside
   Claude Code). Rendering works at once; the plugin's own skill (the craft of motion) loads in the next
   conversation. Node.js 18+ is needed too; the installer prints the install command if it is missing.
6. `python scripts/setup_studio.py status`: read it to the person in one or two lines (what is installed, what was
   skipped, how much disk the studio uses).

## 4 · Write the settings
`setup_studio.py set <section> <key> <value>` writes one value and keeps the file's comments (values are TOML: text
in double quotes, lists in brackets). From the interview: `[channel]` (name, short_name, tagline, website,
presenter, presenter_title, the labels in their language: subscribe_label, comment_label, watch_label,
diagram_label, short_cta), `[language]` (narration, subtitle_main / _second / _third, length_unit = "cjk" for
Chinese or Japanese else "words", pace 3.9 characters or 2.5 words per second until measured on a first recording,
max_cue 20 or 12, whisper_prompt_prefix, new_idea_words in their language), `[ui] language` ("en" or "zh": the
review and editing pages and the reports), `[video] final_encoder` (the hardware encoder the probe found, if any),
`[whisper] device`.

Then the project folder: `CHANNEL.md` and `CLAUDE.md` from `<plugin>/channel-template/` filled in from the
interview, `voice-examples.md` (empty template: how this person talks, filled from their own recordings and their
edits of scripts), `brand/logo/` (their logo files as `watermark.png` and `seal.png`), `episodes/`, `shorts/`,
`music/`. If the narration is not English, translate `<studio>/templates/episode/script.md` and
`templates/short/script.md` into it once and save them as `<project>/templates/episode/script.md` and
`<project>/templates/short/script.md` (the tools use those when they exist); keep the shot ids and the `[CAM]`
markers as they are.

## 5 · House style: choose from pictures
One house style for the channel (or one per field of the channel): cards, the intro, labels, the ground of every
animated shot and the burned subtitles all follow it. Needs the `animation` part; without it, skip to section 6
(subtitles then use the default look).

1. `python scripts/gs_styles.py preview` renders the same sample shot four ways into
   `<project>/brand/styles/compare.png`: **CHANNEL** (their own colours from `[palette]`: for someone upgrading,
   this is the look they have now) beside the three examples **BLUEPRINT** (technical drawing), **CHALK**
   (chalkboard) and **POSTER** (flat editorial). Send the picture (SendUserFile) and say in a line each what the
   three are and which topics they suit. Add `--vertical` for the 9:16 version if they make shorts.
2. Ask: one of the three, keep their current look, or a style of their own. **Suggest** one from the topic and say
   why (a history channel and a blueprint grid do not belong together).
3. A style of their own: copy the nearest entry in `web/kit/themes.json` under a new name, change colours, ground
   (`grid` / `dust` / `paper` / `flat`), name-tag plate and title font from what they describe or from their logo's
   colours; add a drawing piece to `web/kit/house.js` when the style needs one (a texture, a symbol set). Preview
   again beside the others, change, repeat until they say yes. Follow visuals.md of the explainer-episode skill.
4. `python scripts/gs_styles.py use <ID>` writes `[style] house`. Note the decision and the reason in `CHANNEL.md`.
5. Offer once: "the intro (4 seconds, on every video) is a plain starting version: redesign it around your logo?"
   If yes, rewrite `web/kit/intro.js` in the chosen style, render stills, and show them before finishing.

## 6 · Music: ask how they want it
Explain the choices in one line each and ask (one answer; it can change later):
- **Library tracks**: they download finished tracks (for example the YouTube Audio Library, free with a YouTube
  account; other libraries need their own licence) into `<project>/music/` as `Title - Artist.mp3`. Claude proposes
  a shortlist per video by mood, they listen and pick, the track is fitted to the cut. Sounds like real music.
  Needs `music_fit`. A used-list (`music-used.md`) keeps tracks from repeating too soon.
- **Their own music**: the same, with tracks they made or commissioned. Needs `music_fit`.
- **Programmed score**: Claude composes the music note by note for each video and it is played through a
  SoundFont. No downloads, no licences to check, fits the cut exactly; sounds simpler, like game music. Needs
  `score`. **For someone coming from v0.1 this is what they have now: ask plainly whether to continue with it or
  change**, and say what changes for them either way.
- **No music.**
- **Something else they prefer** (a subscription library, a composer): record what they say in `CHANNEL.md` and
  treat the files as "their own music".

Write the answer: `set music mode "library" | "own" | "score" | "none"`, and install the part it needs if it was
not chosen in section 3 (ask again, with its size).

## 7 · Try it (optional, offer it)
`python scripts/make_sample.py` makes a four-line sample short and has the computer's own voice read it like a real
session (a spoken slate, a slip, the line read again). Then `python scripts/gs_run.py ss900-sample voicecut`, start
the pages (`python scripts/gs_review.py`, http://localhost:8770) and let the person watch the cut, leave a note and
try the editing page; with the `animation` part, `gs_run.py ss900-sample preview`. Say what each thing they see is.
Use the measured time of this run to correct the estimate from section 1 ("the sample took 2 minutes, so a
6-minute video is nearer 12 than 9"). Delete the sample when they are done (the three folders `make_sample.py`
names). If there is no voice for their language, they read the four lines into their phone instead.

## 8 · Upgrading from Explainer Studio v0.1
Version 2 changed the pipeline. Go through this list with the person: say what they have now, what version 2 does
instead, **suggest**, and **ask** for each one. Never assume.

| What they have (v0.1) | Version 2 | What to do |
|---|---|---|
| A palette per episode, channel colours in `[palette]` | One house style for the channel | Their `[palette]` becomes the CHANNEL look. Show it beside the three examples (section 5) and ask: keep it, take an example, or build their own from their colours |
| Manim animation (`shots.py`, `cam_cg.py`) | Web animation engine (`web/ep/<id>/`), Manim removed | Finished episodes stay as they are (their MP4s are final). New episodes use the new engine. Ask whether any unfinished episode should be redone in it. Manim itself can be uninstalled to free about 500 MB: ask |
| Programmed score (FluidSynth + SoundFont) | Music is their choice | Section 6: continue with the programmed score, switch to library tracks or their own, or none. Their generated loops and stings in `brand/music` keep working with mode "score" |
| A hand-written cut list per episode (`make_edl.py`), rough cut reviewed at 480p | Automatic first cut, a voice-cut stop before any animation, review page + editing page | Explain the new stop and show it on the sample (section 7) |
| Fonts installed in the operating system | Fonts live in `<studio>/web/fonts` | `install fonts`; the old ones can stay |
| Three title options, LinkedIn text | One title; posts by platform | Ask which platforms they post to; record in `CHANNEL.md` |
| `studio.toml` (v0.1 keys) | New keys: `[components]`, `[ui]`, `[style]`, `[music] mode`, `subtitle_third`, labels in `[channel]` | Keep their file; add only the missing keys (`setup_studio.py set`), never replace it |
| The channel-website skill | Not part of version 2 | Their site keeps working. Version 0.1 of the plugin stays available as the git tag `v0.1.0` if they want that skill |

Back up first: copy their studio's `scripts/`, `templates/`, `episodes/`, `studio.toml` to
`<project>/studio-code-backup-v0.1/`. Then copy the new `scripts/`, `templates/`, `web/kit/`, `requirements/` in
(their `episodes/`, `studio.toml`, `models/` are not touched; the Whisper model they already downloaded is reused).

## 9 · Updating, moving, uninstalling
- **Update the plugin**: the person runs `/plugin marketplace update explainer-studio` then
  `/plugin update explainer-studio@explainer-studio` (or reinstalls). Then compare `<plugin>/studio/` with their
  studio: copy changed files of `scripts/`, `templates/`, `requirements/` and `web/kit/*.js` after
  `python scripts/backup_code.py`. **Never overwrite** `studio.toml`, `web/kit/themes.json` (their style lives
  there: merge new entries only), `web/kit/intro.js` and `house.js` if they changed them (compare first, show the
  difference, ask), `web/kit/fonts.css`, anything under `episodes/`, `shorts/`, `web/ep/`. New settings:
  add the missing keys from `studio.example.toml`. Read `CHANGELOG.md` and tell them what changed for them.
- **Free disk space**: `setup_studio.py status` shows what uses it. `remove whisper` (the model, up to 3 GB),
  `remove animation`, `remove music_fit`, `remove score`; the render cache (`<studio>/render`) can always be
  deleted, finished videos are in the project folder. Ask before each removal and say what stops working.
- **A smaller or larger speech model later**: `install whisper --model <name>`, then delete the old model folder
  in `<studio>/models` after asking.
- **Move to a new computer**: the project folder comes along by itself if it is synced; on the new machine run
  this setup again, choose the same parts, then copy `studio.toml`, `episodes/`, `shorts/`, `web/ep/` and
  `web/kit/` back from `<project>/studio-code-backup/` (`backup_code.py` keeps that copy current). Run the probe
  again: the time estimates change with the machine.
- **Uninstall everything**: delete the studio folder (tools, model, cache); the person removes the plugin with
  `/plugin uninstall explainer-studio@explainer-studio`. The browser used for animation sits in Playwright's shared
  cache: `npx playwright uninstall --all` removes it. Their project folder (scripts, recordings, videos) is theirs:
  never delete it.

## 10 · Finish
One short message: what is installed and what was skipped (with the sentence that adds a skipped part later), the
house style and music choice, where the two folders are, the time estimate for their usual video, and how to
start: "Start a new episode about …". Save the decisions in `<project>/CHANNEL.md` so a new conversation knows them.
