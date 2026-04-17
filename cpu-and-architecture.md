# Sepentia — CPU performance and architecture

> What the CPU is actually doing when the engine thinks, how runtimes
> change that picture, what Lazy SMP is, and how the engine is wired
> together today.

Written in the same plain-language style as `improvements.md` and
`before-and-after.md`, with analogies.

---

## 1. The CPU, briefly

A modern CPU is not one worker — it's a small factory. Every name in
this table matters for what the chess engine can or can't do.

| Piece | What it does | Analogy |
|---|---|---|
| **Clock** | heartbeat (~3–4 GHz = 3 × 10⁹ cycles/sec/core) | the factory's shift bell |
| **Cores** | independent workers (4–12 on a typical laptop) | separate assembly lines |
| **Pipeline** | a single core's assembly line (~15–20 stages deep) | many hands on one line |
| **Branch predictor** | guesses which way an `if` will go before knowing | the foreman who pre-stages parts |
| **Out-of-order execution** | re-orders independent instructions to fill idle slots | moving ahead while you wait for a part |
| **L1 / L2 / L3 cache** | tiny-but-fast memory next to the core | hands, shelves, back room |
| **RAM** | big-but-slow memory | off-site warehouse |
| **ALU** (arithmetic logic unit) | adds/subs/bitwise | the arithmetic station |
| **FPU** (floating-point unit) | decimals | the engineer's calculator |
| **SIMD / AVX** (vector) | 4–16 ops at once | a rack of synchronized stations |

A well-optimized program runs through this factory at 3–4 instructions
per clock cycle per core — hundreds of millions of useful operations
per second. Python does not.

## 2. Why Python wastes the factory

CPython (the standard Python interpreter) has a central dispatch loop.
For every operation — variable load, attribute access, integer add,
function call — the interpreter:

1. Fetches the next bytecode opcode.
2. **Jumps** (indirect branch) to its handler.
3. Does type dispatch, ref-count bumps, argument unpacking.
4. Returns to step 1.

Each of these steps is silicon poison:

- **The branch predictor thrashes.** It can't guess where step 2 will
  jump — each opcode is different. When it guesses wrong, the pipeline
  flushes and starts over. That's ~15 wasted cycles per misprediction.
- **The L1 cache thrashes.** The handlers are scattered across memory;
  every jump may miss the cache.
- **Out-of-order execution has nothing to do.** Every instruction
  depends on the opcode dispatch; nothing can run in parallel.
- **Objects are heap-allocated.** A Python int is not a register-sized
  integer; it's a pointer to an object with header, type tag, refcount.
  Every arithmetic op chases pointers.

**Analogy.** A factory where the assembly line reconfigures between
every single product. No batching, no specialization. Workers spend 90%
of their shift re-reading the blueprint instead of building.

Concretely: our Python engine does **~10,000–100,000 CPU instructions per
chess node**. A C engine does **~100**. We're at roughly **1%** of the
CPU's real throughput.

## 3. What PyPy changes at the silicon level

CPython is an **interpreter**. PyPy is a **JIT (just-in-time) compiler
runtime**. Start-up is interpreted, but once PyPy sees a loop run
thousands of times, it compiles that loop to native machine code,
specialized to the types it has actually observed.

That one change cascades all the way down.

| Behavior | CPython | PyPy (after warmup) |
|---|---|---|
| Main loop dispatch | indirect jump on every opcode | **compiled away** — just machine instructions |
| Variable access | dict lookup | direct register / stack slot |
| Integer `a + b` | ~100 CPU instructions | 1 CPU instruction |
| Branch predictor accuracy | poor on the dispatch loop | near native |
| L1 cache hit rate | poor (scattered objects) | much better |
| Out-of-order execution | underutilized | actually used |
| Allocation pressure | one `PyObject` per int | escape-analysis often keeps values in registers |

### Why chess is PyPy's ideal workload

- **Hot**: one function (`_negamax`) is called millions of times.
- **Type-stable**: `board` is always the same shape; `depth` is always
  an int.
- **Small**: the hot inner loop fits in the JIT's compilation budget.
- **Allocation-light after tracing**: PyPy often keeps loop variables in
  registers.

**Typical speedup on chess engines**: **5–10×**, sometimes 15–20× on
move-generation loops.

**Cost**: warmup. The first 200–500 ms of a search are still
interpreted while PyPy decides what to compile. By second 1 you're at
JIT speed. For our 5-second time budget, warmup is noise.

### Analogy

- CPython: a worker reading the blueprint from scratch for every widget.
- PyPy: the same worker, but after seeing 1,000 identical widgets,
  they build a **jig**. From then on, same widget in 10% of the time —
  but they needed enough repetitions to justify building the jig.

