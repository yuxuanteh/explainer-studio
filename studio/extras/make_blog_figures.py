"""Figures for the website blog posts (light "paper" style to match the article pages).

    python make_blog_figures.py            # all figures, zh + en
    python make_blog_figures.py rock_cycle # only one

Output: [paths] blog_images in studio.toml (default <project>/blog-images)/<name>-<lang>.png (1600 px wide).
The figures here are the original channel's geoscience examples: add a function per figure your posts need.
Data: USGS ComCat (catalogue), Natural Earth (coastlines). Text in the figure is kept short;
the explanation and the source credit go in the caption (image alt text) in the post.
"""
import csv
import hashlib
import io
import sys
import urllib.request
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))   # <studio>/scripts
import gs_env
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle, Circle, Ellipse  # noqa: E402
import numpy as np  # noqa: E402

FONTS = gs_env.BRAND / "fonts" / "static"
for f in ["NotoSansSC-Regular.ttf", "NotoSansSC-Medium.ttf", "NotoSansSC-Bold.ttf", "SpaceGrotesk-Bold.ttf"]:
    font_manager.fontManager.addfont(str(FONTS / f))
FONT = "Noto Sans SC"
plt.rcParams["font.family"] = FONT

OUT = Path(gs_env.cfg("paths", "blog_images", "") or gs_env.PROJECT / "blog-images")
CACHE = gs_env.STUDIO / "cache" / "blog"

# Paper palette (matches the website's light sections)
BG = "#FBF8F0"
INK = "#1A160C"
MUTED = "#6E6350"
GOLD = "#D9A60B"
GOLD_D = "#8A6400"
CYAN = "#0097A0"
RED = "#C8452A"
SEA = "#E7EEEB"
LAND = "#E6DCC3"
COAST = "#B5A47A"
ROCKS = ["#D8C9A3", "#C9B88E", "#E3D6B4", "#BFAE85", "#D2C19A", "#C4B289"]
DEPTH = ["#E0A100", "#D2582A", "#6B3FA0"]   # shallow / intermediate / deep

W, H = 1600, 900


def T(lang, zh, en):
    return zh if lang == "zh" else en


def fig(w=W, h=H):
    f = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    f.patch.set_facecolor(BG)
    return f


def save(f, name, lang):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}-{lang}.png"
    f.savefig(p, facecolor=BG)
    plt.close(f)
    print("wrote", p.name)


