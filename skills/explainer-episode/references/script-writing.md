# Writing the script: the one rulebook

This file is the only place script rules live. SKILL.md step 2 holds the order and the stops; the channel's
`voice-examples.md` holds how this director talks and what they changed in earlier drafts: the evidence behind the
rules. A new decision about scripts from the director goes into `CHANNEL.md` ("Script decisions") and wins over
anything here.

It grew out of a real channel (金釘子 GoldenSpike, Mandarin earth-science explainers for Malaysian viewers), so the
examples are from geology. The method is not tied to the subject or the language.

The rules sit under five principles (from 鄭國威 of PanSci on science communication): **the Door**, **the Map**,
**the Scaffold**, **the Keel**, **the Voice**. Each has one test. Mechanical things (length, long subtitle pieces,
spelling) are checked by `check_script.py`, so attention goes to the five tests while writing.

**Rules are tests, not ingredients.** Every rule here is something to *check* a draft against, never a slot to
fill. Outlines that fill every slot (a hook scene, an answer line, a surprise, a limit, the answer again) read as
forced, and every piece comes out built the same way. The topic decides the move: a real misconception → open on
it; an event viewers remember → ask about it; a striking number → lead with it.

**The real question comes first, before any rule.** For every hook and chapter question: (1) write the question a
real viewer would actually ask or type, in the plainest words, and when they would think of it (standing at the
waterfall, reading the news); (2) only then pick the way of opening that fits it; (3) variety is a reference only.
**The simplest, most natural question a viewer would really ask wins, even if it repeats an earlier piece.**

## Who it is for, and what each format is for
`CHANNEL.md` says who the viewers are, which language is spoken, how terms and spelling are handled. One topic =
one concept. Each format has its own speed and its own job; do not make one format do another's job.

| Format | Speed | Job | Length |
|---|---|---|---|
| News short | fast | one event: what happened and what the numbers mean, nothing else | 45–60 s |
| Short (episode teaser or standalone) | fast | one side-door question, fully answered, for someone scrolling with no background | about 1 min, at most ~1:20 |
| Long video | medium | **the map**: join the dots the viewer has already met into one line, so they know where they stand | 5–8 min, up to 10 when the topic needs it |
| Blog / description | slow | mechanisms, history, details, "what I am not sure about" | as needed |

Length follows the director's measured pace (`[language] pace` in studio.toml). The intro (4 s), chapter cards
(~3 s each) and the 12 s end card come on top.

## The process (one order, every pass in it)
1. **Questions first, from a real-viewer interview.** Before writing any question, run one subagent playing a real
   viewer from `CHANNEL.md`'s audience (age, place, no background in the subject; persona only, no files). Ask it:
   when in real life would you think about this, or never? How would you say it to a friend, or type it into
   YouTube? What would make you say "wait, really?" (ranked)? What do you already believe that may be wrong? React
   to the candidate questions: real, or invented? For a batch, one call for every piece. Then write at the top of
   `work/logic-draft.md`: the hook question, each chapter's question and the short's question, **in the viewer's
   own words**, with a short note of what the interview said.
2. **Fact-check** (`fact-check.md`) into `work/references.md`. Anything that cannot be verified goes to the
   director as a question, not into the script.
3. **Logic draft** (`work/logic-draft.md`). One plain paragraph per chapter (3–5 sentences, not in teleprompter
   form): what the viewer already knows, the one new step, why it follows. Also: every analogy, how it maps back
   and **where it stops**; how the ending answers each hook question from a new angle; the optional "how do we
   know" beat; the on-camera proposal table (section · content · why it suits the camera · how to film it).
   For a short, the outline is already the spoken lines in the short's shape.
   Before sending, a **viewer read** of the draft (one subagent, the same persona, reads only the questions and the
   outline): would you really wonder this here? Where would you get lost or bored? Does the ending give you
   something new and answer the opening? Fix what it finds.

   **Stop: the director approves the logic before any narration is written.** It is a five-minute read; fixing
   logic here is far cheaper than rewriting finished narration.
4. **Narration, written from the director's own sentences.** Do not draft in your own feel for the language and
   patch it with rules afterwards: it never comes out clean. For each line, first find the closest thing the
   director has actually said (`voice-examples.md`: their edits of earlier drafts first, then transcripts of them
   talking without a script) and follow its sentence shape with the new content. Copy their way of thinking (why
   they asked it that way), not only the outer shape. Break teleprompter lines only at the end, at natural pauses.
   **When there is no evidence yet (a new channel):** ask the director for a one-minute voice memo explaining the
   topic off the cuff to a friend; transcribe it, start `voice-examples.md` from it, and build the outline from
   their own words, then fact-check.
