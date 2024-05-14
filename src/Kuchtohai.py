# import pygame as p 
# import ChessMain as cm
# import HighlightArea

# def drawGameState(screen, game_state, valid_moves, square_selected):
#     """
#     Responsible for all the graphics within current game state.
#     """
#     drawBoard(screen)  # draw squares on the board
#     HighlightArea.highlightSquares(screen, game_state, valid_moves, square_selected)
#     drawPieces(screen, game_state.board)  # draw pieces on top of those squares


# def drawBoard(screen):
#     """
#     Draw the squares on the board.
#     The top left square is always light.
#     """
#     global colors
#     colors = [p.Color("white"), p.Color("dark green")]
#     for row in range(cm.DIMENSION):
#         for column in range(cm.DIMENSION):
#             color = colors[((row + column) % 2)]
#             p.draw.rect(screen, color, p.Rect(column * cm.SQUARE_SIZE, row * cm.SQUARE_SIZE, cm.SQUARE_SIZE, cm.SQUARE_SIZE))


# def drawPieces(screen, board):
#     """
#     Draw the pieces on the board using the current game_state.board
#     """
#     for row in range(cm.DIMENSION):
#         for column in range(cm.DIMENSION):
#             piece = board[row][column]
#             if piece != "--":
#                 screen.blit(cm.IMAGES[piece], p.Rect(column * cm.SQUARE_SIZE, row * cm.SQUARE_SIZE, cm.SQUARE_SIZE, cm.SQUARE_SIZE))


# def animateMove(move, screen, board, clock):
#     """
#     Animating a move
#     """
#     global colors
#     d_row = move.end_row - move.start_row
#     d_col = move.end_col - move.start_col
#     frames_per_square = 10  # frames to move one square
#     frame_count = (abs(d_row) + abs(d_col)) * frames_per_square
#     for frame in range(frame_count + 1):
#         row, col = (move.start_row + d_row * frame / frame_count, move.start_col + d_col * frame / frame_count)
#         drawBoard(screen)
#         drawPieces(screen, board)
#         # erase the piece moved from its ending square
#         color = colors[(move.end_row + move.end_col) % 2]
#         end_square = p.Rect(move.end_col * cm.SQUARE_SIZE, move.end_row * cm.SQUARE_SIZE, cm.SQUARE_SIZE, cm.SQUARE_SIZE)
#         p.draw.rect(screen, color, end_square)
#         # draw captured piece onto rectangle
#         if move.piece_captured != '--':
#             if move.is_enpassant_move:
#                 enpassant_row = move.end_row + 1 if move.piece_captured[0] == 'b' else move.end_row - 1
#                 end_square = p.Rect(move.end_col * cm.SQUARE_SIZE, enpassant_row * cm.SQUARE_SIZE, cm.SQUARE_SIZE, cm.SQUARE_SIZE)
#             screen.blit(cm.IMAGES[move.piece_captured], end_square)
#         # draw moving piece
#         screen.blit(cm.IMAGES[move.piece_moved], p.Rect(col * cm.SQUARE_SIZE, row * cm.SQUARE_SIZE, cm.SQUARE_SIZE, cm.SQUARE_SIZE))
#         p.display.flip()
#         clock.tick(60)