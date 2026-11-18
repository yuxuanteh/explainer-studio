"""Scaffold a standalone short (not tied to a long video).

    python new_short.py <NNN|next> <english-slug> "<title>" "<field>" [kind] [--batch]
    e.g. python new_short.py next city-quake-2026 "The quake last night" "Seismology" news   -> ss001-... (outside a batch)
         python new_short.py next hollow-hill "Why is that hill hollow?" "Geology" --batch   -> s001-...  (inside a batch)
Numbers: ss<NNN> = shorts made outside a batch, s<NNN> = batch shorts, so the two never collide.
kind: explainer (default) or news (a fast lane for something that just happened; skill references/shorts.md).

Creates
  <project>/shorts/<id>/   raw/ work/ preview/ publish/{short,social}, script.md, notes.md, work/references.md
  <studio>/shorts/<id>/    edl.py (template);  animation modules go in <studio>/web/ep/<id>/
The teaser short of an episode stays in that episode (X shots in its script), not here.
"""
import datetime
import re
import sys

import gs_env
from new_episode import L, checklist, fill, published, references, template


def next_number(prefix):
    used = [int(m.group(1)) for d in (gs_env.SHORTS, gs_env.STUDIO / "shorts") if d.exists()
            for p in d.iterdir() if (m := re.match(rf"{prefix}(\d{{3}})-", p.name))]
    return f"{max(used, default=0) + 1:03d}"


def main():
    args = [a for a in sys.argv[1:] if a != "--batch"]
    prefix = "s" if "--batch" in sys.argv else "ss"
    if len(args) < 4:
        raise SystemExit(__doc__)
    no, slug, title, field = args[:4]
    kind = args[4] if len(args) > 4 else "explainer"
    no = next_number(prefix) if no == "next" else no
    if not re.fullmatch(r"\d{3}", no) or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        raise SystemExit("short number must be three digits (or 'next') and the slug lower-case english words joined by '-'")
    ep = f"{prefix}{no}-{slug}"
    g, c = gs_env.ep_dir(ep), gs_env.code_dir(ep)
    if g.exists() or c.exists():
        raise SystemExit(f"{ep} already exists")
    kw = dict(EPISODE=ep, TITLE=title, FIELD=field, KIND=kind)
    for d in ["raw", "work", "preview", "publish/short", "publish/social"]:
        (g / d).mkdir(parents=True)
    c.mkdir(parents=True)
    (g / "script.md").write_text(fill(template("short", "script.md"), **kw), encoding="utf-8")
    today = datetime.date.today().isoformat()
    (g / "notes.md").write_text(f"# notes · {ep}\n\n" + L("## Decisions", "## 决定记录") + f"\n- {today} " +
                                L(f"new short: {title} ({kind} · {field}).", f"开新短片：{title}（{kind} · {field}）。") + "\n\n" + checklist(short=True),
                                encoding="utf-8")
    (g / "work" / "references.md").write_text(references(ep, today), encoding="utf-8")
    (c / "edl.py").write_text(fill(template("short", "edl.py"), **kw), encoding="utf-8")
    import gs_web
    w = gs_web.scaffold(ep, kw, short=True)
    print(f"created {g}\ncreated {c}\ncreated {w}")
    published(ep)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
