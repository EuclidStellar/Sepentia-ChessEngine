# this classs is responsibel for storing all the info of a chess game and deciding the valid moves at the current state
# This class will also be responsible for keeping a move log


class GameState():
    def __init__(self):
        #board is an 8x8 2d list, each element of the list has 2 characters
        #the first character represents the color of the piece, 'b' or 'w'
        #the second character represents the type of the piece, 'K', 'Q', 'R', 'B', 'N', 'P'
        # "--" represents an empty space with no piece
        
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "wR", "--", "bR", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["--", "--", "--", "--", "--", "--", "--", "--"],
            ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"], 
        ]
        self.moveFunctions = {
            
            'p': self.getPawnMoves, 'R': self.getRookMoves, 
            'N': self.getKnightMoves, 'B': self.getBishopMoves, 
            'Q': self.getQueenMoves, 'K': self.getKingMoves
                            
            }
        self.whiteToMove = True
        self.moveLog = []
    def makeMove(self, move):
        self.board[move.startRow][move.startCol] = "--"
        self.board[move.endRow][move.endCol] = move.pieceMoved
        self.moveLog.append(move)
        self.whiteToMove = not self.whiteToMove
        
    '''
    Undo the last move made'''
    
    def undoMove(self):
        if len(self.moveLog) != 0:
            move = self.moveLog.pop()
            self.board[move.startRow][move.startCol] = move.pieceMoved
            self.board[move.endRow][move.endCol] = move.pieceCaptured
            self.whiteToMove = not self.whiteToMove

    '''
    All moves considering checks'''
    
    def getValidMoves(self):
        return self.getAllPossibleMoves()
    
    '''
    all possible moves '''
    
    def getAllPossibleMoves(self):
        moves = []
        for r in range(len(self.board)):
            for c in range(len(self.board[r])):
                turn = self.board[r][c][0]
               
                if (turn == 'w' and self.whiteToMove) or (turn == 'b' and not self.whiteToMove):
                    
                    piece = self.board[r][c][1]
                    self.moveFunctions[piece](r, c, moves)
        
        return moves
        
       
    
    def getPawnMoves(self, row, col, moves):
        '''
        Get all the pawn moves for the pawn located at row, col and add the moves to the list.
        '''
        if self.whiteToMove: #white pawn moves
            if self.board[row-1][col] == "--": #1 square pawn advance
                moves.append(Move((row, col), (row-1, col), self.board)) #(start square, end square, board)
                if row == 6 and self.board[row-2][col] == "--": #2 square pawn advance
                    moves.append(Move((row, col), (row-2, col), self.board))
            if col - 1 >= 0: #capturing to the left - impossible if a pawn is standing in a far left column
                if self.board[row-1][col-1][0] == "b": #enemy piece to capture
                    moves.append(Move((row, col), (row-1, col-1), self.board))
            if col + 1 <= 7: #capturing to the right - analogical
                if self.board[row-1][col+1][0] == "b": #enemy piece to capture
                    moves.append(Move((row, col), (row-1, col+1), self.board))
        if not self.whiteToMove: #black pawn moves
            if self.board[row+1][col] == "--": #1 suare pawn advance
                moves.append(Move((row, col), (row+1, col), self.board))
                if row == 1 and self.board[row+2][col] == "--":
                    moves.append(Move((row ,col), (row+2, col), self.board))
            if col - 1 >= 0:
                if self.board[row+1][col-1][0] == "w":
                    moves.append(Move((row, col), (row+1, col-1), self.board))
            if col + 1 <= 7:
                if self.board[row+1][col+1][0] == "w":
                    moves.append(Move((row, col), (row+1, col+1), self.board))


    def getRookMoves(self, r, c, moves):
        pass
    
    def getKnightMoves(self, r, c, moves):
        pass
    
    def getBishopMoves(self, r, c, moves):
        pass
    
    def getQueenMoves(self, r, c, moves):
        pass
    
    def getKingMoves(self, r, c, moves):
        pass
    

    
            
    
class Move():
    
    ranksToRows = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}
    rowsToRanks = {v: k for k, v in ranksToRows.items()}
    
    filesToCols = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
    colsToFiles = {v: k for k, v in filesToCols.items()}
    
    def __init__(self , startSq, endSq, board):
        self.startRow = startSq[0]
        self.startCol = startSq[1]
        self.endRow = endSq[0]
        self.endCol = endSq[1]
        self.pieceMoved = board[self.startRow][self.startCol]
        self.pieceCaptured = board[self.endRow][self.endCol]
        self.moveID = self.startRow * 1000 + self.startCol * 100 + self.endRow * 10 + self.endCol
        print(self.moveID)
        
    
    '''
    Overriding the equals method'''
    def __eq__(self, other):
        if isinstance(other, Move):
            return self.moveID == other.moveID
        return False
        
     
    
    def getChessNotation(self):
        #you can add to make this like real chess notation
        return self.getRankFile(self.startRow, self.startCol) + self.getRankFile(self.endRow, self.endCol)
    
    def getRankFile(self, r, c):
        return self.colsToFiles[c] + self.rowsToRanks[r]
        
        