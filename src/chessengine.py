'''
Storing all the information about the current state of chess game.
Determining valid moves at current state.
It will keep move log.
'''
class GameState():
    def __init__(self):
        '''
        Board is an 8x8 2d list, each element in list has 2 characters.
        The first character represtents the color of the piece: 'b' or 'w'.
        The second character represtents the type of the piece: 'R', 'N', 'B', 'Q', 'K' or 'p'.
        "--" represents an empty space with no piece.
        '''
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "wB", "--", "--", "--", "--"],
            ["--", "--", "bB", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]]
        self.moveFunctions = {"p": self.getPawnMoves, "R": self.getRookMoves, "N": self.getKnightMoves,
                              "B": self.getBishopMoves, "Q": self.getQueenMoves, "K": self.getKingMoves}
        self.white_to_move = True
        self.move_log = []
        self.white_king_location = (7,4)
        self.black_king_location = (0,4)
        self.check_mate = False
        self.stale_mate = False
        self.in_check = False
        self.pins = []
        self.checks = []
        self.enpassant_possible = () #coordinates for the square where en passant capture is possible
        
    def makeMove(self, move):
        '''
        Takes a Move as a parameter and exectutes it.
        (this will not work for castling, pawn promotion and en-passant)
        '''
        self.board[move.start_row][move.start_col] = "--"
        self.board[move.end_row][move.end_col] = move.piece_moved
        self.move_log.append(move) #log the move so we can undo it later
        self.white_to_move = not self.white_to_move #switch players
        if move.piece_moved == "wK":
            self.white_king_location = (move.end_row, move.end_col)
        elif move.piece_moved == "bK":
            self.black_king_location = (move.end_row, move.end_col)
            
         #pawn promotion
        if move.is_pawn_promotion:
            promoted_piece = input("Promote to Q, R, B, or N:") #take this to UI later
            self.board[move.end_row][move.end_col] = move.piece_moved[0] + promoted_piece

        #enpassant move
        if move.is_enpassant_move:
            self.board[move.start_row][move.end_col] = "--" #capturing the pawn

        #update enpassant_possible variable
        if move.piece_moved[1] == "p" and abs(move.start_row - move.end_row) == 2: #only on 2 square pawn advance
            self.enpassant_possible = ((move.start_row + move.end_row) // 2, move.start_col)  
        else:
            self.enpassant_possible = ()
       
 
    def undoMove(self):
        '''
        Undo the last move
        '''   
        if len(self.move_log) != 0: #make sure that there is a move to undo
            move = self.move_log.pop()
            self.board[move.start_row][move.start_col] = move.piece_moved
            self.board[move.end_row][move.end_col] = move.piece_captured
            self.white_to_move = not self.white_to_move #swap players
            
             #update the king's position if needed
            if move.piece_moved == "wK":
                self.white_king_location = (move.start_row, move.start_col)
            elif move.piece_moved == "bK":
                self.black_king_location = (move.start_row, move.start_col)   
             #undo en passant move
            if move.is_enpassant_move:
                self.board[move.end_row][move.end_col] = "--" #leave landing square blank
                self.board[move.start_row][move.end_col] == move.piece_captured
                self.enpassant_possible = (move.end_row, move.end_col)
            #undo a 2 square pawn advance 
            if move.piece_moved[1] == "p" and abs(move.start_row - move.end_row) == 2:
                self.enpassant_possible = ()
         
            
    def getValidMoves(self):
        '''
        All moves considering checks.
        '''
        # 1) generate all possible moves
        # moves = self.getAllPossibleMoves()
        # # 2) for each move, make the move
        # for i in range(len(moves)-1, -1, -1): # when removing from a list go backwards through that list
        #     self.makeMove(moves[i])
        #     # 3) generate all oponent's moves
        #     # 4) for each of your oponent's moves, see if they attack your king
        #     self.white_to_move = not self.white_to_move
        #     if self.inCheck():
        #         # 5) if they do attack your king, not a valid move
        #         moves.remove(moves[i])
        #     self.white_to_move = not self.white_to_move
        #     self.undoMove()
        # return moves
        
        
        #advanced algorithm
        moves = []
        self.in_check, self.pins, self.checks = self.checkForPinsAndChecks()

        if self.white_to_move: 
            king_row = self.white_king_location[0]
            king_col = self.white_king_location[1]
        else:
            king_row = self.black_king_location[0]
            king_col = self.black_king_location[1]
        if self.in_check:
            if len(self.checks) == 1: #only 1 check, block the check or move the king
                moves = self.getAllPossibleMoves()
                #to block the check you must put a piece into one of the squares between the enemy piece and your king
                check = self.checks[0] #check information
                check_row = check[0]
                check_col = check[1]
                piece_checking = self.board[check_row][check_col]
                valid_squares = [] #squares that pieces can move to
                #if knight, must capture the knight or move your king, other pieces can be blocked
                if piece_checking[1] == "N":
                    valid_squares = [(check_row, check_col)]
                else:
                    for i in range(1, 8):
                        valid_square = (king_row + check[2] * i, king_col + check[3] * i) #check[2] and check[3] are the check directions
                        valid_squares.append(valid_square)
                        if valid_square[0] == check_row and valid_square[1] == check_col: #once you get to piece and check
                            break
                #get rid of any moves that don't block check or move king
                for i in range(len(moves)-1, -1, -1): #iterate through the list backwards when removing elements
                    if moves[i].piece_moved[1] != "K": #move doesn't move king so it must block or capture
                        if not (moves[i].end_row, moves[i].end_col) in valid_squares: #move doesn't block or capture piece
                            moves.remove(moves[i])
            else: #double check, king has to move
                self.getKingMoves(king_row, king_col, moves)
        else: #not in check - all moves are fine
            moves = self.getAllPossibleMoves()  

        if len(moves) == 0:
            if self.inCheck():
                self.check_mate = True
            else:
                self.stale_mate = True
        else:
            self.check_mate = False
            self.stale_mate = False
        return moves
    
    def checkForPinsAndChecks(self):
        pins = [] #squares pinned and the direction it's pinned from
        checks = [] #squares where enemy is applying a check
        in_check = False
        if self.white_to_move:
            enemy_color = "b"
            ally_color = "w"
            start_row = self.white_king_location[0]
            start_col = self.white_king_location[1]
        else:
            enemy_color = "w"
            ally_color = "b"
            start_row = self.black_king_location[0]
            start_col = self.black_king_location[1]
        #check outwards from king for pins and checks, keep track of pins
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
        for j in range(len(directions)):
            direction = directions[j]
            possible_pin = () #reset possible pins
            for i in range(1, 8):
                end_row = start_row + direction[0] * i
                end_col = start_col + direction[1] * i
                if 0 <= end_row <= 7 and 0 <= end_col <= 7:        
                    end_piece = self.board[end_row][end_col]
                    if end_piece[0] == ally_color and end_piece[1] != "K":
                        if possible_pin == (): #first allied piece could be pinned
                            possible_pin = (end_row, end_col, direction[0], direction[1])
                        else: #2nd allied piece - no check or pin from this direction
                            break
                    elif end_piece[0] == enemy_color:
                        enemy_type = end_piece[1]
                         # 5 possibilities in this complex conditional
                        # 1.) orthogonally away from king and piece is a rook
                        # 2.) diagonally away from king and piece is a bishop
                        # 3.) 1 square away diagonally from king and piece is a pawn
                        # 4.) any direction and piece is a queen
                        # 5.) any direction 1 square away and piece is a king
                        if (0 <= j <= 3 and enemy_type == "R") or (4 <= j <= 7 and enemy_type == "B") or (i == 1 and enemy_type == "p" and ((enemy_color == "w" and 6 <= j <= 7) or (enemy_color == "b" and 4 <= j <= 5))) or (enemy_type == "Q") or (i == 1 and enemy_type == "K"):
                            if possible_pin == (): #no piece blocking, so check
                                in_check = True
                                checks.append((end_row, end_col, direction[0], direction[1]))
                                break
                            else: #piece blocking so pin
                                pins.append(possible_pin)
                                break
                        else: #enemy piece not applying checks
                            break
                else:
                    break #off board
        #check for knight checks
        knight_moves = ((-2, -1), (-2, 1), (-1, 2), (1, 2), (2, -1), (2, 1), (-1, -2), (1, -2))
        for move in knight_moves:
            end_row = start_row + move[0]
            end_col = start_col + move[1]
            if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                end_piece = self.board[end_row][end_col]
                if end_piece[0] == enemy_color and end_piece[1] == "N": #enemy knight attaking a king
                    in_check = True
                    checks.append((end_row, end_col, move[0], move[1]))
        return in_check, pins, checks

      
    def inCheck(self):
        '''
        Determine if a current player is in check
        '''
        if self.white_to_move:
            return self.squareUnderAttack(self.white_king_location[0], self.white_king_location[1])
        else:
            return self.squareUnderAttack(self.black_king_location[0], self.black_king_location[1])  
        
    def squareUnderAttack(self, row, col):
        '''
        Determine if enemy can attack the square row col
        '''
        self.white_to_move = not self.white_to_move #switch to oponent's point of wiev
        opponents_moves = self.getAllPossibleMoves()
        self.white_to_move = not self.white_to_move
        for move in opponents_moves:
            if move.end_row == row and move.end_col == col: #square is under attack
                return True
        return False
    
    def getAllPossibleMoves(self):
        '''
        All moves without considering checks.
        '''
        moves = []
        for row in range(len(self.board)):
            for col in range(len(self.board[row])):
                turn = self.board[row][col][0]
                if (turn == "w" and self.white_to_move) or (turn == "b" and not self.white_to_move):
                    piece = self.board[row][col][1]
                    self.moveFunctions[piece](row, col, moves) #calls appropriate move function based on piece type
        return moves
       
    def getPawnMoves(self, row, col, moves):
        '''
        Get all the pawn moves for the pawn located at row, col and add the moves to the list.
        '''
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins)-1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break
        if self.white_to_move:
            move_amount = -1
            start_row = 6
            enemy_color = "b"
        else:
            move_amount = 1
            start_row = 1
            enemy_color = "w"

        # if self.white_to_move: #white pawn moves
        #     if self.board[row-1][col] == "--": #1 square pawn advance
        #         if not piece_pinned or pin_direction == (-1, 0):
        #             moves.append(Move((row, col), (row-1, col), self.board)) #(start square, end square, board)
        #             if row == 6 and self.board[row-2][col] == "--": #2 square pawn advance
        #                 moves.append(Move((row, col), (row-2, col), self.board))

        #     if col - 1 >= 0: #capturing to the left - impossible if a pawn is standing in a far left column
        #         if self.board[row-1][col-1][0] == "b": #enemy piece to capture
        #            # moves.append(Move((row, col), (row-1, col-1), self.board))
        #             if not piece_pinned or pin_direction == (-1, -1):
        #                 moves.append(Move((row, col), (row-1, col-1), self.board))

        #     if col + 1 <= 7: #capturing to the right - analogical
        #         if self.board[row-1][col+1][0] == "b": #enemy piece to capture
        #            # moves.append(Move((row, col), (row-1, col+1), self.board))
        # #if not self.white_to_move: #black pawn moves
        #             if not piece_pinned or pin_direction == (-1, 1):
        #                 moves.append(Move((row, col), (row-1, col+1), self.board))
        if self.board[row+move_amount][col] == "--": #1 square pawn advance
            if not piece_pinned or pin_direction == (move_amount, 0):
                moves.append(Move((row, col), (row + move_amount, col), self.board))
                if row == start_row and self.board[row + 2 * move_amount][col] == "--": #2 square pawn advance
                    moves.append(Move((row, col), (row + 2 * move_amount, col), self.board))
        if col - 1 >= 0: #capture to the left
            if not piece_pinned or pin_direction == (move_amount, -1):
                if self.board[row + move_amount][col - 1][0] == enemy_color:
                    moves.append(Move((row, col), (row + move_amount, col - 1), self.board))
                if (row + move_amount, col - 1) == self.enpassant_possible:
                    moves.append(Move((row, col), (row + move_amount, col - 1), self.board, is_enpassant_move = True))
        if col + 1 <= 7: #capture to the right
            if not piece_pinned or pin_direction == (move_amount, +1):
                if self.board[row + move_amount][col +1][0] == enemy_color:
                    moves.append(Move((row, col), (row + move_amount, col + 1), self.board))
                if (row + move_amount, col + 1) == self.enpassant_possible:
                    moves.append(Move((row, col), (row + move_amount, col + 1), self.board, is_enpassant_move = True))

        # else: #black pawn moves
        #     if self.board[row+1][col] == "--": #1 suare pawn advance
        #        # moves.append(Move((row, col), (row+1, col), self.board))
        #         #if row == 1 and self.board[row+2][col] == "--":
        #            # moves.append(Move((row ,col), (row+2, col), self.board))
        #         if not piece_pinned or pin_direction == (1, 0):
        #             moves.append(Move((row, col), (row+1, col), self.board))
        #             if row == 1 and self.board[row+2][col] == "--":
        #                 moves.append(Move((row ,col), (row+2, col), self.board))

        #     if col - 1 >= 0:
        #         if self.board[row+1][col-1][0] == "w":
        #             #moves.append(Move((row, col), (row+1, col-1), self.board))
        #             if not piece_pinned or pin_direction == (1, -1):
        #                 moves.append(Move((row, col), (row+1, col-1), self.board))

        #     if col + 1 <= 7:
        #         if self.board[row+1][col+1][0] == "w":
        #             #moves.append(Move((row, col), (row+1, col+1), self.board))
        #             if not piece_pinned or pin_direction == (1, 1):
        #                 moves.append(Move((row, col), (row+1, col+1), self.board))
        
    
    def getRookMoves(self, row, col, moves):
        '''
        Get all the rook moves for the rook located at row, col and add the moves to the list.
        '''
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins)-1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                if self.board[row][col][1] != "Q": #can't remove queen from pin on rook moves, only remove it on bishop moves
                    self.pins.remove(self.pins[i])
                break
        
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1)) #up, left, down, right
        enemy_color = "b" if self.white_to_move else "w"
        for direction in directions:
            for i in range(1, 8):
                end_row = row + direction[0] * i
                end_col = col + direction[1] * i
                if 0 <= end_row <= 7 and 0 <= end_col <= 7: #check for possible moves only in boundries of the board
                    # end_piece = self.board[end_row][end_col]
                    # if end_piece == "--": #empty space is valid
                    #     moves.append(Move((row, col), (end_row, end_col), self.board))
                    # elif end_piece[0] == enemy_color: #capture enemy piece
                    #     moves.append(Move((row, col), (end_row, end_col), self.board))
                    #     break
                    if not piece_pinned or pin_direction == direction or pin_direction == (-direction[0], -direction[1]):
                        end_piece = self.board[end_row][end_col]
                        if end_piece == "--": #empty space is valid
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                        elif end_piece[0] == enemy_color: #capture enemy piece
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                            break
                        else: #friendly piece
                            break
                else: #off board
                    break
                        
                        
    def getKnightMoves(self, row, col, moves):
        '''
        Get all the knight moves for the knight located at row col and add the moves to the list.
        '''
        piece_pinned = False
        for i in range(len(self.pins)-1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                self.pins.remove(self.pins[i])
                break
        knight_moves = ((-2, -1), (-2, 1), (-1, 2), (1, 2), (2, -1), (2, 1), (-1, -2), (1, -2)) #up/left up/right right/up right/down down/left down/right left/up left/down
        ally_color = "w" if self.white_to_move else "b"
        for move in knight_moves:
            end_row = row + move[0]
            end_col = col + move[1]
            if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                # end_piece = self.board[end_row][end_col]
                # if end_piece[0] != ally_color: #so it's either enemy piece or empty equare 
                #     moves.append(Move((row, col), (end_row, end_col), self.board))
                if not piece_pinned:
                    end_piece = self.board[end_row][end_col]
                    if end_piece[0] != ally_color: #so it's either enemy piece or empty equare 
                        moves.append(Move((row, col), (end_row, end_col), self.board))
                    
    
    def getBishopMoves(self, row, col, moves):
        '''
        Get all the bishop moves for the bishop located at row col and add the moves to the list.
        '''
        
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins)-1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break
            
        directions = ((-1, -1), (-1, 1), (1, 1), (1, -1)) #digaonals: up/left up/right down/right down/left
        enemy_color = "b" if self.white_to_move else "w"    
        for direction in directions:
            for i in range(1, 8):
                end_row = row + direction[0] * i
                end_col = col + direction[1] * i
                if 0 <= end_row <= 7 and 0 <= end_col <= 7: #check if the move is on board
                    if not piece_pinned or pin_direction == direction or pin_direction == (-direction[0], -direction[1]):
                        end_piece = self.board[end_row][end_col]
                        if end_piece == "--": #empty space is valid
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                        elif end_piece[0] == enemy_color: #capture enemy piece
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                            break
                        else: #friendly piece
                            break
                else: #off board
                    break




    def getQueenMoves(self, row, col, moves):
        '''
        Get all the queen moves for the queen located at row col and add the moves to the list.
        '''
        self.getBishopMoves(row, col, moves)
        self.getRookMoves(row, col, moves)


    def getKingMoves(self, row, col, moves):
        '''
        Get all the king moves for the king located at row col and add the moves to the list.
        '''
       # king_moves = ((-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1))
        row_moves = (-1, -1, -1, 0, 0, 0, 1, 1, 1)
        col_moves = (-1, 0, 1, -1, 0, 1, -1, 0, 1)
        ally_color = "w" if self.white_to_move else "b"
        # for move in king_moves:
        #     end_row = row + move[0]
        #     end_col = col + move[1]
        for i in range(8):
            end_row = row + row_moves[i]
            end_col = col + col_moves[i]
            if 0 <= end_row <= 7 and 0 <= end_col <= 7:
                end_piece = self.board[end_row][end_col]
                # if end_piece[0] != ally_color:
                #     moves.append(Move((row, col), (end_row, end_col), self.board))
                if end_piece[0] != ally_color: #not an ally piece - empty or enemy
                    #place king on end square and check for checks
                    if ally_color == "w":
                        self.white_king_location = (end_row, end_col)
                    else:
                        self.black_king_location = (end_row, end_col)
                    in_check, pins, checks = self.checkForPinsAndChecks()
                    if not in_check:
                        moves.append(Move((row, col), (end_row, end_col), self.board))
                    #place king back on original location
                    if ally_color == "w":
                        self.white_king_location = (row, col)
                    else:
                        self.black_king_location = (row, col)


