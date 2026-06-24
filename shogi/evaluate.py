"""Hand-crafted evaluation, with benchmarkable versions.

evaluate()    - v3: material + position + king-safety + king placement (PST)
evaluate_v2() - king-safety only (no king PST)
evaluate_v1() - material + light position only

Score is from the perspective of pos.turn (positive = good to move), for negamax.
Uses precomputed FILE_OF / RANK_OF / CHEBY tables for speed.
"""

from .position import (
    Position, PAWN, LANCE, KNIGHT, SILVER, GOLD, BISHOP, ROOK, KING,
    PPAWN, PLANCE, PKNIGHT, PSILVER, PBISHOP, PROOK,
    SENTE, GOTE, HAND_TYPES, FILE_OF, RANK_OF, CHEBY, PCOLOR, PTYPE,
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
KING_RANK = [-115, -90, -68, -48, -28, -10, 6, 22, 34]

# Per-piece advancement+center positional bonus, precomputed by (ptype, sq).
_FCENTER = [4 - abs(5 - FILE_OF[s]) for s in range(81)]
MATE = 100000


def _core(pos, king_pst):
    b = pos.board
    ks = pos.king_sq
    ks0, ks1 = ks[SENTE], ks[GOTE]
    score = 0
    d0 = s0 = d1 = s1 = 0  # danger/shield for sente(0)/gote(1)
    for sq in range(81):
        v = b[sq]
        if not v:
            continue
        c = PCOLOR[v]
        pt = PTYPE[v]
        val = VALUE[pt]
        if pt != KING:
            if c == SENTE:
                val += (9 - RANK_OF[sq]) * 2 + _FCENTER[sq]
                score += val
                if ks1 >= 0:
                    dd = CHEBY[sq][ks1]
                    if dd <= 2:
                        d1 += ATK[pt] * (3 - dd)
                if ks0 >= 0 and CHEBY[sq][ks0] == 1:
                    s0 += DEF[pt]
            else:
                val += (RANK_OF[sq] - 1) * 2 + _FCENTER[sq]
                score -= val
                if ks0 >= 0:
                    dd = CHEBY[sq][ks0]
                    if dd <= 2:
                        d0 += ATK[pt] * (3 - dd)
                if ks1 >= 0 and CHEBY[sq][ks1] == 1:
                    s1 += DEF[pt]
        else:
            if c == SENTE:
                score += val
                if king_pst:
                    score += KING_RANK[RANK_OF[sq] - 1]
            else:
                score -= val
                if king_pst:
                    score -= KING_RANK[9 - RANK_OF[sq]]
    for c in (SENTE, GOTE):
        h = pos.hands[c]
        ss = sum(h[pt] * HAND_VALUE[pt] for pt in HAND_TYPES)
        score += ss if c == SENTE else -ss
    score += s0 - d0 - s1 + d1
    return score if pos.turn == SENTE else -score


def evaluate(pos):
    return _core(pos, True)


def evaluate_v2(pos):
    return _core(pos, False)


def evaluate_v1(pos):
    b = pos.board
    score = 0
    for sq in range(81):
        v = b[sq]
        if not v:
            continue
        c = PCOLOR[v]
        pt = PTYPE[v]
        val = VALUE[pt]
        if pt != KING:
            adv = (9 - RANK_OF[sq]) if c == SENTE else (RANK_OF[sq] - 1)
            val += adv * 2 + _FCENTER[sq]
        score += val if c == SENTE else -val
    for c in (SENTE, GOTE):
        h = pos.hands[c]
        ss = sum(h[pt] * HAND_VALUE[pt] for pt in HAND_TYPES)
        score += ss if c == SENTE else -ss
    return score if pos.turn == SENTE else -score