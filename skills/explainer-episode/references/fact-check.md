# Fact checking (every episode, before the director records)

The director must be able to stand behind every sentence in front of experts in the field. So a claim or
number goes into the script only after it has been checked against a reliable source.

## Sources, in order of preference
1. Official agencies and institutions for the topic (CHANNEL.md lists the channel's usual ones; e.g. for
   earth science: USGS, national meteorological / geological surveys, GFZ, EMSC, IRIS, NOAA).
2. Peer-reviewed papers (Google Scholar, journal pages; cite authors, year, journal, DOI).
3. Standard textbooks and university pages.
4. Wikipedia only to find the primary source, never as the citation.

Use WebSearch / WebFetch; quote what the page actually says. If two good sources disagree, say which convention
the script uses and note the other.

## Traps (learned on real episodes)
- **Never mix sources in one sentence.** One agency's magnitude with another agency's depth makes a number no one
  published. Quote one source's pair and name it; if both are shown, show both pairs side by side.
- **Check that a detail was actually published.** A coordinate repeated everywhere may belong to a different
  event; find the bulletin itself. If there is no published value, show it as approximate and say so on screen
  and in references.md.
- Old scripts and old videos are for dedup only - their facts may be outdated; re-check everything reused.
- Newspaper numbers are second-hand: trace them to the primary source and cite that; cite the newspaper only for
  what it reported (news card).

## work/references.md format
```
## Claim by claim
| Claim in the video | Verdict | Source |
| Upper-crust P-wave speed ~6 km/s | ✅ typical upper-crust value; agency X uses ~7 km/s average | [2][5] |
## Sources
1. Agency / authors (year). Title. URL
## Description version (copy-paste)
References
Short label – URL
```
Mark each claim ✅ supported, ⚠️ supported with caveat (write the caveat), ❌ not supported (remove / rewrite).
Anything ❌ or unfindable goes to the director as a question, not into the script.

## On screen and in the description
- Every shot showing a fact, number, map or data gets `gs.source_note("Source: …")` (top-right, left of the
  watermark). Diagrams that are not real events say so ("schematic, not a real event").
- The description's references block is the description version from references.md, plus caveats in one line.
- The blog post ends with the same numbered references.
- Maps: Natural Earth (public domain) - credit it.

## Re-check after recording
If the director said something different from the script (Whisper transcript), check whether the spoken version
is still correct; subtitles follow what was said only when it is correct, otherwise ask about a pickup line.
