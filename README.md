# Multi-Agent Chess Arena: Minimax vs. Alpha-Beta

23CSE401 Fundamentals of AI case study. Two game-playing agents share the same heuristic
evaluation (material + piece-square tables) and compete in a chess arena:

- **Minimax agent**: depth-limited minimax that searches every move.
- **Alpha-Beta agent**: the same search with alpha-beta pruning and MVV-LVA move ordering.

The code shows that alpha-beta returns exactly the minimax value while visiting far fewer positions.
With the saved effort the agent can search one ply deeper, and that deeper search wins games.

## Requirements

- Python 3.9 or newer
- `pip install chess matplotlib python-pptx`
  (`python-pptx` is only needed to rebuild the slides)
- To rebuild the report PDF: any LaTeX distribution (`pdflatex`) or [Tectonic](https://tectonic-typesetting.github.io)

## How to run

```bash
cd code

# watch a game move by move (default: Minimax depth 2 as White vs Alpha-Beta depth 3 as Black)
python chess_agents.py --white minimax:2 --black alphabeta:3

# compare both searches on one position
python chess_agents.py --analyse --white minimax:3 --fen "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"

# regenerate every table and figure used in the report and slides
python experiments.py            # about 10-15 minutes (minimax at depth 4 is slow)
python experiments.py --quick    # about 1 minute (depth <= 3, fewer games)

# rebuild slides and report
python make_ppt.py
cd ../report && pdflatex report.tex       # or: tectonic report.tex
```

## Inputs

| Option | Meaning |
|---|---|
| `--white`, `--black` | Agent spec `algo:depth[:ordering]`. `algo` is `minimax` or `alphabeta`; `ordering` (alpha-beta only) is `mvv` (default), `none` or `worst` |
| `--fen` | Start position in FEN (default: the normal start position) |
| `--max-plies` | Game length limit. At the limit, a lead of 300 centipawns or more counts as a win, otherwise a draw |
| `--analyse` | Do not play; run both searches on `--fen` and print move, value, nodes and time |

The test positions, cases and arena openings are listed at the top of `code/experiments.py`.

## Outputs

- **Console**: every move with its search value, nodes visited and time, then the final board and result.
- **`results/results.json`**: all raw numbers (node counts, case results, and every arena game with its move list).
- **`results/table_*.tex`**: tables that the report loads.
- **`figures/*.png`**: search tree, node counts versus depth, case boards and arena results.

## Files

| File | Description |
|---|---|
| `code/chess_agents.py` | Heuristic evaluation, Minimax, Alpha-Beta (with move ordering), the game loop (arena) and the command-line interface |
| `code/experiments.py` | All experiments: game-tree figure, node counts at depths 1-4, working and edge cases, two arena matches |
| `code/make_ppt.py` | Builds `presentation/Chess_Arena_Minimax_vs_AlphaBeta.pptx` from the results |
| `report/report.tex`, `report/report.pdf` | LaTeX report |
| `presentation/*.pptx` | Slides |
| `results/`, `figures/` | Generated outputs (see above) |
