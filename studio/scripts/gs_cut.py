"""Automatic first cut from the script and the recordings.

    python gs_cut.py <EPISODE> [--dry]      -> <code dir>/edl_auto.py + <episode>/work/cut-report.md

Claude trims first, then the director checks and fixes by ear. This tool makes that first trim:
  1. each script section belongs to the recording that says it (cam-<id> for [CAM] sections, else by content);
  2. every teleprompter line is found in the recording, going backwards from the end, so when a line was said more
     than once the LAST take is kept (recording.md: after a slip, pause and re-read the whole line);
  3. cuts are placed from loudness, not Whisper's word edges: in 0.12 s before the voice (0.45 s before a new idea),
     out 0.15 s into the following silence; levels are relative to each file's own speech and room noise;
  4. what lies between two kept lines is removed (SQUEEZE) when it holds speech (a dropped take) or, in an animation
     shot, when the pause is longer than 0.75 s; a pure pause on camera is left alone (a cut there would jump);
  5. subtitles = the script's lines (split at commas to about 20 characters), timed on the words that were said.
     Lines where the recording differs from the script are listed in the report: the subtitle follows the
     recording, so correct those texts (editing page, or CUE_TEXT in edl.py).
gs_episode.py reads edl_auto.py while edl.py's own SHOTS / SHORT_SHOTS are empty; a hand-filled edl.py always wins.
English / Japanese subtitles are left empty here: translation comes after the director has approved the cut.
"""
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

import gs_env
from gs_text import CAM_MARK, MARK, SHOT_ID, char_times, load_words, norm, ulen

L = gs_env.tr
ZH = gs_env.LANG.get("narration", "zh") == "zh"

FR = 0.02
HEAD, HEAD_NEW, TAIL, LONG_PAUSE, JOIN = 0.12, 0.45, 0.15, 0.75, 0.2
PAUSE_SPLIT = 0.6      # a gap between words longer than this ends a saying: a line is never stretched across it
NEW_IDEA = tuple(gs_env.LANG.get("new_idea_words", ["可是", "但是", "然而", "那", "我们", "还有一点", "反过来", "所以"] if ZH else
                                 ["But", "So", "Now", "However", "And yet"]))
CUE_MAX = int(gs_env.LANG.get("max_cue", 20 if gs_env.CJK else 9))   # characters or words per subtitle


# ---------------------------------------------------------------------------------------------- script

def script(ep):
    """[(sid, on camera?, [lines])] in script order, chapter cards included (lines = the card's question)."""
    text = (gs_env.ep_dir(ep) / "script.md").read_text(encoding="utf-8")
    out = []
    for block in re.findall(r"```[a-z]*\n(.*?)```", text, re.S):
        cur = None
        for raw in block.splitlines():
            m = re.match(rf"^({SHOT_ID})\s+(.*)$", raw.strip())
            line = m.group(2) if m else raw.strip()
            if m:
                cur = [m.group(1), False, []]
                out.append(cur)
            if not cur:
                continue
            if re.match(CAM_MARK, line):
                cur[1] = True
            line = re.sub(MARK, "", line).strip()
            if line and not line.startswith(("（", "(")):
                cur[2].append(line)
    return [tuple(r) for r in out]


# ---------------------------------------------------------------------------------------------- audio

def levels(path):
    """dB per 20 ms frame of a recording, its speech level and the threshold between room noise and voice."""
    import gs_episode as G
    x = G.decode(path, channels=1, sr=16000)
    n = len(x) // 320
    db = 20 * np.log10(np.sqrt(np.mean(x[:n * 320].reshape(n, 320) ** 2, axis=1)) + 1e-9)
    speech, floor = np.percentile(db, 92), np.percentile(db, 8)
    return db, speech, floor + (speech - floor) * 0.38


