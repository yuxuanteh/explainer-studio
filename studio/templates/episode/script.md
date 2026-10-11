# {{EPISODE_NO}} · {{TITLE}}

> Series: {{SERIES}} · target 5-10 minutes (check with `python check_script.py {{EPISODE}}`)
> Fact-check table: `work/references.md` (every number and claim needs a source, or it stays out of the script)

## 1. Teleprompter (read only this block)

> One line = one breath, half a second between lines. If you slip, pause 2 s and re-read that line.
> Start every recording with 3 s of silence. Keep each phrase short enough for one subtitle cue.

```
S01  (hook: grab in the first seconds - a shared experience, a counter-intuitive fact, a striking event, a question)

C1   (chapter 1 · the basics: a complete beginner can follow - analogies, pictures, everyday experience)
S02
S03

C2   (chapter 2 · how it works: for viewers who want to really understand - mechanism, key numbers, why)
S04
S05

C3   (chapter 3 · going deeper: people in the field still learn something - details, real data, misconceptions)
S06
S07

S08  (answer every question the hook raised, in plain words, then one natural closing line - no "to summarise")

END  (next episode teaser: one or two lines)
```

## 2. Shot table

| # | Narration (summary) | Picture / animation | Layout | Music mood | SFX | Source note |
|---|---|---|---|---|---|---|
| S01 | | | full screen / camera | tense | | |
| INTRO | - | intro sting | full screen | intro | - | - |
| C1 | - | chapter card | full screen | curious | transition | - |
| END | next episode | end card (12 s) | template | outro | - | - |

**Episode palette** (intro, end card, logo and name tag always use the channel palette):

## 3. Fact check and sources
See `work/references.md` (claim -> verdict -> source link; note any difference from the source).

## 4. Recording guide
- Voice: quiet room, phone or mic 10-15 cm from the mouth, slightly off-axis; WAV if possible (48 kHz). File: `raw/voice.wav` (or .m4a).
- Camera: landscape 16:9, fixed tripod, a clean wall area beside you for CG. Files: `raw/cam-<shot id>.mp4`. Clap once at the start of each take.
- When done, tell Claude: "the {{EPISODE}} recordings are in raw".
