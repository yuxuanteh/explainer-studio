"""Monitor wallpapers made from REAL public data, for the computer screen behind the presenter.

The figure must belong to the episode's theme - pick the types that echo what the episode
explains (e.g. depth episode: seismicity coloured by depth + the 10 km depth spike; P/S episode: record section;
a Malaysian event: its own waveforms). Always per episode -> episodes/<EP>/work/screens/.

    python make_screens.py --episode 01-epicenter-hypocenter --event us6000sasz --types record,heli,seismicity,depthhist
    python make_screens.py --episode 02-xxx --event us7000abcd --types record,heli --region 90 130 -10 20

Types (default: all that the arguments allow):
  record      record section of one event: stations sorted by distance, P / S arrivals (iasp91)   needs --event
  heli        3-hour drum-recorder (helicorder) of the nearest good station                       needs --event
  seismicity  map of USGS M4.5+ earthquakes in --region over --years, coloured by depth
  depthhist   histogram of catalogue depths in --region (the spike at 10 km = fixed depths)
Palette: the episode's shots.py constants (BG, WAVE, EPI, HYPO, TEXT, MUTED, DEPTH) when --episode is given,
otherwise the channel palette. Dark backgrounds so the monitor does not blow out on camera (screen at 30-40 %).
Outputs 1920x1080 and 2560x1440 PNGs; every image carries its data credit. Waveforms: EarthScope (IRIS DMC) FDSN;
catalogue: USGS ComCat; coastlines: Natural Earth.
"""
import argparse
import csv
import io
import json
import re
import urllib.request

from pathlib import Path
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))   # <studio>/scripts
import gs_env
import matplotlib
import matplotlib.patches
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402

FONTS = gs_env.FONTS / "static"
for f in ["SpaceGrotesk-Medium.ttf", "SpaceGrotesk-Bold.ttf", "NotoSansSC-Medium.ttf"]:
    font_manager.fontManager.addfont(str(FONTS / f))
EN = "Space Grotesk"
CACHE = gs_env.STUDIO / "cache" / "waves"
SIZES = [(1920, 1080), (2560, 1440)]

CHANNEL = dict(BG="#131008", GRID="#2A2414", WAVE="#00C8D2", EPI="#F2B90D", HYPO="#FF7A4D", TEXT="#F5F1E8",
               MUTED="#8C8064", LAND="#231E10", COAST="#6B5E3C", DEPTH=["#FFD95C", "#F2B90D", "#8A6400"])


def palette(episode):
    if not episode:
        return dict(CHANNEL)
    src = (gs_env.STUDIO / "episodes" / episode / "shots.py").read_text(encoding="utf-8")
    pal = dict(CHANNEL)
    for k in ("BG", "WAVE", "EPI", "HYPO", "TEXT", "MUTED", "LAND"):
        m = re.search(rf'^{k}\s*=\s*"(#[0-9A-Fa-f]{{6}})"', src, re.M)
        if m:
            pal[k] = m.group(1)
    m = re.search(r'^DEPTH\s*=\s*\[([^\]]+)\]', src, re.M)
    if m:
        pal["DEPTH"] = re.findall(r'"(#[0-9A-Fa-f]{6})"', m.group(1))
    pal["GRID"] = _mix(pal["BG"], pal["TEXT"], 0.08)
    pal["COAST"] = _mix(pal["BG"], pal["MUTED"], 0.6)
    return pal


def _mix(a, b, k):
    ca = np.array([int(a[i:i + 2], 16) for i in (1, 3, 5)])
    cb = np.array([int(b[i:i + 2], 16) for i in (1, 3, 5)])
    c = (ca * (1 - k) + cb * k).astype(int)
    return "#" + "".join(f"{v:02X}" for v in c)


def fig_px(w, h, P):
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor(P["BG"])
    return fig


