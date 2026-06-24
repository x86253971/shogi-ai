"""Browser-based Shogi board. Run: python webboard.py  then open http://localhost:8000

Pure stdlib HTTP server wrapping the engine. You are Sente (bottom). Click a
piece, then a destination. Click a captured piece in your hand to drop it.
"""

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from shogi.position import Position, SENTE, GOTE, make_sq, sq_file, sq_rank
from shogi.movegen import generate_legal, make_move, move_to_usi, usi_to_move
from shogi.search import Search

THINK_TIME = 3.0
state = {"moves": [], "human": SENTE, "info": ""}
lock = threading.Lock()


def build_pos():
    pos = Position.startpos()
    for mv in state["moves"]:
        make_move(pos, usi_to_move(mv))
    return pos


def snapshot():
    pos = build_pos()
    legal = [move_to_usi(m) for m in generate_legal(pos)]
    board = []
    for sq in range(81):
        v = pos.board[sq]
        if v == 0:
            board.append(None)
        else:
            c, pt = Position.dec(v)
            board.append({"c": c, "t": pt})
    st = ""
    if not legal:
        st = "詰み" if pos.in_check(pos.turn) else "ステイルメイト"
    elif pos.in_check(pos.turn):
        st = "王手"
    return {
        "board": board,
        "hands": {"0": pos.hands[0], "1": pos.hands[1]},
        "turn": pos.turn,
        "legal": legal,
        "ply": pos.ply,
        "status": st,
        "last": state["moves"][-1] if state["moves"] else None,
        "info": state["info"],
    }


def engine_reply():
    pos = Position.startpos()
    hist = [pos.zob]
    for mv in state["moves"]:
        make_move(pos, usi_to_move(mv))
        hist.append(pos.zob)
    if not generate_legal(pos):
        return
    s = Search()
    s._hist = hist[:-1]
    captured = {}

    def info(line):
        parts = line.split()
        try:
            d = parts[parts.index("depth") + 1]
            sc = parts[parts.index("score") + 2]
            captured["info"] = f"depth {d}, score {sc}"
        except Exception:
            pass
    best = s.think(pos, THINK_TIME, max_depth=16, info=info, history=s._hist)
    if best is not None:
        state["moves"].append(move_to_usi(best))
        state["info"] = captured.get("info", "")


