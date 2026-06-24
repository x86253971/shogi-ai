"""Shogi board, SFEN I/O, attack detection (table-driven), Zobrist hashing.

Square indexing: sq = (rank-1)*9 + (9-file). Sente (Black, 0) moves toward
rank 1 (index decreasing); Gote (White, 1) toward rank 9.
"""

import random as _random

PAWN, LANCE, KNIGHT, SILVER, GOLD, BISHOP, ROOK, KING = range(8)
PPAWN, PLANCE, PKNIGHT, PSILVER, PBISHOP, PROOK = range(8, 14)
NUM_PTYPES = 14
SENTE, GOTE = 0, 1

PROMOTE = [PPAWN, PLANCE, PKNIGHT, PSILVER, -1, PBISHOP, PROOK,
           -1, -1, -1, -1, -1, -1, -1]
UNPROMOTE = [PAWN, LANCE, KNIGHT, SILVER, GOLD, BISHOP, ROOK, KING,
             PAWN, LANCE, KNIGHT, SILVER, BISHOP, ROOK]
HAND_TYPES = [PAWN, LANCE, KNIGHT, SILVER, GOLD, BISHOP, ROOK]

USI_DROP_CHAR = {PAWN: "P", LANCE: "L", KNIGHT: "N", SILVER: "S",
                 GOLD: "G", BISHOP: "B", ROOK: "R"}
SFEN_CHAR = ["P", "L", "N", "S", "G", "B", "R", "K"]
SFEN_PROM_CHAR = {PPAWN: "P", PLANCE: "L", PKNIGHT: "N", PSILVER: "S",
                  PBISHOP: "B", PROOK: "R"}
CHAR_TO_TYPE = {"P": PAWN, "L": LANCE, "N": KNIGHT, "S": SILVER,
                "G": GOLD, "B": BISHOP, "R": ROOK, "K": KING}
DISP = ["P", "L", "N", "S", "G", "B", "R", "K",
        "+P", "+L", "+N", "+S", "+B", "+R"]

_rng = _random.Random(0xC0FFEE)
ZOB_PIECE = [[_rng.getrandbits(64) for _ in range(29)] for _ in range(81)]
ZOB_HAND = [[[_rng.getrandbits(64) for _ in range(19)] for _ in range(7)]
            for _ in range(2)]
ZOB_SIDE = _rng.getrandbits(64)

# Decode tables indexed by piece value (1..28); 0 = empty.
PCOLOR = [0] * 29
PTYPE = [0] * 29
for _v in range(1, 29):
    PCOLOR[_v] = (_v - 1) // NUM_PTYPES
    PTYPE[_v] = (_v - 1) % NUM_PTYPES

_GOLDSET = frozenset({GOLD, PPAWN, PLANCE, PKNIGHT, PSILVER})
_BISHOPSET = frozenset({BISHOP, PBISHOP})
_ROOKSET = frozenset({ROOK, PROOK})


def sq_file(sq):
    return 9 - (sq % 9)


def sq_rank(sq):
    return sq // 9 + 1


def make_sq(file, rank):
    return (rank - 1) * 9 + (9 - file)


def sq_to_usi(sq):
    return f"{sq_file(sq)}{chr(ord('a') + sq_rank(sq) - 1)}"


def usi_to_sq(s):
    return make_sq(int(s[0]), ord(s[1]) - ord("a") + 1)


