"""USI protocol entry point. Run: python -m usi  (or python usi.py)"""

import sys
from shogi.position import Position, SENTE
from shogi.movegen import generate_legal, make_move, usi_to_move, move_to_usi
from shogi.search import Search

ENGINE_NAME = "HanyuShogi 0.1 (Python)"
ENGINE_AUTHOR = "Claude Code + x86253971"


def out(s):
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def parse_position(cmd):
    tokens = cmd.split()
    idx = 1
    if tokens[idx] == "startpos":
        pos = Position.startpos()
        idx += 1
    elif tokens[idx] == "sfen":
        sfen = " ".join(tokens[idx + 1:idx + 5])
        pos = Position.from_sfen(sfen)
        idx += 5
    else:
        pos = Position.startpos()
    if idx < len(tokens) and tokens[idx] == "moves":
        for mv in tokens[idx + 1:]:
            m = usi_to_move(mv)
            make_move(pos, m)
    return pos


def compute_budget(pos, args):
    bt = wt = byo = bi = wi = mt = 0
    depth = None
    infinite = False
    keys = {}
    it = iter(args)
    for tok in it:
        if tok in ("btime", "wtime", "byoyomi", "binc", "winc", "movetime", "depth"):
            keys[tok] = int(next(it))
        elif tok == "infinite":
            infinite = True
    bt = keys.get("btime", 0)
    wt = keys.get("wtime", 0)
    byo = keys.get("byoyomi", 0)
    bi = keys.get("binc", 0)
    wi = keys.get("winc", 0)
    mt = keys.get("movetime", 0)
    depth = keys.get("depth")
    if infinite:
        return 3600.0, 64
    if depth is not None:
        return 3600.0, depth
    if mt:
        return max(0.05, mt / 1000.0 - 0.05), 64
    ourtime = bt if pos.turn == SENTE else wt
    ourinc = bi if pos.turn == SENTE else wi
    budget = byo / 1000.0
    if ourtime:
        budget += (ourtime / 1000.0) / 30.0 + (ourinc / 1000.0) * 0.8
    if budget <= 0:
        budget = 1.0
    return max(0.05, budget - 0.15), 64


def main():
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    pos = Position.startpos()
    search = Search()
    for line in sys.stdin:
        cmd = line.strip().lstrip("\ufeff")
        if cmd == "usi":
            out(f"id name {ENGINE_NAME}")
            out(f"id author {ENGINE_AUTHOR}")
            out("option name USI_Hash type spin default 256 min 1 max 4096")
            out("option name USI_Ponder type check default false")
            out("usiok")
        elif cmd == "isready":
            out("readyok")
        elif cmd == "usinewgame":
            pos = Position.startpos()
            search.new_game()
        elif cmd.startswith("position"):
            pos = parse_position(cmd)
        elif cmd.startswith("go"):
            budget, depth = compute_budget(pos, cmd.split()[1:])
            mv = search.think(pos, budget, max_depth=depth, info=out)
            if mv is None:
                out("bestmove resign")
            else:
                out(f"bestmove {move_to_usi(mv)}")
        elif cmd == "stop":
            pass
        elif cmd in ("quit", "exit"):
            break
        elif cmd == "isready":
            out("readyok")
    return 0


if __name__ == "__main__":
    sys.exit(main())