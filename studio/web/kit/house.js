// house.js — drawing pieces that follow the house style (kit/themes.json; set by the player from edl.CARD_THEME or
// studio.toml [style] house). Everything here is deterministic (seeded hash only). Sizes are 1080p design px.
// Add your own pieces here when your style needs them (a texture, a symbol set, a frame for photos).
import { theme, text } from './gs.js';

const hash = (i, j = 0) => { const s = Math.sin(i * 127.1 + j * 311.7) * 43758.5453; return s - Math.floor(s); };
const CACHE = new Map();

/** The style's ground, full frame: call it first in every full-screen shot instead of bg().
 *  ground: grid (fine drawing grid) · dust (chalk dust on a board) · paper (grain) · flat. */
export function styleBg(S) {
  const T = theme(), { ctx } = S;
  const key = `${T.bg}:${T.ground}:${S.W}x${S.H}`;
  if (!CACHE.has(key)) {
    const c = new OffscreenCanvas(S.W, S.H), g = c.getContext('2d'), u = S.u;
    g.fillStyle = T.bg; g.fillRect(0, 0, S.W, S.H);
    if (T.ground === 'grid') {
      for (let x = 0, k = 0; x <= S.DW; x += 40, k++) { g.fillStyle = k % 5 ? 'rgba(255,255,255,0.045)' : 'rgba(255,255,255,0.10)'; g.fillRect(x * u, 0, Math.max(1, u), S.H); }
      for (let y = 0, k = 0; y <= S.DH; y += 40, k++) { g.fillStyle = k % 5 ? 'rgba(255,255,255,0.045)' : 'rgba(255,255,255,0.10)'; g.fillRect(0, y * u, S.W, Math.max(1, u)); }
    } else if (T.ground === 'dust') {
      for (let i = 0; i < 900; i++) {                          // wiped chalk: long faint smears
        const x = hash(i, 1) * S.W, y = hash(i, 2) * S.H, w = (120 + hash(i, 3) * 380) * u;
        g.fillStyle = `rgba(255,255,255,${0.006 + hash(i, 4) * 0.012})`; g.fillRect(x - w / 2, y, w, (6 + hash(i, 5) * 22) * u);
      }
      for (let i = 0; i < 22000; i++) { g.fillStyle = 'rgba(255,255,255,0.035)'; g.fillRect(hash(i, 6) * S.W, hash(i, 7) * S.H, 2 * u, 2 * u); }
    } else if (T.ground === 'paper') {
      for (let i = 0; i < 26000; i++) {
        g.fillStyle = hash(i, 3) > 0.5 ? 'rgba(255,255,255,0.05)' : 'rgba(60,45,20,0.035)';
        g.fillRect(hash(i, 1) * S.W, hash(i, 2) * S.H, 2 * u, 2 * u);
      }
    }
    CACHE.set(key, c);
  }
  ctx.drawImage(CACHE.get(key), 0, 0);
}