def http(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (hashlib.md5(url.encode()).hexdigest() + ".txt")
    if not key.exists():
        with urllib.request.urlopen(url, timeout=90) as r:
            key.write_text(r.read().decode("utf-8"), encoding="utf-8")
    return key.read_text(encoding="utf-8")


def land(ax, region, res="50m"):
    import cartopy.io.shapereader as shpreader
    from shapely.geometry import box
    lon0, lon1, lat0, lat1 = region
    clip = box(lon0, lat0, lon1, lat1)
    ax.set_facecolor(SEA)
    for g in shpreader.Reader(shpreader.natural_earth(res, "physical", "land")).geometries():
        if g.intersects(clip):
            part = g.intersection(clip)
            for poly in getattr(part, "geoms", [part]):
                if poly.geom_type == "Polygon":
                    x, y = poly.exterior.xy
                    ax.fill(x, y, color=LAND, ec=COAST, lw=0.8, zorder=1)
    ax.set_xlim(lon0, lon1)
    ax.set_ylim(lat0, lat1)
    ax.set_aspect(1 / np.cos(np.radians((lat0 + lat1) / 2)))
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color(COAST)


def label(ax, x, y, text, size=17, color=INK, weight="medium", **kw):
    ax.text(x, y, text, fontsize=size, color=color, weight=weight, zorder=6, **kw)


# ------------------------------------------------------------------ golden spike

def gssp_concept(lang):
    f = fig()
    ax = f.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")
    # rock section
    x0, x1 = 1.2, 8.2
    edges = [0.8, 1.9, 2.8, 3.9, 4.6, 5.8, 6.7, 7.9]
    for i in range(len(edges) - 1):
        ax.add_patch(Rectangle((x0, edges[i]), x1 - x0, edges[i + 1] - edges[i], color=ROCKS[i % len(ROCKS)], lw=0))
        ax.plot([x0, x1], [edges[i], edges[i]], color=COAST, lw=1)
    ax.add_patch(Rectangle((x0, 0.8), x1 - x0, 7.1, fill=False, ec=COAST, lw=1.5))
    yb = 3.9                                           # the boundary
    ax.plot([x0 - 0.3, x1 + 0.3], [yb, yb], color=GOLD, lw=4, zorder=4)
    # older fossils (below) and the new one (above)
    rng = np.random.default_rng(3)
    for _ in range(9):
        x, y = rng.uniform(x0 + 0.4, x1 - 0.4), rng.uniform(1.0, yb - 0.3)
        ax.add_patch(Ellipse((x, y), 0.34, 0.16, color=MUTED, alpha=0.55))
    for _ in range(9):
        x, y = rng.uniform(x0 + 0.4, x1 - 0.4), rng.uniform(yb + 0.12, 7.6)
        ax.add_patch(Circle((x, y), 0.13, color=CYAN, alpha=0.85))
    ax.add_patch(Circle((5.1, yb + 0.16), 0.13, color=CYAN, zorder=5))
    # the spike, driven into the boundary from the right
    tip = (x1 - 0.05, yb)
    ax.add_patch(Polygon([tip, (x1 + 1.2, yb + 0.22), (x1 + 1.2, yb - 0.22)], color=GOLD, zorder=6))
    ax.add_patch(Rectangle((x1 + 1.2, yb - 0.45), 0.3, 0.9, color=GOLD, zorder=6))
    # labels
    label(ax, 10.2, 6.4, T(lang, "较新的时代", "Younger period"), 24, weight="bold")
    label(ax, 10.2, 5.9, T(lang, "新的化石出现了", "New fossils appear"), 18, color=CYAN)
    label(ax, 10.2, 2.4, T(lang, "较老的时代", "Older period"), 24, weight="bold")
    label(ax, 10.2, 1.9, T(lang, "只有旧的化石", "Only older fossils"), 18, color=MUTED)
    label(ax, 10.2, 4.25, T(lang, "金钉子（GSSP）", "Golden spike (GSSP)"), 24, color=GOLD_D, weight="bold")
    label(ax, 10.2, 3.55, T(lang, "钉在新化石第一次出现的那一层", "placed where the new fossil first appears"), 17, color=INK)
    ax.annotate("", xy=(5.25, yb + 0.25), xytext=(6.6, 5.6),
                arrowprops=dict(arrowstyle="->", color=CYAN, lw=2))
    label(ax, 6.0, 5.7, T(lang, "第一次出现", "first appearance"), 16, color=CYAN, weight="bold")
    label(ax, 1.2, 8.25, T(lang, "一段真实的岩层剖面（示意）", "A real rock section (schematic)"), 18, color=MUTED)
    save(f, "gssp-concept", lang)


def gssp_map(lang):
    f = fig(1600, 560)
    ax = f.add_axes([0.01, 0.01, 0.98, 0.98])
    region = [-100, 140, -4, 60]
    land(ax, region)
    pts = [
        (14.06, 49.86, "spike", T(lang, "Klonk，捷克\n1972 · 第一个金钉子", "Klonk, Czech Republic\n1972 · the first golden spike"), (-38, 6)),
        (119.71, 31.08, "spike", T(lang, "煤山，中国\n2001 · 二叠纪／三叠纪", "Meishan, China\n2001 · Permian / Triassic"), (-52, 12)),
        (8.65, 36.15, "spike", T(lang, "El Kef，突尼斯\n1991 · 白垩纪／古近纪", "El Kef, Tunisia\n1991 · Cretaceous / Paleogene"), (-40, -12)),
        (-79.95, 43.47, "no", T(lang, "Crawford Lake，加拿大\n人类世提案，2024 年被否决", "Crawford Lake, Canada\nAnthropocene proposal, rejected 2024"), (-12, -30)),
        (99.80, 6.35, "rock", T(lang, "Langkawi\n马来西亚最古老的岩层（不是金钉子）", "Langkawi\nMalaysia's oldest rocks (not a GSSP)"), (-72, 6)),
    ]
    for lon, lat, kind, text, (dx, dy) in pts:
        if kind == "spike":
            ax.scatter(lon, lat, marker="v", s=420, color=GOLD, ec=GOLD_D, lw=1.5, zorder=5)
        elif kind == "no":
            ax.scatter(lon, lat, marker="X", s=360, color=MUTED, zorder=5)
        else:
            ax.scatter(lon, lat, marker="o", s=300, color=CYAN, ec="white", lw=1.5, zorder=5)
        ax.annotate(text, xy=(lon, lat), xytext=(lon + dx, lat + dy), fontsize=17, color=INK, weight="medium",
                    zorder=6, arrowprops=dict(arrowstyle="-", color=MUTED, lw=1),
                    bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=COAST, alpha=0.92))
    save(f, "gssp-map", lang)


