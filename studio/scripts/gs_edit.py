"""Editing page for cuts: Claude trims first, then the director checks and fixes by ear (served by gs_review.py at
/edit). The page text is Chinese in this file; gs_i18n.page() gives the English page when [ui] language = "en".

The page shows a piece shot by shot: the waveform of the recording around the shot, lit where the cut keeps the
sound and dark where it is cut away, and the shot's subtitles as text boxes. The director can play the shot exactly
as it is cut, drag over a stretch and cut it or put it back (the start and the end of a shot move the same way), and
correct subtitle wording. Saving writes only <episode>/work/edit.json (the old file is copied to
work/review/edit-backup/ first); gs_episode.load applies it on top of the automatic cut and of edl.py, so nothing the
director fixed is ever overwritten by a rerun of gs_cut.py. "保存并重做" rebuilds the voice cut for the review page.
"""
import json
import subprocess
import sys
import time

import gs_env


def state(ep, short):
    import gs_episode as G
    E = G.load(ep)
    S = G.short_edl(E) if short else E
    cname = "SHORT_CUES" if short else "CUES"
    shots = []
    for sid, kind, src, tin, tout, hold, *_ in S.SHOTS:
        if not src:
            continue
        b = E.BASE["shots"][sid]
        shots.append(dict(id=sid, kind=kind, src=src, **{"in": tin, "out": tout}, cut=[list(c) for c in E.SQUEEZE.get(sid, [])],
                          base=dict(**{"in": b[0], "out": b[1]}, cut=b[2])))
    cues = []
    for (src, a, b, zh, en), base, g in zip(S.CUES, E.BASE[cname], E.SPLIT[cname]):
        if cues and cues[-1]["g"] == g:              # pieces of one subtitle split with "/": one box, "前半/后半"
            cues[-1]["zh"] += "/" + zh
            cues[-1]["b"] = b
            continue
        sh = next((s for s in shots if s["src"] == src and s["in"] - 0.011 <= a <= s["out"] + 0.011), None)
        cues.append(dict(src=src, a=a, b=b, zh=zh, base=base, g=g, shot=sh["id"] if sh else None))
    return dict(id=ep, short=short, has_long=bool(E.SHOTS), has_short=bool(E.SHORT_SHOTS), shots=shots, cues=cues,
                sources=sorted({s["src"] for s in shots}))


def audio(ep, src):
    """A small mono copy of a recording for the page (made once)."""
    import gs_episode as G
    E = G.load(ep)
    if src not in E.SRC:
        raise FileNotFoundError(src)
    out = E.RENDER / "edit-audio" / f"{src}.wav"
    if not out.exists() or out.stat().st_mtime < E.SRC[src].stat().st_mtime:
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([gs_env.FFMPEG, "-v", "error", "-nostdin", "-y", "-i", str(E.SRC[src]), "-map", "0:a:0", "-ac", "1", "-ar", "16000",
                        str(out)], check=True, timeout=600)
    return out


