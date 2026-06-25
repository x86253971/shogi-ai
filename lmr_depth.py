"""Deterministic LMR verification: at a fixed node budget, compare depth reached
and best move chosen, LMR-on vs LMR-off (both PVS), across many positions
reached from random self-play. LMR's purpose is to reach deeper at equal cost.
Usage: python lmr_depth.py [positions] [nodes]
"""
import random, sys
from shogi.position import Position, SENTE
from shogi.movegen import generate_legal, make_move, move_to_usi
from shogi.search import Search
from shogi.evaluate import evaluate
BIG_T = 10 ** 9

def gen_positions(n, seed=1):
    rng = random.Random(seed); out = []
    while len(out) < n:
        pos = Position.startpos()
        depth = rng.randint(6, 40)
        ok = True
        for _ in range(depth):
            legal = generate_legal(pos)
            if not legal: ok = False; break
            make_move(pos, rng.choice(legal))
        if ok and generate_legal(pos):
            out.append(pos.clone())
    return out

def run(pos, lmr, nodes):
    s = Search(); s.eval_fn = evaluate; s.use_pvs = True; s.use_lmr = lmr
    info = {"depth": 0, "val": 0, "mv": ""}
    def cap(line, **k):
        # parse "info depth D score cp V ... pv MV"
        t = line.split()
        try:
            info["depth"] = int(t[t.index("depth")+1])
            si = t.index("score")
            info["val"] = int(t[si+2]) if t[si+1] == "cp" else 99999
            info["mv"] = t[t.index("pv")+1]
        except Exception:
            pass
    mv = s.think(pos, BIG_T, max_depth=40, info=cap, max_nodes=nodes)
    return info["depth"], move_to_usi(mv) if mv else "", s.nodes

def main():
    npos = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    nodes = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    positions = gen_positions(npos)
    dsum_on = dsum_off = same_mv = deeper = shallower = 0
    for i, p in enumerate(positions):
        doff, moff, _ = run(p.clone(), False, nodes)
        don, mon, _ = run(p.clone(), True, nodes)
        dsum_off += doff; dsum_on += don
        if mon == moff: same_mv += 1
        if don > doff: deeper += 1
        elif don < doff: shallower += 1
    print(f"positions={npos} nodes={nodes}")
    print(f"avg depth  LMR-off={dsum_off/npos:.2f}  LMR-on={dsum_on/npos:.2f}")
    print(f"LMR deeper in {deeper}, shallower in {shallower}, equal in "
          f"{npos-deeper-shallower}")
    print(f"same best move: {same_mv}/{npos}")

if __name__ == "__main__":
    main()