### Does it actually change the CPU cycles?

Yes, and dramatically. Per-node cost drops from ~100,000 cycles to
maybe ~10,000. Same silicon. Same clock. Same memory. The pipeline
actually fills with useful work, the branch predictor starts being
right, and the cache starts being useful.

This is why the single highest-ROI lever on the whole engine is:
**`pypy3 -m venv .venv-pypy && .venv-pypy/bin/python chessmain.py`**.

Zero code changes. A factor of 5–10 in throughput. Every other
improvement we make benefits proportionally.

---

## 4. Lazy SMP — using the 7 idle cores

Right now the engine uses **1 of your 8 cores**. The others are idle
during AI think time. Converting that idleness into search speed is
the second big lever.

### Why chess is hard to parallelize correctly

The "obvious" approach — split the move list across threads, have each
thread search a subtree — runs into α-β cutoffs:

- In serial search, when move #1 causes an α-β cutoff, you throw away
  moves #2–#30. Free.
- In parallel search, if you already started 7 threads on moves #2–#8,
  **their work is wasted** the moment the cutoff happens.

Managing "start work, maybe abort" across cores cleanly is called YBWC
(Young Brothers Wait Concept). It is a PhD-thesis's worth of engineering.

### Lazy SMP: the pragmatic shortcut

The modern trick (Stockfish uses it): don't orchestrate. Just have
**every core search the same root position**, with tiny perturbations
so they naturally explore different parts of the tree, and make them
all share the transposition table.

How the cores diverge:
- Different cores start iterative deepening at different depths.
- Their move-ordering TT hits drift as they write concurrently.
- By the time they're all at depth 10, they've explored overlapping
  but not identical subtrees.
- The **shared TT** is the glue: anything one core computed, the
  others can re-use via a hash hit.

### Why it works

Chess search is not uniform. Good move ordering means 90%+ of time
goes into the first move. Threads that pick slightly different first
moves (or the same move but with different TT scoring on children)
cover more of the real tree per wall-clock second than any one thread.

**Typical speedup on 8 cores**: 3–4× (sub-linear — threads step on
each other). Not as good as 8×, but much better than 1× and almost
free to wire up.

### The Python-specific hurdle

CPython has the **GIL (Global Interpreter Lock)**: only one thread
executes Python bytecode at a time. So `threading.Thread` does **not**
actually give parallel CPU work in CPython.

Three paths:

1. **`multiprocessing`**: multiple OS processes, each with its own
   Python interpreter. Each gets its own CPU core. The TT has to be
   shared via `multiprocessing.shared_memory` or a `Manager.dict`.
   Adds inter-process-communication overhead; shared TT is tricky but
   workable.
2. **PyPy**: has experimental STM (software transactional memory)
   threads. Not mainstream; I wouldn't bet on it.
3. **C extension**: if you compile the hot path to C/Cython, you can
   release the GIL in the compiled code. Then `threading.Thread` gives
   real parallelism. This is what Stockfish-family engines do.

For our engine: **`multiprocessing` with shared TT** is the practical
path. ~200–300 lines of coordination code. Combined with PyPy (each
process is a PyPy), this is realistic engineering.

### Analogy

- CPython + single thread: one chef, one stove, one blueprint
  re-read for every dish.
- PyPy + single thread: the same chef, but now equipped with
  everything they need and working at speed.
- **Lazy SMP**: 8 chefs, but they share one pantry (the TT). They
  sometimes reach for the same ingredient (contention), but
  collectively cook way more food per hour.

---

## 5. Other CPU-level improvements, ranked

Every item here is about getting more useful work from each clock cycle.

### 5.1 Zobrist hashing (paired with PyPy)

Today `getHashKey()` builds a tuple-of-tuples every position — 64
string lookups, ~60 allocations, hash everything. It is correct but
heavy.

**Zobrist**: precompute one random 64-bit number per `(piece, square)`
pair (768 numbers total), plus a few for castling and side-to-move.
The current position's hash is the **XOR** of all its piece/square
numbers. XOR is a 1-cycle CPU op.

Even better: **incremental updates**. When a piece moves A→B:
```
hash ^= ZOBRIST[piece][A]    # remove from A
hash ^= ZOBRIST[piece][B]    # place at B
```
O(1) per move, not O(64). Per-move hash cost drops from thousands of
cycles to ~10.

**Speedup in CPython**: marginal (Python int XOR is still slow).
**Speedup in PyPy/Cython**: huge (XOR compiles to a single ADC-class
instruction). Do this *alongside* the runtime upgrade.

### 5.2 Cython / mypyc compilation

