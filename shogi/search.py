"""Alpha-beta search with iterative deepening, quiescence, time control."""

import time
from .movegen import (
    generate_legal, make_move, unmake_move,
    m_to, m_from, m_is_drop, m_is_promo, move_to_usi,
)
from .position import Position
from .evaluate import evaluate, VALUE, MATE


class TimeUp(Exception):
    pass


class Search:
    def __init__(self):
        self.nodes = 0
        self.deadline = 0.0
        self.stop = False

    def _check_time(self):
        if self.nodes & 1023 == 0 and time.time() >= self.deadline:
            raise TimeUp

    def _order(self, pos, moves, tt_move=None):
        b = pos.board
        def score(m):
            s = 0
            if m == tt_move:
                return 1 << 30
            if not m_is_drop(m):
                cap = b[m_to(m)]
                if cap:
                    _, cpt = Position.dec(cap)
                    _, mpt = Position.dec(b[m_from(m)])
                    s += 1000 + VALUE[cpt] - VALUE[mpt] // 10
                if m_is_promo(m):
                    s += 600
            return s
        moves.sort(key=score, reverse=True)
        return moves

    def _qsearch(self, pos, alpha, beta, ply):
        self.nodes += 1
        self._check_time()
        in_check = pos.in_check(pos.turn)
        if not in_check:
            stand = evaluate(pos)
            if stand >= beta:
                return beta
            if stand > alpha:
                alpha = stand
        legal = generate_legal(pos)
        if not legal:
            return -MATE + ply if in_check else evaluate(pos)
        b = pos.board
        moves = legal if in_check else [
            m for m in legal
            if (not m_is_drop(m) and b[m_to(m)]) or m_is_promo(m)
        ]
        if not in_check and not moves:
            return alpha
        self._order(pos, moves)
        for m in moves:
            cap = make_move(pos, m)
            val = -self._qsearch(pos, -beta, -alpha, ply + 1)
            unmake_move(pos, m, cap)
            if val >= beta:
                return beta
            if val > alpha:
                alpha = val
        return alpha

    def _negamax(self, pos, depth, alpha, beta, ply):
        self.nodes += 1
        self._check_time()
        legal = generate_legal(pos)
        if not legal:
            return -MATE + ply  # no legal move = loss (mate or stalemate)
        if depth <= 0:
            return self._qsearch(pos, alpha, beta, ply)
        self._order(pos, legal)
        best = -MATE * 2
        for m in legal:
            cap = make_move(pos, m)
            val = -self._negamax(pos, depth - 1, -beta, -alpha, ply + 1)
            unmake_move(pos, m, cap)
            if val > best:
                best = val
                if val > alpha:
                    alpha = val
            if alpha >= beta:
                break
        return best

    def think(self, pos, max_time_s, max_depth=64, info=print):
        self.nodes = 0
        self.deadline = time.time() + max_time_s
        start = time.time()
        legal = generate_legal(pos)
        if not legal:
            return None
        best_move = legal[0]
        for depth in range(1, max_depth + 1):
            alpha, beta = -MATE * 2, MATE * 2
            local_best = None
            best_val = -MATE * 3
            ordered = self._order(pos, list(legal), tt_move=best_move)
            try:
                for m in ordered:
                    cap = make_move(pos, m)
                    val = -self._negamax(pos, depth - 1, -beta, -alpha, 1)
                    unmake_move(pos, m, cap)
                    if val > best_val:
                        best_val = val
                        local_best = m
                        if val > alpha:
                            alpha = val
            except TimeUp:
                break
            if local_best is not None:
                best_move = local_best
                elapsed = time.time() - start
                nps = int(self.nodes / elapsed) if elapsed > 0 else 0
                if abs(best_val) > MATE - 1000:
                    mate_n = (MATE - abs(best_val) + 1) // 2
                    sc = f"mate {mate_n if best_val > 0 else -mate_n}"
                else:
                    sc = f"cp {best_val}"
                info(f"info depth {depth} score {sc} nodes {self.nodes} "
                     f"nps {nps} time {int(elapsed*1000)} pv {move_to_usi(best_move)}")
                if abs(best_val) > MATE - 1000:
                    break
            if time.time() >= self.deadline:
                break
        return best_move