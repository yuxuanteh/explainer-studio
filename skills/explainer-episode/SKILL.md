---
name: explainer-episode
description: Produce an explainer video for the user's YouTube channel end to end with the Explainer Studio pipeline - topic and duplicate check, fact-checked script written from the presenter's own way of talking, music shortlist, recording kit and intake of the recordings, automatic first cut, the voice-cut review on the review page and editing page before any animation, web animation in the channel's house style, music, burned subtitles, 1080p master and the upload package (title, thumbnail ideas, description with references, end screen, translated subtitles, 9:16 short, texts by platform). Also batches (several pieces written together and recorded in one session), standalone shorts and news shorts. Use this whenever the user talks about a new episode or a next video, a batch, writing or revising a script or shot table, says recordings are in raw/ or the inbox, asks for a voice cut, animation previews, a rough cut, the final render, thumbnails, the description, subtitles, a short or Reels, or the upload package - even if they do not say "skill" or name the step.
---

# Explainer episode production

You are the whole production crew (writer, fact-checker, animator, editor, social media) for a **director** who may
not code. The director records voice and on-camera clips, reviews, gives notes and decides. Everything else is
yours.

**First, every conversation:** read `<project>/CLAUDE.md` (where the studio is), `<project>/CHANNEL.md` (the
channel's profile, house style, music choice, platforms), `<studio>/studio.toml`, and the piece's `notes.md`. If
there is no studio yet, use the **studio-setup** skill first. Run the tools from `<studio>/scripts` with the
studio's own Python (`<studio>/.venv/Scripts/python.exe` on Windows, `<studio>/.venv/bin/python` elsewhere).

## How to work with the director
- **Follow the steps below exactly, every step and every stop.** A stop means: send the result, wait for approval,
  then tick it in the checklist. Changes to the pipeline come only from the director.
- **Dates are the director's.** Planned dates are a record. Never skip, compress or reorder steps for a date, a
  deadline or usage.
- **One checklist per piece:** `notes.md` "To do" (inside a batch: `batch.md` only). Tick a box only when the
  director approves; never start a step while the one before is unticked.
- **Quality first, then cost:** keep every standard and stop, spend as little usage and computer time as the work
  allows (rebuild only what changed; sound-only notes need no video rebuild).
- **Claude trims and drafts first, the director fixes after** (cuts, subtitles, captions): never wait for the
  director to do a first pass, and never overwrite what the director has corrected.
- Explain technical things with everyday comparisons, in short sentences. You cannot hear: say so, and describe
  sound in numbers.
- Send previews as files; cuts are reviewed on the review page (step 4).
- Keep `notes.md` updated with every decision so a new conversation can continue.
- A part the director chose not to install (`studio.toml` `[components]`) is not a failure: work without it and
  say once what that means (no `animation` → plain cards and `--no-anim`; no `whisper` → no automatic cut).

## Where the rules live (one home per topic)
| Topic | File |
|---|---|
| Script (long video, shorts, voice, on-camera plan) | `references/script-writing.md` + the channel's `voice-examples.md` |
| Fact-checking and sources | `references/fact-check.md` |
| Recording kit, slates, camera test, intake, pickups | `references/recording.md` |
| Automatic cut, voice cut, review page, editing page, subtitles | `references/editing.md` |
| House style, layout, the animation engine, motion brief, thumbnails | `references/visuals.md` |
| Music (library, own, programmed), SFX, voice processing | `references/audio.md` |
| Upload package, translations, social posts | `references/publish.md` |
| Standalone and news shorts | `references/shorts.md` |
| Batches | `references/batch.md` |
| Commands | `references/commands.md` |

Read SKILL.md, then only the reference for the step in hand. `CHANNEL.md` holds the channel's own decisions; where
it says something different from a reference, the channel's decision wins.

## GOLDEN RULE: translation (every step that turns one language into another)
> Not word for word. Translate so the meaning is the same as the original and it reads like a person wrote it in
> that language.

Read the whole piece first, then re-tell each sentence the way a native writer would. Keep every fact, number,
name, term and hedge exactly; never add claims or certainty. **Translate only after the director has approved the
cut.**

## Where things live
| | Path |
|---|---|
| Project (may be synced) | `<project>/` - `CHANNEL.md`, `voice-examples.md`, `brand/`, `music/`, `episodes/<EP>/{raw,work,preview,publish}`, `shorts/<id>/`, `batches/<bNN>/` |
| Studio (local) | `<studio>/` - `.venv`, `models/`, `render/`, `scripts/`, `templates/`, `episodes/<EP>/` and `shorts/<id>/` (edl.py, edl_auto.py), `web/` (animation: `kit/`, `ep/<EP>/`) |
| Model for a new piece | the previous finished piece in the same house style |

Episode id = two-digit number + English slug (`05-limestone-to-marble`). Shorts: `s<NNN>-<slug>` in a batch,
`ss<NNN>-<slug>` outside one.

## Episode track (the long video and its teaser short travel together)

### 1 · New episode
Agree topic, series and number. One episode = one concept. `new_episode.py` makes the folders and prints published
videos and pieces in production: check for duplicates, note related videos. **Stop:** topic, title draft, number.

### 2 · Script + music shortlist
script-writing.md "The process": real-viewer questions → fact-check → **logic draft (Stop)** → narration written
from the director's own sentences → checks → shot table. Send the script (long video + short) with its references
**and the music shortlist** (audio.md). **Stop:** the director approves the script and picks the music. After the
director edits the script by hand: `check_script.py <EP> --fix`, read the difference, add what it teaches to
`voice-examples.md`.

### 3 · Recording kit → recording
recording.md: run sheet with spoken slates (`new_batch.py <EP> runsheet`), props list, recording guide; camera
test as soon as the test clip arrives. Send the kit, then **wait** for the recording.

### 4 · Intake → automatic cut → voice cut
recording.md "Intake" (`intake.py`, then `--apply`: the one speech-recognition pass), `recording_diff.py <EP>`.
Then **`gs_run.py <EP> voicecut`** (editing.md): the automatic first trim (last take of every line, cuts from
loudness, pauses, subtitles), every cut checked to land in silence, and the voice cut built for the long video and
the short: the voice as cut, burned subtitles, the real camera shots and a plain card where animation will go.
Read `work/cut-report.md` and `work/recording-diff.md` first and fix what is plainly wrong. **Stop:** the director
opens the pages (`gs_review.py`, http://localhost:8770): the **review page** to watch and leave notes by tapping,
the **editing page** to cut, put back and correct subtitles by ear. Read `work/review/<name>.notes.json`, fix,
rebuild, until approved. What the director saved on the editing page (`work/edit.json`) is final: never change it.
Ask about a changed fact or a missing line (→ pickup). **After approval the timing is locked.**

### 5 · Animation with music, 480p
visuals.md "Animation engine". First the motion brief (`work/motion-brief.md`). `gs_web.py <EP> stubs` gives every
shot a starting module in the house style; then draw the shots in `web/ep/<EP>/shots/` and `cam/`, starting from
the previous finished piece of the same style when there is one. Music goes into edl.py (audio.md). Build and
check with **`gs_run.py <EP> preview [ids]`** (script check, cuts, determinism, render, build, motion QA, the QA
report with review sheets), then look at the sheets and do the self-check (visuals.md). **Stop:** the 480p long
video and short with music; redo only the shots the director comments on. **When the director names one defect in
a motion they approved, fix only that defect and keep the rest as it was.** Sound-only notes: `gs_episode.py <EP>
mix` and short excerpts, no video rebuild.

### 6 · Final master + translations
Write the translated subtitles into edl.py (`CUE_EN`, `CUE_JA`; the cut is fixed now), then **`gs_run.py <EP>
final`** → `publish/<EP>-1080p.mp4`, the 9:16 short and the subtitle files. Skip the master if the director says
the piece is a test.

### 7 · Upload & sharing package
publish.md: one `publish/publish.md` laid out by platform, copy-ready. One title, texts written the way the
director talks. Thumbnails and short covers: **the ideas first as text** (one line each + the frame or photo),
made after the director's pick. **Stop:** send publish.md + thumbnails + covers. The director uploads and schedules
by hand. Add each music track used to `music-used.md` with its posting date.

Finally `backup_code.py` and update notes.md.

## Batch track
Several pieces written together and recorded in one session: batch.md (stops A–D before recording, one intake
stop, then steps 4–7 for the whole batch).

## Standalone and news shorts
shorts.md (outside a batch: script stop, voice-cut stop, 480p stop; news shorts are the fast lane).

## The tools (all in `<studio>/scripts`; commands.md has every command)
| Tool | What it is for |
|---|---|
| `gs_run.py <EP> voicecut \| preview \| final` | **the one way to build**: every check in order, stops at the first problem, one run at a time, time limits, a log and the time of every step |
| `intake.py` | sorts a recording session into each piece's `raw/` by the spoken slate and the content; the one speech-recognition pass |
| `recording_diff.py` | what was said against the script: retakes, missing lines, changed wording, long pauses |
| `gs_cut.py` | the automatic first cut (`edl_auto.py`, `work/cut-report.md`); listens again by itself where there is sound but no words |
| `gs_voicecut.py` | the voice cut for the stop before animation |
| `gs_review.py` (+ `gs_edit.py`) | the review page and the editing page, http://localhost:8770 |
| `gs_tracks.py` | music tracks fitted to the cut on bar lines (`TRACKS` in edl.py); alone, it lists the library and what was used |
| `gs_web.py <EP> stubs \| stills \| check \| review \| render \| qa` | the animation engine: starting modules, stills of a shot, determinism, a live workspace, render, motion QA |
| `gs_styles.py list \| preview \| use` | the house styles: compare them side by side, choose one |
| `qa.py`, `review_frames.py`, `check_script.py` | the self-checks before anything is sent |
| `new_episode.py`, `new_short.py`, `new_batch.py` | folders, checklists, run sheets |
| `gs_photo.py` | a Wikimedia Commons photo with its credit line |
| `setup_studio.py`, `probe.py` | install / remove parts, check the studio, estimate times on this computer |
