# HanyuShogi — a USI Shogi engine (Python)

A working, **USI-protocol-compliant** Shogi (将棋) engine written in pure Python.
It plays fully legal Shogi and runs in standard GUIs such as **ShogiGUI** and
**将棋所 (Shogidokoro)**.

## What it does

- Complete Shogi rules: legal move generation, drops, promotion (incl.
  mandatory promotion), checks, checkmate/stalemate, **nifu** (two-pawns) and
  **uchifuzume** (pawn-drop-mate) prohibitions.
- Move generator verified by **perft**: 30 / 900 / 25470 / 719731 at depths
  1–4 (exact match to known reference values).
- Alpha-beta search with iterative deepening, quiescence search, MVV-LVA move
  ordering, and USI time control (byoyomi / Fischer increment / movetime).
- Hand-crafted evaluation (material + light positional terms).

## Run

```bash
python -m unittest tests.test_rules -v   # tests
python perft.py 4                        # perft self-check
python usi.py                            # start the USI engine (stdin/stdout)
```

### Register in ShogiGUI / 将棋所

Point the GUI at a launcher. On Windows create `engine.bat`:

```bat
@echo off
python "%~dp0usi.py"
```

Register `engine.bat` as a USI engine. It answers `usi`, `isready`,
`usinewgame`, `position`, `go`, `quit`.

## Architecture

| File | Role |
|------|------|
| `shogi/position.py` | Board, SFEN I/O, attack detection |
| `shogi/movegen.py`  | Move encoding, make/unmake, legal move generation |
| `shogi/evaluate.py` | Hand-crafted evaluation |
| `shogi/search.py`   | Alpha-beta + iterative deepening + quiescence |
| `usi.py`            | USI protocol loop |

## Honest scope

This is a **correct, legal, playable** engine — not a world-champion engine.
Reaching the strength of WCSC-class programs (氷彗 / dlshogi / Ryfamate)
requires a C++/GPU stack (NNUE + deep-learning MCTS via TensorRT), billions of
training positions, and months of training. This project is a clean,
extensible foundation for that road. Pure-Python search reaches roughly
depth 3–5 per move at blitz time controls.

### Not yet implemented
- Opening book, transposition table (Zobrist), nyugyoku (入玉) win declaration.
- NNUE / deep-learning evaluation.

## License
MIT