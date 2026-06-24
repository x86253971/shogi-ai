"""Hand-crafted evaluation, with benchmarkable versions.

evaluate()    - v3: material + position + king-safety + king placement (PST)
evaluate_v2() - king-safety only (no king PST)
evaluate_v1() - material + light position only

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

ATK = [6, 10, 10, 14, 16, 22, 28, 0, 16, 14, 14, 16, 30, 38]
DEF = [8, 8, 8, 28, 32, 12, 12, 0, 24, 24, 24, 26, 16, 16]

# King placement by rank, from Sente's view (rank 1 = enemy back, 9 = own back).
# Strongly prefers staying home; punishes a king that wanders forward/centre.
KING_RANK = [-115, -90, -68, -48, -28, -10, 6, 22, 34]

MATE = 100000


def _cheby(a, b):
    return max(abs(sq_file(a) - sq_file(b)), abs(sq_rank(a) - sq_rank(b)))


def _core(pos, king_pst):
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
            ek = ks[1 - c]
            if ek >= 0:
                d = _cheby(sq, ek)
                if d <= 2:
                    danger[1 - c] += ATK[pt] * (3 - d)
            ok = ks[c]
            if ok >= 0 and _cheby(sq, ok) == 1:
                shield[c] += DEF[pt]
        else:
            score += val if c == SENTE else -val
            if king_pst:
                r = sq_rank(sq)
                if c == SENTE:
                    score += KING_RANK[r - 1]
                else:
                    score -= KING_RANK[9 - r]
    for c in (SENTE, GOTE):
        h = pos.hands[c]
        s = sum(h[pt] * HAND_VALUE[pt] for pt in HAND_TYPES)
        score += s if c == SENTE else -s
    score += shield[SENTE] - danger[SENTE] - shield[GOTE] + danger[GOTE]
    return score if pos.turn == SENTE else -score


def evaluate(pos):
    return _core(pos, king_pst=True)


def evaluate_v2(pos):
    return _core(pos, king_pst=False)


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