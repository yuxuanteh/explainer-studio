# 金釘子 GoldenSpike · channel profile (example)

The channel this pipeline was built for: Mandarin earth-science explainers (geology and seismology) for
Malaysian Chinese viewers. Shown here as a filled-in example of `channel-template/CHANNEL.md`.

## The channel
- Name: 金釘子 GoldenSpike. Tagline: "Stories Written in Stone". Intro title: 读懂脚下的地球.
- Topic area: geology and seismology, one concept per episode, 5-10 minutes, three depth layers.
- Audience: Malaysian Chinese viewers. They learned science in English at school, so English technical terms are
  the words they know.
- Series: earthquakes, rocks, landscapes, Malaysian geology.

## The presenter
- Name tag: two lines, Chinese only: the channel name, then the presenter's degree and current research.
- **Never "Geologist / 地质师"**: in Malaysia that title requires registration with the Board of Geologists.

## Language
- Narration in Mandarin (simplified characters). Burned-in Chinese subtitles; English SRT track.
- **Scientific terms, rock and mineral names, place names and scientists' names in English** (Basalt, P-wave,
  subduction zone, Sundaland). A Chinese gloss may appear once, small, on screen ("Basalt · 玄武岩"), never in the
  narration. `term_list = "brand/terms-geoscience-zh.toml"`.
- **British English everywhere** (Malaysian usage): Epicentre, Hypocentre, centre, metre, colour, grey, analyse.
- Subtitles: half-width commas `, `; ≤ ~20 characters per cue; English terms in gold.
- Translation rule: natural, same meaning, not word for word, no AI tone.

## Look
- Channel palette: gold #F2B90D, deep gold #8A6400, dark #1A160C / #131008, card #231E10, text #F5F1E8,
  muted #CBBC90, seismic cyan #00C8D2. Episodes pick their own animation palette (volcano reds, ocean blues...).
- Fonts: Noto Serif SC (titles), Noto Sans SC (labels, subtitles), Space Grotesk (English labels), Playfair
  Display italic (tagline), Manrope (English body).
- Logo: a golden spike driven into rock strata, its tip on a golden boundary that turns into a cyan seismic wave.
- Camera set: presenter right of centre, dark wall on the left for CG (CG centre x ≈ 400 at 1080p).

## Sound
- Warm, bass-heavy GeneralUser GS orchestra. The VSCO 2 CE strings were rejected as too bright.
- A through-composed score per episode (SCORE), varied transitions, never a fade-cut ending.
- Voice: gentle chain, `TAIL_EXPANDER = "light"` (the room rings ~0.5 s; lavalier recommended).
- Credit: "配乐由 AI（Claude）作曲、程序合成，音色来自 GeneralUser GS（S. Christian Collins）。"

## Facts and sources
- USGS, JMA, MetMalaysia, JMG (Jabatan Mineral dan Geosains Malaysia), GFZ / GEOFON, EMSC, IRIS, NOAA / PTWC,
  BMKG, PHIVOLCS; peer-reviewed papers; standard textbooks (Stein & Wysession; Marshak).
- Real data on screen wherever possible: USGS ComCat catalogue, ObsPy + EarthScope waveforms, Natural Earth maps.
- Never mix agencies in one sentence (MetMalaysia's depth with USGS's magnitude).

## Publishing
- Description: two hook lines, a plain paragraph, chapters, references, "更多细节：" blog link, website,
  Instagram, email, music credit, three hashtags. No emoji headers or bullets.
- Education fields: academic system Malaysia, level upper secondary.
- Quiz in Chinese and English, also on the website.
- Blog: a Chinese and an English post per video with the same slug, each with its own angle (never the video's
  chapter order), several images, callouts, [n] citations.
- Social: Instagram, Facebook page, LinkedIn (researcher tone).

## Decisions log (excerpt)
- 2026-10-10 about 1/3 of each episode on camera; hands-on demos with household props.
- 2026-10-10 on-screen text never repeats the narration; labels next to their subject.
- 2026-10-11 the hook's questions are answered in plain words at the end; shorts never end on a teaser.
- 2026-10-11 news references use a neutral news card, not press photos.
- 2026-10-11 descriptions and posts written like a person: no symbols at line starts, first person.
