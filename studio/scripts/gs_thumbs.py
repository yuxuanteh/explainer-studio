"""Render an episode's thumbs.py and export YouTube thumbnails (4 layers each) + IG / FB covers to publish/.

    python gs_thumbs.py <EPISODE>                          # renders Thumb<V>{Full,Bg,Text,El} + IgCover, exports
    python gs_thumbs.py <EPISODE> photo camS2 7.0 [990]    # presenter photo from a camera source at 7.0 s
"""
import re
import subprocess
import sys

from PIL import Image

import gs_env
from gs_episode import load

LAYERS = [("Full", "", False), ("Bg", "-background-notext", False), ("Text", "-text-layer", True),
          ("El", "-elements", True)]


def presenter_photo(E, source, t, center_x=990):
    """Grab a camera frame at `t` s, brighten it, and save the two fades used by thumbs.py:
    thumbnails/photo-presenter.png (760x720, fades to the left) and social/photo-presenter-portrait.png (1080x900)."""
    import numpy as np
    full = E.RENDER / "photo-full.png"
    full.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([gs_env.FFMPEG, "-v", "error", "-y", "-ss", str(t), "-i", str(E.SRC[source]), "-vf",
                    E.CAM_GRADE.replace("0.04", "0.05").replace("1.15", "1.2"), "-frames:v", "1", "-update", "1",
                    str(full)], check=True)
    im = Image.open(full).convert("RGB")
    h = gs_env.CFG.get("palette", {}).get("bg_deep", "#131008").lstrip("#")
    dark = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)   # fade colour = channel background
    x0 = int(np.clip(center_x - 570, 0, im.width - 1140))
    a = np.array(im.crop((x0, 0, x0 + 1140, 1080)).resize((760, 720), Image.LANCZOS)).astype(np.float32)
    f = np.clip(np.arange(760) / (760 * 0.42), 0, 1)[None, :, None] ** 1.4
    Image.fromarray((a * f + dark * (1 - f)).astype(np.uint8)).save(E.EP_DIR / "publish" / "thumbnails" / "photo-presenter.png")
    x1 = int(np.clip(center_x - 648, 0, im.width - 1296))
    b = np.array(im.crop((x1, 0, x1 + 1296, 1080)).resize((1080, 900), Image.LANCZOS)).astype(np.float32)
    g = np.clip((900 - np.arange(900)) / (900 * 0.35), 0, 1)[:, None, None] ** 1.3
    Image.fromarray((b * g + dark * (1 - g)).astype(np.uint8)).save(E.EP_DIR / "publish" / "social" / "photo-presenter-portrait.png")
    print("saved presenter photos from", source, t)


def main():
    E = load(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == "photo":      # gs_thumbs.py <EP> photo <source key> <seconds> [center_x]
        for d in ("thumbnails", "social"):
            (E.EP_DIR / "publish" / d).mkdir(parents=True, exist_ok=True)
        presenter_photo(E, sys.argv[3], float(sys.argv[4]), *(int(x) for x in sys.argv[5:6]))
        return
    src = (E.CODE_DIR / "thumbs.py").read_text(encoding="utf-8")
    versions = sorted(set(re.findall(r"^class Thumb([A-Z])\(", src, re.M)))
    media = E.RENDER / "thumbs"
    img = media / "images" / "thumbs"
    pub = E.EP_DIR / "publish"
    (pub / "thumbnails").mkdir(parents=True, exist_ok=True)
    (pub / "social").mkdir(parents=True, exist_ok=True)

    def render(scene, res, transparent=False):
        args = [sys.executable, "-m", "manim", "-s", "-r", res, "--media_dir", str(media)]
        args += (["-t"] if transparent else []) + ["thumbs.py", scene]
        subprocess.run(args, cwd=E.CODE_DIR, check=True, capture_output=True)
        return next(img.glob(f"{scene}_ManimCE_*.png"))

    for v in versions:
        for layer, suffix, transparent in LAYERS:
            im = Image.open(render(f"Thumb{v}{layer}", "1280,720", transparent))
            (im if transparent else im.convert("RGB")).save(pub / "thumbnails" / f"thumb-{v}{suffix}.png", optimize=True)
    if "class IgCover(" in src:
        Image.open(render("IgCover", "1080,1350")).convert("RGB").save(pub / "social" / "ig-cover-1080x1350.png",
                                                                        optimize=True)
    if "class ShortCover(" in src:   # Shorts / Reels cover (Reels: upload as cover; Shorts: pick a frame in the app)
        (pub / "short").mkdir(parents=True, exist_ok=True)
        Image.open(render("ShortCover", "1080,1920")).convert("RGB").save(pub / "short" / "short-cover-1080x1920.png",
                                                                           optimize=True)
    if versions:   # Facebook share image cropped from thumbnail A
        a = Image.open(pub / "thumbnails" / f"thumb-{versions[0]}.png").resize((1200, 675), Image.LANCZOS)
        a.crop((0, 22, 1200, 652)).save(pub / "social" / "fb-share-1200x630.png", optimize=True)
    for p in sorted(list((pub / "thumbnails").glob("*.png")) + list((pub / "social").glob("*.png")) + list((pub / "short").glob("*.png"))):
        size_mb = p.stat().st_size / 1e6
        warn = "  !! YouTube limit is 2 MB" if p.name.startswith("thumb-") and size_mb > 2 else ""
        print(f"{p.relative_to(pub)!s:46s} {Image.open(p).size}  {size_mb:.2f} MB{warn}")


if __name__ == "__main__":
    main()
