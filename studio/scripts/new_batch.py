"""A batch: several pieces written together and recorded in one session (skill references/batch.md).

    python new_batch.py <bNN> <piece> <piece> ...
        long videos first (their teasers ride with them), then standalone shorts; any number of each
        -> <project>/batches/<bNN>/batch.md (pieces table, stops checklist, pickups) + batch.json + raw-inbox/
           (create the episodes / shorts first with new_episode.py / new_short.py)
    python new_batch.py <bNN | EPISODE> runsheet
        -> batches/<bNN>/runsheet.md  or  episodes/<EP>/work/runsheet.md: every section in setup order with the
           slate to say ("zero four, S zero one", "short three, X zero one"), first words, props, a tick box
"""
import datetime
import json
import re
import sys

import gs_env
from gs_text import CAM_MARK, MARK, SHOT_ID

L = gs_env.tr
ZH = gs_env.UI == "zh"
CN = "零一二三四五六七八九"
EN = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def digits(d):
    return "".join(CN[int(x)] for x in d) if ZH else " ".join(EN[int(x)] for x in d)


def slate(slot, sid):
    head = (L(f"short {EN[int(slot)]}", f"短片{CN[int(slot)]}") if len(slot) == 1 else digits(slot))
    if sid == "END":
        return f"{head}, " + L("end", "结尾")
    m = re.fullmatch(r"([SXC])(\d+)([a-z]?)", sid)
    return f"{head}, {m.group(1)} {digits(m.group(2))}{(' ' + m.group(3)) if m.group(3) else ''}"


def rows(ep):
    """[(sid, camera?, props, first words)] in script order, from script.md's teleprompter blocks."""
    text = (gs_env.ep_dir(ep) / "script.md").read_text(encoding="utf-8")
    out = []
    for block in re.findall(r"```[a-z]*\n(.*?)```", text, re.S):
        cur = None
        for raw in block.splitlines():
            m = re.match(rf"^({SHOT_ID})\s+(.*)$", raw.strip())
            line = m.group(2) if m else raw.strip()
            if m:
                cur = [m.group(1), False, "", ""]
                out.append(cur)
            if not cur:
                continue
            d = re.match(CAM_MARK, line)
            if d:
                cur[1], cur[2] = True, (d.group(1) or d.group(2) or "").strip()
                line = line[d.end():].strip()
            line = re.sub(MARK, "", line).strip()
            if line and not cur[3] and not line.startswith(("（", "(")):
                cur[3] = line[:18] if gs_env.CJK else " ".join(line.split()[:6])
    return [tuple(r) for r in out if not r[0].startswith("C")]


def runsheet(target):
    if re.fullmatch(r"b\d{2}", target):
        bj = json.loads((gs_env.BATCHES / target / "batch.json").read_text(encoding="utf-8"))
        ps, out = [(p["slot"], p["id"]) for p in bj["pieces"]], gs_env.BATCHES / target / "runsheet.md"
    else:
        ps, out = [(target[:2], target)], gs_env.ep_dir(target) / "work" / "runsheet.md"
    secs = {pid: rows(pid) for _, pid in ps}
    head = [L("| ☐ | Say this first | Section | First words | Props / framing |", "| ☐ | 先念编号 | 段落 | 开头几个字 | 道具 / 取景 |"), "|---|---|---|---|---|"]
    inbox = "`raw-inbox/`" if target.startswith("b") else "`raw/`"
    S = [L(f"# Run sheet · {target}", f"# 录音流程表 · {target}"), "",
         L("> Every take: say the slate → 3 seconds of silence → read the script. After a slip, stop 2 seconds and read the",
           "> 每一条：先念编号 → 安静 3 秒 → 念台本。念错就停 2 秒，整句重念（同一个文件里）。录完一条打勾；"),
         L(f"> whole line again (same file). Tick each take; what is not ticked is the pickup list. Put every file in {inbox}, no renaming.",
           f"> 没打勾的就是补录清单。录好的文件全部放进 {inbox}，不用改名。"), "",
         L("## 0 · Test clip", "## 0 · 测试片"), "",
         L("- ☐ Film a 10-second test clip `test.mp4` (normal light, what you will wear) and send it first: brightness and white balance are checked before the session",
           "- ☐ 拍 10 秒测试片 `test.mp4`（正常灯光、当天的衣服），先传给 Claude 看亮度和白平衡"), ""]
    n = 1
    for slot, pid in ps:                                    # camera, piece by piece
        cams = [r for r in secs[pid] if r[1]]
        if not cams:
            continue
        S += [f"## {n} · " + L("On camera", "出镜") + f" · {pid}", ""] + head
        for sid, _, props, first in cams:
            frame = L("camera upright 9:16", "相机竖拍 9:16") if len(slot) == 1 or sid.startswith("X") else L("landscape 16:9", "横拍 16:9")
            S.append(f"| ☐ | {slate(slot, sid)} | {sid} | {first} | {props or '—'} · {frame} |")
        S.append("")
        n += 1
    for slot, pid in ps:                                    # voice, piece by piece
        voice = [r for r in secs[pid] if not r[1]]
        if not voice:
            continue
        S += [f"## {n} · " + L("Narration", "旁白") + f" · {pid}", "",
              L("> One file may hold several sections: say each section's slate before reading it.",
                "> 可以一个文件连念好几段：每一段开头都念那一段的编号。"), ""] + head
        S += [f"| ☐ | {slate(slot, sid)} | {sid} | {first} | — |" for sid, _, _, first in voice] + [""]
        n += 1
    S += [L("## Pickups", "## 补录"), "", L("| Section | Why |", "| 编号 | 原因 |"), "|---|---|", "| | |", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(S), encoding="utf-8")
    print(f"-> {out}")


