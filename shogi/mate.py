"""Forced-mate (tsume) search: continuous-check mate detection.

find_mate(pos, max_plies) returns (move, mate_in_moves) if the side to move
can force checkmate by continuous checks within max_plies (odd) plies, else
(None, 0). Defender legality (including uchifuzume) comes from generate_legal,
so illegal pawn-drop mates are never counted.
"""

from .movegen import generate_legal, make_move, unmake_move, m_to


class _Abort(Exception):
    pass


def find_mate(pos, max_plies=7, node_cap=400000):
    state = {"n": 0}

    def tick():
        state["n"] += 1
        if state["n"] > node_cap:
            raise _Abort

    def mate_and(depth):
        # Defender to move (in check). True if defender is mated within depth.
        tick()
        legal = generate_legal(pos)
        if not legal:
            return True
        if depth <= 0:
            return False
        for m in legal:
            cap = make_move(pos, m)
            escaped = not mate_or(depth - 1)
            unmake_move(pos, m, cap)
            if escaped:
                return False
        return True

    def mate_or(depth):
        # Attacker to move. True if a checking move forces mate within depth.
        tick()
        if depth <= 0:
            return False
        for m in generate_legal(pos):
            cap = make_move(pos, m)
            ok = pos.in_check(pos.turn) and mate_and(depth - 1)
            unmake_move(pos, m, cap)
            if ok:
                return True
        return False

    try:
        for d in range(1, max_plies + 1, 2):
            for m in generate_legal(pos):
                cap = make_move(pos, m)
                solved = pos.in_check(pos.turn) and mate_and(d - 1)
                unmake_move(pos, m, cap)
                if solved:
                    return m, (d + 1) // 2
    except _Abort:
        return None, 0
    return None, 0