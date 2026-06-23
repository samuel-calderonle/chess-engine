import sys
import chess
import time

# =====================================================================
# 1. FIXED POSITIONAL TABLES (Sunfish Balanced Data)
# =====================================================================
PAWN_TABLE = [
    0, 0, 0, 0, 0, 0, 0, 0,
    10, 10, 0, -10, -10, 0, 10, 10,
    5, 0, 0, 5, 5, 0, 0, 5,
    0, 0, 10, 20, 20, 10, 0, 0,
    5, 5, 20, 30, 30, 20, 5, 5,
    10, 10, 20, 30, 30, 20, 10, 10,
    10, 20, 20, 30, 30, 20, 20, 10,
    0, 0, 0, 0, 0, 0, 0, 0
]

# Tamed the center down to +10 so knights don't get obsessed with diving in prematurely
KNIGHT_TABLE = [
    -50, -40, -20, -20, -20, -20, -40, -50,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -30, 5, 10, 10, 10, 10, 5, -30,
    -30, 0, 10, 10, 10, 10, 0, -30,
    -30, 5, 10, 10, 10, 10, 5, -30,
    -30, 0, 5, 10, 10, 5, 0, -30,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50
]

BISHOP_TABLE = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20
]

ROOK_TABLE = [
    0, 0, 0, 5, 5, 0, 0, 0,
    5, 10, 10, 10, 10, 10, 10, 5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    0, 0, 0, 0, 0, 0, 0, 0
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

KING_OPENING = [
    20, 30, 10, 0, 0, 10, 30, 20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    -20, -10, -10, -10, -10, -10, -10, -20
]

PIECE_VALUES = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000
}

TABLES = {
    chess.PAWN: PAWN_TABLE, chess.KNIGHT: KNIGHT_TABLE, chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE, chess.QUEEN: QUEEN_TABLE, chess.KING: KING_OPENING
}

TRANSPOSITION_TABLE = {}
START_TIME = 0
ALLOCATED_TIME = 0
TIME_OUT = False


# =====================================================================
# 2. INTELLECTUAL MOVE ORDERING (The Dance Killer)
# =====================================================================
def score_move(board, move, tt_move=None):
    """Assigns priority scores to sort best moves to the front of the tree."""
    if move == tt_move:
        return 100000  # Stored TT move always checked absolute first

    # MVV-LVA sorting for captures
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        victim_val = PIECE_VALUES[victim.piece_type] if victim else 100
        attacker_val = PIECE_VALUES[attacker.piece_type] if attacker else 100
        return 50000 + (victim_val - (attacker_val / 100.0))

    # Promote early castling
    if board.is_castling(move):
        return 1000

    # ANTIDOTE TO TRAP: Penalize moving the same piece twice in a row during opening
    if board.fullmove_number <= 10 and board.move_stack:
        last_move = board.move_stack[-2] if len(board.move_stack) >= 2 else None
        if last_move and board.piece_at(move.from_square) == board.piece_at(last_move.to_square):
            return -500  # Heavily discourages shuffling the same knight around

    # Prioritize developing bishops/knights from home rank
    moving_piece = board.piece_at(move.from_square)
    if moving_piece and moving_piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
        from_rank = chess.square_rank(move.from_square)
        if (moving_piece.color == chess.WHITE and from_rank == 0) or (
                moving_piece.color == chess.BLACK and from_rank == 7):
            return 500  # Bonus for standard initial development!

    return 0


# =====================================================================
# 3. INCREMENTAL EVALUATION MATH
# =====================================================================
def get_initial_score(board):
    score = 0
    current_move_number = board.fullmove_number
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            value = PIECE_VALUES[piece.piece_type]
            table_index = square if piece.color == chess.WHITE else chess.square_mirror(square)

            position_bonus = TABLES[piece.piece_type][table_index]
            if piece.piece_type == chess.BISHOP and current_move_number > 15:
                position_bonus = 0

            total_value = value + position_bonus
            if piece.color == chess.WHITE:
                score += total_value
            else:
                score -= total_value
    # =====================================================================
    # THE KING-HUNT HEURISTIC (Forces the engine to close out won endgames)
    # =====================================================================
    # Count how many pieces are left alive on the board
    total_pieces = len(board.piece_map())

    # If it's an endgame (less than 6 pieces total left alive), start the hunt!
    if total_pieces <= 6:
        # Find where both kings are located
        white_king_sq = board.king(chess.WHITE)
        black_king_sq = board.king(chess.BLACK)

        if white_king_sq is not None and black_king_sq is not None:
            # Calculate the literal distance between the two kings
            king_distance = chess.square_distance(white_king_sq, black_king_sq)

            # Find how close the enemy king is to the edges of the board
            # Center squares have high rank/file IDs (3,4). Edges have low or high (0, 7).
            enemy_king = black_king_sq if board.turn == chess.WHITE else white_king_sq
            ek_rank = chess.square_rank(enemy_king)
            ek_file = chess.square_file(enemy_king)

            # Distance from center (3.5 is the absolute center of the board)
            dist_from_center = abs(ek_rank - 3.5) + abs(ek_file - 3.5)

            # Award points for pushing the enemy king to the edge and bringing your king close!
            hunt_bonus = int((dist_from_center * 10) + (14 - king_distance))

            if board.turn == chess.WHITE:
                score += hunt_bonus
            else:
                score -= hunt_bonus

    return score


