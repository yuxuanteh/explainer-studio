# Episode code (`<studio>/episodes/<EP>/`)

Created from `templates/episode/` by `new_episode.py`. The pipeline (`scripts/gs_episode.py`) reads everything
from `edl.py`; scene files only draw.

## edl.py (data only)
```python
EPISODE = "01-granite"
SOURCES = {"voice": "voice.wav", "camS05": "cam-S05.mp4"}          # files in raw/
SHOTS = [  # id, kind, source, in, out, hold, mood, beats{name: source time}
    ("S01", "anim", "voice", 3.40, 11.70, 0.0, "tense", {"updown": 7.41, "shake": 10.93}),
    ("INTRO", "intro", None, 0.0, 4.20, 0.0, "intro", {}),
    ("C1", "chapter", None, 0.0, 3.0, 0.0, "curious", {}),
    ("S05", "cam", "camS05", 3.45, 8.25, 0.0, "curious", {"two": 7.27}),
    ("END", "card", "voice", 73.68, 79.20, 6.48, "outro", {}),      # 12 s total
]
CUES = [("voice", 3.63, 5.85, "<main-language cue>", "<translation cue>"), ...]
GOLD_TERMS = ["P-wave", "S-wave"]                     # highlighted in the accent colour in subtitles
SFX = [("S01", "updown", "rumble-short", -14), ("S03", 0.0, "whoosh", -18)]
CAM_GRADE = "eq=brightness=0.04:gamma=1.15:saturation=1.05"
SHORT = {"segments": [("S01", "S01"), ("S06", "S08")], "title": ("line one", "line two?")}
EXT_AUDIO = {"camS05": ("cam-S05.m4a", 4.67)}      # phone track for a camera shot; lag = phone started later (s)
SQUEEZE = {"S10": [(155.45, 158.70)]}              # source ranges removed inside a shot (pauses, false starts)
SCORE = [("S01", "mystery"), ("INTRO", None, "button"), ("C1", "curious", "fade"), ...]   # gs_score.py
TAIL_EXPANDER = "light"                            # sentence-end room tail: off | light | strong
```

## make_edl.py (generates SHOTS / CUES / SQUEEZE)
Fill `LAG` (= EXT_AUDIO lags), `TAKES` (shot id, kind, source key, from, to, mood, cues) where from/to bracket the
words of the take in source time (camera time for cam shots) and cues are the text *as actually said* with the
translation, then `BEATS` (name -> anchor text). Run it and paste the output into edl.py. Hand fixes:
`PIN` (cut points after checking the loudness profile), `CUE_FIX` (cue times where Whisper aligned text to a
dropped first attempt), `MANUAL_CUTS` (false starts verified by re-transcribing the window alone).
- Cut points come from loudness (`onset()` / `offset()`), not Whisper word edges.
- Cue boundaries are matched character by character for CJK narration; for word-based languages adapt `cjk()`.
- Then **always** run `gs_episode.py <EP> check`; move any flagged `out` later until the check passes.
- Beats are word start times used by scenes and SFX.

## Subtitles
- One cue per spoken phrase (≤ `max_cue`), text from the script corrected to what was said.
- The second track is a translation, not a gloss: translate the whole sentence first like a human subtitler,
  then split it across that sentence's cues at natural phrase breaks. Conversational, no calques, no AI tells.
  Keep every number, agency and term exactly; don't add certainty the original doesn't have.
- After editing CUES: `gs_episode.py <EP> srt` rewrites both SRTs without a re-render.
- Chapter cards: silent shots of ~3 s; the end card is 12 s (voice teaser + hold).
- SHORT: 15-60 s, hook -> answer -> one wow fact; the title band is two lines; `"S01@18.75"` cuts inside a shot.

## shots.py / cam_cg.py / thumbs.py
- `shots.py`: `Clocked.E = here(__file__)` once; one class per shot id (`class S03(Clocked)`,
  `class C1(ChapterCard)`, `class END(EndCard)`). Scenes run exactly `shot.dur` seconds.
- `cam_cg.py`: `CamClocked.E = here(__file__)`; class `Cam<id>`; rendered with a transparent background and
  overlaid on the graded camera clip.
- `thumbs.py`: `ThumbA/B/C` built with `Layered.put(bg=[...], el=[...], text=[...])` + `IgCover` (+ optional
  `ShortCover`); the four layer variants are generated automatically.

## Rendering notes
- `render` runs Manim scenes one at a time (parallel runs corrupt the shared text cache).
- Preview: 480p15; final: 1080p at `[video] fps`, master encoded with `[video] final_encoder`.
- Intermediates in `<studio>/render/<EP>/` (safe to delete; re-render when needed).
- Fonts must be installed in the OS; never `manimpango.register_font` (every Text then takes 25-55 s).
