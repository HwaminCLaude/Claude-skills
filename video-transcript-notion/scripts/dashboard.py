"""실시간 진행 대시보드 — 업로드가 몇 시간 걸릴 때 상태를 눈으로 보는 용도.

    python dashboard.py --work <폴더>                 → http://localhost:8765
    python dashboard.py --work <폴더> --port 9000 --detach

무거운 조회(rclone lsjson)는 60초마다, 가벼운 조회(로그·상태파일)는 3초마다.
브라우저는 2초마다 폴링한다. 업로드를 방해하지 않도록 주기를 나눠 뒀다.
"""
from __future__ import annotations

import collections
import json
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vt_common as C

STATS_RE = re.compile(
    r"([\d.]+)\s+([KMGT]?i?B)\s*/\s*([\d.]+)\s+([KMGT]?i?B),\s*(\d+)%,\s*"
    r"([\d.]+)\s*([KMGT]?i?B)/s,\s*ETA\s*(\S+)")
COPIED_RE = re.compile(r"INFO\s*:\s*(.+?):\s*Copied \(new\)")
PROCS = ["02_upload_videos", "04_sync_videos"]

_state: dict = {"ready": False}
_lock = threading.Lock()
LOCAL: list[dict] = []


def heavy_loop() -> None:
    while True:
        try:
            have = set(C.drive_listing())
            per = {}
            done = done_b = 0
            for unit in LOCAL:
                g = per.setdefault(unit["group"], {"done": 0, "total": 0, "gb": 0.0})
                g["total"] += 1
                g["gb"] += unit["size"] / 2**30
                if unit["video"] in have:
                    g["done"] += 1
                    done += 1
                    done_b += unit["size"]
            for g in per.values():
                g["gb"] = round(g["gb"], 1)
            with _lock:
                _state["drive"] = {
                    "done": done, "total": len(LOCAL),
                    "done_gb": round(done_b / 2**30, 2),
                    "total_gb": round(sum(u["size"] for u in LOCAL) / 2**30, 2),
                    "per_group": per, "at": time.strftime("%H:%M:%S"),
                }
                _state["ready"] = True
        except Exception as exc:
            with _lock:
                _state["drive_error"] = str(exc)[:200]
        time.sleep(60)


def tail(path: Path, n: int = 400) -> list[str]:
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except Exception:
        return []


def light_loop() -> None:
    while True:
        info: dict = {}
        lines = tail(C.out_dir() / "upload.log")
        speed = eta = None
        for line in reversed(lines):
            m = STATS_RE.search(line)
            if m:
                speed, eta = f"{m[6]} {m[7]}/s", m[8]
                break
        recent = []
        for line in reversed(lines):
            m = COPIED_RE.search(line)
            if m:
                recent.append(m[1])
                if len(recent) >= 8:
                    break
        info.update(speed=speed, eta=eta, recent=recent,
                    rounds=sum(1 for l in lines if "[ROUND" in l),
                    stalls=sum(1 for l in lines if "[WATCHDOG]" in l))

        state = C.load_json("pages.json", {}) or {}
        if state:
            info["notion"] = {
                "pages": len(state),
                "with_text": sum(1 for v in state.values() if v.get("segments")),
                "sentences": sum(v.get("segments", 0) for v in state.values()),
                "with_video": sum(1 for v in state.values() if v.get("video_filled")),
            }

        alive = {"rclone": False, **{p: False for p in PROCS}}
        try:
            import psutil
            for p in psutil.process_iter(["name", "cmdline"]):
                if (p.info.get("name") or "").lower().startswith("rclone"):
                    alive["rclone"] = True
                    continue
                cmd = " ".join(p.info.get("cmdline") or [])
                for t in PROCS:
                    if t in cmd:
                        alive[t] = True
        except Exception:
            pass
        info["procs"] = alive
        info["at"] = time.strftime("%H:%M:%S")
        with _lock:
            _state["live"] = info
        time.sleep(3)


