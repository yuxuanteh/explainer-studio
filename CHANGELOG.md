# Changelog

## 2.0.0 (2026-11-18)

The studio pipeline as it runs today, replacing the first public version. Version 0.1.0 stays available as the git
tag `v0.1.0`.

**New**
- Setup checks the computer first (`probe.py`: processor, memory, graphics card, disk, two speed tests) and estimates
  the time of every pipeline step on it.
- Setup explains every part and asks before installing it (`setup_studio.py`): core, fonts, speech recognition (three
  model sizes), animation engine, music fitting, programmed score. Parts can be removed again to free space.
- Automatic first cut (`gs_cut.py`): the last take of every line, cuts placed in silence by loudness, retakes and long
  pauses removed, subtitles timed to the words.
- A voice-cut stop before any animation, with a review page (notes by tapping) and an editing page (cut, put back and
  correct subtitles by ear) at http://localhost:8770, in English or Chinese.
- One gate for every build (`gs_run.py voicecut | preview | final`): all checks in order, one run at a time, time
  limits, logs and timings per step.
- Web animation engine (render(t) pages rendered with the motion-showreel plugin's tools) with one house style for
  the channel; three example styles (Blueprint, Chalkboard, Poster) and a side-by-side comparison (`gs_styles.py`).
- Music is a choice: library tracks or your own, fitted to the cut on bar lines (`gs_tracks.py`); the programmed
  score; or none.
- Intake of a recording session by spoken slate and content (`intake.py`), recording-diff report, batches, standalone
  shorts and news shorts, run sheets.
- A try-it sample (`make_sample.py`).
- Works without the animation engine (`--no-anim`: plain cards, camera without overlays).
- Chinese README.

**Changed**
- The look: a palette per episode → one house style (the old `[palette]` is kept as the CHANNEL look).
- Titles: three options → one. The cut list is no longer written by hand per episode.
- Fonts live in the studio (`web/fonts`), not in the operating system.

**Removed**
- Manim (animation engine of 0.1) and its templates.
- The channel-website skill, the thumbnail tool and the topic-specific extras of 0.1.

**Upgrading from 0.1:** say "set up my studio"; the setup skill backs up the old code, keeps your episodes,
settings and speech model, and asks about each difference (style, music, unfinished episodes).

## 0.1.0 (2026-10-11)
First public version: Manim animation, per-episode palettes, programmed score, hand-made cut lists.