_GOLD_STEPS_S = [(-1, 0), (-1, -1), (-1, 1), (0, -1), (0, 1), (1, 0)]
_SILVER_STEPS_S = [(-1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]
_KING_STEPS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
_KNIGHT_STEPS_S = [(-2, -1), (-2, 1)]
_BISHOP_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
_ROOK_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def _mirror(steps):
    return [(-dr, df) for dr, df in steps]


_GOLD_STEPS = [_GOLD_STEPS_S, _mirror(_GOLD_STEPS_S)]
_SILVER_STEPS = [_SILVER_STEPS_S, _mirror(_SILVER_STEPS_S)]
_KNIGHT_STEPS = [_KNIGHT_STEPS_S, _mirror(_KNIGHT_STEPS_S)]


def step_targets(sq, steps):
    f, r = sq_file(sq), sq_rank(sq)
    for dr, df in steps:
        nf, nr = f + df, r + dr
        if 1 <= nf <= 9 and 1 <= nr <= 9:
            yield make_sq(nf, nr)


# --- Precomputed attack-origin tables (built once) ---
def _step_from(steps_by_color):
    tbl = [[[] for _ in range(81)] for _ in range(2)]
    for opp in (0, 1):
        for sq in range(81):
            f0, r0 = sq_file(sq), sq_rank(sq)
            for dr, df in steps_by_color[opp]:
                nf, nr = f0 - df, r0 - dr
                if 1 <= nf <= 9 and 1 <= nr <= 9:
                    tbl[opp][sq].append(make_sq(nf, nr))
    return tbl


GOLD_FROM = _step_from(_GOLD_STEPS)
SILVER_FROM = _step_from(_SILVER_STEPS)
KNIGHT_FROM = _step_from(_KNIGHT_STEPS)

KING_FROM = [[] for _ in range(81)]
for _sq in range(81):
    _f0, _r0 = sq_file(_sq), sq_rank(_sq)
    for _dr, _df in _KING_STEPS:
        _nf, _nr = _f0 + _df, _r0 + _dr
        if 1 <= _nf <= 9 and 1 <= _nr <= 9:
            KING_FROM[_sq].append(make_sq(_nf, _nr))

PAWN_FROM = [[-1] * 81 for _ in range(2)]
for _opp in (0, 1):
    _pdr = -1 if _opp == SENTE else 1
    for _sq in range(81):
        _r = sq_rank(_sq) - _pdr
        if 1 <= _r <= 9:
            PAWN_FROM[_opp][_sq] = make_sq(sq_file(_sq), _r)

LANCE_RAY = [[[] for _ in range(81)] for _ in range(2)]
for _opp in (0, 1):
    _dr = 1 if _opp == SENTE else -1
    for _sq in range(81):
        _f0, _r0 = sq_file(_sq), sq_rank(_sq)
        _r = _r0 + _dr
        while 1 <= _r <= 9:
            LANCE_RAY[_opp][_sq].append(make_sq(_f0, _r))
            _r += _dr


def _rays(sq, dirs):
    out = []
    f0, r0 = sq_file(sq), sq_rank(sq)
    for dr, df in dirs:
        ray = []
        f, r = f0 + df, r0 + dr
        while 1 <= f <= 9 and 1 <= r <= 9:
            ray.append(make_sq(f, r))
            f += df
            r += dr
        if ray:
            out.append(tuple(ray))
    return out


BISHOP_RAYS = [_rays(sq, _BISHOP_DIRS) for sq in range(81)]
ROOK_RAYS = [_rays(sq, _ROOK_DIRS) for sq in range(81)]

# Per-square file/rank and pairwise Chebyshev distance (for evaluation).
FILE_OF = [sq_file(s) for s in range(81)]
RANK_OF = [sq_rank(s) for s in range(81)]
CHEBY = [[max(abs(FILE_OF[a] - FILE_OF[b]), abs(RANK_OF[a] - RANK_OF[b]))
          for b in range(81)] for a in range(81)]

class Position:
    __slots__ = ("board", "hands", "turn", "ply", "king_sq", "zob")

    def __init__(self):
        self.board = [0] * 81
        self.hands = [[0] * 7, [0] * 7]
        self.turn = SENTE
        self.ply = 1
        self.king_sq = [-1, -1]
        self.zob = 0

    @staticmethod
    def enc(color, ptype):
        return 1 + color * NUM_PTYPES + ptype

    @staticmethod
    def dec(v):
        v -= 1
        return v // NUM_PTYPES, v % NUM_PTYPES

    def clone(self):
        p = Position()
        p.board = self.board[:]
        p.hands = [self.hands[0][:], self.hands[1][:]]
        p.turn = self.turn
        p.ply = self.ply
        p.king_sq = self.king_sq[:]
        p.zob = self.zob
        return p

    @classmethod
    def from_sfen(cls, sfen):
        p = cls()
        parts = sfen.split()
        board_s, turn_s, hand_s = parts[0], parts[1], parts[2]
        p.ply = int(parts[3]) if len(parts) > 3 else 1
        sq = 0
        promoted = False
        for ch in board_s:
            if ch == "/":
                continue
            if ch == "+":
                promoted = True
                continue
            if ch.isdigit():
                sq += int(ch)
                continue
            color = SENTE if ch.isupper() else GOTE
            base = CHAR_TO_TYPE[ch.upper()]
            ptype = PROMOTE[base] if promoted else base
            promoted = False
            p.board[sq] = cls.enc(color, ptype)
            if ptype == KING:
                p.king_sq[color] = sq
            sq += 1
        p.turn = SENTE if turn_s == "b" else GOTE
        if hand_s != "-":
            num = 0
            for ch in hand_s:
                if ch.isdigit():
                    num = num * 10 + int(ch)
                    continue
                color = SENTE if ch.isupper() else GOTE
                ptype = CHAR_TO_TYPE[ch.upper()]
                p.hands[color][ptype] += num if num else 1
                num = 0
        p.zob = p.compute_zobrist()
        return p

    @classmethod
    def startpos(cls):
        return cls.from_sfen(
            "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1")

    def compute_zobrist(self):
        h = 0
        for sq in range(81):
            v = self.board[sq]
            if v:
                h ^= ZOB_PIECE[sq][v]
        for c in (SENTE, GOTE):
            hc = self.hands[c]
            for pt in range(7):
                cnt = hc[pt]
                if cnt:
                    h ^= ZOB_HAND[c][pt][cnt]
        if self.turn == GOTE:
            h ^= ZOB_SIDE
        return h

    def to_sfen(self):
        rows = []
        for r in range(1, 10):
            row = ""
            empty = 0
            for f in range(9, 0, -1):
                v = self.board[make_sq(f, r)]
                if v == 0:
                    empty += 1
                    continue
                if empty:
                    row += str(empty)
                    empty = 0
                color, ptype = self.dec(v)
                if ptype >= PPAWN:
                    ch = "+" + SFEN_PROM_CHAR[ptype]
                else:
                    ch = SFEN_CHAR[ptype]
                row += ch if color == SENTE else ch.lower()
            if empty:
                row += str(empty)
            rows.append(row)
        board_s = "/".join(rows)
        turn_s = "b" if self.turn == SENTE else "w"
        hand_s = ""
        for color in (SENTE, GOTE):
            for pt in [ROOK, BISHOP, GOLD, SILVER, KNIGHT, LANCE, PAWN]:
                c = self.hands[color][pt]
                if c:
                    ch = USI_DROP_CHAR[pt]
                    hand_s += (str(c) if c > 1 else "") + (ch if color == SENTE else ch.lower())
        if not hand_s:
            hand_s = "-"
        return f"{board_s} {turn_s} {hand_s} {self.ply}"

    def is_attacked(self, sq, opp):
        b = self.board
        for o in GOLD_FROM[opp][sq]:
            v = b[o]
            if v and PCOLOR[v] == opp and PTYPE[v] in _GOLDSET:
                return True
        for o in SILVER_FROM[opp][sq]:
            v = b[o]
            if v and PCOLOR[v] == opp and PTYPE[v] == SILVER:
                return True
        for o in KNIGHT_FROM[opp][sq]:
            v = b[o]
            if v and PCOLOR[v] == opp and PTYPE[v] == KNIGHT:
                return True
        o = PAWN_FROM[opp][sq]
        if o >= 0:
            v = b[o]
            if v and PCOLOR[v] == opp and PTYPE[v] == PAWN:
                return True
        for o in KING_FROM[sq]:
            v = b[o]
            if v and PCOLOR[v] == opp and PTYPE[v] == KING:
                return True
        for o in LANCE_RAY[opp][sq]:
            v = b[o]
            if v:
                if PCOLOR[v] == opp and PTYPE[v] == LANCE:
                    return True
                break
        for ray in BISHOP_RAYS[sq]:
            first = True
            for o in ray:
                v = b[o]
                if v:
                    if PCOLOR[v] == opp and (PTYPE[v] in _BISHOPSET
                                             or (first and PTYPE[v] == PROOK)):
                        return True
                    break
                first = False
        for ray in ROOK_RAYS[sq]:
            first = True
            for o in ray:
                v = b[o]
                if v:
                    if PCOLOR[v] == opp and (PTYPE[v] in _ROOKSET
                                             or (first and PTYPE[v] == PBISHOP)):
                        return True
                    break
                first = False
        return False

    def in_check(self, color=None):
        if color is None:
            color = self.turn
        ks = self.king_sq[color]
        if ks < 0:
            return False
        return self.is_attacked(ks, 1 - color)