const path = (S, pts, close) => { const { ctx, u } = S; ctx.beginPath(); pts.forEach(([x, y], i) => ctx[i ? 'lineTo' : 'moveTo'](x * u, y * u)); if (close) ctx.closePath(); };
/** A polyline in the style's ink. `draw` 0 → 1 draws it on (for a line that appears as it is spoken). */
export function line(S, pts, { color = theme().ink, w = 3, alpha = 1, dash = null, close = false, draw = 1 } = {}) {
  const { ctx, u } = S;
  if (draw <= 0) return;
  let p = pts;
  if (draw < 1) {                                               // cut the polyline at `draw` of its length
    const seg = pts.slice(1).map((q, i) => Math.hypot(q[0] - pts[i][0], q[1] - pts[i][1]));
    let left = seg.reduce((a, b) => a + b, 0) * draw; p = [pts[0]];
    for (let i = 0; i < seg.length && left > 0; i++) {
      const k = Math.min(1, left / seg[i]);
      p.push([pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k]); left -= seg[i];
    }
  }
  ctx.save(); ctx.globalAlpha *= alpha; path(S, p, close && draw >= 1); ctx.strokeStyle = color; ctx.lineWidth = w * u; ctx.lineJoin = ctx.lineCap = 'round';
  if (dash) ctx.setLineDash(dash.map(d => d * u)); ctx.stroke(); ctx.restore();
}
/** A filled polygon (a region, a layer, a block). */
export function fill(S, pts, color = theme().card, { alpha = 1, stroke = null, w = 3 } = {}) {
  const { ctx, u } = S; ctx.save(); ctx.globalAlpha *= alpha; path(S, pts, true); ctx.fillStyle = color; ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = w * u; ctx.lineJoin = 'round'; ctx.stroke(); } ctx.restore();
}
/** Run fn clipped to a polygon (design px). */
export function inside(S, poly, fn) { S.ctx.save(); path(S, poly, true); S.ctx.clip(); fn(); S.ctx.restore(); }
/** A dot with an optional ring: "this point". */
export function dot(S, x, y, r = 10, { color = theme().accent, alpha = 1, ring = 0 } = {}) {
  const { ctx, u } = S; ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = ctx.strokeStyle = color;
  ctx.beginPath(); ctx.arc(x * u, y * u, r * u, 0, Math.PI * 2); ctx.fill();
  if (ring) { ctx.lineWidth = 3 * u; ctx.beginPath(); ctx.arc(x * u, y * u, (r + ring) * u, 0, Math.PI * 2); ctx.stroke(); }
  ctx.restore();
}
/** An arrow from a to b in the accent colour. */
export function arrow(S, [x0, y0], [x1, y1], { color = theme().accent, w = 4, alpha = 1, head = 18, draw = 1 } = {}) {
  const k = Math.max(0, Math.min(1, draw)), ex = x0 + (x1 - x0) * k, ey = y0 + (y1 - y0) * k, a = Math.atan2(y1 - y0, x1 - x0);
  if (k <= 0) return;
  line(S, [[x0, y0], [ex, ey]], { color, w, alpha });
  line(S, [[ex - head * Math.cos(a - 0.45), ey - head * Math.sin(a - 0.45)], [ex, ey], [ex - head * Math.cos(a + 0.45), ey - head * Math.sin(a + 0.45)]], { color, w, alpha });
}
/** A label beside its subject with a leader line to the point `to`: main line + an optional second line. */
export function note(S, main, second, x, y, to, { color = theme().ink, alpha = 1, size = 30 } = {}) {
  if (to) line(S, [[x - 10, y - size * 0.35], to], { color, w: 2, alpha: alpha * 0.8 });
  text(S, main, x, y, { size, weight: 700, color, alpha, font: theme().titleFont === 'hand' ? 'hand' : 'sans' });
  if (second) text(S, second, x, y + size * 0.95, { size: size * 0.7, color: theme().muted, alpha, font: 'label' });
}
/** A photo in a frame that fits the style (white border and a small tilt), with a credit line under it. */
export function photo(S, img, x, y, w, { caption = '', tilt = 0, alpha = 1 } = {}) {
  const { ctx, u } = S, h = w * img.height / img.width, T = theme();
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate((x + w / 2) * u, (y + h / 2) * u); ctx.rotate(tilt);
  ctx.shadowColor = 'rgba(0,0,0,0.3)'; ctx.shadowBlur = 18 * u; ctx.shadowOffsetY = 6 * u;
  ctx.fillStyle = T.card; ctx.fillRect((-w / 2 - 10) * u, (-h / 2 - 10) * u, (w + 20) * u, (h + 20 + (caption ? 34 : 0)) * u);
  ctx.shadowColor = 'transparent'; ctx.drawImage(img, -w / 2 * u, -h / 2 * u, w * u, h * u);
  if (caption) { ctx.fillStyle = T.muted; ctx.font = `500 ${18 * u}px "K Sans", sans-serif`; ctx.textAlign = 'left'; ctx.fillText(caption, -w / 2 * u, (h / 2 + 30) * u); }
  ctx.restore();
}
