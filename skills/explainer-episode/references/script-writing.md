# Writing the script

## Who it is for
CHANNEL.md names the audience and language. The default model: one episode = one concept, explained so that a
complete beginner follows the start, and an expert still learns or refreshes something at the end. That is why
episodes are 5-10 minutes instead of 60 seconds.

## Length
- Target **5-10 min of speech** at the presenter's measured pace (`[language] pace` in studio.toml; measure it
  on the first recording: units spoken / seconds of speech). Intro (4 s), chapter cards (~3 s each) and the
  12 s end card come on top.
- `check_script.py <EP>` prints per-section length, total ≈ duration and subtitle warnings.

## Structure (three depth layers)
| Part | Purpose | Typical length |
|---|---|---|
| Hook (S01) | First seconds must grab: a shared experience, a counter-intuitive fact, a striking (local) event, a question. No greeting first. | 5-15 s |
| Intro sting | Channel intro (template). | 4 s |
| C1 the basics | Anyone can follow: everyday analogies, pictures, what you see / feel. | 25-35 % |
| C2 how it works | Mechanism, the key numbers, cause and effect, a simple formula's intuition. | 30-40 % |
| C3 going deeper | For people in the field: details, real data, a local / regional case, common misconceptions, limits of the simple picture. | 20-30 % |
| Closing | First **answer the hook's question(s) in plain words**, then one natural sentence that lands the idea. **No "to summarise" section.** | 1-2 lines |
| END teaser | Next episode in the same series, 1-2 lines, spoken over the end card. | 5-8 s |

### Close every question the hook opens
A hook often raises questions without a question mark: "Most people think the epicentre is where the quake
happens. It isn't. And that 10 km depth wasn't even measured." raises *then where does it happen?* and *where
did 10 km come from?* The closing lines must answer each of them **in plain words**, so a viewer who only
remembers the start and the end still gets the answer.
- Before sending the script, list every question / claim-to-be-revealed in the hook and tick where the closing
  answers it (put the list under the script). Explaining it in the middle is not enough - restate the answer at
  the end, then the closing line.
- The short is cut from the same pair (hook + answer), so shorts never end on a teaser.

Each layer starts with a chapter card (`ChapterCard` in shots.py) - also YouTube chapters, so experts can jump.

## Terms, spelling, language
Follow CHANNEL.md. Common choices:
- Keep technical terms in the language viewers learned them in (e.g. English terms in Mandarin narration for
  audiences schooled in English). A translation may appear once, small, on screen - never instead of the term.
  `[language] term_list` lets `check_script.py` flag local-language terms.
- One spelling standard everywhere (`[language] british_spelling` flags American spellings), except quoted
  source titles, catalogue field names and code identifiers.
- Highlight key terms in subtitles via `GOLD_TERMS`.

## Voice and sentences
- Short, spoken sentences. One teleprompter line = one breath. Avoid long chains of commas (sounds like AI).
- Each phrase between punctuation ≤ `max_cue` units - each phrase becomes one subtitle cue.
- Speak to the viewer ("have you noticed...", "you may have heard..."). Local references are welcome, but only
  with verified facts.
- Numbers: say the rounded value the source supports and keep the precise value + source in references.md;
  mention when official sources use a different convention.

## Teleprompter block format (script.md)
```
S01  When an earthquake hits, have you noticed,
     the ground first jolts up and down,
C1   (chapter card: no narration, or a one-line title read)
S02  ...
END  Next time,
     why earthquakes keep choosing the same places.
```
A line starting with a shot id starts a section; indented lines continue it. Shot ids: `S01..`, chapter cards
`C1..`, end card `END` (must match edl.py / shots.py class names). To split a section into camera + animation,
add a letter suffix (`S14` on camera, `S14b` animation). Mark camera sections with `[ON CAMERA]` (or
`[ON CAMERA · demo: <prop>]`) as the first line.

## How much on camera
Two camera shots (opening + closing) is **too few**. Plan **about 1/3 of the episode on camera** (≈ 8-10
sections), the rest animation. Choose by content:

| Put on camera | Keep as animation |
|---|---|
| Hook and closing line | Cross-sections, processes you cannot film |
| **Hands-on demos with simple household props** (a glass of water + coin, a torch, a printed map + string, a sample) | Maps with real data, catalogue numbers, comparisons of sources |
| Conversational "why" questions | Classifications, multi-step diagrams, formulas |
| The presenter's opinion / judgement | Historical events (maps, timelines) |
| References to the channel's earlier videos (place a YouTube card there) | |
| Personal admissions / corrections - must be face to camera | |
| One line of the presenter's own experience (ask first) | |

- Present the proposal as a table (section · content · why on camera · how to shoot) and let the director pick.
- Demos: design them so they **cannot fail on camera**, keep props to what a home has, label the shot
  schematic when positions are not real. Plan a 2-second animation replay in case the demo is unclear.
- **Check the analogy's geometry** before writing it (a shadow falls *below* an object; if the thing you explain
  is *above*, the analogy is wrong).
- Recording guide: one table row per camera file (`raw/cam-<id>.mp4`, which section, framing, props, optional
  second angle); remind the director not to film unpublished or private material.
- Subtitle style B on every camera section; name tag only on the first appearance.

## Shot table
Columns: # · narration summary · picture / animation · layout (full-screen animation / camera + CG / photo) ·
music mood (tense / curious / calm / epic) · SFX · source note. Note the episode palette at the bottom.
