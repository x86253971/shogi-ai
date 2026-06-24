"""Alpha-beta search: iterative deepening, transposition table, quiescence,
killer moves and history heuristic, USI time control.

Time-out safety: a TimeUp raised mid-tree skips the pending unmake_move calls,
so think() snapshots the root position and restores it in the TimeUp handler.
"""

import time
from .movegen import (
    generate_legal, make_move, unmake_move,
    m_to, m_from, m_is_drop, m_is_promo, move_to_usi,
)
from .position import Position
from .mate import find_mate
from .evaluate import evaluate, VALUE, MATE

EXACT, LOWER, UPPER = 0, 1, 2
MATE_THRESH = MATE - 1000


class TimeUp(Exception):
    pass


class Search:
    def __init__(self):
        self.nodes = 0
        self.deadline = 0.0
        self.tt = {}
        self.killers = [[0, 0] for _ in range(256)]
        self.history = {}
        self.eval_fn = evaluate
        self.rep = {}
        self.max_nodes = 0

    def new_game(self):
        self.tt.clear()
        self.history.clear()

    def _check_time(self):
        if self.max_nodes and self.nodes >= self.max_nodes:
            raise TimeUp
        if self.nodes & 1023 == 0 and time.time() >= self.deadline:
            raise TimeUp

    def _order(self, pos, moves, ply, tt_move=0):
        b = pos.board
        killers = self.killers[ply] if ply < 256 else (0, 0)
        hist = self.history

        def score(m):
            if m == tt_move:
                return 1 << 30
            s = 0
            if not m_is_drop(m):
                cap = b[m_to(m)]
                if cap:
                    _, cpt = Position.dec(cap)
                    _, mpt = Position.dec(b[m_from(m)])
                    return (1 << 20) + VALUE[cpt] * 16 - VALUE[mpt]
                if m_is_promo(m):
                    s += 1 << 18
            if m == killers[0]:
                return (1 << 17) + 1
            if m == killers[1]:
                return 1 << 17
            return s + hist.get(m, 0)
        moves.sort(key=score, reverse=True)
        return moves

    def _qsearch(self, pos, alpha, beta, ply):
        self.nodes += 1
        self._check_time()
        in_check = pos.in_check(pos.turn)
        if not in_check:
            stand = self.eval_fn(pos)
            if stand >= beta:
                return beta
            if stand > alpha:
                alpha = stand
        legal = generate_legal(pos)
        if not legal:
            return -MATE + ply if in_check else self.eval_fn(pos)
        b = pos.board
        if in_check:
            moves = legal
        else:
            moves = [m for m in legal
                     if (not m_is_drop(m) and b[m_to(m)]) or m_is_promo(m)]
            if not moves:
                return alpha
        self._order(pos, moves, ply)
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
        z = pos.zob
        if self.rep.get(z, 0) >= 1:
            return 0
        alpha0 = alpha
        tt_move = 0
        entry = self.tt.get(pos.zob)
        if entry is not None:
            e_depth, e_flag, e_val, e_move = entry
            tt_move = e_move
            if e_depth >= depth and abs(e_val) < MATE_THRESH:
                if e_flag == EXACT:
                    return e_val
                if e_flag == LOWER and e_val > alpha:
                    alpha = e_val
                elif e_flag == UPPER and e_val < beta:
                    beta = e_val
                if alpha >= beta:
                    return e_val

        legal = generate_legal(pos)
        if not legal:
            return -MATE + ply
        if depth <= 0:
            return self._qsearch(pos, alpha, beta, ply)

        self._order(pos, legal, ply, tt_move)
        self.rep[z] = self.rep.get(z, 0) + 1
        best = -MATE * 2
        best_move = legal[0]
        for m in legal:
            cap = make_move(pos, m)
            ext = 1 if (ply < 24 and pos.in_check(pos.turn)) else 0
            val = -self._negamax(pos, depth - 1 + ext, -beta, -alpha, ply + 1)
            unmake_move(pos, m, cap)
            if val > best:
                best = val
                best_move = m
                if val > alpha:
                    alpha = val
            if alpha >= beta:
                if not m_is_drop(m) and pos.board[m_to(m)] == 0 and ply < 256:
                    k = self.killers[ply]
                    if k[0] != m:
                        k[1] = k[0]
                        k[0] = m
                    self.history[m] = self.history.get(m, 0) + depth * depth
                break

        self.rep[z] -= 1
        flag = EXACT
        if best <= alpha0:
            flag = UPPER
        elif best >= beta:
            flag = LOWER
        self.tt[pos.zob] = (depth, flag, best, best_move)
        return best

    def _restore(self, pos, snap):
        pos.board[:] = snap.board
        pos.hands[0][:] = snap.hands[0]
        pos.hands[1][:] = snap.hands[1]
        pos.king_sq[:] = snap.king_sq
        pos.turn = snap.turn
        pos.ply = snap.ply
        pos.zob = snap.zob

    def think(self, pos, max_time_s, max_depth=64, info=print, history=None,
              max_nodes=0):
        self.nodes = 0
        self.max_nodes = max_nodes
        self.deadline = time.time() + max_time_s
        start = time.time()
        self.rep = {}
        if history:
            for z in history:
                self.rep[z] = self.rep.get(z, 0) + 1
        self.rep[pos.zob] = self.rep.get(pos.zob, 0) + 1
        legal = generate_legal(pos)
        if not legal:
            return None
        snap = pos.clone()
        best_move = legal[0]
        mate_move, mate_in = find_mate(pos, max_plies=7, node_cap=50000)
        if mate_move is not None:
            info(f"info depth {mate_in * 2 - 1} score mate {mate_in} "
                 f"nodes {self.nodes} pv {move_to_usi(mate_move)}")
            return mate_move
        for depth in range(1, max_depth + 1):
            alpha, beta = -MATE * 2, MATE * 2
            local_best = None
            best_val = -MATE * 3
            tt_mv = self.tt.get(pos.zob, (0, 0, 0, best_move))[3]
            ordered = self._order(pos, list(legal), 0, tt_mv)
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
                self._restore(pos, snap)
                break
            if local_best is not None:
                best_move = local_best
                self.tt[pos.zob] = (depth, EXACT, best_val, best_move)
                elapsed = time.time() - start
                nps = int(self.nodes / elapsed) if elapsed > 0 else 0
                if abs(best_val) > MATE_THRESH:
                    mate_n = (MATE - abs(best_val) + 1) // 2
                    sc = f"mate {mate_n if best_val > 0 else -mate_n}"
                else:
                    sc = f"cp {best_val}"
                info(f"info depth {depth} score {sc} nodes {self.nodes} "
                     f"nps {nps} time {int(elapsed*1000)} pv {move_to_usi(best_move)}")
                if abs(best_val) > MATE_THRESH:
                    break
            if time.time() >= self.deadline:
                break
        return best_move