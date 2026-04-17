"""
Optional opening-book (Polyglot) and endgame-tablebase (Syzygy) integration.

This module is loaded lazily by ChessAI. If python-chess isn't installed, or
the book/tablebase files aren't present, the functions return None and the
engine falls back to its own search. No external files are required to run.

To enable:
  * Opening book: drop a Polyglot .bin file at  ./book.bin  (project root)
    or set env var  SEPENTIA_BOOK=/path/to/book.bin
    Free books: https://github.com/official-stockfish/books
  * Syzygy tablebases: extract .rtbw/.rtbz files to  ./syzygy/
    or set env var  SEPENTIA_SYZYGY=/path/to/dir
    Free TBs (3-5 piece): https://syzygy-tables.info/
"""
import os

try:
    import chess
    import chess.polyglot
    import chess.syzygy
    _HAVE_CHESS = True
except Exception:
    _HAVE_CHESS = False

_book_reader = None
_tb = None
_book_tried = False
_tb_tried = False


def _lazy_open_book():
    global _book_reader, _book_tried
    if _book_tried or not _HAVE_CHESS:
        return _book_reader
    _book_tried = True
    path = os.environ.get("SEPENTIA_BOOK", "book.bin")
    if os.path.isfile(path):
        try:
            _book_reader = chess.polyglot.open_reader(path)
        except Exception:
            _book_reader = None
    return _book_reader


def _lazy_open_tb():
    global _tb, _tb_tried
    if _tb_tried or not _HAVE_CHESS:
        return _tb
    _tb_tried = True
    path = os.environ.get("SEPENTIA_SYZYGY", "syzygy")
    if os.path.isdir(path):
        try:
            _tb = chess.syzygy.open_tablebase(path)
        except Exception:
            _tb = None
    return _tb


def _gs_to_fen(game_state):
    """Convert engine GameState to a FEN string."""
    rows = []
    for r in range(8):
        row_str = ""
        empty = 0
        for c in range(8):
            p = game_state.board[r][c]
            if p == "--":
                empty += 1
            else:
                if empty > 0:
                    row_str += str(empty)
                    empty = 0
                ch = p[1].upper() if p[0] == "w" else p[1].lower()
                row_str += ch
        if empty > 0:
            row_str += str(empty)
        rows.append(row_str)
    position = "/".join(rows)

    side = "w" if game_state.white_to_move else "b"

    cr = game_state.current_castling_rights
    castling = ""
    if cr.wks: castling += "K"
    if cr.wqs: castling += "Q"
    if cr.bks: castling += "k"
    if cr.bqs: castling += "q"
    if not castling:
        castling = "-"

    if game_state.enpassant_possible:
        er, ec = game_state.enpassant_possible
        ep = "abcdefgh"[ec] + str(8 - er)
    else:
        ep = "-"

    fullmove = max(1, len(game_state.move_log) // 2 + 1)
    return f"{position} {side} {castling} {ep} 0 {fullmove}"


def _pc_move_to_engine(pc_move, valid_moves):
    """Match a python-chess Move to one of our engine's legal Move objects."""
    start_row = 7 - chess.square_rank(pc_move.from_square)
    start_col = chess.square_file(pc_move.from_square)
    end_row = 7 - chess.square_rank(pc_move.to_square)
    end_col = chess.square_file(pc_move.to_square)
    for m in valid_moves:
        if (m.start_row == start_row and m.start_col == start_col
                and m.end_row == end_row and m.end_col == end_col):
            return m
    return None


def book_move(game_state, valid_moves):
    """Return a book move for the current position, or None."""
    reader = _lazy_open_book()
    if reader is None:
        return None
    try:
        board = chess.Board(_gs_to_fen(game_state))
    except Exception:
        return None
    try:
        # weighted_choice picks proportional to book weights
        entry = reader.weighted_choice(board)
    except (IndexError, KeyError, Exception):
        return None
    return _pc_move_to_engine(entry.move, valid_moves)


def _piece_count(game_state):
    n = 0
    for row in game_state.board:
        for p in row:
            if p != "--":
                n += 1
    return n


def tablebase_move(game_state, valid_moves):
    """Return the best move per Syzygy, or None if out of TB range."""
    tb = _lazy_open_tb()
    if tb is None:
        return None
    if _piece_count(game_state) > 6:
        return None

    try:
        board = chess.Board(_gs_to_fen(game_state))
    except Exception:
        return None

    # Try probing root for DTZ-optimal move.
    best = None
    best_key = None  # (our_wdl, tiebreak) — higher is better
    for m in valid_moves:
        pc_m = chess.Move(
            from_square=chess.square(m.start_col, 7 - m.start_row),
            to_square=chess.square(m.end_col, 7 - m.end_row),
            promotion=chess.QUEEN if m.is_pawn_promotion else None,
        )
        if pc_m not in board.legal_moves:
            continue
        board.push(pc_m)
        try:
            # wdl from opponent's perspective (they're to move now).
            wdl = tb.probe_wdl(board)
            dtz = tb.probe_dtz(board)
        except Exception:
            board.pop()
            continue
        board.pop()
        our_wdl = -wdl
        # Tiebreak: when winning, prefer SHORTER path (smaller |dtz|);
        # when losing, prefer LONGER path (larger |dtz|); when drawing,
        # prefer keeping it drawn (any).
        if our_wdl > 0:
            tiebreak = -abs(dtz)
        elif our_wdl < 0:
            tiebreak = abs(dtz)
        else:
            tiebreak = 0
        key = (our_wdl, tiebreak)
        if best_key is None or key > best_key:
            best_key = key
            best = m
    return best


def close():
    """Release file handles (called on engine shutdown)."""
    global _book_reader, _tb
    if _book_reader is not None:
        try:
            _book_reader.close()
        except Exception:
            pass
        _book_reader = None
    if _tb is not None:
        try:
            _tb.close()
        except Exception:
            pass
        _tb = None
