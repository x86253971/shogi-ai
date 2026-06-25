"""Deterministic NMP verification: fixed node budget, compare depth reached and
best move, NMP-on vs NMP-off (PVS+LMR both). NMP should reach equal-or-deeper.
Usage: python nmp_depth.py [positions] [nodes]
"""
import random, sys
from shogi.position import Position
from shogi.movegen import generate_legal, make_move, move_to_usi
from shogi.search import Search
from shogi.evaluate import evaluate
BIG_T = 10 ** 9

def gen_positions(n, seed=1):
    rng = random.Random(seed); out = []
    while len(out) < n:
        pos = Position.startpos(); ok = True
        for _ in range(rng.randint(6, 40)):
            legal = generate_legal(pos)
            if not legal: ok = False; break
            make_move(pos, rng.choice(legal))
        if ok and generate_legal(pos):
            out.append(pos.clone())
    return out

def run(pos, nmp, nodes):
    s = Search(); s.eval_fn = evaluate; s.use_pvs = True; s.use_lmr = True
    s.use_nmp = nmp
    info = {"depth": 0, "mv": ""}
    def cap(line, **k):
        t = line.split()
        try:
            info["depth"] = int(t[t.index("depth")+1])
            info["mv"] = t[t.index("pv")+1]
        except Exception:
            pass
    mv = s.think(pos, BIG_T, max_depth=40, info=cap, max_nodes=nodes)
    return info["depth"], move_to_usi(mv) if mv else ""

def main():
    npos = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    nodes = int(sys.argv[2]) if len(sys.argv) > 2 else 12000
    positions = gen_positions(npos)
    don_s = doff_s = same = deeper = shallower = 0
    for p in positions:
        doff, moff = run(p.clone(), False, nodes)
        don, mon = run(p.clone(), True, nodes)
        doff_s += doff; don_s += don
        if mon == moff: same += 1
        if don > doff: deeper += 1
        elif don < doff: shallower += 1
    print(f"positions={npos} nodes={nodes}")
    print(f"avg depth  NMP-off={doff_s/npos:.2f}  NMP-on={don_s/npos:.2f}")
    print(f"NMP deeper in {deeper}, shallower in {shallower}, equal in "
          f"{npos-deeper-shallower}")
    print(f"same best move: {same}/{npos}")

if __name__ == "__main__":
    main()