"""
AI move search and evaluation.

Search: iterative deepening negamax with alpha-beta, aspiration windows,
quiescence (with delta pruning + SEE), transposition table, null-move
pruning, late move reductions, reverse + forward futility pruning,
MVV-LVA + SEE capture ordering, killer moves, and history heuristic.

Evaluation: tapered (middlegame <-> endgame) piece-square tables including
king tables, pawn structure (passed/doubled/isolated), bishop-pair bonus,
and king safety (pawn shield + open-file penalty, mg-weighted).

Optional integrations (enabled if present): Polyglot opening book and
Syzygy endgame tablebases via python-chess.
"""
import random
import time

piece_score = {"K": 20000, "Q": 929, "R": 512, "B": 320, "N": 280, "p": 100}

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

king_mg_scores = [[-65,  23,  16, -15, -56, -34,   2,  13],
                  [ 29,  -1, -20,  -7,  -8,  -4, -38, -29],
                  [ -9,  24,   2, -16, -20,   6,  22, -22],
                  [-17, -20, -12, -27, -30, -25, -14, -36],
                  [-49,  -1, -27, -39, -46, -44, -33, -51],
                  [-14, -14, -22, -46, -44, -30, -15, -27],
                  [  1,   7,  -8, -64, -43, -16,   9,   8],
                  [-15,  36,  12, -54,   8, -28,  24,  14]]

king_eg_scores = [[-74, -35, -18, -18, -11,  15,   4, -17],
                  [-12,  17,  14,  17,  17,  38,  23,  11],
                  [ 10,  17,  23,  15,  20,  45,  44,  13],
                  [ -8,  22,  24,  27,  26,  33,  26,   3],
                  [-18,  -4,  21,  24,  27,  23,   9, -11],
                  [-19,  -3,  11,  21,  23,  16,   7,  -9],
                  [-27, -11,   4,  13,  14,   4,  -5, -17],
                  [-53, -34, -21, -11, -28, -14, -24, -43]]

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

king_mg_black = king_mg_scores[::-1]
king_eg_black = king_eg_scores[::-1]

CHECKMATE = 1_000_000
STALEMATE = 0
MAX_DEPTH = 64
TIME_LIMIT = 5.0
QUIESCENCE_MAX_DEPTH = 6
VERBOSE = True  # print one-line per-move search summary to stdout

TT_EXACT, TT_LOWER, TT_UPPER = 0, 1, 2
MAX_TT_SIZE = 500_000  # cap to keep persistent TT from unbounded growth

PHASE_WEIGHT = {"N": 1, "B": 1, "R": 2, "Q": 4}
MAX_PHASE = 24

PASSED_PAWN_MG = [0,  10,  15,  25,  50,  90, 160, 0]
PASSED_PAWN_EG = [0,  20,  35,  55, 100, 170, 280, 0]
DOUBLED_PAWN_PENALTY = 12
ISOLATED_PAWN_PENALTY = 15
BISHOP_PAIR_BONUS = 35

NULL_MOVE_R_SHALLOW = 2
NULL_MOVE_R_DEEP = 3

ASPIRATION_DELTA = 50  # initial aspiration-window half-width

# Per-search + per-call globals. TT persists across moves; killer/history
# reset on each call to avoid stale-ply drift.
transposition_table = {}
killer_moves = {}
history_table = {}
search_start = 0.0
time_up = False
cancel_flag = False
nodes = 0
next_move = None

# Optional: opening book + endgame tablebase (lazy-loaded once).
try:
    import ChessBook as _book_module
except Exception:
    _book_module = None


def request_cancel():
    """Signal the currently-running search to stop. Used by the UI for
    undo/reset. Safe to call from any thread (GIL-protected flag write)."""
    global cancel_flag
    cancel_flag = True


def _should_stop():
    return time_up or cancel_flag


def _time_expired():
    return time.time() - search_start > TIME_LIMIT


# ----- SEE (Static Exchange Evaluation) helpers -----

