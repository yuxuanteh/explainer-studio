"""Scaffold a new episode.

    python new_episode.py <NN> <english-slug> "<working title>" "<series>"
    e.g. python new_episode.py 01 granite "Why is granite everywhere?" "Rocks"

Creates
  <project>/episodes/<NN>-<slug>/  raw/ work/ preview/ publish/{thumbnails,social,short}
      script.md (template), notes.md, work/references.md
  <studio>/episodes/<NN>-<slug>/   edl.py make_edl.py shots.py cam_cg.py thumbs.py (templates)
and prints the already-published videos so the topic can be checked for duplicates.
"""
import datetime
import json
import re
import sys
from pathlib import Path

import gs_env

TEMPLATES = gs_env.STUDIO / "templates" / "episode"
_vj = gs_env.cfg("paths", "videos_json", "")
VIDEOS_JSON = (Path(_vj) if Path(_vj).is_absolute() else gs_env.PROJECT / _vj) if _vj else None


def fill(text, **kw):
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", v)
    return text


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
    (g / "script.md").write_text(fill((TEMPLATES / "script.md").read_text(encoding="utf-8"), **kw), encoding="utf-8")
    today = datetime.date.today().isoformat()
    (g / "notes.md").write_text(
        f"# notes · {ep}\n\n## Decisions\n- {today} new episode: {title} (series: {series}).\n\n"
        "## To do\n- [ ] script + fact check (work/references.md) -> director approves\n"
        "- [ ] episode palette -> director picks\n- [ ] director records voice / camera -> raw/\n"
        "- [ ] Whisper alignment + cut list + cut check\n- [ ] 480p animation previews -> director approves\n"
        "- [ ] 480p rough cut -> director approves\n- [ ] 1080p master\n- [ ] upload & sharing package\n",
        encoding="utf-8")
    (g / "work" / "references.md").write_text(
        f"# References · {ep}\n\n> Checked on: {today}\n\n## Claim by claim\n| Claim in the video | Verdict | Source |\n"
        "|---|---|---|\n\n## Sources\n\n## Description version (copy-paste)\n```\nReferences\n```\n", encoding="utf-8")
    for f in ["edl.py", "make_edl.py", "shots.py", "cam_cg.py", "thumbs.py"]:
        (c / f).write_text(fill((TEMPLATES / f).read_text(encoding="utf-8"), **kw), encoding="utf-8")
    print(f"created {g}\ncreated {c}")
    if VIDEOS_JSON and VIDEOS_JSON.exists():
        print("\nalready published (check for duplicate topics):")
        for v in json.loads(VIDEOS_JSON.read_text(encoding="utf-8"))["videos"]:
            print(f"  {v['date']}  [{v['series']}]  {v['title']}")
    for p in sorted(gs_env.EPISODES.iterdir()):
        if p.is_dir() and p.name != ep:
            print(f"  (in production) {p.name}")


if __name__ == "__main__":
    main()
