// intro.js — the channel intro (4.2 s), drawn in the house style. A starting point: the logo (or the channel's short
// name) lands on a rule that draws itself across the frame, then the channel name and the tagline come in.
// Make it your own: this is the one shot every video shares, so Claude can redesign it with you once
// ("redesign the intro around my logo and show me a preview").
import { seg, ease } from './motion.js';
import { theme, channel, text, rect, seal, bg } from './gs.js';
import { styleBg } from './house.js';

export const INTRO_T = { mark: 0.2, rule: 0.7, title: 1.3, tagline: 1.8, end: 4.2 };

export default async function intro(S) {
  return t => {
    const T = theme(), C = channel(), cx = S.DW / 2, cy = S.DH / 2;
    if (T.ground === 'flat') bg(S, T.bg); else styleBg(S);
    const m = ease.outCubic(seg(t, INTRO_T.mark, INTRO_T.mark + 0.6));
    const r = ease.inOutCubic(seg(t, INTRO_T.rule, INTRO_T.rule + 0.7));
    const a = ease.outCubic(seg(t, INTRO_T.title, INTRO_T.title + 0.5));
    const g = ease.outCubic(seg(t, INTRO_T.tagline, INTRO_T.tagline + 0.5));
    const out = 1 - ease.inCubic(seg(t, INTRO_T.end - 0.35, INTRO_T.end));
    const top = S.vertical ? cy - 330 : cy - 250;
    if (C.seal) seal(S, cx, top + 130 - 40 * (1 - m), 260, { alpha: m * out });
    else text(S, C.shortName || (C.name || '').slice(0, 2), cx, top + 190 - 40 * (1 - m), { font: 'label', size: 170, weight: 700, color: T.accent, align: 'center', alpha: m * out });
    const w = Math.min(S.DW - 240, 760) * r;
    rect(S, cx - w / 2, top + 290, w, 4, T.accent, { alpha: out });
    const name = C.name || '';
    const fs = Math.min(96, 96 * (S.DW - 200) / Math.max(1, name.length * 96 * (C.cjk ? 1.05 : 0.6)));
    text(S, name, cx, top + 290 + 40 + fs + 20 * (1 - a), { font: T.titleFont, size: fs, weight: 900, color: T.text, align: 'center', alpha: a * out });
    if (C.tagline) text(S, C.tagline, cx, top + 290 + 40 + fs + 70, { font: 'label', size: 34, weight: 500, color: T.muted, align: 'center', alpha: g * out });
  };
}