_ORTHO_DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))
_DIAG_DIRS = ((-1, -1), (-1, 1), (1, -1), (1, 1))
_KNIGHT_OFFSETS = ((-2, -1), (-2, 1), (-1, 2), (1, 2),
                   (2, -1), (2, 1), (-1, -2), (1, -2))


def _attackers_to(board, tr, tc, color):
    """All pieces of `color` that attack square (tr, tc), as (r, c, piece)."""
    out = []
    # Pawn: attacks diagonally forward. A white pawn on (r, c) attacks (r-1, c±1);
    # so a square (tr, tc) is attacked by a white pawn at (tr+1, tc±1).
    if color == "w":
        for dc in (-1, 1):
            r, c = tr + 1, tc + dc
            if 0 <= r < 8 and 0 <= c < 8 and board[r][c] == "wp":
                out.append((r, c, "wp"))
    else:
        for dc in (-1, 1):
            r, c = tr - 1, tc + dc
            if 0 <= r < 8 and 0 <= c < 8 and board[r][c] == "bp":
                out.append((r, c, "bp"))
    # Knight
    for dr, dc in _KNIGHT_OFFSETS:
        r, c = tr + dr, tc + dc
        if 0 <= r < 8 and 0 <= c < 8:
            p = board[r][c]
            if p != "--" and p[0] == color and p[1] == "N":
                out.append((r, c, p))
    # King
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r, c = tr + dr, tc + dc
            if 0 <= r < 8 and 0 <= c < 8:
                p = board[r][c]
                if p != "--" and p[0] == color and p[1] == "K":
                    out.append((r, c, p))
    # Rook / Queen (orthogonal rays)
    for dr, dc in _ORTHO_DIRS:
        r, c = tr + dr, tc + dc
        while 0 <= r < 8 and 0 <= c < 8:
            p = board[r][c]
            if p != "--":
                if p[0] == color and p[1] in ("R", "Q"):
                    out.append((r, c, p))
                break
            r += dr
            c += dc
    # Bishop / Queen (diagonal rays)
    for dr, dc in _DIAG_DIRS:
        r, c = tr + dr, tc + dc
        while 0 <= r < 8 and 0 <= c < 8:
            p = board[r][c]
            if p != "--":
                if p[0] == color and p[1] in ("B", "Q"):
                    out.append((r, c, p))
                break
            r += dr
            c += dc
    return out


def _see(board, move):
    """Static Exchange Evaluation: estimated material swing of a capture.

    Returns a centipawn score. Positive means our side comes out ahead.
    Simplified: ignores x-ray attackers revealed when a slider captures,
    which slightly under-counts exchanges but is fast and robust.
    """
    victim = move.piece_captured
    if victim == "--":
        return 0
    tr, tc = move.end_row, move.end_col
    sim = [row[:] for row in board]
    sim[move.start_row][move.start_col] = "--"
    sim[tr][tc] = move.piece_moved

    gains = [piece_score.get(victim[1], 0)]
    on_square = move.piece_moved
    next_side = "b" if move.piece_moved[0] == "w" else "w"

    while True:
        attackers = _attackers_to(sim, tr, tc, next_side)
        if not attackers:
            break
        attackers.sort(key=lambda a: piece_score.get(a[2][1], 0))
        ar, ac, ap = attackers[0]
        gains.append(piece_score.get(on_square[1], 0) - gains[-1])
        sim[ar][ac] = "--"
        sim[tr][tc] = ap
        on_square = ap
        next_side = "b" if next_side == "w" else "w"

    for i in range(len(gains) - 2, -1, -1):
        gains[i] = -max(-gains[i], gains[i + 1])
    return gains[0]


# ----- Move ordering -----

def _mvv_lva(move):
    victim = move.piece_captured
    victim_val = piece_score.get(victim[1], 100) if victim != "--" else 100
    attacker_val = piece_score.get(move.piece_moved[1], 100)
    return 10 * victim_val - attacker_val


def _score_move(move, ply, tt_move):
    if tt_move is not None and move == tt_move:
        return 10_000_000
    if move.is_capture:
        return 1_000_000 + _mvv_lva(move)
    if move.is_pawn_promotion:
        return 900_000
    killers = killer_moves.get(ply)
    if killers:
        if killers[0] is not None and move == killers[0]:
            return 800_000
        if killers[1] is not None and move == killers[1]:
            return 700_000
    return history_table.get((move.piece_moved, move.end_row, move.end_col), 0)