# ------------------------------------------------------------------ Segamat

def segamat_sequence(lang):
    f = fig(1600, 820)
    ax = f.add_axes([0.08, 0.14, 0.88, 0.76])
    ax.set_facecolor(BG)
    labels = [T(lang, "8月24日\n06:13", "24 Aug\n06:13"), T(lang, "8月24日\n09:00", "24 Aug\n09:00"),
              T(lang, "8月27日", "27 Aug"), T(lang, "8月29日", "29 Aug"), T(lang, "8月30日", "30 Aug")]
    mags = [4.1, 2.8, 3.2, 3.4, 2.7]
    cols = [GOLD] + [COAST] * 4
    b = ax.bar(range(5), mags, color=cols, width=0.6)
    for r, m in zip(b, mags):
        ax.text(r.get_x() + r.get_width() / 2, m + 0.08, f"{m}", ha="center", fontsize=24, weight="bold", color=INK)
    ax.set_xticks(range(5), labels, fontsize=17, color=INK)
    ax.set_ylim(0, 5)
    ax.set_ylabel(T(lang, "规模（MetMalaysia）", "Magnitude (MetMalaysia)"), fontsize=17, color=MUTED)
    ax.tick_params(axis="y", labelsize=15, colors=MUTED)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(COAST)
    ax.grid(axis="y", color="#E8DFC8")
    ax.set_axisbelow(True)
    f.text(0.08, 0.93, T(lang, "2025 年 8 月 Segamat 一带的地震", "Earthquakes around Segamat, August 2025"),
           fontsize=24, weight="bold", color=INK)
    save(f, "segamat-sequence", lang)


def km_to_deg(dx_km, dy_km, lat):
    return dx_km / (111.32 * np.cos(np.radians(lat))), dy_km / 110.57


def segamat_map(lang):
    f = fig(1600, 1000)
    ax = f.add_axes([0.01, 0.01, 0.98, 0.98])
    region = [102.35, 103.55, 1.85, 2.75]
    land(ax, region, "10m")
    towns = [("Segamat", 102.8156, 2.5027), ("Labis", 103.0210, 2.3850), ("Yong Peng", 103.0659, 2.0136),
             ("Kluang", 103.3185, 2.0301), ("Muar", 102.5689, 2.0442)]
    for n, lo, la in towns:
        ax.scatter(lo, la, s=90, color=INK, zorder=5)
        label(ax, lo + 0.012, la + 0.012, n, 18, weight="bold")
    # USGS solution (real coordinates) with its 6.7 km horizontal error
    ulo, ula = 102.936, 2.4785
    rx, ry = km_to_deg(6.7, 6.7, ula)
    ax.add_patch(Ellipse((ulo, ula), 2 * rx, 2 * ry, color=CYAN, alpha=0.15, zorder=3))
    ax.scatter(ulo, ula, marker="*", s=900, color=CYAN, ec="white", lw=1.5, zorder=6)
    label(ax, ulo + 0.06, ula - 0.025, T(lang, "USGS 震中\n（圆圈：水平误差约 6.7 km）", "USGS epicentre\n(circle: ~6.7 km horizontal error)"),
          16, color=CYAN, weight="bold")
    # MetMalaysia: only described as "about 5 km west of Segamat"
    dlo, _ = km_to_deg(5, 0, 2.5027)
    mlo, mla = 102.8156 - dlo, 2.5027
    ax.scatter(mlo, mla, marker="*", s=900, color=GOLD, ec=GOLD_D, lw=1.5, zorder=6)
    label(ax, mlo + 0.03, mla + 0.06, T(lang, "MetMalaysia 震中\n（按「以西约 5 km」示意）", "MetMalaysia epicentre\n(placed from \"about 5 km west\")"),
          16, color=GOLD_D, weight="bold", ha="right")
    ax.plot([mlo, ulo], [mla, ula], color=INK, lw=1.5, ls="--", zorder=4)
    label(ax, (mlo + ulo) / 2 - 0.03, (mla + ula) / 2 - 0.045, "≈ 18 km", 18, weight="bold")
    # the 2.8 at 09:00, "about 28 km north-west of Kluang"
    dx, dy = km_to_deg(-19.8, 19.8, 2.03)
    klo, kla = 103.3185 + dx, 2.0301 + dy
    ax.scatter(klo, kla, marker="*", s=420, color=COAST, ec=MUTED, zorder=6)
    label(ax, klo + 0.03, kla - 0.015, T(lang, "M2.8（09:00，示意位置）", "M2.8 (09:00, approximate)"), 15, color=MUTED)
    # scale bar 20 km
    sx, _ = km_to_deg(20, 0, 1.9)
    ax.plot([103.25, 103.25 + sx], [1.9, 1.9], color=INK, lw=4, zorder=6)
    label(ax, 103.25, 1.92, "20 km", 16)
    save(f, "segamat-map", lang)


