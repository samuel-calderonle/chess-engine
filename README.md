# FoundationEngine v5 Elite

A high-performance, lightweight chess engine written in Python. It features a complete search pipeline, dynamic move sorting, evaluation acceleration, and full **UCI (Universal Chess Interface)** compatibility for seamless integration with modern GUI applications.

---

## Key Features

*   **Principal Variation Search (PVS)**: Enhanced depth pruning using highly narrow search corridors.
*   **Transposition Table Cache**: Remembers previously explored positions to prevent deep search redundancies.
*   **Aspiration Windows**: Accelerates iteration layers by predicting tight alphabeta evaluation boundaries.
*   **Incremental Evaluation Math**: Accelerates node assessment by evaluating only moving pieces instead of recounting the full board layout.
*   **The King-Hunt Heuristic**: Applies localized endgame tracking vectors to trap bare enemy kings.
*   **The Dance Killer Ordering**: Prioritizes key strategic actions like MVV-LVA captures, early castling, and piece development.

---

## Architectural Overview

### 1. Static Evaluation Tables
The engine calculates square control metrics using fine-tuned **Sunfish Balanced positional arrays**. Piece valuations utilize standard centipawn metrics combined with specialized modifications:
*   **Knights**: Center values are restricted to +10 to prevent premature opening leaps.
*   **Bishops**: Positional bonuses scale down past move 15 to account for open midgames.

### 2. Move Ordering Pipeline
To prune suboptimal moves immediately, legal transitions are prioritized before Alpha-Beta assessment:
*   **Absolute First**: Stored Transposition Table hits.
*   **Captures**: Evaluated via **MVV-LVA** (Most Valuable Victim - Least Valuable Attacker).
*   **Development**: Offers positive rewards for rank-0/rank-7 minor piece progression while penalizing repetitive opening shifts.

### 3. Search Mechanics
The engine operates on a multi-stage search architecture to ensure deep calculation within time constraints:
1.  **Iterative Deepening**: Explores deeper horizons progressively from layer 1 up to 14.
2.  **Quiescence Search**: Extends search lines during tactical captures to avoid horizon effect distortions.
3.  **Dynamic Allocator**: Adjusts search depths automatically based on remaining time metrics and increment allocations.

---

## Requirements & Installation

The engine utilizes native Python libraries along with the `python-chess` API for fast rules validation.

### Install Dependencies
```bash
pip install python-chess
```

---

## How to Use

### 1. Command Line Interface (UCI)
Run the script directly via terminal to launch the interface loop:
```bash
python chess_engine.py
```
Type **`uci`** to verify communication protocols. The engine will respond with its signature metadata:
```text
id name FoundationEngine_v5_Elite
id author MasterDeveloper
uciok
```

### 2. Standard GUI Integration
You can connect this engine directly to popular graphical applications (such as **Arena Chess GUI**, **Cutechess**, or **BanksiaGUI**):
1. Locate the engine configuration or settings menu in your preferred GUI application.
2. Select **Add New Engine** and specify your system's python executable route.
3. Pass the engine script file name as the primary configuration parameter.
4. Set the engine type option field explicitly to **UCI**.
