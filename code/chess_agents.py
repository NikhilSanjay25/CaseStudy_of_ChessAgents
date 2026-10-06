"""Multi-Agent Chess Arena: a Minimax agent vs. an Alpha-Beta pruning agent.

Both agents use the SAME heuristic evaluation (material + piece-square tables) and a
depth-limited adversarial search. The only difference is the search technique:
  minimax   - explores every move to the given depth
  alphabeta - same decisions, but skips branches that cannot change the result
The chess rules (legal moves, check, mate, draws) come from the python-chess library.

Play a game:   python chess_agents.py --white minimax:2 --black alphabeta:3
"""
import argparse, time
import chess

# ---------------------------------------------------------------- heuristic evaluation
VALUE = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
         chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}

# Piece-square tables (Michniewski's "simplified evaluation function"), written from
# White's point of view with rank 8 on the first line.
PST = {
    chess.PAWN: [0, 0, 0, 0, 0, 0, 0, 0,
                 50, 50, 50, 50, 50, 50, 50, 50,
                 10, 10, 20, 30, 30, 20, 10, 10,
                 5, 5, 10, 25, 25, 10, 5, 5,
                 0, 0, 0, 20, 20, 0, 0, 0,
                 5, -5, -10, 0, 0, -10, -5, 5,
                 5, 10, 10, -20, -20, 10, 10, 5,
                 0, 0, 0, 0, 0, 0, 0, 0],
    chess.KNIGHT: [-50, -40, -30, -30, -30, -30, -40, -50,
                   -40, -20, 0, 0, 0, 0, -20, -40,
                   -30, 0, 10, 15, 15, 10, 0, -30,
                   -30, 5, 15, 20, 20, 15, 5, -30,
                   -30, 0, 15, 20, 20, 15, 0, -30,
                   -30, 5, 10, 15, 15, 10, 5, -30,
                   -40, -20, 0, 5, 5, 0, -20, -40,
                   -50, -40, -30, -30, -30, -30, -40, -50],
    chess.BISHOP: [-20, -10, -10, -10, -10, -10, -10, -20,
                   -10, 0, 0, 0, 0, 0, 0, -10,
                   -10, 0, 5, 10, 10, 5, 0, -10,
                   -10, 5, 5, 10, 10, 5, 5, -10,
                   -10, 0, 10, 10, 10, 10, 0, -10,
                   -10, 10, 10, 10, 10, 10, 10, -10,
                   -10, 5, 0, 0, 0, 0, 5, -10,
                   -20, -10, -10, -10, -10, -10, -10, -20],
    chess.ROOK: [0, 0, 0, 0, 0, 0, 0, 0,
                 5, 10, 10, 10, 10, 10, 10, 5,
                 -5, 0, 0, 0, 0, 0, 0, -5,
                 -5, 0, 0, 0, 0, 0, 0, -5,
                 -5, 0, 0, 0, 0, 0, 0, -5,
                 -5, 0, 0, 0, 0, 0, 0, -5,
                 -5, 0, 0, 0, 0, 0, 0, -5,
                 0, 0, 0, 5, 5, 0, 0, 0],
    chess.QUEEN: [-20, -10, -10, -5, -5, -10, -10, -20,
                  -10, 0, 0, 0, 0, 0, 0, -10,
                  -10, 0, 5, 5, 5, 5, 0, -10,
                  -5, 0, 5, 5, 5, 5, 0, -5,
                  0, 0, 5, 5, 5, 5, 0, -5,
                  -10, 5, 5, 5, 5, 5, 0, -10,
                  -10, 0, 5, 0, 0, 0, 0, -10,
                  -20, -10, -10, -5, -5, -10, -10, -20],
    chess.KING: [-30, -40, -40, -50, -50, -40, -40, -30,
                 -30, -40, -40, -50, -50, -40, -40, -30,
                 -30, -40, -40, -50, -50, -40, -40, -30,
                 -30, -40, -40, -50, -50, -40, -40, -30,
                 -20, -30, -30, -40, -40, -30, -30, -20,
                 -10, -20, -20, -20, -20, -20, -20, -10,
                 20, 20, 0, 0, 0, 0, 20, 20,
                 20, 30, 10, 0, 0, 10, 30, 20],
}
MATE = 100_000
INF = float("inf")


