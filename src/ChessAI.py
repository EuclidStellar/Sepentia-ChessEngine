"""
Handling the AI moves.
"""
import random
import threading
import queue

piece_score = {"K": 0, "Q": 9, "R": 5, "B": 3, "N": 3, "p": 1}

knight_scores = [[0.0, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1, 0.0],
                 [0.1, 0.3, 0.5, 0.5, 0.5, 0.5, 0.3, 0.1],
                 [0.2, 0.5, 0.6, 0.65, 0.65, 0.6, 0.5, 0.2],
                 [0.2, 0.55, 0.65, 0.7, 0.7, 0.65, 0.55, 0.2],
                 [0.2, 0.5, 0.65, 0.7, 0.7, 0.65, 0.5, 0.2],
                 [0.2, 0.55, 0.6, 0.65, 0.65, 0.6, 0.55, 0.2],
                 [0.1, 0.3, 0.5, 0.55, 0.55, 0.5, 0.3, 0.1],
                 [0.0, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1, 0.0]]

bishop_scores = [[0.0, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0],
                 [0.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.2],
                 [0.2, 0.4, 0.5, 0.6, 0.6, 0.5, 0.4, 0.2],
                 [0.2, 0.5, 0.5, 0.6, 0.6, 0.5, 0.5, 0.2],
                 [0.2, 0.4, 0.6, 0.6, 0.6, 0.6, 0.4, 0.2],
                 [0.2, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.2],
                 [0.2, 0.5, 0.4, 0.4, 0.4, 0.4, 0.5, 0.2],
                 [0.0, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0]]

rook_scores = [[0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25],
               [0.5, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.5],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.25, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25, 0.25]]

queen_scores = [[0.0, 0.2, 0.2, 0.3, 0.3, 0.2, 0.2, 0.0],
                [0.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.2],
                [0.2, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.2],
                [0.3, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.3],
                [0.4, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.3],
                [0.2, 0.5, 0.5, 0.5, 0.5, 0.5, 0.4, 0.2],
                [0.2, 0.4, 0.5, 0.4, 0.4, 0.4, 0.4, 0.2],
                [0.0, 0.2, 0.2, 0.3, 0.3, 0.2, 0.2, 0.0]]

