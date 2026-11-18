# Command sheet

All commands: from `<studio>/scripts`, with the studio's own Python (`../.venv/Scripts/python.exe` on Windows,
`../.venv/bin/python` elsewhere). Set `PYTHONIOENCODING=utf-8` when a console cannot print the narration language.

| Step | Command | Result |
|---|---|---|
| New episode | `new_episode.py 04 rock-cycle "Title" "Series"` | project + studio folders, script template, checklist, list of published videos and pieces in production |
| New short outside a batch | `new_short.py next city-quake "Title" "Field" [news]` | `shorts/ss<NNN>-<slug>/` |
| New short inside a batch | `new_short.py next hollow-hill "Title" "Field" --batch` | `shorts/s<NNN>-<slug>/` |
| New batch | `new_batch.py b02 04-rock-cycle 05-… s005-… s006-…` | `batches/b02/batch.md`, `batch.json`, `raw-inbox/` |
| Run sheet | `new_batch.py b02 runsheet` / `new_batch.py 04-rock-cycle runsheet` | `runsheet.md` |
| Script check | `check_script.py 04-rock-cycle [--fix]` | lengths, estimated duration, warnings |
| Intake | `intake.py 04-rock-cycle` / `intake.py b02`, then `--apply` | `intake.md`, files renamed into `raw/`, transcripts in `work/noprompt/` |
| Recording diff | `recording_diff.py 04-rock-cycle` | `work/recording-diff.md` |
| **Build anything** | `gs_run.py <EP> voicecut` / `preview [ids]` / `final` (`--keep-cut`, `--no-anim`) | every check in order, stops at the first problem; `READY` lines name the files; logs and `timings-<mode>.json` in `render/<EP>/logs/` |
| Review + editing pages | `gs_review.py [port]` (run in the background) | http://localhost:8770 · notes in `work/review/<name>.notes.json` · edits in `work/edit.json` |
| Automatic cut alone | `gs_cut.py <EP> [--dry]` | `edl_auto.py`, `work/cut-report.md` |
| Listen to one stretch again | `transcribe.py <episode folder> --stretch <file> <from> <to>` | words merged into `work/noprompt/<stem>.json` (old file kept) |
| Voice cut alone | `gs_voicecut.py <EP> [short]` | `preview/<EP>-voicecut-480p.mp4` / `preview/short-voicecut.mp4` |
| Timeline / cut check | `gs_episode.py <EP> timeline [short]` / `check [short]` | shot list with times; cuts not in silence |
| Sound only | `gs_episode.py <EP> mix` | the mix without video |
| Subtitle files only | `gs_episode.py <EP> srt` | `work/subtitles.<lang>_<COUNTRY>.srt`, `publish/short/short.<lang>_<COUNTRY>.srt` |
| Music library | `gs_tracks.py ["Title" …]` | length, tempo, bars, whether the used-list has the track |
| House styles | `gs_styles.py list` / `preview [ids] [--vertical]` / `use <ID>` | `<project>/brand/styles/compare.png` |
| QA before sending | `qa.py <EP> [preview\|final]` | `work/qa.md` |
| Review sheets | `review_frames.py <EP> [preview\|final] [ids]` | `render/<EP>/review/page*.png` |
| Commons photo | `gs_photo.py <EP> "<Commons file page>" [name.jpg] [--width 1920]` | `web/ep/<EP>/assets/<name>` + the credit row |
| Back up the code | `backup_code.py` | `<project>/studio-code-backup/` |
| Parts | `setup_studio.py list` / `status` / `install <part>` / `remove <part>` / `set <section> <key> <value>` | see the studio-setup skill |
| This computer | `probe.py [--minutes 6] [--short 1] [--model …] [--json]` | hardware, speed, time per step |
| Try-it sample | `make_sample.py [--record]` | the short `ss900-sample` with a synthetic recording |

## Animation engine (`gs_web.py`)
| Step | Command | Result |
|---|---|---|
| Starting modules | `gs_web.py <EP> stubs` | a module in the house style for every shot without one |
| Stills of one shot | `gs_web.py <EP> stills S05 0.5,3,7 [--guides]` | `render/<EP>/web-qa/S05/` PNGs + `sheet.png` |
| Determinism | `gs_web.py <EP> check [ids]` | ok / NOT deterministic per shot |
| Render shots | `gs_web.py <EP> render preview\|final [ids]` | `render/<EP>/videos/web/<mode>/<id>.mp4` (+ `-matte.mp4` for camera graphics) |
| Live workspace | `gs_web.py <EP> review [ids] [--short]`, then run the printed `node … editor.mjs …` in the background | a page with the shots and their sound |
| Motion QA | `gs_web.py <EP> qa [--short]` | technical checks + dead air, jumps, flash frames |

The renderer is the motion-showreel plugin's `scripts/` folder (found in Claude Code's plugin folders; `[paths]
motion_showreel` or the `MOTION_SHOWREEL` environment variable overrides). Its Node packages are in
`<studio>/web/node_modules` (`setup_studio.py install animation`).

## Quick look at a video (contact sheet)
```bash
ffmpeg -v error -y -i video.mp4 -vf "fps=1/4,scale=320:180,tile=4x6" -frames:v 1 -update 1 sheet.png
```