def http(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8")


# ------------------------------------------------------------------ event-based figures

def event_info(eid):
    d = json.loads(http(f"https://earthquake.usgs.gov/fdsnws/event/1/query?eventid={eid}&format=geojson"))
    lon, lat, dep = d["geometry"]["coordinates"]
    pr = d["properties"]
    from obspy import UTCDateTime
    return dict(id=eid, lat=lat, lon=lon, depth=dep, mag=pr["mag"], magtype=pr.get("magType", ""),
                place=pr["place"], t=UTCDateTime(pr["time"] / 1000))


def fetch(net, sta, loc, t0, t1, tag):
    from obspy import read
    from obspy.clients.fdsn import Client
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{tag}.{net}.{sta}.mseed"
    if not path.exists():
        try:
            st = Client("IRIS").get_waveforms(net, sta, loc or "*", "BHZ", t0, t1)
            st.merge(fill_value=0)
            st.write(str(path), format="MSEED")
        except Exception:  # noqa: BLE001
            return None
    st = read(str(path))
    return st[0] if st else None


def stations_for(ev, max_deg=30, want=7):
    """Open broadband stations with data for this event, spread over distance."""
    from obspy.clients.fdsn import Client
    from obspy.geodetics import locations2degrees
    inv = Client("IRIS").get_stations(latitude=ev["lat"], longitude=ev["lon"], maxradius=max_deg, channel="BHZ",
                                      starttime=ev["t"], endtime=ev["t"] + 600, level="channel")
    cands = {}
    for net in inv:
        for sta in net:
            for ch in sta:
                key = (net.code, sta.code)
                if key not in cands:
                    cands[key] = (ch.location_code, locations2degrees(ev["lat"], ev["lon"], sta.latitude, sta.longitude))
    ranked = sorted(cands.items(), key=lambda kv: kv[1][1])
    picked, last_d = [], -99
    for (net, sta), (loc, d) in ranked:
        if d - last_d < (max_deg / want) * 0.6 or d < 1.0:
            continue
        tr = fetch(net, sta, loc, ev["t"] - 60, ev["t"] + 1260, ev["id"])
        if tr is not None and np.abs(tr.data).max() > 0:
            picked.append((net, sta, loc, d, tr))
            last_d = d
        if len(picked) >= want:
            break
    return picked


def record_section(ev, P, w, h, out):
    from obspy.taup import TauPyModel
    model = TauPyModel("iasp91")
    rows = []
    for net, sta, loc, d, tr in stations_for(ev):
        tr = tr.copy().detrend("demean").taper(0.02).filter("bandpass", freqmin=0.05, freqmax=1.0, corners=4)
        arr = {a.name: a.time for a in model.get_travel_times(max(ev["depth"], 0.1), d, ["P", "S"])}
        rows.append((d, f"{net}.{sta}", tr, arr.get("P"), arr.get("S")))
    fig = fig_px(w, h, P)
    ax = fig.add_axes([0.12, 0.1, 0.84, 0.8])
    ax.set_facecolor(P["BG"])
    fs = w / 1920
    for i, (d, name, tr, tp, ts) in enumerate(rows):
        t = tr.times() + (tr.stats.starttime - ev["t"])
        ax.plot(t, i + 0.45 * tr.data / (np.abs(tr.data).max() or 1), color=P["WAVE"], lw=0.7)
        ax.text(-40, i, f"{name}  {d:4.1f}°", color=P["MUTED"], fontsize=11 * fs, family=EN, ha="right", va="center")
        for tt, col in [(tp, P["EPI"]), (ts, P["HYPO"])]:
            if tt:
                ax.plot([tt, tt], [i - 0.4, i + 0.4], color=col, lw=1.6 * fs)
    ax.set_xlim(-30, 1200)
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.grid(True, axis="x", color=P["GRID"], lw=0.8)
    ax.set_yticks([])
    ax.tick_params(colors=P["MUTED"], labelsize=10 * fs)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("seconds after origin", color=P["MUTED"], family=EN, fontsize=11 * fs)
    fig.text(0.06, 0.94, f"M{ev['mag']:.1f}  {ev['place']}  ·  {ev['t'].strftime('%Y-%m-%d %H:%M')} UTC  ·  "
             f"depth {ev['depth']:.0f} km", color=P["TEXT"], family=EN, fontsize=20 * fs, weight="bold")
    fig.text(0.90, 0.94, "P-wave", color=P["EPI"], family=EN, fontsize=16 * fs, weight="bold", ha="right")
    fig.text(0.96, 0.94, "S-wave", color=P["HYPO"], family=EN, fontsize=16 * fs, weight="bold", ha="right")
    nets = ", ".join(sorted({r[1].split(".")[0] for r in rows}))
    fig.text(0.06, 0.03, f"Vertical (BHZ), 0.05–1 Hz · Data: EarthScope (IRIS DMC) – networks {nets} · "
             f"Event: USGS {ev['id']} · Arrivals: iasp91", color=P["MUTED"], family=EN, fontsize=9 * fs)
    path = out / f"screen-record-section-{w}x{h}.png"
    fig.savefig(path, facecolor=P["BG"])
    plt.close(fig)
    return path


def helicorder(ev, P, w, h, out):
    st = stations_for(ev, max_deg=20, want=3)
    if not st:
        return None
    net, sta, loc, d, _ = st[min(1, len(st) - 1)]
    t0 = ev["t"] - 1800
    tr = fetch(net, sta, loc, t0, t0 + 3 * 3600, f"heli-{ev['id']}")
    if tr is None:
        return None
    tr = tr.copy().detrend("demean").taper(0.01).filter("bandpass", freqmin=0.5, freqmax=5.0, corners=4)
    line_s, n = 10 * 60, 18
    fig = fig_px(w, h, P)
    ax = fig.add_axes([0.06, 0.08, 0.9, 0.82])
    data, sr = tr.data.astype(float), tr.stats.sampling_rate
    off = int((tr.stats.starttime - t0) * sr)
    clip = np.percentile(np.abs(data), 50) * 12          # drum look: noise visible, the quake saturates
    fs = w / 1920
    for i in range(n):
        a, b = i * line_s * sr - off, (i + 1) * line_s * sr - off
        seg = data[max(int(a), 0):max(int(b), 0)]
        if len(seg):
            ax.plot(np.arange(len(seg)) / sr / 60, -i + 0.42 * np.clip(seg / clip, -1.6, 1.6),
                    color=P["WAVE"] if i % 2 == 0 else P["MUTED"], lw=0.5)
        ax.text(-0.3, -i, (t0 + i * line_s).strftime("%H:%M"), color=P["MUTED"], family=EN, fontsize=10 * fs,
                ha="right", va="center")
    ax.set_xlim(0, 10)
    ax.set_ylim(-n + 0.3, 1)
    ax.axis("off")
    fig.text(0.06, 0.94, f"{net}.{sta}  BHZ  ·  {ev['t'].strftime('%Y-%m-%d')} UTC", color=P["TEXT"], family=EN,
             fontsize=20 * fs, weight="bold")
    fig.text(0.06, 0.03, f"M{ev['mag']:.1f} {ev['place']} (USGS {ev['id']}) · Data: EarthScope (IRIS DMC) · "
             "0.5–5 Hz · 10 min per line", color=P["MUTED"], family=EN, fontsize=9 * fs)
    path = out / f"screen-helicorder-{w}x{h}.png"
    fig.savefig(path, facecolor=P["BG"])
    plt.close(fig)
    return path


# ------------------------------------------------------------------ catalogue-based figures

def catalogue(region, years, minmag=4.5, maxdepth=None):
    lon0, lon1, lat0, lat1 = region
    t1 = 2026
    url = ("https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&orderby=time-asc"
           f"&starttime={t1 - years}-01-01&endtime={t1}-10-01&minlatitude={lat0}&maxlatitude={lat1}"
           f"&minlongitude={lon0}&maxlongitude={lon1}&minmagnitude={minmag}"
           + (f"&maxdepth={maxdepth}" if maxdepth else ""))
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / f"cat-{lon0}-{lon1}-{lat0}-{lat1}-{years}-{minmag}-{maxdepth}.csv"
    if not key.exists():
        key.write_text(http(url), encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(key.read_text(encoding="utf-8"))))
    return [(float(r["longitude"]), float(r["latitude"]), float(r["depth"]), float(r["mag"])) for r in rows], url