def _order_moves(moves, ply, tt_move):
    moves.sort(key=lambda m: _score_move(m, ply, tt_move), reverse=True)


# ----- Null move -----

def _null_move_forward(game_state):
    saved_ep = game_state.enpassant_possible
    game_state.white_to_move = not game_state.white_to_move
    game_state.enpassant_possible = ()
    game_state.enpassant_possible_log.append(())
    return saved_ep


def _null_move_backward(game_state, saved_ep):
    game_state.white_to_move = not game_state.white_to_move
    game_state.enpassant_possible_log.pop()
    game_state.enpassant_possible = saved_ep


def _has_non_pawn_material(game_state):
    side = "w" if game_state.white_to_move else "b"
    for row in game_state.board:
        for piece in row:
            if piece != "--" and piece[0] == side and piece[1] not in ("K", "p"):
                return True
    return False


# ----- Quiescence -----

def _quiescence(game_state, alpha, beta, turn_multiplier, qdepth):
    global nodes, time_up
    nodes += 1
    if (nodes & 2047) == 0 and _time_expired():
        time_up = True
    if _should_stop():
        return 0

    moves = game_state.getValidMoves()
    if game_state.checkmate:
        return -CHECKMATE + 1000 + qdepth
    if game_state.stalemate:
        return STALEMATE

    in_check = game_state.in_check
    stand_pat = turn_multiplier * scoreBoard(game_state)

    if not in_check:
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

    if qdepth >= QUIESCENCE_MAX_DEPTH:
        return stand_pat if not in_check else alpha

    if in_check:
        # In check: must consider all legal moves (evasion).
        search_moves = moves
    else:
        # Only captures / promotions, and apply delta + SEE pruning.
        search_moves = []
        for m in moves:
            if not (m.is_capture or m.is_pawn_promotion):
                continue
            # Delta pruning: if even capturing this piece + margin can't raise
            # alpha, skip. Promotions bypass delta pruning (huge material swing).
            if m.is_capture and not m.is_pawn_promotion:
                captured_val = (piece_score.get(m.piece_captured[1], 0)
                                if m.piece_captured != "--" else 0)
                if stand_pat + captured_val + 200 < alpha:
                    continue
                # SEE pruning: skip captures that lose material.
                if _see(game_state.board, m) < 0:
                    continue
            search_moves.append(m)

    search_moves.sort(key=lambda m: _score_move(m, 0, None), reverse=True)

    for move in search_moves:
        game_state.makeMove(move)
        score = -_quiescence(game_state, -beta, -alpha, -turn_multiplier, qdepth + 1)
        game_state.undoMove()
        if _should_stop():
            return 0
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha


# ----- Negamax with TT, null move, LMR, futility -----

