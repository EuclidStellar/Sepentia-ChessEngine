#main driver file for chess game

import pygame as p
# from chessengine import ChessEngine
import ChessEngine
import sys
WIDTH = HEIGHT = 512
DIMENSION = 8
SQUARE_SIZE = HEIGHT // DIMENSION
MAX_FPS = 15
    
IMAGES = {}
def loadImages():
    '''
    Initialize a global directory of images.
    This will be called exactly once in the main.
    '''
    pieces = ['wp', 'wR', 'wN', 'wB' ,'wK', 'wQ', 'bp', 'bR', 'bN', 'bB', 'bK', 'bQ']
    for piece in pieces:
        IMAGES[piece] = p.transform.scale(p.image.load("images/" + piece + ".png"), (SQUARE_SIZE,SQUARE_SIZE))
        
        
def main():
    '''
    The main driver for our code.
    This will handle user input and updating the graphics.
    '''
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    clock = p.time.Clock()
    screen.fill(p.Color("white"))
    game_state = ChessEngine.GameState()
    valid_moves = game_state.getValidMoves()
    move_made = False #flag variable for when a move is made
    animate = False #flag variable for when we should animate a move
    loadImages() #do this only once before while loop
    
    running = True
    square_selected = () #no square is selected initially, this will keep track of the last click of the user (tuple(row,col))
    player_clicks = [] #this will keep track of player clicks (two tuples)
    game_over = False

    while running:
        for e in p.event.get():  
            if e.type == p.QUIT:
                running = False
                p.quit()
                sys.exit()
            #mouse handler            
            elif e.type == p.MOUSEBUTTONDOWN:
                # location = p.mouse.get_pos() #(x, y) location of the mouse
                # col = location[0] // SQUARE_SIZE
                # row = location[1] // SQUARE_SIZE
                # if square_selected == (row, col): #user clicked the same square twice
                #     square_selected = () #deselect
                #     player_clicks = [] #clear clicks
                # else:
                #     square_selected = (row, col)
                #     player_clicks.append(square_selected) #append for both 1st and 2nd click
                # if len(player_clicks) == 2: #after 2nd click
                #     move = ChessEngine.Move(player_clicks[0], player_clicks[1], game_state.board)  
                #     for i in range(len(valid_moves)):
                #         if move == valid_moves[i]:
                #             game_state.makeMove(valid_moves[i])
                #             move_made = True
                #             square_selected = ()
                #             player_clicks = []
                #     if not move_made:
                #         player_clicks = [square_selected]
                if not game_over:
                    location = p.mouse.get_pos() #(x, y) location of the mouse
                    col = location[0] // SQUARE_SIZE
                    row = location[1] // SQUARE_SIZE
                    if square_selected == (row, col): #user clicked the same square twice
                        square_selected = () #deselect
                        player_clicks = [] #clear clicks
                    else:
                        square_selected = (row, col)
                        player_clicks.append(square_selected) #append for both 1st and 2nd click
                    if len(player_clicks) == 2: #after 2nd click                                                                    
                        move = ChessEngine.Move(player_clicks[0], player_clicks[1], game_state.board)  
                        for i in range(len(valid_moves)):
                            if move == valid_moves[i]:
                                print(move.getChessNotation()) 
                                game_state.makeMove(valid_moves[i])
                                move_made = True
                                animate = True
                                square_selected = () #reset user clicks
                                player_clicks = [] 
                        if not move_made:
                            player_clicks = [square_selected]
            #key handler
            elif e.type == p.KEYDOWN:
                if e.key == p.K_z: #undo when 'z' is pressed
                    game_state.undoMove()
                    move_made = True
                    animate = False
                    game_over = False
                if e.key == p.K_r: #reset the game when 'r' is pressed
                    game_state = ChessEngine.GameState()
                    valid_moves = game_state.getValidMoves()
                    square_selected = ()
                    player_clicks = []
                    move_made = False
                    animate = False
                    game_over = False
                    
        if move_made:
            if animate:
                animateMove(game_state.move_log[-1], screen, game_state.board, clock)
            valid_moves = game_state.getValidMoves()
            move_made = False
            animate = False
                    
                            
        drawGameState(screen, game_state, valid_moves, square_selected) 

        if game_state.check_mate:
            game_over = True
            if game_state.white_to_move:
                drawText(screen, "Black wins by checkmate")
            else:
                drawText(screen, "White wins by checkmate")
        elif game_state.stale_mate:
            game_over = True
            drawText(screen, "Stalemate")

        clock.tick(MAX_FPS)
        p.display.flip()
        