def _widen(region, w, h):
    lon0, lon1, lat0, lat1 = region
    need = (lat1 - lat0) / np.cos(np.radians((lat0 + lat1) / 2)) * w / h
    if need > lon1 - lon0:
        mid = (lon0 + lon1) / 2
        lon0, lon1 = round(mid - need / 2, 1), round(mid + need / 2, 1)
    return [lon0, lon1, lat0, lat1]


def seismicity(P, w, h, out, region, years):
    import cartopy.io.shapereader as shpreader
    from shapely.geometry import box
    ev, _ = catalogue(_widen(region, w, h), years)
    fig = fig_px(w, h, P)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(P["BG"])
    lon0, lon1, lat0, lat1 = region
    coslat = np.cos(np.radians((lat0 + lat1) / 2))
    need = (lat1 - lat0) / coslat * w / h                 # widen the longitude range so the map fills 16:9
    if need > lon1 - lon0:
        mid = (lon0 + lon1) / 2
        lon0, lon1 = mid - need / 2, mid + need / 2
    clip = box(lon0, lat0, lon1, lat1)
    for g in shpreader.Reader(shpreader.natural_earth("50m", "physical", "land")).geometries():
        if g.intersects(clip):
            part = g.intersection(clip)
            for poly in getattr(part, "geoms", [part]):
                if poly.geom_type == "Polygon":
                    x, y = poly.exterior.xy
                    ax.fill(x, y, color=P["LAND"], ec=P["COAST"], lw=0.6)
    lo, la, de, ma = (np.array(c) for c in zip(*ev))
    cols = np.where(de < 70, 0, np.where(de < 300, 1, 2))
    order = np.argsort(-de)                               # deep first, shallow on top
    for k in order:
        ax.scatter(lo[k], la[k], s=(ma[k] - 4.0) ** 2.2 * 6 * (w / 1920), color=P["DEPTH"][cols[k]],
                   alpha=0.75, lw=0)
    ax.set_xlim(lon0, lon1)
    ax.set_ylim(lat0, lat1)
    ax.set_aspect(1 / np.cos(np.radians((lat0 + lat1) / 2)))
    ax.axis("off")
    fs = w / 1920
    fig.text(0.04, 0.94, f"Seismicity  ·  M4.5+  ·  {2026 - years}–2026", color=P["TEXT"], family=EN,
             fontsize=22 * fs, weight="bold")
    for i, (lab, c) in enumerate(zip(["0–70 km", "70–300 km", "300–700 km"], P["DEPTH"])):
        x = 0.04 + i * 0.10                               # drawn dot (Space Grotesk has no ● glyph)
        fig.patches.append(matplotlib.patches.Circle((x + 0.006, 0.906), 0.006 * h / w * 1.0, transform=fig.transFigure,
                                                     color=c, figure=fig))
        fig.text(x + 0.016, 0.90, lab, color=c, family=EN, fontsize=13 * fs, weight="bold")
    fig.text(0.04, 0.03, f"{len(ev)} events · Data: USGS ComCat · Coastlines: Natural Earth", color=P["MUTED"],
             family=EN, fontsize=10 * fs)
    path = out / f"screen-seismicity-{w}x{h}.png"
    fig.savefig(path, facecolor=P["BG"])
    plt.close(fig)
    return path


