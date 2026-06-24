"""Strength match between two evaluation functions (time-bounded per move).

Each game starts from a random short opening (same for both sides) for variety,
then both engines play with a fixed wall-clock time per move (bounded, so check
extensions cannot explode). Colors / eval roles alternate. Repetition history is
passed so engines avoid shuffling.

Usage: python match.py [games] [seconds_per_move]
"""

import random
import sys
from shogi.position import Position, SENTE, GOTE
from shogi.movegen import generate_legal, make_move, usi_to_move, move_to_usi
from shogi.search import Search
from shogi.evaluate import evaluate, evaluate_v1


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


def play_game(eval_sente, eval_gote, time_s, opening, max_ply=160):
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
        best = s.think(pos, time_s, max_depth=20, info=lambda *_: None,
                       history=hist[:-1])
        make_move(pos, best)
        hist.append(pos.zob)
    return None


def main():
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    time_s = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
    new_pts = old_pts = draws = 0
    for g in range(games):
        opening = random_opening(2000 + g)
        new_is_sente = (g % 2 == 0)
        if new_is_sente:
            winner = play_game(evaluate, evaluate_v1, time_s, opening)
            new_color = SENTE
        else:
            winner = play_game(evaluate_v1, evaluate, time_s, opening)
            new_color = GOTE
        if winner is None:
            draws += 1; res = "draw"
        elif winner == new_color:
            new_pts += 1; res = "NEW wins"
        else:
            old_pts += 1; res = "old wins"
        print(f"game {g+1}/{games} (new={'S' if new_is_sente else 'G'}): {res}", flush=True)
    print(f"\nRESULT  NEW(king-safety) {new_pts} - {old_pts} old   draws {draws}", flush=True)


if __name__ == "__main__":
    main()