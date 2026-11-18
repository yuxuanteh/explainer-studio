"""Intake: sort a recording session's files into each piece's raw/.

    python intake.py <EPISODE | bNN>            -> work/intake.md + intake-plan.json (batch: batches/<bNN>/)
    python intake.py <EPISODE | bNN> --apply    -> moves the files the plan marks ok into raw/ with their new names
    options: --inbox DIR  (default: episode raw/ or batches/<bNN>/raw-inbox/)   --cache DIR   --all (also files
             that already have cam- / voice- names: for testing)

Every take starts with a spoken slate ("zero four, S zero one", "short three, X zero one", + "pickup" for a pickup;
Mandarin: "零四, S 零一", "短片三, X 零一", "补录"; recording.md). For each
file: transcribe without a prompt (cached), read the slate from the first seconds, score the content against every
script section of every piece, decide the section, pair camera clips with the phone memo of the same section, and
measure the phone-vs-camera lag (cross-correlation of loudness envelopes; claps proved unreliable).
Rows marked ⚠ need the director; resolve them by editing the plan's "dest" / "status" ("ok" / "unused"), then --apply.
"""
import difflib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

import gs_env
import gs_i18n
from gs_text import load_words, norm, sections

VIDEO = {".mp4", ".mov", ".mts"}
AUDIO = {".m4a", ".wav", ".mp3", ".aac"}
SR = 8000


# ------------------------------------------------------------------------------------------------ pieces

def pieces(target):
    """[(slot, id)]: slot = what the director says in the slate ('04' for episode 04, '1'-'9' for the standalone shorts of a batch)."""
    if re.fullmatch(r"b\d{2}", target):
        bj = json.loads((gs_env.BATCHES / target / "batch.json").read_text(encoding="utf-8"))
        return [(p["slot"], p["id"]) for p in bj["pieces"]], gs_env.BATCHES / target / "raw-inbox", gs_env.BATCHES / target
    return [(target[:2], target)], gs_env.ep_dir(target) / "raw", gs_env.ep_dir(target) / "work"


# ------------------------------------------------------------------------------------------------ transcripts

def transcript(path, cache):
    js = cache / f"{path.name}.json"
    if not js.exists():
        import transcribe
        out, _ = transcribe.run(transcribe.decode(path), None)
        cache.mkdir(parents=True, exist_ok=True)
        js.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return load_words(js)


def slate(words):
    """(slot, section id, pickup?) from the first ~8 s, or (None, None, False)."""
    head = norm("".join(w for s, _, w, _ in words if s < 8.0), digits=True)
    pickup = "补录" in head or "pickup" in head
    # 影片 / 短篇: a slip of "影片二" for 短片二 is accepted; Whisper also hears 短片 as 短篇
    m = re.search(r"(?:短片|影片|短篇|short)(\d)\D{0,3}x(\d{1,2})([a-z]?)", head)
    if m:
        return m.group(1), f"X{int(m.group(2)):02d}{m.group(3)}", pickup
    m = re.search(r"(\d{2})\D{0,3}(end|结尾|[sxc])(\d{0,2})((?:[a-z](?![a-z]))?)", head)
    if m:
        kind = m.group(2)
        sid = "END" if kind in ("end", "结尾") else f"{kind.upper()}{int(m.group(3) or 0):02d}{m.group(4)}"
        return m.group(1), sid, pickup
    return None, None, pickup


def scores(said, secs):
    out = {}
    for sid, text in secs:
        t = norm(text)
        if len(t) < 4:
            continue
        sm = difflib.SequenceMatcher(None, t, said, autojunk=False)
        out[sid] = sum(b.size for b in sm.get_matching_blocks()) / len(t)
    return out


# ------------------------------------------------------------------------------------------------ sync

