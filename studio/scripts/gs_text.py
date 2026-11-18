"""Shared text helpers for script ↔ recording matching (gs_cut.py, recording_diff.py, intake.py).

Script markers: a line may start with an on-camera marker, [CAM] or [CAM · demo: a rock] (Chinese scripts:
【出镜】 / 【出镜 · 示范: …】); any other […] in capitals or 【…】 is a stage note and is never matched. A line that
starts with a bracket ( or （ is a direction and is skipped.

    sections(ep_dir)        -> [(sid, text)] in script order, from script.md's teleprompter blocks (stage directions out)
    norm(s)                 -> comparable text: no spaces / punctuation, Chinese numerals as digits, latin lower-case
    load_words(json_path)   -> [(start, end, word, p)] from a Whisper json (prompted 'p' or unprompted 'probability')
    char_times(words)       -> (text, [time per char]) for locating a match in the recording
"""
import json
import re
from pathlib import Path

import gs_env

SHOT_ID = r"(?:S|C|X)\d+[a-z]?|END"
CAM_MARK = r"(?:【出镜(?:\s*·\s*示范[:：]\s*([^】]*))?】|\[CAM(?:\s*·\s*demo:\s*([^\]]*))?\])"   # groups: props
MARK = r"【[^】]*】|\[[A-Z][A-Z0-9 ·:,\-]*[^\]]*\]"
EN_DIGIT = {"zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
            "seven": "7", "eight": "8", "nine": "9"}
PUNCT = r"[\s,，.。!！?？;；:：、\"“”'‘’（）()\[\]【】—\-–…·/]"
CN_DIGIT = {"零": "0", "〇": "0", "一": "1", "二": "2", "两": "2", "三": "3", "四": "4", "五": "5", "六": "6",
            "七": "7", "八": "8", "九": "9"}


def sections(ep_dir):
    text = (Path(ep_dir) / "script.md").read_text(encoding="utf-8")
    out, cur = [], None
    for block in re.findall(r"```[a-z]*\n(.*?)```", text, re.S):
        cur = None
        for raw in block.splitlines():
            m = re.match(rf"^({SHOT_ID})\s+(.*)$", raw.strip())
            if m:
                cur = [m.group(1), []]
                out.append(cur)
                line = m.group(2)
            else:
                line = raw.strip()
            line = re.sub(MARK, "", line).strip()
            if line and cur and not line.startswith(("（", "(")):
                cur[1].append(line)
    return [(sid, " ".join(lines)) for sid, lines in out if lines and not sid.startswith("C")]


# Whisper's known inventions on silence / music (YouTube-caption training data): drop whole segments that contain them
# ([language] whisper_ignore in studio.toml replaces the list; the default is for Mandarin, empty for other languages)
_IGNORE = gs_env.LANG.get("whisper_ignore", ["请不吝", "点赞", "订阅", "转发", "打赏", "明镜", "字幕由", "字幕志愿者", "谢谢观看",
                                              "感谢观看"] if gs_env.LANG.get("narration", "zh") == "zh" else [])
HALLUCINATION = re.compile("|".join(map(re.escape, _IGNORE)) or r"(?!x)x")


def norm(s, digits=False):
    if digits:                                     # spoken slates: "zero four, S zero one" -> "04s01"
        s = re.sub(r"[A-Za-z]+", lambda m: EN_DIGIT.get(m.group(0).lower(), m.group(0)), s)
    s = re.sub(PUNCT, "", s).lower()
    return "".join(CN_DIGIT.get(c, c) for c in s) if digits else s


def ulen(s):
    """Length of a line in the narration's own unit: characters (Chinese / Japanese) or words."""
    return len(norm(s)) if gs_env.CJK else len(s.split())


def load_words(path, drop_hallucinations=True):
    """Words with text (Whisper's bare '-' tokens dropped). Segments with a known hallucination are removed."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return [(w["start"], w["end"], w["word"], w.get("p", w.get("probability", 1.0)))
            for s in d["segments"] if not (drop_hallucinations and HALLUCINATION.search(s.get("text", "")))
            for w in s.get("words", []) if norm(w["word"])]


def hallucinated(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return [s["text"] for s in d["segments"] if HALLUCINATION.search(s.get("text", ""))]


def char_times(words):
    chars, times = [], []
    for st, en, w, _ in words:
        n = norm(w)
        for i, c in enumerate(n):
            chars.append(c)
            times.append(st + (en - st) * i / max(len(n), 1))
    return "".join(chars), times