pawn_scores = [[0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
               [0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7],
               [0.3, 0.3, 0.4, 0.5, 0.5, 0.4, 0.3, 0.3],
               [0.25, 0.25, 0.3, 0.45, 0.45, 0.3, 0.25, 0.25],
               [0.2, 0.2, 0.2, 0.4, 0.4, 0.2, 0.2, 0.2],
               [0.25, 0.15, 0.1, 0.2, 0.2, 0.1, 0.15, 0.25],
               [0.25, 0.3, 0.3, 0.0, 0.0, 0.3, 0.3, 0.25],
               [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]]

piece_position_scores = {"wN": knight_scores,
                         "bN": knight_scores[::-1],
                         "wB": bishop_scores,
                         "bB": bishop_scores[::-1],
                         "wQ": queen_scores,
                         "bQ": queen_scores[::-1],
                         "wR": rook_scores,
                         "bR": rook_scores[::-1],
                         "wp": pawn_scores,
                         "bp": pawn_scores[::-1]}

CHECKMATE = 10000
STALEMATE = 0
DEPTH = 5


def orderMoves(moves, game_state):
    # Order moves based on captures and high-value targets
    capture_moves = [move for move in moves if game_state.board[move.end_row][move.end_col] != "--"]
    quiet_moves = [move for move in moves if move not in capture_moves]
    
    # Sort capture moves by their value
    #what will be benifit if this ? benifit is that we will capture the high value pieces first
    capture_moves.sort(key=lambda move: piece_score[game_state.board[move.end_row][move.end_col][1]], reverse=True)

    # Sort quiet moves by their positional score
    #what will be benifit if this ? benifit is that we will move the pieces to the best position
    quiet_moves.sort(key=lambda move: piece_position_scores.get(game_state.board[move.start_row][move.start_col], [[0]*8]*8)[move.end_row][move.end_col], reverse=True)
    
    ordered_moves = capture_moves + quiet_moves

    return ordered_moves


def findMoveNegaMaxAlphaBeta(game_state, valid_moves, depth, alpha, beta, turn_multiplier):
    global next_move
    if depth == 0 or game_state.stalemate or game_state.checkmate:
        return turn_multiplier * scoreBoard(game_state)

    max_score = -CHECKMATE
    # Move Ordering: Sort moves based on some heuristic
    ordered_moves = orderMoves(valid_moves, game_state)
    for move in ordered_moves:
        game_state.makeMove(move)
        next_moves = game_state.getValidMoves()
        score = -findMoveNegaMaxAlphaBeta(game_state, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)
        game_state.undoMove()
        if score > max_score:
            max_score = score
            if depth == DEPTH:
                next_move = move
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return max_score

# Transposition Table
transposition_table = {}

def findMove(game_state, valid_moves, return_queue):
    global next_move, transposition_table
    next_move = None
    for depth in range(1, DEPTH + 1):
        findMoveNegaMaxAlphaBetaTT(game_state, valid_moves, depth, -CHECKMATE, CHECKMATE, 1 if game_state.white_to_move else -1)
        # clear transposition table after each depth iteration
        transposition_table = {}
        if next_move is not None:
            break
    return_queue.put(next_move)

def findMoveNegaMaxAlphaBetaTT(game_state, valid_moves, depth, alpha, beta, turn_multiplier):
    global next_move, transposition_table
    hash_key = game_state.getHashKey()
    if hash_key in transposition_table:
        return transposition_table[hash_key]

    if depth == 0 or game_state.stalemate or game_state.checkmate:
        return turn_multiplier * scoreBoard(game_state)

    max_score = -CHECKMATE
    ordered_moves = orderMoves(valid_moves, game_state)
    for move in ordered_moves:
        game_state.makeMove(move)
        next_moves = game_state.getValidMoves()
        score = -findMoveNegaMaxAlphaBetaTT(game_state, next_moves, depth - 1, -beta, -alpha, -turn_multiplier)
        game_state.undoMove()
        if score > max_score:
            max_score = score
            if depth == DEPTH:
                next_move = move
        alpha = max(alpha, score)
        if alpha >= beta:
            break

    transposition_table[hash_key] = max_score
    return max_score

def controlCenterMoves(game_state, valid_moves):
    """
    Prioritize moves that control the center.
    """
    center_moves = []
    for move in valid_moves:
        if move.start_row in [1, 6] and abs(move.start_col - move.end_col) <= 1:
            center_moves.append(move)
        elif move.start_col == 4 or move.end_col == 4:
            center_moves.append(move)
    return center_moves

def openingMoves(game_state, valid_moves):
    """
    Integrate famous opening moves.
    """
    # Define opening moves (e.g., for white)
    opening_moves = {"Italian Game": ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"],
                     "Sicilian Defense": ["e2e4", "c7c5"]}

    # Check if current moves match any opening moves
    current_moves = [move.getChessNotation() for move in game_state.move_log]
    for opening in opening_moves.values():
        if current_moves[:len(opening)] == opening:
            return valid_moves[len(opening):]  # Return moves after opening moves

    return valid_moves

def findBestMove(game_state, valid_moves, return_queue):
    global next_move
    next_move = None
    #random.shuffle(valid_moves)
    findMoveNegaMaxAlphaBeta(game_state, valid_moves, DEPTH, -CHECKMATE, CHECKMATE,
                             1 if game_state.white_to_move else -1)
    return_queue.put(next_move)
        
def scoreBoard(game_state):
    """
    Score the board. A positive score is good for white, a negative score is good for black.
    """
    if game_state.checkmate:
        if game_state.white_to_move:
            return -CHECKMATE  # black wins
        else:
            return CHECKMATE  # white wins
    elif game_state.stalemate:
        return STALEMATE
    score = 0
    for row in range(len(game_state.board)):
        for col in range(len(game_state.board[row])):
            piece = game_state.board[row][col]
            if piece != "--":
                piece_position_score = 0
                if piece[1] != "K":
                    piece_position_score = piece_position_scores[piece][row][col]
                if piece[0] == "w":
                    score += piece_score[piece[1]] + piece_position_score
                if piece[0] == "b":
                    score -= piece_score[piece[1]] + piece_position_score

    return score


def findRandomMove(valid_moves):
    """
    Picks and returns a random valid move.
    """
    return random.choice(valid_moves)





