# Recording: the kit, the session, intake

## Recording kit (made before the session; one per episode, or one per batch)
- **Run sheet** `new_batch.py <EP | bNN> runsheet` → `work/runsheet.md` (batch: `batches/<bNN>/runsheet.md`): every
  section in set-up order (the test clip, then on camera, then narration) with the slate to say, the first words,
  props and framing, and a tick box. What is not ticked after the session is the pickup list.
- **Props list** from the script's `[CAM · demo: …]` lines. Props from a normal home; a demo must not be able to
  fail on camera.
- **Recording guide** in the director's language: quiet room, the same microphone for everything when possible,
  microphone 10–15 cm from the mouth and slightly to one side; landscape 16:9 with a clean wall beside the
  presenter for on-screen graphics; shorts filmed upright 9:16; fixed camera.
- Screen pictures for a monitor behind the presenter, if the set has one, in the house style.

## Slates: every take says what it is
Before each section the director says the slate, waits three seconds, then reads:
"zero four, S zero one" (episode 04, section S01) · "zero four, end" · "short three, X zero one" (the third
standalone short of a batch) · add "pickup" for a re-recording. Mandarin: "零四, S 零一" · "短片三, X 零一" · "补录".
One file may hold several sections, each with its slate. After a slip: stop two seconds and read the whole line
again, in the same file. Files need no renaming.

## Camera test (first thing in every session)
A 10-second test clip (`test.mp4`) in the day's light and clothes. Look at a frame: exposure of the face, white
balance, focus, framing, what is behind the presenter, room for graphics. Say what to change **before** the session
continues: lighting is fixed on set. The edit applies one light grade (`CAM_GRADE`) and nothing more.

## Intake (after the session)
The director puts every file into `raw/` (batch: `batches/<bNN>/raw-inbox/`) and says so.
1. `intake.py <EP | bNN>` writes down every file once (the only speech-recognition pass; saved without a script
   prompt, because a prompted pass can silently drop the section it was prompted with), reads the slate from the
   first seconds, scores the content against every script section, and writes `intake.md` + `intake-plan.json`:
   file → piece and section, the slate heard, match, status. Rows marked ⚠ need the director (a slate that does not
   match the content, two recordings of one section, nothing recognisable).
2. Resolve the ⚠ rows with the director (edit `dest` / `status` in the plan), then `intake.py <EP | bNN> --apply`:
   files are moved into each piece's `raw/` as `cam-<id>.mp4` (an on-camera section) or `voice-<id>.<ext>`
   (narration; a pickup gets a `p`), the transcript goes to `work/noprompt/`, unused takes to `raw/unused/`.
3. `recording_diff.py <EP>` → `work/recording-diff.md`: per recording, what was said against the script (not said,
   extra, said differently, a number that changed), possible retakes, long pauses, words the speech model was
   unsure of. Then step 4 of the skill (the automatic cut).

A recording already named `cam-<id>` / `voice-<id>` and put straight into `raw/` works too: the cut writes it down
by itself.

When a camera section also has a separate sound recording (a phone beside the camera), intake pairs them and
measures the lag; `EXT_AUDIO` in edl.py then uses the cleaner track.

## Pickups
A line that is missing, wrong in fact, or unusable goes onto the pickup list (batch.md or notes.md) with the
reason. The director records it with its slate + "pickup" in the same room and microphone; run intake again. Never
rewrite a subtitle to hide a missing line, and never build a line from pieces of other takes.
