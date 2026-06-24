"""Hand-crafted evaluation.

evaluate()    - material + position + king safety (current, stronger)
evaluate_v1() - the earlier material+light-position version, kept for
                head-to-head benchmarking (see match.py).

Score is from the perspective of pos.turn (positive = good to move), for negamax.
"""

from .position import (
    Position, PAWN, LANCE, KNIGHT, SILVER, GOLD, BISHOP, ROOK, KING,
    PPAWN, PLANCE, PKNIGHT, PSILVER, PBISHOP, PROOK,
    SENTE, GOTE, HAND_TYPES, sq_rank, sq_file,
)

VALUE = [0] * 14
VALUE[PAWN] = 90
VALUE[LANCE] = 315
VALUE[KNIGHT] = 405
VALUE[SILVER] = 495
VALUE[GOLD] = 540
VALUE[BISHOP] = 855
VALUE[ROOK] = 990
VALUE[KING] = 15000
VALUE[PPAWN] = 540
VALUE[PLANCE] = 540
VALUE[PKNIGHT] = 540
VALUE[PSILVER] = 540
VALUE[PBISHOP] = 945
VALUE[PROOK] = 1395

HAND_VALUE = [int(VALUE[pt] * 1.10) for pt in range(14)]

# Weight of an enemy piece menacing the squares around a king (per piece type).
ATK = [6, 10, 10, 14, 16, 22, 28, 0, 16, 14, 14, 16, 30, 38]
# Value of a friendly piece shielding (adjacent to) its own king.
DEF = [8, 8, 8, 28, 32, 12, 12, 0, 24, 24, 24, 26, 16, 16]

MATE = 100000


def _cheby(a, b):
    return max(abs(sq_file(a) - sq_file(b)), abs(sq_rank(a) - sq_rank(b)))


def evaluate(pos):
    b = pos.board
    ks = pos.king_sq
    score = 0
    danger = [0, 0]
    shield = [0, 0]
    for sq in range(81):
        v = b[sq]
        if not v:
            continue
        c, pt = Position.dec(v)
        val = VALUE[pt]
        if pt != KING:
            r = sq_rank(sq)
            adv = (9 - r) if c == SENTE else (r - 1)
            val += adv * 2
            val += 4 - abs(5 - sq_file(sq))
        score += val if c == SENTE else -val
        if pt != KING:
            ek = ks[1 - c]
            if ek >= 0:
                d = _cheby(sq, ek)
                if d <= 2:
                    danger[1 - c] += ATK[pt] * (3 - d)
            ok = ks[c]
            if ok >= 0 and _cheby(sq, ok) == 1:
                shield[c] += DEF[pt]
    for c in (SENTE, GOTE):
        h = pos.hands[c]
        s = sum(h[pt] * HAND_VALUE[pt] for pt in HAND_TYPES)
        score += s if c == SENTE else -s
    score += shield[SENTE] - danger[SENTE] - shield[GOTE] + danger[GOTE]
    return score if pos.turn == SENTE else -score


def evaluate_v1(pos):
    b = pos.board
    score = 0
    for sq in range(81):
        v = b[sq]
        if not v:
            continue
        c, pt = Position.dec(v)
        val = VALUE[pt]
        if pt != KING:
            r = sq_rank(sq)
            adv = (9 - r) if c == SENTE else (r - 1)
            val += adv * 2
            val += 4 - abs(5 - sq_file(sq))
        score += val if c == SENTE else -val
    for c in (SENTE, GOTE):
        h = pos.hands[c]
        s = sum(h[pt] * HAND_VALUE[pt] for pt in HAND_TYPES)
        score += s if c == SENTE else -s
    return score if pos.turn == SENTE else -score