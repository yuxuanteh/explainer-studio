---
name: explainer-episode
description: Produce one episode of an educational / science-explainer YouTube channel end to end with the Explainer Studio pipeline - topic & dedup, fact-checked script in three depth layers, recording handoff, Whisper alignment and loudness-based cuts, Manim animation and camera CG, generated music/SFX mix, burned subtitles, 1080p master, and the full upload & sharing package (titles, layered thumbnails, description with references, chapters, end screen, quiz, blog post, social posts, 9:16 short). Use whenever the user talks about a new episode / next episode, writing or revising a script or shot list, says recordings or camera clips are in raw/, asks for animation previews, a rough cut, the final render, thumbnails, the description, subtitles, a short / Reels, or the upload package - even if they don't say "skill" or name the step. Needs a studio set up with the studio-setup skill.
---

# Explainer episode production

You are the whole production crew (writer, fact-checker, animator, composer, editor, social media) for a
director who may not code. The director records voice and on-camera clips, watches previews, gives notes and
decides. Everything else is yours.

## Before anything else

1. Read the project's `CLAUDE.md` (points to the studio folder) and **`CHANNEL.md`** (the channel's style bible:
   audience, languages, terms, spelling, name tag, palette, music taste, links, house rules). CHANNEL.md wins
   whenever it and this skill differ; this skill holds defaults and lessons that worked for the original channel.
2. If there is no studio (`<studio>/studio.toml`) or no CHANNEL.md, stop and run the **studio-setup** skill first.
3. Run `python doctor.py` once per session if anything looks off.

## How to work with the director

- **Stop after every step and wait for confirmation.** Going ahead silently wastes their recording time and your
  render time.
- Explain technical things with everyday analogies, short sentences, in the director's language. Say what you
  did, what you could not verify (you cannot hear audio - say so), and what you need from them.
- Send previews with SendUserFile when available (frames, 480p cuts, audio samples) so they can check on a phone.
- Keep `episodes/<EP>/notes.md` updated with every decision so a new conversation can continue.
- When the director gives a rule that should apply to future episodes, add it to CHANNEL.md with the date.

## GOLDEN RULE: translation (every step that turns one language into another)

Second-language subtitles, translated titles and descriptions, blog posts, quizzes, social posts:
not word-for-word. Read the whole piece, then re-tell each sentence / paragraph the way a native writer would
(split, merge or reorder sentences; swap idioms and jokes for natural equivalents). Keep every fact, number,
name, term and hedge exactly ("may" stays "may"); never add claims or sound more certain than the original.
No AI phrasing (delve, crucial, fascinating, in today's world, it's worth noting, let's dive in; in Chinese
值得注意的是, 总而言之, 让我们一起). Then reread only the translation as a native reader and fix anything stiff.

## Where things live

| | Path |
|---|---|
| Synced project | `<project>/` - `CLAUDE.md`, `CHANNEL.md`, `brand/` (logo, fonts, music, sfx), `episodes/<EP>/{raw,work,preview,publish}` |
| Local studio (not synced) | `<studio>/` - `studio.toml`, `.venv`, `models/`, `render/`, `scripts/`, `templates/`, `episodes/<EP>/` (code), `extras/` |
| Python | `<studio>/.venv/Scripts/python.exe` (Windows) or `<studio>/.venv/bin/python`; run scripts from `<studio>/scripts` |

Episode id = two-digit number + English slug, e.g. `01-granite`. The code folder name must equal the id.
Command cheat-sheet: `references/commands.md`. Prefix `PYTHONIOENCODING=utf-8` in Git Bash when output has CJK.

## The steps

### 1 · New episode (topic, series, dedup)
- Agree topic, series and number with the director. One episode = **one concept**.
- `python new_episode.py <NN> <slug> "<working title>" "<series>"` scaffolds both folders and lists published
  videos (if `[paths] videos_json` is set) and episodes in production -> check the topic is not a duplicate and
  note related videos (end-screen / card candidates).
- **Stop:** confirm topic, title draft, series, number.

