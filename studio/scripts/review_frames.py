"""Self-review contact sheets before sending previews to the director.

    python review_frames.py <EPISODE> [preview|final] [shot ids...]

Grabs 3 frames per shot (35 % / 65 % / 95 % of its duration) from the rendered shots, for the long video AND the
short (standalone shorts and the teaser's X shots used to get no sheet), and for the intro, chapter and
end cards too (they follow the house style now, so they need looking at). Camera shots are composited the way the
build does it (camera trimmed first, then the CG overlaid). Landscape frames carry a red line at y = 880 (subtitle
band: no text below it); portrait frames at y = 1360. Pages go to render/<EP>/review/page<N>.png (long video) and
short-page<N>.png (9:16).

Check every page for: text in the subtitle band, tofu boxes (missing glyphs), labels not next to their subject or
covering the presenter, chips that repeat the narration, things appearing before / after their word, CG not centred
in the free wall zone, blinks at cuts (compare the last frame of one shot with the first of the next).
"""
import subprocess
import sys

from PIL import Image, ImageDraw

import gs_env
from gs_episode import QUALITY, VQUALITY, anim_src, cg_overlay, load, short_edl, timeline


def frames_of(E, s, mode, vertical, out, W, H):
    folder = ""
    res = []
    for f in (0.35, 0.65, 0.95):
        t = s["dur"] * f
        png = out / f"{s['id']}_{int(f * 100)}.png"
        if s["kind"] == "cam":
            cg_in, cg_chain, cg_alpha = cg_overlay(E, s["id"], folder, mode, W, H)
            if not all(__import__("pathlib").Path(str(x)).exists() for x in cg_in[1::2]):
                continue
            pre = E.CAM_FRAME.get(s["src"], "")
            subprocess.run([gs_env.FFMPEG, "-v", "error", "-nostdin", "-y", "-ss", f"{s['in']:.2f}", "-t", f"{s['dur']:.2f}",
                            "-i", str(E.SRC[s["src"]]), *map(str, cg_in), "-filter_complex",
                            f"[0:v]{pre + ',' if pre else ''}{E.CAM_GRADE},scale={W}:{H}:force_original_aspect_ratio=increase,"
                            f"crop={W}:{H},fps=30[c];{cg_chain};[c][cg]overlay=0:0:shortest=0{cg_alpha}", "-ss", f"{t:.2f}",
                            "-frames:v", "1", str(png)], check=True, timeout=300)
        elif s["kind"] in ("anim", "chapter", "card", "intro"):
            src = anim_src(E, s["id"], folder, mode)
            if not src.exists():
                continue
            subprocess.run([gs_env.FFMPEG, "-v", "error", "-nostdin", "-y", "-ss", f"{min(t, max(s['dur'] - 0.1, 0)):.2f}", "-i",
                            str(src), "-vf", f"scale={W}:{H}", "-frames:v", "1", str(png)], check=True, timeout=300)
        else:
            continue
        res.append(png)
    return res


def sheets(rows, out, prefix, W, H, band_y):
    for k in range(0, len(rows), 5):
        chunk = rows[k:k + 5]
        sheet = Image.new("RGB", (W * 3, H * len(chunk)), "black")
        for r, (sid, frames) in enumerate(chunk):
            for c, f in enumerate(frames):
                im = Image.open(f).convert("RGB")
                d = ImageDraw.Draw(im)
                d.rectangle([0, 0, 64, 22], fill="black")
                d.text((5, 5), sid, fill="yellow")
                d.line([(0, band_y), (W, band_y)], fill="red")
                sheet.paste(im, (c * W, r * H))
        p = out / f"{prefix}page{k // 5}.png"
        sheet.save(p)
        print(p)


def main():
    import gs_episode
    if gs_episode.NO_ANIM:
        return print("no animation engine: no review sheets")
    E = load(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in QUALITY else "preview"
    only = set(sys.argv[3:]) - {"preview", "final"}
    out = E.RENDER / "review"
    out.mkdir(parents=True, exist_ok=True)
    web = True
    for tl, short in ((timeline(E) if E.SHOTS else [], False), (timeline(short_edl(E)) if E.SHORT_SHOTS else [], True)):
        vertical = bool(short and E.SHORT_VERTICAL)
        W, H = (270, 480) if vertical else (854, 480)
        rows = []
        for s in tl:
            if (only and s["id"] not in only) or (s["kind"] in ("intro", "chapter", "card") and not web):
                continue
            fr = frames_of(E, s, mode, vertical, out, W, H)
            if fr:
                rows.append((s["id"], fr))
        if rows:
            sheets(rows, out, "short-" if short else "", W, H, int(H * (1360 / 1920 if vertical else 880 / 1080)))


if __name__ == "__main__":
    main()
