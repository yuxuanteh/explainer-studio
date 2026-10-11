# Visuals: style rules and the shot kit

The channel's own rules are in CHANNEL.md. The essentials:

## Fixed brand elements (channel palette, `[palette]` in studio.toml)
- Intro sting (`templates/intro.py`, inserted automatically as the INTRO shot - redesign it around the logo),
  end card (`EndCard`), logo, watermark (`gs.watermark()`, top-right), name tag (`gs.name_tag()`), subtitles.
- Palette roles: `accent` (aliases `gs.GOLD`), `accent_hi`, `accent_deep`, `accent2` (`gs.CYAN`), `bg`
  (`gs.DARK`), `bg_deep` (`gs.DARKER`), `card`, `line`, `text`, `muted`.
- Fonts (`[fonts]`, installed in the OS - never `manimpango.register_font`): `gs.ZH_SERIF` titles (weight=HEAVY),
  `gs.ZH_SANS` labels / captions, `gs.EN_LABEL` Latin labels (BOLD / MEDIUM), `gs.EN_TAG` tagline. A Latin-only
  label font has no CJK glyphs: use `mixed(en, zh)`.

## Episode palette (changes per episode)
Animations, diagrams, maps and data plots get their own palette that fits the topic (volcano: lava reds /
oranges; ocean: deep blues; limestone: off-white / grey-green). Keep contrast against the dark background and
text readable. Define it at the top of shots.py.

## Layout rules
- **Subtitle band (y > 880 at 1080p)**: no *text* there (labels, legends, chips). **Graphics run to the frame
  edge** (cross-sections, wavefronts, maps, panels): if the animation stops at 880 the subtitle area looks like a
  separate empty strip.
- Source note top-right for facts; kicker top-left (`gs.kicker("ENGLISH", zh="…")`).
- Labels never cover the subject or the presenter. **Labels sit next to what they describe** (a magnitude chip
  beside the pin, a distance next to the radius line). No label floating in an empty half; centre maps on the action.

## On-screen text
- **Never put the narration sentence on screen** - the subtitles already show it. Use only terms, numbers, very
  short keywords, or nothing. Before sending, read every chip against its narration line and delete paraphrases.
- A visual for something mentioned appears **on that word** (beats) and stays long enough to read; the thing being
  contrasted is on screen from the start of the comparison.
- When the narration describes an action ("seen from directly above"), the animation performs it.
- References to the channel's earlier videos use the **real thumbnail**.
- Maps with event locations: only real coordinates; where a source gave only a description, say so in the
  source note and tell the director.

## Camera CG placement
- Centre wall CG **half-way between the frame edge and the presenter** (measure the presenter's edge on a frame;
  write the free zone into CHANNEL.md once the set is fixed), not hugging the edge. Cards ~480 px wide, text
  >= 24 px. Check hands (gestures reach far) on a contact sheet.
- Text size in 1080p px via `gs.text(s, font, size)`; `at(x, y)` positions in 1080p px (origin top-left).

## Shot kit (`scripts/gs_shotkit.py`)
| Helper | Use |
|---|---|
| `Clocked` / `CamClocked` | time-driven scene; `self.t()`, `self.beats[...]`, `self.fade_at(mob, t_in, d, t_out, shift)`, `self.fade_each(group, ...)`, `self.run()` |
| `ChapterCard`, `EndCard` | subclass and set texts |
| `label_chip`, `mixed`, `warn_icon`, `pause_icon`, `play_icon` | labels and icons (no emoji / symbol glyphs - fonts lack them) |
| `house`, `quake_signal`, `natural_earth_map(lon0, lat0, scale, bbox=...)` | example drawings (earth science); add your topic's reusable drawings |
| `DeskPlane(near, A, B)`, `stick_figure(P, pose)` | CG standing on real furniture in a camera shot |
| `ramp(t, t0, d)` | smooth 0->1 for custom animation |

Draw continuously changing things with `always_redraw(lambda: ...)` reading `self.t()`; beats come from the edl
so motion lands on the spoken word.

## Camera shots with CG
- Full-screen camera (not split screen). Grade with `CAM_GRADE` in edl.py.
- First look at frames: where the presenter is, clean wall areas, real surfaces. CG never crosses the face or
  body (gestures included). Wall CG = labels, diagrams, countdowns.
- CG that stands on furniture: measure the perspective from a real object on that surface (a box seen corner-on:
  shallow V bottom edges, thin top face, verticals vertical) -> `DeskPlane`. Add a contact shadow.
- First appearance of the presenter: name tag 3-5 s.

## Thumbnails
1280x720, < 2 MB, three versions for YouTube "test & compare": A presenter + question, B illustration, C key fact /
number. Huge text (≈ 140 px at 1280) with a dark outline, few words per line. All four layers are rendered (full,
background without text, transparent text, transparent elements) so the director can rebuild in Canva.
Portrait renders (`-r 1080,1350`): `config.frame_width` stays 14.2 while the real height grows and
`config.frame_height` still reads 8 - compute `fh = fw * pixel_height / pixel_width` and use `move_to`, not `to_edge`.