Annotate the hot paths (`_negamax`, `_quiescence`, `scoreBoard`,
`_attackers_to`, `getValidMoves`) with type info. Compile to C.
Typical result: **10–30×** on the compiled function.

Unlike PyPy, Cython output is stable machine code you can pin to
specific functions. You get native integer arithmetic, native array
indexing, no ref counts on hot variables.

Cost: a weekend of annotations + a compile step in the build.

### 5.3 Packed move encoding

A Python `Move` object is ~300 bytes (headers, attributes, refcounts).
We allocate thousands per search.

Pack it into a single 16-bit int: `from_sq<<6 | to_sq | flag_bits`.
Fits in a CPU register. No allocation. Lists of moves become packed
int arrays → cache-friendly.

**In pure CPython**: modest gain. **In Cython**: large gain (now the
compiler can keep move lists in contiguous memory).

### 5.4 Bitboard move generation

Represent each piece type as a 64-bit integer: bit N is set iff the
piece is on square N. Then:

- "where can a rook move?" = a few bitwise masks + population counts.
- "is this square attacked?" = AND with the union of all enemy
  attack masks.
- "flip side to move" = a single register flip.

The CPU's ALU does 64-bit AND / OR / XOR / POPCNT / BSF in **1 cycle**.
A rook's 4 ray directions become 4 bitwise operations instead of 32
list iterations with bounds checks.

Chess engines built around bitboards hit 10–100 M nodes/s in C. In
Python they still help because Python's big-int is backed by
C-level arrays.

**Cost**: rewrite move generation. Weeks of work. Biggest-lever
single change available, but expensive.

### 5.5 Cache-friendly TT

Python dict + tuple keys is correct but pointer-heavy. Every TT lookup
chases 3–4 pointers (dict entry → tuple key → tuple of strings → …).

A C-style TT is a **flat array of fixed-size structs**, indexed by
`hash & (size - 1)`. Lookup = one memory read. Cache line–aligned.
**Two-bucket probing** (try slot H, then H+1) handles collisions with
one extra read.

In pure Python: marginal. In Cython/C: large. Worth doing when you
compile the TT code.

### 5.6 Branch hints (Cython only)

Cython lets you annotate `if likely(...)` and `if unlikely(...)`.
The compiler emits code that matches the CPU's preferred branch
direction, so the predictor starts out right.

Minor effect (~1–2% per tagged branch). Worth it only after everything
else is compiled.

### 5.7 SIMD / AVX

Chess's classical evaluation doesn't vectorize well — it's a lot of
different, dependent lookups, not parallel arithmetic on arrays.

Where SIMD matters for chess: **NNUE** (small neural-net evaluation).
The matrix-vector product at the heart of NNUE inference is a perfect
SIMD workload. This is how Stockfish uses AVX2 and AVX-512.

**Not applicable to our current eval.** Only becomes relevant if we
move to NNUE, at which point numpy or a custom C backend with SIMD
intrinsics becomes essential.

---

## 6. Current engine architecture

### 6.1 Modules

```
src/
├── chessmain.py         UI event loop. Spawns the search thread on
│                        AI turns; handles clicks, undo, reset.
├── chessengine.py       GameState, Move, move generation, rules,
│                        check/pin detection, hash key, repetition
│                        history. The canonical "what is the position
│                        and what moves exist" module.
├── ChessAI.py           Search (negamax, quiescence, TT, ordering,
│                        null move, LMR, aspiration, futility),
│                        evaluation (tapered PST, pawn structure,
│                        king safety, bishop pair), SEE.
├── ChessBook.py         Optional Polyglot book + Syzygy tablebase
│                        integration. No-op when files absent.
├── texel_tuner.py       Standalone eval-tuning script (off the hot
│                        path — run manually on labeled datasets).
├── HighlightArea.py     UI: highlight selected and legal squares.
└── MoveLog.py           UI: right-panel move history display.
```

### 6.2 Threading model

```
    main thread                       search thread
┌────────────────────┐          ┌──────────────────────┐
│ pygame event loop  │          │ ChessAI.findBestMove │
│ render at ~15 FPS  │          │   iterative deepen   │
│ handle clicks      │          │   _negamax           │
│                    │          │   _quiescence        │
│ on AI turn:        │─spawn──→ │   write to TT        │
│   start Thread     │          │   check cancel_flag  │
│                    │          │   put move on queue  │
│ poll is_alive()    │←queue─── │                      │
│ apply AI move      │          │ (thread exits)       │
│                    │          │                      │
│ on undo/reset:     │          │                      │
│   request_cancel() │──flag──→ │   sees flag, returns │
│   join thread      │          │   (TT preserved)     │
└────────────────────┘          └──────────────────────┘

      Shared state (module-level in ChessAI):
        - transposition_table  (persists across moves)
        - cancel_flag          (main → search; GIL-safe read/write)
        - killer_moves         (reset per move)
        - history_table        (reset per move)

      Shared mutable object:
        - game_state  (search mutates via make/undo; main thread
                       doesn't touch it while search is running)
```

