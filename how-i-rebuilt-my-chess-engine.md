# How I Rebuilt My 2-Year-Old Chess Engine — and Moved It to the Web

Two years ago, I shipped a chess engine. I don't really remember shipping it. I remember starting it — the thrill of piecing together move generation, the pain of tracking down pin-detection bugs, the satisfaction of the AI finally beating me. Then I slapped a README on it, pushed the last commit, and moved on.

Last week I opened the repo. This is what `git log` said:

```
daef42b  Update README.md       2 years ago
f1d9d6b  Update README.md       2 years ago
bd61ee7  typo corrected         2 years ago
17025bf  Readme Refined         2 years ago
```

The last *actual* change was a README tweak. The engine itself hadn't been touched in years. It was a depth-4 search with a material-only evaluation, running in a `pygame` window on my laptop. A human rated around 1400 could beat it.

This is the story of bringing it back. Fixing the bugs. Making it actually think. And then — the interesting part — getting it off my laptop and into a browser that anyone can open.

No new hardware. No rewrite in Rust. Just better thinking about what the code should be doing, and a runtime change that did a lot of the heavy lifting for free.

---

## What the engine was

A chess engine has two parts. A **search** that looks several moves ahead, and an **evaluation** that scores a position when the search stops. My old engine had both, and both were broken in subtle ways.