class Move():
    '''
    in chess fields on the board are described by two symbols, one of them being number between 1-8 (which is corespodning to rows)
    and the second one being a letter between a-f (coresponding to columns), in order to use this notation we need to map our [row][col] coordinates
    to match the ones used in the original chess game
    '''
    ranks_to_rows = {"1": 7, "2": 6, "3": 5, "4": 4,
                     "5": 3, "6": 2, "7": 1, "8": 0}
    rows_to_ranks = {v: k for k, v in ranks_to_rows.items()}
    files_to_cols = {"a": 0, "b": 1, "c": 2, "d": 3,
                     "e": 4, "f": 5, "g": 6, "h": 7}
    cols_to_files = {v: k for k, v in files_to_cols.items()}
    
    def __init__(self, start_square, end_square, board , is_enpassant_move = False):
        self.start_row = start_square[0]
        self.start_col = start_square[1]
        self.end_row = end_square[0]
        self.end_col = end_square[1]
        self.piece_moved = board[self.start_row][self.start_col]
        self.piece_captured = board[self.end_row][self.end_col]
        self.is_pawn_promotion = (self.piece_moved == "wp" and self.end_row == 0) or (self.piece_moved == "bp" and self.end_row == 7)   
        self.is_enpassant_move = is_enpassant_move
        if self.is_enpassant_move:
            self.piece_captured = "wp" if self.piece_moved == "bp" else "bp"
        self.moveID = self.start_row * 1000 + self.start_col * 100 + self.end_row * 10 + self.end_col 
    
    def __eq__(self, other):
        '''
        Overriding the equals method.
        '''
        if isinstance(other, Move):
            return self.moveID == other.moveID
        return False
            
        
    def getChessNotation(self):
        return self.piece_moved + " " + self.getRankFile(self.start_row, self.start_col) + "->" + self.getRankFile(self.end_row, self.end_col) + " " + self.piece_captured 
    
    
    def getRankFile(self, row, col):
        return self.cols_to_files[col] + self.rows_to_ranks[row]
        
     