def voice_start(db, thr, t_word, back=1.2):
    """Where the voice really starts near a word's start: walk back while it is still loud, stop at 0.1 s of quiet."""
    i = int(t_word / FR)
    lo = max(0, int((t_word - back) / FR))
    j = min(i + int(0.3 / FR), len(db) - 1)          # Whisper may start the word a little early
    while j < len(db) - 1 and db[j] < thr and j < i + int(0.6 / FR):
        j += 1
    while j > lo and not (db[max(j - 5, 0):j] < thr).all():
        j -= 1
    return j * FR


def voice_end(db, thr, t_word_end, fwd=1.5, quiet=0.2):
    """Where the voice stops after a word's end: the start of the first `quiet` seconds of silence."""
    i, q = max(0, int((t_word_end - 0.25) / FR)), int(quiet / FR)
    for j in range(i, min(len(db) - q, i + int(fwd / FR))):
        if (db[j:j + q] < thr).all():
            return j * FR
    return t_word_end


def has_speech(db, thr, a, b, need=0.3):
    seg = db[int(a / FR):int(b / FR)] >= thr
    run = best = 0
    for v in seg:
        run = run + 1 if v else 0
        best = max(best, run)
    return best * FR >= need


# ---------------------------------------------------------------------------------------------- matching

def find_last(line, said, limit):
    """(start, end, coverage) of the last place before `limit` where `line` is said; None when it is not there."""
    n = len(line)
    if not n:
        return None
    best = None
    for end in range(limit, max(n // 2, 1) - 1, -1):
        a = max(0, end - int(n * 1.35) - 2)
        sm = difflib.SequenceMatcher(None, line, said[a:end], autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        cov = sum(b.size for b in blocks) / n
        if cov < 0.55:
            if best and end < best[1] - n:           # well past the match we already have
                break
            continue
        s, e = a + blocks[0].b, a + blocks[-1].b + blocks[-1].size
        if e - s > n * 1.6:                          # matched chars scattered over two takes: not one saying
            continue
        cand = (s, e, cov)
        if best is None or cov > best[2] + 0.04:
            best = cand
        if best and end < best[1] - n:
            break
    if best:                                         # a restart inside the match ("像 A 像 A 就…"): keep the last start
        s, e, cov = best
        for s2 in range(e - max(int(n * 0.8), 1), s, -1):
            sm = difflib.SequenceMatcher(None, line, said[s2:e], autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size]
            if blocks and sum(b.size for b in blocks) / n >= cov - 0.02:
                best = (s2 + blocks[0].b, e, sum(b.size for b in blocks) / n)
                break
    return best


def sound(text):
    """One toneless syllable per character, so Whisper's sound-alike characters still match the script (a place name or an
    unusual word written in other characters with the same sound). zh/ch/sh -> z/c/s and -ng -> -n: many speakers merge them.
    Only a last try for lines the character match cannot find."""
    if not ZH:
        return list(text)
    from pypinyin import lazy_pinyin
    out = []
    for ch in text:
        if "一" <= ch <= "鿿":
            py = re.sub(r"^([zcs])h", r"\1", lazy_pinyin(ch)[0])
            out.append(re.sub(r"ng$", "n", py))
        else:
            out.append(ch)
    return out


def split_cue(line):
    """One teleprompter line -> subtitle pieces of about CUE_MAX characters, split only at commas."""
    parts = [p for p in re.split(r"(?<=[,，])\s*", line.strip()) if p]
    out, cur = [], ""
    for p in parts:
        if cur and ulen(cur) + ulen(p) > CUE_MAX:
            out.append(cur.strip())
            cur = p
        else:
            cur = (cur + " " + p).strip() if cur else p
    if cur:
        out.append(cur.strip())
    # no comma or full stop left hanging at the end of a subtitle (the director removed every one of them on the
    # editing page)
    return [re.sub(r"\s*[,，]\s*", ", ", c).strip().rstrip((".。,， " if gs_env.CJK else ",， ")).strip() for c in out]


# ---------------------------------------------------------------------------------------------- the cut

DRY = "--dry" in sys.argv


def silent_words(words, db, thr):
    """(from, to) of stretches with sound but no words: a word that lasts over 2 s with speech after its first 0.6 s
    and no other word inside it, or a gap of over 1 s between two words with speech in it."""
    out = []
    for i, (s0, e0, _, _) in enumerate(words):
        if e0 - s0 > 2.0 and has_speech(db, thr, s0 + 0.6, e0, need=0.6) and                 not any(s0 + 0.3 < (a + b) / 2 < e0 for j, (a, b, _, _) in enumerate(words) if j != i):
            out.append((s0 + 0.6, e0))
        if i + 1 < len(words) and words[i + 1][0] - e0 > 1.0 and has_speech(db, thr, e0 + 0.15, words[i + 1][0] - 0.15, need=0.6):
            out.append((e0, words[i + 1][0]))
    return out


def cut(ep):
    E = gs_env.ep_dir(ep)
    secs = script(ep)
    raw = sorted(p for p in (E / "raw").iterdir() if re.match(r"(cam|voice)-.*\.(mp4|m4a|mov|wav)$", p.name, re.I))
    stems = {p.name.split(".")[0]: p for p in raw}
    rec, flags = {}, []
    for st, p in stems.items():
        # the no-prompt transcript first: a prompted pass silently drops the section it was prompted with (it has
        # happened: the first seconds of a recording were missing from the prompted transcript)
        js = next((f for f in (E / "work" / "noprompt" / f"{st}.json", E / "work" / f"{st}.whisper.json") if f.exists()), None)
        if not js:
            # a recording put straight into raw/ under its final name (no intake): listen to it now, without a prompt
            import transcribe
            out, _ = transcribe.run(transcribe.decode(p), None)
            out["file"] = p.name
            js = E / "work" / "noprompt" / f"{st}.json"
            js.parent.mkdir(parents=True, exist_ok=True)
            js.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        words = load_words(js)
        said, times = char_times(words)
        ends = []
        for s, e, w, _ in words:
            ends += [e] * len(norm(w))
        db, speech, thr = levels(p)
        # sound but no words: Whisper sometimes writes one word that lasts for seconds over speech it gave no word
        # times for, and a retake hidden there is never found. Listen to that stretch again
        # alone, once, and say so in the report.
        done_f = js.with_name(f"{st}.stretches.json")
        done = json.loads(done_f.read_text(encoding="utf-8")) if done_f.exists() else []
        for a, b in silent_words(words, db, thr):
            if any(abs(a - x) < 0.3 and abs(b - y) < 0.3 for x, y in done):
                continue
            if DRY or js.parent.name != "noprompt":
                flags.append(f"- {st} {a:.1f}–{b:.1f} " + L("s: sound but no words in the transcript (a retake may hide there): please listen", "秒有声音，可是听写没有字（可能藏着重念）：请听一下"))
                continue
            got = subprocess.run([sys.executable, str(Path(__file__).with_name("transcribe.py")), str(E), "--stretch",
                                  p.name, f"{a:.2f}", f"{b:.2f}"], capture_output=True, text=True, encoding="utf-8")
            heard = next((l[8:] for l in got.stdout.splitlines() if l.startswith("STRETCH ")), "")
            done.append([round(a, 2), round(b, 2)])
            done_f.write_text(json.dumps(done), encoding="utf-8")
            flags.append(f"- {st} {a:.1f}–{b:.1f} " + L(f"s: sound but no words; this stretch was transcribed again alone and gave \"{heard or '(still no words)'}\": please listen",
                                                       f"秒有声音，可是听写没有字：这一段单独重新听写了，听到「{heard or '（还是没有字）'}」，请听一下"))
            words = load_words(js)
            said, times = char_times(words)
            ends = []
            for s, e, w, _ in words:
                ends += [e] * len(norm(w))
        rec[st] = dict(path=p, said=said, sound=sound(said), t0=times, t1=ends, db=db, thr=thr, limit=len(said))
    # owner of each spoken section
    owner = {}
    for sid, cam, lines in secs:
        if sid.startswith("C") or not lines:
            continue
        text = norm("".join(lines))
        if f"cam-{sid}" in stems and cam:
            owner[sid] = f"cam-{sid}"
            continue
        track = "X" if sid.startswith("X") else "S"
        cands = [st for st in stems if st.split("-", 1)[1][:1] == track] or list(stems)
        score = {st: sum(b.size for b in difflib.SequenceMatcher(None, text, rec[st]["said"], autojunk=False)
                         .get_matching_blocks()) / max(len(text), 1) for st in cands}
        best = max(score, key=score.get)
        if score[best] >= 0.5:
            owner[sid] = best
    # lines, backwards per recording, so the last take of each line wins
    found, report, per_rec = {}, flags, {}
    for sid, cam, lines in reversed(secs):
        if sid not in owner:
            continue
        R = rec[owner[sid]]
        got = []
        for line in reversed(lines):
            n = norm(line)
            zh_only = re.sub(r"[a-z]+", "", n) if ZH else ""   # Whisper writes English terms as Chinese sounds (calcite -> 靠塞)
            hit = (find_last(zh_only, R["said"], R["limit"]) if len(zh_only) >= 4 else None) or \
                find_last(n, R["said"], R["limit"])
            if not hit and len(zh_only) >= 4:        # last try by sound (Whisper wrote sound-alike characters)
                hit = find_last(sound(zh_only), R["sound"], R["limit"])
                if hit:
                    report.append(f"- {sid} 这一行是照读音找到的（Whisper 听成别的字）：「{line}」→ 录音「{R['said'][hit[0]:hit[1]]}」，请听一下")   # zh only
            if not hit:
                got.append((line, None))
                report.append(f"- {sid} " + L("line not found (the sound around it is kept whole, please listen): ", "找不到这一行（它前后的声音整段留着，请听一下）：") + f"「{line}」")
                continue
            # only the last clause re-read ("head clause, tail… [slip] tail… tail…"): the whole-line match lands on an earlier take of that clause; keep the head clause where
            # it was said and the LAST saying of the tail clause, as two pieces (the speech between them is squeezed)
            pieces = [(line, hit)]
            cut_at = max(line.rfind(","), line.rfind("，"))
            if cut_at > 0:
                head_l, tail_l = line[:cut_at + 1].strip(), line[cut_at + 1:].strip()
                tn = norm(tail_l)
                th = find_last(tn, R["said"], R["limit"]) if len(re.sub(r"[a-z]+", "", tn) if ZH else tn) >= (4 if ZH else 12) else None
                if th and th[0] >= hit[1] and th[2] >= 0.8:
                    hh = find_last(norm(head_l), R["said"], hit[1])
                    if hh and hh[1] <= th[0]:
                        pieces = [(tail_l, th), (head_l, hh)]
                        report.append(f"- {sid} " + L("second half re-read: the last saying is kept, the earlier one is cut (please listen): ", "后半句重念：留最后一次，前面的说法剪掉（请听一下）：") + f"「{tail_l}」")
            for line, (s, e, cov) in pieces:
                n = norm(line)
                # words at the start or end of a line that are not in the match (mostly English terms): how many
                # characters of the recording they should take, so the span can be stretched over them below
                bl = [b for b in difflib.SequenceMatcher(None, n, R["said"][s:e], autojunk=False).get_matching_blocks() if b.size]
                est = (lambda x: len(re.sub(r"[a-z]", "", x)) + (len(re.findall(r"[a-z]", x)) + 1) // 2) if ZH else len  # noqa: E731
                head, tail = (est(n[:bl[0].a]), est(n[bl[-1].a + bl[-1].size:])) if bl else (0, 0)
                R["limit"] = s
                h = [s, e, 0.0, 0.0, cov, head, tail]
                per_rec.setdefault(owner[sid], []).append(h)
                got.append((line, h))
                if cov < 0.86:
                    report.append(f"- {sid} " + L(f"said differently from the script ({cov:.0%}): script ", f"说的跟台本不一样（{cov:.0%}）：台本") + f"「{line}」→ " + L("recording ", "录音") + f"「{R['said'][s:e]}」")
        found[sid] = list(reversed(got))
    # stretch each line over its unmatched first / last words, never into its neighbour (a line ending in English terms
    # matched only its Chinese part: the English words must not fall into a cut), then take the times
    for st, lst in per_rec.items():
        R = rec[st]
        lst.sort(key=lambda h: h[0])
        new = []
        for k, h in enumerate(lst):
            s2, e2 = h[0] - (h[5] + 1 if h[5] else 0), h[1] + (h[6] + 1 if h[6] else 0)
            if k:
                p = lst[k - 1]
                gap, need = h[0] - p[1], p[6] + h[5]
                s2 = (h[0] - round(gap * h[5] / need) if need else h[0]) if gap <= need + 3 else max(s2, p[1] + p[6] + 1)
            if k + 1 < len(lst):
                q = lst[k + 1]
                gap, need = q[0] - h[1], h[6] + q[5]
                e2 = (h[1] + round(gap * h[6] / need) if need else h[1]) if gap <= need + 3 else min(e2, q[0] - q[5] - 1)
            # never stretch across a pause: past it is another saying (a start stretched two characters back
            # once landed on the last word of the earlier take 2.7 s before, which kept that take's tail)
            s2, e2 = max(0, min(s2, h[0])), min(len(R["said"]), max(e2, h[1]))
            for j in range(h[0] - 1, s2 - 1, -1):
                if R["t0"][j + 1] - R["t1"][j] > PAUSE_SPLIT:
                    s2 = j + 1
                    break
            for j in range(h[1], e2):
                if R["t0"][j] - R["t1"][j - 1] > PAUSE_SPLIT:
                    e2 = j
                    break
            new.append((s2, e2))
        for h, (s2, e2) in zip(lst, new):
            h[:] = [s2, e2, voice_start(R["db"], R["thr"], R["t0"][s2]), voice_end(R["db"], R["thr"], R["t1"][e2 - 1]), h[4]]
        # two lines said without a pause: the loudness walk runs into the neighbour, so they meet where the words meet
        # (otherwise their subtitles overlap)
        for p, h in zip(lst, lst[1:]):
            if h[2] < p[3]:
                mid = round((R["t1"][p[1] - 1] + R["t0"][h[0]]) / 2, 2)
                p[3] = h[2] = mid
    # shots, squeezes, cues
    main, short, cues_main, cues_short, squeeze, sources = [], [], [], [], {}, {}
    intro_done = False
    for sid, cam, lines in secs:
        is_short = sid.startswith("X")
        rows = short if is_short else main
        if sid.startswith("C"):
            if not intro_done and not is_short:
                rows.append(("INTRO", "intro", None, 0.0, 4.20, 0.0, "intro", {}))
                intro_done = True
            rows.append((sid, "chapter", None, 0.0, 3.0, 0.0, "curious", {}))
            continue
        allr = found.get(sid, [])
        hits = [(l, h) for l, h in allr if h]
        # a line that was not found sits somewhere between its neighbours: never cut between those two
        keep_after = {id(allr[i - 1][1]) for i in range(1, len(allr)) if allr[i][1] is None and allr[i - 1][1]}
        if not hits:
            report.append(f"- {sid} " + L("no recording: this section stays empty (pickup)", "没有录音：这一段先空着（补录）"))
            continue
        st = owner[sid]
        R = rec[st]
        key = st.replace("-", "")
        sources[key] = R["path"].name
        kind = "cam" if cam and st.startswith("cam-") else ("card" if sid == "END" else "anim")
        first_new = hits[0][0].startswith(NEW_IDEA) or "?" in hits[0][0] or "？" in hits[0][0]
        t_in = max(0.0, hits[0][1][2] - (HEAD_NEW if first_new else HEAD))
        t_out = hits[-1][1][3] + TAIL
        prev = next((r for r in reversed(rows) if r[2] == key), None)
        if prev and t_in < prev[4]:                  # two shots back to back in one recording: share the gap
            mid = round((prev[4] - TAIL + hits[0][1][2]) / 2, 2)
            rows[rows.index(prev)] = (*prev[:4], mid, *prev[5:])
            t_in = mid
        cuts = []
        for (la, ha), (lb, hb) in zip(hits, hits[1:]):
            # a join inside a shot gets a little more air than a shot edge (qa.py flags joins under 0.15 s as "cut off")
            a, b = ha[3] + JOIN, hb[2] - (HEAD_NEW if (lb.startswith(NEW_IDEA) or "?" in la or "？" in la) else JOIN)
            if b - a <= 0.05 or id(ha) in keep_after:
                continue
            dropped = has_speech(R["db"], R["thr"], a, b)
            if dropped or (kind != "cam" and hb[2] - ha[3] > LONG_PAUSE):
                cuts.append((round(a, 2), round(b, 2)))
                if dropped:
                    report.append(f"- {sid} " + L(f"cut {a:.1f}–{b:.1f} s ({st}): there is speech in it, most likely the earlier take of a re-read; the later one is kept",
                                                 f"剪掉 {a:.1f}–{b:.1f} 秒（{st}）：里面有话，应该是重念的前一次，留后面那一次"))
        if cuts:
            squeeze[sid] = cuts
        hold = round(max(12.0 - (t_out - t_in - sum(b - a for a, b in cuts)), 0.0), 2) if sid == "END" else 0.0
        rows.append((sid, kind, key, round(t_in, 2), round(t_out, 2), hold, "curious", {}))
        for line, (s, e, li, lo, cov) in hits:
            pieces = split_cue(line)
            total = sum(len(norm(p)) for p in pieces) or 1   # time is shared by characters in every language
            pos = 0
            for p in pieces:
                k0, k1 = pos / total, (pos + len(norm(p))) / total
                c0 = min(e - 1, s + int(round((e - s) * k0)))
                c1 = min(e - 1, max(c0, s + int(round((e - s) * k1)) - 1))
                a = li if pos == 0 else R["t0"][c0]
                b = lo if k1 >= 1 else R["t1"][c1]
                (cues_short if is_short else cues_main).append((key, round(a, 2), round(max(b, a + 0.4), 2), p, ""))
                pos += len(norm(p))
    return dict(SOURCES=sources, SHOTS=main, CUES=cues_main, SHORT_SHOTS=short, SHORT_CUES=cues_short,
                SQUEEZE=squeeze), report


def write(ep, data, report):
    code = gs_env.code_dir(ep)
    lines = [f'"""Generated by gs_cut.py for {ep}: the automatic first cut. Do not edit; rerun gs_cut.py.',
             'gs_episode.py uses it while edl.py has no SHOTS / SHORT_SHOTS of its own."""']
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{k} = {{")
            lines += [f"    {a!r}: {b!r}," for a, b in v.items()]
            lines.append("}")
        else:
            lines.append(f"{k} = [")
            lines += [f"    {r!r}," for r in v]
            lines.append("]")
    (code / "edl_auto.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
    rep = [L(f"# Automatic first cut · {ep}", f"# 自动初剪 · {ep}"), "",
           L("> Made by gs_cut.py. Claude trims first, then you check and fix by ear. Subtitles follow the recording; the list below is what to listen for.",
             "> gs_cut.py 生成。Claude 先剪，导演再用耳朵检查、修改。字幕照录音，下面列的是要留意的地方。"), ""]
    rep += report or [L("Every line was found in the recording, matches the script, and no retake had to be cut.", "每一行都在录音里找到，跟台本一致，没有剪掉重念。")]
    (gs_env.ep_dir(ep) / "work" / "cut-report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ep = sys.argv[1]
    data, report = cut(ep)
    for name in ("SHOTS", "SHORT_SHOTS"):
        for r in data[name]:
            print(name, r[:6])
    print("SQUEEZE", data["SQUEEZE"])
    print(f"{len(data['CUES'])} cues, {len(data['SHORT_CUES'])} short cues")
    print("\n".join(report) or "nothing to flag")
    if "--dry" not in sys.argv:
        write(ep, data, report)
        print("->", gs_env.code_dir(ep) / "edl_auto.py")
