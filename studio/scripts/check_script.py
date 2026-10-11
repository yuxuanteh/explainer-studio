"""Check an episode script (script.md): length, estimated duration, subtitle-friendly sentences.

    python check_script.py <EPISODE>

Reads the teleprompter block (the first ``` fenced block). Lines starting with a shot id (S01, C1 ...) start a
section; following indented lines belong to it. Estimates duration from the presenter's measured pace ([language] pace in studio.toml).
"""
import re
import sys
from pathlib import Path

import gs_env

UNIT = gs_env.LANG.get("length_unit", "cjk")   # "cjk" characters or "words"
PACE = float(gs_env.LANG.get("pace", 3.9 if UNIT == "cjk" else 2.5))   # units per second, measured on your voice:
#                            read a known passage aloud, divide its length by the seconds of speech
TARGET = (5 * 60, 10 * 60)  # 5-10 minutes per episode
MAX_CUE = int(gs_env.LANG.get("max_cue", 20 if UNIT == "cjk" else 8))   # units per subtitle cue before splitting
BRITISH = bool(gs_env.LANG.get("british_spelling", False))
PAUSE_PER_LINE = 0.5       # breath between teleprompter lines


# Local-language technical terms -> the English term the channel wants in narration / subtitles. Optional: a TOML
# file of `"local term" = "English term"` lines named by [language] term_list (see examples/terms-geoscience-zh.toml).
# Leave it empty if your channel keeps terms in the narration language.
def _load_terms():
    name = gs_env.LANG.get("term_list", "")
    if not name:
        return {}
    import tomllib
    p = Path(name) if Path(name).is_absolute() else gs_env.PROJECT / name
    return tomllib.loads(p.read_text(encoding="utf-8")).get("terms", {})


TERMS = _load_terms()


# American -> British spelling ([language] british_spelling = true). Whole words only, so
# "seismometer" / "parameter" are not flagged.
US_UK = {
    "epicenter": "epicentre", "hypocenter": "hypocentre", "center": "centre", "centered": "centred",
    "meter": "metre", "meters": "metres", "kilometer": "kilometre", "kilometers": "kilometres",
    "centimeter": "centimetre", "millimeter": "millimetre", "liter": "litre", "fiber": "fibre",
    "color": "colour", "colors": "colours", "gray": "grey", "behavior": "behaviour", "favorite": "favourite",
    "analyze": "analyse", "analyzed": "analysed", "modeling": "modelling", "modeled": "modelled",
    "traveled": "travelled", "traveling": "travelling", "defense": "defence", "aluminum": "aluminium",
    "mold": "mould", "neighbor": "neighbour", "harbor": "harbour", "labeled": "labelled",
}


def spelling_warnings(sid, line):
    out = []
    if not BRITISH:
        return out
    for w in re.findall(r"[A-Za-z]+", line):
        uk = US_UK.get(w.lower())
        if uk:
            out.append(f"{sid}: “{w}” -> British spelling “{uk}”")
    return out


def term_warnings(sid, line):
    out = []
    for zh in sorted(TERMS, key=len, reverse=True):          # longest first: 矩震级 before 震级
        if zh in line and TERMS[zh].split(" (")[0].split(" / ")[0].lower() not in line.lower():
            out.append(f"{sid}: “{zh}” -> say “{TERMS[zh]}” (technical terms in English)")
            line = line.replace(zh, "")
    return out


def spoken_len(s):
    """cjk: CJK characters count 1 each; a Latin word / number ~1.5 (it takes about that long to say).
    words: every word or number counts 1."""
    if UNIT != "cjk":
        return len(re.findall(r"\w+", s))
    cjk = len(re.findall(r"[一-鿿]", s))
    latin = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]*", s))
    return cjk + 1.5 * latin