def plate_types(lang):
    f = fig()
    ax = f.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")
    # oceanic plate diving under the continental plate on the left
    # slab top runs from (3.0, 5.5) down to (5.8, 1.6); the continent sits on top of it
    slope = (5.5 - 1.6) / (5.8 - 3.0)
    xs = lambda y: 3.0 + (5.5 - y) / slope            # x of the slab top at height y
    ax.add_patch(Polygon([(0, 5.5), (3.0, 5.5), (xs(5.9), 5.9), (0, 5.9)], color="#BFD8DE"))   # sea water
    ax.add_patch(Polygon([(0, 5.5), (3.0, 5.5), (5.8, 1.6), (5.1, 1.1), (2.55, 4.65), (0, 4.65)], color="#9FB8B8"))
    ax.add_patch(Polygon([(xs(5.9), 5.9), (16, 5.9), (16, 3.3), (xs(3.3), 3.3)], color=LAND, ec=COAST))
    for y in (4.9, 4.2, 3.5):
        ax.scatter(xs(y) + 0.05, y, marker="*", s=700, color=RED, ec="white", zorder=5)
    # a fault inside the plate
    ax.plot([11.2, 12.2], [5.9, 3.6], color=INK, lw=3)
    ax.scatter(11.6, 4.9, marker="*", s=700, color=GOLD, ec=GOLD_D, zorder=5)
    label(ax, 0.6, 7.7, T(lang, "Interplate earthquake\n板块交界的地震", "Interplate earthquake\nat a plate boundary"), 22, weight="bold", color=RED)
    label(ax, 0.6, 6.8, T(lang, "例：日本、印尼", "e.g. Japan, Indonesia"), 17, color=MUTED)
    label(ax, 9.6, 7.7, T(lang, "Intraplate earthquake\n板块内部的地震", "Intraplate earthquake\ninside a plate"), 22, weight="bold", color=GOLD_D)
    label(ax, 9.6, 6.8, T(lang, "例：Segamat", "e.g. Segamat"), 17, color=MUTED)
    label(ax, 12.4, 4.4, T(lang, "古老断层\n重新滑动", "old fault\nslips again"), 16, color=INK)
    label(ax, 6.0, 1.3, T(lang, "海洋板块插进大陆板块底下", "ocean plate sliding under the continent"), 16, color=MUTED)
    ax.annotate("", xy=(4.9, 2.1), xytext=(3.1, 4.6), arrowprops=dict(arrowstyle="->", color="#5E7F86", lw=2.5))
    label(ax, 0.3, 6.05, T(lang, "海", "sea"), 15, color="#5E7F86")
    label(ax, 7.5, 8.5, T(lang, "示意图", "schematic"), 14, color=MUTED)
    save(f, "plate-types", lang)