def evaluate(board):
    """Static heuristic from White's point of view (centipawns). Positive = good for White."""
    score = 0
    for sq, piece in board.piece_map().items():
        if piece.color == chess.WHITE:
            score += VALUE[piece.piece_type] + PST[piece.piece_type][chess.square_mirror(sq)]
        else:
            score -= VALUE[piece.piece_type] + PST[piece.piece_type][sq]
    return score


def terminal_value(board, ply):
    """Value of a position with no legal moves: mate (closer mates score higher) or stalemate."""
    if board.is_check():
        return -(MATE - ply) if board.turn == chess.WHITE else MATE - ply
    return 0


# ---------------------------------------------------------------- search
class Stats:
    def __init__(self):
        self.nodes = 0     # positions visited (including leaves)
        self.leaves = 0    # positions scored by the heuristic
        self.cutoffs = 0   # alpha-beta prunings


def order_moves(board, moves, ordering):
    """'mvv' = captures first, most valuable victim / least valuable attacker (MVV-LVA),
    then promotions and checks.  'none' = generator order.  'worst' = reverse of 'mvv'."""
    if ordering == "none":
        return moves

    def key(m):
        s = 0
        if board.is_capture(m):
            victim = board.piece_at(m.to_square)
            s += 10 * (VALUE[victim.piece_type] if victim else 100) - VALUE[board.piece_at(m.from_square).piece_type] // 10 + 10_000
        if m.promotion:
            s += 9_000
        if board.gives_check(m):
            s += 500
        return s
    ms = sorted(moves, key=key, reverse=True)
    return ms[::-1] if ordering == "worst" else ms


def minimax(board, depth, ply, stats, trace=None, path=()):
    stats.nodes += 1
    moves = list(board.legal_moves)
    if not moves:
        v = terminal_value(board, ply)
    elif depth == 0 or board.is_insufficient_material():
        stats.leaves += 1
        v = 0 if board.is_insufficient_material() else evaluate(board)
    else:
        maximizing = board.turn == chess.WHITE
        v = -INF if maximizing else INF
        for m in moves:
            san = board.san(m) if trace is not None else None
            board.push(m)
            child = minimax(board, depth - 1, ply + 1, stats, trace, path + (san,))
            board.pop()
            v = max(v, child) if maximizing else min(v, child)
    if trace is not None:
        trace.append(("node", path, v))
    return v


def alphabeta(board, depth, ply, alpha, beta, stats, ordering="mvv", trace=None, path=()):
    stats.nodes += 1
    moves = list(board.legal_moves)
    if not moves:
        v = terminal_value(board, ply)
    elif depth == 0 or board.is_insufficient_material():
        stats.leaves += 1
        v = 0 if board.is_insufficient_material() else evaluate(board)
    else:
        maximizing = board.turn == chess.WHITE
        v = -INF if maximizing else INF
        moves = order_moves(board, moves, ordering)
        for i, m in enumerate(moves):
            san = board.san(m) if trace is not None else None
            board.push(m)
            child = alphabeta(board, depth - 1, ply + 1, alpha, beta, stats, ordering, trace, path + (san,))
            board.pop()
            if maximizing:
                v = max(v, child); alpha = max(alpha, v)
            else:
                v = min(v, child); beta = min(beta, v)
            if alpha >= beta:  # the opponent will never allow this line: prune the rest
                stats.cutoffs += 1
                if trace is not None:
                    for rest in moves[i + 1:]:
                        trace.append(("pruned", path + (board.san(rest),), None))
                break
    if trace is not None:
        trace.append(("node", path, v))
    return v


