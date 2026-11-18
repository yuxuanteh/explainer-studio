# Visuals: house style, layout, the animation engine, thumbnails

## House style
The channel has **one house style** (a channel with several fields may have one per field: `CARD_THEME` in a
piece's edl.py, else `[style] house` in studio.toml). There is no style choice per video. Chapter and end cards, the
intro, the name tag, labels, the ground of every animated shot and the burned subtitles all follow it; only the
logo is the same everywhere.

- A style is one entry of `<studio>/web/kit/themes.json`: `bg`, `bg2`, `card`, `text`, `muted`, `accent`,
  `accentDeep`, `onAccent`, `ink`, `ground` (`grid | dust | paper | flat`), `plate` (the name tag: `bar | outline |
  chalk | block | card`), `titleFont` (`sans | label | mono | hand`). `CHANNEL` is the look built from `[palette]`.
- BLUEPRINT, CHALK and POSTER are examples. A channel's own style is a new entry plus, when it needs them, drawing
  pieces in `web/kit/house.js` (a texture, a symbol set, a frame for photos). `gs_styles.py preview` shows any set
  of styles side by side on the same sample shot; `gs_styles.py use <ID>` sets the channel's.
- A hand-made subtitle look for a style: `<project>/brand/subtitles/<ID>.json` (fields of the ASS style lines);
  without one, subtitle colours are derived from the style.
- **Model for a new piece: the previous finished piece in the same style.** Reuse its shot modules and drawing
  pieces; a style gets better by being used, not by being redesigned per video.
- Changing the house style is the director's decision: show the comparison picture, never switch silently.

## Layout rules
- Design size 1920×1080 (landscape) and 1080×1920 (portrait). **Nothing but subtitles below y = 880 (landscape) /
  y = 1360 (portrait)**; in portrait the title band sits above y = 360, content between 400 and 1330.
- Source note top right, left of the watermark. The watermark sits on every shot except the intro.
- A label sits beside its subject with a leader line, never over the presenter's face or body, never across a
  photo's credit.
- One idea per shot. Things appear on the word that names them (`say(S, 'words')` gives the time those words are
  spoken) and nothing leaves the frame half-explained.
- No card that only repeats the narration in text.

## Physics stays real, even in a diagram
Directions, proportions and order of events are right, or the shot says it is a diagram (`sourceNote(S,
'Diagram')`, the word from `[channel] diagram_label`). Real data over illustration when it exists: a real map, a
real record, a real photo with its credit (`gs_photo.py` fetches a Wikimedia Commons photo with author and
licence).

## On-screen text
Short. A term in the language `CHANNEL.md` says terms are shown in; a second language may appear once, small.
Never mix scripts in one string when the label font lacks the glyphs (`mixed()` draws the two parts side by side).

## Camera shots with CG
Graphics over a camera shot are drawn on a transparent canvas (`web/ep/<EP>/cam/<id>.js`): never a background.
Look at a frame first (`gs_web.py <EP> review <id>` puts a still of the clip behind the graphics). The name tag
appears for 3–5 s on the first appearance only.

## Animation engine: web pages + the motion-showreel plugin
Every shot is a small JavaScript module that draws one frame for a given time `t` on a canvas; a headless browser
renders the frames and ffmpeg assembles them. Deterministic: the same `t` gives the same pixels, in any order.

```
web/ep/<EP>/shots/<id>.js    full-screen shots (animation, chapter card, end card), long video and short
web/ep/<EP>/cam/<id>.js      graphics over a camera shot (transparent)
web/ep/<EP>/assets/          photos, data, SVG used by the shots
web/kit/                     gs.js (brand pieces), themes.json (styles), house.js (drawing pieces),
                             intro.js (the channel intro), player.js, motion.js (easing, noise, cameras)
```
A module: `export default async function (S) { /* load images */ return t => { /* draw the frame at t */ }; }`.
`S` = `{ id, kind, W, H, DW, DH, u, ctx, dur, beats, cues, vertical, style, img(path) }`; coordinates are design
pixels, `S.u` scales them. **Rules: the picture depends on `t` only.** No `Math.random`, `Date.now`, timers,
`requestAnimationFrame`, CSS animation, or state kept between frames; seeded noise from `motion.js`.

Kit pieces (`gs.js`): `theme()`, `text`, `title`, `kicker`, `label`, `chip`, `mixed`, `rect`, `image`, `vis(t, in,
d, out)`, `ramp`, `say(S, words)`, `beat(S, name)`, `nameTag`, `sourceNote`, `watermark`, `chapterCard`,
`endCard`, `bg`. Drawing pieces (`house.js`): `styleBg`, `line` (can draw itself on), `fill`, `arrow`, `dot`,
`note`, `photo`, `inside`. `web/kit/demo.js` is a short worked example.

Workflow for step 5:
1. `gs_web.py <EP> stubs`: a starting module for every shot (style ground, watermark, a placeholder).
2. **Motion brief** (`work/motion-brief.md`, short, one per piece, before the first shot): per shot, what moves and
   why, what appears on which word, what is reused from an earlier piece.
3. Draw the shots. `gs_web.py <EP> stills <id> 0.5,3,7 [--guides]` gives stills and a contact sheet of one shot
   (`--guides` paints the subtitle band red). `gs_web.py <EP> review [ids] [--short]` prints a command that opens a
   live workspace with the shots and their sound.
4. `gs_run.py <EP> preview [ids]`: determinism, render, build, motion QA (dead air, sudden jumps, flash frames),
   the QA report and the review sheets in `<studio>/render/<EP>/review/`.
5. Read the motion-showreel skill for the craft of motion (easing, staging, timing).

### Self-check before sending
Look at every review sheet: no text in the subtitle band, no missing glyphs (empty boxes), labels beside their
subject, nothing covering the presenter, no card repeating the narration, things appear on their word, no blink at
a cut, every shot with a fact has its source and every pure illustration says so. Then a design critique of the
whole: does it read in two seconds, is one thing the centre of each frame, is it the house style throughout?

### Chapter card and end card
The chapter card shows the chapter's question, word for word. The end card is the YouTube end screen: 12 s, two
video frames on the right and the bottom-left slot left empty for YouTube's own subscribe element (positions in
`gs.js` `esSlots()`), one question for the comments (`ask`), never the next video's title.

## Thumbnails: the idea first
For each video, propose **ideas as text before making anything**: one line each (what the viewer sees, the two or
three words on it, why it makes someone click) plus the frame or photo it would use. An idea per video, not a
template with the title swapped. The director picks; then make it: a still of a shot (`gs_web.py <EP> stills`),
a frame of the camera clip, the house style's colours and title font, large type that reads at phone size. A short's
cover follows the same rule in 9:16. Version 2 has no thumbnail tool of its own: compose the picture with the
animation engine (a one-off module rendered as a still) or an image tool, and keep the layered source so the
director can change it.