def pore_pressure(lang):
    f = fig(1600, 760)
    ax = f.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 7.6)
    ax.axis("off")
    for x0, wet in [(0.8, False), (8.8, True)]:
        gap = 0.45 if wet else 0.08
        ax.add_patch(Rectangle((x0, 1.4), 2.8, 3.6, color=ROCKS[0], ec=COAST))
        ax.add_patch(Rectangle((x0 + 2.8 + gap, 1.4), 2.8, 3.6, color=ROCKS[3], ec=COAST))
        if wet:
            ax.add_patch(Rectangle((x0 + 2.8, 1.4), gap, 3.6, color="#7CC3D6"))
            for y in [1.7, 4.1]:
                ax.annotate("", xy=(x0 + 2.45, y + 0.2), xytext=(x0 + 3.0, y + 0.2), arrowprops=dict(arrowstyle="->", color=CYAN, lw=2.5))
                ax.annotate("", xy=(x0 + 3.65 + gap - 0.3, y + 0.2), xytext=(x0 + 3.1 + gap - 0.3, y + 0.2), arrowprops=dict(arrowstyle="->", color=CYAN, lw=2.5))
        lw = 3 if wet else 6
        ax.annotate("", xy=(x0 + 2.6, 3.2), xytext=(x0 - 0.6, 3.2), arrowprops=dict(arrowstyle="->", color=INK, lw=lw))
        ax.annotate("", xy=(x0 + 3.0 + gap, 3.2), xytext=(x0 + 6.2 + gap, 3.2), arrowprops=dict(arrowstyle="->", color=INK, lw=lw))
    label(ax, 0.8, 6.4, T(lang, "干的断层", "Dry fault"), 24, weight="bold")
    label(ax, 0.8, 5.7, T(lang, "两边被压得很紧，不容易滑动", "the two sides are clamped tight"), 17, color=MUTED)
    label(ax, 8.8, 6.4, T(lang, "有水渗进来", "Water gets in"), 24, weight="bold", color=CYAN)
    label(ax, 8.8, 5.7, T(lang, "水压把两边撑开一点，压紧的力量变小", "water pressure props the sides apart a little"), 17, color=MUTED)
    label(ax, 6.8, 0.5, T(lang, "示意图（缝隙宽度放大了）", "schematic (gap exaggerated)"), 14, color=MUTED)
    save(f, "pore-pressure", lang)


# ------------------------------------------------------------------ Malaysia

def catalogue(url):
    rows = list(csv.DictReader(io.StringIO(http(url))))
    return [(float(r["longitude"]), float(r["latitude"]), float(r["depth"]), float(r["mag"])) for r in rows]


SEISMIC_URL = ("https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&orderby=magnitude"
               "&starttime=1976-01-01&endtime=2026-01-01&minlatitude=-7&maxlatitude=10"
               "&minlongitude=88&maxlongitude=115&minmagnitude=5")


def malaysia_seismicity(lang):
    f = fig(1600, 1000)
    ax = f.add_axes([0.005, 0.005, 0.99, 0.99])
    region = [88, 115, -7, 10]
    land(ax, region)
    ev = catalogue(SEISMIC_URL)
    lo, la, de, ma = (np.array(c) for c in zip(*ev))
    cls = np.where(de < 70, 0, np.where(de < 300, 1, 2))
    for k in np.argsort(-de):
        ax.scatter(lo[k], la[k], s=(ma[k] - 4.6) ** 2 * 18, color=DEPTH[cls[k]], alpha=0.6, lw=0, zorder=3)
    box = dict(boxstyle="round,pad=0.3", fc="white", ec=COAST, alpha=0.9)
    ax.scatter(95.982, 3.295, marker="*", s=1300, color=RED, ec="white", lw=2, zorder=6)
    ax.annotate(T(lang, "2004 M9.1 震中", "2004 M9.1 epicentre"), xy=(95.98, 3.3), xytext=(88.6, 6.2), fontsize=17,
                color=RED, weight="bold", zorder=7, bbox=box, arrowprops=dict(arrowstyle="-", color=RED, lw=1.5))
    for n, lo_, la_, tx, ty in [("Kuala Lumpur", 101.687, 3.139, 103.6, 4.3), ("Bukit Tinggi", 101.82, 3.40, 103.6, 5.4),
                                ("Segamat", 102.816, 2.503, 104.2, 3.0)]:
        ax.scatter(lo_, la_, s=110, color=INK, zorder=6)
        ax.annotate(n, xy=(lo_, la_), xytext=(tx, ty), fontsize=16, weight="bold", color=INK, zorder=7, bbox=box,
                    arrowprops=dict(arrowstyle="-", color=INK, lw=1))
    label(ax, 89.2, -6.2, T(lang, "Sumatra Subduction Zone（印度–澳洲板块从这里插进去）",
                            "Sumatra Subduction Zone (the Indian-Australian Plate dives in here)"),
          16, color=INK, weight="bold", rotation=-34, bbox=box)
    label(ax, 106.2, 0.6, "Sundaland", 28, color=MUTED, weight="bold", style="italic")
    # legend in the open South China Sea
    lx, ly = 107.0, 8.9
    label(ax, lx - 0.2, ly, T(lang, f"M5+ 地震，1976–2025（{len(ev)} 个）", f"M5+ earthquakes, 1976–2025 ({len(ev)})"), 16, weight="bold")
    for i, (t, c) in enumerate(zip([T(lang, "浅层 0–70 km", "shallow 0–70 km"), T(lang, "中层 70–300 km", "intermediate 70–300 km"),
                                    T(lang, "深层 300–700 km", "deep 300–700 km")], DEPTH)):
        ax.scatter(lx, ly - 0.75 - i * 0.75, s=220, color=c, zorder=6)
        label(ax, lx + 0.4, ly - 0.95 - i * 0.75, t, 16)
    save(f, "malaysia-seismicity", lang)
    return len(ev)


