# Shogi AI Project - Claude Code Governing Rules

## 1. Architecture
Pure-Python, USI-compliant Shogi engine. No C++/GPU toolchain on this machine.
- `shogi/position.py` - board, SFEN, attack detection
- `shogi/movegen.py`  - move encoding, make/unmake, legal move generation
- `shogi/evaluate.py` - hand-crafted evaluation
- `shogi/search.py`   - alpha-beta, iterative deepening, quiescence
- `usi.py`            - USI protocol loop

## 2. Verify before shipping (CRITICAL)
Always run both, both must pass:
- `python -m unittest tests.test_rules -v`
- `python perft.py 4`  (must print 30 / 900 / 25470 / 719731, all "OK")

Never claim a move-gen change is correct without a green perft.

## 3. Invariants
- Square index: sq = (rank-1)*9 + (9-file). Sente forward = index -9.
- `make_move` returns the captured piece value; `unmake_move` needs it.
  Every make MUST be paired with an unmake (see test_legal_moves_are_replayable).
- Piece encoding: 0 = empty, else 1 + color*14 + ptype.
- Keep `is_attacked` and move generation consistent: a change to one usually
  requires the matching change in the other (e.g. horse/dragon adjacency).

## 4. Environment
- Windows + PowerShell. Create/edit files via PowerShell here-strings, not the
  Write/Edit tools (they hang on this machine).
- USI I/O reconfigures stdin/stdout to UTF-8 and strips a leading BOM.