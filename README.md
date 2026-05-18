# COMP30024 Project Part B — Cascade Game Playing Agent

**Team:** Water Bottle — Phuong Trang Tran (1409466), Ha Linh Nguyen (1492069)
**Subject:** COMP30024 Artificial Intelligence, Semester 1 2026, The University of Melbourne

## Overview

This project implements a game-playing agent for **Cascade**, a two-player adversarial board game played on an 8×8 grid. The agent is built on iterative deepening alpha-beta minimax and consistently beats the depth-3 minimax reference agent with a win rate of ~85%+.

## Approach

- **Search:** Iterative deepening alpha-beta minimax (depth up to 12), with a 2-second per-move time budget
- **Move ordering:** Killer moves + history heuristic + static type priority (eat > cascade > move > place)
- **Transposition table:** Persisted across turns, capped at 500,000 entries
- **Draw avoidance:** Path-set cycle detection and threefold-repetition penalty at the search level
- **Evaluation function:** Material advantage, squared stack heights, edge penalty, eat threats, cascade threats, and a centre bonus during placement

## Structure

```
agent/
  program.py          # Agent entry point (action + update interface)
  game_algorithm.py   # Minimax search, move ordering, heuristic
  state.py            # GameState, move generation, precomputed tables
referee/              # Provided game referee (do not modify)
report.tex            # LaTeX source for the project report
report.md             # Markdown draft of the report
```

## Running

Play against another agent using the referee:

```bash
python -m referee <red_agent> <blue_agent>
```

Compile the report:

```bash
pdflatex report.tex && pdflatex report.tex
```

