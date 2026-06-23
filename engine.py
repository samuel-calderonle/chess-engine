import sys
import chess
import time

# =====================================================================
# 1. CORE CACHE & EVALUATION ARRAYS
# =====================================================================
TRANSPOSITION_TABLE = {}

PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,  # Rank 8 (Promotion)
    50, 50, 50, 50, 50, 50, 50, 50,  # Rank 7
    10, 10, 20, 30, 30, 20, 10, 10,  # Rank 6
     5,  5, 10, 25, 25, 10,  5,  5,  # Rank 5
     0,  0,  0, 20, 20,  0,  0,  0,  # Rank 4
     5, -5,-10,  0,  0,-10, -5,  5,  # Rank 3
     5, 10, 10,-20,-20, 10, 10,  5,  # Rank 2
     0,  0,  0,  0,  0,  0,  0,  0   # Rank 1
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10, 10,  5,  5,  5,  5, 10,-10,
    -10, 20,  0,  0,  0,  0, 20,-10,
    -20,-10,-40,-10,-10,-40,-10,-20  # Penalize trapping behind central pawns
]


ROOK_TABLE = [
    0, 0, 0, 15, 15, 0, 0, 0,
    5, 40, 40, 40, 40, 30, 10, 5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    0, 0, 20, 30, 30, 20, 0, 0
]

QUEEN_TABLE = [
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 5, 0, 0, 0, 0, -10,
    -10, 5, 5, 5, 5, 5, 0, -10,
    -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -10, 5, 0, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20
]

PIECE_VALUES = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 350,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000
}

# Global search variables for tracking time allocations
START_TIME = 0
ALLOCATED_TIME = 0
TIME_OUT = False


def evaluate_board(board):
    if board.is_checkmate():
        return -99999 if board.turn == chess.WHITE else 99999
    if board.is_game_over():
        return 0

    score = 0
    current_move_number = board.fullmove_number

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            value = PIECE_VALUES[piece.piece_type]
            table_index = square if piece.color == chess.WHITE else chess.square_mirror(square)

            position_bonus = 0
            if piece.piece_type == chess.PAWN:
                position_bonus = PAWN_TABLE[table_index]
            elif piece.piece_type == chess.KNIGHT:
                position_bonus = KNIGHT_TABLE[table_index]
            elif piece.piece_type == chess.BISHOP:
                if current_move_number <= 15:
                    position_bonus = BISHOP_TABLE[table_index]
            elif piece.piece_type == chess.ROOK:
                position_bonus = ROOK_TABLE[table_index]
            elif piece.piece_type == chess.QUEEN:
                position_bonus = QUEEN_TABLE[table_index]

            total_value = value + position_bonus
            if piece.color == chess.WHITE:
                score += total_value
            else:
                score -= total_value
    return score


# =====================================================================
# 2. FUNDAMENTAL: QUIESCENCE SEARCH (TACTICAL BLUNDER CONTROL)
# =====================================================================
def quiescence_search(board, alpha, beta):
    global TIME_OUT
    # Check timer limits periodically
    if time.time() - START_TIME > ALLOCATED_TIME:
        TIME_OUT = True
        return alpha

    color_multiplier = 1 if board.turn == chess.WHITE else -1
    stand_pat = evaluate_board(board) * color_multiplier

    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    # Only look at captures beyond the standard depth boundary
    moves = [m for m in board.legal_moves if board.is_capture(m)]
    moves = sorted(moves, key=lambda m: board.is_capture(m), reverse=True)

    for move in moves:
        board.push(move)
        score = -quiescence_search(board, -beta, -alpha)
        board.pop()

        if TIME_OUT:
            return alpha

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


# =====================================================================
# 3. ADVANCED SELECTION ENGINE (ALPHA-BETA + TT MOVE SORTING)
# =====================================================================
def negamax_alpha_beta(board, depth, alpha, beta):
    global TIME_OUT
    if time.time() - START_TIME > ALLOCATED_TIME:
        TIME_OUT = True
        return alpha

    board_fen = board.fen()
    tt_move = None

    # Retrieve memory data from the enhanced Transposition Table
    if board_fen in TRANSPOSITION_TABLE:
        cached_depth, cached_score, tt_move = TRANSPOSITION_TABLE[board_fen]
        if cached_depth >= depth:
            return cached_score

    # Hand off to Quiescence Search at depth zero
    if depth == 0 or board.is_game_over():
        return quiescence_search(board, alpha, beta)

    # --- HEURISTIC: SORT TT MOVE FIRST ---
    # Put the best move found in previous iterations at the absolute front of the list
    legal_moves = list(board.legal_moves)
    if tt_move and tt_move in legal_moves:
        legal_moves.remove(tt_move)
        legal_moves.insert(0, tt_move)
    else:
        legal_moves.sort(key=lambda m: board.is_capture(m), reverse=True)

    max_score = float('-inf')
    best_move_found = None

    for move in legal_moves:
        board.push(move)
        score = -negamax_alpha_beta(board, depth - 1, -beta, -alpha)
        board.pop()

        if TIME_OUT:
            return alpha

        if score > max_score:
            max_score = score
            best_move_found = move
        if score > alpha:
            alpha = score

        if alpha >= beta:
            break

    if not TIME_OUT:
        TRANSPOSITION_TABLE[board_fen] = (depth, max_score, best_move_found)

    return max_score


