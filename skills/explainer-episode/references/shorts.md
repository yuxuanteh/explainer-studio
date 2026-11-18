# Standalone shorts and news shorts

A **teaser short** belongs to a long video: it is written, recorded and built with it (the X shots of that
episode), and its question is a side door into the long video (script-writing.md). Everything below is about shorts
that stand alone.

## Standalone short
- `new_short.py next <slug> "<title>" "<field>"` → `ss<NNN>-<slug>` (outside a batch) or, with `--batch`,
  `s<NNN>-<slug>` (inside one). Folders: `<project>/shorts/<id>/`, `<studio>/shorts/<id>/`, `<studio>/web/ep/<id>/`.
- One question, answered in full, about a minute; the script rules for a short apply (shape, length is a
  reference only, one idea).
- It cannot lean on a long video's animations: keep the picture simple and reuse shots from earlier shorts in the
  same house style.
- Filmed upright (9:16). The title band at the top (two lines, `SHORT["title"]` in edl.py) is the question in the
  viewer's words; the bottom line is `[channel] short_cta` (or `SHORT_CTA` in edl.py). A small source line per
  shot: `SHORT_SRC = {"X02": "Source: …"}`.
- Stops outside a batch: **script** (with references and the music pick) → recording → **voice cut** on the review
  page → **480p with music** → final + package. Inside a batch the stops are the batch's (batch.md).
- The description has **no links** (they cannot be clicked in a short). Name the related long video in the upload
  settings instead.
- It must make sense months later: no "tomorrow", no "this week", no teaser ending.

## News short (the fast lane)
For something that just happened and that the channel's viewers are asking about.
- `new_short.py next <slug> "<title>" "<field>" news`.
- **One event: what happened and what the numbers mean. Nothing else**: no cause that is not yet known, no
  forecast, no advice the channel is not qualified to give.
- **Facts only from official sources, with the time they were read** in `work/references.md`; early numbers change,
  so say "as first reported" when they are preliminary, and never mix two agencies' numbers in one sentence.
- Tone: serious. No sign-off line, no joke, no music that makes it light (often no music at all).
- Category: news. A simulated screen (an alert, a map made for the video) carries a permanent label saying it is
  simulated (`SCREEN` shots do this by themselves).
- Fast, but no stop is skipped: script and facts → recording → voice cut → 480p → final. If the director cannot
  review a step, the short waits; an unreviewed news short is worse than a late one.
- If the facts change after posting: tell the director at once and propose a pinned correction.

## Scheduling
When and how often shorts are posted is the director's plan (CHANNEL.md, or a calendar file the channel keeps).
Planned dates are a record: never skip, compress or reorder steps for a date.
