"""Download a Wikimedia Commons photo for a piece, with its credit line. (upload.wikimedia.org sometimes
answers 429 to every scripted download for hours; the way round is a real browser.)

    python gs_photo.py <EP> "<Commons file page URL or File:Name.jpg>" [save-as.jpg] [--width 1920]

Saves to web/ep/<EP>/assets/<save-as> and prints the row for the photo table in <episode>/work/references.md
(file | Commons name | author | licence | page). Order: the Commons API for the picture's address, author and licence;
a plain download with waits when the site says "too many requests"; then the studio's own headless browser
(web/fetch.mjs, Playwright) if that still fails. Nothing personal is sent: a generic client name only.
"""
import html
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import gs_env

UA = "ExplainerStudio/2.0 (educational video production; photo fetch)"
API = "https://commons.wikimedia.org/w/api.php"


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or k == tries - 1:
                raise
            wait = min(int(e.headers.get("Retry-After") or 0) or 5 * (k + 1), 30)
            print(f"   {e.code}: waiting {wait} s")
            time.sleep(wait)


def info(title, width):
    q = urllib.parse.urlencode({"action": "query", "format": "json", "titles": title, "prop": "imageinfo",
                                "iiprop": "url|extmetadata|size", "iiurlwidth": width})
    page = next(iter(json.loads(get(f"{API}?{q}"))["query"]["pages"].values()))
    if "imageinfo" not in page:
        raise SystemExit(f"not found on Commons: {title}")
    ii = page["imageinfo"][0]
    meta = ii.get("extmetadata", {})
    clean = lambda k: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", meta.get(k, {}).get("value", "")))).strip()  # noqa: E731
    return dict(url=ii.get("thumburl") or ii["url"], page=ii["descriptionurl"], author=clean("Artist") or "?",
                licence=clean("LicenseShortName") or "?", w=ii.get("thumbwidth") or ii["width"])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        raise SystemExit(__doc__)
    width = int(sys.argv[sys.argv.index("--width") + 1]) if "--width" in sys.argv else 1920
    args = [a for a in args if a != str(width)] if "--width" in sys.argv else args
    ep, ref = args[0], args[1]
    title = urllib.parse.unquote(ref.rsplit("/", 1)[-1]).replace("_", " ")
    title = title if title.lower().startswith("file:") else "File:" + title
    d = info(title, width)
    name = args[2] if len(args) > 2 else re.sub(r"[^\w.-]+", "-", title[5:]).strip("-").lower()
    dest = gs_env.STUDIO / "web" / "ep" / ep / "assets" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    how = "direct"
    try:
        dest.write_bytes(get(d["url"]))
    except Exception as e:                                   # refused: go through a real browser
        print(f"   direct download refused ({e}); trying the browser")
        r = subprocess.run(["node", "fetch.mjs", d["page"], d["url"], str(dest)], cwd=gs_env.STUDIO / "web",
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            raise SystemExit(f"FAILED {name}: {r.stdout.strip() or r.stderr.strip()[-300:]}")
        how = "browser"
    if dest.stat().st_size < 5000 or dest.read_bytes()[:1] == b"<":
        dest.unlink()
        raise SystemExit(f"FAILED {name}: what came back is not a picture")
    print(f"saved {dest}  ({dest.stat().st_size / 1e6:.1f} MB, {d['w']} px wide, {how})")
    print(f"| {name} | {title[5:]} | {d['author']} | {d['licence']} | {d['page']} |")


if __name__ == "__main__":
    main()
