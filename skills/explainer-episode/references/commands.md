# Command cheat-sheet

All commands: `cd <studio>/scripts` then run with the studio venv
(`../.venv/Scripts/python.exe <script> ...` on Windows, `../.venv/bin/python <script> ...` elsewhere).
In Git Bash prefix `PYTHONIOENCODING=utf-8` when the output contains CJK text.

| Step | Command | Output |
|---|---|---|
| Health check | `doctor.py` | config, ffmpeg + encoder, fonts, Whisper model, music tools |
| New episode | `new_episode.py 01 granite "Working title" "Rocks"` | project + studio folders, templates, published-video list |
| Script length | `check_script.py 01-granite [--fix]` | units, ≈ duration, subtitle / term / spelling warnings; `--fix` tidies CJK spacing |
| Transcribe | `transcribe.py "<project>/episodes/01-granite" voice.wav cam-S05.m4a` | `work/<stem>.whisper.json/.txt` |
| Cut list | `<studio>/episodes/01-granite/make_edl.py` | prints SHOTS / CUES / SQUEEZE to paste into edl.py |
| Timeline | `gs_episode.py 01-granite timeline` | shot list with start/end/beats |
| Cut check | `gs_episode.py 01-granite check` | flags cuts that are not in silence |
| Render | `gs_episode.py 01-granite render preview [S03 S04]` | `<studio>/render/01-granite/videos/...` |
| Self-review | `review_frames.py 01-granite [preview|final] [S03 S04]` | `render/<EP>/review/page*.png` (3 frames/shot, CG composited) |
| Audio only | `gs_episode.py 01-granite mix` | final audio mix without the video |
| Subtitles only | `gs_episode.py 01-granite srt` | rewrites both SRTs in `work/` from CUES (no render) |
| Rough cut | `gs_episode.py 01-granite build preview` | `preview/01-granite-rough-480p.mp4` + SRTs |
| Final | `gs_episode.py 01-granite render final` then `build final` | `publish/01-granite-1080p.mp4` |
| Short | `gs_episode.py 01-granite short [preview|final]` | `publish/short/short-9x16-*.mp4` |
| Presenter photo | `gs_thumbs.py 01-granite photo camS05 7.0 [center_x]` | photo fades for thumbnails / IG |
| Thumbnails | `gs_thumbs.py 01-granite` | `publish/thumbnails/thumb-*.png` (4 layers), IG + FB covers |
| Backup code | `backup_code.py` | `[paths] backup` (default `<project>/studio-code-backup/`) |
| Brand audio | `make_music.py`, `../templates/intro_audio.py`, `make_samples.py` | music library, intro sting, listening samples |

## Quick looks (ffmpeg contact sheets)
```bash
ffmpeg -v error -y -i video.mp4 -vf "fps=1/4,scale=320:180,tile=4x6" -frames:v 1 -update 1 sheet.png
```
Use forward slashes in Python paths on Windows (`\f`, `\t` in a normal string become escape characters).
