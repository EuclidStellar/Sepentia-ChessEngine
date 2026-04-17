"""
Texel-style evaluation tuner.

Fits the engine's static evaluation to a labeled dataset of positions using
logistic regression: each position gets a win probability via sigmoid(eval * K),
and we minimize squared error against the label (1.0=win, 0.5=draw, 0.0=loss).

Usage:
    python3 texel_tuner.py <dataset.epd>

Dataset format: one position per line, space-separated FEN followed by a
label token. Common conventions:
    ... w KQkq - 0 1 c9 "1-0";     (Zurichess / STS style)
    ... w KQkq - 0 1 1.0           (simple-label style)
Both are parsed. Labels: 1-0 / 1.0 -> 1.0 ; 1/2-1/2 / 0.5 -> 0.5 ;
                         0-1 / 0.0 -> 0.0.

Free datasets:
    https://github.com/zamar/zurichess/blob/master/data/quiet-labeled.epd
    https://bitbucket.org/zurichess/tuner/downloads/quiet-labeled.v7.epd.zip

Outputs:
    1. Best K (eval -> win-probability scaling, usually ~0.003-0.004).
    2. Total loss before tuning.
    3. Optionally: gradient-descent step on selected parameters.

This is a scaffold: full tuning of all eval constants across tens of
thousands of positions takes hours and benefits from C-accelerated eval.
For a Python engine it is most useful as a benchmark: you see the loss
go down after each change.
"""
import math
import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "src")

import chess
import chessengine
import ChessAI


def sigmoid(x):
    if x > 50:
        return 1.0
    if x < -50:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def fen_to_gamestate(fen):
    """Convert a FEN string into an engine GameState (minimal fields set)."""
    gs = chessengine.GameState()
    # Clear board
    for r in range(8):
        for c in range(8):
            gs.board[r][c] = "--"

    parts = fen.split()
    position, side, castling, ep = parts[0], parts[1], parts[2], parts[3]

    # Piece placement
    for r, row_str in enumerate(position.split("/")):
        c = 0
        for ch in row_str:
            if ch.isdigit():
                c += int(ch)
            else:
                color = "w" if ch.isupper() else "b"
                typ = ch.upper() if ch.lower() != "p" else "p"
                gs.board[r][c] = color + typ
                if typ == "K":
                    if color == "w":
                        gs.white_king_location = (r, c)
                    else:
                        gs.black_king_location = (r, c)
                c += 1

    gs.white_to_move = (side == "w")
    gs.current_castling_rights = chessengine.CastleRights(
        wks="K" in castling, bks="k" in castling,
        wqs="Q" in castling, bqs="q" in castling,
    )
    gs.castle_rights_log = [gs.current_castling_rights]
    if ep != "-":
        file = "abcdefgh".index(ep[0])
        rank = 8 - int(ep[1])
        gs.enpassant_possible = (rank, file)
        gs.enpassant_possible_log = [gs.enpassant_possible]
    else:
        gs.enpassant_possible_log = [()]

    return gs


def parse_label(line):
    """Extract the label from a dataset line; returns (fen, label) or None."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # Try to find standard result tokens
    for token, value in (('"1-0"', 1.0), ('"0-1"', 0.0), ('"1/2-1/2"', 0.5),
                        (" 1-0", 1.0), (" 0-1", 0.0), (" 1/2-1/2", 0.5)):
        idx = line.rfind(token)
        if idx != -1:
            fen = line[:idx].rstrip().rstrip("c9").rstrip()
            # Strip trailing 'c9' EPD opcode marker if present
            if fen.endswith(" c9"):
                fen = fen[:-3].rstrip()
            return fen, value
    # Fallback: last token is a float
    parts = line.rsplit(None, 1)
    if len(parts) == 2:
        try:
            value = float(parts[1])
            if 0.0 <= value <= 1.0:
                return parts[0], value
        except ValueError:
            pass
    return None


def load_dataset(path, limit=None):
    data = []
    with open(path) as f:
        for line in f:
            parsed = parse_label(line)
            if parsed is not None:
                data.append(parsed)
                if limit and len(data) >= limit:
                    break
    return data


def total_loss(data, K):
    """Mean squared error of sigmoid(score*K) vs label across dataset."""
    total = 0.0
    n = 0
    for fen, label in data:
        try:
            gs = fen_to_gamestate(fen)
        except Exception:
            continue
        # ScoreBoard returns cp from white's perspective.
        gs.checkmate = False
        gs.stalemate = False
        score = ChessAI.scoreBoard(gs)
        err = sigmoid(score * K) - label
        total += err * err
        n += 1
    return total / max(n, 1), n


def find_best_K(data, K_lo=0.0005, K_hi=0.02, steps=20):
    """Golden-section-ish sweep to find the K that minimizes loss."""
    best_K, best_loss = None, float("inf")
    for i in range(steps):
        K = K_lo + (K_hi - K_lo) * i / (steps - 1)
        loss, n = total_loss(data, K)
        if loss < best_loss:
            best_K, best_loss = K, loss
    return best_K, best_loss


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Missing dataset argument.")
        sys.exit(1)
    path = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None

    print(f"Loading dataset: {path}")
    t0 = time.time()
    data = load_dataset(path, limit=limit)
    print(f"  loaded {len(data)} positions in {time.time()-t0:.1f}s")
    if not data:
        print("  (empty — check file format)")
        return

    print("Sweeping K (eval-to-win-probability scaling)...")
    t0 = time.time()
    K, loss = find_best_K(data)
    print(f"  best K = {K:.5f}   loss = {loss:.5f}   ({time.time()-t0:.1f}s)")

    print()
    print("Baseline loss above is the current eval's fit.")
    print("To tune: perturb eval constants in ChessAI.py, re-run, and keep")
    print("changes that reduce loss. For automated tuning, wrap this in")
    print("scipy.optimize.minimize over the parameter vector.")


if __name__ == "__main__":
    main()
