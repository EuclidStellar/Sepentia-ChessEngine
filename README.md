
# Sepentia - Chess Engine 

## Prerequisites

Before you start, ensure you have the following installed on your system:

- [Python](https://www.python.org/downloads/) (version 3.6 or higher)
- [Git](https://git-scm.com/downloads) (optional, if you want to clone the repository)

## Installation Steps

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/euclidstellar/chess-engine.git

   ```
2. **Install Pygame**:
   ```bash
   pip3 install pygame
   ```
4. **Open Sepentia in Code Editor (VS code)**:
   ```bash
   python3 ChessMain.py
   ```

## Heurestia

As AI is a buzzword nowadays, let's talk mathematics and implement some real positional statistics and some algorithms that you have used in cp but never in real life. Ever thought about how Samay Raina's chess-dotcom bot plays against you at 1800 ElO? As Most of your answers will be: we will collect all his game data on how he plays and then train a model that replicates his moves but I mean how you can train something that has 121 million possibilities maybe Chess.com personalise some of his blunders in his bot but that's not how it works 

So, when I was watching Nakamura vs Pragg ( 98.8 vs 98.3 ) I just out of curiosity got a question how these accuracies are calculated 
ans: chess engine ( Stockfish ) OK how do they work? 
Chess Engine uses a very simple and standard algorithm minimax ( https://leetcode.com/problems/can-i-win/description/ ) just in case you are a leetcode grinder here's a task for you & you know the drill 
moreover, minimax is not an optimal algorithm to calculate the best move on the square board of 64 blocks where positional statistics changes after every move.

So here's my experience of coding a Chess Engine of 1400 ElO at a depth of 5
for non-chess players: ELO is a rating stat, and depth is the number of moves you calculate ahead in the game tree to evaluate possible moves 

First, we will check all the valid moves available on the chessboard then we use the minimax algorithm to explore each level of the possible game tree where 
each level represents a player's turn, and each node represents a possible board position after a move. The main objective of the minimax algorithm is to evaluate maximising moves for your turn and evaluating minimising moves for the opponent ( for now, consider this for material on the board algo will always try to have your maximum material on the chessboard for you and minimum for the opponent )
The main problem with the minimax algorithm is its computational complexity, especially where the branching factor (number of possible moves) is high
Minimax explores the entire game tree to find the best move which is not optimal because you are lazy(human) and you cannot travel each node 

here comes the alpha-beta pruning algorithm: 
When a maximising player finds a move with a value greater than or equal to beta, it means that the opponent has a better move elsewhere. Therefore, the maximising doesn't need to explore further down this branch. It cuts off the exploration and returns the current best move with value beta.

OK now we know how a game tree works and how we search inside a game tree 
but the problem is in chess there's a huge role of positional scores, pawn structures, centre control, forking and pins all these parameters make a chess engine.
how are we gonna tackle all this?
well well we have some desired data on the internet through which we can make this possible as each piece has a different value as a material and different value on different positions of the chessboard 
Example:  king = 0 ( you cannot capture king ), Queen = 9, Rook = 5, Bishop = 3, Knight= 3, pawn=1 [yhese al are material value )
positional scores: every piece on the chessboard will have a different position score on 64 blocks based on studies ex: The value 0.0 represents the lowest score, meaning the worst position for a knight. The values increase as we move towards the centre of the board, indicating better positions example: a knight placed in the centre (rows 2 to 5, columns 2 to 5) would have higher scores compared to those placed on the edges with the highest score, 0.7, is assigned to the centre-most squares (row 3, column 3 to 6) the score gradually decreases as we move away from the centre. 
The role of these scores in the code is to help evaluate the relative strength of different positions on the board for each type of piece during the algorithm’s decision-making process, these scores are used to prioritize moves that lead to positions with higher scores 
 