def bukit_tinggi(lang):
    f = fig(1600, 700)
    ax = f.add_axes([0.08, 0.16, 0.88, 0.7])
    ax.set_facecolor(BG)
    b = ax.bar(["2007", "2008", "2009"], [9, 8, 5], color=[GOLD, GOLD, GOLD], width=0.5)
    for r, v in zip(b, [9, 8, 5]):
        ax.text(r.get_x() + r.get_width() / 2, v + 0.2, str(v), ha="center", fontsize=26, weight="bold", color=INK)
    ax.set_ylim(0, 11)
    ax.tick_params(labelsize=18, colors=INK)
    ax.set_ylabel(T(lang, "本地地震次数", "local earthquakes"), fontsize=17, color=MUTED)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(COAST)
    f.text(0.08, 0.9, T(lang, "Bukit Tinggi 一带的本地地震（2007–2009，约 22 次）", "Local earthquakes around Bukit Tinggi (2007–2009, about 22)"),
           fontsize=24, weight="bold", color=INK)
    save(f, "bukit-tinggi", lang)


# ------------------------------------------------------------------ rock cycle

def rock_cycle(lang):
    f = fig(1600, 1100)
    ax = f.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11)
    ax.axis("off")
    HW, HH = 1.7, 0.85                                  # box half width / height
    nodes = {
        "magma": (8, 9.4, T(lang, "Magma\n岩浆", "Magma"), "#E9B9A0"),
        "igneous": (13.0, 6.2, T(lang, "Igneous rock\n火成岩", "Igneous rock"), "#E6C27A"),
        "sediment": (11.2, 1.6, T(lang, "Sediment\n沉积物（沙、泥）", "Sediment\n(sand, mud)"), "#EADFC2"),
        "sedimentary": (4.8, 1.6, T(lang, "Sedimentary rock\n沉积岩", "Sedimentary rock"), "#D9C79A"),
        "metamorphic": (3.0, 6.2, T(lang, "Metamorphic rock\n变质岩", "Metamorphic rock"), "#C9B6C9"),
    }
    for k, (x, y, t, c) in nodes.items():
        ax.add_patch(FancyBboxPatch((x - HW + 0.1, y - HH + 0.1), 2 * HW - 0.2, 2 * HH - 0.2,
                                    boxstyle="round,pad=0.1,rounding_size=0.3", fc=c, ec=INK, lw=1.5, zorder=3))
        ax.text(x, y, t, ha="center", va="center", fontsize=20, weight="bold", color=INK, zorder=4)

    def edge(p, q, gap=0.12):
        """Point where the line from box centre p towards q leaves the box (plus a small gap)."""
        dx, dy = q[0] - p[0], q[1] - p[1]
        s = min(HW / abs(dx) if dx else 1e9, HH / abs(dy) if dy else 1e9)
        L = np.hypot(dx, dy)
        return (p[0] + dx * s + dx / L * gap, p[1] + dy * s + dy / L * gap)

    def arrow(a, b, text, rad=0.0, tx=0, ty=0, color=INK):
        p, q = nodes[a][:2], nodes[b][:2]
        ax.add_patch(FancyArrowPatch(edge(p, q), edge(q, p), connectionstyle=f"arc3,rad={rad}", arrowstyle="-|>",
                                     mutation_scale=30, lw=2.8, color=color, shrinkA=0, shrinkB=0, zorder=5))
        if text:
            ax.text((p[0] + q[0]) / 2 + tx, (p[1] + q[1]) / 2 + ty, text, ha="center", va="center", fontsize=17,
                    color=color, weight="bold", zorder=6, bbox=dict(boxstyle="round,pad=0.25", fc=BG, ec="none"))

    PURPLE = "#7A4F8C"
    arrow("magma", "igneous", T(lang, "冷却凝固", "cooling"), -0.2, 0.9, 0.55, RED)
    arrow("igneous", "sediment", T(lang, "风化、侵蚀、搬运", "weathering, erosion,\ntransport"), -0.2, 1.5, 0.1, CYAN)
    arrow("sediment", "sedimentary", T(lang, "沉积、压实、胶结", "burial, compaction,\ncementation"), 0, 0, -0.85, GOLD_D)
    arrow("sedimentary", "metamorphic", T(lang, "高温高压", "heat and pressure"), -0.2, -1.4, 0.1, PURPLE)
    arrow("metamorphic", "magma", T(lang, "熔化", "melting"), -0.2, -0.9, 0.55, RED)
    arrow("igneous", "metamorphic", T(lang, "高温高压", "heat and pressure"), 0, 0, 0.42, PURPLE)
    ax.text(8, 3.9, T(lang, "这不是单行道：任何岩石露出地表都会被风化，\n任何岩石埋得够深都可能变质或熔化。",
                      "It isn't one-way: any rock at the surface can be weathered,\nand any rock buried deep enough can be changed or melted."),
            ha="center", va="center", fontsize=16, color=MUTED, style="italic", linespacing=1.6)
    save(f, "rock-cycle", lang)


