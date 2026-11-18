"""Recording-diff report: what the director said vs the script, per section.

    python recording_diff.py <EPISODE> [stem ...]       -> <episode>/work/recording-diff.md

Reads the UNPROMPTED transcripts (work/noprompt/<stem>.json; the prompted ones hide repeats) of the recordings in
raw/ named cam-<id> / voice-<id>. Each script section belongs to the recording whose transcript actually contains it
(one voice file often holds many sections, a camera clip only its own); a section found nowhere
falls back to the latest recording whose id comes at or before it in script order. Flags, with times in the recording:
  retake candidates   a phrase said more often than the script has it (restart, slip, line read twice)
  missing / changed   script text not said, or said differently (follow the recording unless a FACT changed)
  long pauses         > 1.5 s between words inside the recording (often a restart)
  Whisper inventions  zero-length or p < 0.3 words, words lasting > 1 s: never act on these without checking loudness
"""
import difflib
import re
import sys
from collections import Counter

import gs_env
import gs_i18n
from gs_text import char_times, hallucinated, load_words, norm, sections

NGRAM = 5
GAP = 1.5
SLATE = re.compile(r"(短片[一二三四1-4]|short(one|two|three|four|five|six|\d)|[零一二三四五六七八九\d]{2}|(zero|oh|one|two|three|four|five|six|seven|eight|nine){2})?"
                   r"(s|x|结尾|end)?([零一二三四五六七八九\d]|zero|oh|one|two|three|four|five|six|seven|eight|nine){0,2}[a-z]?(补录|pickup)?")


