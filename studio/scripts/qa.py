"""One self-check before anything is sent to the director.

    python qa.py <EPISODE> [preview|final]      -> <episode>/work/qa.md + printed summary

Runs check_script.py, the cut check (long video and short), review_frames.py, and scans the shot modules for
shots that show no source note (sourceNote(...)). It only collects: Claude still looks at the review pages
(text in the subtitle band, tofu boxes, labels beside their subject, chips repeating the narration, timing).
"""
import re
import subprocess
import sys

import gs_env
import gs_i18n

HERE = gs_env.STUDIO / "scripts"


def run(*args):
    p = subprocess.run([sys.executable, *args], cwd=HERE, capture_output=True, text=True, encoding="utf-8",
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    return p.returncode, (p.stdout + p.stderr).strip()


def unsourced(ep):
    """Scene classes whose body never sets a source note. Chapter / end cards and helpers are skipped."""
    out = []
    web = gs_env.STUDIO / "web" / "ep" / ep              # web engine: one module per shot (shots/, cam/)
    for f in sorted(list(web.glob("shots/*.js")) + list(web.glob("cam/*.js"))):
        if re.fullmatch(r"(S|X)\d+[a-z]?", f.stem) and not re.search(r"sourceNote|示意图|SRC|资料来源",
                                                                     f.read_text(encoding="utf-8")):
            out.append(f"{f.parent.name}:{f.stem}")
    edl = gs_env.code_dir(ep) / "edl.py"
    if edl.exists() and "SHORT_SRC" in edl.read_text(encoding="utf-8"):     # shorts may carry sources from edl
        out = [o for o in out if ":X" not in o and ":CamX" not in o]
    return out


LONG_PAUSE, TIGHT_JOIN, NGRAM = 0.9, 0.15, 8   # seconds, seconds, characters (from real review notes)


def rhythm(ep):
    """Pauses a director keeps asking to fix: silences > 0.9 s inside a shot's kept speech,
    joins (SQUEEZE cuts, shot to shot) that leave < 0.15 s of air, and the same 8 characters said twice inside one
    shot when the script says them once (a retake left in). A list to listen for, not an automatic change."""
    import gs_episode as G
    from gs_text import char_times, load_words, norm, sections
    E = G.load(ep)
    script = {sid: norm(t) for sid, t in sections(E.EP_DIR)}
    out, cache = [], {}
    for tl in ([G.timeline(E)] if E.SHOTS else []) + ([G.timeline(G.short_edl(E))] if E.SHORT_SHOTS else []):
        prev_tail = None
        for s in tl:
            if not s["src"] or s["kind"] not in ("anim", "cam", "foot"):
                prev_tail = None
                continue
            path, lag = G.speech_src(E, s)
            x = cache.setdefault(str(path), G.decode(path, channels=1, sr=16000))
            loud = lambda t: G.db(x[int(max(t - lag, 0) * 16000):int(max(t - lag + 0.05, 0) * 16000)]) > -35  # noqa: E731
            parts = G.pieces(s)
            for k, (a, b) in enumerate(parts):
                frames = [loud(a + i * 0.05) for i in range(int((b - a) / 0.05))]
                on = [i for i, v in enumerate(frames) if v]
                if not on:
                    continue
                for i, j in zip(on, on[1:]):
                    if (j - i) * 0.05 > LONG_PAUSE:
                        out.append(f"{s['id']} 停顿 {(j - i) * 0.05:.1f} 秒（原档 {a + i * 0.05:.2f}s 起）")
                head, tail = on[0] * 0.05, (len(frames) - 1 - on[-1]) * 0.05
                if k and parts_tail + head < TIGHT_JOIN:
                    out.append(f"{s['id']} 剪接点只留 {parts_tail + head:.2f} 秒空气（原档 {a:.2f}s），听起来会像被切")
                if k == 0 and prev_tail is not None and prev_tail + head < TIGHT_JOIN:
                    out.append(f"{s['id']} 接上一个镜头只留 {prev_tail + head:.2f} 秒空气")
                parts_tail = tail
            prev_tail = parts_tail + s["hold"]
            js = next((f for f in (E.EP_DIR / "work" / "noprompt" / f"{path.stem}.json",
                                   E.EP_DIR / "work" / f"{path.stem}.whisper.json") if f.exists()), None)
            if js:
                words = [w for w in load_words(js) if any(a <= w[0] + lag <= b for a, b in parts)]
                said, _ = char_times(words)
                ref = script.get(s["id"], "")
                seen = {}
                for i in range(len(said) - NGRAM + 1):
                    g = said[i:i + NGRAM]
                    seen[g] = seen.get(g, 0) + 1
                    if seen[g] == 2 and ref.count(g) < 2:
                        out.append(f"{s['id']} “{g}”说了两次，台本只有一次：重念没剪掉？")
                        break
    return out


def main():
    ep = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "preview"
    report = [f"# QA · {ep} · {mode}", ""]
    rc, txt = run("check_script.py", ep)
    warn = txt.split("subtitle / style warnings:")[-1].strip() if "warnings:" in txt else ""
    report += ["## 台本 check_script", "", "```", "\n".join(txt.splitlines()[-6:]) if not warn else warn[:3000], "```", ""]
    for what in (["check"], ["check", "short"]):
        rc, txt = run("gs_episode.py", ep, *what)
        report += [f"## 剪点 {' '.join(what)}", "", "```", txt[-1500:] or "(no output)", "```", ""]
    rc, txt = run("review_frames.py", ep, mode)
    report += ["## 画面自查页", "", "```", txt[-800:], "```", "",
               "看每一页：字幕带没有文字、没有方块字、标签在旁边、没有重复旁白的卡片、出现时间对字。", ""]
    try:
        rh = rhythm(ep)
    except Exception as e:  # missing audio / transcript must not block the rest of the QA
        rh = [f"（节奏检查没跑完：{e}）"]
    report += ["## 节奏", "", "\n".join(f"- {r}" for r in rh) if rh else "停顿、接点、重念都没发现问题。", ""]
    miss = unsourced(ep)
    report += ["## 没有来源标注的镜头", "", "、".join(miss) + "（逐个确认：有事实就要来源，纯示意要写“示意图”）"
               if miss else "全部都有来源或“示意图”。", ""]
    out = gs_env.ep_dir(ep) / "work" / "qa.md"
    out.write_text(gs_i18n.loc("\n".join(report)), encoding="utf-8")
    print(f"-> {out}\n   shots without a source note: {', '.join(miss) or 'none'}\n   rhythm notes: {len(rh)}")


if __name__ == "__main__":
    main()