def save(ep, short, data):
    """Merge the page's edits for this track (long video or short) into work/edit.json."""
    cur = state(ep, short)
    f = gs_env.ep_dir(ep) / "work" / "edit.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    if f.exists():
        b = f.parent / "review" / "edit-backup"
        b.mkdir(parents=True, exist_ok=True)
        (b / f"edit.{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    ids, bases = {s["id"] for s in cur["shots"]}, {c["base"] for c in cur["cues"]}
    shots = {k: v for k, v in old.get("shots", {}).items() if k not in ids}
    text = {k: v for k, v in old.get("text", {}).items() if k not in bases}
    for sid, o in data.get("shots", {}).items():
        if sid in ids:
            shots[sid] = {"in": round(float(o["in"]), 3), "out": round(float(o["out"]), 3),
                          "cut": sorted([round(float(a), 3), round(float(b), 3)] for a, b in o.get("cut", []) if b - a > 0.02)}
    for base, zh in data.get("text", {}).items():
        if base in bases and zh.strip() and zh != base:
            text[base] = zh.strip()
    new = {"saved": time.strftime("%Y-%m-%d %H:%M"), "shots": shots, "text": text}
    f.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
    return dict(ok=True, shots=len(shots), text=len(text))


def rebuild(ep, short):
    r = subprocess.run([sys.executable, "gs_voicecut.py", ep] + (["short"] if short else []), cwd=gs_env.STUDIO / "scripts",
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    tail = (r.stdout + r.stderr).strip().splitlines()[-4:]
    return dict(ok=r.returncode == 0, log="\n".join(tail))


PAGE = r"""<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>棚拍剪辑</title><style>
body{margin:0;background:#17181a;color:#e9e6de;font:15px/1.5 "Noto Sans SC",system-ui,sans-serif}
header{position:sticky;top:0;background:#101113;padding:10px 16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;z-index:2;border-bottom:1px solid #33312c}
main{display:grid;grid-template-columns:minmax(300px,440px) minmax(0,1fr);gap:16px;padding:16px}
@media(max-width:900px){main{grid-template-columns:1fr}}
h1{font-size:18px;margin:0 12px 0 0} a{color:#f2b90d} .dim{color:#9a968c;font-size:13px}
button{font:inherit;padding:8px 12px;border-radius:8px;border:1px solid #4a473f;background:#26272a;color:#e9e6de;cursor:pointer}
button:hover{border-color:#f2b90d} button.go{background:#f2b90d;color:#1a160c;border-color:#f2b90d;font-weight:700}
.shot{background:#202124;border-radius:8px;margin:0 0 10px;padding:8px 10px;border:2px solid transparent;cursor:pointer}
.shot.on{border-color:#f2b90d} .shot b{color:#f2b90d} .shot.changed b:after{content:" · 改过";color:#7fd08a;font-weight:400}
input[type=text]{width:100%;box-sizing:border-box;margin:4px 0;background:#101113;color:#e9e6de;border:1px solid #3a3833;border-radius:6px;padding:6px 8px;font:inherit}
input.changed{border-color:#7fd08a} canvas{width:100%;height:230px;background:#0c0d0e;border-radius:8px;display:block;cursor:crosshair}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0} #right{position:sticky;top:70px;align-self:start} #msg{color:#7fd08a}
</style><header><h1 id="ttl">棚拍剪辑</h1><span id="tracks"></span>
<button class="go" id="save">保存 (Ctrl+S)</button><button id="redo">保存并重做人声初剪</button><button id="undo">撤销 (Ctrl+Z)</button>
<a href="/">全部影片</a><a id="rev" href="/">审片页（这一支）</a><span id="msg"></span></header>
<main><div id="left"></div><div id="right"><div class="dim" id="info">点左边一个镜头。亮的地方是影片里留着的声音，暗的地方是剪掉的。</div>
<canvas id="cv"></canvas>
<div class="bar"><button id="pk">▶ 听这个镜头（照现在剪的）</button><button id="ps">▶ 听选起来的</button><button id="st">■ 停</button></div>
<div class="bar"><button id="cut">✂ 剪掉选起来的 (X)</button><button id="keep">↩ 把选起来的放回去 (R)</button><button id="reset">还原这个镜头</button></div>
<p class="dim"><b>键盘：</b>空格＝播放 / 停（有选起来就只播那一段）· X＝剪掉 · R＝放回去 · ↑ ↓＝上一个 / 下一个镜头 · Ctrl+Z＝撤销 · Ctrl+S＝保存 · Esc＝取消选取（在字幕格子里按 Esc 是离开格子）</p>
<p class="dim">在波形上按住拖一段就是选起来。选到镜头开头或结尾外面再按「放回去」，镜头就会往外延长；从开头或结尾往里选再「剪掉」，就是把头尾收短。字幕直接在左边改字；一句太长，在要断开的地方打一个 <b>/</b>（例如「前半句/后半句」），保存后就会变成前后两句字幕，各自跟着你讲到的时候出现。</p></div></main>
<script>
const q=new URLSearchParams(location.search),ep=q.get('id');let short=q.get('short')==='1',D=null,sel=0,range=null,dirty=false;
const AC=new (window.AudioContext||window.webkitAudioContext)(),BUF={},playing=[];
const $=id=>document.getElementById(id),fmt=t=>t.toFixed(2);
const msg=s=>{$('msg').textContent=s};
async function load(){D=await (await fetch(`/api/edit?id=${ep}&short=${short?1:0}`)).json();if(D.error){$('left').textContent=D.error;return}
 $('ttl').textContent=ep+(short?' · 短片':' · 正片');$('tracks').innerHTML=(D.has_long&&D.has_short)?`<a href="?id=${ep}&short=${short?0:1}">${short?'换到正片':'换到短片'}</a>`:'';
 $('rev').href=`/?id=${ep}&name=${short?'short-voicecut':ep+'-voicecut-480p'}`;sel=Math.min(sel,D.shots.length-1);left();await pick(sel);dirty=false}
function changed(s){return s.in!==s.base.in||s.out!==s.base.out||JSON.stringify(s.cut)!==JSON.stringify(s.base.cut)}
function left(){$('left').innerHTML=D.shots.map((s,i)=>`<div class="shot ${i===sel?'on':''} ${changed(s)?'changed':''}" data-i="${i}"><b>${s.id}</b> <span class="dim">${s.kind==='cam'?'出镜':'旁白'} · ${fmt(kept(s).reduce((a,[x,y])=>a+y-x,0))} 秒</span>`+
 D.cues.map((c,k)=>c.shot===s.id?`<input type="text" data-k="${k}" class="${c.zh!==c.base?'changed':''}" value="${c.zh.replace(/"/g,'&quot;')}">`:'').join('')+`</div>`).join('')}
$('left').onclick=e=>{const d=e.target.closest('.shot');if(d&&e.target.tagName!=='INPUT')pick(+d.dataset.i)};
$('left').oninput=e=>{const k=e.target.dataset.k;if(k===undefined)return;D.cues[+k].zh=e.target.value;e.target.className=D.cues[+k].zh!==D.cues[+k].base?'changed':'';dirty=true;msg('还没保存')};
function kept(s){let out=[],cur=s.in;[...s.cut].sort((a,b)=>a[0]-b[0]).forEach(([a,b])=>{if(b<=s.in||a>=s.out)return;if(a>cur)out.push([cur,Math.min(a,s.out)]);cur=Math.max(cur,b)});if(cur<s.out)out.push([cur,s.out]);return out.filter(([a,b])=>b-a>0.01)}
async function buf(src){if(!BUF[src]){msg('读声音…');const a=await (await fetch(`/audio?id=${ep}&src=${src}`)).arrayBuffer();BUF[src]=await AC.decodeAudioData(a);msg(dirty?'还没保存':'')}return BUF[src]}
let win=[0,1];
async function pick(i){sel=i;range=null;stop();left();const s=D.shots[i],b=await buf(s.src);win=[Math.max(0,Math.min(s.in,s.base.in)-2.5),Math.min(b.duration,Math.max(s.out,s.base.out)+2.5)];draw()}
function draw(){const s=D.shots[sel];if(!s||!BUF[s.src])return;const cv=$('cv'),W=cv.width=cv.clientWidth*devicePixelRatio,H=cv.height=cv.clientHeight*devicePixelRatio,g=cv.getContext('2d'),b=BUF[s.src],x=b.getChannelData(0),sr=b.sampleRate,K=kept(s);
 g.fillStyle='#0c0d0e';g.fillRect(0,0,W,H);const T=p=>win[0]+(win[1]-win[0])*p/W,X=t=>(t-win[0])/(win[1]-win[0])*W;
 for(let p=0;p<W;p++){const t0=T(p),t1=T(p+1),i0=Math.floor(t0*sr),i1=Math.max(i0+1,Math.floor(t1*sr));let m=0;for(let i=i0;i<i1&&i<x.length;i+=4){const v=Math.abs(x[i]);if(v>m)m=v}
  const on=K.some(([a,c])=>t0>=a&&t0<c);g.fillStyle=on?'#f2b90d':'#55524a';const h=Math.min(H*0.46,Math.sqrt(m)*H*0.75);g.fillRect(p,H/2-h,1,h*2||1)}
 g.fillStyle='#7fd08a';[s.in,s.out].forEach(t=>g.fillRect(X(t)-1,0,2,H));
 g.font=`${12*devicePixelRatio}px sans-serif`;D.cues.forEach(c=>{if(c.shot!==s.id)return;g.fillStyle='rgba(255,255,255,0.35)';g.fillRect(X(c.a),0,1,H*0.12);g.fillStyle='#c9c5ba';g.fillText(c.zh.slice(0,8),X(c.a)+4,14*devicePixelRatio)});
 if(range){g.fillStyle='rgba(255,255,255,0.22)';g.fillRect(X(range[0]),0,X(range[1])-X(range[0]),H)}
 $('info').innerHTML=`<b>${s.id}</b> · 录音 ${s.src} · 从 ${fmt(s.in)} 到 ${fmt(s.out)} 秒 · 中间剪掉 ${s.cut.length} 处`+(range?` · 选起来 ${fmt(range[0])}–${fmt(range[1])}（${fmt(range[1]-range[0])} 秒）`:'')}
let down=null;const cv=$('cv'),tAt=e=>{const r=cv.getBoundingClientRect();return win[0]+(win[1]-win[0])*Math.min(1,Math.max(0,(e.clientX-r.left)/r.width))};
cv.onmousedown=e=>{down=tAt(e);range=null;draw()};window.onmousemove=e=>{if(down===null)return;const t=tAt(e);range=[Math.min(down,t),Math.max(down,t)];draw()};
window.onmouseup=()=>{if(down!==null&&range&&range[1]-range[0]<0.03)range=null;down=null;draw()};window.onresize=draw;
function stop(){playing.splice(0).forEach(n=>{try{n.stop()}catch(e){}})}
function play(pieces){stop();const s=D.shots[sel],b=BUF[s.src];if(!b)return;AC.resume();let t=AC.currentTime+0.05;pieces.forEach(([a,c])=>{const n=AC.createBufferSource();n.buffer=b;n.connect(AC.destination);n.onended=()=>{const i=playing.indexOf(n);if(i>=0)playing.splice(i,1)};n.start(t,a,c-a);playing.push(n);t+=c-a})}
const UNDO=[],snap=()=>{UNDO.push(JSON.stringify({s:D.shots.map(x=>[x.in,x.out,x.cut]),c:D.cues.map(x=>x.zh)}));if(UNDO.length>200)UNDO.shift()};
function undo(){const u=UNDO.pop();if(!u){msg('没有可以撤销的');return}const o=JSON.parse(u);D.shots.forEach((x,i)=>{[x.in,x.out,x.cut]=o.s[i]});D.cues.forEach((x,i)=>{x.zh=o.c[i]});range=null;touch()}
$('undo').onclick=undo;$('left').addEventListener('focusin',e=>{if(e.target.dataset.k!==undefined)snap()});
document.addEventListener('keydown',e=>{const inp=e.target.tagName==='INPUT',k=e.key.toLowerCase();
 if((e.ctrlKey||e.metaKey)&&k==='s'){e.preventDefault();save();return}
 if(inp){if(k==='escape')e.target.blur();return}
 if((e.ctrlKey||e.metaKey)&&k==='z'){e.preventDefault();undo();return}
 if(e.ctrlKey||e.metaKey||e.altKey)return;
 if(k===' '){e.preventDefault();playing.length?stop():(range?play([range]):play(kept(D.shots[sel])))}
 else if(k==='x')$('cut').click();else if(k==='r')$('keep').click();
 else if(k==='arrowup'||k==='arrowdown'){e.preventDefault();pick(Math.max(0,Math.min(D.shots.length-1,sel+(k==='arrowup'?-1:1))))}
 else if(k==='escape'){range=null;stop();draw()}});
$('pk').onclick=()=>play(kept(D.shots[sel]));$('ps').onclick=()=>range&&play([range]);$('st').onclick=stop;
function touch(){dirty=true;msg('还没保存');left();draw()}
$('cut').onclick=()=>{if(!range)return;snap();const s=D.shots[sel];let [a,b]=range;if(a<=s.in+0.02&&b>s.in)s.in=Math.min(b,s.out-0.2);else if(b>=s.out-0.02&&a<s.out)s.out=Math.max(a,s.in+0.2);
 else{a=Math.max(a,s.in);b=Math.min(b,s.out);if(b-a>0.02){const all=[...s.cut,[a,b]].sort((p,q)=>p[0]-q[0]),m=[];all.forEach(c=>{if(m.length&&c[0]<=m[m.length-1][1])m[m.length-1][1]=Math.max(m[m.length-1][1],c[1]);else m.push([...c])});s.cut=m}}
 s.cut=s.cut.filter(c=>c[1]>s.in&&c[0]<s.out).map(c=>[+c[0].toFixed(3),+c[1].toFixed(3)]);s.in=+s.in.toFixed(3);s.out=+s.out.toFixed(3);range=null;touch()};
$('keep').onclick=()=>{if(!range)return;snap();const s=D.shots[sel],[a,b]=range;if(a<s.in)s.in=+a.toFixed(3);if(b>s.out)s.out=+b.toFixed(3);const m=[];s.cut.forEach(([c,d])=>{if(b<=c||a>=d){m.push([c,d]);return}if(a>c+0.02)m.push([c,+a.toFixed(3)]);if(b<d-0.02)m.push([+b.toFixed(3),d])});s.cut=m;range=null;touch()};
$('reset').onclick=()=>{snap();const s=D.shots[sel];s.in=s.base.in;s.out=s.base.out;s.cut=JSON.parse(JSON.stringify(s.base.cut));range=null;touch()};
async function save(){const shots={},text={};D.shots.forEach(s=>{if(changed(s))shots[s.id]={in:s.in,out:s.out,cut:s.cut}});D.cues.forEach(c=>{if(c.zh!==c.base&&c.zh.trim())text[c.base]=c.zh});
 const r=await (await fetch(`/api/edit?id=${ep}&short=${short?1:0}`,{method:'POST',body:JSON.stringify({shots,text})})).json();dirty=false;msg(r.ok?`保存了（${r.shots} 个镜头、${r.text} 句字幕改过）`:'保存失败：'+(r.error||''));return r.ok}
$('save').onclick=save;
$('redo').onclick=async()=>{if(!await save())return;msg('重做人声初剪，要一两分钟…');const r=await (await fetch(`/api/voicecut?id=${ep}&short=${short?1:0}`,{method:'POST'})).json();msg(r.ok?'做好了，可以去审片页看':'没做成：'+r.log)};
window.onbeforeunload=()=>dirty?'还没保存':undefined;
ep?load():($('left').textContent='网址要带 ?id=<编号>');
</script></html>"""