def create(bnn, ids):
    if len(ids) < 2:
        raise SystemExit(__doc__)
    for i in ids:
        if not gs_env.ep_dir(i).exists():
            raise SystemExit(f"{i} does not exist yet: create it with new_episode.py / new_short.py first")
    d = gs_env.BATCHES / bnn
    if d.exists():
        raise SystemExit(f"{d} already exists")
    (d / "raw-inbox").mkdir(parents=True)
    longs, shorts = [i for i in ids if not gs_env.is_short(i)], [i for i in ids if gs_env.is_short(i)]
    if len(shorts) > 9:
        raise SystemExit("at most 9 standalone shorts in one batch (the spoken slate is one digit)")
    pieces = [{"slot": i[:2], "id": i, "role": L("long", "正片") + f" {chr(65 + k)}"} for k, i in enumerate(longs)]
    pieces += [{"slot": str(k + 1), "id": s, "role": L(f"short {k + 1}", f"短片{CN[k + 1]}")} for k, s in enumerate(shorts)]
    (d / "batch.json").write_text(json.dumps({"batch": bnn, "pieces": pieces}, ensure_ascii=False, indent=1), encoding="utf-8")
    today = datetime.date.today().isoformat()
    stages = L("Logic | Script | Recorded | Intake | Voice cut | 480p with music | Package", "逻辑稿 | 台本 | 已录 | 整理 | 人声初剪 | 480p（含配乐） | 上传包")
    box = " | ".join("☐" for _ in stages.split("|"))
    table = []
    for p in pieces:
        table.append(f"| {p['role']} | {p['id']} | | | | {box} |")
        if not gs_env.is_short(p["id"]):
            table.append(f"| {p['role']} · " + L("teaser", "预告") + f" | {p['id']} X | | | | {box} |")
    md = "\n".join([
        L(f"# Batch {bnn}", f"# 批次 {bnn}"), "",
        L(f"> Started: {today}. Rules: the skill's `references/batch.md`. Dates are a record of the plan; the director decides when to record and when to post.",
          f"> 开始：{today}。规则：技能 `references/batch.md`。日期只是计划记录，导演决定什么时候录、什么时候发。"),
        L("> Every new conversation reads this file first, then the notes.md of the piece in hand. A tick = approved by the director.",
          "> 每个 Claude 对话先读这份，再读正在做的那一支的 notes.md。打勾 = 导演确认过。"), "",
        L("## Pieces", "## 这一批的影片"), "",
        L("| Slot | Id | Planned release | Field · house style | Music | ", "| 位置 | 编号 | 计划发布 | 领域 · 固定风格 | 配乐 | ") + stages + " |",
        "|---|---|---|---|---|" + "---|" * len(stages.split("|")), *table, "",
        L("## Before recording (tick after each approval)", "## 录音之前（每一站导演确认后打勾）"),
        L("- [ ] A · Plan: topics, planned dates, fields, duplicates checked", "- [ ] A · 选题：题目、计划日期、领域轮换、去重"),
        L("- [ ] B · Logic drafts (first long video first, its notes applied to the rest)", "- [ ] B · 逻辑稿（先做第一支正片，意见套用到其余）"),
        L("- [ ] C · Scripts + music shortlist (first long video first)", "- [ ] C · 台本 + 配乐候选单（先做第一支正片）"),
        L("- [ ] D · Recording kit: `runsheet.md`, props", "- [ ] D · 录音包：录音流程表 `runsheet.md`、道具"), "",
        L("## After recording", "## 录音之后"),
        L("- [ ] Intake + recording-diff report (`intake.md`; pickups below)", "- [ ] 整理录音 + 录音对照报告（`intake.md`；补录清单在下面）"),
        L("- [ ] The whole batch: voice cut ☐ · 480p with music ☐ · package ☐ · scheduled by the director ☐", "- [ ] 整批一起：人声初剪 ☐ · 480p（含配乐）☐ · 上传包 ☐ · 导演排程 ☐"), "",
        L("## Pickups", "## 补录清单"), L("| Section | Why | Done |", "| 编号 | 原因 | 已补 |"), "|---|---|---|", "| | | |", "",
        L("## Log", "## 记录"), f"- {today} " + L("batch opened: ", "开这一批：") + ", ".join(ids) + ".", ""])
    (d / "batch.md").write_text(md, encoding="utf-8")
    for i in ids:                       # one checklist per piece: inside a batch, progress lives only in batch.md
        notes = gs_env.ep_dir(i) / "notes.md"
        if notes.exists():
            text = notes.read_text(encoding="utf-8")
            text = re.sub(r"## (?:To do|待办)[^\n]*\n(?:- \[[ x]\][^\n]*\n)*",
                          L(f"## Progress\nSee `batches/{bnn}/batch.md` (inside a batch that is the only checklist).\n",
                            f"## 进度\n进度看 `batches/{bnn}/batch.md`（批次里只有那一张清单）。\n"), text)
            notes.write_text(text, encoding="utf-8")
    print(f"created {d}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    if len(a) == 2 and a[1] == "runsheet":
        runsheet(a[0])
    elif a and re.fullmatch(r"b\d{2}", a[0]):
        create(a[0], a[1:])
    else:
        raise SystemExit(__doc__)
