# <Channel name> video project

This folder is the synced project for the Explainer Studio pipeline (plugin `explainer-studio`).

- Channel profile and style bible: `CHANNEL.md` - read it before working on an episode.
- Local studio (code, venv, Whisper model, render cache; not synced): `<STUDIO PATH>`
  Settings: `<STUDIO PATH>/studio.toml`. Run scripts from `<STUDIO PATH>/scripts` with
  `<STUDIO PATH>/.venv/Scripts/python.exe` (Windows) or `<STUDIO PATH>/.venv/bin/python`.
- Episodes: `episodes/<NN>-<slug>/` (raw, work, preview, publish, notes.md). Each episode's notes.md holds the
  decisions so far - read it when continuing an episode in a new conversation.
- To make an episode, use the `explainer-episode` skill ("start a new episode about ..."). Stop after every step
  and wait for the director's confirmation.
- 480p previews first; 1080p only after approval. Redo only the shots the director comments on.
- After code changes run `python backup_code.py` so the studio can be rebuilt from this folder.
