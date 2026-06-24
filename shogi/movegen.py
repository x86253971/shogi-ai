"""Move encoding, make/unmake (with incremental Zobrist), legal move gen.

Move int layout:
  bits 0-6   : to square (0..80)
  bits 7-13  : from square (0..80); for drops this holds the dropped ptype
  bit 14     : promotion flag
  bit 15     : drop flag
"""

from .position import (
    Position, PAWN, LANCE, KNIGHT, SILVER, GOLD, BISHOP, ROOK, KING,
    PPAWN, PLANCE, PKNIGHT, PSILVER, PBISHOP, PROOK,
    SENTE, GOTE, PROMOTE, UNPROMOTE, HAND_TYPES,
    USI_DROP_CHAR, CHAR_TO_TYPE,
    make_sq, sq_file, sq_rank, sq_to_usi, usi_to_sq,
    _GOLD_STEPS, _SILVER_STEPS, _KING_STEPS, _KNIGHT_STEPS,
    _BISHOP_DIRS, _ROOK_DIRS, step_targets,
    ZOB_PIECE, ZOB_HAND, ZOB_SIDE,
)

DROP_BIT = 1 << 15
PROMO_BIT = 1 << 14


def mk_move(frm, to, promo=False):
    return to | (frm << 7) | (PROMO_BIT if promo else 0)


def mk_drop(ptype, to):
    return to | (ptype << 7) | DROP_BIT


def m_to(m):
    return m & 0x7F


def m_from(m):
    return (m >> 7) & 0x7F


def m_is_drop(m):
    return bool(m & DROP_BIT)


def m_is_promo(m):
    return bool(m & PROMO_BIT)


def move_to_usi(m):
    to = m_to(m)
    if m_is_drop(m):
        return f"{USI_DROP_CHAR[m_from(m)]}*{sq_to_usi(to)}"
    s = sq_to_usi(m_from(m)) + sq_to_usi(to)
    return s + "+" if m_is_promo(m) else s


def usi_to_move(s):
    if s[1] == "*":
        return mk_drop(CHAR_TO_TYPE[s[0].upper()], usi_to_sq(s[2:4]))
    frm = usi_to_sq(s[0:2])
    to = usi_to_sq(s[2:4])
    return mk_move(frm, to, len(s) > 4 and s[4] == "+")


def _in_zone(sq, color):
    r = sq_rank(sq)
    return r <= 3 if color == SENTE else r >= 7


def _must_promote(pt, to, color):
    r = sq_rank(to)
    if pt in (PAWN, LANCE):
        return r == 1 if color == SENTE else r == 9
    if pt == KNIGHT:
        return r <= 2 if color == SENTE else r >= 8
    return False


def _slide(b, sq, dirs):
    f0, r0 = sq_file(sq), sq_rank(sq)
    for dr, df in dirs:
        f, r = f0 + df, r0 + dr
        while 1 <= f <= 9 and 1 <= r <= 9:
            t = make_sq(f, r)
            yield t
            if b[t]:
                break
            f += df
            r += dr


def _piece_targets(pos, sq, c, pt):
    b = pos.board
    if pt == PAWN:
        dr = -1 if c == SENTE else 1
        yield from step_targets(sq, [(dr, 0)])
    elif pt == KNIGHT:
        yield from step_targets(sq, _KNIGHT_STEPS[c])
    elif pt == SILVER:
        yield from step_targets(sq, _SILVER_STEPS[c])
    elif pt in (GOLD, PPAWN, PLANCE, PKNIGHT, PSILVER):
        yield from step_targets(sq, _GOLD_STEPS[c])
    elif pt == KING:
        yield from step_targets(sq, _KING_STEPS)
    elif pt == LANCE:
        dr = -1 if c == SENTE else 1
        yield from _slide(b, sq, [(dr, 0)])
    elif pt == BISHOP:
        yield from _slide(b, sq, _BISHOP_DIRS)
    elif pt == ROOK:
        yield from _slide(b, sq, _ROOK_DIRS)
    elif pt == PBISHOP:
        yield from _slide(b, sq, _BISHOP_DIRS)
        yield from step_targets(sq, _ROOK_DIRS)
    elif pt == PROOK:
        yield from _slide(b, sq, _ROOK_DIRS)
        yield from step_targets(sq, _BISHOP_DIRS)


def generate_pseudo(pos):
    moves = []
    b = pos.board
    c = pos.turn
    for sq in range(81):
        v = b[sq]
        if not v:
            continue
        pc, pt = Position.dec(v)
        if pc != c:
            continue
        for to in _piece_targets(pos, sq, c, pt):
            tv = b[to]
            if tv and Position.dec(tv)[0] == c:
                continue
            if _must_promote(pt, to, c):
                moves.append(mk_move(sq, to, True))
            else:
                moves.append(mk_move(sq, to, False))
                if PROMOTE[pt] != -1 and (_in_zone(sq, c) or _in_zone(to, c)):
                    moves.append(mk_move(sq, to, True))
    _generate_drops(pos, moves)
    return moves


