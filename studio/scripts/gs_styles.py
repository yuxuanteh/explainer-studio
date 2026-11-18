"""House styles: list them, and render the same sample shot under each one so they can be compared.

    python gs_styles.py list                         the styles in web/kit/themes.json, plus CHANNEL (your [palette])
    python gs_styles.py preview [ids...] [--vertical] [--at 3.5]
        -> <project>/brand/styles/compare.png (each style as one picture, side by side) + one PNG per style
           (no ids: every style, with CHANNEL = the look you have now, for comparison)
    python gs_styles.py use <id>                     make it the channel's house style ([style] house in studio.toml)

A style is one entry of web/kit/themes.json: colours, the ground (grid / dust / paper / flat), the name-tag plate and
the title font. Cards, the intro, labels and the burned subtitles all follow it. BLUEPRINT, CHALK and POSTER are
examples; add an entry for your own (copy one, change it, preview, repeat).
"""
import json
import sys
import time

from PIL import Image, ImageDraw, ImageFont

import gs_env
import gs_web

THEMES = gs_env.WEB / "kit" / "themes.json"


def themes():
    d = json.loads(THEMES.read_text(encoding="utf-8"))
    return {k: v for k, v in d.items() if isinstance(v, dict)}


def preview(ids, vertical=False, at="3.5"):
    T = themes()
    ids = ids or ["CHANNEL", *T]
    for i in ids:
        if i != "CHANNEL" and i not in T:
            raise SystemExit(f"no style {i} in {THEMES} (have: {', '.join(T)})")
    gs_web.brand()
    out = gs_env.BRAND / "styles"
    out.mkdir(parents=True, exist_ok=True)
    (gs_env.WEB / "ep" / "_styles").mkdir(parents=True, exist_ok=True)
    w, h = (1080, 1920) if vertical else (1920, 1080)
    shots = []
    for i in ids:
        spec = {"ep": "_styles", "vertical": vertical, "review": False, "bust": int(time.time()), "cardTheme": i,
                "channel": gs_web.channel_spec(),
                "shots": [{"id": "DEMO", "kind": "anim", "module": "../../kit/demo.js", "t0": 0, "dur": 6.0, "beats": {}, "cues": []}]}
        page = gs_env.WEB / f"_styles_{i}.html"
        page.write_text('<!doctype html><html><head><meta charset="utf-8"><title>style ' + i + '</title>\n'
                        '<link rel="stylesheet" href="kit/fonts.css"></head><body><canvas id="c"></canvas>\n'
                        f"<script>window.GS_SPEC = {json.dumps(spec, ensure_ascii=False)};</script>\n"
                        '<script type="module" src="kit/player.js"></script></body></html>\n', encoding="utf-8")
        png = out / f"{i}{'-9x16' if vertical else ''}.png"
        gs_web.node("render.mjs", page, "--size", f"{w}x{h}", "--poster", at, "--out", png)
        page.unlink(missing_ok=True)
        shots.append((i, png))
        print("rendered", png)
    cw = 540 if vertical else 960
    ch = cw * h // w
    cols = min(len(shots), 4 if vertical else 2)
    rows = -(-len(shots) // cols)
    sheet = Image.new("RGB", (cols * cw, rows * (ch + 56)), "#111111")
    d = ImageDraw.Draw(sheet)
    fonts = gs_env.subtitle_fonts()
    try:
        font = ImageFont.truetype(str(gs_env.FONTS / fonts[0]), 30)
    except OSError:
        font = ImageFont.load_default()
    for k, (i, png) in enumerate(shots):
        x, y = (k % cols) * cw, (k // cols) * (ch + 56)
        sheet.paste(Image.open(png).convert("RGB").resize((cw, ch), Image.LANCZOS), (x, y + 56))
        d.text((x + 16, y + 10), i + ("  (your colours now)" if i == "CHANNEL" else ""), fill="#FFFFFF", font=font)
    dst = out / f"compare{'-9x16' if vertical else ''}.png"
    sheet.save(dst)
    print(dst)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a or a[0] == "list":
        print("CHANNEL: your own colours from [palette] in studio.toml (dark plate, accent bar)")
        for k, v in themes().items():
            print(f"{k}: {v.get('label', '')}")
        print(f"\nhouse style now: {gs_env.cfg('style', 'house', '') or 'CHANNEL'}")
    elif a[0] == "preview":
        at = next((sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == "--at"), "3.5")
        preview([x for x in a[1:] if x != at], vertical="--vertical" in sys.argv, at=at)
    elif a[0] == "use" and len(a) == 2:
        if a[1] != "CHANNEL" and a[1] not in themes():
            raise SystemExit(f"no style {a[1]}")
        import setup_studio
        setup_studio.set_value("style", "house", json.dumps(a[1]))
        print(f"house style: {a[1]}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