PAGE = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>업로드 현황</title><style>
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 system-ui,'Malgun Gothic',sans-serif;background:#f6f7f9;color:#1a1c1f}
@media(prefers-color-scheme:dark){body{background:#14161a;color:#e6e8eb}}
.wrap{max-width:1000px;margin:0 auto;padding:24px 18px 60px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:14px;margin:0 0 10px;font-weight:600}
.sub{color:#7a828c;font-size:13px;margin-bottom:20px}
.card{background:#fff;border:1px solid #e3e6ea;border-radius:12px;padding:18px;margin-bottom:14px}
@media(prefers-color-scheme:dark){.card{background:#1c1f24;border-color:#2c3138}}
.row{display:flex;gap:14px;flex-wrap:wrap}.row>.card{flex:1 1 200px;margin-bottom:0}
.big{font-size:30px;font-weight:650;letter-spacing:-.5px}
.lbl{font-size:12px;color:#7a828c;text-transform:uppercase;letter-spacing:.4px}
.bar{height:12px;background:#e8ebef;border-radius:99px;overflow:hidden;margin:10px 0 6px}
.wkbar{height:9px;background:#e8ebef;border-radius:99px;overflow:hidden}
@media(prefers-color-scheme:dark){.bar,.wkbar{background:#2a2f36}}
.fill{height:100%;background:linear-gradient(90deg,#4a8cf7,#38c48b);transition:width .6s}
.wkfill{height:100%;background:#4a8cf7}.wkfill.done{background:#38c48b}
.wk{display:grid;grid-template-columns:100px 1fr 92px;gap:8px;align-items:center;margin:5px 0;font-size:13px}
.num{text-align:right;color:#7a828c;font-variant-numeric:tabular-nums;font-size:12px}
.pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:99px;
 font-size:12.5px;background:#eef1f5;margin:3px 5px 3px 0}
@media(prefers-color-scheme:dark){.pill{background:#262b32}}
.dot{width:8px;height:8px;border-radius:99px;background:#c9ced6}
.dot.on{background:#38c48b;box-shadow:0 0 0 3px rgba(56,196,139,.2)}.dot.off{background:#e5654a}
ul{margin:8px 0 0;padding-left:0;list-style:none}
li{font-size:12.5px;color:#5d666f;padding:3px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
@media(prefers-color-scheme:dark){li{color:#9aa3ad}}
</style></head><body><div class="wrap">
<h1>업로드 현황</h1><div class="sub" id="stamp">불러오는 중…</div>
<div class="card">
 <div class="lbl">전체 진행 (파일)</div><div class="big" id="pf">–</div>
 <div class="bar"><div class="fill" id="bf" style="width:0"></div></div>
 <div class="lbl" style="margin-top:14px">전체 진행 (용량)</div><div class="big" id="pg">–</div>
 <div class="bar"><div class="fill" id="bg" style="width:0"></div></div></div>
<div class="row">
 <div class="card"><div class="lbl">현재 속도</div><div class="big" id="sp">–</div></div>
 <div class="card"><div class="lbl">rclone 추정</div><div class="big" id="eta">–</div></div>
 <div class="card"><div class="lbl">정체 개입</div><div class="big" id="st">–</div></div></div>
<div class="card"><h2>프로세스</h2><div id="pr"></div></div>
<div class="card"><h2>Notion</h2><div class="row" style="gap:20px">
 <div><div class="lbl">페이지</div><div class="big" id="np">–</div></div>
 <div><div class="lbl">대본</div><div class="big" id="nt">–</div></div>
 <div><div class="lbl">영상</div><div class="big" id="nv">–</div></div>
 <div><div class="lbl">문장</div><div class="big" id="ns">–</div></div></div></div>
<div class="card"><h2>그룹별</h2><div id="wk"></div></div>
<div class="card"><h2>최근 업로드</h2><ul id="rc"></ul></div>
</div><script>
const $=i=>document.getElementById(i), pct=(a,b)=>b?Math.round(a/b*1000)/10:0;
async function tick(){
 let d; try{d=await (await fetch('/api/status',{cache:'no-store'})).json()}catch(e){return}
 const L=d.live||{}, D=d.drive;
 $('stamp').textContent='갱신 '+(L.at||'–')+(D?'  ·  드라이브 '+D.at:'  ·  드라이브 대기')
   +(L.rounds?'  ·  라운드 '+L.rounds:'');
 if(D){
  $('pf').textContent=D.done+' / '+D.total+' 개  ('+pct(D.done,D.total)+'%)';
  $('bf').style.width=pct(D.done,D.total)+'%';
  $('pg').textContent=D.done_gb+' / '+D.total_gb+' GB  ('+pct(D.done_gb,D.total_gb)+'%)';
  $('bg').style.width=pct(D.done_gb,D.total_gb)+'%';
  $('wk').innerHTML=Object.entries(D.per_group).map(([w,v])=>{const p=pct(v.done,v.total);
   return '<div class="wk"><span>'+w+'</span><div class="wkbar"><div class="wkfill'
    +(v.done===v.total?' done':'')+'" style="width:'+p+'%"></div></div>'
    +'<span class="num">'+v.done+'/'+v.total+' · '+v.gb+'GB</span></div>';}).join('');
 }
 $('sp').textContent=L.speed||'–'; $('eta').textContent=L.eta||'–';
 $('st').textContent=(L.stalls??'–')+' 회';
 $('pr').innerHTML=Object.entries(L.procs||{}).map(([k,v])=>
  '<span class="pill"><span class="dot '+(v?'on':'off')+'"></span>'+k+'</span>').join('');
 const N=L.notion;
 if(N){$('np').textContent=N.pages;$('nt').textContent=N.with_text+'/'+N.pages;
  $('nv').textContent=N.with_video+'/'+N.pages;$('ns').textContent=N.sentences.toLocaleString();}
 $('rc').innerHTML=(L.recent||[]).map(x=>'<li>'+x.replace(/[<>&]/g,'')+'</li>').join('')||'<li>–</li>';
}
tick(); setInterval(tick,2000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/status"):
            with _lock:
                body = json.dumps(_state, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
        elif self.path in ("/", "/index.html"):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def main() -> None:
    global LOCAL
    C.init()
    argv = sys.argv
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8765
    if "--detach" in argv:
        print(f"대시보드 분리 실행 PID={C.detach('dashboard.py', ['--port', str(port)])}"
              f"  →  http://localhost:{port}")
        return
    LOCAL = C.load_json("units.json") or []
    threading.Thread(target=heavy_loop, daemon=True).start()
    threading.Thread(target=light_loop, daemon=True).start()
    print(f"대시보드 →  http://localhost:{port}   (종료: Ctrl+C)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
