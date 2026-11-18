"""Review page for cuts: notes by tapping instead of written feedback.

    python gs_review.py [port]        -> http://localhost:8770

Lists every cut that has a timeline (work/review/<name>.timeline.json, written by gs_voicecut.py). The director plays
it, pauses, taps a ready note and maybe adds a few words. Each note is saved with the time, the shot on screen, the
place in the recording and the subtitle being said: <episode>/work/review/<name>.notes.json. Claude reads that file
instead of asking for written feedback. Notes left on an older copy of the video are moved to
work/review/old-notes/ when a new copy is built, so a new copy always opens clean.
"""
import json
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import subprocess

import gs_edit
import gs_env
import gs_i18n

TAGS = gs_env.cfg("ui", "review_tags", None) or [gs_i18n.t(x) for x in
                                                 ["停顿太长", "停顿太短", "重念没剪掉", "这句被切到", "字幕有错", "这句想重录", "事实要查", "画面 / 镜头", "其他"]]


def cuts():
    out = []
    for root in (gs_env.EPISODES, gs_env.SHORTS):
        for f in sorted(root.glob("*/work/review/*.timeline.json")):
            t = json.loads(f.read_text(encoding="utf-8"))
            v = f.parents[2] / "preview" / t["file"]
            if v.exists():
                out.append(dict(id=t["id"], name=t["name"], total=t["total"], vertical=t.get("vertical", False),
                                mt=v.stat().st_mtime, built=time.strftime("%m-%d %H:%M", time.localtime(v.stat().st_mtime))))
    return out


def paths(ep, name):
    if not re.fullmatch(r"[\w.-]+", ep) or not re.fullmatch(r"[\w.-]+", name):
        raise ValueError("bad id")
    d = gs_env.ep_dir(ep)
    tl = json.loads((d / "work" / "review" / f"{name}.timeline.json").read_text(encoding="utf-8"))
    return d, tl, d / "preview" / tl["file"], d / "work" / "review" / f"{name}.notes.json"


def copy_id(video):
    st = video.stat()
    return f"{st.st_size}-{int(st.st_mtime)}"


def load_notes(ep, name):
    d, tl, video, nf = paths(ep, name)
    data = json.loads(nf.read_text(encoding="utf-8")) if nf.exists() else {"notes": []}
    cur = copy_id(video)
    old = [n for n in data["notes"] if n.get("copy") != cur]
    if old:
        dest = nf.parent / "old-notes" / f"{name}.notes.{time.strftime('%Y%m%d-%H%M')}.json"
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(json.dumps({"notes": old}, ensure_ascii=False, indent=1), encoding="utf-8")
        data["notes"] = [n for n in data["notes"] if n.get("copy") == cur]
        nf.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def place(tl, t):
    """Which shot and which second of the recording a time in the cut is."""
    sh = next((s for s in tl["shots"] if s["t"] <= t < s["t"] + s["d"]), tl["shots"][-1])
    src_t = None
    if sh["src"]:
        x = sh["in"] + (t - sh["t"])
        for a, b in sh.get("cut", []):
            if x >= a:
                x += b - a
        src_t = round(x, 2)
    sub = next((c["text"] for c in tl["subs"] if c["s"] - 0.2 <= t <= c["e"] + 0.2), "")
    return dict(shot=sh["id"], kind=sh["kind"], src=sh["src"], src_t=src_t, sub=sub)


