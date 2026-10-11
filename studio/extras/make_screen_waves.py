"""Monitor wallpapers with REAL seismograms, for the screen behind the presenter.

    python make_screen_waves.py

Downloads open broadband data (EarthScope / IRIS FDSN) for the 2026-02-22 M7.1 deep earthquake off Sabah
(USGS us6000sasz, 629 km deep) and draws:
  * record section - stations sorted by distance, P and S arrivals marked (iasp91 via TauP)
  * helicorder     - one station, 3 hours, drum-recorder style
at 1920x1080 and 2560x1440 into youtube/brand/screens/. Colours: episode-01 "B2" palette (dark, so the monitor
does not blow out on camera). Data is public; the credit line is drawn on the image.
"""
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))   # <studio>/scripts
import gs_env
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from obspy import UTCDateTime  # noqa: E402
from obspy.clients.fdsn import Client  # noqa: E402
from obspy.geodetics import locations2degrees  # noqa: E402
from obspy.taup import TauPyModel  # noqa: E402

OUT = gs_env.BRAND / "screens"
CACHE = gs_env.STUDIO / "cache" / "waves"
FONTS = gs_env.FONTS / "static"
for f in ["SpaceGrotesk-Medium.ttf", "SpaceGrotesk-Bold.ttf", "NotoSansSC-Medium.ttf"]:
    font_manager.fontManager.addfont(str(FONTS / f))
EN = "Space Grotesk"

BG, GRID, TRACE, TRACE2 = "#0B1320", "#16243A", "#3EC1D3", "#8FA3BA"
P_COL, S_COL, TEXT, MUTED = "#FFD166", "#FF4D6D", "#EAF1F8", "#5E728A"

ORIGIN = UTCDateTime("2026-02-22T16:57:46")
EV_LAT, EV_LON, EV_DEP = 6.8541, 116.2942, 629.0
# Open stations whose data EarthScope serves for this event (GE / AD / CB returned no data there).
STATIONS = [("II", "KAPI", "00"), ("IC", "QIZ", "00"), ("HK", "HKPS", "00"), ("AU", "XMI", "00"),
            ("IU", "CHTO", "00"), ("AU", "MTN", "00")]
HELI = ("HK", "HKPS", "00")


def fetch(net, sta, loc, t0, t1, tag):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{tag}.{net}.{sta}.mseed"
    if not path.exists():
        for name in ["IRIS"]:
            try:
                st = Client(name).get_waveforms(net, sta, loc, "BHZ", t0, t1)
                st.merge(fill_value=0)
                st.write(str(path), format="MSEED")
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {net}.{sta} via {name}: {type(e).__name__}")
    if not path.exists():
        return None
    from obspy import read
    st = read(str(path))
    return st[0] if st else None


def station_coords(net, sta):
    inv = Client("IRIS").get_stations(network=net, station=sta, starttime=ORIGIN, endtime=ORIGIN + 60)
    s = inv[0][0]
    return s.latitude, s.longitude


def fig_px(w, h):
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor(BG)
    return fig