def _generate_drops(pos, moves):
    b = pos.board
    c = pos.turn
    hand = pos.hands[c]
    if not any(hand):
        return
    pawn_files = set()
    for sq in range(81):
        v = b[sq]
        if v:
            pc, pt = Position.dec(v)
            if pc == c and pt == PAWN:
                pawn_files.add(sq_file(sq))
    for pt in HAND_TYPES:
        if hand[pt] == 0:
            continue
        for to in range(81):
            if b[to]:
                continue
            r = sq_rank(to)
            if pt == PAWN:
                if sq_file(to) in pawn_files:
                    continue
                if (r == 1) if c == SENTE else (r == 9):
                    continue
            elif pt == LANCE:
                if (r == 1) if c == SENTE else (r == 9):
                    continue
            elif pt == KNIGHT:
                if (r <= 2) if c == SENTE else (r >= 8):
                    continue
            moves.append(mk_drop(pt, to))


def make_move(pos, m):
    """Apply move, update Zobrist, return captured piece value (0 if none)."""
    b = pos.board
    c = pos.turn
    to = m_to(m)
    z = pos.zob
    captured = 0
    if m_is_drop(m):
        pt = m_from(m)
        old = pos.hands[c][pt]
        z ^= ZOB_HAND[c][pt][old]
        pos.hands[c][pt] = old - 1
        if old - 1:
            z ^= ZOB_HAND[c][pt][old - 1]
        pv = Position.enc(c, pt)
        b[to] = pv
        z ^= ZOB_PIECE[to][pv]
    else:
        frm = m_from(m)
        v = b[frm]
        _, pt = Position.dec(v)
        captured = b[to]
        if captured:
            z ^= ZOB_PIECE[to][captured]
            _, cpt = Position.dec(captured)
            ht = UNPROMOTE[cpt]
            old = pos.hands[c][ht]
            if old:
                z ^= ZOB_HAND[c][ht][old]
            pos.hands[c][ht] = old + 1
            z ^= ZOB_HAND[c][ht][old + 1]
        newpt = PROMOTE[pt] if m_is_promo(m) else pt
        pv = Position.enc(c, newpt)
        b[to] = pv
        z ^= ZOB_PIECE[to][pv]
        z ^= ZOB_PIECE[frm][v]
        b[frm] = 0
        if newpt == KING:
            pos.king_sq[c] = to
    z ^= ZOB_SIDE
    pos.zob = z
    pos.turn = 1 - c
    pos.ply += 1
    return captured


def unmake_move(pos, m, captured):
    c = 1 - pos.turn  # mover
    b = pos.board
    to = m_to(m)
    z = pos.zob ^ ZOB_SIDE
    pos.turn = c
    pos.ply -= 1
    if m_is_drop(m):
        pt = m_from(m)
        pv = b[to]
        z ^= ZOB_PIECE[to][pv]
        b[to] = 0
        old = pos.hands[c][pt]
        if old:
            z ^= ZOB_HAND[c][pt][old]
        pos.hands[c][pt] = old + 1
        z ^= ZOB_HAND[c][pt][old + 1]
    else:
        frm = m_from(m)
        pv = b[to]
        _, newpt = Position.dec(pv)
        z ^= ZOB_PIECE[to][pv]
        pt = UNPROMOTE[newpt] if m_is_promo(m) else newpt
        ov = Position.enc(c, pt)
        b[frm] = ov
        z ^= ZOB_PIECE[frm][ov]
        b[to] = captured
        if captured:
            z ^= ZOB_PIECE[to][captured]
            _, cpt = Position.dec(captured)
            ht = UNPROMOTE[cpt]
            old = pos.hands[c][ht]
            z ^= ZOB_HAND[c][ht][old]
            pos.hands[c][ht] = old - 1
            if old - 1:
                z ^= ZOB_HAND[c][ht][old - 1]
        if pt == KING:
            pos.king_sq[c] = frm
    pos.zob = z


def _make_light(pos, m):
    """Board+king_sq-only make for legality tests (no zobrist/hands/ply)."""
    b = pos.board
    c = pos.turn
    to = m_to(m)
    if m_is_drop(m):
        b[to] = Position.enc(c, m_from(m))
        cap = 0
    else:
        frm = m_from(m)
        v = b[frm]
        _, pt = Position.dec(v)
        cap = b[to]
        newpt = PROMOTE[pt] if m_is_promo(m) else pt
        b[to] = Position.enc(c, newpt)
        b[frm] = 0
        if newpt == KING:
            pos.king_sq[c] = to
    pos.turn = 1 - c
    return cap


def _unmake_light(pos, m, cap):
    c = 1 - pos.turn
    b = pos.board
    to = m_to(m)
    pos.turn = c
    if m_is_drop(m):
        b[to] = 0
    else:
        frm = m_from(m)
        _, newpt = Position.dec(b[to])
        pt = UNPROMOTE[newpt] if m_is_promo(m) else newpt
        b[frm] = Position.enc(c, pt)
        b[to] = cap
        if pt == KING:
            pos.king_sq[c] = frm


def _has_any_legal(pos):
    for m in generate_pseudo(pos):
        cap = _make_light(pos, m)
        ok = not pos.in_check(1 - pos.turn)
        _unmake_light(pos, m, cap)
        if ok:
            return True
    return False


def generate_legal(pos):
    legal = []
    for m in generate_pseudo(pos):
        cap = _make_light(pos, m)
        mover = 1 - pos.turn
        if not pos.in_check(mover):
            ok = True
            if m_is_drop(m) and m_from(m) == PAWN and pos.in_check(pos.turn):
                if not _has_any_legal(pos):
                    ok = False
            if ok:
                legal.append(m)
        _unmake_light(pos, m, cap)
    return legal