"""Voice cut: the stop before any animation is made.

    python gs_voicecut.py <EPISODE> [short]     -> preview/<EP>-voicecut-480p.mp4 (short: preview/short-voicecut.mp4)
                                                   + work/review/<name>.timeline.json for the review page

The director checks pacing, retakes and subtitles here, while a change costs nothing: the voice as cut (gs_cut.py or
a hand-filled edl.py), burned subtitles, the real camera shots, and a plain card wherever animation will
go (shot id + the words said there). No music, no stings, no CG. Once approved, shot lengths are locked and the
animation is made to them.
"""
import json
import shutil
import sys

from PIL import Image, ImageDraw, ImageFont

import gs_env
import gs_episode as G
import gs_cut

LABEL = {"anim": gs_env.tr("animation goes here", "动画位置"), "chapter": gs_env.tr("chapter card", "章节卡"), "intro": gs_env.tr("intro", "片头"),
         "card": gs_env.tr("end card", "片尾卡"), "foot": gs_env.tr("own footage", "实拍画面"), "screen": gs_env.tr("screen recording", "屏幕录影")}


def wrap(d, text, font, width):
    lines, cur = [], ""
    for ch in (text if gs_env.CJK else [w + " " for w in text.split()]):   # words stay whole outside Chinese / Japanese
        if cur and d.textlength(cur + ch, font=font) > width:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    return lines + ([cur] if cur else [])


def card(path, W, H, sid, kind, words):
    """A plain placeholder: which shot, what kind, and what is being said (so the cut can be judged by ear)."""
    im = Image.new("RGB", (W, H), "#1D1E21")
    d = ImageDraw.Draw(im)
    fs = gs_env.subtitle_fonts()
    f = lambda px, w="Bold": ImageFont.truetype(str(gs_env.FONTS / (fs[-1] if w == "Black" else fs[0])), px)  # noqa: E731
    u = min(W, H) / 480
    d.text((int(28 * u), int(24 * u)), sid, font=f(int(46 * u), "Black"), fill="#F2B90D")
    d.text((int(28 * u), int(84 * u)), LABEL.get(kind, kind), font=f(int(22 * u)), fill="#8E8A80")
    y = int(150 * u)
    for line in wrap(d, words, f(int(20 * u), "Medium"), W - int(56 * u))[:9]:
        d.text((int(28 * u), y), line, font=f(int(20 * u), "Medium"), fill="#C9C5BA")
        y += int(30 * u)
    im.save(path)


def build(E, short=False):
    S = G.short_edl(E) if short else E
    S.VOICECUT, S.MUSIC = True, False
    vertical = bool(short and E.SHORT_VERTICAL)
    W, H = (480, 854) if vertical else (854, 480)
    name = "short-voicecut" if short else f"{E.EPISODE}-voicecut-480p"
    B = E.RENDER / ("build-voicecut-short" if short else "build-voicecut")
    (B / "fonts").mkdir(parents=True, exist_ok=True)
    for f in G.theme_fonts(E):
        shutil.copy(gs_env.FONTS / f, B / "fonts")
    tl = G.timeline(S)
    words = {sid: " ".join(lines) for sid, _, lines in gs_cut.script(E.EPISODE)}
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-an"]
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={G.FPS}"
    clips = []
    for s in tl:
        out, dur = B / f"{s['id']}.mp4", f"{s['dur']:.3f}"
        if s["kind"] == "cam":
            pre = E.CAM_FRAME.get(s["src"], "")
            parts = []
            for k, (a, b) in enumerate(G.pieces(s)):          # a removed take inside a camera shot: alternate punch-in
                z = G.CAM_ZOOM if k % 2 else 1.0
                zf = (f",crop=iw/{z}:ih/{z}:iw*{G.CAM_ZOOM_CENTRE[0]}-iw/{z}/2:ih*{G.CAM_ZOOM_CENTRE[1]}-ih/{z}/2" if z != 1.0 else "")
                pf = B / f"{s['id']}-p{k}.mp4"
                G.ff("-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", E.SRC[s["src"]], "-vf",
                     f"{pre + ',' if pre else ''}{E.CAM_GRADE}{zf},{fit}", *enc, pf)
                parts.append(pf)
            (B / f"{s['id']}-parts.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
            G.ff("-f", "concat", "-safe", "0", "-i", B / f"{s['id']}-parts.txt", "-vf",
                 f"tpad=stop_mode=clone:stop_duration=2", "-t", dur, *enc, out)
        else:
            png = B / f"{s['id']}.png"
            card(png, W, H, s["id"], s["kind"], words.get(s["id"], ""))
            G.ff("-loop", "1", "-framerate", G.FPS, "-t", dur, "-i", png, "-vf", f"fps={G.FPS}", *enc, out)
        clips.append(out)
    (B / "concat.txt").write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    G.ff("-f", "concat", "-safe", "0", "-i", B / "concat.txt", "-c", "copy", B / "video.mp4")
    G._mix(S, B, tl)
    cs = G.cues(S)
    if vertical:
        head = G.themed(E, G.SHORT_ASS_HEAD)
        ev = [f"Dialogue: 0,{G.ass_time(a)},{G.ass_time(b)},Sub,,0,0,0,,{{\\pos(540,1380)}}{G.gold(E, zh)}" for a, b, zh, *_ in cs]
    else:
        head = G.themed(E, G.ass_head()).rstrip() + "\n"
        ev = [f"Dialogue: 0,{G.ass_time(a)},{G.ass_time(b)},A,,0,0,0,,{G.gold(E, zh)}" for a, b, zh, *_ in cs]
    (B / "subs.ass").write_text(head + "\n".join(ev) + "\n", encoding="utf-8")
    outdir = E.EP_DIR / "preview"
    outdir.mkdir(exist_ok=True)
    dst = outdir / f"{name}.mp4"
    G.ff("-i", "video.mp4", "-i", "mix.wav", "-vf", "subtitles=subs.ass:fontsdir=fonts", "-c:v", "libx264", "-preset",
         "medium", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-af",
         G.loudnorm_linear(B / "mix.wav", -14), "-shortest", "-movflags", "+faststart", dst, cwd=B)
    rv = E.EP_DIR / "work" / "review"
    rv.mkdir(parents=True, exist_ok=True)
    (rv / f"{name}.timeline.json").write_text(json.dumps({
        "id": E.EPISODE, "name": name, "file": dst.name, "total": round(tl[-1]["end"], 3), "vertical": vertical,
        "shots": [{"id": s["id"], "kind": s["kind"], "t": round(s["start"], 3), "d": round(s["dur"], 3), "src": s["src"],
                   "in": s["in"], "out": s["out"], "cut": s["cut"]} for s in tl],
        "subs": [{"s": round(a, 3), "e": round(b, 3), "text": zh} for a, b, zh, *_ in cs]}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(dst, f"({tl[-1]['end']:.1f}s, {len(tl)} shots, {len(cs)} subtitles)")
    return dst


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    E = G.load(sys.argv[1])
    build(E, short=(sys.argv[2:3] == ["short"] or not E.SHOTS))
