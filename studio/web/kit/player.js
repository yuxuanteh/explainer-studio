// player.js — runs one or more shots as a single render(t) page (motion-showreel page contract).
// gs_web.py writes the page with window.GS_SPEC and imports this file. A shot module lives at
//   ep/<EP>/shots/<id>.js  (anim / chapter / card)   or   ep/<EP>/cam/<id>.js  (CG over a camera shot)
// and exports   default async function (S) { ...load assets...; return t => { ...draw frame at shot time t... } }
// S = { id, kind, ep, W, H, DW, DH, u, ctx, dur, beats, cues, vertical, matte, review, style, q (URL params), img(path) }.
// Rules: the picture depends on t only. No Math.random / Date.now / rAF / timers / CSS animation,
// no state kept between frames. Seeded noise: motion.js rng / hash / noise2.
import { stageSize, setupCanvas, loadFonts, loadImage } from './motion.js';
import { FONT_SPECS, loadBrand, guides, useTheme, setup } from './gs.js';

const spec = window.GS_SPEC;
const q = new URLSearchParams(location.search);
const matte = q.get('matte') === '1' || !!spec.matte;   // camera CG alpha pass: white where CG is, black elsewhere
const showGuides = q.get('guides') === '1';
const { W, H } = stageSize();
const ctx = setupCanvas(document.getElementById('c'), W, H);
const DW = spec.vertical ? 1080 : 1920, DH = spec.vertical ? 1920 : 1080, u = W / DW;

// spec.cardTheme = the house style (kit/themes.json), spec.channel = studio.toml [channel] + [palette]. Both are set
// before every shot is built and drawn, so brand pieces (cards, name tag, kicker, source note) follow them without
// each module asking.
const themes = await (await fetch(new URL('./themes.json', import.meta.url))).json();
setup(themes, spec.channel || {});
await Promise.all([loadFonts(FONT_SPECS), loadBrand()]);
useTheme(spec.cardTheme || null);
const base = new URL(`../ep/${spec.ep}/`, import.meta.url).href;
const shots = [];
for (const s of spec.shots) {
  const S = { ...s, ep: spec.ep, W, H, DW, DH, u, ctx, vertical: !!spec.vertical, matte, review: !!spec.review, q, style: spec.cardTheme || null,
              img: p => loadImage(base + p) };
  const mod = await import(base + s.module + (spec.bust ? `?v=${spec.bust}` : ''));
  const draw = await mod.default(S);
  if (typeof draw !== 'function') throw new Error(`${s.module}: default export must return t => draw`);
  const camBg = spec.review && s.kind === 'cam' && s.camStill ? await loadImage(base + s.camStill) : null;
  shots.push({ S, draw, camBg });
}

window.DUR = spec.shots.reduce((a, s) => a + s.dur, 0);
window.render = t => {
  let i = shots.findIndex(x => t < x.S.t0 + x.S.dur);
  if (i < 0) i = shots.length - 1;
  const { S, draw, camBg } = shots[i];
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height); ctx.restore();
  useTheme(spec.cardTheme || null);
  ctx.save(); draw(Math.min(Math.max(t - S.t0, 0), S.dur)); ctx.restore();
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  if (S.kind === 'cam' && matte) {                // alpha matte: keep coverage, drop colour
    ctx.globalCompositeOperation = 'source-in'; ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    ctx.globalCompositeOperation = 'destination-over'; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  } else if (camBg) {                              // review only: a still of the camera clip behind the CG
    ctx.globalCompositeOperation = 'destination-over'; ctx.drawImage(camBg, 0, 0, ctx.canvas.width, ctx.canvas.height);
  }
  ctx.restore();
  if (showGuides) guides(S);
};
window.render(0);
window.READY = true;
