// gs.js — the channel's brand kit for render(t) shots.
// Coordinates and sizes are 1080p design pixels (landscape 1920×1080, portrait 1080×1920); S.u scales them to the
// render size. Text `size` = visible capital / CJK glyph height in design px.
// The look comes from two places, both set by the player before any shot is drawn:
//   the house style   kit/themes.json entry named by edl.CARD_THEME or studio.toml [style] house
//   the channel       studio.toml [channel] + [palette] (name, presenter, labels, logo files, the CHANNEL look)
import { clamp, lerp, ease, glide, loadImage } from './motion.js';

export const FONT = { sans: 'K Sans', label: 'K Label', mono: 'K Mono', hand: 'K Hand' };
const EM = 1 / 0.9;            // font em per visible glyph height
const fontCss = (font = 'sans', size = 40, weight = 500, italic = false) =>
  `${italic ? 'italic ' : ''}${weight} ${size * EM}px "${FONT[font] || font}", "K Sans", sans-serif`;
export const FONT_SPECS = [
  fontCss('sans', 40, 500), fontCss('sans', 40, 700), fontCss('sans', 40, 900), fontCss('label', 40, 500),
  fontCss('label', 40, 700), fontCss('mono', 40, 400), fontCss('mono', 40, 700), fontCss('hand', 40, 700),
];

// ── house style + channel ──
let THEMES = {}, CH = {}, TH = null;
/** The CHANNEL look: built from studio.toml [palette] (the channel's own colours). */
function channelTheme() {
  const p = CH.palette || {};
  return { bg: p.bg || '#1A160C', bg2: p.bg_deep || '#131008', card: p.card || '#231E10', text: p.text || '#F5F1E8',
    muted: p.muted || '#CBBC90', accent: p.accent || '#F2B90D', accentDeep: p.accent_deep || '#8A6400',
    onAccent: p.bg || '#1A160C', ink: p.text || '#F5F1E8', ground: 'flat', plate: 'bar', titleFont: 'sans' };
}
export function setup(themes, channel) { THEMES = themes || {}; CH = channel || {}; }
/** Pick the house style for the brand pieces (unknown id = the CHANNEL look). */
export function useTheme(id) { TH = { ...channelTheme(), ...((id && THEMES[id]) || {}) }; return TH; }
/** The current house style: { bg, bg2, card, text, muted, accent, accentDeep, onAccent, ink, ground, plate, titleFont }. */
export const theme = () => TH || useTheme(null);
export const channel = () => CH;
const th = key => theme()[key];

// ── time ──
/** 0 → 1 smoothstep between t0 and t0 + d. */
export const ramp = (t, t0, d = 0.4) => { const a = clamp((t - t0) / d); return a * a * (3 - 2 * a); };
/** Visibility of something that appears at tIn (fade d) and optionally leaves at tOut. Exits are quicker. */
export function vis(t, tIn, d = 0.4, tOut = null, dOut = 0.25) {
  return ramp(t, tIn, d) * (tOut == null ? 1 : 1 - ramp(t, tOut, dOut));
}
/** Shot-local time when `words` are spoken: found in the shot's subtitles (S.cues = [a, b, text], the director's
 *  corrected subtitles) and placed by character position inside that subtitle; at = 0 start of the words, 1 their end.
 *  Fails loudly, so a typo is caught on render. */
