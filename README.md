
# Sepentia - Chess Engine 

## Prerequisites

Before you start, ensure you have the following installed on your system:

- [Python](https://www.python.org/downloads/) (version 3.6 or higher)
- [Git](https://git-scm.com/downloads) (optional, if you want to clone the repository)

## Installation Steps

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/EuclidStellar/Sepentia-ChessEngine.git

   ```
2. **Install Pygame**:
   ```bash
   pip3 install pygame
   ```
4. **Open Sepentia in Code Editor (VS code)**:
   ```bash
   python3 chessmain.py
   ```

## Heurestia

[![Medium](https://github-readme-medium.vercel.app/?username=euclidstellar_57634)](https://medium.com/@euclidstellar_57634)

As AI is a buzzword nowadays, let's talk mathematics and implement some real positional statistics and some algorithms that you have used in cp but never in real life. Ever thought about how Samay Raina's chess-dotcom bot plays against you at 1800 ElO? As Most of your answers will be: we will collect all his game data on how he plays and then train a model that replicates his moves but I mean how you can train something that has 121 million possibilities maybe Chess.com personalise some of his blunders in his bot but that's not how it works 

So, when I was watching Nakamura vs Pragg ( 98.8 vs 98.3 ) I just out of curiosity got a question how these accuracies are calculated 
ans: chess engine ( Stockfish ) OK how do they work? 
Chess Engine uses a very simple and standard algorithm minimax ( https://leetcode.com/problems/can-i-win/description/ ) just in case you are a leetcode grinder here's a task for you & you know the drill 
moreover, minimax is not an optimal algorithm to calculate the best move on the square board of 64 blocks where positional statistics changes after every move.

So here's my experience of coding a Chess Engine of 1400 ElO at a depth of 5
for non-chess players: ELO is a rating stat, and depth is the number of moves you calculate ahead in the game tree to evaluate possible moves 

![Depth](/images/depth.png)

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
Example:  king = 0 ( you cannot capture king ), Queen = 9, Rook = 5, Bishop = 3, Knight= 3, pawn=1 [yhese al are material value ]
positional scores: every piece on the chessboard will have a different position score on 64 blocks based on studies ex: The value 0.0 represents the lowest score, meaning the worst position for a knight. The values increase as we move towards the centre of the board, indicating better positions example: a knight placed in the centre (rows 2 to 5, columns 2 to 5) would have higher scores compared to those placed on the edges with the highest score, 0.7, is assigned to the centre-most squares (row 3, column 3 to 6) the score gradually decreases as we move away from the centre. 
The role of these scores in the code is to help evaluate the relative strength of different positions on the board for each type of piece during the algorithm’s decision-making process, these scores are used to prioritize moves that lead to positions with higher scores 

![Relative-Positional-value](/images/positional-value.jpg)

example : The positional score of a piece reflects its strength based on its position on the board and in chess, certain positions are more advantageous for pieces than others example, a knight in the center of the board has more mobility and control over squares than a knight stuck in a corner. Similarly, a rook on an open file has more attacking potential than a rook blocked by pawns by incorporating positional scores into the evaluation function of a chess engine, the engine can make smarter decisions about which moves to prioritize. For instance, the engine might prefer moving a piece to a square where it has better control over the board or can support other pieces more effectively.

![Positional-value](/images/positional-value-2.png)

Now let's understand how ordering of move is done and why ordering of move is very important for a chess engine to make decision ?
By ordering moves, the engine reduces the search space, focusing on the most promising moves first this pruning of less promising moves makes the search more efficient, allowing the engine to explore deeper and find better moves within a given time frame.

I have divided ordering move in 2 steps: capture moves and quiet moves 
Capture moves are those moves where a piece captures an opponent's piece and Quiet moves are those moves where a piece moves to a square without capturing any opponent's piece. Capture moves are sorted based on the value of the piece being captured higher-valued pieces are prioritized for capture this is implemented using a lambda function that retrieves the piece value from the piece_score dictionary and sorts the capture moves in descending order of piece value.
Quiet moves are sorted based on the value of the target square each square has a positional score that indicates how good it is for a piece to occupy that square the piece_position_scores dictionary stores these positional scores for each piece type on each square of the board and quiet moves are sorted in descending order of the positional score of the target square and evaluating quiet moves based on positional scores helps the engine identify moves that improve the overall position of its pieces this ensures that the engine doesn't just capture pieces but also aims to improve its position on the board, leading to better long-term prospects and then I'm returning the summision of both the operations.

When evaluating the chessboard, we consider two main factors: intrinsic value and positional value. Intrinsic value is like the importance of a department in a company; it's how valuable the piece is in isolation. Positional value is akin to the location of the department within the company's offices. A sales department located in a prime location (like controlling the center of the board) is more valuable than one in a less desirable area (like trapped in a corner).
Checkmate in chess is like one company buying out another. If one company decisively takes over, its value rises while the other company's value becomes zero. Stalemate, on the other hand, is like a merger negotiation that stalls. No company wins or loses; the value remains static.
The total score of the chessboard, calculated by summing up the intrinsic and positional values of all pieces, gives an overall appraisal of the game state. This evaluation is essential for a chess engine's decision-making process. It helps the engine decide which moves are better than others, formulate long-term strategies, and even determine the order in which moves should be explored during the search process

![Move-order](/images/move-order.png)

Ok now we have understanding of how engine works let's understand how to make it effecient ?

Imagine you're playing chess and you have to decide which move to make where each move you can make leads to another set of possible moves for your opponent, and those moves lead to even more moves, forming a tree-like structure this structure is called a game tree.

Let's say you're considering three possible moves, labeled A, B, and C. Each of these moves leads to two possible responses from your opponent, and each of those responses leads to another two possible moves from you, and so on.
```bash
            A
          /   \
       Opp1  Opp2
      / \     / \
    B1   B2  C1   C2
   / \   / \ / \  / \
   ...   ... ...  ...
```
the game tree is much larger and deeper, but for this example, we'll keep it simple.
Alpha-Beta Pruning: Imagine you have to explore this entire game tree to find the best move. It would take a lot of time and computational power. This is where alpha-beta pruning comes in.
Alpha-beta pruning is a way to reduce the number of nodes explored in the game tree by eliminating branches that can't possibly lead to a better outcome.
Alpha: Represents the best (highest) value found so far by any means along the path for the maximizing player (e.g., white).
Beta: Represents the best (lowest) value found so far by any means along the path for the minimizing player (e.g., black).
If the algorithm finds a move that is better than the current alpha (for the maximizing player) or beta (for the minimizing player), it updates the alpha or beta accordingly.
If, during the exploration of the subtree, the algorithm finds a node where the beta of the minimizing player becomes less than or equal to the alpha of the maximizing player, it knows that the maximizing player won't choose this path because the minimizing player has a better option elsewhere. So, the algorithm prunes (cuts off) this branch and doesn't explore it further.


![Depth](/images/alpha-beta.png)

In the context of game trees, depth refers to how many moves ahead the algorithm is exploring. Each level of depth represents a move by one player (e.g., white), followed by a response by the opponent (e.g., black).

```bash
          Depth 0 (Initial Board)
             /   \
    Depth 1     Depth 1
    (White)      (Black)
      / \          / \
 Depth 2 Depth 2 Depth 2 Depth 2
(White) (Black) (White) (Black)
  ...     ...      ...     ...

In this tree, the root node represents the initial board position.
Each subsequent level of nodes represents the possible moves by each player.
The depth of the tree indicates how many moves ahead the algorithm is exploring.

```
How we are achieving depth ?
Using recursion ( yeah , you got it if there's a recursion there must be a problem with time and memory hold on we will sort this later)
for now let's understand recursive calls in this engine 
The depth of the game tree corresponds to the recursion depth of the algorithm and recursive calls continue until a stopping condition is met, such as reaching the desired depth or encountering a terminal node (checkmate) and more importantly recursive calls allow the algorithm to evaluate positions at different depths, considering the moves of both players and after exploring a branch of the tree, recursive calls backtrack to explore other branches this backtracking process effectively explores the entire tree up to the specified depth.

Now you must say "hehe recursive calls hi to hai badha do depth badh jayegi aur engine acha ho jayega ?"
Lemme ask you something "paise hi to hai government se bolo aur chaap de gareebi khatam ho jayegi ?"
Let's understand why NOT?
As the depth of the game tree increases, the number of nodes explored and the computational power required also increase exponentially this has significant effects on both memory and CPU power
When we explore additional level of depth, the number of nodes in the tree grows exponentially and more memory is required to store information about each node, including board positions, scores, and move sequences and deeper searches require more memory to hold the additional nodes, potentially leading to memory overflow or excessive memory consumption which ultimately leads to more time.

here this line comes in " yeah , you got it if there's a recursion there must be a problem with time and memory hold on we will sort this later"

now understand how I'm handling memory and computational resources to make my chess engine more fast and accurate 
Using Transposition table is the most crucial step I choose to tackle this problem :
A transposition table is essentially a cache that stores previously computed positions and their evaluations it's like a memory bank that remembers positions encountered during the search.
Let's understand how it works and how it is helping my algo:
Each position in the game is hashed to create a unique identifier and this hash serves as the key to store and retrieve information about the position in the transposition table when a position is evaluated during the search, its evaluation value, depth, and other relevant information are stored in the transposition table whereas this information is associated with the hashed position

Before evaluating a position, the algorithm checks if it has already been evaluated and stored in the transposition table and if the position is found in the table and its depth is sufficient, the algorithm can use the stored evaluation value instead of re-evaluating the position and if the stored depth is less than the current depth, the information may not be reliable, and the position may need to be re-evaluated.
During deep searches, many positions are revisited due to branching in the game tree and the transposition table helps avoid re-evaluating these positions. With transposition table, the algorithm can safely increase the depth of the search without running out of memory even with limited memory resources, the table ensures that previously explored positions are available for reference.

OK Gaurav We tackled the memory but how we are managing the time you may have saved memory but what about time ? 
ok let's understanding it with an analogy :
Imagine you're building a puzzle, and each friend helps with a different section. The depth of the task represents its complexity, like adding more layers to the puzzle. Recursive calls break down complex tasks into smaller parts, just as you might divide a puzzle into smaller sections to solve them. As depth increases, so does the demand for memory and processing power. Here multiprocessing helps by distributing the workload across multiple CPU cores, allowing tasks to be completed faster and more efficiently.

![Depth](/images/trans-table.jpg)

By far you have got an answer of using multiprocessing let's understand how it gonna help sepentia:
In Sepentia, the search process involves exploring possible moves and counter-moves where this search can be broken down into independent tasks that can be executed simultaneously. Multiprocessing allows the chess engine to perform these tasks concurrently across multiple CPU cores, drastically speeding up the search process where each core can explore a different branch of the game tree simultaneously, effectively increasing the search depth within the same amount of time. While one process explores a particular branch, other processes can generate moves for subsequent branches, thus overlapping computation and improving efficiency which helps to process more positions per second.

I also tried to use GPU for achieving parallelism but failed to fight with the architecture of my mac but here's a intution how GPU can help to make sepentia more better :
GPUs are highly parallel processors that excel at performing many computations simultaneously by offloading certain computational tasks to GPUs, Sepentia can achieve even greater performance gains, especially in tasks like evaluating positions and performing deep searches.


That's the whole intution and logic behind this If you read the complete stuff I have written I sincerely thank you for your time and 
If you have any idea to Improve this and want to give a suggestion drop a mail at euclidstellar@gmail.com I will be more than happy to have your suggestions.

```bash
Sepentia,
Gaurav 
@euclidstellar
```












 