# ------------------------------------------------------------------ epicentre

DEPTH_URL = ("https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&starttime=2026-01-01&endtime=2026-10-01"
             "&minlatitude=-10&maxlatitude=20&minlongitude=90&maxlongitude=130&minmagnitude=4.5&maxdepth=40")


def depth_histogram(lang):
    de = np.array([e[2] for e in catalogue(DEPTH_URL)])
    f = fig(1600, 820)
    ax = f.add_axes([0.08, 0.13, 0.88, 0.72])
    ax.set_facecolor(BG)
    n, edges, patches = ax.hist(de, bins=np.arange(0, 41, 1), color=CYAN, alpha=0.85)
    k10 = int(np.searchsorted(edges, 10, side="right") - 1)
    patches[k10].set_color(RED)
    exact10 = int(np.sum(np.isclose(de, 10.0)))
    ax.annotate(T(lang, f"{exact10} 个刚好是 10.0 km", f"{exact10} at exactly 10.0 km"), xy=(10.5, n[k10] * 0.98),
                xytext=(17, n[k10] * 0.8), fontsize=22, weight="bold", color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=2.5))
    ax.set_xlabel(T(lang, "目录里的深度（km）", "catalogue depth (km)"), fontsize=17, color=MUTED)
    ax.set_ylabel(T(lang, "地震数目", "earthquakes"), fontsize=17, color=MUTED)
    ax.tick_params(labelsize=15, colors=MUTED)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(COAST)
    f.text(0.08, 0.9, T(lang, f"东南亚浅层地震的深度（2026 年 1–9 月，M4.5+，共 {len(de)} 个）",
                        f"Depths of shallow earthquakes in Southeast Asia (Jan–Sep 2026, M4.5+, {len(de)} events)"),
           fontsize=22, weight="bold", color=INK)
    save(f, "depth-histogram", lang)
    return len(de), exact10


ALL = [gssp_concept, gssp_map, segamat_sequence, segamat_map, plate_types, pore_pressure,
       malaysia_seismicity, bukit_tinggi, rock_cycle, depth_histogram]

if __name__ == "__main__":
    want = sys.argv[1:]
    for fn in ALL:
        if want and fn.__name__ not in want:
            continue
        for lang in ("zh", "en"):
            r = fn(lang)
            if r is not None:
                print(fn.__name__, lang, r)
