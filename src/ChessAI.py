"""
Handling the AI moves.
"""
import random
import threading
import queue

piece_score = {"K": 6000, "Q": 929, "R": 512, "B": 320, "N": 280, "p": 100}


pawn_scores = [[ 0,   0,   0,   0,   0,   0,   0,   0,],
                 [78,  83,  86,  73, 102,  82,  85,  90],
                 [ 7,  29,  21,  44,  40,  31,  44,   7],
                 [-17,  16,  -2,  15,  14,   0,  15, -13],
                 [-26,   3,  10,   9,   6,   1,   0, -23],
                 [-22,   9,   5, -11, -10,  -2,   3, -19],
                 [-31,   8,  -7, -37, -36, -14,   3, -31],
                 [0.0, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1, 0.0]]

bishop_scores = [[-59, -78, -82, -76, -23, -107, -37, -50],
                 [-11, 20, 35, -42, -39, 31, 2, -22],
                 [-9, 39, -32, 41, 52, -10, 28, -14],
                 [25, 17, 20, 34, 26, 25, 15, 10],
                 [13, 10, 17, 23, 17, 16, 0, 7],
                 [14, 25, 24, 15, 8, 25, 20, 15],
                 [19, 20, 11, 6, 7, 6, 20, 16],
                 [-7, 2, -15, -12, -14, -15, -10, -10]]

rook_scores = [[35,  29,  33,   4,  37,  33,  56,  50],
               [55,  29,  56,  67,  55,  62,  34,  60],
               [19,  35,  28,  33,  45,  27,  25,  15],
               [0,    5,  16,  13,  18,  -4,  -9,  -6],
               [-28, -35, -16, -21, -13, -29, -46, -30],
               [-42, -28, -42, -25, -25, -35, -26, -46],
               [-53, -38, -31, -26, -29, -43, -44, -53],
               [-30, -24, -18,   5,  -2, -18, -31, -32]]

queen_scores = [[  6,   1,  -8, -104,  69,  24,  88,  26],
                [ 14,  32,  60,  -10,  20,  76,  57,  24],
                [ -2,  43,  32,   60,  72,  63,  43,   2],
                [  1, -16,  22,   17,  25,  20, -13,  -6],
                [ -14, -15,  -2,   -5,  -1, -10, -20, -22],
                [ -30,  -6, -13,  -11, -16, -11, -16, -27],
                [ -36, -18,   0,  -19, -15, -15, -21, -38],
                [ -39, -30, -31,  -13, -31, -36, -34, -42]]


knight_scores = [[-66, -53, -75, -75, -10, -55, -58, -70],
                 [-3, -6, 100, -36, 4, 62, -4, -14],
                 [10, 67, 1, 74, 73, 27, 62, -2],
                 [24, 24, 45, 37, 33, 41, 25, 17],
                 [-1, 5, 31, 21, 22, 35, 2, 0],
                 [-18, 10, 13, 22, 18, 15, 11, -14],
                 [-23, -15, 2, 0, 2, 0, -23, -20],
                 [-66, -53, -75, -75, -10, -55, -58, -70]]

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
DEPTH = 4


def orderMoves(moves, game_state):
    # Order moves based on captures and high-value targets
    capture_moves = [move for move in moves if game_state.board[move.end_row][move.end_col] != "--"]
    quiet_moves = [move for move in moves if move not in capture_moves]
    
    #what will be benifit if this ? benifit is that we will capture the high value pieces first
    capture_moves.sort(key=lambda move: piece_score[game_state.board[move.end_row][move.end_col][1]], reverse=True)

    #what will be benifit if this ? benifit is that we will move the pieces to the best position
    quiet_moves.sort(key=lambda move: piece_position_scores.get(game_state.board[move.start_row][move.start_col], [[0]*8]*8)[move.end_row][move.end_col], reverse=True)
    
    ordered_moves = capture_moves + quiet_moves

    return ordered_moves


def findMoveNegaMaxAlphaBeta(game_state, valid_moves, depth, alpha, beta, turn_multiplier):
    global next_move
    if depth == 0 or game_state.stalemate or game_state.checkmate:
        return turn_multiplier * scoreBoard(game_state)

    max_score = -CHECKMATE
    # Move Ordering: Sorting moves based on some heuristic 
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
transposition_table = {} #used to not re-evaluate position that is already evaluated

def findMove(game_state, valid_moves, return_queue):
    global next_move, transposition_table
    next_move = None
    for depth in range(1, DEPTH + 1):
        findMoveNegaMaxAlphaBetaTT(game_state, valid_moves, depth, -CHECKMATE, CHECKMATE, 1 if game_state.white_to_move else -1)
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
    opening_moves = {"Italian Game": ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"],
                     "Sicilian Defense": ["e2e4", "c7c5"]}

    current_moves = [move.getChessNotation() for move in game_state.move_log]
    for opening in opening_moves.values():
        if current_moves[:len(opening)] == opening:
            return valid_moves[len(opening):] 

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






# knight_scores = [[0.0, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1, 0.0],
#                  [0.1, 0.3, 0.5, 0.5, 0.5, 0.5, 0.3, 0.1],
#                  [0.2, 0.5, 0.6, 0.65, 0.65, 0.6, 0.5, 0.2],
#                  [0.2, 0.55, 0.65, 0.7, 0.7, 0.65, 0.55, 0.2],
#                  [0.2, 0.5, 0.65, 0.7, 0.7, 0.65, 0.5, 0.2],
#                  [0.2, 0.55, 0.6, 0.65, 0.65, 0.6, 0.55, 0.2],
#                  [0.1, 0.3, 0.5, 0.55, 0.55, 0.5, 0.3, 0.1],
#                  [0.0, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1, 0.0]]

# bishop_scores = [[0.0, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0],
#                  [0.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.2],
#                  [0.2, 0.4, 0.5, 0.6, 0.6, 0.5, 0.4, 0.2],
#                  [0.2, 0.5, 0.5, 0.6, 0.6, 0.5, 0.5, 0.2],
#                  [0.2, 0.4, 0.6, 0.6, 0.6, 0.6, 0.4, 0.2],
#                  [0.2, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.2],
#                  [0.2, 0.5, 0.4, 0.4, 0.4, 0.4, 0.5, 0.2],
#                  [0.0, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0]]

# rook_scores = [[0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25],
#                [0.5, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.5],
#                [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
#                [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
#                [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
#                [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
#                [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
#                [0.25, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25, 0.25]]

# queen_scores = [[0.0, 0.2, 0.2, 0.3, 0.3, 0.2, 0.2, 0.0],
#                 [0.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.2],
#                 [0.2, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.2],
#                 [0.3, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.3],
#                 [0.4, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.3],
#                 [0.2, 0.5, 0.5, 0.5, 0.5, 0.5, 0.4, 0.2],
#                 [0.2, 0.4, 0.5, 0.4, 0.4, 0.4, 0.4, 0.2],
#                 [0.0, 0.2, 0.2, 0.3, 0.3, 0.2, 0.2, 0.0]]

# pawn_scores = [[0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
#                [0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7],
#                [0.3, 0.3, 0.4, 0.5, 0.5, 0.4, 0.3, 0.3],
#                [0.25, 0.25, 0.3, 0.45, 0.45, 0.3, 0.25, 0.25],
#                [0.2, 0.2, 0.2, 0.4, 0.4, 0.2, 0.2, 0.2],
#                [0.25, 0.15, 0.1, 0.2, 0.2, 0.1, 0.15, 0.25],
#                [0.25, 0.3, 0.3, 0.0, 0.0, 0.3, 0.3, 0.25],
#                [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]]


# test data of positional statistics 