# =====================================================================
# 4. FUNDAMENTAL: ITERATIVE DEEPENING & TIME MANAGEMENT
# =====================================================================
def get_best_move(board, wtime, btime, winc, binc):
    global START_TIME, ALLOCATED_TIME, TIME_OUT
    START_TIME = time.time()
    TIME_OUT = False

    # Dynamic clock calculations: manage allocations safely based on player side
    my_time = wtime if board.turn == chess.WHITE else btime
    my_inc = winc if board.turn == chess.WHITE else binc

    # Budget rule: spend roughly 1/30th of main clock plus the increment cushion
    if my_time > 0:
        ALLOCATED_TIME = (my_time / 30.0) + (my_inc * 0.8)
    else:
        ALLOCATED_TIME = 0.5  # Fallback safety default time limit

    best_move = None
    # Step up layer depth iteratively from 1 up to 10+
    for current_depth in range(1, 12):
        alpha = float('-inf')
        beta = float('inf')

        legal_moves = list(board.legal_moves)
        # Check Transposition Table entry to prioritize move ordering
        board_fen = board.fen()
        if board_fen in TRANSPOSITION_TABLE:
            _, _, tt_move = TRANSPOSITION_TABLE[board_fen]
            if tt_move and tt_move in legal_moves:
                legal_moves.remove(tt_move)
                legal_moves.insert(0, tt_move)

        current_best_score = float('-inf')
        current_best_move = None

        for move in legal_moves:
            board.push(move)
            score = -negamax_alpha_beta(board, current_depth - 1, -beta, -alpha)
            board.pop()

            if TIME_OUT:
                break

            if score > current_best_score:
                current_best_score = score
                current_best_move = move
            alpha = max(alpha, score)

        if TIME_OUT:
            break  # Stop search safely and preserve previous layer's data

        best_move = current_best_move
        # Send debugging data back to Cutechess log panels
        print(f"info depth {current_depth} score cp {current_best_score}")
        sys.stdout.flush()

    # Absolute fallback safety selection
    if not best_move and list(board.legal_moves):
        best_move = list(board.legal_moves)[0]

    return best_move


# =====================================================================
# 5. UCI INTERFACE ROUTER LOOP
# =====================================================================
def uci_loop():
    board = chess.Board()

    while True:
        line = sys.stdin.readline().strip()
        if not line:
            continue

        tokens = line.split()
        if not tokens:
            continue
        command = tokens[0]

        if command == "uci":
            print("id name FoundationEngine_v4")
            print("id author MasterDeveloper")
            print("uciok")
            sys.stdout.flush()

        elif command == "isready":
            print("readyok")
            sys.stdout.flush()

        elif command == "ucinewgame":
            board = chess.Board()
            TRANSPOSITION_TABLE.clear()

        elif command == "position":
            board = chess.Board()
            if "moves" in tokens:
                moves_index = tokens.index("moves")
                for move_str in tokens[moves_index + 1:]:
                    board.push(chess.Move.from_uci(move_str))

        elif command == "go":
            wtime, btime, winc, binc = 0, 0, 0, 0
            # Read real physical game clocks provided dynamically by Cutechess
            if "wtime" in tokens:
                wtime = int(tokens[tokens.index("wtime") + 1]) / 1000.0
            if "btime" in tokens:
                btime = int(tokens[tokens.index("btime") + 1]) / 1000.0
            if "winc" in tokens:
                winc = int(tokens[tokens.index("winc") + 1]) / 1000.0
            if "binc" in tokens:
                binc = int(tokens[tokens.index("binc") + 1]) / 1000.0

            best_move = get_best_move(board, wtime, btime, winc, binc)

            if best_move:
                print(f"bestmove {best_move.uci()}")
            else:
                print("bestmove 0000")
            sys.stdout.flush()

        elif command == "quit":
            break


if __name__ == "__main__":
    uci_loop()
