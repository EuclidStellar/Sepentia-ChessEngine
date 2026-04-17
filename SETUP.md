# Sepentia setup

## Quick start (CPython)

```bash
python3 -m venv .venv
.venv/bin/pip install pygame-ce python-chess
.venv/bin/python src/chessmain.py
```

Must be run from the project root so the `images/` directory resolves.

## PyPy for 5–10× speedup (recommended)

The engine is pure Python. Running it on PyPy's JIT typically doubles or
triples the effective search depth at the same time budget — the single
highest-leverage change you can make without editing code.

```bash
# macOS
brew install pypy3
# Linux (Debian/Ubuntu)
sudo apt install pypy3 pypy3-venv

pypy3 -m venv .venv-pypy
.venv-pypy/bin/pip install pygame-ce python-chess
.venv-pypy/bin/python src/chessmain.py
```

Both `pygame-ce` and `python-chess` support PyPy3. If `pip install pygame-ce`
fails on PyPy, try `pygame` (classic) instead — it also works.

## Optional: opening book (Polyglot)

Drop a `.bin` Polyglot book at the project root as `book.bin`, or point
`SEPENTIA_BOOK` at it:

```bash
export SEPENTIA_BOOK=/path/to/book.bin
```

Free books:
- https://github.com/official-stockfish/books — many options
- https://sourceforge.net/projects/codekiddy-chess/files/ — Performance.bin is popular

With a book loaded, the engine plays book moves instantly for the first
10–20 plies of theory rather than searching.

## Optional: Syzygy endgame tablebases

Extract `.rtbw` / `.rtbz` files to `./syzygy/` or point `SEPENTIA_SYZYGY`
at the directory:

```bash
mkdir -p syzygy
# Put 3-piece TBs in there (tiny — KPvK, KNvK, KBvK, KQvK, KRvK).
# Full download: https://syzygy-tables.info/
export SEPENTIA_SYZYGY=$(pwd)/syzygy
```

3-piece tables are ~1 MB total. 4-piece tables are ~150 MB. 5-piece are
~1 GB. 6-piece are ~150 GB (overkill). With TBs loaded, the engine plays
**perfectly** in positions with ≤ N pieces (however many you have).

The engine falls back to its own search when the TB doesn't cover the
position, so partial downloads are fine.

## Optional: Texel eval tuning

```bash
# Grab a labeled dataset, for example:
curl -O https://bitbucket.org/zurichess/tuner/downloads/quiet-labeled.v7.epd.zip
unzip quiet-labeled.v7.epd.zip

.venv/bin/python src/texel_tuner.py quiet-labeled.v7.epd 5000
```

The tuner reports the optimal K (eval-to-win-probability scaling) and the
current eval's loss. Use it as a regression metric: perturb constants in
`src/ChessAI.py`, re-run, keep changes that reduce loss.

## Controls

- Click piece, click destination — make a move
- `z` — undo
- `r` — reset

By default you play white (see `src/chessmain.py` lines `player_one` and
`player_two`). Set both to `False` for AI vs AI.