HTML = r"""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>将棋 — Claude Code Engine</title>
<style>
 body{font-family:sans-serif;background:#2b2b2b;color:#eee;text-align:center;margin:0;padding:12px}
 h1{font-size:18px;margin:6px}
 #board{display:inline-block;background:#d9a85a;border:3px solid #5a3b14;border-collapse:collapse}
 table{border-collapse:collapse}
 td{width:46px;height:50px;border:1px solid #5a3b14;text-align:center;font-size:26px;
    cursor:pointer;font-weight:bold;position:relative;user-select:none}
 .sente{color:#111}
 .gote{color:#b00;transform:rotate(180deg)}
 .sel{background:#9fe0a0}
 .tgt{background:#bfe9ff}
 .last{box-shadow:inset 0 0 0 3px #f5d76e}
 .hand{display:inline-block;min-width:280px;margin:8px;padding:6px;background:#3a3a3a;border-radius:6px}
 .hp{display:inline-block;padding:4px 8px;margin:2px;background:#d9a85a;color:#111;border-radius:4px;cursor:pointer;font-weight:bold}
 .hp.dis{opacity:.35;cursor:default}
 .hpsel{outline:3px solid #9fe0a0}
 button{font-size:15px;padding:6px 14px;margin:6px;cursor:pointer}
 #msg{min-height:22px;font-size:16px;margin:6px;color:#f5d76e}
 #info{font-size:13px;color:#9ab}
</style></head><body>
<h1>将棋 — あなた=先手（下） vs Claude Codeエンジン</h1>
<div id="msg"></div>
<div class="hand" id="goteHand"></div>
<div id="board"></div>
<div class="hand" id="senteHand"></div>
<div><button onclick="newGame()">新規対局</button>
<button onclick="undo()">待った（1手戻す）</button></div>
<div id="info"></div>
<script>
const GLYPH=["歩","香","桂","銀","金","角","飛","玉","と","杏","圭","全","馬","龍"];
const HAND_GLYPH=["歩","香","桂","銀","金","角","飛"];
let S=null, sel=null, dropSel=null, busy=false;
const files=[9,8,7,6,5,4,3,2,1];
function sqOf(file,rank){return (rank-1)*9+(9-file);}
function usiSq(file,rank){return ""+file+"abcdefghi"[rank-1];}
async function api(path,body){
  const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify(body||{})});
  return await r.json();
}
async function newGame(){S=await api("/api/new");sel=null;dropSel=null;render();}
async function undo(){S=await api("/api/undo");sel=null;dropSel=null;render();}
async function refresh(){S=await api("/api/state");render();}
function legalFrom(fsq){
  const u=usiSq(sqFile(fsq),sqRank(fsq));
  return S.legal.filter(m=>m.length>=4&&m[1]!="*"&&m.substr(0,2)==u);
}
function sqFile(sq){return 9-(sq%9);}
function sqRank(sq){return Math.floor(sq/9)+1;}
async function clickCell(file,rank){
  if(busy||S.turn!=0)return;
  const sq=sqOf(file,rank), cell=S.board[sq], to=usiSq(file,rank);
  if(dropSel!==null){
    const mv=HAND_GLYPH_LETTER[dropSel]+"*"+to;
    if(S.legal.includes(mv)){await send(mv);}
    dropSel=null;render();return;
  }
  if(sel===null){
    if(cell&&cell.c==0){sel=sq;render();}
    return;
  }
  if(sq===sel){sel=null;render();return;}
  if(cell&&cell.c==0){sel=sq;render();return;}
  // attempt move sel->to
  const from=usiSq(sqFile(sel),sqRank(sel));
  const base=from+to;
  const canP=S.legal.includes(base+"+"), canN=S.legal.includes(base);
  let mv=null;
  if(canP&&canN){mv=confirm("成りますか？")?base+"+":base;}
  else if(canP){mv=base+"+";}
  else if(canN){mv=base;}
  if(mv){sel=null;await send(mv);}
  else{sel=null;render();}
}
const HAND_GLYPH_LETTER=["P","L","N","S","G","B","R"];
async function send(mv){
  busy=true;document.getElementById("msg").textContent="エンジン思考中…";
  S=await api("/api/move",{usi:mv});busy=false;sel=null;dropSel=null;render();
}
function clickHand(color,pt){
  if(busy||S.turn!=0||color!=0)return;
  if(S.hands["0"][pt]<=0)return;
  dropSel=(dropSel===pt?null:pt);sel=null;render();
}
function render(){
  if(!S)return;
  const b=document.getElementById("board");
  let h="<table>";
  for(let ri=0;ri<9;ri++){const rank=ri+1;
    h+="<tr>";
    for(const file of files){
      const sq=sqOf(file,rank),c=S.board[sq];
      let cls="",txt="";
      if(c){cls=c.c==0?"sente":"gote";txt=GLYPH[c.t];}
      if(sel===sq)cls+=" sel";
      if(sel!==null){const u=usiSq(sqFile(sel),sqRank(sel));
        if(S.legal.includes(u+usiSq(file,rank))||S.legal.includes(u+usiSq(file,rank)+"+"))cls+=" tgt";}
      if(dropSel!==null){const mv=HAND_GLYPH_LETTER[dropSel]+"*"+usiSq(file,rank);
        if(S.legal.includes(mv))cls+=" tgt";}
      if(S.last){const lt=S.last.replace("+","").slice(-2);
        if(lt===usiSq(file,rank))cls+=" last";}
      h+=`<td class="${cls}" onclick="clickCell(${file},${rank})">${txt}</td>`;
    }
    h+="</tr>";
  }
  h+="</table>";b.innerHTML=h;
  renderHand("senteHand",0);renderHand("goteHand",1);
  let m=`手数:${S.ply}　手番:${S.turn==0?"あなた(先手)":"エンジン(後手)"}`;
  if(S.status)m+=`　【${S.status}】`;
  if(S.status=="詰み")m=S.turn==0?"あなたの負け（詰み）":"あなたの勝ち！";
  document.getElementById("msg").textContent=m;
  document.getElementById("info").textContent=S.info?("engine: "+S.info):"";
}
function renderHand(id,color){
  const el=document.getElementById(id);const hands=S.hands[""+color];
  let h=(color==0?"先手 持駒":"後手 持駒")+": ";
  for(let pt=0;pt<7;pt++){const n=hands[pt];
    const dis=(n<=0)?" dis":"";const selc=(color==0&&dropSel===pt)?" hpsel":"";
    h+=`<span class="hp${dis}${selc}" onclick="clickHand(${color},${pt})">${HAND_GLYPH[pt]}${n>1?("×"+n):""}</span>`;
  }
  el.innerHTML=h;
}
newGame();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, HTML, "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        ln = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(ln) if ln else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except Exception:
            body = {}
        with lock:
            if self.path == "/api/new":
                state["moves"] = []
                state["info"] = ""
            elif self.path == "/api/undo":
                state["moves"] = state["moves"][:-2]
            elif self.path == "/api/move":
                mv = body.get("usi")
                pos = build_pos()
                legal = [move_to_usi(m) for m in generate_legal(pos)]
                if mv in legal:
                    state["moves"].append(mv)
                    engine_reply()
            out = snapshot()
        self._send(200, json.dumps(out), "application/json")


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    url = "http://localhost:8000"
    print("Shogi board running at", url)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    srv.serve_forever()


if __name__ == "__main__":
    main()