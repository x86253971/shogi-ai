import sys, time
from shogi.position import Position
from shogi.movegen import generate_legal, make_move, unmake_move

def perft(pos, depth):
    if depth == 0:
        return 1
    n = 0
    for m in generate_legal(pos):
        cap = make_move(pos, m)
        n += perft(pos, depth - 1)
        unmake_move(pos, m, cap)
    return n

if __name__ == "__main__":
    pos = Position.startpos()
    expected = {1: 30, 2: 900, 3: 25470, 4: 719731}
    maxd = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    for d in range(1, maxd + 1):
        t = time.time()
        n = perft(pos, d)
        dt = time.time() - t
        exp = expected.get(d)
        tag = "OK" if exp == n else (f"EXPECTED {exp}" if exp else "?")
        print(f"perft {d}: {n:>9}  {tag}   ({dt:.2f}s)")