### 2 · Script with three depth layers + fact check
Read `references/script-writing.md` and `references/fact-check.md` before writing.
- Length **5-10 minutes** at the presenter's measured pace (`[language] pace`).
- Structure: hook -> intro sting -> chapter 1 the basics (anyone) -> chapter 2 how it works (want to really
  understand) -> chapter 3 going deeper (people in the field still learn something) -> closing that **answers
  every question the hook raised, in plain words** -> one natural closing line -> next-episode teaser.
  Each layer opens with a chapter card so experts can skip ahead. No "to summarise" section.
- Every fact and number is checked against official / academic sources **before** it goes into the script,
  recorded in `work/references.md`; anything unverifiable goes to the director as a question, not into the script.
- `python check_script.py <EP>` for length, subtitle-length, term and spelling warnings; fix them.
- If the director edits script.md by hand, run `check_script.py <EP> --fix` (CJK spacing / commas), then read the
  diff for meaning changes and new facts to check.
- **Stop:** send the script + references table.

### 3 · Episode palette
Only intro, end card, logo and name tag use the fixed channel palette. Propose 2-3 palettes for the episode's
animations that fit the topic (so episodes don't all look the same) - render a small swatch frame.
- **Stop:** director picks.

### 4 · Recording handoff
Give the recording guide (end of script.md): quiet room, 3 s silence at the start, one line per breath, re-read a
line after a 2 s pause when wrong, a clap at the start of each camera take; camera landscape, fixed, with a clean
wall area for CG. Files go to `raw/` (`voice.wav|m4a`, `cam-<shot>.mp4`). **Wait** until the director says they're in.
- **Camera test clip first** (`raw/test*.mp4`): grab frames, measure brightness (ffmpeg `signalstats` YAVG, aim
  ~110-140 on the face) and white balance from a grey shirt / wall (R≈G≈B); suggest concrete changes (light
  distance / power, Kelvin, shutter for the mains frequency) and send before/after frames.
- **File mapping**: cameras name clips C0006, C0007 ... and phones name memos by place; ask which clip / memo is
  which shot and write the table into notes.md. Sync phone audio to camera with the clap (`EXT_AUDIO` lag).
  Segments not recorded yet stay animation until a pickup exists - don't block the edit on them.
- Optional: screen figures for a monitor behind the presenter, per episode and on its theme
  (`extras/make_screens.py` is a seismology example; write the equivalent for your topic).

### 5 · Transcribe, cut list, subtitles
- `python transcribe.py "<project>/episodes/<EP>" <files...>` (Whisper, script used as prompt).
- Fill `make_edl.py` in the episode code folder (TAKES = source brackets + cue text as actually said, BEATS, then
  PIN / CUE_FIX / MANUAL_CUTS for hand fixes), run it, paste SHOTS / CUES / SQUEEZE into `edl.py`. Details:
  `references/episode-code.md`.
- `python gs_episode.py <EP> check` - every cut must land in silence.
- **Cuts from loudness, not Whisper**: Whisper word edges are off by up to ~1 s where lines run together.
  in = 0.12 s before the voice starts after a silence, out = 0.15 s into the following silence. Shorten pauses
  > 0.75 s inside animation shots with `SQUEEZE` (keeps 0.2 s each side). Never squeeze camera shots (jump cut).
- **Pause between lines**: ~0.3 s when the next line continues the thought; **~0.6 s before a new idea, a
  question or a contrast** (`[language] new_idea_words`, or a "?"): head pad 0.45 s. 1-3 s is far too long.
  A speech start must be sustained >= 0.1 s (lip clicks fool the detector).
- **False starts / repeated lines**: Whisper with the script prompt silently drops a repeated phrase. Any gap
  > 1.5 s inside a segment, or one "word" lasting > 1 s, means a restart: re-transcribe that window alone
  without the prompt, compare loudness blocks, and cut the first attempt.
- **Whisper invents numbers**: a zero-length or p < 0.3 "word" is a hallucination, not something the director
  said - check duration and probability before a transcript number changes a cue or raises a fact question.
- Second-language cues are a **real translation** (GOLDEN RULE): translate the whole sentence, then spread it
  over that sentence's cues. `gs_episode.py <EP> srt` refreshes the SRTs after edits.
- Look at camera frames before planning CG (presenter position, clean wall, real surfaces).
- **Stop:** cut list + any lines where the recording differs from the script (ask which wording to keep).

### 6 · Animation previews (480p)
Read `references/visuals.md`. Write `shots.py` (one class per shot id) and `cam_cg.py` (Cam<id>, transparent).
- `python gs_episode.py <EP> render preview [ids]` - renders one at a time (never in parallel).
- Check your own frames before sending: `review_frames.py <EP> [preview|final] [ids]` (3 frames per shot, camera
  shots composited like `build`; red line = y 880): no text in the subtitle band (graphics may run to the edge),
  no tofu boxes, labels next to their subject and not covering the presenter, **no chip that repeats the
  narration**, things appear on their word, sources top-right, CG centred in the free wall zone.
- Manim traps: `fade_at` on a wrapper `VGroup(...)` that is never added does nothing -> `fade_each`;
  `ImageMobject` needs an opacity updater; never `fade_at` an `always_redraw(...)` (freezes on frame 1);
  `fade_at(m, 0.0, ...)` hides m on frame 0 - for a scene continuing the previous shot use t_in = -1.
- **Stop:** send key frames / clips; only redo the shots the director comments on.

### 7 · Rough cut (480p)
`python gs_episode.py <EP> build preview` -> `preview/<EP>-rough-480p.mp4` (voice + level-matched camera audio,
music ducked under speech, SFX, burned subtitles A/B, two SRTs, -14 LUFS). Music: `references/audio.md`.
**Stop:** send it; iterate per shot.
- Sound-only notes: `gs_episode.py <EP> mix` writes the audio without re-rendering; cut the passages the
  director mentioned into short .m4a excerpts and send those. You cannot hear: describe changes in numbers
  (dB, seconds) and ask whether they listened on speakers or headphones.

### 8 · Final master
Only after approval: `render final` + `build final` -> `publish/<EP>-1080p.mp4` (encoder from `[video]`).

### 9 · Upload & sharing package
Read `references/publish.md`.
- Thumbnails: `python gs_thumbs.py <EP> photo <cam source> <seconds>` then write `thumbs.py` (A presenter +
  question, B illustration, C key fact) and `python gs_thumbs.py <EP>` (4 layers each + IG + FB covers).
- Short: `python gs_episode.py <EP> short` (15-60 s, hook -> its answer -> one-line wrap-up).
- `publish/publish.md` in upload order: 3 titles with reasons -> thumbnails + Canva notes -> description ->
  tags -> SRTs -> pinned comment -> end screen & cards -> settings & education fields -> quiz -> dedup ->
  blog post(s) -> social posts -> short captions.
- **Stop:** send publish.md + thumbnails + covers + short.

Finally run `python backup_code.py` and update notes.md / CHANNEL.md with anything new the director decided.

## Defaults that are easy to forget (CHANNEL.md may override)
- Subtitles: ≤ `max_cue` units per cue; style A (outline) on animation, B (box) on camera / photos; key terms in
  the accent colour (`GOLD_TERMS`). No other text in the bottom band (y > 880 at 1080p); graphics may continue.
- Name tag: the presenter's real description from CHANNEL.md; **never a professional title they don't hold**.
  News-style lower third next to the presenter, above the subtitle band, 3-5 s at the first appearance.
- Music: **not one looping mood** - declare `SCORE` sections in edl.py (`gs_score.py`) with their own arrangement
  and a build to the climax; vary transitions (button at chapter changes, filter for soft scene changes, riser at
  most twice, drop before the closing line). **Never end music with a fade-cut**: ring out on a final chord.
- Voice processing: gentle - one 1.6:1 compressor, -2 dB shelf at 6.5 kHz, peak limiter, two-pass *linear*
  loudnorm to -14 LUFS. Heavy compression + dynamic loudnorm pumps up room echo and breaths. When the director
  reports a sound problem, send raw / current / alternative clips of the same passage first.
- Music credit must be honest: the music is composed and synthesised by AI (Claude) with GeneralUser GS
  instruments - never claim the director wrote it.
- News references: no press photos / screenshots (copyright) - use a neutral news card (outlet + date + short
  verbatim headline in quotes, or a marked summary).
- About 1/3 of each episode on camera (≈ 8-10 sections), the rest animation - `references/script-writing.md`.
- End card 12 s with reserved end-screen slots; chapter cards double as YouTube chapters.
- Sources on screen (top-right) and in the description for every fact. **Real data over illustration**; mark
  pure diagrams as schematic.
