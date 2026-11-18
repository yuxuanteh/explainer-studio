// demo.js — one sample shot that shows a house style at work: ground, title, a small labelled diagram, a chip, the
// name tag, the source note, the watermark and a subtitle line. `gs_styles.py preview` renders it under every style
// so the looks can be compared side by side. Also a small worked example of how a shot module is written.
import { vis, glide, text, kicker, title, chip, nameTag, sourceNote, watermark, theme, channel, rect } from './gs.js';
import { styleBg, line, fill, arrow, dot, note } from './house.js';

export default async function (S) {
  const C = channel(), cjk = !!C.cjk;
  const W = cjk ? { k: 'CHAPTER 1', q: '山是怎么长高的?', a: '地壳抬升', b: '风化和侵蚀', c: '还在长高', chip: '每年几毫米', sub: '所以一座山的高度, 是两股力量拉出来的', src: '示意图' }
               : { k: 'CHAPTER 1', q: 'How does a mountain grow?', a: 'uplift', b: 'weathering and erosion', c: 'still rising', chip: 'a few mm a year', sub: 'so the height of a mountain is a tug of war between two forces', src: 'Diagram' };
  return t => {
    const T = theme(), V = S.vertical, cx = S.DW / 2;
    styleBg(S);
    const a = vis(t, 0.1, 0.5), b = vis(t, 0.6, 0.5), c = vis(t, 1.2, 0.6), d = vis(t, 2.0, 0.5);
    kicker(S, W.k, V ? 90 : 140, V ? 300 : 170, { alpha: a });
    title(S, W.q, V ? 90 : 140, V ? 400 : 260, { size: V ? 70 : 76, alpha: a, dx: -30 * (1 - glide(a)) });
    // a mountain in three layers, pushed up from below and worn down from above
    const x0 = V ? 140 : 520, base = V ? 1180 : 800, w = V ? 800 : 880, h = V ? 420 : 360;
    const peak = [x0 + w * 0.52, base - h];
    fill(S, [[x0, base], [x0 + w * 0.3, base - h * 0.55], peak, [x0 + w * 0.74, base - h * 0.5], [x0 + w, base]], T.card, { alpha: b, stroke: T.ink, w: 4 });
    line(S, [[x0 + w * 0.12, base - h * 0.2], [x0 + w * 0.45, base - h * 0.42], [x0 + w * 0.9, base - h * 0.18]], { color: T.muted, w: 3, alpha: b, draw: b });
    line(S, [[x0 + w * 0.05, base - h * 0.08], [x0 + w * 0.5, base - h * 0.2], [x0 + w * 0.96, base - h * 0.07]], { color: T.muted, w: 3, alpha: b, draw: b, dash: [14, 10] });
    arrow(S, [x0 + w * 0.5, base + 90], [x0 + w * 0.5, base + 12], { color: T.accent, w: 7, head: 26, draw: c });
    arrow(S, [peak[0] + 150, peak[1] - 110], [peak[0] + 40, peak[1] - 6], { color: T.accentDeep, w: 6, head: 22, draw: c });
    dot(S, peak[0], peak[1], 9, { color: T.accent, alpha: d, ring: 12 });
    note(S, W.a, cjk ? 'uplift' : null, x0 + w * 0.5 + 40, base + 70, null, { alpha: c });
    note(S, W.b, cjk ? 'erosion' : null, peak[0] + 170, peak[1] - 110, null, { alpha: c });
    chip(S, W.chip, peak[0] - 60, peak[1] - 84, { align: 'right', alpha: d, color: T.onAccent, bg: T.accent, opacity: 1 });
    nameTag(S, V ? 90 : 140, V ? 1500 : 640, { alpha: d, dx: -40 * (1 - glide(d)) });
    sourceNote(S, W.src);
    watermark(S);
    // the burned subtitle is added by ffmpeg in a real build; drawn here so the style sheet shows the whole look
    const sy = V ? 1420 : 990, fs = V ? 44 : 46;
    S.ctx.save(); S.ctx.lineJoin = 'round'; S.ctx.lineWidth = 9 * S.u; S.ctx.strokeStyle = T.bg2; S.ctx.textAlign = 'center';
    S.ctx.font = `500 ${fs * S.u / 0.9}px "K Sans", sans-serif`; S.ctx.strokeText(W.sub, cx * S.u, sy * S.u); S.ctx.restore();
    text(S, W.sub, cx, sy, { size: fs, weight: 500, align: 'center', color: T.text });
    rect(S, 0, 0, 0, 0, null);
  };
}
