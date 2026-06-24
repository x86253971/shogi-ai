from shogi.position import Position, SENTE, GOTE
from shogi.movegen import generate_legal, make_move
from shogi.search import Search
import random
ok=True
for g in range(10):
    rng=random.Random(700+g)
    pos=Position.startpos(); s=Search()
    for _ in range(160):
        legal=generate_legal(pos)
        if not legal: break
        best=s.think(pos,10**9,max_depth=40,info=lambda*a:None,max_nodes=2500)
        if best not in legal:
            print("ILLEGAL pick game",g); ok=False; break
        make_move(pos,best)
    if not ok: break
print("ROBUSTNESS OK: 10 games, no crash/illegal" if ok else "FAILED")