5. **Checks** (two subagents in parallel; for a batch, one call each covering every piece of the stop):
   - **viewer cold read** (the step-1 persona, sees only the script). Per section: would you really ask this? What
     does this mean, how does it follow from the line before, where did you get lost or bored, does the ending
     clearly answer the opening question? Fix what it trips on. **A fix that adds a caveat or an extra step goes to
     "Left for the blog" instead, unless it prevents a wrong belief that matters.**
   - **"would the director say this?"** (a subagent that has seen only `voice-examples.md` and the script): marks
     every line the director would have rewritten the way they rewrote earlier drafts (a cause and its result split
     into two sentences, extra commas, a vague word where a precise one fits, a long ending), with a rewrite.
   - the newcomer-test table and the hook → ending table in script.md;
   - `check_script.py <EP>`, then reread the fact-check against the final wording.
   Rerun a subagent only on the sections that changed.
6. **Shot table**, then send script + references **with the music shortlist** (audio.md). **Stop.**
7. After the director edits the script by hand: `check_script.py <EP> --fix`, read the difference for changes of
   meaning and new facts, and add the useful changes to `voice-examples.md` (before / after / why).

## 1 · The Door: start from a question the viewer already has
Experts live inside the knowledge; viewers stand outside the wall. Do not open with the topic ("today: P-waves"),
open with something they already care about or have felt, then show them the door.

**Test: would a friend actually say this out loud, right after the section before?** If it is a teacher's question
("do earthquakes send out only one kind of shaking?"), reword it from the viewer's side ("then why did I feel it
in two parts?").

- **Hook (S01):** the first seconds must grab; no greeting first. The best doors touch what viewers care about:
  their safety, something on their phone, news forwarded in the family group, a place they have been, a fact that
  contradicts what they heard. Curiosity about the subject alone is a weaker door.
- **Chapter card = the question, word for word**, in the viewer's words; it is also the YouTube chapter title and
  helps search.
- **No level signals** in narration or on screen: no "basics / advanced", no "the next part is harder".
- **The teaser short's question is a side door into the long video:** a separate, narrower question touching the
  same idea, *not* the long video's own hook (if the short fully answered the hook, the long video would have
  nothing left to reveal). It must pass the **typed-into-YouTube test**: something a person with no background
  would really search or ask. "Why does the phone alert arrive before the shaking?" passes; "which is faster, the
  P-wave or the S-wave?" fails (only someone who knows the terms asks it).

## 2 · The Map: one connected line, no walls
The long video is a chain of 3–5 questions; each grows out of the answer before it ("but then…?"). Difficulty
still rises, but nobody hits a wall: every harder step answers something the viewer already wants to know.

**Test (newcomer test): "someone who knows nothing but watched the chapters before can follow this because…"** One
line per chapter in script.md. If it cannot be filled in, rewrite, or move the point to "Left for the blog".

| Part | Purpose | Typical length |
|---|---|---|
| Hook (S01) | see the Door | 5–15 s |
| Intro | the channel intro | 4 s |
| C1 question 1 | the most basic question; everyday pictures, a demo on camera | 20–30 % |
| C2, C3 (C4, C5) | each grows out of the last answer: mechanism, key numbers, real data, a local case, common mistakes, where the simple picture stops working | 50–65 % |
| Closing | answer the hook's question(s), then one natural line that lands the idea; no "to sum up" section | 1–2 lines |
| END | a short goodbye over the end card. **It never names or teases the next video**, in voice or on screen (a change of schedule must not make a published video wrong). The end card shows one question for the comments | 5–8 s |

- **Ceiling: a curious secondary-school student can follow it with the animation.** Every new term arrives with a
  picture, an analogy or a demo; if it cannot, it goes to "Left for the blog".
- **Experts still get value** from real data, local cases, comparisons and the limits of the simple picture: depth
  without jargon.
- **End each chapter on the next question** (one line), so there is a reason to keep watching every 60–90 s.
- **Close every question the hook opens**, including the implied ones, **in plain words** in the closing, so a
  viewer who remembers only the start and the end still has the answer. Explaining it in the middle is not enough.
  List every hook question in script.md's table and mark where the closing answers it.
