"""Strength match between two evaluation functions.

Default mode is a fixed NODE budget per move: deterministic and fast, so few
games give a clean signal. Random short openings add variety; repetition
history is passed so engines avoid shuffling.

Usage: python match.py [games] [nodes_per_move]
"""

import random
import sys
from shogi.position import Position, SENTE, GOTE
from shogi.movegen import generate_legal, make_move, usi_to_move, move_to_usi
from shogi.search import Search
from shogi.evaluate import evaluate, evaluate_v2, evaluate_v1

BIG_T = 10 ** 9


def random_opening(seed, plies=4):
    rng = random.Random(seed)
    pos = Position.startpos()
    moves = []
    for _ in range(plies):
        legal = generate_legal(pos)
        if not legal:
            break
        m = rng.choice(legal)
        make_move(pos, m)
        moves.append(move_to_usi(m))
    return moves


def play_game(eval_sente, eval_gote, nodes, opening, max_ply=160):
    pos = Position.startpos()
    hist = [pos.zob]
    for mv in opening:
        make_move(pos, usi_to_move(mv))
        hist.append(pos.zob)
    sA = Search(); sA.eval_fn = eval_sente
    sB = Search(); sB.eval_fn = eval_gote
    for _ in range(max_ply):
        legal = generate_legal(pos)
        if not legal:
            return GOTE if pos.turn == SENTE else SENTE
        s = sA if pos.turn == SENTE else sB
        best = s.think(pos, BIG_T, max_depth=30, info=lambda *_: None,
                       history=hist[:-1], max_nodes=nodes)
        make_move(pos, best)
        hist.append(pos.zob)
    return None


# A = challenger, B = baseline. Edit these two to choose what to compare.
EVAL_A, NAME_A = evaluate, "v3-kingPST"
EVAL_B, NAME_B = evaluate_v2, "v2-kingsafety"


def main():
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    nodes = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    a_pts = b_pts = draws = 0
    for g in range(games):
        opening = random_opening(3000 + g)
        a_is_sente = (g % 2 == 0)
        if a_is_sente:
            winner = play_game(EVAL_A, EVAL_B, nodes, opening)
            a_color = SENTE
        else:
            winner = play_game(EVAL_B, EVAL_A, nodes, opening)
            a_color = GOTE
        if winner is None:
            draws += 1; res = "draw"
        elif winner == a_color:
            a_pts += 1; res = f"{NAME_A} wins"
        else:
            b_pts += 1; res = f"{NAME_B} wins"
        print(f"game {g+1}/{games}: {res}", flush=True)
    print(f"\nRESULT  {NAME_A} {a_pts} - {b_pts} {NAME_B}   draws {draws}", flush=True)


if __name__ == "__main__":
    main()