def record_section(w, h):
    model = TauPyModel("iasp91")
    rows = []
    for net, sta, loc in STATIONS:
        tr = fetch(net, sta, loc, ORIGIN - 60, ORIGIN + 1260, "sabah")
        if tr is None:
            continue
        try:
            lat, lon = station_coords(net, sta)
        except Exception:  # noqa: BLE001
            continue
        tr.detrend("demean").taper(0.02).filter("bandpass", freqmin=0.05, freqmax=1.0, corners=4)
        d = locations2degrees(EV_LAT, EV_LON, lat, lon)
        arr = {a.name: a.time for a in model.get_travel_times(EV_DEP, d, ["P", "S"])}
        rows.append((d, f"{net}.{sta}", tr, arr.get("P"), arr.get("S")))
    rows.sort(key=lambda r: r[0])
    print(f"  record section: {len(rows)} stations")

    fig = fig_px(w, h)
    ax = fig.add_axes([0.12, 0.1, 0.84, 0.8])
    ax.set_facecolor(BG)
    for i, (d, name, tr, tp, ts) in enumerate(rows):
        t = tr.times() + (tr.stats.starttime - ORIGIN)
        y = tr.data / (np.abs(tr.data).max() or 1)
        ax.plot(t, i + 0.45 * y, color=TRACE, lw=0.7, alpha=0.95)
        ax.text(-40, i, f"{name}  {d:4.1f}°", color=TRACE2, fontsize=11 * w / 1920, family=EN, ha="right", va="center")
        for tt, col in [(tp, P_COL), (ts, S_COL)]:
            if tt:
                ax.plot([tt, tt], [i - 0.4, i + 0.4], color=col, lw=1.6 * w / 1920)
    ax.set_xlim(-30, 1200)
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.grid(True, axis="x", color=GRID, lw=0.8)
    ax.set_yticks([])
    ax.tick_params(colors=MUTED, labelsize=10 * w / 1920)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("seconds after origin", color=MUTED, family=EN, fontsize=11 * w / 1920)
    fs = w / 1920
    fig.text(0.06, 0.94, "M7.1  off Sabah  ·  2026-02-22 16:57 UTC  ·  depth 629 km", color=TEXT, family=EN,
             fontsize=20 * fs, weight="bold")
    fig.text(0.90, 0.94, "P-wave", color=P_COL, family=EN, fontsize=16 * fs, weight="bold", ha="right")
    fig.text(0.96, 0.94, "S-wave", color=S_COL, family=EN, fontsize=16 * fs, weight="bold", ha="right")
    fig.text(0.06, 0.03, "Vertical (BHZ), 0.05–1 Hz · Data: EarthScope (IRIS DMC) – networks II, IC, HK, AU, IU · "
             "Event: USGS us6000sasz · Arrivals: iasp91", color=MUTED, family=EN, fontsize=9 * fs)
    path = OUT / f"screen-record-section-{w}x{h}.png"
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path


def helicorder(w, h):
    net, sta, loc = HELI
    t0 = ORIGIN - 1800
    tr = fetch(net, sta, loc, t0, t0 + 3 * 3600, "heli")
    if tr is None:
        return None
    tr.detrend("demean").taper(0.01).filter("bandpass", freqmin=0.5, freqmax=5.0, corners=4)
    line_s, n = 10 * 60, 18
    fig = fig_px(w, h)
    ax = fig.add_axes([0.06, 0.08, 0.9, 0.82])
    ax.set_facecolor(BG)
    data, sr = tr.data.astype(float), tr.stats.sampling_rate
    off = int((tr.stats.starttime - t0) * sr)
    clip = np.percentile(np.abs(data), 50) * 12   # drum-recorder look: noise visible, the quake saturates
    for i in range(n):
        a, b = i * line_s * sr - off, (i + 1) * line_s * sr - off
        seg = data[max(int(a), 0):max(int(b), 0)]
        if not len(seg):
            continue
        y = np.clip(seg / clip, -1.6, 1.6)
        x = np.arange(len(seg)) / sr / 60
        ax.plot(x, -i + 0.42 * y, color=TRACE if i % 2 == 0 else TRACE2, lw=0.5)
        ax.text(-0.3, -i, (t0 + i * line_s).strftime("%H:%M"), color=MUTED, family=EN, fontsize=10 * w / 1920,
                ha="right", va="center")
    ax.set_xlim(0, 10)
    ax.set_ylim(-n + 0.3, 1)
    ax.axis("off")
    fs = w / 1920
    fig.text(0.06, 0.94, f"{net}.{sta}  BHZ  ·  2026-02-22 UTC", color=TEXT, family=EN, fontsize=20 * fs,
             weight="bold")
    fig.text(0.06, 0.03, "M7.1 off Sabah (USGS us6000sasz) · Data: EarthScope (IRIS DMC), HK network · 0.5–5 Hz · 10 min per line", color=MUTED, family=EN,
             fontsize=9 * fs)
    path = OUT / f"screen-helicorder-{w}x{h}.png"
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for w, h in [(1920, 1080), (2560, 1440)]:
        for fn in (record_section, helicorder):
            p = fn(w, h)
            print(p)


if __name__ == "__main__":
    main()
