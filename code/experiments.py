
import json, os, sys
import chess
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from chess_agents import choose_move, play_game, evaluate

HERE = os.path.dirname(os.path.abspath(__file__))
RES, FIG = os.path.join(HERE, "..", "results"), os.path.join(HERE, "..", "figures")
QUICK = "--quick" in sys.argv
BLUE, ORANGE, GREEN, GREY, PURPLE = "#2a6fdb", "#e0552b", "#1e9e63", "#9a9a9a", "#9b4dca"

SUITE = {  # positions for the node-count experiment
    "Start position": chess.STARTING_FEN,
    "Italian opening": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "Middlegame (E1)": "1k3b1r/r1q1nBpp/p1p2n2/5b2/2NP4/2N1BQ2/PPP2PPP/R4RK1 b - - 3 15",
    "Knight fork (W2)": "r3k3/8/8/1N6/8/8/4P3/4K3 w - - 0 1",
    "Rook endgame": "8/5k2/8/3R4/8/2K5/5r2/8 w - - 0 1",
}
CASES = {
    "W1": ("Back-rank mate in one", "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"),
    "W2": ("Knight fork wins the rook", "r3k3/8/8/1N6/8/8/4P3/4K3 w - - 0 1"),
    "E1": ("Horizon effect: the poisoned pawn", SUITE["Middlegame (E1)"]),
    "E2": ("Stalemate trap", "7k/8/3Qn2K/8/8/8/8/8 w - - 0 1"),
}
OPENINGS = {  # every arena game starts from one of these, played once with each colour assignment
    "Italian": "e2e4 e7e5 g1f3 b8c6 f1c4 f8c5",
    "Sicilian": "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4",
    "Queen's Gambit": "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6",
    "French": "e2e4 e7e6 d2d4 d7d5 b1c3 f8b4",
    "English": "c2c4 e7e5 b1c3 g8f6 g2g3 d7d5",
    "Caro-Kann": "e2e4 c7c6 d2d4 d7d5 e4e5 c8f5",
}


def fen_after(uci):
    b = chess.Board()
    for u in uci.split():
        b.push_uci(u)
    return b.fen()


# ---------------------------------------------------------------- figures
GLYPH = {"K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙",
         "k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"}


def draw_board(ax, board, arrows=(), title=""):
    for sq in chess.SQUARES:
        f, r = chess.square_file(sq), chess.square_rank(sq)
        ax.add_patch(plt.Rectangle((f, r), 1, 1, color="#f0d9b5" if (f + r) % 2 else "#b58863"))
        p = board.piece_at(sq)
        if p:
            ax.text(f + 0.5, r + 0.47, GLYPH[p.symbol()], fontsize=22, ha="center", va="center",
                    color="black", family="DejaVu Sans")
    for i in range(8):
        ax.text(i + 0.5, -0.3, "abcdefgh"[i], ha="center", fontsize=8)
        ax.text(-0.3, i + 0.5, str(i + 1), va="center", fontsize=8)
    for move, col in arrows:
        a, b = move.from_square, move.to_square
        ax.add_patch(FancyArrowPatch((chess.square_file(a) + .5, chess.square_rank(a) + .5),
                                     (chess.square_file(b) + .5, chess.square_rank(b) + .5),
                                     arrowstyle="-|>", mutation_scale=18, lw=3, color=col, alpha=0.8))
    ax.set_xlim(-0.5, 8); ax.set_ylim(-0.5, 8); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontsize=9)


def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(FIG, name), dpi=160); plt.close(fig)