def fmt(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def owners(secs, stems):
    """section id -> recording stem (the latest recording starting at or before it, long video and short apart)."""
    order = [sid for sid, _ in secs]
    start = {}
    for st in stems:
        sid = st.split("-", 1)[1]
        if sid in order:
            start[order.index(sid)] = st
    own, cur = {}, {"S": None, "X": None}
    for i, sid in enumerate(order):
        track = "X" if sid.startswith("X") else "S"
        if i in start:
            cur[track] = start[i]
        if cur[track]:
            own[sid] = cur[track]
    return own


def found_in(text, said):
    """Share of a section's text that appears, in order, in a transcript."""
    if not text:
        return 0.0
    sm = difflib.SequenceMatcher(None, text, said, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / len(text)


def owners_by_content(secs, stems, said_of, fallback):
    """section id -> the recording that says it best (same track first); `fallback` where nothing matches."""
    own = {}
    for sid, text in secs:
        t = norm(text)
        track = "X" if sid.startswith("X") else "S"
        cands = [st for st in stems if st in said_of and st.split("-", 1)[1][:1] == track] or                 [st for st in stems if st in said_of]
        best = max(cands, key=lambda st: found_in(t, said_of[st]), default=None)
        if best and found_in(t, said_of[best]) >= 0.5:
            own[sid] = best
        elif sid in fallback:
            own[sid] = fallback[sid]
    return own


def retakes(said, script, times):
    """Spans of the recording whose n-grams occur more often than in the script."""
    sc = Counter(script[i:i + NGRAM] for i in range(len(script) - NGRAM + 1))
    seen = Counter()
    hits = []
    for i in range(len(said) - NGRAM + 1):
        g = said[i:i + NGRAM]
        seen[g] += 1
        if seen[g] > max(sc[g], 0) and seen[g] > 1:
            hits.append(i)
    spans = []
    for i in hits:
        if spans and i <= spans[-1][1] + 2:
            spans[-1][1] = i + NGRAM
        else:
            spans.append([i, i + NGRAM])
    return [(times[a], said[a:b]) for a, b in spans]


def report(ep, only=()):
    E = gs_env.ep_dir(ep)
    secs = sections(E)
    stems = sorted({p.stem.split(".")[0] for p in (E / "raw").glob("*") if re.match(r"(cam|voice)-", p.name)},
                   key=lambda s: [sid for sid, _ in secs].index(s.split("-", 1)[1]) if s.split("-", 1)[1] in dict(secs) else 999)
    only = set(only)
    said_of = {}
    for st in stems:     # transcripts once, for matching sections to recordings
        js = next((f for f in (E / "work" / "noprompt" / f"{st}.json", E / "work" / f"{st}.whisper.json") if f.exists()), None)
        if js:
            said_of[st] = char_times(load_words(js))[0]
    own = owners_by_content(secs, stems, said_of, owners(secs, stems))
    lines = [f"# 录音对照 · {ep}", "",
             "> 自动生成（recording_diff.py）。用的是不带台本提示的转写，时间是录音档里的位置。",
             "> 字幕和剪辑照导演实际说的；只有**事实**说错、或重念 / 口误不清楚时才问导演。", ""]
    todo = 0
    for st in stems:
        if only and st not in only:
            continue
        mine = [(sid, norm(t)) for sid, t in secs if own.get(sid) == st]
        script = "".join(t for _, t in mine)
        if not mine and st in said_of:
            lines += [f"## {st}", "", "这个录音没有对上台本的任何段落（补录、测试片，或段落已经在别的录音里）。", ""]
            continue
        np_js, pr_js = E / "work" / "noprompt" / f"{st}.json", E / "work" / f"{st}.whisper.json"
        notes = []
        if not np_js.exists() and not pr_js.exists():
            lines += [f"## {st}", "", "⚠ 还没有转写（先跑 transcribe.py）", ""]
            todo += 1
            continue
        js = np_js if np_js.exists() else pr_js
        if js == pr_js:
            notes.append("没有不带提示的转写：重念可能被吞掉，要人工看")
        elif hallucinated(js):
            notes.append(f"Whisper 在静音处编了“{hallucinated(js)[0][:14]}…”，这一段已略过")
        words = load_words(js)
        said, times = char_times(words)
        cover = sum(b.size for b in difflib.SequenceMatcher(None, script, said, autojunk=False).get_matching_blocks())
        if js == np_js and pr_js.exists() and cover / max(len(script), 1) < 0.6:
            notes.append("不带提示的转写太不可靠，改用带提示的：重念可能被吞掉，要人工看")
            words = load_words(pr_js)
            said, times = char_times(words)
        bounds, pos = [], 0
        for sid, t in mine:
            bounds.append((pos, pos + len(t), sid))
            pos += len(t)

        def sec_at(i):
            return next((sid for a, b, sid in bounds if a <= i < b), bounds[-1][2] if bounds else "?")

        sm = difflib.SequenceMatcher(None, script, said, autojunk=False)
        match = sum(b.size for b in sm.get_matching_blocks()) / max(len(script), 1)
        lines += [f"## {st} · {', '.join(s for s, _ in mine) or '（台本里找不到这一段）'} · 吻合 {match:.0%}", ""]
        lines += [f"> ⚠ {n}" for n in notes] + ([""] if notes else [])
        rows = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal" or max(i2 - i1, j2 - j1) < 2:
                continue
            if re.fullmatch(r"[a-z0-9]*", script[i1:i2]) and re.search(r"[a-z]", script[i1:i2]) and tag == "replace" \
                    and abs((j2 - j1) - (i2 - i1) / 2) <= 3:
                continue        # an English term Whisper wrote in Chinese sounds (Penang -> 宾夷): not a real change
            if tag == "insert" and SLATE.fullmatch(said[j1:j2]):
                continue        # a spoken slate ("零四, S 零一") at the start of a section
            t = times[min(j1, len(times) - 1)] if times else 0
            kind = {"delete": "没念到", "insert": "多出来", "replace": "说法不同"}[tag]
            num = " · 有数字，核对事实" if re.search(r"\d", script[i1:i2] + said[j1:j2]) else ""
            rows.append(f"| {fmt(t)} | {sec_at(i1)} | {kind}{num} | {script[i1:i2] or '—'} | {said[j1:j2] or '—'} |")
        rt = retakes(said, script, times)
        gaps = [(a[1], b[0]) for a, b in zip(words, words[1:]) if b[0] - a[1] > GAP]
        odd = [(w[0], w[2], w[3], w[1] - w[0]) for w in words if w[3] < 0.3 or w[1] - w[0] > 1.0]
        if rt:
            lines += ["**可能的重念 / 口误**（同一句说了不止一次）：", ""]
            lines += [f"- {fmt(t)}  “{txt}”" for t, txt in rt] + [""]
            todo += 1
        if rows:
            lines += ["| 时间 | 段落 | 类型 | 台本 | 实际说的 |", "|---|---|---|---|---|"] + rows + [""]
            todo += any("没念到" in r or "核对事实" in r for r in rows)
        if gaps:
            lines += ["停顿 > 1.5 秒：" + "，".join(f"{fmt(a)}–{fmt(b)}" for a, b in gaps), ""]
        if odd:
            lines += ["Whisper 不确定的词（别据此改字幕，先看音量）：" +
                      "，".join(f"{fmt(t)} “{w.strip()}” (p {p:.2f}, {d:.2f}s)" for t, w, p, d in odd[:12]), ""]
        if not (rt or rows or gaps or odd):
            lines += ["跟台本一致。", ""]
    missing = [sid for sid, _ in secs if sid not in own]
    if missing:
        lines += ["## 没有录音的段落", "", "、".join(missing), ""]
        todo += 1
    out = E / "work" / "recording-diff.md"
    out.write_text(gs_i18n.loc("\n".join(lines)), encoding="utf-8")
    print(f"-> {out}  ({'needs a look from the director' if todo else 'nothing for the director to decide'})")
    return todo


if __name__ == "__main__":
    report(sys.argv[1], sys.argv[2:])
