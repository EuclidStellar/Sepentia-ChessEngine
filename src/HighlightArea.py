
import pygame as p

import ChessMain as cm

def highlightSquares(screen, game_state, valid_moves, square_selected):
    """
    Highlight square selected and moves for piece selected.
    """
    if (len(game_state.move_log)) > 0:
        last_move = game_state.move_log[-1]
        s = p.Surface((cm.SQUARE_SIZE, cm.SQUARE_SIZE))
        s.set_alpha(100)
        s.fill(p.Color('green'))
        screen.blit(s, (last_move.end_col * cm.SQUARE_SIZE, last_move.end_row * cm.SQUARE_SIZE))
    if square_selected != ():
        row, col = square_selected
        if game_state.board[row][col][0] == (
                'w' if game_state.white_to_move else 'b'):  # square_selected is a piece that can be moved
            # highlight selected square
            s = p.Surface((cm.SQUARE_SIZE, cm.SQUARE_SIZE))
            s.set_alpha(100)  # transparency value 0 -> transparent, 255 -> opaque
            s.fill(p.Color('blue'))
            screen.blit(s, (col * cm.SQUARE_SIZE, row * cm.SQUARE_SIZE))
            # highlight moves from that square
            s.fill(p.Color('yellow'))
            for move in valid_moves:
                if move.start_row == row and move.start_col == col:
                    screen.blit(s, (move.end_col * cm.SQUARE_SIZE, move.end_row * cm.SQUARE_SIZE))

