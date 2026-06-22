"""Shogi board representation, SFEN I/O, move generation, attack detection.

Square indexing: sq = (rank-1)*9 + (9-file), so sq 0 = file9/rank1 (top-left in
SFEN reading order), sq 80 = file1/rank9. Sente (Black, color 0) moves toward
rank 1 (index decreasing). Gote (White, color 1) moves toward rank 9.
"""

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


# Step/slide tables as (d_rank, d_file). Sente forward = rank decreases.
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


class Position:
    __slots__ = ("board", "hands", "turn", "ply", "king_sq", "history")

    def __init__(self):
        self.board = [0] * 81
        self.hands = [[0] * 7, [0] * 7]
        self.turn = SENTE
        self.ply = 1
        self.king_sq = [-1, -1]
        self.history = []

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
        p.history = self.history[:]
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
        return p

    @classmethod
    def startpos(cls):
        return cls.from_sfen(
            "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1")

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

    def key(self):
        return self.to_sfen().rsplit(" ", 1)[0]

    def is_attacked(self, sq, opp):
        b = self.board
        f0, r0 = sq_file(sq), sq_rank(sq)

        def at(f, r):
            return b[make_sq(f, r)] if (1 <= f <= 9 and 1 <= r <= 9) else None

        for dr, df in _GOLD_STEPS[opp]:
            pc = at(f0 - df, r0 - dr)
            if pc:
                c, pt = self.dec(pc)
                if c == opp and pt in (GOLD, PPAWN, PLANCE, PKNIGHT, PSILVER):
                    return True
        for dr, df in _SILVER_STEPS[opp]:
            pc = at(f0 - df, r0 - dr)
            if pc:
                c, pt = self.dec(pc)
                if c == opp and pt == SILVER:
                    return True
        for dr, df in _KNIGHT_STEPS[opp]:
            pc = at(f0 - df, r0 - dr)
            if pc:
                c, pt = self.dec(pc)
                if c == opp and pt == KNIGHT:
                    return True
        pawn_dr = -1 if opp == SENTE else 1
        pc = at(f0, r0 - pawn_dr)
        if pc:
            c, pt = self.dec(pc)
            if c == opp and pt == PAWN:
                return True
        for dr, df in _KING_STEPS:
            pc = at(f0 - df, r0 - dr)
            if pc:
                c, pt = self.dec(pc)
                if c == opp and pt == KING:
                    return True
        # Lance: sits behind sq along the file relative to opp forward.
        dr, df = (1, 0) if opp == SENTE else (-1, 0)
        f, r = f0 + df, r0 + dr
        while 1 <= f <= 9 and 1 <= r <= 9:
            v = b[make_sq(f, r)]
            if v:
                c, pt = self.dec(v)
                if c == opp and pt == LANCE:
                    return True
                break
            f += df
            r += dr
        # Diagonal sliders: bishop/horse; dragon adds one diagonal step (dist 1).
        for dr, df in _BISHOP_DIRS:
            f, r = f0 + df, r0 + dr
            dist = 1
            while 1 <= f <= 9 and 1 <= r <= 9:
                v = b[make_sq(f, r)]
                if v:
                    c, pt = self.dec(v)
                    if c == opp and (pt in (BISHOP, PBISHOP) or (dist == 1 and pt == PROOK)):
                        return True
                    break
                f += df
                r += dr
                dist += 1
        # Orthogonal sliders: rook/dragon; horse adds one orthogonal step (dist 1).
        for dr, df in _ROOK_DIRS:
            f, r = f0 + df, r0 + dr
            dist = 1
            while 1 <= f <= 9 and 1 <= r <= 9:
                v = b[make_sq(f, r)]
                if v:
                    c, pt = self.dec(v)
                    if c == opp and (pt in (ROOK, PROOK) or (dist == 1 and pt == PBISHOP)):
                        return True
                    break
                f += df
                r += dr
                dist += 1
        return False

    def in_check(self, color=None):
        if color is None:
            color = self.turn
        ks = self.king_sq[color]
        if ks < 0:
            return False
        return self.is_attacked(ks, 1 - color)