export function say(S, words, at = 0) {
  const clean = s => s.replace(/[\s,，.。!！?？;；:：、"“”'‘’/()（）]/g, '').toLowerCase();
  const w = clean(words);
  for (const [a, b, line] of S.cues || []) {
    const z = clean(line), i = z.indexOf(w);
    if (i >= 0) return a + (b - a) * (i + at * w.length) / Math.max(1, z.length);
  }
  throw new Error(`${S.id}: "${words}" is not in this shot's subtitles (${(S.cues || []).map(c => c[2]).join(' | ')})`);
}
/** A beat from edl.py (hand-set, shot-local seconds). Missing names throw. */
export function beat(S, name) {
  if (!(name in S.beats)) throw new Error(`${S.id}: no beat "${name}" (have: ${Object.keys(S.beats).join(', ')})`);
  return S.beats[name];
}

// ── drawing helpers (all take S, the shot context) ──
function withAlpha(ctx, a, fn) { if (a <= 0.001) return; ctx.save(); ctx.globalAlpha *= a; fn(); ctx.restore(); }

/** Draw text at design (x, y). Returns { w, h } in design px. align: left|center|right; y = baseline. */
export function text(S, s, x, y, { font = 'sans', size = 40, weight = 500, italic = false, color = th('text'), align = 'left',
  alpha = 1, baseline = 'alphabetic', dx = 0, dy = 0 } = {}) {
  const { ctx, u } = S;
  ctx.font = fontCss(font, size * u, weight, italic);
  const w = ctx.measureText(s).width / u;
  withAlpha(ctx, alpha, () => {
    ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = baseline;
    ctx.fillText(s, (x + dx) * u, (y + dy) * u);
  });
  return { w, h: size };
}
export function measure(S, s, { font = 'sans', size = 40, weight = 500, italic = false } = {}) {
  S.ctx.font = fontCss(font, size * S.u, weight, italic);
  return S.ctx.measureText(s).width / S.u;
}
export function rect(S, x, y, w, h, color, { r = 0, alpha = 1, stroke = null, lw = 3 } = {}) {
  const { ctx, u } = S;
  withAlpha(ctx, alpha, () => {
    ctx.beginPath(); ctx.roundRect(x * u, y * u, w * u, h * u, r * u);
    if (color) { ctx.fillStyle = color; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw * u; ctx.stroke(); }
  });
}

export const title = (S, s, x, y, o = {}) => text(S, s, x, y, { font: th('titleFont'), weight: 900, size: 72, ...o });
/** Small upper-case kicker in the label font, with an optional second part in the body font. */
export function kicker(S, en, x, y, { zh = null, size = 24, color = th('accent'), alpha = 1, dx = 0 } = {}) {
  const a = text(S, en, x, y, { font: 'label', weight: 700, size, color, alpha, dx });
  if (zh) text(S, zh, x + a.w + size * 0.6, y, { font: 'sans', weight: 700, size, color, alpha, dx });
}
/** A Latin term + its local-language word side by side (the label font may have no CJK glyphs). */
export function mixed(S, en, zh, x, y, { size = 30, color = th('text'), zhColor = th('text'), alpha = 1 } = {}) {
  const a = text(S, en, x, y, { font: 'label', weight: 700, size, color, alpha });
  text(S, zh, x + a.w + size * 0.35, y, { font: 'sans', weight: 700, size, color: zhColor, alpha });
}
/** Label chip: text on a rounded box. (x, y) = box top-left unless align is center/right. Returns the box. */
export function chip(S, s, x, y, { size = 30, font = 'sans', weight = 700, color = th('text'), bg = th('bg2'), opacity = 0.8,
  pad = 12, align = 'left', alpha = 1, dx = 0, dy = 0 } = {}) {
  const w = measure(S, s, { font, size, weight }) + pad * 2, h = size * 1.25 + pad * 2;
  const x0 = (align === 'center' ? x - w / 2 : align === 'right' ? x - w : x) + dx, y0 = y + dy;
  rect(S, x0, y0, w, h, bg, { r: 8, alpha: alpha * opacity });
  text(S, s, x0 + pad, y0 + pad + size * 1.02, { font, size, weight, color, alpha });
  return { x: x0, y: y0, w, h };
}
/** Feature label: accent bar + name + a second line (a term, a translation). (x, y) = top-left of the bar. */
export function label(S, main, second, x, y, { color = th('accent'), textColor = th('text'), alpha = 1, dx = 0 } = {}) {
  const h = 34 + 8 + 24;
  rect(S, x + dx, y, 6, h + 6, color, { alpha });
  text(S, main, x + 20 + dx, y + 34, { size: 34, weight: 700, color: textColor, alpha });
  if (second) text(S, second, x + 20 + dx, y + h + 4, { font: 'label', size: 24, weight: 500, color, alpha });
}

// ── brand pieces ──
const BRAND = {};
export async function loadBrand() {
  const base = new URL('../brand/', import.meta.url).href;
  BRAND.mark = CH.watermark ? await loadImage(base + 'watermark.png') : null;
  BRAND.seal = CH.seal ? await loadImage(base + 'seal.png') : null;
}
export function image(S, img, x, y, w, h = w * img.height / img.width, { alpha = 1 } = {}) {
  withAlpha(S.ctx, alpha, () => S.ctx.drawImage(img, x * S.u, y * S.u, w * S.u, h * S.u));
}
/** Watermark top-right: the channel's logo file, or its short name when there is none. */
export function watermark(S, { opacity = 0.7, size = 60 } = {}) {
  if (BRAND.mark) image(S, BRAND.mark, S.DW - 36 - size, 36, size, size, { alpha: opacity });
  else if (CH.shortName) text(S, CH.shortName, S.DW - 36, 36 + size * 0.55, { font: 'label', size: size * 0.42, weight: 700, color: th('muted'), align: 'right', alpha: opacity });
}
/** Data source credit: top-right, left of the watermark (the bottom belongs to the subtitles). */
export function sourceNote(S, s, { alpha = 1, color = th('muted') } = {}) {
  text(S, s, S.DW - 36 - 84, 36 + 20 + 18, { size: 18, color, align: 'right', alpha: 0.85 * alpha });
}
/** Presenter lower third. (x, y) = top-left. Show 3-5 s at the first appearance. Name and line: studio.toml. */
export function nameTag(S, x, y, { name = CH.presenter || CH.name || '', line = CH.presenterTitle || '', alpha = 1, dx = 0 } = {}) {
  const w = Math.max(measure(S, name, { size: 30, weight: 900 }), measure(S, line, { size: 20 })) + 46;
  const h = 30 + 8 + 20 + 28, plate = th('plate'), { ctx, u } = S;
  let nameC = th('text'), subC = th('muted');
  if (plate === 'outline') {                                     // thin technical frame with corner ticks
    rect(S, x + dx, y, w + 6, h, th('bg2'), { alpha: alpha * 0.82 });
    rect(S, x + dx, y, w + 6, h, null, { stroke: th('accent'), lw: 2, alpha });
    rect(S, x + dx - 5, y - 5, 12, 12, th('accent'), { alpha });
  } else if (plate === 'chalk') {                                // a hand-drawn chalk frame
    rect(S, x + dx, y, w + 6, h, th('bg2'), { r: 6, alpha: alpha * 0.8 });
    withAlpha(ctx, alpha, () => { ctx.strokeStyle = th('text'); ctx.lineWidth = 3 * u; ctx.setLineDash([18 * u, 5 * u, 40 * u, 4 * u]);
      ctx.beginPath(); ctx.roundRect((x + dx) * u, y * u, (w + 6) * u, h * u, 10 * u); ctx.stroke(); });
    nameC = th('accent');
  } else if (plate === 'block') {                                // a solid colour block, text reversed
    rect(S, x + dx + 8, y + 8, w + 6, h, th('accentDeep'), { alpha });
    rect(S, x + dx, y, w + 6, h, th('accent'), { alpha });
    nameC = th('onAccent'); subC = th('onAccent');
  } else if (plate === 'card') {                                 // a rounded card with a soft shadow
    withAlpha(ctx, alpha, () => { ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.22)'; ctx.shadowBlur = 24 * u; ctx.shadowOffsetY = 8 * u;
      ctx.fillStyle = th('card'); ctx.beginPath(); ctx.roundRect((x + dx) * u, y * u, (w + 6) * u, h * u, 18 * u); ctx.fill(); ctx.restore(); });
  } else {                                                       // bar: accent bar + dark plate (the CHANNEL look)
    rect(S, x + dx, y, 6, h, th('accent'), { alpha }); rect(S, x + 6 + dx, y, w, h, th('bg2'), { alpha: alpha * 0.85 });
  }
  text(S, name, x + 26 + dx, y + 14 + 30, { size: 30, weight: 900, color: nameC, alpha });
  text(S, line, x + 26 + dx, y + 14 + 30 + 8 + 20, { size: 20, color: subC, alpha });
}
export const seal = (S, cx, cy, size = 420, o = {}) => { if (BRAND.seal) image(S, BRAND.seal, cx - size / 2, cy - size / 2, size, size, o); };
export function playIcon(S, cx, cy, size = 26, color = th('accent'), alpha = 1) {
  const { ctx, u } = S, r = size * 0.6;
  withAlpha(ctx, alpha, () => {
    ctx.fillStyle = color; ctx.beginPath();
    ctx.moveTo((cx + r) * u, cy * u); ctx.lineTo((cx - r / 2) * u, (cy - r * 0.866) * u); ctx.lineTo((cx - r / 2) * u, (cy + r * 0.866) * u);
    ctx.closePath(); ctx.fill();
  });
}
/** Debug only (?guides=1): the subtitle band (no text there). */
export function guides(S) {
  const { ctx, u } = S, y = S.vertical ? 1360 : 880;
  ctx.save(); ctx.fillStyle = 'rgba(255,0,0,0.18)'; ctx.fillRect(0, y * u, S.W, S.H - y * u); ctx.restore();
}

// ── chapter card and end card (one function = one shot) ──
/** Chapter card (also a YouTube chapter): big number + CHAPTER n + the question + a rule + an optional second line. */
export function chapterCard(S, { number, title: ttl, en = '' }) {
  return t => {
    bg(S, th('bg')); const TF = th('titleFont');
    const numW = measure(S, String(number).padStart(2, '0'), { font: 'label', size: 160, weight: 700 });
    const fs = Math.min(84, 84 * (S.DW - 240 - numW - 60) / measure(S, ttl, { font: TF, size: 84, weight: 900 }));
    const tw = Math.max(measure(S, ttl, { font: TF, size: fs, weight: 900 }), 520);
    const x0 = (S.DW - (numW + 60 + tw)) / 2, cy = S.DH / 2;
    const a = vis(t, 0, 0.4), b = vis(t, 0.2, 0.5);
    text(S, String(number).padStart(2, '0'), x0, cy + 80, { font: 'label', size: 160, weight: 700, color: th('accentDeep'), alpha: a, dx: -30 * (1 - glide(a)) });
    const rx = x0 + numW + 60, dx = 30 * (1 - glide(b));
    kicker(S, `${CH.chapter || 'CHAPTER'} ${number}`, rx, cy - 86, { size: 26, alpha: b, dx });
    text(S, ttl, rx, cy + 14, { font: TF, size: fs, weight: 900, color: th('text'), alpha: b, dx });
    rect(S, rx + dx, cy + 40, 520, 3, th('accent'), { alpha: b });
    if (en) text(S, en, rx, cy + 104, { font: 'label', size: 34, weight: 500, color: th('muted'), alpha: b, dx });
    watermark(S);
  };
}

// YouTube Studio end-screen editor, measured at 1080p (±4 px): elements snap into its guide lines.
export const ES_SAFE = [40, 136, 1876, 916], ES_VIDEO = [628, 353], ES_SUBSCRIBE = 304;
export function esSlots() {
  const [l, t, r, b] = ES_SAFE, [w, h] = ES_VIDEO;
  return { A: [r - w, t, r, t + h], B: [r - w, b - h, r, b], subscribe: [l, b - ES_SUBSCRIBE, l + ES_SUBSCRIBE, b] };
}
/** End card = the YouTube end screen (keep the shot 12 s). Slots match esSlots() exactly; the bottom-left slot stays
 *  empty for YouTube's own subscribe element. ask = one question for the comments, 1-2 short lines. */
export function endCard(S, { ask = [], series = '', frameLabels = [CH.watch || 'Watch next', ''], logo = false } = {}) {
  const slots = esSlots();
  return t => {
    bg(S, th('bg2'));
    const k = vis(t, 0, 0.4), l = vis(t, 0.3, 0.5), sub = vis(t, 0.7, 0.5), side = vis(t, 1.0, 0.5);
    let y = 300 - (ask.length * 82 + 100) / 2 + 28;
    if (ask.length) {
      kicker(S, 'COMMENT', 120, y, { zh: CH.comment || '', size: 28, alpha: k, dx: -30 * (1 - glide(k)) });
      for (const line of ask) { y += 82; title(S, line, 120, y, { size: 60, color: th('text'), alpha: l, dx: -30 * (1 - glide(l)) }); }
    }
    if (series) text(S, series, 120, y + 60, { size: 30, color: th('muted'), alpha: sub });
    const [sx0, sy0, sx1, sy1] = slots.subscribe;
    if (logo) seal(S, (sx0 + sx1) / 2, (sy0 + sy1) / 2, ES_SUBSCRIBE);
    const bx = sx1 + 44, by = (sy0 + sy1) / 2 - 60;
    rect(S, bx, by, 260, 66, th('accent'), { r: 10, alpha: side });
    text(S, CH.subscribe || 'Subscribe', bx + 130, by + 46, { size: 28, weight: 700, color: th('onAccent'), align: 'center', alpha: side });
    if (CH.website) text(S, CH.website, bx, by + 66 + 18 + 22, { font: 'label', size: 22, color: th('muted'), alpha: side });
    ['A', 'B'].forEach((key, i) => {
      const [x0, y0, x1, y1] = slots[key], a = vis(t, 1.2 + 0.3 * i, 0.5), dx = 30 * (1 - glide(a));
      rect(S, x0 - dx, y0, x1 - x0, y1 - y0, th('card'), { r: 12, stroke: th('accent'), lw: 3, alpha: a });
      playIcon(S, (x0 + x1) / 2 - dx, (y0 + y1) / 2, 56, th('muted'), a);
      text(S, frameLabels[i] || '', x0 - dx, y0 - 10, { size: 24, weight: 700, color: th('accent'), alpha: a });
    });
  };
}

/** Fill the whole frame (full-screen shots). Camera CG shots never call this: they stay transparent. */
export function bg(S, color = th('bg')) { S.ctx.save(); S.ctx.fillStyle = color; S.ctx.fillRect(0, 0, S.W, S.H); S.ctx.restore(); }
export { clamp, lerp, ease, glide };
