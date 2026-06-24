"""Rule-correctness and engine-integration tests (stdlib unittest)."""

import unittest
from shogi.position import Position, SENTE, GOTE, sq_file
from shogi.movegen import (
    generate_legal, make_move, unmake_move,
    m_is_drop, m_from, m_to, move_to_usi, usi_to_move,
)
from shogi.search import Search
from shogi.evaluate import MATE

START = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"


def perft(pos, d):
    if d == 0:
        return 1
    n = 0
    for m in generate_legal(pos):
        cap = make_move(pos, m)
        n += perft(pos, d - 1)
        unmake_move(pos, m, cap)
    return n


class TestRules(unittest.TestCase):
    def test_sfen_roundtrip(self):
        self.assertEqual(Position.from_sfen(START).to_sfen(), START)
        s = "4k4/9/9/9/4P4/9/9/9/4K4 b P 1"
        self.assertEqual(Position.from_sfen(s).to_sfen(), s)

    def test_perft(self):
        pos = Position.startpos()
        self.assertEqual(perft(pos, 1), 30)
        self.assertEqual(perft(pos, 2), 900)
        self.assertEqual(perft(pos, 3), 25470)

    def test_nifu(self):
        pos = Position.from_sfen("4k4/9/9/9/4P4/9/9/9/4K4 b P 1")
        drops_file5 = [
            m for m in generate_legal(pos)
            if m_is_drop(m) and m_from(m) == 0 and sq_file(m_to(m)) == 5
        ]
        self.assertEqual(drops_file5, [], "nifu: pawn drop on occupied file")
        any_pawn_drop = [
            m for m in generate_legal(pos)
            if m_is_drop(m) and m_from(m) == 0
        ]
        self.assertTrue(any_pawn_drop)

    def test_uchifuzume(self):
        # Gote king 1a; Sente gold 2c (guards 2b, defends 1b); Sente knight 3c
        # (guards 2a). P*1b would be immediate mate => uchifuzume => illegal.
        pos = Position.from_sfen("8k/9/6NG1/9/9/9/9/9/8K b P 1")
        moves = [move_to_usi(m) for m in generate_legal(pos)]
        self.assertNotIn("P*1b", moves, "uchifuzume drop must be illegal")
        self.assertIn("P*5e", moves, "ordinary pawn drops must still be legal")

    def test_mate_in_one_found(self):
        pos = Position.from_sfen("k8/9/K8/9/9/9/9/9/9 b R 1")
        s = Search()
        best = s.think(pos, 1.0, max_depth=3, info=lambda *_: None)
        self.assertIsNotNone(best)

    def test_legal_moves_are_replayable(self):
        pos = Position.startpos()
        ref = pos.to_sfen()
        for m in generate_legal(pos):
            cap = make_move(pos, m)
            unmake_move(pos, m, cap)
            self.assertEqual(pos.to_sfen(), ref)

    def test_selfplay_no_illegal(self):
        pos = Position.startpos()
        s = Search()
        for _ in range(30):
            legal = generate_legal(pos)
            if not legal:
                break
            best = s.think(pos, 0.05, max_depth=2, info=lambda *_: None)
            self.assertIn(best, legal)
            make_move(pos, best)

    def test_mate_search_finds_mate_in_1(self):
        from shogi.mate import find_mate
        pos = Position.from_sfen("4k4/9/4G4/9/9/9/9/9/4K4 b G 1")
        m, n = find_mate(pos, 7)
        self.assertIsNotNone(m)
        self.assertEqual(n, 1)
        self.assertEqual(move_to_usi(m), "G*5b")
        best = Search().think(pos, 1.0, max_depth=4, info=lambda *_: None)
        self.assertEqual(move_to_usi(best), "G*5b")

    def test_mate_search_no_false_positive(self):
        from shogi.mate import find_mate
        m, _ = find_mate(Position.startpos(), 7)
        self.assertIsNone(m)


if __name__ == "__main__":
    unittest.main(verbosity=2)