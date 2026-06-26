"""Deterministic RFP verification: fixed node budget, depth + best move,
RFP-on vs RFP-off (PVS+LMR+NMP all on).
Usage: python rfp_depth.py [positions] [nodes]
"""
import random, sys
from shogi.position import Position
from shogi.movegen import generate_legal, make_move, move_to_usi
from shogi.search import Search
from shogi.evaluate import evaluate

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

def run(pos, rfp, nodes):
    s = Search(); s.eval_fn = evaluate
    s.use_pvs = s.use_lmr = s.use_nmp = True
    s.use_rfp = rfp
    info = {"depth": 0, "mv": ""}
    def cap(line, **k):
        t = line.split()
        try:
            info["depth"] = int(t[t.index("depth")+1])
            info["mv"] = t[t.index("pv")+1]
        except Exception:
            pass
    mv = s.think(pos, 10**9, max_depth=40, info=cap, max_nodes=nodes)
    return info["depth"], move_to_usi(mv) if mv else ""

def main():
    npos = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    nodes = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    positions = gen_positions(npos)
    on_s = off_s = same = deeper = shallower = 0
    for p in positions:
        doff, moff = run(p.clone(), False, nodes)
        don, mon = run(p.clone(), True, nodes)
        off_s += doff; on_s += don
        if mon == moff: same += 1
        if don > doff: deeper += 1
        elif don < doff: shallower += 1
    print(f"positions={npos} nodes={nodes}")
    print(f"avg depth  RFP-off={off_s/npos:.2f}  RFP-on={on_s/npos:.2f}")
    print(f"RFP deeper in {deeper}, shallower in {shallower}, equal in "
          f"{npos-deeper-shallower}")
    print(f"same best move: {same}/{npos}")

if __name__ == "__main__":
    main()