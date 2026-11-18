"""Edit decision list · {{EPISODE}} (data only; tools: scripts/gs_episode.py, built through scripts/gs_run.py).

After recording:  intake.py -> gs_run.py {{EPISODE}} voicecut  (gs_cut.py writes edl_auto.py: SOURCES / SHOTS / CUES /
SQUEEZE / SHORT_*), which is used while SHOTS and SHORT_SHOTS below stay empty. Correct here only what the automatic
cut cannot know: CUE_TEXT = {"automatic subtitle": "subtitle as it was really said"}, extra SQUEEZE ranges, or copy
edl_auto.py's lists in and edit them (a filled edl.py always wins). What the director saves on the editing page
(work/edit.json) is applied last and is never overwritten.
"""
EPISODE = "{{EPISODE}}"
# CARD_THEME = "BLUEPRINT"   # house style of this piece (kit/themes.json); default: studio.toml [style] house

# Music (audio.md). Library / own tracks: first shot of each music section + the track's title, e.g.
#   TRACKS = [("S01", "Track Title"), ("C3", "Another Track")]      SHORT_TRACKS = [("X01", "Track Title")]
# Programmed score (optional component): SCORE = [...] (gs_score.py). No music: leave both empty.
TRACKS = []
SHORT_TRACKS = []

# Step 6, after the cut is approved: translations keyed on the final subtitle text, so they survive re-cuts.
CUE_EN = {}            # second subtitle language ([language] subtitle_second): {"subtitle": "translation"}
CUE_JA = {}            # third subtitle language ([language] subtitle_third), if the channel has one

GOLD_TERMS = []        # terms shown in the accent colour in the subtitles, e.g. ["Hypocentre", "Epicentre"]
SFX = []               # (shot, seconds into the shot, sound file in <project>/brand/sfx or the piece's folder, dB)

CAM_GRADE = "eq=gamma=1.08:saturation=1.03"    # the one light grade every camera shot gets; fix lighting on set
TAIL_EXPANDER = "light"                        # room echo at sentence ends: "off" | "light" | "strong"

# The teaser short (its own narration, X01, X02 ...): filmed upright, full 9:16 frame.
SHORT_VERTICAL = True
SHORT = {"segments": [], "title": ("Title line one", "Title line two?")}   # the short's question, two lines