- **Answer, do not recap:** the closing never re-reads lines already heard. A **new angle that puts the chapters
  together** (the "oh, that is why" moment) is welcome when the topic has one.
- **The short** follows the same rule for its own question: the steps lead to the answer, and the ending answers
  the hook in a short, plain sentence, never a repeat of an earlier line. It never ends on a teaser and never
  names a day ("tomorrow"): shorts are watched for months.

### Left for the blog
When a point fails the newcomer test or would clutter a line, do not cut it silently: list it in script.md under
"Left for the blog" with its source. The description or blog picks from that list.

## 3 · The Scaffold: an analogy is put up, used, then taken down
An analogy hangs the unfamiliar on something familiar. If it runs too smoothly the viewer forgets it is only an
analogy, and the wrong belief stays.

**Test, at the logic draft: "if the viewer believes this analogy literally, what wrong belief do they leave
with?"** If that belief matters, the video says where the analogy stops, in one sentence. If it does not matter,
the caveat goes to "Left for the blog".

- **Finish every analogy, then map it back:** give its concrete numbers, then say plainly how the real thing is the
  same or different.
- **One job per analogy.**
- **An abstract property needs something you can touch** (a rock that "springs back fast" stayed hard to imagine
  until it became a block of jelly: hard to squash, easy to push sideways).
- **Pictures from the viewers' own life** (their school running track, a drive they all know, their money), not
  textbook set-ups.
- **Do not make it cute in a way that bends the science.** Check the analogy's geometry first (a shadow falls
  *below* a thing; if the real point is *above*, the shadow analogy is wrong).
- **Props show exactly the concept:** change only the thing being explained.
- **No slogans in place of an explanation.** A catchy phrase that stands for a concept leaves words but no picture.
  Show the steps with a concrete example. **If a concept needs more than about three steps, keep only the everyday
  analogy in the video and move the mechanism to "Left for the blog".**
- **Complete definitions, not halves.**

## 4 · The Keel: the story gets people on board, the evidence makes it sail
Only accuracy gives a paper abstract nobody watches; only attention gives exaggeration. The hook, analogies and
voice are the hull; the evidence is the keel.

**Test: could the director defend every sentence in front of people who work in the field?**

- Every fact and number is checked **before** it goes into the script (`fact-check.md`). Sources on screen and in
  the description.
- **Keep every hedge.** The friendly voice must never make a claim stronger ("not always" stays "not always").
  New everyday claims need a source like any other fact.
- **Numbers:** say the rounded value the source supports; the precise value and source live in references.md.
  Never mix sources that measure differently in one sentence.
