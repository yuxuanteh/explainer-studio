# Audio: music, SFX, voice, mix

## Music: the channel's choice (`[music] mode` in studio.toml, decided at setup; CHANNEL.md says why)

### `library` or `own`: finished tracks fitted to the cut
- Tracks live in `[paths] music_library` (default `<project>/music/`) as `Title - Artist.mp3` (or .wav / .m4a /
  .flac). Library tracks are downloaded **by the director** (for example the YouTube Audio Library, free with a
  YouTube account; another library needs its own licence: the director is responsible for it and says which one in
  CHANNEL.md). Never download music yourself and never use a track whose licence you have not been told.
- **Music shortlist, sent with the script (step 2):** per piece, the feeling of each part (hook, each chapter, the
  ending) and 3–4 candidates for each: title · artist · mood · length, preferring tracks that need no attribution,
  and none that the used-list shows inside about three months (a soft rule: a track may return later). Candidates
  come from the library folder (`gs_tracks.py` lists it with length, tempo and use) and from what the director
  finds; a fresh search of an online library needs the director signed in to it. The director listens, picks and
  puts the files in the folder.
- In edl.py: `TRACKS = [("S01", "Track Title"), ("C3", "Another Track")]` (the first shot of each music section) and
  `SHORT_TRACKS = [("X01", "Track Title")]` (a short: one track).
- **How a track is fitted** (`gs_tracks.py`, needs the `music_fit` part): pieces are cut only on bar lines, whole
  phrases preferred; the track's own ending lands at the end of its section; a track that is too long loses whole
  phrases from its middle, one that is too short repeats a middle phrase; the next track eases in over the ring of
  the last. No added fade-out, no added hit. Every track is set to the same average level.
- In the mix the music sits about 18 dB under the voice while someone talks and rises about 7 dB in pauses
  (`build-*/music-plan.txt` says what was used from each track).
- **Used-list** `[paths] music_used` (default `<project>/music-used.md`): a table `| track | artist | piece |
  posted |`. Add each track when its video is posted.
- **Credit line** in the description, as the library asks (YouTube Audio Library: "Music: <title> (<artist>),
  YouTube Audio Library"). Own music: credit as the director says.

### `score`: programmed music composed by Claude (needs the `score` part)
- Built once per channel: `make_music.py` writes mood loops, an intro and outro sting and a set of SFX into
  `<project>/brand/music` and `brand/sfx` (instruments: GeneralUser GS through FluidSynth). `make_samples.py` makes a
  30-second sample to send before anything is used.
- Per piece, a through-composed score: `SCORE = [(first shot, style, transition), ...]` in edl.py. Styles: mystery,
  curious, pulse, discovery, reflective, tension, investigate, epic, resolve. Transitions: `button` at chapter
  changes, `filter` for soft scene changes, `riser` at most twice, `drop` before the closing line, `ringout` into
  the end card, `fade` otherwise. Never end on a cut-off fade.
- **Credit honestly:** "Music composed by AI (Claude) and synthesised with GeneralUser GS instruments (S. Christian
  Collins)", in the channel's language. Never "original score by <the director>".
- It fits the cut exactly and needs no licences, and it sounds simpler than recorded music. If the director calls
  it thin or cheap, say plainly that library tracks are the remedy and offer the change (studio-setup, section 6).

### `none`
No `TRACKS`, no `SCORE`. Voice and SFX only.

## SFX
`SFX = [(shot, seconds into the shot or a beat name, file, dB)]`: a file name in `<project>/brand/sfx` (without
.wav) or a path inside the piece's folder. Sparingly, on something that happens on screen; around −12 to −18 dB.

## Voice processing (done by the build)
High-pass at 80 Hz, one gentle compressor (1.6:1), −2 dB shelf at 6.5 kHz, an optional reducer for room echo at
sentence ends (`TAIL_EXPANDER = "off" | "light" | "strong"`). Camera sound: high-pass + light noise reduction,
level-matched to the narration. `VOICE_GAIN = {shot: [(from, to, dB)]}` lifts or lowers one phrase. Peak limiter
only, then one constant gain to −14 LUFS (two-pass, linear). No stacked compressors: they pump up room echo and
breaths, and the voice becomes tiring to listen to.

## Sound-only notes
A note about music level, a track, or the voice needs no video rebuild: `gs_episode.py <EP> mix` rebuilds only
the mix; send a short excerpt of the place in question (ffmpeg, 15–20 s). You cannot hear: check placement and
levels in numbers (loudness, peaks, a waveform), say so, and let the director judge taste.