The search was pure negamax with alpha-beta pruning — the standard recipe from 1970s chess programming. Depth was hardcoded to **4 plies** (2 of my moves + 2 of the opponent's). No iterative deepening. No quiescence search. No working transposition table.

Well — the code *had* a transposition table. A cache that says "I already analyzed this position, here's the answer." But the game loop called the wrong search function and never used the cache. The TT sat there, fully implemented, completely dead. The engine was re-analyzing identical positions thousands of times per move.

The evaluation was worse. It added up piece values (queen = 929, pawn = 100) plus a small positional bonus per square. **The king's position contributed zero to the score.** Zero. The engine literally couldn't tell whether its king was safely castled or wandering into the opponent's artillery.

The result: ~1400 ELO, mediocre tactics, terrible endgames, and a pygame window that froze solid for 5–10 seconds per move.

---

## First, the bugs

Before making anything *better*, I had to fix what was **wrong**.

### The transposition table was silently corrupt

The cache used a key to identify positions. The key was just the piece layout on the board. Nothing else. Not whose turn it was. Not whether you could still castle. Not en-passant possibilities.

Imagine a library indexed by book titles, ignoring edition and language. You ask for *War and Peace*. You get back the French children's abridged audiobook edition. Sometimes you get the one you wanted. Sometimes you don't.

That was the engine, consulting its own memory, occasionally retrieving a completely different position's analysis and then playing the recommended move for that other position.

Fix: the key now includes side-to-move, all castling rights, and the en-passant target. Correct lookups. It's not a speed fix — the engine was lying to itself before.

### The iterative deepening loop ran exactly once

Iterative deepening means: search 1 ply deep, then 2, then 3, then 4 — each pass using information from the previous one to order moves better. The loop existed. It looked right at a glance. But the exit condition was "if we found a move, break" — which is true at every depth ≥ 1. So the loop always ran exactly one iteration.

A student opens their textbook, reads one page, thinks "I know something now," closes the book. That was my engine, preparing for every move.

### The right search function was never called

Two search functions existed in the code: one with the transposition table, one without. The game loop called the one without. The cached, smarter version was unreachable dead code.

Two chefs in a restaurant: one experienced, one on day one. The manager only ever sends orders to the new chef. The experienced one stands at the window reading a book.

---

## Making it think smarter

Once the foundations worked, I stacked on the standard modern search tricks. None of these are original — they're all in chess-programming textbooks. All are free ELO if you put in the time.

### Quiescence search — "don't evaluate mid-punch"

The biggest source of 1400-level blunders: the engine captures your knight → its evaluation says "+knight" → plays the move. But it never looks one move further to notice you queen'd it.

Fix: at leaf nodes, keep searching **captures only** until the position is "quiet" (no more captures available). *Then* score it. Don't stop in the middle of a trade.

Counting your chips at poker while the dealer is still sliding cards is meaningless. Wait until the hand is over.

### Transposition table done right

Even after fixing the key: the old TT only stored raw scores. Modern engines store a **bound type** along with the score — is this the exact value, an upper bound, or a lower bound? Bounds let you prune harder.

Plus: when looking up a position, the TT now returns the best move that worked last time. The search tries that move first. If that move causes an alpha-beta cutoff, we skip the other 30 candidate moves entirely. One good guess eliminates 95% of the work.

### Null-move pruning — "what if I skip my turn?"

If I skip my turn and my opponent *still* can't hurt me, my position is so strong that I don't need to exhaustively evaluate every candidate move of my own. Prune.

You're playing checkers against a toddler. You don't carefully think through 30 options. Even if the toddler got a free extra move, you'd still win. No need to agonize.

(Safety: this doesn't work when you're in check, or in pawn-only endgames where zugzwang matters — skipping your turn might genuinely be your best option in those cases. Both are disabled in those cases.)

### Late Move Reductions (LMR)

Move ordering puts the best guesses first. After the first three moves at any node, the remaining 30 moves are almost certainly worse. Instead of searching them at full depth, search them at reduced depth. If one surprisingly looks better than expected, re-search it at full depth.

Triage at a hospital. Don't spend 30 minutes on every walk-in. Quick look; if they're fine, move on; if something's off, *then* dig in.

### MVV-LVA and SEE — smarter capture ordering

**MVV-LVA**: Most Valuable Victim, Least Valuable Attacker. Try capturing the queen with a pawn before capturing the pawn with the queen. Obvious in retrospect — the old engine didn't do it.

**SEE** (Static Exchange Evaluation): before even *ordering* or *searching* a capture, mentally play out the entire exchange. "I take your bishop → you recapture → I recapture back → you take my rook → I take your queen." Sum it up. If the net is negative (I lose material overall), don't even bother searching that line in quiescence.

Before accepting a trade offer in a board game, think the chain through. Don't just look at the first step.

### Killer moves and the history heuristic

**Killer moves**: when a quiet (non-capture) move causes a cutoff at some search depth, remember it. Next time we hit the same depth elsewhere, try that move early.

**History heuristic**: more general. Keep a running count of how often "piece X to square Y" has caused cutoffs anywhere in the search. Use it to order moves we haven't seen specifically.

On a problem set, you notice that a certain trick solves problem #3. Try it on problem #4 first. And remember it for future problems.

### Aspiration windows

After each iteration of iterative deepening, you have a pretty good guess for the final score. Next iteration, start with a narrow search window (last score ± 50 centipawns). If the search confirms "yeah, roughly that score," you're done — narrow windows are faster. If the score turns out to be wildly different, widen and re-search.

Checking your dinner bill. You expect $100. Glance: $102. Done. If it says $500, *then* you pull out the calculator and audit.

### Futility pruning

At shallow depth, if the static evaluation plus a generous gain can't even reach the alpha threshold, skip. It's hopeless.

Before buying a lottery ticket, a mathematician checks the expected value. If it's clearly negative, don't bother picking numbers.

### Repetition detection — the bug that lost me a game

Chess has a draw rule: if the same position appears three times, the game is a draw. The old engine didn't know this. It evaluated a position as "+5 (winning)", shuffled pieces back and forth, and happily drew a game it should have won.

Fix: maintain a list of every position seen in the actual game. Inside the search, if we reach a position that's already been seen, return 0 (draw) immediately. Now, when the engine is winning, it correctly prefers any move that makes real progress over a repeat.

---

## Making it *understand* chess better

The evaluation function is the engine's taste. Every leaf of the search tree ends here. Better evaluation = better moves, with or without deeper search.

### Tapered evaluation — the king wants two different things

What a king wants changes with the game. In the middlegame: hide in the corner behind pawns. In the endgame: stride into the center and fight.

These aren't small differences. They're *opposite* preferences. The same table of "where the king wants to be" can't work for both phases. So I use two tables — one for middlegame, one for endgame — and interpolate between them based on how much material is left on the board.

What you want in a car changes with context. Commute = fuel efficiency. Road trip = comfort. Same car, different priorities per context.

### King piece-square tables

Two 8x8 tables telling the king where to stand. Middlegame: corners good, center bad. Endgame: the opposite. The old engine **skipped the king entirely** in its position evaluation — literally zero positional awareness for the most important piece on the board.

### Passed, doubled, isolated pawns

A pawn with no enemy pawns blocking its march to promotion is a **passed pawn**. In the endgame, one on the 7th rank is worth roughly a queen. The old engine valued every pawn at 100 centipawns. Passed, blocked, doubled, whatever. All the same.

Fix: passed-pawn bonus scaled by rank (higher rank = bigger bonus) and by game phase (endgame = bigger bonus). Plus penalties for **doubled pawns** (two on the same file, structurally weak) and **isolated pawns** (no friendly pawns on adjacent files, hard to defend).

This single change fixed the most embarrassing loss I'd had with the old engine: the opponent's a-pawn walked all the way down the board to promote, and the old engine had absolutely zero idea this was dangerous until it was a queen.

### King safety

Pawn shield scoring: count friendly pawns on the three files in front of the king. Bonus for each one present. Penalty for each missing one (open files near the king = tactical vulnerability).

A castle without a moat is just a house.

Scaled by game phase: huge in the middlegame, irrelevant in the endgame when the king should be active.

### Bishop pair

Two bishops cover both the light and dark squares; a bishop + knight leaves one color uncovered. Small but real endgame advantage. +35 centipawns if you have both.

---

## Then I moved it to the web

The Python version lived in a pygame window on my laptop. Anyone who wanted to play it had to clone my repo, install Python 3, install `pygame`, and run a script. Essentially: nobody would ever play it.

I rewrote the entire engine in TypeScript. React for the UI. Vite for bundling. Now you open a URL — no install, works on any device with a browser.

Here's what that actually changed.

### Same algorithm, different language

The TypeScript port is faithful. Same search, same evaluation, same pruning thresholds, same tuning constants. Same *strength* of play. The only things missing from the web version are features that depend on local files (opening books, endgame tablebases) — the browser can't read arbitrary disk files.

I want to be honest about this because it matters for the story: **moving to the web did not make the algorithms smarter.** They're literally the same algorithms. What changed was the runtime underneath them, and that's where the speed came from.

### What actually made it fast: V8's JIT

I initially thought the speed gain would come from JavaScript being "closer to the metal" than Python. That's not the real story.

The real story is **V8** — the JavaScript engine inside Chrome, Node, Edge, and every modern browser.

V8 is a **JIT (just-in-time) compiler**. When it sees a loop run thousands of times — like the `_negamax` function during a chess search — it *compiles that loop to native CPU machine code*, specialized to the types it has actually observed.

CPython, by contrast, is an **interpreter**. For every single Python operation — adding two numbers, reading a variable, accessing a list element — the interpreter does a big lookup dance: fetch bytecode, jump to a handler, bump reference counts, check types. It's hundreds of CPU instructions for what should be one.

Analogy:
- **CPython** is a factory worker who reads the blueprint from scratch for every single widget. One widget at a time, always fresh.
- **V8** is the same worker, but after building 1,000 identical widgets, they construct a **jig** — a specialized tool tuned for this exact widget shape. From then on, each widget takes 10% of the time.

Chess search is V8's ideal workload. One hot function (`_negamax`) called millions of times. Types don't change — the board is always 8x8 of strings, depth is always an integer. By the time you're half a second into a search, V8 has largely replaced its interpreter with native machine code specialized to *our specific code*.

Result: the web version reaches **deeper search depth** than the Python version at the same wall-clock budget. Not because the algorithm is better — it's identical — but because the runtime isn't wasting 90% of the CPU's capacity on interpreter bookkeeping.

**Did we do any CPU optimization?** No. We didn't touch anything CPU-specific. No SIMD, no cache-aligned structures, no hand-tuned loops. We just chose a better runtime, and V8 optimizes the CPU for us.

### TypeScript is a bonus, not a source of speed

TypeScript doesn't run in the browser. It compiles *to* JavaScript before being served. So TypeScript adds no runtime speed — it adds type safety during development, which caught maybe 10 bugs during the port that would have been runtime errors in plain JS. The speed is purely V8's doing.

### Web Workers — responsiveness, not speed

Here's a common confusion worth unpacking carefully, because I was confused about it too.

**A Web Worker does not make code run faster.** It runs code on a separate thread so the UI stays responsive.

Without a worker: when the AI starts thinking, the whole page freezes. The chessboard locks up. Clicks don't register. Animations stop. The user stares at a frozen screen for 3 seconds.

With a worker: the AI search runs on its own OS thread. The main thread keeps rendering the UI at 60 frames per second. You can see the board, click buttons, cancel the search mid-thinking. The AI does *exactly the same amount of work either way.* Same depth, same nodes, same time. It's not faster.

Analogy: you're cooking dinner AND answering the doorbell.
- Without a helper, you have to choose. Either the food burns, or the guest waits on the porch.
- With a helper who handles the stove, both things happen smoothly. The food doesn't cook faster. The doorbell just doesn't have to wait.

That's the Web Worker. It doesn't cook faster. It unblocks the door.

### What else the web version has

A live info panel showing depth reached, score, nodes searched, and best move — updated every iteration of the search. The Python version printed these to stdout; in the browser they're right next to the board, updating in real time as the engine thinks.

Legal-move highlighting (click a piece, see where it can go). Adjustable think-time slider from 0.5 to 10 seconds. Undo and reset buttons. Works on phone, tablet, laptop.

Build pipeline: Vite. A push to `main` triggers GitHub Actions, which builds `web/dist/` and publishes it to GitHub Pages. Every commit is automatically a new version on the internet.

### What the web version doesn't have (yet)

- **Opening book** — browsers can't read arbitrary disk files. Could be bundled as a static asset later.
- **Endgame tablebases** — same reason.
- **Multi-core parallel search** — Web Workers run on one core each. The one running the AI is fully utilized; the other 7 cores on your laptop are still idle. Could be added with `SharedArrayBuffer` and multiple workers sharing a transposition table — that's a real project, not a quick fix.
- **Persistence across page reloads** — the transposition table is in-memory. Close the tab, lose the cache. Could add `localStorage` serialization if it mattered.

---

## The numbers

Before (the 2-year-old desktop version) vs. after (the web version), at the same 3-second time budget:

|  | 2-year-old desktop engine | Current web engine |
|---|---|---|
| Language | Python (CPython interpreter) | TypeScript (V8 JIT) |
| Runtime speed | ~10–30K nodes/sec | ~100–500K nodes/sec |
| Search depth — opening | 4 (fixed) | 7–9 |
| Search depth — middlegame | 4 | 7–8 |
| Search depth — endgame | ~5 | 11–14 |
| Transposition table | existed but unused | persistent across moves |
| Quiescence search | no | yes (+ up to 6 extra plies) |
| Iterative deepening | broken (ran once) | working |
| Null-move pruning | no | yes |
| Late move reductions | no | yes |
| SEE capture ordering | no | yes |
| Killer + history heuristic | no | yes |
| Aspiration windows | no | yes |
| Futility pruning | no | yes |
| Repetition detection | no (cost me a game) | yes |
| King position in eval | skipped entirely | tapered middlegame + endgame tables |
| Passed pawn awareness | no | yes (scaled by rank + phase) |
| King safety | no | pawn-shield + open-file scoring |
| Bishop pair bonus | no | yes |
| UI during think | frozen pygame | smooth 60 fps (worker) |
| To play | clone repo, install Python, install pygame | open URL |
| Estimated ELO | ~1300 | ~1800–2000 |

---

## What I didn't do

Being honest about the ceiling. I didn't:

- Write any SIMD or hand-tune any CPU-specific code
- Use multi-threading for actual parallel search (one core busy, seven idle)
- Implement Zobrist hashing for the transposition table
- Rewrite move generation using bitboards
- Train a neural-network evaluation (NNUE — Stockfish's current secret sauce)

Each of those would be another real project. Stacked, they'd push the engine into modern open-source territory. But for a personal project running in a browser and giving my 1800-rated friend a tough game, I called it done.

---

## Lessons

**Correctness before optimization.** The first things I fixed weren't slow code — they were *wrong* code hiding as slow code. The TT silently returned analyses for different positions. The iterative deepening loop never actually iterated. No amount of tuning could fix these; they had to be recognized and rewritten.

**Algorithms beat language choice, until they don't.** Everything from quiescence through LMR is language-neutral. Porting them to TypeScript doesn't improve the algorithm — the algorithm is the same. But *once the algorithms are right*, the runtime starts mattering: V8's JIT gave another 5–10× on top of the algorithmic work, essentially for free.

**Web Workers aren't the magic.** They solved a UX problem (frozen UI), not a performance problem. Conflating the two leads to cargo-cult thinking — "I'll add more workers to make it faster." You won't. You'll just split the same work across more threads, not do more of it.

**A 2-year-old side project is not a write-off.** The hardest part was understanding what I'd built. Once I had that, most of the wins came from stacking well-known techniques that existed in textbooks the whole time.

Two years of nothing. A week of focused work. +400–600 ELO. A version anyone with a URL can play.

That's the story.