- **One "how do we know?" beat per long video (optional, the director's call at the logic draft):** one or two
  lines on how it was measured, what is still an estimate, or what was once believed and then corrected. A line
  from the director's own work is the strongest version, but only when they offer it: never write one for them.
- **A short gives an honest limit only when leaving it out would leave a wrong belief.**

## 5 · The Voice: explaining to a friend across a table
A script can fail both ways: sounding like a lecture, or over-correcting into choppy fragments. The voice is casual
in its **words**, but its **sentences** are whole and connected.

**Test: read it aloud as the viewer, heard once, without the picture.** If you have to think about what a line
means, or the director would never say it that way, rewrite it.

Sentences and links:
- **Whole sentences** with a subject that say what they mean.
- **Say the real link to the line before** (so, because, which means, if…then, but). **Only the relation that is
  really there: no "but" without a real contrast.**
- **Restate the premise before a puzzle.**
- **A cause and its result go in one sentence.** Do not split one thought into two sentences or chop it with
  commas; put a comma only where the director would pause. Drop detail that does no job.
- **Explain the cause first**, then the result.
- **Key fact up front:** the number or event the viewer must know goes early.
- Name the thing instead of "it" when "it" could be unclear; full names over abbreviations.
- The subtitle length limit belongs to the **subtitle step** only (editing.md), never to writing: no sentence is
  chopped or rephrased to fit it.

Words:
- **Spoken words, but the precise word wins.** Avoid stiff written words; keep the director's own words and their
  regional way of speaking exactly as they say it (never "correct" a dialect word). Where accuracy matters, use
  the precise or technical word over a casual one.
- **The word the viewer knows.** Follow `CHANNEL.md` on which language technical terms are said in.
- **Describe first, name last:** the thing or situation, then "that point is called the hypocentre".
- **No lists of more than two** in narration: put the list on screen and say one surprising thing about it.
- **Do not announce, just start:** no "interestingly", "next", "let's look at", "first".

Talking to one person:
- "You" often; small check-ins ("right?"); the viewer's own experience.
- **Invite, do not assume:** "if you ever built a sandcastle as a child", not "when you built sandcastles at…".

**Variety is a reference, not a rule.** Following the director's voice should not turn into a formula, but
**repetition is fine when it is the simplest, most natural line and what a viewer would really ask**. Variety never
decides a hook or an ending; it only helps choose between two lines that are both natural.

**No jokes, puns or memes.** A long video may have one warm or surprising moment that makes the viewer smile. Test:
if the viewer would remember the line instead of the point, cut it. It must not bend a fact.

## Short
A complete little video, not a clip of the long one, written as if explaining to a 12-year-old (or a parent who
never studied the subject). It must make sense to someone who never sees the long video.
- **Shape: hook → but → so… so… → pay-off.** A check on the order, not slots to fill.
  - **Hook** (on camera, 2–4 s, no greeting): something the viewer has seen or knows, plus the missing piece.
    Curiosity needs a gap the viewer already feels and thinks can be closed; a made-up scene is not their gap.
  - **But:** the one thing that makes it puzzling. It may live inside the hook. No real "but" → probably the wrong
    hook.
  - **So… so…:** the steps, each one caused by the one before. Drop any step the next one does not need.
  - **Pay-off:** the conclusion the steps lead to, a short plain sentence that clearly answers the hook. **The
    answer appears in full once, here.** The opening may point the way but not give the whole answer. Never re-say
    an earlier line.
- **Length is a reference only; ask before cutting.** Never remove a line or an idea from a script (short or long)
  to meet a length on your own: tell the director the length, propose what could go, and cut only after their yes.
- **Clarity over the 60-second target.** A short may run to about 1:10–1:20 when the extra lines carry information
  or the logic between steps. **To shorten, remove a whole idea** (it becomes its own topic or goes to the
  description), never words inside sentences. Never cut a short into fragments: no dropped connectors, no
  half-sentences, no ending squeezed into a slogan.
- **One idea only.** If it needs two ideas, it is two shorts.
- **Mostly animation + one camera moment** (the hook or the demo). Reuse the long video's animations (simpler,
  fewer labels).
- Title band (two lines) = the question in the viewer's words.

## How much on camera
Plan **about a third of the episode on camera**, the rest animation (or whatever `CHANNEL.md` says). All camera
sections are fully written out and read.

| Put on camera | Keep as animation |
|---|---|
| Hook and closing line | Cross-sections, things that move or change over time |
| **Hands-on demos with household props** | Maps with real data, numbers, comparisons |
| Conversational "why" questions | Classifications, multi-step diagrams |
| The presenter's own judgement ("this does not mean anyone got it wrong") | Historical events, timelines |

- Present the proposal as a table in the logic draft and let the director pick.
- Demos must **not be able to fail on camera**, with props from a normal home. Plan a two-second animation replay
  in case the demo is unclear.
- The camera sections go onto the run sheet (recording.md). Name tag only on the first appearance.

## script.md format
Sections (template: `<studio>/templates/episode/script.md`, or the channel's translated copy in
`<project>/templates/`): 1 teleprompter (long video + short blocks) · 2 hook → ending · 3 newcomer test · 4 left
for the blog · 5 shot table · 6 facts.

```
S01  When the ground shakes, have you noticed
     that it gives one small jolt first?
C1   (chapter card: the question)
S02  [CAM · demo: a glass of water]
     ...
END  (a short goodbye; no next topic)
```
A line starting with a shot id starts a section; indented lines continue it. Shot ids: `S01..`, chapter cards
`C1..`, end card `END`, the short `X01..` in its own fenced block. Split a section into camera + animation with a
letter suffix (`S14` on camera, `S14b` animation). Mark camera sections with `[CAM]` (or `[CAM · demo: <prop>]`) as
the first line; Chinese scripts may use `【出镜】` / `【出镜 · 示范: …】`. A line in (brackets) is a note and is never
read or matched.

## What check_script.py checks
Per-section length and the estimated duration of the long video and the short; subtitle pieces that are very long
without a comma; optional: local-language technical terms that the channel says in English (`[language]
term_list`), American spellings (`british_spelling`). `--fix` tidies commas and spacing after hand edits (Chinese
/ Japanese scripts). Warnings are pointers to reread, not orders: the director's own wording wins.
