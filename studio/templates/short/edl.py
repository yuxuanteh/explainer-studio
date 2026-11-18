"""Edit decision list · standalone short {{EPISODE}} (data only; built through scripts/gs_run.py).

A standalone short has no long video: everything is SHORT_*. After recording:  intake.py ->
gs_run.py {{EPISODE}} voicecut  (gs_cut.py writes edl_auto.py). Correct here only what the automatic cut cannot
know: CUE_TEXT = {"automatic subtitle": "subtitle as it was really said"}, extra SQUEEZE ranges. What the director
saves on the editing page (work/edit.json) is applied last and is never overwritten.
"""
EPISODE = "{{EPISODE}}"
# CARD_THEME = "BLUEPRINT"   # house style of this piece (kit/themes.json); default: studio.toml [style] house

SHORT_TRACKS = []      # music: [("X01", "Track Title")] (audio.md); empty = no music
CUE_EN = {}            # second subtitle language, after the cut is approved: {"subtitle": "translation"}
CUE_JA = {}            # third subtitle language, if the channel has one
GOLD_TERMS = []
SHORT_SFX = []

CAM_GRADE = "eq=gamma=1.08:saturation=1.03"
TAIL_EXPANDER = "light"

# Full 9:16 frame: animations rendered in portrait, camera takes filmed upright (a landscape file is turned upright
# by itself; if it comes out upside down: CAM_FRAME = {"camX01": "transpose=1"}).
SHORT_VERTICAL = True
CAM_FRAME = {}
SHORT = {"segments": [], "title": ("Title line one", "Title line two?")}   # the short's question, two lines
# SHORT_CTA = "..."    # bottom line of the short; default: studio.toml [channel] short_cta
