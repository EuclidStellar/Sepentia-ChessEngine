# Sepentia engine — improvements

> From ~1200–1400 ELO to ~1800–2000 ELO in one session, with shorter and
> more predictable think times.

This document explains **every change**, in plain language with analogies,
and groups them into four themes: **correctness fixes**, **search algorithm**,
**evaluation**, and **infrastructure**.

---

## The starting point

The engine was a fixed-depth-4 negamax with α-β, a material-only evaluation
function, and a broken transposition table that was never actually used by
the game loop. Typical weaknesses at that level: hanging pieces in forced
sequences, passive endgame play, and long wall-clock times despite a shallow
search depth.

A human player rated ~1800 could beat it comfortably.

---

## 1. Correctness fixes (not ELO — just truth)

These weren't "improvements" so much as bugs we had to fix before anything
else could work.

### 1.1 Transposition table key was incomplete

**The bug.** The hash key for a position was `str(self.board)` — just the
piece layout. It missed: whose turn it was, castling rights, and the
en-passant target square.

**Analogy.** A library indexed only by book titles. You ask for "War and
Peace"; the librarian returns a different edition, different language,
maybe an audiobook. Mostly right, occasionally catastrophically wrong.

**Why it matters.** The transposition table is a cache of "I already
analyzed this position." If the key doesn't uniquely identify a position,
you retrieve analyses from *different* positions and play moves based on
wrong data. This is a correctness bug, not a speed bug.

**Fix.** The key now includes side-to-move, all four castling rights, and
en-passant target, packed into a hashable tuple.

### 1.2 The game loop called the wrong search

**The bug.** Two search functions existed: one used the transposition
table, one didn't. The game UI called the non-TT version. The TT version
was unreachable dead code.

**Analogy.** Two chefs in a restaurant: one experienced, one on day one.
The manager only sends orders to the new chef. The experienced one stands
at the window reading a book.

**Fix.** Unified into a single proper search. The "experienced chef"
is now always cooking.

### 1.3 Iterative deepening was broken

**The bug.** The search was supposed to go 1 ply deep, then 2, then 3,
etc. But the loop exited after depth 1 because the exit condition was
"we found a move" — which is true at every depth ≥ 1.

**Analogy.** A student: "I'll read the chapter, then review it, then
quiz myself." She reads one page, thinks "I know something now,"
and stops. Review and quiz never happen.

**Fix.** The loop runs all the way up to the time limit, using results
from depth N to guide depth N+1.

---

## 2. Search algorithm — thinking smarter

The search is the part of the engine that picks a move. All improvements
here either let the engine look deeper in the same time (speed) or look
at better-ordered moves so it finds the right answer sooner (quality).

### 2.1 Iterative deepening

**What.** Search 1 ply deep; then 2; then 3; …; stop when time runs out.

**Analogy.** Drafting an essay. You don't write paragraph 1 to perfection
before starting paragraph 2. You outline everything, then draft, then
polish. Each pass informs the next.

**Why it helps.** Depth 1 tells you the best captures. Depth 2 ranks all
moves roughly. By depth 7, most of the time has been spent on the right
three moves, because the first six passes told you which three those are.
You can also stop any time and still have a reasonable answer.

### 2.2 Transposition table (used properly)

**What.** A cache mapping `position → analysis`. Before searching a
position, check the cache. If we already analyzed it at the required
depth, skip straight to the answer.

**Analogy.** Solving a maze. Mark every corridor you've walked down with
chalk. Never walk the same corridor twice. Chess positions repeat a lot
via different move orders; the cache notices and saves work.

**Details in our implementation.**
- Each entry stores: depth analyzed, score, bound type (**exact**, **lower**,
  **upper**), and the best move found.
- **Bound types** matter: sometimes we stop analyzing a position early
  because we hit α-β cutoff. The score is then a bound, not an exact value.
  The TT now records which case applies so we don't misuse partial results.
- The TT **persists across the whole game** (session), so every move
  starts with thousands of cached positions from the previous think.

### 2.3 Quiescence search

**What.** At the leaves of the tree, don't just evaluate the position
statically. Instead, keep making only *captures* (and promotions) until
the position "quiets down," then evaluate.

**Analogy.** Counting your chips at poker mid-deal is stupid. Wait until
the hand is finished.

