"""Scaffold a new episode.

    python new_episode.py <NN> <english-slug> "<title>" "<series>"
    e.g. python new_episode.py 01 granite "Why is granite everywhere?" "Rocks"

Creates
  <project>/episodes/<NN>-<slug>/   raw/ work/ preview/ publish/{thumbnails,social,short}
      script.md (template), notes.md (the checklist), work/references.md
  <studio>/episodes/<NN>-<slug>/    edl.py (template);  animation modules go in <studio>/web/ep/<id>/
and prints the already-published videos and the pieces in production, so the topic can be checked for duplicates.
"""
import datetime
import json
import re
import sys

import gs_env

L = gs_env.tr
TEMPLATES = gs_env.STUDIO / "templates" / "episode"
_vj = gs_env.cfg("paths", "videos_json", "")
VIDEOS_JSON = gs_env._path(_vj, gs_env.PROJECT) if _vj else None


def fill(text, **kw):
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def template(kind, name):
    """A template in the studio, or the channel's own copy in <project>/templates/<kind>/ (e.g. translated)."""
    own = gs_env.PROJECT / "templates" / kind / name
    return (own if own.exists() else gs_env.STUDIO / "templates" / kind / name).read_text(encoding="utf-8")


def checklist(short=False):
    steps = [L("1 Topic: title draft, series, field, number → approved", "1 开新集：题目、系列、领域、编号 → 导演确认")] if not short else []
    steps += [
        L("2a Logic draft (work/logic-draft.md) → approved", "2a 逻辑稿（work/logic-draft.md）→ 导演确认"),
        L("2b Script + references.md + music shortlist → approved, tracks picked", "2b 台本 + references.md + 配乐候选单 → 导演确认、选好配乐"),
        L("3 Recording kit (run sheet, props, guide); camera test → recorded", "3 录音包（录音流程表、道具、指引）；测试片 → 导演录音"),
        L("4 Intake → automatic cut → voice cut on the review page → approved (timing locked)", "4 整理录音 → 自动初剪 → 人声初剪（审片页）→ 导演确认（时间锁定）"),
        L("5 Animation with music, 480p → approved", "5 动画 + 配乐 480p → 导演确认"),
        L("6 Final master + translated subtitles", "6 成片 + 翻译字幕"),
        L("7 Upload & sharing package (publish.md, thumbnails) → approved → uploaded by hand", "7 上传与分享包（publish.md、缩略图）→ 导演确认 → 手动上传"),
    ]
    head = L("## To do (the skill's steps; tick only after approval, never start a step while the one before is unticked)",
             "## 待办（技能的步骤；导演确认后才打勾，前一站没打勾不开始下一站）")
    return head + "\n" + "\n".join(f"- [ ] {s}" for s in steps) + "\n"


def references(ep, today):
    return (L(f"# References · {ep}\n\n> Checked on: {today}\n\n## Claim by claim\n| Claim in the video | Verdict | Source |\n|---|---|---|\n\n"
              "## Sources\n\n## For the description (copy and paste)\n```\nReferences\n```\n",
              f"# 参考资料 · {ep}\n\n> 核查日期：{today}\n\n## 逐条核查\n| 片中说法 | 结论 | 来源 |\n|---|---|---|\n\n"
              "## 来源\n\n## 简介版（复制贴上）\n```\n参考资料\n```\n"))


def published(skip):
    if VIDEOS_JSON and VIDEOS_JSON.exists():
        print("\nalready published (check for duplicate topics):")
        for v in json.loads(VIDEOS_JSON.read_text(encoding="utf-8")).get("videos", []):
            print(f"  {v.get('date', '')}  [{v.get('series', '')}]  {v.get('format', 'long'):5s}  {v.get('title', '')}")
    for d in (gs_env.EPISODES, gs_env.SHORTS):
        for p in sorted(d.iterdir()) if d.exists() else []:
            if p.is_dir() and p.name != skip and re.match(r"(s{1,2}\d{3}|\d{2})-", p.name):
                print(f"  (in production) {p.name}")


def main():
    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    no, slug, title, series = sys.argv[1:5]
    if not re.fullmatch(r"\d{2}", no) or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        raise SystemExit("episode number must be two digits and the slug lower-case english words joined by '-'")
    ep = f"{no}-{slug}"
    g, c = gs_env.EPISODES / ep, gs_env.STUDIO / "episodes" / ep
    if g.exists() or c.exists():
        raise SystemExit(f"{ep} already exists")
    kw = dict(EPISODE=ep, EPISODE_NO=no, TITLE=title, SERIES=series)
    for d in ["raw", "work", "preview", "publish/thumbnails", "publish/social", "publish/short"]:
        (g / d).mkdir(parents=True)
    c.mkdir(parents=True)
    (g / "script.md").write_text(fill(template("episode", "script.md"), **kw), encoding="utf-8")
    today = datetime.date.today().isoformat()
    (g / "notes.md").write_text(f"# notes · {ep}\n\n" + L("## Decisions", "## 决定记录") + f"\n- {today} " +
                                L(f"new episode: {title} (series: {series}).", f"开新集：{title}（系列：{series}）。") + "\n\n" + checklist(),
                                encoding="utf-8")
    (g / "work" / "references.md").write_text(references(ep, today), encoding="utf-8")
    (c / "edl.py").write_text(fill(template("episode", "edl.py"), **kw), encoding="utf-8")
    import gs_web
    w = gs_web.scaffold(ep, kw)
    print(f"created {g}\ncreated {c}\ncreated {w}")
    published(ep)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
