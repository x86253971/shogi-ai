"""Hand-crafted evaluation (material + light positional terms).

Returns a score from the perspective of pos.turn (positive = good for the
side to move), suitable for negamax search.
"""

from .position import (
    Position, PAWN, LANCE, KNIGHT, SILVER, GOLD, BISHOP, ROOK, KING,
    PPAWN, PLANCE, PKNIGHT, PSILVER, PBISHOP, PROOK,
    SENTE, GOTE, HAND_TYPES, sq_rank, sq_file,
)

# Material value by piece type (board).
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

# In-hand value (a piece in hand is worth slightly more, classic heuristic).
HAND_VALUE = [int(VALUE[pt] * 1.10) for pt in range(14)]

MATE = 100000


def evaluate(pos):
    b = pos.board
    score = 0  # from Sente's perspective
    for sq in range(81):
        v = b[sq]
        if not v:
            continue
        c, pt = Position.dec(v)
        val = VALUE[pt]
        # Light positional bonus: advance pieces (except king) toward enemy,
        # and reward central files a little.
        if pt != KING:
            r = sq_rank(sq)
            adv = (9 - r) if c == SENTE else (r - 1)  # 0..8 toward enemy camp
            val += adv * 2
            f = sq_file(sq)
            val += (4 - abs(5 - f))  # center files slightly better
        else:
            # King safety: stay back early; penalty handled lightly via attackers.
            pass
        score += val if c == SENTE else -val
    for c in (SENTE, GOTE):
        h = pos.hands[c]
        s = sum(h[pt] * HAND_VALUE[pt] for pt in HAND_TYPES)
        score += s if c == SENTE else -s
    return score if pos.turn == SENTE else -score