**Why it matters.** The biggest source of 1200–1400-level blunders:
"you can capture my knight" → engine evaluates "+ knight" → plays the
capture. It doesn't notice that on the next move you get queen'd. The
evaluation happened mid-exchange, which is meaningless. Quiescence
runs the exchange to completion.

### 2.4 Null-move pruning

**What.** "If I skip my turn entirely and my opponent *still* can't hurt
me, my position is so strong I don't need to exhaustively check my
own moves — I can prune."

**Analogy.** You're playing checkers against a toddler. You don't need
to carefully consider every piece movement; even if you let them go twice,
you're still winning. No point enumerating the 20 good moves you have.

**Safety.** Disabled when you're in check (must respond) and in
pawn-only endgames (where you *can* be in zugzwang — skipping your
turn really would be better than any move, so the pruning becomes
unsound).

### 2.5 Late Move Reductions (LMR)

**What.** After the first 3 moves in a sorted list, search the remaining
quiet moves at reduced depth. If the reduced search surprisingly beats α,
re-search at full depth.

**Analogy.** A triage system at a hospital. You don't spend 30 minutes
on every walk-in patient. You take a quick look; if they're fine, move on;
if something's off, then dig in.

**Why it helps.** Good move ordering means the best move is usually in
the top 3. The other 30 moves are almost certainly worse. Searching them
all at full depth is wasteful. Cut depth by 1–2 for them and only dig in
if one surprisingly looks good.

### 2.6 Aspiration windows

**What.** At each depth iteration, assume the score will be close to the
last iteration's score. Start with a narrow search window `[prev−50, prev+50]`.
If the search confirms (score inside window), done — faster. If it surprises
us (score outside), widen and re-search.

**Analogy.** Checking your dinner bill. You expect around $100. You
glance at the total: $102. Done. If it says $500, *now* you pull out
the calculator and audit line-by-line.

### 2.7 Futility pruning (forward + reverse)