### 6.3 Data flow for one AI move

1. User makes a move → `chessmain.py` calls
   `game_state.makeMove(user_move)` and appends to
   `position_history`.
2. Main thread detects "AI's turn" and spawns a `Thread` running
   `ChessAI.findBestMove(game_state, valid_moves, return_queue)`.
3. Inside `findBestMove`:
   a. Reset per-move state (killer, history, cancel flag, node count).
   b. (Optional) Probe `ChessBook.book_move(...)` — if a Polyglot book
      is loaded and this position is in it, return that move.
   c. (Optional) Probe `ChessBook.tablebase_move(...)` — if Syzygy is
      loaded and piece count ≤ 6, return tablebase-optimal move.
   d. Iterative deepening: `_negamax` at depth 1, 2, 3, …, each with
      aspiration windows, stopping on time / mate / cancel.
   e. Every leaf drops into `_quiescence`.
   f. Put chosen move on the queue. Log a one-line summary.
4. Main thread polls `thread.is_alive()`; when false, `get_nowait()`
   the move, apply it, animate, re-render.
5. TT stays populated into the next move. Killer/history do not.

### 6.4 Key state objects

| Object | Location | Lifetime | Size |
|---|---|---|---|
| `GameState.board` | per-game | game | ~1 KB |
| `GameState.position_history` | per-game | game | ~10 KB |
| `GameState.move_log` | per-game | game | ~10 KB |
| `transposition_table` | `ChessAI` module | game (capped) | up to ~300 MB |
| `killer_moves`, `history_table` | `ChessAI` module | per move | < 1 MB |
| pygame surfaces, images | UI | process | ~100 MB |

### 6.5 Design choices worth calling out

- **Thread, not process, for the search worker.** The UI thread is
  mostly idle (rendering at 15 FPS, waiting for input), so the GIL
  contention is negligible. We keep the TT in-process with the UI
  and avoid IPC serialization overhead. When we go parallel with
  Lazy SMP, that changes — we'll need `multiprocessing`.
- **Cooperative cancellation**, not `Thread.terminate()` (which
  doesn't exist). The search polls a flag every 2,048 nodes. On
  abort it unwinds cleanly — TT is kept, in-flight make/undo pairs
  complete, game_state is restored.
- **All state is module-level.** Could be cleaner as an `Engine`
  class but is functionally identical and easier to reason about.
- **`queue.Queue` for result handoff.** Simpler than an Event +
  shared variable and the main loop already polls.

---

## 7. Roadmap (CPU-focused)

Ordered by ROI and effort. Cumulative gains are rough.

| Order | Change | Effort | Speedup | Cumulative |
|---|---|---|---|---|
| 1 | **Run on PyPy** | 10 min | 5–10× | 5–10× |
| 2 | **Zobrist hashing** with incremental update | half-day | 1.5–2× | 10–20× |
| 3 | **Packed move encoding** (16-bit int) | 1 day | 1.3× | 15–25× |
| 4 | **Cython-compile** `_negamax`, `_quiescence`, `scoreBoard` | weekend | 3–5× over PyPy | 50–100× |
| 5 | **Lazy SMP** via `multiprocessing` + shared TT | 3–5 days | 3–4× on 8 cores | 150–400× |
| 6 | **Bitboard movegen** rewrite | weeks | 5–10× movegen | 500–1000× |

In ELO terms, each 2× of node throughput is worth roughly +50 ELO
(diminishing returns as you get stronger). So the table above is
another **+200–400 ELO** ceiling if pursued fully. Which is NNUE
territory — at that point, the bigger gain switches from "make CPU
faster" to "replace the evaluation function with a neural net."

---

## TL;DR

- Today, the engine saturates **1 CPU core** and uses **~1% of that
  core's real throughput** because Python's interpreter dispatches
  are silicon-unfriendly.
- **PyPy** is the single biggest lever: 5–10× for free, by letting the
  CPU pipeline and cache and branch predictor actually do their jobs.
- **Lazy SMP** is the second lever: turn the 7 idle cores into another
  3–4× on top.
- The remaining levers (Zobrist, Cython, bitboards) each compound.
  Stacked, they reach ~100× node throughput without changing the
  algorithm.
- Engineering-wise, the engine is already set up to accept these:
  thread-based worker, cancel flag, persistent TT, modular book/TB
  integration, standalone tuner. Each next step plugs into the
  existing architecture.