def incremental_update(board, move, current_score):
    piece = board.piece_at(move.from_square)
    if not piece:
        return current_score

    from_idx = move.from_square if piece.color == chess.WHITE else chess.square_mirror(move.from_square)
    to_idx = move.to_square if piece.color == chess.WHITE else chess.square_mirror(move.to_square)

    old_val = PIECE_VALUES[piece.piece_type] + TABLES[piece.piece_type][from_idx]
    new_val = PIECE_VALUES[piece.piece_type] + TABLES[piece.piece_type][to_idx]

    if piece.color == chess.WHITE:
        current_score += (new_val - old_val)
    else:
        current_score -= (new_val - old_val)

    if board.is_castling(move):
        if move.to_square == chess.G1:
            r_from, r_to = chess.H1, chess.F1
        elif move.to_square == chess.C1:
            r_from, r_to = chess.A1, chess.D1
        elif move.to_square == chess.G8:
            r_from, r_to = chess.H8, chess.F8
        elif move.to_square == chess.C8:
            r_from, r_to = chess.A8, chess.D8
        r_piece = board.piece_at(r_from)
        if r_piece:
            rf_idx = r_from if r_piece.color == chess.WHITE else chess.square_mirror(r_from)
            rt_idx = r_to if r_piece.color == chess.WHITE else chess.square_mirror(r_to)
            current_score += (PIECE_VALUES[chess.ROOK] + ROOK_TABLE[rt_idx]) - (
                        PIECE_VALUES[chess.ROOK] + ROOK_TABLE[rf_idx]) if r_piece.color == chess.WHITE else -(
                        (PIECE_VALUES[chess.ROOK] + ROOK_TABLE[rt_idx]) - (
                            PIECE_VALUES[chess.ROOK] + ROOK_TABLE[rf_idx]))

    if board.is_capture(move) and not board.is_en_passant(move):
        captured_piece = board.piece_at(move.to_square)
        if captured_piece:
            cap_idx = move.to_square if captured_piece.color == chess.WHITE else chess.square_mirror(move.to_square)
            cap_val = PIECE_VALUES[captured_piece.piece_type] + TABLES[captured_piece.piece_type][cap_idx]
            if captured_piece.color == chess.WHITE:
                current_score -= cap_val
            else:
                current_score += cap_val

    return current_score


# =====================================================================
# 4. SEARCH PIPELINES (PVS + CACHE + QS)
# =====================================================================
def quiescence_search(board, alpha, beta, current_score):
    global TIME_OUT
    if time.time() - START_TIME > ALLOCATED_TIME:
        TIME_OUT = True
        return alpha

    color_multiplier = 1 if board.turn == chess.WHITE else -1
    stand_pat = current_score * color_multiplier

    if stand_pat >= beta: return beta
    if stand_pat > alpha: alpha = stand_pat

    moves = [m for m in board.legal_moves if board.is_capture(m)]
    moves.sort(key=lambda m: score_move(board, m), reverse=True)

    for move in moves:
        next_score = incremental_update(board, move, current_score)
        board.push(move)
        score = -quiescence_search(board, -beta, -alpha, next_score)
        board.pop()

        if TIME_OUT: return alpha
        if score >= beta: return beta
        if score > alpha: alpha = score
    return alpha