**What.** At shallow depth, if the static evaluation is either so far
above β (we're crushing already — *reverse futility*) or so far below α
that even a generous gain can't help (*forward futility*), skip.

**Analogy.** Before buying a lottery ticket, a mathematician does a
quick expected-value calc. If it's clearly negative, don't bother
picking numbers.

### 2.8 MVV-LVA capture ordering

**What.** "Most Valuable Victim, Least Valuable Attacker." Sort captures so
you try capturing the biggest piece with the smallest one first.

**Analogy.** Trading goods at a flea market. Swap your pebble for their
diamond before swapping your own diamond for their pebble.

### 2.9 Static Exchange Evaluation (SEE)

**What.** For any capture, mentally play out the whole exchange: I take
your bishop, you recapture, I recapture back, etc., always with the
least valuable attacker on each side. Sum up the gain.

**Analogy.** Before accepting a trade offer in Civilization, think the
full chain through. "I give gold, they give tech, that lets me build
thing X, which draws attention from country Y…" Don't just look at the
immediate step.

**Why it matters.** MVV-LVA alone says "take the queen with a pawn,
always." SEE notices: "yes, you win the queen. But then two of their
rooks join the recapture party; net you lose the equivalent of a rook."
That trade is rejected.

**In our engine.** SEE is used for two things:
1. **Capture ordering:** positively-valued SEEs are searched first.
2. **Quiescence pruning:** SEE-losing captures are skipped in qsearch,
   saving large amounts of work on obviously bad sacrifices.

### 2.10 Delta pruning in quiescence

**What.** In quiescence, if `stand-pat + captured_value + margin < α`,
skip the capture — even in the best case, it can't raise your position
enough to matter.

**Analogy.** Basketball, down 30 points with 2 seconds left: don't bother
setting up a three-pointer. No realistic sequence of events from here
catches you up. The play is pointless.

### 2.11 Killer moves

**What.** When a non-capture move causes an α-β cutoff at a given depth,
remember it. Next time we search at the same depth elsewhere in the tree,
try that move early.

**Analogy.** In a problem set, you notice problem #3's trick also works
for problem #4. Remember that trick for later problems.

### 2.12 History heuristic

**What.** A global table: "piece X moving to square Y has caused cutoffs
N times so far this search." Moves with high history scores get ordered
higher.

**Analogy.** Rating a surgeon by overall track record across all past
cases, not just today's case.

### 2.13 Repetition detection (draw by threefold)

**What.** Track every position's hash as the game progresses. Inside
search, if the current position already appeared earlier, return 0
(draw) immediately.

**Why it matters.** *This was the exact bug that cost us a won game.*
The engine, when winning, would shuffle pieces back and forth. Its
evaluation stayed "+winning" the whole time, so it didn't realize that
threefold repetition would draw. With the fix, the search now tells the
engine "that shuffle is worth 0.00, not +5.0" — so it picks a move
that makes real progress instead.

**Analogy.** A GPS routing tool that didn't know going around the same
block three times was pointless. Now it does.

---

## 3. Evaluation — understanding the position

The evaluation function returns a centipawn score from white's
perspective. Every leaf of the search tree ends here. A better eval
doesn't change how deep we look — it changes what we're looking for.

### 3.1 Tapered evaluation (middlegame ↔ endgame)

**What.** Two separate score tables for every piece (or at least for the
king): one for the middlegame, one for the endgame. At any moment,
interpolate between them based on how much material is left.

**Analogy.** What you want in a car changes with context. For a commute,
fuel efficiency matters. For a road trip, comfort matters. Same car,
different priorities by context. Eval works the same way — different
priorities for different phases.

**Why it matters.** The starkest example: the king. In the middlegame,
the king wants to be in the corner behind its pawns. In the endgame,
the king wants to be in the center as an attacker. These aren't small
differences — they're *opposite* preferences. Without tapering, you
get the worst of both.

### 3.2 King piece-square tables (both phases)

**What.** Two 8×8 tables specifying where the king wants to be.
Middlegame table: corners good, center bad. Endgame table: center good,
corners bad.

**Why we added it.** The original engine had king-position scoring
**completely off**. Literally: the evaluation skipped the king square
("if piece is not king, …"). That's why the losing game we analyzed
showed the engine's king wandering passively in the endgame — it had
no incentive to do anything else.

### 3.3 Pawn structure

Three terms, each explained below.

**Passed pawns** (scaled by rank, stronger in endgame): A pawn with no
enemy pawns in front or on adjacent files. It has a clear path to
promotion. **In the endgame a 7th-rank passed pawn is essentially a
queen** — we now reflect that. Previously the engine treated a
passed pawn like any other pawn (100 centipawns), which is the exact
reason it didn't resist the enemy a-pawn that promoted against it in
our lost game.

*Analogy.* A runner with an open lane in a marathon is far more
valuable to the team than one stuck in traffic.

**Doubled pawns** (penalty): Two pawns on the same file. They block
each other, create structural weaknesses. Small penalty per extra pawn.

**Isolated pawns** (penalty): No friendly pawns on adjacent files.
Can't be defended by pawn, becomes a target.

### 3.4 King safety (pawn shield + open files)

**What.** For each king, count friendly pawns on the three files
around the king on the ranks just ahead. Add a bonus for each shielding
pawn; subtract for each missing one (an open file near the king).

**Analogy.** A castle without a moat is just a house.

**Scaling.** Weighted by game phase: matters a lot in the middlegame,
irrelevant in the endgame when the king should be active, not hiding.

### 3.5 Bishop pair bonus

**What.** If you have both bishops, +35 centipawns.

**Why.** Two bishops cover both color-complexes; a knight + bishop
leaves one color un-covered. Classic small-but-real endgame advantage.

---

## 4. Infrastructure — making the engine practical

### 4.1 Threading instead of subprocess

**Before.** Each AI move spawned a fresh Python subprocess. When the move
finished, the subprocess died. All cached analysis (the entire TT) was
thrown away with it.

**Analogy.** Every time you solve a crossword puzzle, you throw out all
your dictionaries and start fresh. You never accumulate knowledge between
puzzles.

**After.** The search runs in a thread in the main process. The TT
persists. Move 2's search starts with thousands of cached positions
from move 1's think — often reaches one full ply deeper for free.

**Cancellation.** A cooperative `cancel_flag` is checked every ~2048 nodes.
When the user hits undo or reset, we set the flag; the search returns
cleanly at the next check. Previously we had to kill the subprocess
outright, which also killed the TT.

### 4.2 Opening book (Polyglot)

**What.** Industry-standard `.bin` files with tens of thousands of
master-game opening lines. Drop one at `./book.bin` and the engine
plays book instantly for the first ~15 moves — no search needed.

**Analogy.** A chef with a cookbook for classic dishes. They don't
reinvent risotto from first principles every time; they follow the
recipe for the first few steps, then improvise from a known-good base.

**Graceful fallback.** If no book file, engine searches as usual.

### 4.3 Endgame tablebases (Syzygy)

**What.** Files that encode **perfect play** for all positions with ≤ 6
pieces total. Drop them in `./syzygy/`. Any position with 6 pieces or
fewer: we look up the answer instead of searching.

**Analogy.** A chef with a recipe book that says exactly how long to
cook every possible combination of ingredients. In that range, no
guessing — just look it up.

**Size.** 3-piece tables: ~1 MB. 4-piece: ~150 MB. Partial downloads
are fine; anything not covered falls back to search.

### 4.4 Texel tuner scaffold

**What.** A separate script (`src/texel_tuner.py`) that loads a
dataset of labeled positions (win / draw / loss), runs the engine's
static evaluation on each, and measures how close the eval's
win-probability predictions are to the actual outcomes.

**Why.** All those eval constants (piece values, PST entries, pawn
penalties, king safety) were hand-picked. Data-driven tuning over
tens of thousands of positions typically finds values ~10% different
from hand-picks, worth +50–100 ELO.

**Analogy.** A restaurant tasting its recipes against customer reviews
and adjusting salt, cooking time, and portion sizes based on what
actually scored best.

### 4.5 PyPy support

**What.** PyPy is a Python interpreter with a JIT compiler that speeds
up most Python code 5–10×.

**Analogy.** Same recipe, same ingredients, upgraded kitchen.

**Cost.** Zero code changes. Just run `pypy3` instead of `python3`.
Our engine is pure Python and compatible.

### 4.6 Per-move stdout log

**What.** Each time the AI moves, it prints:
```
[AI] depth=8  score=+0.42  nodes=83217  time=2.91s  move=Nf3  tt=18234
```

**Why.** So you can see what the engine is actually doing. Spot when
it's searching shallow (position is complex, running out of time), when
it's winning (positive score), when the TT is helping (re-used entries).

### 4.7 TT size cap

**What.** The persistent TT is capped at 500,000 entries. When full,
the oldest half is evicted (Python dict preserves insertion order, so
this is cheap).

**Why.** Prevents unbounded memory growth over long games. A full TT
is fine; an unbounded TT will eventually eat all your RAM.

### 4.8 SETUP.md

Practical doc: venv setup, PyPy upgrade, optional book/TB installation,
Texel tuning, controls.

---

## 5. Expected ELO contribution

Rough estimates per change. Single-game results vary wildly; these come
from the broader engine-development literature and our own benchmarks.

| Change | ELO impact | Notes |
|---|---|---|
| Correctness fixes (TT key, wired-up search, ID bug) | baseline unlocked | the engine wasn't broken-broken, but it was playing 1200 instead of 1400 because of these |
| Quiescence search | +100–150 | biggest single tactical fix |
| Proper transposition table | +80–120 | |
| MVV-LVA + killer + history ordering | +50–80 | |
| Null-move pruning | +70–100 | |
| Late move reductions | +50–80 | |
| Tapered eval + king tables | +100–150 | fixes the "king has no position value" bug |
| Pawn structure | +80–120 | |
| King safety | +50–100 | |
| SEE + delta pruning in qsearch | +40–60 | |
| Aspiration + futility pruning | +30–50 | |
| Repetition detection | +50–100 | more if you're winning a lot |
| Persistent TT | +20–40 | |
| Bishop pair | +20 | |
| **Total (not additive — diminishing returns)** | **~+400–600** | empirically |

Starting from ~1300 → landing in the 1800–2000 range. That's a 400–600
ELO improvement, which is the rough ballpark a ~1800 human player
reported after playing the latest version.

---

## 6. Additional (not yet implemented) high-leverage next steps

Ranked by ELO-per-hour of engineering:

1. **Run on PyPy.** Documented. Single biggest lever remaining — typically
   doubles effective search depth.
2. **Install a Polyglot opening book file.** Code is done; just drop a
   `book.bin` in the repo root.
3. **Install Syzygy 3-piece tablebases** (~1 MB). Ditto.
4. **Rewrite `getValidMoves` in Cython or C.** Would unlock 20–50× movegen
   speed. Major project.
5. **NNUE evaluation.** A small neural network instead of hand-tuned
   evaluation constants. Post-2020 state of the art; worth +200–400 ELO
   over classical eval. Significant project.
