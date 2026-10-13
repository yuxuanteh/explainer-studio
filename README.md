# Explainer Studio

A Claude Code plugin for making science-explainer YouTube episodes, where Claude does the work of the whole
crew and you direct. You write nothing in code. You pick the topic, record your voice and on-camera clips,
watch the previews and approve each step.

It was built for and with the Mandarin earth-science channel 金釘子 GoldenSpike and then generalised. Every rule
in it comes from something that went wrong, or right, on a real episode.

## What it does, step by step

1. **Topic and dedup.** It checks the idea against your published videos. One concept per episode.
2. **Script in three depth layers** (the basics, how it works, going deeper), 5-10 minutes long. Every fact is
   checked against official or academic sources and logged in a references table. The ending answers the
   question the hook asked.
3. **Episode palette.** Each episode gets its own colours, and the channel colours stay fixed.
4. **Recording handoff.** A teleprompter script, a recording guide, and a check of your camera test clip
   (brightness and white balance).
5. **Transcription with faster-whisper.** Cuts come from loudness rather than Whisper's word edges, long pauses
   are squeezed out, and subtitles are timed to the words.
6. **Animation in Manim.** Things appear on the spoken word, CG overlays sit on your camera shots, and the frames
   are self-reviewed before you see them.
7. **Rough cut at 480p.** Voice processing, a through-composed music score made by Claude with real instrument
   samples, SFX, burned subtitles and a second-language SRT.
8. **1080p master.**
9. **Upload package.** Titles, layered thumbnails for Canva, a description with chapters and references, the
   end screen, a quiz, a blog post, Instagram, Facebook and LinkedIn posts, and a 9:16 short that answers its
   own hook.

Claude stops after every step and waits for your OK.

It can also build your channel's **website**: a free, bilingual site on GitHub Pages with your videos, a blog,
quizzes, a gallery and an About page, edited in a web editor. It's made from the template at
https://github.com/yuxuanteh/explainer-studio-site.

## Install

In Claude Code (CLI, desktop app or IDE extension), type these two commands:

```
/plugin marketplace add yuxuanteh/explainer-studio
/plugin install explainer-studio@explainer-studio
```

## What to type, start to finish

Open an empty folder for your channel in Claude Code, then type these messages one at a time and answer
Claude's questions in between.

**1. Set up the video studio** (tools, folders, your channel profile, your music):
> Set up my studio with the explainer-studio plugin. My channel is called "<name>". It explains <topic> to
> <audience> in <language>, with <language> subtitles. Ask me whatever else you need.

**2. Make it look like your channel** (do any of these, any time):
> Here is my logo: <path to file>. Use it for the watermark, the intro and the end card.
> Use these colours: <hex codes>, or: propose three palettes that fit my topic and show me swatches.
> Use the fonts <font names> from Google Fonts.
> Redesign the intro animation around my logo and show me a preview.
> Make the music warmer / brighter / more minimal and send me a 30-second sample.

**3. Make the website** (free on GitHub Pages; needs a GitHub account and the GitHub CLI):
> Make my channel website with the explainer-studio-site template. My GitHub username is <username>.

and later, for example:
> Change the website colours / fonts / logo to match my channel.
> Remove the earthquake monitor page and rename the gallery to "Field photos".
> Make the website editor labels English.

> Add free visitor statistics to my website with Cloudflare Web Analytics.

**4. Make an episode**:
> Start a new episode about <topic>.

Claude stops after every step and waits for you. Useful things to say along the way:

- "the recordings for 02 are in raw" (after you record)
- "S05: the label covers my hand, move it left" (a note on a preview)
- "the music in chapter 2 is too busy" (Claude sends audio clips instead of rebuilding the video)
- "make the final" (only after you approve the rough cut)
- "make the upload package"

## What you need

- Claude Code with a Claude plan.
- Windows, macOS or Linux, about 6 GB of disk space, and 16 GB of RAM recommended. Whisper runs on the CPU; a GPU
  speeds it up.
- A phone or mic for your voice. A camera is optional but recommended: about a third of each episode is on camera.
- Python 3.12, ffmpeg, FluidSynth, the faster-whisper large-v3 model, the GeneralUser GS SoundFont, and free
  fonts. The setup skill installs all of these.

## How it is organised

| Folder | What it is |
|---|---|
| `skills/explainer-episode/` | the production workflow and its references (script writing, fact checking, visuals, audio, episode code, publishing) |
| `skills/studio-setup/` | installation, the channel interview, moving to a new computer |
| `skills/channel-website/` | create, customise and publish the channel website from the template repo |
| `studio/` | Python pipeline copied into your local studio: `gs_episode.py` (timeline, cut check, render, build, mix, SRT, short), `transcribe.py`, `check_script.py`, `gs_thumbs.py`, `review_frames.py`, `gs_shotkit.py` (Manim helpers), music generation, `doctor.py` |
| `studio/extras/` | topic-specific examples from the original channel: monitor wallpapers and blog figures from real seismic data |
| `channel-template/` | `CHANNEL.md` (your style bible), `CLAUDE.md`, recording guide |
| `examples/` | the GoldenSpike channel profile and a Mandarin to English geoscience term list |

Your files live in two places. The **project folder** can be synced with Google Drive, Dropbox or similar, and
holds the scripts, recordings, outputs and brand files. The **studio folder** stays local and is not synced: it
holds the code, the Python environment, the Whisper model and the render cache.

## Languages

The pipeline was built for Mandarin narration with English technical terms and an English subtitle track. The
Whisper language, length counting (characters or words), pace, subtitle length, spelling checks, term list and
"new idea" pause words are all settings in `studio.toml`. For word-based languages, the cue matcher in
`make_edl.py` needs a small change, which is noted in the file.

## Licences

The code and docs in this repository are MIT licensed. Nothing third-party is bundled; setup downloads these:
Manim (MIT), faster-whisper (MIT), FFmpeg (LGPL/GPL builds), FluidSynth (LGPL), GeneralUser GS (its own free
licence, which allows use in music productions), fonts from Google Fonts (SIL OFL) and Natural Earth (public
domain). The music the pipeline generates is composed by Claude. Credit it honestly in your descriptions.