PAGE = """<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>棚拍审片</title><style>
body{margin:0;background:#17181a;color:#e9e6de;font:16px/1.5 "Noto Sans SC",system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px;display:grid;gap:16px;grid-template-columns:minmax(0,1fr) 380px}
@media(max-width:860px){main{grid-template-columns:1fr}}
video{width:100%;max-height:78vh;background:#000;border-radius:8px}
h1{font-size:20px;margin:0 0 8px} a{color:#f2b90d} .dim{color:#9a968c;font-size:14px}
button{font:inherit;padding:10px 12px;border-radius:8px;border:1px solid #4a473f;background:#26272a;color:#e9e6de;cursor:pointer}
button:hover{border-color:#f2b90d} .tags{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
textarea{width:100%;box-sizing:border-box;min-height:60px;background:#101113;color:#e9e6de;border:1px solid #4a473f;border-radius:8px;padding:8px;font:inherit}
li{margin:0 0 10px;padding:10px;background:#202124;border-radius:8px;list-style:none} ul{padding:0;margin:8px 0}
.now{padding:10px;background:#202124;border-radius:8px;min-height:56px} .x{float:right;padding:2px 10px} .row{display:flex;justify-content:space-between;gap:4px 16px;flex-wrap:wrap} .r{white-space:nowrap}
</style><main id="app"></main><script>
const q=new URLSearchParams(location.search),ep=q.get('id'),name=q.get('name'),app=document.getElementById('app');
const fmt=t=>Math.floor(t/60)+':'+(t%60).toFixed(1).padStart(4,'0');
const isS=x=>x.name.startsWith('short'),stage=x=>x.name.includes('voicecut')?'人声初剪':'动画 + 配乐 480p';
async function list(){const c=await (await fetch('/api/cuts')).json();
 // one row per piece (the list was long and repeated itself): the name opens the newest
 // build, an older stage of the same piece is one small link behind it
 const g={};c.forEach(x=>{const k=x.id+'|'+isS(x);(g[k]=g[k]||[]).push(x)});
 const rows=Object.values(g).map(a=>a.sort((p,q)=>q.mt-p.mt));
 app.innerHTML='<div><h1>棚拍审片</h1><p class="dim">一支一行，点名字看最新的那一版。</p><ul>'+rows.map(a=>{const x=a[0];
  return `<li class="row"><span><a href="?id=${x.id}&name=${x.name}">${x.id}${isS(x)&&!x.id.startsWith('s')?' · 短片':''}</a> <span class="dim">${stage(x)} · ${fmt(x.total)} · ${x.built}</span></span><span class="r"><a href="/edit?id=${x.id}&short=${isS(x)?1:0}">剪辑</a>${a.slice(1).map(o=>` · <a class="dim" href="?id=${o.id}&name=${o.name}">${stage(o)}</a>`).join('')}</span></li>`}).join('')+'</ul></div>';}
async function review(){const tl=await (await fetch(`/api/timeline?id=${ep}&name=${name}`)).json();let data=await (await fetch(`/api/notes?id=${ep}&name=${name}`)).json();
 const isShort=name.startsWith('short'),all=await (await fetch('/api/cuts')).json(),other=all.filter(x=>x.id===ep&&x.name!==name);
 app.innerHTML=`<div><h1>${ep}${isShort&&!ep.startsWith('s')?' · 短片':''} · ${stage({name})}</h1><video id="v" controls playsinline src="/video?id=${ep}&name=${name}"></video>
 <p><a href="/">← 全部影片</a> · <a href="/edit?id=${ep}&short=${isShort?1:0}">剪辑页（这一支，用耳朵修）</a>${other.map(x=>` · <a href="?id=${x.id}&name=${x.name}">换到 ${ep.startsWith('s')?'':isS(x)?'短片 · ':'正片 · '}${stage(x)}</a>`).join('')}</p>
 <p class="dim"><b>键盘：</b>空格＝播放 / 暂停 · ← →＝退 / 进 2 秒（按住 Shift 是 0.5 秒）· ↑ ↓＝上一个 / 下一个镜头 · 1–9＝点第几个意见 · E＝去剪辑页 · 在打字格里按 Esc 离开格子</p></div>
 <div><div class="now" id="now"></div><div class="tags">${TAGS.map((t,i)=>`<button data-t="${t}">${i+1} ${t}</button>`).join('')}</div>
 <textarea id="w" placeholder="要补充的话（可以不写；先写字再点意见）"></textarea><p class="dim">意见会记下时间、镜头和当时的字幕。</p><ul id="ns"></ul></div>`;
 const v=document.getElementById('v'),now=document.getElementById('now');
 const at=t=>{const s=tl.shots.find(s=>t>=s.t&&t<s.t+s.d)||tl.shots[tl.shots.length-1],c=tl.subs.find(c=>t>=c.s-0.2&&t<=c.e+0.2);return [s,c]};
 v.ontimeupdate=()=>{const [s,c]=at(v.currentTime);now.innerHTML=`<b>${fmt(v.currentTime)}</b> · 镜头 ${s.id} <span class="dim">(${s.kind})</span><br>${c?c.text:'<span class="dim">（没有字幕）</span>'}`};v.ontimeupdate();
 const draw=()=>{document.getElementById('ns').innerHTML=data.notes.map((n,i)=>`<li><button class="x" data-i="${i}">✕</button><a href="#" data-go="${n.t}">${fmt(n.t)}</a> · ${n.shot} · <b>${n.tag}</b><br>${n.words||''}<div class="dim">${n.sub||''}</div></li>`).join('')};
 const save=async()=>{data=await (await fetch(`/api/notes?id=${ep}&name=${name}`,{method:'POST',body:JSON.stringify(data)})).json();draw()};
 document.querySelector('.tags').onclick=e=>{const t=e.target.dataset.t;if(!t)return;v.pause();data.notes.push({t:+v.currentTime.toFixed(2),tag:t,words:document.getElementById('w').value.trim(),at:new Date().toISOString()});document.getElementById('w').value='';data.notes.sort((a,b)=>a.t-b.t);save()};
 document.getElementById('ns').onclick=e=>{if(e.target.dataset.i){data.notes.splice(+e.target.dataset.i,1);save()}if(e.target.dataset.go){e.preventDefault();v.currentTime=+e.target.dataset.go}};draw();
 document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA'){if(e.key==='Escape')e.target.blur();return}
  if(e.ctrlKey||e.metaKey||e.altKey)return;const k=e.key;
  if(k===' '){e.preventDefault();v.paused?v.play():v.pause()}
  else if(k==='ArrowLeft'||k==='ArrowRight'){e.preventDefault();v.currentTime=Math.max(0,v.currentTime+(k==='ArrowLeft'?-1:1)*(e.shiftKey?0.5:2))}
  else if(k==='ArrowUp'||k==='ArrowDown'){e.preventDefault();const i=Math.max(0,tl.shots.findIndex(s=>v.currentTime>=s.t&&v.currentTime<s.t+s.d)),j=Math.max(0,Math.min(tl.shots.length-1,i+(k==='ArrowUp'?-1:1)));v.currentTime=tl.shots[j].t+0.01}
  else if(/^[1-9]$/.test(k)&&TAGS[+k-1]){const b=document.querySelector(`button[data-t="${TAGS[+k-1]}"]`);if(b)b.click()}
  else if(k==='e'||k==='E')location.href=`/edit?id=${ep}&short=${isShort?1:0}`});}
const TAGS=__TAGS__;ep?review():list();
</script></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json", code=200):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def video(self, path, ctype="video/mp4"):
        size = path.stat().st_size
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
        a, b = (int(m[1]) if m and m[1] else 0), (int(m[2]) if m and m[2] else size - 1)
        b = min(b, size - 1)
        self.send_response(206 if m else 200)
        if m:
            self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(b - a + 1))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(a)
            left = b - a + 1
            try:
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/":
                return self.send(gs_i18n.page(PAGE).replace("__TAGS__", json.dumps(TAGS, ensure_ascii=False)), "text/html")
            if u.path == "/api/cuts":
                return self.send(json.dumps(cuts(), ensure_ascii=False))
            if u.path == "/edit":                               # the editing page (gs_edit.py)
                return self.send(gs_i18n.page(gs_edit.PAGE), "text/html")
            if u.path == "/api/edit":
                return self.send(json.dumps(gs_edit.state(q["id"], q.get("short") == "1"), ensure_ascii=False))
            if u.path == "/audio":
                return self.video(gs_edit.audio(q["id"], q["src"]), "audio/wav")
            d, tl, video, nf = paths(q["id"], q["name"])
            if u.path == "/api/timeline":
                return self.send(json.dumps(tl, ensure_ascii=False))
            if u.path == "/api/notes":
                return self.send(json.dumps(load_notes(q["id"], q["name"]), ensure_ascii=False))
            if u.path == "/video":
                return self.video(video)
        except (KeyError, ValueError, FileNotFoundError, SystemExit, subprocess.CalledProcessError) as e:
            return self.send(json.dumps({"error": str(e)}, ensure_ascii=False), code=404)
        self.send("{}", code=404)

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/api/edit":
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
                return self.send(json.dumps(gs_edit.save(q["id"], q.get("short") == "1", data), ensure_ascii=False))
            if u.path == "/api/voicecut":
                return self.send(json.dumps(gs_edit.rebuild(q["id"], q.get("short") == "1"), ensure_ascii=False))
        except (KeyError, ValueError, FileNotFoundError, SystemExit, subprocess.TimeoutExpired) as e:
            return self.send(json.dumps({"error": str(e)}, ensure_ascii=False), code=400)
        if u.path != "/api/notes":
            return self.send("{}", code=404)
        try:
            d, tl, video, nf = paths(q["id"], q["name"])
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
            cur = copy_id(video)
            for n in data.get("notes", []):
                n.setdefault("copy", cur)
                n.update(place(tl, n["t"]))
            data["built"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(video.stat().st_mtime))
            nf.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            self.send(json.dumps(data, ensure_ascii=False))
        except (KeyError, ValueError, FileNotFoundError) as e:
            self.send(json.dumps({"error": str(e)}), code=400)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    print(f"http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