def fix_block(path):
    """--fix: tidy the teleprompter block after the director edits it in a plain text editor: full-width commas
    -> ", ", a space between CJK and Latin letters / digits, no stray spaces between CJK characters (CJK only)."""
    if UNIT != "cjk":
        return 0
    text = path.read_text(encoding="utf-8")
    m = re.search(r"```[a-z]*\n(.*?)```", text, re.S)
    if not m:
        return 0
    out, changed = [], 0
    for line in m.group(1).split("\n"):
        hm = re.match(r"^(((?:S|C)\d+[a-z]?|END)\s+|\s+)", line)
        head, body = (hm.group(1), line[hm.end():]) if hm else ("", line)
        new = body.replace("，", ", ")
        new = re.sub(r"([一-鿿])([A-Za-z0-9])", r"\1 \2", new)
        new = re.sub(r"([A-Za-z0-9])([一-鿿])", r"\1 \2", new)
        new = re.sub(r"(?<=[一-鿿]) +(?=[一-鿿])", "", new)
        new = re.sub(r" {2,}", " ", new).rstrip()
        if new != body.rstrip():
            changed += 1
            print(f"  fixed: {body.strip()}  ->  {new.strip()}")
        out.append(head + new)
    if changed:                                   # newline="\n": Windows would otherwise rewrite every line ending
        path.write_text(text[:m.start(1)] + "\n".join(out) + text[m.end(1):], encoding="utf-8", newline="\n")
    return changed


def main():
    ep = sys.argv[1]
    if "--fix" in sys.argv:
        n = fix_block(gs_env.EPISODES / ep / "script.md")
        print(f"--fix: {n} line(s) tidied\n")
    text = (gs_env.EPISODES / ep / "script.md").read_text(encoding="utf-8")
    block = re.search(r"```[a-z]*\n(.*?)```", text, re.S)
    if not block:
        raise SystemExit("no ``` teleprompter block found in script.md")
    sections, cur = [], None
    for raw in block.group(1).splitlines():
        m = re.match(r"^((?:S|C)\d+[a-z]?|END)\s+(.*)$", raw.strip())
        if m:
            cur = [m.group(1), []]
            sections.append(cur)
            line = m.group(2)
        else:
            line = raw.strip()
        if line and cur:
            cur[1].append(line)

    total_chars, total_s, warnings = 0, 0.0, []
    print(f"{'shot':6s} {'chars':>6s} {'≈sec':>6s}  first line")
    for sid, lines in sections:
        chars = sum(spoken_len(x) for x in lines)
        secs = chars / PACE + PAUSE_PER_LINE * len(lines)
        total_chars += chars
        total_s += secs
        print(f"{sid:6s} {chars:6.0f} {secs:6.1f}  {lines[0][:28] if lines else ''}")
        for x in lines:
            for piece in re.split(r"[,.?!;:，。？！；：]", x):
                if spoken_len(piece) > MAX_CUE:
                    warnings.append(f"{sid}: “{piece.strip()}” is {spoken_len(piece):.0f} chars without a comma "
                                    f"-> split it (subtitle lines max ~{MAX_CUE})")
            warnings += term_warnings(sid, x)
            warnings += spelling_warnings(sid, x)
            if UNIT == "cjk" and "，" in x:
                warnings.append(f"{sid}: full-width comma “，” -> use half-width “, ” (subtitle rule)")
    m, s = divmod(int(total_s), 60)
    lo, hi = TARGET
    verdict = "within 5-10 min ✓" if lo <= total_s <= hi else ("too short (< 5 min)" if total_s < lo else "too long (> 10 min)")
    print(f"\ntotal {total_chars:.0f} spoken chars ≈ {m}:{s:02d}  ->  {verdict}")
    print(f"(target {lo / 60:.0f}-{hi / 60:.0f} min ≈ {lo * PACE:.0f}-{hi * PACE:.0f} chars at {PACE} chars/s; "
          "plus intro, chapter cards and the 12 s end card)")
    if warnings:
        print("\nsubtitle / style warnings:")
        for w in warnings:
            print("  -", w)


if __name__ == "__main__":
    main()
