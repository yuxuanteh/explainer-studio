# Batches: several pieces written together, recorded in one session

A batch saves the director's time: one recording day for a few weeks of videos. A typical batch is two long videos
(each with its teaser short) and a few standalone shorts; any mix works.

## Set-up
1. Create every piece first (`new_episode.py`, `new_short.py … --batch`).
2. `new_batch.py <bNN> <piece> <piece> …` (long videos first) → `<project>/batches/<bNN>/batch.md` (the pieces
   table, the stops, pickups, a log), `batch.json` and `raw-inbox/`.
3. Inside a batch **`batch.md` is the only checklist**: each piece's notes.md points to it. Every new conversation
   reads batch.md first, then the notes.md of the piece in hand.

## Stops before recording (tick each after the director's approval)
- **A · Plan:** the topics, planned dates (a record, not a deadline), the field or series of each, duplicates
  checked against published videos, and for each long video the side-door question of its teaser.
- **B · Logic drafts:** the first long video's logic draft goes **first and alone**. Apply the director's notes on
  it to every other piece before sending those (their notes are usually about the method, not the topic).
- **C · Scripts + music shortlist:** again the first long video first, then the rest with its notes applied. One
  real-viewer interview and one pair of check subagents per stop, covering every piece of that stop.
- **D · Recording kit:** `new_batch.py <bNN> runsheet` (every section of every piece in set-up order: test clip, on
  camera piece by piece, then narration), the props list, the guide.

## Recording
One session. Every take starts with its slate (recording.md): long videos by their two-digit number ("zero five, S
zero three"), standalone shorts by their place in the batch ("short two, X zero one"). All files go into
`batches/<bNN>/raw-inbox/`, unrenamed.

## After recording
- **One intake stop** for the whole batch: `intake.py <bNN>`, the ⚠ rows with the director, `--apply`,
  `recording_diff.py` per piece, and the pickup list in batch.md.
- Then steps 4–7 of the skill **for the whole batch at each stop**: all voice cuts together, then all 480p builds
  with music, then finals and packages. If you think the batch should be split into waves (it is large, or the
  first pieces are due much earlier), say why and let the director decide.
- Build one piece at a time (`gs_run.py` allows one run at a time on a computer) and send the pieces of a stop
  together, in posting order.
- Notes on one piece often hold for the others: apply them across the batch before sending the next stop.

## At the end
Ask the director three short questions and write the answers into CHANNEL.md: what took them longest, what they
had to say twice, did the pieces sound too alike?
