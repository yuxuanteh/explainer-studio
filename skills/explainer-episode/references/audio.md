# Audio: music, SFX, mix

## Library (`<project>/brand/music`, `brand/sfx`) - built once by studio-setup, reused every episode
| File | Use |
|---|---|
| `intro-sting.wav` | under the INTRO shot (synced to `INTRO_T` in templates/intro.py) |
| `loop-curious.wav` | default bed for explanations (pizzicato + harp, F major, 92 bpm) |
| `loop-tense.wav` | hooks, danger, arrivals (spiccato strings + timpani heartbeat) |
| `loop-calm.wav` | reflective, closing line, safety advice (piano + strings) |
| `loop-epic.wav` | big reveals, layer 3 climaxes (strings + horns + timpani + choir) |
| `outro-sting.wav` | start of the end card; a soft calm bed carries the rest and fades out |
| sfx: `whoosh(-long)`, `rumble(-short)`, `impact`, `boom`, `crack`, `tick`, `ding`, `alert`, `spring`, `swish` | place in `edl.SFX` on beats |

Instruments: GeneralUser GS via FluidSynth (`scripts/gs_sf.py`) - warm and bass-heavy. `gs_sampler.py` plays the
VSCO 2 CE samples (CC0) if a channel prefers that brighter sound. New cues / moods: add an arrangement to
`make_music.py`, render, send a 30 s sample (`make_samples.py`) before using it. If the director dislikes a
generated cue they may supply a licensed track - then you only cut and mix it.

**Credit honestly** in descriptions: "Music composed by AI (Claude) and synthesised with GeneralUser GS
instruments (S. Christian Collins)." (translated for the channel's language). Never "original score by <director>".

## Through-composed score (`gs_score.py`)
Instead of one repeating loop, declare sections in edl.py: `SCORE = [(first shot, style, transition), ...]`.
Styles: mystery curious pulse discovery reflective tension investigate epic resolve. Each section gets its own
instruments / key, building towards the climax. Transitions: `button` (chord hit, next starts on the cut) at
chapter changes, `filter` for soft scene changes, `riser` at most twice (into the climax / the advanced chapter),
`drop` (big chord ~2 s before the cut decaying to silence) before the closing line, `ringout` into the end card,
`fade` otherwise. Never end with a fade-cut - it sounds like a sudden stop.

## Mix (done by `gs_episode.py build` / `mix`)
- Voice: high-pass 80 Hz, one gentle compressor (1.6:1) and a -2 dB shelf at 6.5 kHz, optional sentence-end
  room-tail expander (`TAIL_EXPANDER = "off" | "light" | "strong"`); camera audio: high-pass + denoise,
  level-matched to the voice. Phone tracks recorded for camera shots go in `EXT_AUDIO`.
- Music bed -9 dB, ducked ~11 dB under speech (envelope follower).
- Stings at intro and end card; SFX from `edl.SFX` (shot, beat or seconds, file, dB): keep SFX around -12 to
  -18 dB, rumbles louder (-6) only on real impact moments.
- Peak limiter only, then two-pass *linear* loudnorm to -14 LUFS (YouTube). Dynamic loudnorm and stacked
  compressors pump up room echo and breaths.

You cannot hear the result - verify placement with spectrograms / waveforms and say so; the director judges taste.
A room with ~0.5 s reverb: ask for the mic 10-15 cm from the mouth (or a lavalier) and soft furnishings; in post
A/B the tail expander before committing.