def depthhist(P, w, h, out, region, years):
    ev, _ = catalogue(region, years, maxdepth=60)
    de = np.array([e[2] for e in ev])
    fig = fig_px(w, h, P)
    ax = fig.add_axes([0.1, 0.14, 0.84, 0.72])
    ax.set_facecolor(P["BG"])
    bins = np.arange(0, 61, 1)
    n, edges, patches = ax.hist(de, bins=bins, color=P["WAVE"], alpha=0.85)
    k10 = np.searchsorted(edges, 10, side="right") - 1
    patches[k10].set_color(P["HYPO"])
    fs = w / 1920
    ax.annotate(f"{int(n[k10])} events at exactly 10 km", xy=(10.5, n[k10]), xytext=(22, n[k10] * 0.85),
                color=P["HYPO"], family=EN, fontsize=18 * fs, weight="bold",
                arrowprops=dict(arrowstyle="->", color=P["HYPO"], lw=2))
    ax.set_xlabel("catalogue depth (km)", color=P["MUTED"], family=EN, fontsize=13 * fs)
    ax.set_ylabel("events", color=P["MUTED"], family=EN, fontsize=13 * fs)
    ax.tick_params(colors=P["MUTED"], labelsize=11 * fs)
    for s in ax.spines.values():
        s.set_color(P["GRID"])
    ax.grid(True, axis="y", color=P["GRID"], lw=0.8)
    lon0, lon1, lat0, lat1 = region
    fig.text(0.1, 0.92, f"Shallow earthquakes  ·  depth < 60 km  ·  M4.5+  ·  {2026 - years}–2026", color=P["TEXT"],
             family=EN, fontsize=22 * fs, weight="bold")
    fig.text(0.1, 0.04, f"{len(de)} events, {lon0}–{lon1}°E, {lat0}–{lat1}°N · Data: USGS ComCat", color=P["MUTED"],
             family=EN, fontsize=10 * fs)
    path = out / f"screen-depth-histogram-{w}x{h}.png"
    fig.savefig(path, facecolor=P["BG"])
    plt.close(fig)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True)
    ap.add_argument("--event")
    ap.add_argument("--types")
    ap.add_argument("--region", nargs=4, type=float, default=[90, 130, -10, 20], metavar=("LON0", "LON1", "LAT0", "LAT1"))
    ap.add_argument("--years", type=int, default=10)
    a = ap.parse_args()
    P = palette(a.episode)
    out = gs_env.EPISODES / a.episode / "work" / "screens"
    out.mkdir(parents=True, exist_ok=True)
    types = a.types.split(",") if a.types else (["record", "heli"] if a.event else []) + ["seismicity", "depthhist"]
    ev = event_info(a.event) if a.event else None
    region = [int(v) if float(v).is_integer() else v for v in a.region]
    for w, h in SIZES:
        for t in types:
            if t == "record" and ev:
                p = record_section(ev, P, w, h, out)
            elif t == "heli" and ev:
                p = helicorder(ev, P, w, h, out)
            elif t == "seismicity":
                p = seismicity(P, w, h, out, region, a.years)
            elif t == "depthhist":
                p = depthhist(P, w, h, out, region, min(a.years, 3))
            else:
                continue
            print(p)


if __name__ == "__main__":
    main()
