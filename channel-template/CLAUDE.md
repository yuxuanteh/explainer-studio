# <Channel name> video project

This folder is the project of the Explainer Studio pipeline (Claude Code plugin `explainer-studio`).

- Channel profile and decisions: `CHANNEL.md`. Read it before working on any piece.
- How the director talks: `voice-examples.md`. Scripts and captions are written from it.
- Local studio (tools, Python, speech model, render cache; not synced): `<STUDIO PATH>`
  Settings: `<STUDIO PATH>/studio.toml`. Run the tools from `<STUDIO PATH>/scripts` with
  `<STUDIO PATH>/.venv/Scripts/python.exe` (Windows) or `<STUDIO PATH>/.venv/bin/python`.
- Pieces: `episodes/<NN>-<slug>/`, `shorts/<id>/`, `batches/<bNN>/` (raw, work, preview, publish, notes.md). A piece's
  notes.md (inside a batch: `batch.md`) holds the checklist and the decisions so far: read it when continuing in a
  new conversation.
- To make a video use the `explainer-episode` skill ("start a new episode about …"). Follow its steps and stops
  exactly: stop after every step and wait for the director's approval.
- To add or remove a part of the studio, change the house style or the music choice, update or move:
  the `studio-setup` skill.
- 480p previews first; the 1080p master only after approval. Redo only the shots the director comments on.
- After changing code or animation modules run `python backup_code.py`, so the studio can be rebuilt from this
  folder.
