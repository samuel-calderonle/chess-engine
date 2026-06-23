# FoundationEngine_v4 🤖

A lightweight, tournament-ready chess engine written entirely in Python, using standard alpha-beta pruning and advanced move-sorting heuristics.

## 🚀 Features Implemented
*   **Negamax Architecture:** Compact, color-agnostic minimax search flow.
*   **Alpha-Beta Pruning:** High-efficiency branch reduction to maximize search speed.
*   **Iterative Deepening:** Adaptive time management that dynamically scales calculation depth based on remaining match time.
*   **Enhanced Transposition Table:** Color-aware memory caching dictionary (`board.fen()`) that tracks identical board layouts to eliminate duplicate calculations and automatically sort the best move first.
*   **Quiescence Search (QS):** Tactical look-ahead layer that isolates and resolves forcing captures beyond the search boundary to completely mitigate horizon blunders.
*   **Phase-Based Positional Evaluation:** Unique move-15 switch that scales bishop development bonuses through the opening before opening up long-range diagonals in the middlegame.

## 📊 Tournament Calibration Results

### Matchup vs. Stockfish_1320_Baseline
*   **Time Control:** 40 moves in 2 minutes
*   **Total Scope:** 100 Games (Alternate colors)

| Engine | Score | Wins | Losses | Draws | Calculated Elo |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FoundationEngine_v4** | 32 / 100 | 28 | 64 | 8 | **1190 Elo** |
| **Stockfish 1320 Base** | 68 / 100 | 64 | 28 | 8 | **1320 Elo** |

> **Cutechess Output Log:** 
> `Elo difference: -130.9 +/- 70.8, LOS: 0.0 %, DrawRatio: 8.0 %`


## 🛠️ Execution Requirements
*   Python 3.10+
*   `python-chess` library (`pip install python-chess`)
