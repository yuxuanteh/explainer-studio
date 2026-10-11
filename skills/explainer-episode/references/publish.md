# Upload & sharing package

Write `publish/publish.md` in upload order so the director can copy item by item. Links, handles, website and
blog details come from CHANNEL.md. After the first episode, its publish.md is the model for the next ones.

## Write like a person, not like AI
Descriptions, captions, pinned comments and posts must read as if the director wrote them.
- **No symbols at the start of lines**: no emoji headers, no • bullets, no 👉 arrows, no ①②③. Short paragraphs;
  label lines with plain words ("Chapters", "References", "Website:").
- Few or no emoji anywhere; never one per line. No em-dash chains, no "In this episode:" + bullet list.
- First person, conversational, concrete facts from the episode; avoid hype ("you won't believe") and AI phrases
  ("not only... but also", "let's dive in", "delve", "crucial", "fascinating", "game-changer").
- Chapter timecodes and hashtags (last line) stay - those are platform formats, not decoration.

## Contents checklist
1. **Titles** - 3 options, each with one line on why; short enough not to be cut on phones. Recommend one and pair
   it with a thumbnail.
2. **Thumbnails** - A/B/C (see visuals.md), all < 2 MB; Canva notes: canvas 1280x720, the layer files, fonts,
   outline colour and width, a table of each text with size and centre position. Suggest YouTube "test & compare".
3. **Description** - first two lines are the hook (search shows only these) -> what the episode covers (one plain
   paragraph) -> chapters from `gs_episode.py <EP> timeline` (first 00:00, ≥ 3 chapters, each ≥ 10 s; chapter
   cards are natural boundaries) -> references, one per line (description version from references.md + caveat
   line) -> blog link ("For more details: ...") -> website / socials / contact from CHANNEL.md -> honest music
   credit -> 3 hashtags on the last line.
4. **Hashtags** - 3 main + a few extra. **Tags** - comma-separated keywords in the channel's languages.
5. **Subtitles** - both SRTs from `work/`; copy into publish/. If YouTube asks for a translated title and
   description with the second track, write them (natural translation per the GOLDEN RULE, same chapters and
   references, a line saying which language the video is in and that subtitles exist).
6. **Pinned comment** - one discussion question (a local angle works well) + next-episode teaser.
7. **End screen & cards** - the last 12 s: video A top-right frame (best for viewer or a related video), video B
   bottom-right (series playlist), subscribe on the seal. 1-2 info cards where an older video is relevant
   (timestamp and reason).
8. **Settings checklist** - category Education, language, captions, made for kids no, playlist = series,
   altered/synthetic content "No" unless realistic AI imagery or voice was used (explain), comments on.
   Education fields: type, academic system and level (from CHANNEL.md), **Problems** = one line per chapter that
   answers a question: `m:ss <question>` (only questions the video actually answers).
9. **Quiz** (Video elements -> Quiz): 4-5 multiple-choice questions, 3 options, one correct, a one-line
   explanation + the timecode where the video answers it; wrong options are the misconceptions the episode
   corrects. Only facts already in references.md. If the channel is bilingual, write both language versions
   (same answers, same order). If CHANNEL.md has a website quiz format, add the quiz there too.
10. **Dedup** - table against published videos.
11. **Blog post** (if CHANNEL.md has a blog) - a real blog post with its **own angle**, not the script:
    - Pick a reader's question or practical angle the video didn't take, and build the post around it. If the
      headings map one-to-one onto the video's chapters or paragraphs follow the script, start again.
    - Add 3-5 of: a hook from real life; a hands-on part the reader can do; history and people behind the idea
      (with a source); local context with numbers; an open question; a correction of an earlier video in a
      callout; a closing checklist, then a teaser for the next episode.
    - Several images: animation frames from the master (crop off the subtitle band:
      `ffmpeg -ss <t> -i master.mp4 -frames:v 1 -vf "crop=1920:870:0:0,scale=1600:-1" out.png`); real-data
      figures (`extras/make_blog_figures.py` style: one function per figure, view every PNG before using it);
      1-3 freely licensed photos (Wikimedia Commons: check licence + author; public domain / CC BY / CC BY-SA
      only), credited in the caption and an image-credits section.
    - Fact-check everything like the script; same numbered references. Bilingual channels: write each language
      natively, not as a translation.
12. **Instagram** - 4:5 cover `social/ig-cover-1080x1350.png`; caption: hook + 2-3 short plain paragraphs with the
    key facts, "link in bio", 10-15 hashtags.
13. **Facebook** - friendly tone, a question to invite comments, 1200x630 image or the YouTube link.
14. **LinkedIn** (optional) - professional tone: what the video explains (short paragraphs with the numbers),
    who the presenter is (honest description from CHANNEL.md), facts checked against named sources.
15. **Short 9:16** - **it must answer its own hook** (a short that asks and never answers feels like clickbait).
    Cut hook -> the full answer -> a one-line wrap-up; drop any teaser the short doesn't resolve. The full video is
    offered as "more depth", not as the place the answer is hidden. Same for Reels / Shorts captions.
    `publish/short/short-9x16-*.mp4`, 15-60 s; captions for IG Reels, FB Reels, YouTube Shorts (title + #Shorts +
    link to the full video). **Cover** `publish/short/short-cover-1080x1920.png`: a `ShortCover` scene in thumbs.py
    (everything that matters inside the centre 1080x1350 for the IG grid crop). YouTube Shorts only lets you pick
    a frame in the mobile app, so name the best frame (seconds) in publish.md.

Before sending: open every image you produced (thumbnails, covers, a few short frames) and check text is not cut
off, nothing overlaps, and subtitles in the short don't stack.