def tree_figure(fen, depth, name):
    """Depth-2 game tree: each root move with its replies. Leaves are coloured by who saw them:
    both searches (blue), only minimax because alpha-beta pruned them (grey, crossed)."""
    board = chess.Board(fen)
    tm, ta = [], []
    choose_move(board, "minimax", depth, trace=tm)
    _, best_v, st, _ = choose_move(board, "alphabeta", depth, ordering="none", trace=ta)
    mm = {p: v for k, p, v in tm if k == "node"}
    ab_seen = {p for k, p, v in ta if k == "node"}
    roots = [p for p in mm if len(p) == 1]
    fig, ax = plt.subplots(figsize=(12, 0.9 + 0.62 * len(roots)))
    ax.text(0, 1.1, f"Root (White to move): minimax value {mm[()]}", fontsize=10, weight="bold")
    for i, r in enumerate(roots):
        y = -i
        leaves = [p for p in mm if len(p) == 2 and p[0] == r[0]]
        pruned_here = sum(1 for p in leaves if p not in ab_seen)
        ax.text(0, y, f"{r[0]:5s} MIN={mm[r]:>4}", fontsize=10, family="monospace", va="center",
                bbox=dict(boxstyle="round", fc="#dbe8ff", ec=BLUE))
        for j, p in enumerate(leaves):
            seen = p in ab_seen
            ax.text(2.35 + j * 1.02, y, f"{p[1]}\n{mm[p]}", fontsize=7, ha="center", va="center",
                    color="black" if seen else "#888",
                    bbox=dict(boxstyle="round", fc="#eef5ff" if seen else "#f2f2f2", ec=BLUE if seen else GREY,
                              ls="-" if seen else ":"))
            if not seen:
                ax.plot([2.35 + j * 1.02 - .35, 2.35 + j * 1.02 + .35], [y - .22, y + .22], color=ORANGE, lw=1)
        ax.text(2.35 + len(leaves) * 1.02 + 0.1, y, f"pruned {pruned_here}/{len(leaves)}" if pruned_here else "",
                fontsize=8, color=ORANGE, va="center")
    ax.set_xlim(-0.2, 13.5); ax.set_ylim(-len(roots) + 0.4, 1.5); ax.axis("off")
    ax.set_title(f"Depth-{depth} game tree, generator move order. Grey crossed leaves are never visited by alpha-beta "
                 f"({len(mm) - len(ab_seen)} of {len(mm)} positions skipped)", fontsize=10)
    save(fig, name)
    return {"minimax_nodes": len(mm), "alphabeta_nodes": len(ab_seen), "value": mm[()], "ab_value": best_v}


# ---------------------------------------------------------------- experiments
def node_experiment():
    rows = []
    for name, fen in SUITE.items():
        for d in range(1, 4 if QUICK else 5):
            row = {"position": name, "depth": d}
            for algo, order in [("minimax", "mvv"), ("alphabeta", "mvv"), ("alphabeta", "none"), ("alphabeta", "worst")]:
                m, v, st, secs = choose_move(chess.Board(fen), algo, d, order)
                key = algo if algo == "minimax" else f"ab_{order}"
                row[key] = {"move": chess.Board(fen).san(m), "value": v, "nodes": st.nodes,
                            "cutoffs": st.cutoffs, "seconds": secs}
            assert len({row[k]["value"] for k in ["minimax", "ab_mvv", "ab_none", "ab_worst"]}) == 1, \
                f"alpha-beta must return the minimax value ({name}, depth {d})"
            rows.append(row)
            print(f"  {name:18s} d={d}  minimax {row['minimax']['nodes']:>9,}  ab {row['ab_mvv']['nodes']:>7,}  "
                  f"ab-none {row['ab_none']['nodes']:>8,}  ab-worst {row['ab_worst']['nodes']:>9,}")
    return rows


def case_experiment():
    out = {}
    for key, (title, fen) in CASES.items():
        board = chess.Board(fen)
        out[key] = {"title": title, "fen": fen, "by_depth": []}
        for d in range(1, 4 if QUICK else 5):
            for algo in ["minimax", "alphabeta"]:
                if algo == "minimax" and d == 4 and key == "E1":
                    continue  # ~2 million nodes; alpha-beta gives the same value
                m, v, st, secs = choose_move(board, algo, d)
                out[key]["by_depth"].append({"algo": algo, "depth": d, "move": board.san(m), "value": v,
                                             "nodes": st.nodes, "seconds": secs})
    # E2: what a greedy one-ply agent WITHOUT the terminal test would do
    b = chess.Board(CASES["E2"][1])
    greedy = max(b.legal_moves, key=lambda m: (b.push(m), evaluate(b), b.pop())[1])
    out["E2"]["greedy_static"] = b.san(greedy)
    return out