def pvs_search(board, depth, alpha, beta, current_score):
    global TIME_OUT
    if time.time() - START_TIME > ALLOCATED_TIME:
        TIME_OUT = True
        return alpha

    if board.is_repetition(2):
        return 0

    board_fen = board.fen()
    tt_move = None
    if board_fen in TRANSPOSITION_TABLE:
        cached_depth, cached_score, tt_move = TRANSPOSITION_TABLE[board_fen]
        if cached_depth >= depth: return cached_score

    if depth == 0 or board.is_game_over():
        return quiescence_search(board, alpha, beta, current_score)

    legal_moves = list(board.legal_moves)
    legal_moves.sort(key=lambda m: score_move(board, m, tt_move), reverse=True)

    max_score = float('-inf')
    best_move_found = None
    is_first_move = True

    for move in legal_moves:
        next_score = incremental_update(board, move, current_score)
        board.push(move)

        if is_first_move:
            score = -pvs_search(board, depth - 1, -beta, -alpha, next_score)
            is_first_move = False
        else:
            score = -pvs_search(board, depth - 1, -(alpha + 1), -alpha, next_score)
            if alpha < score < beta:
                score = -pvs_search(board, depth - 1, -beta, -alpha, next_score)

        board.pop()
        if TIME_OUT: return alpha

        if score > max_score:
            max_score = score
            best_move_found = move
        if score > alpha: alpha = score
        if alpha >= beta: break

    if not TIME_OUT:
        TRANSPOSITION_TABLE[board_fen] = (depth, max_score, best_move_found)
    return max_score

# =====================================================================
# 5. ASPIRATION WINDOW ENGINE CONTROLLER
# =====================================================================
def get_best_move(board, wtime, btime, winc, binc):
    global START_TIME, ALLOCATED_TIME, TIME_OUT
    START_TIME = time.time()
    TIME_OUT = False

    my_time = wtime if board.turn == chess.WHITE else btime
    my_inc = winc if board.turn == chess.WHITE else binc
    ALLOCATED_TIME = (my_time / 30.0) + (my_inc * 0.8) if my_time > 0 else 0.5

    initial_score = get_initial_score(board)
    best_move = None
    last_layer_score = 0

    for current_depth in range(1, 15):
        alpha = last_layer_score - 150 if current_depth > 1 else float('-inf')
        beta = last_layer_score + 150 if current_depth > 1 else float('inf')

        legal_moves = list(board.legal_moves)
        board_fen = board.fen()
        tt_move = TRANSPOSITION_TABLE[board_fen][2] if (board_fen in TRANSPOSITION_TABLE and TRANSPOSITION_TABLE[board_fen][2]) else None
        legal_moves.sort(key=lambda m: score_move(board, m, tt_move), reverse=True)

        current_best_score = float('-inf')
        current_best_move = None

        while True:
            for move in legal_moves:
                next_score = incremental_update(board, move, initial_score)
                board.push(move)
                score = -pvs_search(board, current_depth - 1, -beta, -alpha, next_score)
                board.pop()

                if TIME_OUT: break
                if score > current_best_score:
                    current_best_score = score
                    current_best_move = move
                alpha = max(alpha, score)

            if TIME_OUT: break
            if current_best_score <= alpha or current_best_score >= beta:
                alpha, beta = float('-inf'), float('inf')
                continue
            break

        if TIME_OUT: break
        best_move = current_best_move
        last_layer_score = current_best_score
        print(f"info depth {current_depth} score cp {current_best_score}")
        sys.stdout.flush()

    if not best_move and list(board.legal_moves):
        best_move = list(board.legal_moves)
    return best_move

# =====================================================================
# 6. ENGINE UCI SYSTEM
# =====================================================================
def uci_loop():
    board = chess.Board()
    while True:
        line = sys.stdin.readline().strip()
        if not line: continue
        tokens = line.split()
        if not tokens: continue
        command = tokens

        if command == "uci":
            print("id name FoundationEngine_v5_Elite")
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
            if "wtime" in tokens: wtime = int(tokens[tokens.index("wtime") + 1]) / 1000.0
            if "btime" in tokens: btime = int(tokens[tokens.index("btime") + 1]) / 1000.0
            if "winc" in tokens: winc = int(tokens[tokens.index("winc") + 1]) / 1000.0
            if "binc" in tokens: binc = int(tokens[tokens.index("binc") + 1]) / 1000.0
            best_move = get_best_move(board, wtime, btime, winc, binc)
            print(f"bestmove {best_move.uci() if best_move else '0000'}")
            sys.stdout.flush()
        elif command == "quit": break

if __name__ == "__main__":
    uci_loop()