def _negamax(game_state, depth, alpha, beta, turn_multiplier, ply, can_null):
    global nodes, time_up, next_move
    nodes += 1
    if (nodes & 2047) == 0 and _time_expired():
        time_up = True
    if _should_stop():
        return 0

    is_root = ply == 0
    alpha_orig = alpha

    # Repetition: treat as draw inside the search so the engine avoids
    # shuffling into threefold when it's winning. At root we don't return
    # immediately (we're choosing a move), only in deeper nodes.
    if not is_root and game_state.isRepetition():
        return 0

    hash_key = game_state.getHashKey()
    tt_entry = transposition_table.get(hash_key)
    tt_move = None
    if tt_entry is not None:
        tt_depth, tt_score, tt_flag, tt_move = tt_entry
        if not is_root and tt_depth >= depth:
            if tt_flag == TT_EXACT:
                return tt_score
            if tt_flag == TT_LOWER and tt_score >= beta:
                return tt_score
            if tt_flag == TT_UPPER and tt_score <= alpha:
                return tt_score

    if depth <= 0:
        return _quiescence(game_state, alpha, beta, turn_multiplier, 0)

    valid_moves = game_state.getValidMoves()
    if game_state.checkmate:
        return -CHECKMATE + ply
    if game_state.stalemate:
        return STALEMATE

    in_check_here = game_state.in_check

    # Static eval for pruning decisions (don't compute if we can't use it).
    static_eval = None
    if not in_check_here and not is_root:
        static_eval = turn_multiplier * scoreBoard(game_state)

        # Reverse futility pruning (static null move): if we're already so
        # far ahead that we beat beta by a wide margin, prune.
        if depth <= 3 and abs(beta) < CHECKMATE - 1000:
            rf_margin = 120 * depth
            if static_eval - rf_margin >= beta:
                return static_eval - rf_margin

    # Null-move pruning.
    if (can_null and not is_root and not in_check_here and depth >= 3
            and abs(beta) < CHECKMATE - 1000
            and _has_non_pawn_material(game_state)):
        R = NULL_MOVE_R_DEEP if depth >= 6 else NULL_MOVE_R_SHALLOW
        saved_ep = _null_move_forward(game_state)
        null_score = -_negamax(game_state, depth - 1 - R, -beta, -beta + 1,
                               -turn_multiplier, ply + 1, False)
        _null_move_backward(game_state, saved_ep)
        if _should_stop():
            return 0
        if null_score >= beta:
            return beta

    _order_moves(valid_moves, ply, tt_move)

    best_score = -CHECKMATE * 2
    best_move = None

    for move_num, move in enumerate(valid_moves):
        # Forward futility pruning: at low depth, quiet moves that can't
        # raise alpha are skipped. Never prune the first move.
        if (static_eval is not None and depth <= 2 and move_num > 0
                and not move.is_capture and not move.is_pawn_promotion
                and abs(alpha) < CHECKMATE - 1000):
            if static_eval + 150 * depth <= alpha:
                continue

        game_state.makeMove(move)

        use_lmr = (move_num >= 3 and depth >= 3
                   and not in_check_here
                   and not move.is_capture
                   and not move.is_pawn_promotion)

        if use_lmr:
            reduction = 1 if move_num < 6 else 2
            reduced = max(1, depth - 1 - reduction)
            score = -_negamax(game_state, reduced, -alpha - 1, -alpha,
                              -turn_multiplier, ply + 1, True)
            if not _should_stop() and score > alpha:
                score = -_negamax(game_state, depth - 1, -beta, -alpha,
                                  -turn_multiplier, ply + 1, True)
        else:
            score = -_negamax(game_state, depth - 1, -beta, -alpha,
                              -turn_multiplier, ply + 1, True)

        game_state.undoMove()

        if _should_stop():
            return 0

        if score > best_score:
            best_score = score
            best_move = move
            if is_root:
                next_move = move

        if score > alpha:
            alpha = score

        if alpha >= beta:
            if not move.is_capture and not move.is_pawn_promotion:
                prev = killer_moves.get(ply)
                if prev is None or prev[0] != move:
                    killer_moves[ply] = (move, prev[0] if prev else None)
                key = (move.piece_moved, move.end_row, move.end_col)
                history_table[key] = history_table.get(key, 0) + depth * depth
            break

    if not _should_stop():
        if best_score <= alpha_orig:
            flag = TT_UPPER
        elif best_score >= beta:
            flag = TT_LOWER
        else:
            flag = TT_EXACT
        if len(transposition_table) >= MAX_TT_SIZE:
            # Evict oldest half (Python 3.7+ dict preserves insertion order).
            for k in list(transposition_table.keys())[:MAX_TT_SIZE // 2]:
                del transposition_table[k]
        transposition_table[hash_key] = (depth, best_score, flag, best_move)

    return best_score


# ----- Entry point -----

def findBestMove(game_state, valid_moves, return_queue):
    """Iterative-deepening search with aspiration windows.

    Called by chessmain.py in a worker thread (see chessmain.py). Puts the
    chosen move on the return_queue. Honors cancel_flag for UI undo/reset.
    """
    global next_move, killer_moves, history_table
    global search_start, time_up, cancel_flag, nodes

    # Killer / history reset per move (ply-indexed, stale across moves).
    # TT persists across calls for reuse.
    killer_moves = {}
    history_table = {}
    search_start = time.time()
    time_up = False
    cancel_flag = False
    nodes = 0
    next_move = None

    # Opening book / tablebase shortcuts.
    if _book_module is not None:
        book_move = _book_module.book_move(game_state, valid_moves)
        if book_move is not None:
            return_queue.put(book_move)
            return
        tb_move = _book_module.tablebase_move(game_state, valid_moves)
        if tb_move is not None:
            return_queue.put(tb_move)
            return

    turn_multiplier = 1 if game_state.white_to_move else -1
    best_move_overall = None
    last_completed_depth = 0
    last_score = 0
    prev_score = None

    for depth in range(1, MAX_DEPTH + 1):
        next_move = None

        # Aspiration windows. Use wide window until depth 3 then narrow.
        if prev_score is None or depth < 3:
            alpha, beta = -CHECKMATE * 2, CHECKMATE * 2
        else:
            alpha = prev_score - ASPIRATION_DELTA
            beta = prev_score + ASPIRATION_DELTA

        delta = ASPIRATION_DELTA
        while True:
            score = _negamax(game_state, depth, alpha, beta,
                             turn_multiplier, 0, True)
            if _should_stop():
                break
            if score <= alpha:
                alpha = max(-CHECKMATE * 2, alpha - delta)
                delta *= 2
                if delta > 1000:
                    alpha, beta = -CHECKMATE * 2, CHECKMATE * 2
            elif score >= beta:
                beta = min(CHECKMATE * 2, beta + delta)
                delta *= 2
                if delta > 1000:
                    alpha, beta = -CHECKMATE * 2, CHECKMATE * 2
            else:
                break

        if _should_stop():
            break
        if next_move is not None:
            best_move_overall = next_move
            last_completed_depth = depth
            last_score = score
        prev_score = score
        if score > CHECKMATE - 1000 or score < -CHECKMATE + 1000:
            break
        if time.time() - search_start > TIME_LIMIT * 0.5:
            break

    if best_move_overall is None:
        best_move_overall = random.choice(valid_moves)

    if VERBOSE:
        elapsed = time.time() - search_start
        print(f"[AI] depth={last_completed_depth}  score={last_score/100:+.2f}  "
              f"nodes={nodes}  time={elapsed:.2f}s  move={best_move_overall}  "
              f"tt={len(transposition_table)}", flush=True)

    return_queue.put(best_move_overall)


# ----- Evaluation -----

def scoreBoard(game_state):
    """Score the board (centipawns). Positive = good for white."""
    if game_state.checkmate:
        return -CHECKMATE if game_state.white_to_move else CHECKMATE
    if game_state.stalemate:
        return STALEMATE

    board = game_state.board
    score = 0
    phase = 0
    w_bishops = 0
    b_bishops = 0
    w_king = None
    b_king = None
    w_pawn_files = [0] * 8
    b_pawn_files = [0] * 8
    w_pawn_rows = [[] for _ in range(8)]
    b_pawn_rows = [[] for _ in range(8)]

    for row in range(8):
        brow = board[row]
        for col in range(8):
            piece = brow[col]
            if piece == "--":
                continue
            color = piece[0]
            typ = piece[1]

            if typ == "K":
                if color == "w":
                    w_king = (row, col)
                else:
                    b_king = (row, col)
                continue

            base = piece_score[typ]
            pst = piece_position_scores[piece][row][col]
            if color == "w":
                score += base + pst
            else:
                score -= base + pst

            pw = PHASE_WEIGHT.get(typ)
            if pw is not None:
                phase += pw

            if typ == "B":
                if color == "w":
                    w_bishops += 1
                else:
                    b_bishops += 1
            elif typ == "p":
                if color == "w":
                    w_pawn_files[col] += 1
                    w_pawn_rows[col].append(row)
                else:
                    b_pawn_files[col] += 1
                    b_pawn_rows[col].append(row)

    if phase > MAX_PHASE:
        phase = MAX_PHASE
    eg_phase = MAX_PHASE - phase

    # Tapered king piece-square eval.
    if w_king is not None:
        r, c = w_king
        mg = king_mg_scores[r][c]
        eg = king_eg_scores[r][c]
        score += (mg * phase + eg * eg_phase) // MAX_PHASE
    if b_king is not None:
        r, c = b_king
        mg = king_mg_black[r][c]
        eg = king_eg_black[r][c]
        score -= (mg * phase + eg * eg_phase) // MAX_PHASE

    # King safety (mg-scaled).
    if phase > 0:
        if w_king is not None:
            score += (_king_safety(board, w_king[0], w_king[1], "w") * phase) // MAX_PHASE
        if b_king is not None:
            score -= (_king_safety(board, b_king[0], b_king[1], "b") * phase) // MAX_PHASE

    if w_bishops >= 2:
        score += BISHOP_PAIR_BONUS
    if b_bishops >= 2:
        score -= BISHOP_PAIR_BONUS

    for col in range(8):
        wf = w_pawn_files[col]
        if wf > 1:
            score -= DOUBLED_PAWN_PENALTY * (wf - 1)
        bf = b_pawn_files[col]
        if bf > 1:
            score += DOUBLED_PAWN_PENALTY * (bf - 1)

    for col in range(8):
        left_has_w = col > 0 and w_pawn_files[col - 1] > 0
        right_has_w = col < 7 and w_pawn_files[col + 1] > 0
        if w_pawn_files[col] > 0 and not (left_has_w or right_has_w):
            score -= ISOLATED_PAWN_PENALTY * w_pawn_files[col]
        left_has_b = col > 0 and b_pawn_files[col - 1] > 0
        right_has_b = col < 7 and b_pawn_files[col + 1] > 0
        if b_pawn_files[col] > 0 and not (left_has_b or right_has_b):
            score += ISOLATED_PAWN_PENALTY * b_pawn_files[col]

    for col in range(8):
        for row in w_pawn_rows[col]:
            blocked = False
            for c in (col - 1, col, col + 1):
                if 0 <= c < 8:
                    for br in b_pawn_rows[c]:
                        if br < row:
                            blocked = True
                            break
                if blocked:
                    break
            if not blocked:
                advance = 6 - row
                if 0 <= advance <= 7:
                    mg = PASSED_PAWN_MG[advance]
                    eg = PASSED_PAWN_EG[advance]
                    score += (mg * phase + eg * eg_phase) // MAX_PHASE
        for row in b_pawn_rows[col]:
            blocked = False
            for c in (col - 1, col, col + 1):
                if 0 <= c < 8:
                    for wr in w_pawn_rows[c]:
                        if wr > row:
                            blocked = True
                            break
                if blocked:
                    break
            if not blocked:
                advance = row - 1
                if 0 <= advance <= 7:
                    mg = PASSED_PAWN_MG[advance]
                    eg = PASSED_PAWN_EG[advance]
                    score -= (mg * phase + eg * eg_phase) // MAX_PHASE

    return score


def _king_safety(board, kr, kc, color):
    """Raw pawn-shield bonus for the king (mg-weighted by caller).

    Adds for friendly pawns on the 3 files around the king in the 2 ranks
    toward the center; subtracts for open files near the king. Active-king
    endgame bonus is already handled by king_eg_scores (tapered eval).
    """
    score = 0
    if color == "w":
        forward = -1
        pawn = "wp"
    else:
        forward = 1
        pawn = "bp"

    for dc in (-1, 0, 1):
        c = kc + dc
        if not (0 <= c < 8):
            continue
        r1 = kr + forward
        r2 = kr + 2 * forward
        shielded = False
        if 0 <= r1 < 8 and board[r1][c] == pawn:
            score += 12
            shielded = True
        elif 0 <= r2 < 8 and board[r2][c] == pawn:
            score += 6
            shielded = True
        if not shielded:
            # No shield pawn on this file near the king: open file.
            score -= 10
    return score


def findRandomMove(valid_moves):
    return random.choice(valid_moves)