def arena(match, white_spec, black_spec, max_plies):
    games = []
    openings = list(OPENINGS.items())[:2] if QUICK else OPENINGS.items()
    for oname, uci in openings:
        for a, b in [(white_spec, black_spec), (black_spec, white_spec)]:
            g = play_game(a, b, fen_after(uci), max_plies)
            g["opening"] = oname
            games.append(g)
            print(f"  [{match}] {oname:15s} W={a:12s} B={b:12s} {g['result']:8s} {g['reason']}")
    return games


def score(games, spec):
    pts = 0.0
    for g in games:
        if g["result"] == "1/2-1/2":
            pts += 0.5
        elif (g["result"] == "1-0" and g["white"] == spec) or (g["result"] == "0-1" and g["black"] == spec):
            pts += 1
    return pts


def per_move(games, algo):
    ms = [m for g in games for m in g["moves"] if m["algo"] == algo]
    return sum(m["nodes"] for m in ms) / len(ms), sum(m["seconds"] for m in ms) / len(ms), len(ms)


def agreement(games):
    """Replay every position of the equal-depth match and ask BOTH agents for their move."""
    same_move = same_value = total = 0
    for g in games:
        b = chess.Board(g["start"])
        for m in g["moves"]:
            mm, vm, _, _ = choose_move(b, "minimax", 2)
            ma, va, _, _ = choose_move(b, "alphabeta", 2)
            total += 1; same_move += mm == ma; same_value += vm == va
            b.push_san(m["move"])
    return {"positions": total, "same_move": same_move, "same_value": same_value}


