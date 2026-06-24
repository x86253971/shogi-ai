"""Interactive play driver. Persists a game in .game.json so each invocation
continues the same game.

  python play.py new [--gote]    start a new game (you are Sente unless --gote)
  python play.py show            print the current board
  python play.py move <usi>      play your move; engine replies
  python play.py undo            undo the last full move (yours + engine's)
  python play.py hint            show what the engine would play for you

Moves use USI notation: 7g7f, 8h2b+ (promote), P*5e (drop).
"""

import json
import os
import sys
from shogi.position import Position, SENTE, GOTE, make_sq, DISP
from shogi.movegen import generate_legal, make_move, move_to_usi, usi_to_move
from shogi.search import Search

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".game.json")
THINK_TIME = 2.0


def load():
    with open(STATE, encoding="utf-8") as f:
        return json.load(f)


def save(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def pos_from(state):
    pos = Position.startpos()
    for mv in state["moves"]:
        make_move(pos, usi_to_move(mv))
    return pos


def render(pos):
    out = []
    out.append("     9  8  7  6  5  4  3  2  1")
    out.append("   +" + "---" * 9 + "+")
    for r in range(1, 10):
        cells = []
        for f in range(9, 0, -1):
            v = pos.board[make_sq(f, r)]
            if v == 0:
                cells.append(" .")
            else:
                c, pt = Position.dec(v)
                g = DISP[pt]
                if len(g) == 1:
                    g = " " + g
                cells.append(g if c == SENTE else g.lower())
        rl = chr(ord("a") + r - 1)
        out.append(f" {rl} | " + " ".join(cells) + f" | {rl}")
    out.append("   +" + "---" * 9 + "+")
    out.append("     9  8  7  6  5  4  3  2  1")

    def hand_str(color):
        names = ["P", "L", "N", "S", "G", "B", "R"]
        parts = []
        for pt in range(7):
            n = pos.hands[color][pt]
            if n:
                parts.append(f"{names[pt]}x{n}" if n > 1 else names[pt])
        return " ".join(parts) if parts else "-"

    out.append(f"Sente(UPPER) hand: {hand_str(SENTE)}")
    out.append(f"Gote (lower) hand: {hand_str(GOTE)}")
    turn = "Sente (you move)" if pos.turn == SENTE else "Gote"
    out.append(f"Turn: {turn}   Move#: {pos.ply}")
    return "\n".join(out)


def status(pos):
    legal = generate_legal(pos)
    if not legal:
        return "CHECKMATE" if pos.in_check(pos.turn) else "STALEMATE (loss)"
    if pos.in_check(pos.turn):
        return "CHECK!"
    return ""


def engine_move(state):
    pos = pos_from(state)
    s = Search()
    best = s.think(pos, THINK_TIME, max_depth=12,
                   info=lambda line: print("  " + line, file=sys.stderr))
    if best is None:
        return None
    return move_to_usi(best)


def cmd_new(args):
    human = GOTE if "--gote" in args else SENTE
    state = {"moves": [], "human": human}
    save(state)
    pos = pos_from(state)
    print(render(pos))
    if human == GOTE:
        mv = engine_move(state)
        state["moves"].append(mv)
        save(state)
        print(f"\nEngine plays: {mv}\n")
        print(render(pos_from(state)))


def cmd_show(args):
    print(render(pos_from(load())))


def cmd_move(args):
    state = load()
    pos = pos_from(state)
    legal = generate_legal(pos)
    try:
        m = usi_to_move(args[0])
    except Exception:
        print("Bad move format. Use USI like 7g7f, 8h2b+, P*5e.")
        return
    if m not in legal:
        sample = ", ".join(move_to_usi(x) for x in legal[:25])
        print(f"Illegal move: {args[0]}")
        print(f"Some legal moves: {sample} ...")
        return
    state["moves"].append(args[0])
    save(state)
    pos = pos_from(state)
    st = status(pos)
    if st in ("CHECKMATE", "STALEMATE (loss)"):
        print(render(pos))
        print(f"\n*** {st} — you win! ***")
        return
    print(f"You played: {args[0]}")
    mv = engine_move(state)
    if mv is None:
        print(render(pos))
        print("\n*** Engine has no moves — you win! ***")
        return
    state["moves"].append(mv)
    save(state)
    pos = pos_from(state)
    print(f"Engine plays: {mv}")
    print()
    print(render(pos))
    st = status(pos)
    if st:
        print(f"\n>>> {st}")
        if st == "CHECKMATE":
            print("*** Engine wins ***")


def cmd_undo(args):
    state = load()
    state["moves"] = state["moves"][:-2]
    save(state)
    print(render(pos_from(state)))


def cmd_hint(args):
    state = load()
    mv = engine_move(state)
    print(f"Engine suggests: {mv}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    args = sys.argv[2:]
    {"new": cmd_new, "show": cmd_show, "move": cmd_move,
     "undo": cmd_undo, "hint": cmd_hint}.get(cmd, lambda a: print(__doc__))(args)


if __name__ == "__main__":
    main()