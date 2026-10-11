"""Self-review contact sheets before sending previews to the director.

    python review_frames.py <EPISODE> [preview|final] [shot ids...]

Grabs 3 frames per shot (35 % / 65 % / 95 % of its duration) from the rendered shots; camera shots are
composited exactly the way `gs_episode.py build` does it (camera trimmed first, then the transparent CG overlaid -
seeking inside the qtrle .mov directly shows an empty overlay). A red line marks y = 880 (subtitle band: no text
below it; graphics may continue). Pages of 5 shots go to the render folder: render/<EP>/review/page<N>.png.

Check every page for: text in the subtitle band, tofu boxes (missing glyphs), labels not next to their subject or
covering the presenter, chips that repeat the narration, things appearing before / after their word, CG not centred
in the free wall zone, blinks at cuts (compare the last frame of one shot with the first of the next).
"""
import subprocess
import sys

from PIL import Image, ImageDraw

import gs_env
from gs_episode import QUALITY, load, timeline


def main():
    E = load(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in QUALITY else "preview"
    only = set(sys.argv[3:]) - {"preview", "final"}
    folder = QUALITY[mode][1] if mode == "preview" else "1080p30"
    out = E.RENDER / "review"
    out.mkdir(parents=True, exist_ok=True)
    R = E.RENDER / "videos"
    W, H = 854, 480
    rows = []
    for s in timeline(E):
        if s["kind"] in ("intro", "chapter", "card") or (only and s["id"] not in only):
            continue
        frames = []
        for f in (0.35, 0.65, 0.95):
            t = s["dur"] * f
            png = out / f"{s['id']}_{int(f * 100)}.png"
            if s["kind"] == "cam":
                cg = R / "cam_cg" / folder / f"Cam{s['id']}.mov"
                subprocess.run([gs_env.FFMPEG, "-v", "error", "-y", "-ss", f"{s['in']:.2f}", "-t", f"{s['dur']:.2f}",
                                "-i", str(E.SRC[s["src"]]), "-i", str(cg), "-filter_complex",
                                f"[0:v]{E.CAM_GRADE},scale={W}:{H},fps=15[c];[1:v]scale={W}:{H}[g];"
                                "[c][g]overlay=0:0:shortest=0", "-ss", f"{t:.2f}", "-frames:v", "1", str(png)],
                               check=True)
            else:
                subprocess.run([gs_env.FFMPEG, "-v", "error", "-y", "-ss", f"{min(t, s['dur'] - 0.1):.2f}", "-i",
                                str(R / "shots" / folder / f"{s['id']}.mp4"), "-vf", f"scale={W}:{H}", "-frames:v", "1",
                                str(png)], check=True)
            frames.append(png)
        rows.append((s["id"], frames))
    y880 = int(H * 880 / 1080)
    for k in range(0, len(rows), 5):
        chunk = rows[k:k + 5]
        sheet = Image.new("RGB", (W * 3, H * len(chunk)), "black")
        for r, (sid, frames) in enumerate(chunk):
            for c, f in enumerate(frames):
                im = Image.open(f).convert("RGB")
                d = ImageDraw.Draw(im)
                d.rectangle([0, 0, 64, 22], fill="black")
                d.text((5, 5), sid, fill="yellow")
                d.line([(0, y880), (W, y880)], fill="red")
                sheet.paste(im, (c * W, r * H))
        p = out / f"page{k // 5}.png"
        sheet.save(p)
        print(p)


if __name__ == "__main__":
    main()
