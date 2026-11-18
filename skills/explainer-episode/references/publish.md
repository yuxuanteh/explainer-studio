# Upload & sharing package

One file, `publish/publish.md`, **laid out by platform in upload order** (YouTube first, then the others from
`CHANNEL.md`), every text copy-ready in its own block, so the director pastes from top to bottom. The director
uploads and schedules by hand; nothing is posted for them. After the first video, its publish.md is the model for
the next.

## Write the way the director talks
Descriptions, captions, pinned comments and posts read as if the director wrote them: first person, their
sentences (`voice-examples.md`), concrete things from the video.
- **No symbols at the start of lines:** no emoji headers, no bullets, no arrows, no ①②③. Short paragraphs; plain
  words as labels ("Chapters", "References").
- Few or no emoji. No hype ("you won't believe"), no stock phrases ("let's dive in", "not only… but also",
  "fascinating", "game-changer"), no report of the schedule ("this week's video").
- Chapter timecodes and hashtags stay: those are platform formats.
- A caption does not chop sentences with commas to look punchy.

## Contents
1. **Title:** one title, with one line on why. Short enough not to be cut on phones. Translated titles are
   translations of that one (the golden rule), not new ideas.
2. **Thumbnail and short cover:** the ideas first as text; made after the director's pick (visuals.md).
3. **Description:** the first two lines are the hook (search shows only these) → what the video covers, one plain
   paragraph → the blog or website line if the channel has one → chapters from `gs_episode.py <EP> timeline`
   (first 00:00, at least three, each at least 10 s; chapter cards are the boundaries, titles are the questions) →
   references, one per line, from `work/references.md` → links from CHANNEL.md → the music credit (audio.md) → three
   hashtags on the last line.
4. **Tags:** comma-separated keywords in the channel's languages.
5. **Subtitles:** the files from `publish/` (the narration language and each translation), named
   `subtitles.<language>_<COUNTRY>.srt` and, for the short, `short/short.<language>_<COUNTRY>.srt`. Facebook takes
   subtitle files only with such names (list them under each Reel for Facebook); YouTube takes the same files.
   For each translated track YouTube wants a translated title and description: write them.
6. **Pinned comment:** the video's question for the comments (the one on the end card).
7. **End screen and cards:** the last 12 s. Video top right: "best for viewer" or a related video; bottom right:
   the series playlist; the subscribe element in the bottom-left slot. One or two info cards where an older video
   is relevant, with the timestamp and the reason.
8. **Settings:** category (the best fit; a news short is news), language, captions, made for kids: no, playlist,
   altered or synthetic content: "no" unless realistic AI imagery or voice was used.
9. **The short** (teaser or standalone): title, description **without links** (links in a short's description
   cannot be clicked), the related video, the subtitle files, the cover (`short/short-cover-1080x1920.png`,
   visuals.md "Short covers": uploaded as the Shorts thumbnail and used as the Reels cover).
10. **Other platforms** (only those CHANNEL.md lists): one caption per platform in that platform's habits (where
    links do not work in captions, point to the profile instead); say which file to upload and in which format.
11. **Duplicate check:** a line on how this video differs from the nearest published one.
12. **Blog post, quiz** or anything else the channel publishes with a video: only if CHANNEL.md says so, and with
    its **own angle**: a reader's question the video did not take, not the script retold in order.

## Translation
The golden rule (SKILL.md). British or American spelling as CHANNEL.md says. Subtitle translations are written
into edl.py at step 6, after the cut is approved; titles and descriptions here.

## After posting
The director sends the links. Add them to `notes.md`, add the music tracks to the used-list with the posting date,
and add the video to the list of published videos (`[paths] videos_json`, if the channel keeps one) so the next
duplicate check sees it.