def choose_move(board, algo, depth, ordering="mvv", trace=None):
    """Root search: returns (best move, its value, Stats, seconds).
    Ties keep the first best move found, so both agents are deterministic."""
    stats, t0 = Stats(), time.perf_counter()
    stats.nodes += 1
    maximizing = board.turn == chess.WHITE
    moves = list(board.legal_moves)
    if algo == "alphabeta":
        moves = order_moves(board, moves, ordering)
    best, best_v = None, -INF if maximizing else INF
    alpha, beta = -INF, INF
    for m in moves:
        san = board.san(m) if trace is not None else None
        board.push(m)
        if algo == "minimax":
            v = minimax(board, depth - 1, 1, stats, trace, (san,))
        else:
            v = alphabeta(board, depth - 1, 1, alpha, beta, stats, ordering, trace, (san,))
        board.pop()
        if (maximizing and v > best_v) or (not maximizing and v < best_v):
            best, best_v = m, v
        if algo == "alphabeta":
            if maximizing:
                alpha = max(alpha, best_v)
            else:
                beta = min(beta, best_v)
    if trace is not None:
        trace.append(("node", (), best_v))
    return best, best_v, stats, time.perf_counter() - t0


# ---------------------------------------------------------------- arena
def parse_agent(spec):
    """'minimax:2', 'alphabeta:3' or 'alphabeta:3:none' -> (algo, depth, ordering)"""
    parts = spec.split(":")
    return parts[0], int(parts[1]), parts[2] if len(parts) > 2 else "mvv"


def play_game(white, black, fen=chess.STARTING_FEN, max_plies=100, verbose=False):
    """Play one game between two agent specs. Returns a dict with the result and per-move stats.
    Games still running after max_plies are adjudicated: a lead of >= 300 centipawns
    (about a minor piece) counts as a win, otherwise a draw."""
    board = chess.Board(fen)
    log = []
    while not board.is_game_over(claim_draw=True) and len(log) < max_plies:
        algo, depth, ordering = parse_agent(white if board.turn == chess.WHITE else black)
        move, value, st, secs = choose_move(board, algo, depth, ordering)
        log.append({"side": "white" if board.turn else "black", "algo": algo, "move": board.san(move),
                    "value": value, "nodes": st.nodes, "cutoffs": st.cutoffs, "seconds": secs})
        board.push(move)
        if verbose:
            print(f"{len(log):3d}. {log[-1]['side']:5s} {algo:9s} {log[-1]['move']:7s} "
                  f"value={value:>7}  nodes={st.nodes:>7}  {secs:.2f}s")
    outcome = board.outcome(claim_draw=True)
    if outcome:
        result, reason = board.result(claim_draw=True), outcome.termination.name.lower()
    else:
        e = evaluate(board)
        result = "1-0" if e >= 300 else "0-1" if e <= -300 else "1/2-1/2"
        reason = f"adjudicated (eval {e:+d})"
    return {"white": white, "black": black, "start": fen, "result": result, "reason": reason,
            "plies": len(log), "moves": log, "final_fen": board.fen()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--white", default="minimax:2", help="algo:depth[:ordering], e.g. minimax:2")
    ap.add_argument("--black", default="alphabeta:3", help="algo:depth[:ordering], e.g. alphabeta:3:mvv")
    ap.add_argument("--fen", default=chess.STARTING_FEN, help="start position (FEN)")
    ap.add_argument("--max-plies", type=int, default=100)
    ap.add_argument("--analyse", action="store_true",
                    help="only compare both searches on --fen at the depth of --white")
    a = ap.parse_args()
    board = chess.Board(a.fen)
    print(board, "\n")
    if a.analyse:
        d = parse_agent(a.white)[1]
        for algo in ["minimax", "alphabeta"]:
            m, v, st, s = choose_move(board, algo, d)
            print(f"{algo:9s} depth {d}: best {board.san(m):6s} value {v:>7}  nodes {st.nodes:>8,}  "
                  f"cutoffs {st.cutoffs:>6,}  {s:.2f}s")
        return
    g = play_game(a.white, a.black, a.fen, a.max_plies, verbose=True)
    print("\n" + str(chess.Board(g["final_fen"])))
    print(f"\nResult {g['result']} ({g['reason']}) after {g['plies']} plies")


if __name__ == "__main__":
    main()
