# Editing: the automatic cut, the voice cut, the pages, subtitles

## The cut: Claude trims first, the director reviews the voice cut
Animation is made only after the director has approved how the voice is cut. Before that a change costs nothing;
after it, every changed second means redrawing shots.

1. `intake.py` has filed the recordings and written each one down (recording.md).
2. **`gs_run.py <EP> voicecut`** runs, in order: `gs_cut.py` (the automatic first cut), the check that every cut
   lands in silence, and `gs_voicecut.py` for the long video and the short.
3. Read `work/cut-report.md` and `work/recording-diff.md`. Fix what is plainly wrong before the director sees it
   (a line the cut could not find, a retake it flags as unsure). Tell the director what you fixed and what you are
   unsure of.
4. **Stop.** The director opens http://localhost:8770 (`gs_review.py`; keep it running in the background).
5. Read `work/review/<name>.notes.json`, fix, `gs_run.py <EP> voicecut --keep-cut` (or without the flag when the
   script changed), until approved. **Then the timing is locked.**

### What gs_cut.py does (`<studio>/episodes/<EP>/edl_auto.py`)
- Each script section belongs to the recording that says it (`cam-<id>` for `[CAM]` sections, else by content).
- Every teleprompter line is found in the recording going backwards from the end, so when a line was said more than
  once **the last take is kept**.
- Cuts come from loudness, not from the speech model's word edges (they run early): in 0.12 s before the voice
  (0.45 s before a new idea: a question, or a line starting with `[language] new_idea_words`), out 0.15 s into the
  silence after it. Levels are relative to each file's own speech and room noise.
- What lies between two kept lines is removed when it holds speech (a dropped take) or, in an animation shot, when
  the pause is longer than 0.75 s. A pure pause on camera is left alone (a cut there would jump).
- Subtitles = the script's lines, split at commas to about `[language] max_cue`, timed on the words as said.
- Where it hears sound but the transcript has no words, it listens to that stretch again alone and says so.
- The report lists: lines not found, lines said differently from the script, retakes removed, stretches to listen
  to. Matching works on characters with spaces removed, in any language; Mandarin also falls back to matching by
  sound when the speech model wrote sound-alike characters.

`gs_episode.py` uses `edl_auto.py` while edl.py has no SHOTS of its own. Corrections that the automatic cut cannot
know go into edl.py: `CUE_TEXT = {"automatic subtitle": "corrected subtitle"}`, extra `SQUEEZE` ranges
(`{"S05": [(12.4, 13.9)]}`, source seconds). A hand-filled edl.py always wins.

### The pages (http://localhost:8770)
- **Review page:** one row per piece, newest build first. The director plays the cut, pauses, taps a ready note
  (pause too long, retake left in, line clipped, subtitle wrong, re-record this, check this fact…) and may type a
  few words. Each note is saved with the time, the shot, the place in the recording and the subtitle on screen.
  Notes left on an older build move to `work/review/old-notes/` when a new one is built. Keys: space, arrows,
  1–9, E.
- **Editing page** (`/edit?id=<EP>&short=0|1`): the piece shot by shot, with the waveform of the recording (bright
  = kept, dark = cut away) and the shot's subtitles as text boxes. The director can play a shot exactly as cut,
  drag over a stretch and cut it or put it back, move a shot's start or end the same way, correct subtitle
  wording, and split a long subtitle with a `/`. Saving writes only `work/edit.json` (the older file is copied to
  `work/review/edit-backup/`).
- **`work/edit.json` is final.** It is applied last, over the automatic cut and over edl.py. Never edit it, never
  rebuild in a way that loses it; a new automatic cut keeps it.
- The page language is `[ui] language` in studio.toml; the note buttons can be replaced with `[ui] review_tags`.

## Follow the recording
Subtitles and cuts follow what the director actually said, not the script. Do not "correct" their wording, their
dialect or a word you would spell differently. Ask only when a **fact** changed, or when a retake or slip is
unclear. A missing line is a pickup (recording.md), not something to paper over.

## Cuts
- Every cut lands in silence (`gs_episode.py <EP> check [short]`; `gs_run.py` stops when one does not). Judge
  clipping by loudness, never by the speech model's word starts.
- A start the director set on the editing page right before the first word is their decision: the check only warns.
- A join inside a shot keeps 0.2 s of air each side; under 0.15 s it sounds clipped (`qa.py` lists these).
- A cut inside a camera shot gets a small punch-in on alternate pieces so the jump reads as intended; `ZOOM` in
  edl.py sets the spans by hand.

## Subtitles
- One subtitle per spoken phrase, no trailing comma or full stop, never two on screen at once.
- Style A (text + outline) on animation, style B (text on a soft box) on camera footage; the house style recolours
  both. `GOLD_TERMS` in edl.py colours the terms worth noticing.
- Nothing but subtitles below y = 880 (landscape) / y = 1360 (portrait).
- Translations come at step 6, keyed on the final text (`CUE_EN`, `CUE_JA`), so later re-cuts keep them;
  `gs_run.py <EP> final` stops if a subtitle has no translation.
- `gs_episode.py <EP> srt` rewrites the subtitle files without rendering.
- **File names:** `subtitles.<language>_<COUNTRY>.srt` for a long video and `short.<language>_<COUNTRY>.srt` for a short (`subtitles.en_GB.srt`, `short.zh_CN.srt`). Facebook accepts
  subtitle files only in this shape, and YouTube takes the same files. The country follows the language (`en` is
  `en_GB` with British spelling, else `en_US`); `[language] subtitle_locales = {en = "en_AU"}` sets it by hand.

## edl.py (data only)
`TRACKS` / `SHORT_TRACKS` (music), `CUE_TEXT`, `CUE_EN`, `CUE_JA`, `GOLD_TERMS`, `SFX`, `SQUEEZE`, `CAM_GRADE` (the
one light grade every camera shot gets: lighting is fixed on set, not in the edit), `CAM_FRAME` (rotate / crop a
clip filmed another way), `TAIL_EXPANDER` (room echo at sentence ends), `VOICE_GAIN`, `ZOOM`, `CARD_THEME` (house
style of this piece), `SHORT`, `SHORT_VERTICAL`, `SHORT_CTA`, `SHORT_SRC` (a source line per short shot),
`FOOTAGE` (own footage under a voice-over). Shot rows: `(id, kind, source, in, out, hold, mood, beats)` with kind
`anim | cam | foot | intro | chapter | card`.

## Rendering
`gs_run.py <EP> preview [ids]` renders only the named shots (or all) at 480p and rebuilds; `final` renders 1080p.
One run at a time on a computer (a lock file); every step has a time limit and a log in
`<studio>/render/<EP>/logs/`, with the seconds of every step in `timings-<mode>.json`. `--no-anim` builds without
the animation engine (plain cards, camera without overlays).