def drawText(screen, text):
    font = p.font.SysFont("Helvitica", 32, True, False)
    text_object = font.render(text, 0, p.Color("gray"))
    text_location = p.Rect(0, 0, WIDTH, HEIGHT).move(WIDTH / 2 - text_object.get_width() / 2, HEIGHT / 2 - text_object.get_height() / 2)
    screen.blit(text_object, text_location)
    text_object = font.render(text, 0, p.Color('black'))
    screen.blit(text_object, text_location.move(2,2))


def highlightSquares(screen, game_state, valid_moves, square_selected):
    '''
    Highlight square selected and moves for piece selected.
    '''
    if (len(game_state.move_log)) > 0:
        last_move = game_state.move_log[-1]
        s = p.Surface((SQUARE_SIZE, SQUARE_SIZE))
        s.set_alpha(100)
        s.fill(p.Color('green'))
        screen.blit(s, (last_move.end_col*SQUARE_SIZE, last_move.end_row*SQUARE_SIZE))
    if square_selected != ():
        row, col = square_selected
        if game_state.board[row][col][0] == ('w' if game_state.white_to_move else 'b'): #square_selected is a piece that can be moved
            #highlight selected square
            s = p.Surface((SQUARE_SIZE, SQUARE_SIZE))
            s.set_alpha(100) #transparency value 0 -> transparent, 255 -> opaque
            s.fill(p.Color('blue'))
            screen.blit(s, (col*SQUARE_SIZE, row*SQUARE_SIZE))
            #highlight moves from that square
            s.fill(p.Color('yellow'))
            for move in valid_moves:
                if move.start_row == row and move.start_col == col:
                    screen.blit(s, (move.end_col*SQUARE_SIZE, move.end_row*SQUARE_SIZE))
                    

def drawGameState(screen, game_state, valid_moves, square_selected):
    '''
    Responsible for all the graphics within current game state.
    '''
    drawBoard(screen) #draw squares on the board
    #add in piece highlighting or move suggestions (later)
    highlightSquares(screen, game_state, valid_moves, square_selected)
    drawPieces(screen, game_state.board) #draw pieces on top of those squares      

def drawBoard(screen):
    '''
    Draw the squares on the board.
    The top left square is always light.
    '''
    global colors
    colors = [p.Color("white"), p.Color("dark green")]
    for row in range(DIMENSION):
        for column in range(DIMENSION):
            color = colors[((row+column) % 2)]
            p.draw.rect(screen, color, p.Rect(column*SQUARE_SIZE, row*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
    
def drawPieces(screen, board):
    '''
    Draw the pieces on the board using the current game_state.board
    '''
    for row in range(DIMENSION):
        for column in range(DIMENSION):
            piece = board[row][column]
            if piece != "--":
                screen.blit(IMAGES[piece], p.Rect(column*SQUARE_SIZE, row*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))



def animateMove(move, screen, board, clock):   
    '''
    Animating a move
    '''
    global colors
    d_row = move.end_row - move.start_row
    d_col = move.end_col - move.start_col
    frames_per_square = 10 #frames to move one square
    frame_count = (abs(d_row) + abs(d_col)) * frames_per_square
    for frame in range(frame_count + 1):
        row, col = (move.start_row + d_row * frame / frame_count, move.start_col + d_col * frame / frame_count)
        drawBoard(screen)
        drawPieces(screen, board)
        #erease the piece moved from its ending square
        color = colors[(move.end_row + move.end_col) % 2]
        end_square = p.Rect(move.end_col*SQUARE_SIZE, move.end_row*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        p.draw.rect(screen, color, end_square)
        #draw captured piece onto rectangle
        if move.piece_captured != '--':
            screen.blit(IMAGES[move.piece_captured], end_square)
        #draw moving piece
        screen.blit(IMAGES[move.piece_moved], p.Rect(col*SQUARE_SIZE, row*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        p.display.flip()
        clock.tick(60)
                
if __name__ == "__main__":
    main()