def write_numbers(R):
    """Numbers quoted in the report text -> results/numbers.tex (\newcommand definitions)."""
    nodes, cases = R["nodes"], R["cases"]
    dmax = max(r["depth"] for r in nodes)
    at = lambda pos, d: next(r for r in nodes if r["position"] == pos and r["depth"] == d)
    pick = lambda k, a, d: next(r for r in cases[k]["by_depth"] if r["algo"] == a and r["depth"] == d)
    poss = list(dict.fromkeys(r["position"] for r in nodes))
    n = {"DMAX": dmax,
         "WoneMM": f"{pick('W1', 'minimax', 3)['nodes']:,}", "WoneAB": f"{pick('W1', 'alphabeta', 3)['nodes']:,}",
         "WtwoMM": f"{pick('W2', 'minimax', 3)['nodes']:,}", "WtwoAB": f"{pick('W2', 'alphabeta', 3)['nodes']:,}",
         "EoneABfour": f"{pick('E1', 'alphabeta', dmax)['nodes']:,}",
         "ItalWorst": f"{at('Italian opening', dmax)['ab_worst']['nodes']:,}",
         "ItalMVV": f"{at('Italian opening', dmax)['ab_mvv']['nodes']:,}",
         "MidMM": f"{at('Middlegame (E1)', dmax)['minimax']['nodes']:,}",
         "MidAB": f"{at('Middlegame (E1)', dmax)['ab_mvv']['nodes']:,}",
         "AvgMM": f"{sum(at(p, dmax)['minimax']['nodes'] for p in poss) / len(poss):,.0f}",
         "AvgAB": f"{sum(at(p, dmax)['ab_mvv']['nodes'] for p in poss) / len(poss):,.0f}"}
    ag = R.get("agreement")
    if ag:
        n.update({"AgreePos": f"{ag['positions']:,}", "AgreeMove": f"{100 * ag['same_move'] / ag['positions']:.1f}",
                  "AgreeValue": f"{100 * ag['same_value'] / ag['positions']:.1f}"})
    open(os.path.join(RES, "numbers.tex"), "w").write(
        "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in n.items()) + "\n")


def arena_plot(arena_a, arena_b):
    fig, ax = plt.subplots(figsize=(10, 3.6))
    labels, mm, ab, dr = [], [], [], []
    for lab, games, abspec in [("Match A: Minimax d2 vs Alpha-beta d2", arena_a, "alphabeta:2"),
                               ("Match B: Minimax d2 vs Alpha-beta d3", arena_b, "alphabeta:3")]:
        w_ab = sum(1 for g in games if (g["result"] == "1-0" and g["white"] == abspec) or (g["result"] == "0-1" and g["black"] == abspec))
        d = sum(1 for g in games if g["result"] == "1/2-1/2")
        labels.append(lab); ab.append(w_ab); dr.append(d); mm.append(len(games) - w_ab - d)
    y = range(len(labels))
    ax.barh(y, ab, color=BLUE, label="Alpha-beta wins")
    ax.barh(y, dr, left=ab, color=GREY, label="Draws")
    ax.barh(y, mm, left=[a + d for a, d in zip(ab, dr)], color=ORANGE, label="Minimax wins")
    ax.set_yticks(list(y)); ax.set_yticklabels(labels); ax.set_xlabel("games"); ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    ax.invert_yaxis(); ax.set_title("Arena results (each opening played with both colour assignments)", fontsize=10)
    save(fig, "arena.png")



def write_tables(R):
    """LaTeX table rows loaded by the report -> results/table_*.tex"""
    nodes, cases, arena_a, arena_b = R["nodes"], R["cases"], R["arena_equal_depth"], R["arena_deeper_ab"]
    dmax = max(r["depth"] for r in nodes)
    L = []
    for r in nodes:
        m, a = r["minimax"], r["ab_mvv"]
        L.append(f"{r['position']} & {r['depth']} & {m['move'].replace('#', chr(92) + '#')} & {m['value']} & {m['nodes']:,} & "
                 f"{r['ab_worst']['nodes']:,} & {r['ab_none']['nodes']:,} & {a['nodes']:,} & "
                 f"{100 * (1 - a['nodes'] / m['nodes']):.1f}\\% \\\\"
                 + ("\\midrule" if r["depth"] == dmax and r is not nodes[-1] else ""))
    open(os.path.join(RES, "table_nodes.tex"), "w").write("\n".join(L))
    L = []
    for key in CASES:
        for r in cases[key]["by_depth"]:
            v = r["value"]
            vs = f"mate ({'+' if v > 0 else '-'})" if abs(v) > 90000 else str(v)
            L.append(f"{key} & {r['algo'].replace('alphabeta', 'alpha-beta')} & {r['depth']} & {r['move'].replace('#', chr(92) + '#')} & {vs} & "
                     f"{r['nodes']:,} & {r['seconds'] * 1000:,.0f} \\\\")
        L.append("\\midrule")
    open(os.path.join(RES, "table_cases.tex"), "w").write("\n".join(L[:-1]))
    L = []
    for lab, games, abspec in [("A (equal depth 2)", arena_a, "alphabeta:2"), ("B (AB depth 3)", arena_b, "alphabeta:3")]:
        nm, tm, km = per_move(games, "minimax"); na, ta, ka = per_move(games, "alphabeta")
        L.append(f"{lab} & {len(games)} & {score(games, 'minimax:2'):g} -- {score(games, abspec):g} & "
                 f"{nm:,.0f} & {na:,.0f} & {tm * 1000:,.0f} & {ta * 1000:,.0f} \\\\")
    open(os.path.join(RES, "table_arena.tex"), "w").write("\n".join(L))
    L = [f"{g['opening']} & {g['white'].replace('alphabeta', 'AB').replace('minimax', 'MM')} & "
         f"{g['black'].replace('alphabeta', 'AB').replace('minimax', 'MM')} & {g['result']} & "
         f"{g['reason'].replace('_', ' ')} & {g['plies']} \\\\" for g in arena_b]
    open(os.path.join(RES, "table_games_b.tex"), "w").write("\n".join(L))


def main():
    os.makedirs(RES, exist_ok=True); os.makedirs(FIG, exist_ok=True)
    if "--post" in sys.argv:  # only recompute the agreement check and report numbers from saved results
        R = json.load(open(os.path.join(RES, "results.json")))
        if "agreement" not in R:
            R["agreement"] = agreement(R["arena_equal_depth"]); print(R["agreement"])
            json.dump(R, open(os.path.join(RES, "results.json"), "w"), indent=1)
        write_numbers(R)
        write_tables(R)
        arena_plot(R["arena_equal_depth"], R["arena_deeper_ab"])
        return
    print("tree figure ..."); tree = tree_figure("8/8/8/4k3/8/8/4P3/4K3 w - - 0 1", 2, "search_tree.png")
    print(tree)
    print("node-count experiment ..."); nodes = node_experiment()
    print("cases ..."); cases = case_experiment()
    print("arena ...")
    plies = 60 if QUICK else 100
    arena_a = arena("A", "minimax:2", "alphabeta:2", plies)
    arena_b = arena("B", "minimax:2", "alphabeta:3", plies)
    R = {"tree": tree, "nodes": nodes, "cases": cases, "arena_equal_depth": arena_a, "arena_deeper_ab": arena_b,
         "agreement": agreement(arena_a)}
    json.dump(R, open(os.path.join(RES, "results.json"), "w"), indent=1)
    write_numbers(R)

    # --- node count plot
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    pos = "Italian opening"
    rr = [r for r in nodes if r["position"] == pos]
    ds = [r["depth"] for r in rr]
    for key, lab, col in [("minimax", "Minimax", ORANGE), ("ab_worst", "Alpha-beta, worst ordering", PURPLE),
                          ("ab_none", "Alpha-beta, generator order", GREY), ("ab_mvv", "Alpha-beta, MVV-LVA ordering", BLUE)]:
        axes[0].plot(ds, [r[key]["nodes"] for r in rr], "o-", color=col, label=lab)
    axes[0].set_yscale("log"); axes[0].set_xlabel("search depth d (plies)"); axes[0].set_xticks(ds)
    axes[0].set_title(f"Nodes searched, {pos}", fontsize=10); axes[0].legend(fontsize=8); axes[0].grid(alpha=.3)
    dmax = max(ds)
    names = list(SUITE)
    x = range(len(names))
    for k, (key, col, lab) in enumerate([("minimax", ORANGE, "Minimax"), ("ab_mvv", BLUE, "Alpha-beta (MVV-LVA)")]):
        vals = [next(r for r in nodes if r["position"] == n and r["depth"] == dmax)[key]["nodes"] for n in names]
        axes[1].bar([i + (k - .5) * .38 for i in x], vals, .38, color=col, label=lab)
    axes[1].set_yscale("log"); axes[1].set_xticks(list(x)); axes[1].set_xticklabels(names, rotation=20, fontsize=8)
    axes[1].set_title(f"Nodes searched at depth {dmax}, all test positions", fontsize=10); axes[1].legend(fontsize=8)
    save(fig, "nodes_vs_depth.png")

    # --- case boards
    for key, (title, fen) in CASES.items():
        b = chess.Board(fen)
        fig, ax = plt.subplots(figsize=(3.6, 3.9))
        arrows = []
        byd = cases[key]["by_depth"]
        shallow = next(r for r in byd if r["algo"] == "alphabeta" and r["depth"] == (1 if key != "E1" else 2))
        deep = [r for r in byd if r["algo"] == "alphabeta"][-1]
        if shallow["move"] != deep["move"]:
            arrows.append((b.parse_san(shallow["move"]), ORANGE))
        if key == "E2":
            arrows.append((b.parse_san(cases["E2"]["greedy_static"]), ORANGE))
        arrows.append((b.parse_san(deep["move"]), GREEN))
        draw_board(ax, b, arrows, f"{key}: {title}\n{'White' if b.turn else 'Black'} to move")
        save(fig, f"case_{key}.png")

    arena_plot(arena_a, arena_b)
    write_tables(R)
    print("done")


if __name__ == "__main__":
    main()