def pcm(path):
    raw = subprocess.run([gs_env.FFMPEG, "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def lag(cam, phone, max_lag=10.0):
    """Seconds the phone started after the camera (= edl.EXT_AUDIO lag), via log-envelope cross-correlation."""
    def env(x):
        n = int(SR * 0.01)
        e = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode="same"))[::n // 2]
        e = np.log(e + 1e-4)
        return e - e.mean(), n // 2 / SR
    ec, dt = env(pcm(cam))
    ep, _ = env(pcm(phone))
    best, bl = -1e9, 0.0
    for sign, a0, b0 in [(1, ec, ep), (-1, ep, ec)]:
        for k in range(int(max_lag / dt)):
            a, b = a0[k:], b0[:len(a0) - k]
            m = min(len(a), len(b))
            if m < 200:
                break
            c = float(np.dot(a[:m], b[:m]) / m)
            if c > best:
                best, bl = c, sign * k * dt
    return bl, best


# ------------------------------------------------------------------------------------------------ main

def plan(target, inbox=None, cache=None, include_named=False):
    ps, default_inbox, out_dir = pieces(target)
    inbox = Path(inbox) if inbox else default_inbox
    cache = Path(cache) if cache else inbox / ".intake"
    secs = {pid: sections(gs_env.ep_dir(pid)) for _, pid in ps}
    slot_of = dict(ps)
    files = sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in VIDEO | AUDIO
                   and (include_named or not re.match(r"(cam|voice)-", p.name)) and not p.name.startswith("test"))
    rows = []
    for f in files:
        words = transcript(f, cache)
        said = norm("".join(w for _, _, w, _ in words))
        slot, ssid, pickup = slate(words)
        best = []
        for _, pid in ps:
            for sid, sc in scores(said, secs[pid]).items():
                best.append((sc, pid, sid))
        best.sort(reverse=True)
        covered = {}
        for sc, pid, sid in best:
            if sc >= 0.6:
                covered.setdefault(pid, []).append(sid)
        r = dict(src=str(f), name=f.name, camera=f.suffix.lower() in VIDEO, slate=f"{slot or ''} {ssid or ''}".strip(),
                 pickup=pickup, status="ok", note="")
        if slot and ssid and slot in slot_of:
            pid = slot_of[slot]
            sc = dict((sid, s) for s, p, sid in best if p == pid).get(ssid, 0)
            r.update(piece=pid, sid=ssid, score=sc)
            if sc < 0.4:
                r.update(status="⚠", note=f"念的编号是 {ssid}，可是内容不像这一段（{sc:.0%}）")
        elif best and best[0][0] >= 0.6:
            sc, pid, _ = best[0]
            order = [s for s, _ in secs[pid]]
            first = min(covered[pid], key=order.index)          # a file starts at the earliest section it covers
            r.update(piece=pid, sid=first, score=sc, note="没听到编号，按内容判断" if not slot else f"编号“{r['slate']}”不在这一批")
        else:
            r.update(piece=best[0][1] if best else None, sid=best[0][2] if best else None,
                     score=best[0][0] if best else 0, status="⚠", note="听不出编号，内容也对不上")
        if r.get("piece"):
            order = [s for s, _ in secs[r["piece"]]]
            cov = sorted(covered.get(r["piece"], []), key=order.index)
            r["covers"] = cov or [r["sid"]]
            text = norm("".join(t for s, t in secs[r["piece"]] if s in r["covers"]))
            explained = sum(b.size for b in difflib.SequenceMatcher(None, said, text, autojunk=False).get_matching_blocks())
            if r["status"] == "ok" and not slot and said and explained / len(said) < 0.6:
                r.update(status="⚠", note=f"没听到编号，而且录音里有 {1 - explained / len(said):.0%} 对不上这几段")
        rows.append(r)

    # names: camera clip of an on-camera (【出镜】) section -> cam-<sid>.mp4, the phone memo of the same section ->
    # cam-<sid>.m4a, others voice-<sid>. Narration may also be recorded on the camera
    # with its external mic (no phone): a camera file of a narration section is named voice-<sid>.mp4.
    from new_batch import rows as script_rows
    oncam = {(pid, sid) for _, pid in ps for sid, cam, *_ in script_rows(pid) if cam}
    cams = {(r["piece"], r["sid"]) for r in rows if r["camera"] and r["status"] == "ok" and (r["piece"], r["sid"]) in oncam}
    taken = {}
    for r in sorted(rows, key=lambda r: Path(r["src"]).stat().st_mtime):
        if r["status"] != "ok":
            continue
        key = (r["piece"], r["sid"])
        stem = f"cam-{r['sid']}" if key in cams else f"voice-{r['sid']}"
        if r["pickup"]:
            stem += "p"
        ext = ".mp4" if r["camera"] else Path(r["src"]).suffix.lower()
        dest = gs_env.ep_dir(r["piece"]) / "raw" / f"{stem}{ext}"
        if dest.name in taken.get(r["piece"], {}):
            old = taken[r["piece"]][dest.name]
            old.update(status="⚠", note=f"{dest.name} 有两个录音，默认用较晚的 {r['name']}；这个移到 unused/")
            old["dest"] = str(gs_env.ep_dir(r["piece"]) / "raw" / "unused" / old["name"])
        taken.setdefault(r["piece"], {})[dest.name] = r
        r["dest"] = str(dest)
    for r in rows:
        if r["camera"] and r["status"] == "ok":
            ph = next((q for q in rows if not q["camera"] and q["status"] == "ok" and
                       (q["piece"], q["sid"]) == (r["piece"], r["sid"])), None)
            if ph:
                try:
                    r["lag"], r["lag_score"] = lag(Path(r["src"]), Path(ph["src"]))
                except subprocess.CalledProcessError:
                    r["note"] += " 读不到声音轨"
            else:
                r["note"] += " 用相机外接麦的声音"
        r.setdefault("dest", "")

    out_dir.mkdir(parents=True, exist_ok=True)
    for r in rows:
        r["note"] = gs_i18n.loc(r["note"])
    (out_dir / "intake-plan.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# 录音整理 · {target}", "", f"> intake.py 自动生成，来源：`{inbox}`。⚠ 的那几行要导演确认；"
             "确认后改 intake-plan.json 的 dest / status，再跑 `intake.py " + target + " --apply`。", "",
             "| 文件 | 听到的编号 | 归到 | 涵盖段落 | 吻合 | 同步延迟 | 状态 |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lag_s = f"{r['lag']:+.3f} s" if "lag" in r else ""
        dest = Path(r["dest"]).name if r["dest"] else "—"
        lines.append(f"| {r['name']} | {r['slate'] or '—'}{' 补录' if r['pickup'] else ''} | {r.get('piece') or '—'} · {dest} | "
                     f"{', '.join(r.get('covers', [])) or '—'} | {r.get('score', 0):.0%} | {lag_s} | {r['status']} {r['note']} |")
    (out_dir / "intake.md").write_text(gs_i18n.loc("\n".join(lines) + "\n"), encoding="utf-8")
    print(f"-> {out_dir / 'intake.md'}  ({sum(r['status'] == '⚠' for r in rows)} row(s) to confirm)")
    return rows


def apply(target):
    _, _, out_dir = pieces(target)
    rows = json.loads((out_dir / "intake-plan.json").read_text(encoding="utf-8"))
    for r in rows:
        if r["status"] not in ("ok", "unused") or not r["dest"]:
            print(f"skip  {r['name']}  ({r['status']} {r['note']})")
            continue
        dest = Path(r["dest"]) if r["status"] == "ok" else Path(r["dest"]).parent / "unused" / r["name"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            print(f"exists, skip  {dest}")
            continue
        shutil.move(r["src"], dest)
        print(f"{r['name']}  ->  {dest}")
        # the no-prompt transcript made here is the one transcribe.py needs: hand it over, so Whisper never runs the
        # same pass twice on a file 
        js = Path(r["src"]).parent / ".intake" / f"{r['name']}.json"
        if r["status"] == "ok" and js.exists():
            d = json.loads(js.read_text(encoding="utf-8"))
            d["file"] = dest.name
            np_dir = dest.parent.parent / "work" / "noprompt"
            np_dir.mkdir(parents=True, exist_ok=True)
            (np_dir / f"{dest.name.split('.')[0]}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                                                    encoding="utf-8")


if __name__ == "__main__":
    args = sys.argv[1:]
    opt = {a: args[args.index(a) + 1] for a in ("--inbox", "--cache") if a in args}
    if "--apply" in args:
        apply(args[0])
    else:
        plan(args[0], opt.get("--inbox"), opt.get("--cache"), "--all" in args)
