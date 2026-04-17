// AI search + evaluation, ported from src/ChessAI.py.
//
// Search: iterative deepening negamax with alpha-beta, aspiration windows,
// quiescence (with delta + SEE pruning), transposition table (EXACT/LOWER/
// UPPER bounds + best-move ordering), null-move pruning, late move
// reductions, reverse + forward futility pruning, MVV-LVA + SEE capture
// ordering, killer moves, and history heuristic.
//
// Evaluation: tapered (middlegame <-> endgame) piece-square tables including
// king tables, pawn structure (passed/doubled/isolated), bishop-pair bonus,
// king safety (pawn shield + open-file penalty, mg-weighted).

import { GameState, Move } from "./chessengine";
import type { Board } from "./chessengine";

export const piece_score: Record<string, number> = {
  K: 20000, Q: 929, R: 512, B: 320, N: 280, p: 100,
};

export const pawn_scores: number[][] = [
  [0, 0, 0, 0, 0, 0, 0, 0],
  [78, 83, 86, 73, 102, 82, 85, 90],
  [7, 29, 21, 44, 40, 31, 44, 7],
  [-17, 16, -2, 15, 14, 0, 15, -13],
  [-26, 3, 10, 9, 6, 1, 0, -23],
  [-22, 9, 5, -11, -10, -2, 3, -19],
  [-31, 8, -7, -37, -36, -14, 3, -31],
  [0, 0, 0, 0, 0, 0, 0, 0],
];

export const bishop_scores: number[][] = [
  [-59, -78, -82, -76, -23, -107, -37, -50],
  [-11, 20, 35, -42, -39, 31, 2, -22],
  [-9, 39, -32, 41, 52, -10, 28, -14],
  [25, 17, 20, 34, 26, 25, 15, 10],
  [13, 10, 17, 23, 17, 16, 0, 7],
  [14, 25, 24, 15, 8, 25, 20, 15],
  [19, 20, 11, 6, 7, 6, 20, 16],
  [-7, 2, -15, -12, -14, -15, -10, -10],
];

export const rook_scores: number[][] = [
  [35, 29, 33, 4, 37, 33, 56, 50],
  [55, 29, 56, 67, 55, 62, 34, 60],
  [19, 35, 28, 33, 45, 27, 25, 15],
  [0, 5, 16, 13, 18, -4, -9, -6],
  [-28, -35, -16, -21, -13, -29, -46, -30],
  [-42, -28, -42, -25, -25, -35, -26, -46],
  [-53, -38, -31, -26, -29, -43, -44, -53],
  [-30, -24, -18, 5, -2, -18, -31, -32],
];

export const queen_scores: number[][] = [
  [6, 1, -8, -104, 69, 24, 88, 26],
  [14, 32, 60, -10, 20, 76, 57, 24],
  [-2, 43, 32, 60, 72, 63, 43, 2],
  [1, -16, 22, 17, 25, 20, -13, -6],
  [-14, -15, -2, -5, -1, -10, -20, -22],
  [-30, -6, -13, -11, -16, -11, -16, -27],
  [-36, -18, 0, -19, -15, -15, -21, -38],
  [-39, -30, -31, -13, -31, -36, -34, -42],
];

export const knight_scores: number[][] = [
  [-66, -53, -75, -75, -10, -55, -58, -70],
  [-3, -6, 100, -36, 4, 62, -4, -14],
  [10, 67, 1, 74, 73, 27, 62, -2],
  [24, 24, 45, 37, 33, 41, 25, 17],
  [-1, 5, 31, 21, 22, 35, 2, 0],
  [-18, 10, 13, 22, 18, 15, 11, -14],
  [-23, -15, 2, 0, 2, 0, -23, -20],
  [-66, -53, -75, -75, -10, -55, -58, -70],
];

export const king_mg_scores: number[][] = [
  [-65, 23, 16, -15, -56, -34, 2, 13],
  [29, -1, -20, -7, -8, -4, -38, -29],
  [-9, 24, 2, -16, -20, 6, 22, -22],
  [-17, -20, -12, -27, -30, -25, -14, -36],
  [-49, -1, -27, -39, -46, -44, -33, -51],
  [-14, -14, -22, -46, -44, -30, -15, -27],
  [1, 7, -8, -64, -43, -16, 9, 8],
  [-15, 36, 12, -54, 8, -28, 24, 14],
];

export const king_eg_scores: number[][] = [
  [-74, -35, -18, -18, -11, 15, 4, -17],
  [-12, 17, 14, 17, 17, 38, 23, 11],
  [10, 17, 23, 15, 20, 45, 44, 13],
  [-8, 22, 24, 27, 26, 33, 26, 3],
  [-18, -4, 21, 24, 27, 23, 9, -11],
  [-19, -3, 11, 21, 23, 16, 7, -9],
  [-27, -11, 4, 13, 14, 4, -5, -17],
  [-53, -34, -21, -11, -28, -14, -24, -43],
];

function reverse<T>(a: T[]): T[] { return a.slice().reverse(); }

const king_mg_black = reverse(king_mg_scores);
const king_eg_black = reverse(king_eg_scores);

export const piece_position_scores: Record<string, number[][]> = {
  wN: knight_scores,
  bN: reverse(knight_scores),
  wB: bishop_scores,
  bB: reverse(bishop_scores),
  wQ: queen_scores,
  bQ: reverse(queen_scores),
  wR: rook_scores,
  bR: reverse(rook_scores),
  wp: pawn_scores,
  bp: reverse(pawn_scores),
};

export const CHECKMATE = 1_000_000;
export const STALEMATE = 0;
export const MAX_DEPTH = 64;
export const QUIESCENCE_MAX_DEPTH = 6;
export const MAX_TT_SIZE = 500_000;

const PHASE_WEIGHT: Record<string, number> = { N: 1, B: 1, R: 2, Q: 4 };
const MAX_PHASE = 24;

const PASSED_PAWN_MG = [0, 10, 15, 25, 50, 90, 160, 0];
const PASSED_PAWN_EG = [0, 20, 35, 55, 100, 170, 280, 0];
const DOUBLED_PAWN_PENALTY = 12;
const ISOLATED_PAWN_PENALTY = 15;
const BISHOP_PAIR_BONUS = 35;

const ASPIRATION_DELTA = 50;
const NULL_MOVE_R_SHALLOW = 2;
const NULL_MOVE_R_DEEP = 3;

const TT_EXACT = 0, TT_LOWER = 1, TT_UPPER = 2;

interface TTEntry {
  depth: number;
  score: number;
  flag: number;
  bestMove: Move | null;
}

export class Engine {
  // Per-game state: TT persists, killer/history reset per move.
  transposition_table: Map<string, TTEntry> = new Map();
  killer_moves: Map<number, [Move | null, Move | null]> = new Map();
  history_table: Map<string, number> = new Map();
  nodes = 0;
  searchStart = 0;
  timeLimitMs = 3000;
  timeUp = false;
  cancelFlag = false;
  nextMove: Move | null = null;
  // Progress callback (e.g. for UI): (depth, score_cp, move, nodes, timeMs)
  onIteration: ((d: number, s: number, m: Move | null, nodes: number, timeMs: number) => void) | null = null;

  requestCancel() { this.cancelFlag = true; }
  resetTT() { this.transposition_table.clear(); }

  private shouldStop(): boolean {
    return this.timeUp || this.cancelFlag;
  }

  private timeExpired(): boolean {
    return (performance.now() - this.searchStart) > this.timeLimitMs;
  }

  // ----- SEE -----
  private _attackers_to(board: Board, tr: number, tc: number, color: string): [number, number, string][] {
    const out: [number, number, string][] = [];
    // Pawn
    if (color === "w") {
      for (const dc of [-1, 1]) {
        const r = tr + 1, c = tc + dc;
        if (r >= 0 && r < 8 && c >= 0 && c < 8 && board[r][c] === "wp") out.push([r, c, "wp"]);
      }
    } else {
      for (const dc of [-1, 1]) {
        const r = tr - 1, c = tc + dc;
        if (r >= 0 && r < 8 && c >= 0 && c < 8 && board[r][c] === "bp") out.push([r, c, "bp"]);
      }
    }
    // Knight
    const kn: [number, number][] = [
      [-2, -1], [-2, 1], [-1, 2], [1, 2], [2, -1], [2, 1], [-1, -2], [1, -2],
    ];
    for (const [dr, dc] of kn) {
      const r = tr + dr, c = tc + dc;
      if (r >= 0 && r < 8 && c >= 0 && c < 8) {
        const p = board[r][c];
        if (p !== "--" && p[0] === color && p[1] === "N") out.push([r, c, p]);
      }
    }
    // King
    for (let dr = -1; dr <= 1; dr++) {
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        const r = tr + dr, c = tc + dc;
        if (r >= 0 && r < 8 && c >= 0 && c < 8) {
          const p = board[r][c];
          if (p !== "--" && p[0] === color && p[1] === "K") out.push([r, c, p]);
        }
      }
    }
    // Sliders
    const ortho: [number, number][] = [[-1, 0], [1, 0], [0, -1], [0, 1]];
    const diag: [number, number][] = [[-1, -1], [-1, 1], [1, -1], [1, 1]];
    for (const [dr, dc] of ortho) {
      let r = tr + dr, c = tc + dc;
      while (r >= 0 && r < 8 && c >= 0 && c < 8) {
        const p = board[r][c];
        if (p !== "--") {
          if (p[0] === color && (p[1] === "R" || p[1] === "Q")) out.push([r, c, p]);
          break;
        }
        r += dr; c += dc;
      }
    }
    for (const [dr, dc] of diag) {
      let r = tr + dr, c = tc + dc;
      while (r >= 0 && r < 8 && c >= 0 && c < 8) {
        const p = board[r][c];
        if (p !== "--") {
          if (p[0] === color && (p[1] === "B" || p[1] === "Q")) out.push([r, c, p]);
          break;
        }
        r += dr; c += dc;
      }
    }
    return out;
  }

  private _see(board: Board, move: Move): number {
    const victim = move.piece_captured;
    if (victim === "--") return 0;
    const tr = move.end_row, tc = move.end_col;
    // Copy board.
    const sim: Board = board.map(row => row.slice());
    sim[move.start_row][move.start_col] = "--";
    sim[tr][tc] = move.piece_moved;

    const gains: number[] = [piece_score[victim[1]] ?? 0];
    let onSquare = move.piece_moved;
    let nextSide = move.piece_moved[0] === "w" ? "b" : "w";

    while (true) {
      const attackers = this._attackers_to(sim, tr, tc, nextSide);
      if (attackers.length === 0) break;
      attackers.sort((a, b) => (piece_score[a[2][1]] ?? 0) - (piece_score[b[2][1]] ?? 0));
      const [ar, ac, ap] = attackers[0];
      gains.push((piece_score[onSquare[1]] ?? 0) - gains[gains.length - 1]);
      sim[ar][ac] = "--";
      sim[tr][tc] = ap;
      onSquare = ap;
      nextSide = nextSide === "w" ? "b" : "w";
    }

    for (let i = gains.length - 2; i >= 0; i--) {
      gains[i] = -Math.max(-gains[i], gains[i + 1]);
    }
    return gains[0];
  }

  // ----- Move ordering -----
  private _mvv_lva(move: Move): number {
    const victim = move.piece_captured;
    const victimVal = victim !== "--" ? (piece_score[victim[1]] ?? 100) : 100;
    const attackerVal = piece_score[move.piece_moved[1]] ?? 100;
    return 10 * victimVal - attackerVal;
  }

  private _score_move(move: Move, ply: number, ttMove: Move | null): number {
    if (ttMove && move.equals(ttMove)) return 10_000_000;
    if (move.is_capture) return 1_000_000 + this._mvv_lva(move);
    if (move.is_pawn_promotion) return 900_000;
    const killers = this.killer_moves.get(ply);
    if (killers) {
      if (killers[0] && move.equals(killers[0])) return 800_000;
      if (killers[1] && move.equals(killers[1])) return 700_000;
    }
    const key = move.piece_moved + move.end_row + "," + move.end_col;
    return this.history_table.get(key) ?? 0;
  }

  private _order_moves(moves: Move[], ply: number, ttMove: Move | null): void {
    moves.sort((a, b) => this._score_move(b, ply, ttMove) - this._score_move(a, ply, ttMove));
  }

  // ----- Null move helpers -----
  private _nullMoveForward(gs: GameState): [number, number] | null {
    const saved = gs.enpassant_possible;
    gs.white_to_move = !gs.white_to_move;
    gs.enpassant_possible = null;
    gs.enpassant_possible_log.push(null);
    return saved;
  }

  private _nullMoveBackward(gs: GameState, saved: [number, number] | null): void {
    gs.white_to_move = !gs.white_to_move;
    gs.enpassant_possible_log.pop();
    gs.enpassant_possible = saved;
  }

  private _hasNonPawnMaterial(gs: GameState): boolean {
    const side = gs.white_to_move ? "w" : "b";
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const p = gs.board[r][c];
        if (p !== "--" && p[0] === side && p[1] !== "K" && p[1] !== "p") return true;
      }
    }
    return false;
  }

  // ----- Quiescence -----
  private _quiescence(gs: GameState, alpha: number, beta: number, turn: number, qdepth: number): number {
    this.nodes++;
    if ((this.nodes & 2047) === 0 && this.timeExpired()) this.timeUp = true;
    if (this.shouldStop()) return 0;

    const moves = gs.getValidMoves();
    if (gs.checkmate) return -CHECKMATE + 1000 + qdepth;
    if (gs.stalemate) return STALEMATE;

    const inCheck = gs.in_check;
    const standPat = turn * this.scoreBoard(gs);

    if (!inCheck) {
      if (standPat >= beta) return beta;
      if (standPat > alpha) alpha = standPat;
    }

    if (qdepth >= QUIESCENCE_MAX_DEPTH) {
      return inCheck ? alpha : standPat;
    }

    let searchMoves: Move[];
    if (inCheck) {
      searchMoves = moves;
    } else {
      searchMoves = [];
      for (const m of moves) {
        if (!(m.is_capture || m.is_pawn_promotion)) continue;
        if (m.is_capture && !m.is_pawn_promotion) {
          const capturedVal = m.piece_captured !== "--"
            ? (piece_score[m.piece_captured[1]] ?? 0) : 0;
          if (standPat + capturedVal + 200 < alpha) continue;
          if (this._see(gs.board, m) < 0) continue;
        }
        searchMoves.push(m);
      }
    }

    searchMoves.sort((a, b) => this._score_move(b, 0, null) - this._score_move(a, 0, null));

    for (const move of searchMoves) {
      gs.makeMove(move);
      const score = -this._quiescence(gs, -beta, -alpha, -turn, qdepth + 1);
      gs.undoMove();
      if (this.shouldStop()) return 0;
      if (score >= beta) return beta;
      if (score > alpha) alpha = score;
    }
    return alpha;
  }

  // ----- Negamax -----
  private _negamax(gs: GameState, depth: number, alpha: number, beta: number, turn: number, ply: number, canNull: boolean): number {
    this.nodes++;
    if ((this.nodes & 2047) === 0 && this.timeExpired()) this.timeUp = true;
    if (this.shouldStop()) return 0;

    const isRoot = ply === 0;
    const alphaOrig = alpha;

    if (!isRoot && gs.isRepetition()) return 0;

    const hashKey = gs.getHashKey();
    const ttEntry = this.transposition_table.get(hashKey);
    let ttMove: Move | null = null;
    if (ttEntry) {
      ttMove = ttEntry.bestMove;
      if (!isRoot && ttEntry.depth >= depth) {
        if (ttEntry.flag === TT_EXACT) return ttEntry.score;
        if (ttEntry.flag === TT_LOWER && ttEntry.score >= beta) return ttEntry.score;
        if (ttEntry.flag === TT_UPPER && ttEntry.score <= alpha) return ttEntry.score;
      }
    }

    if (depth <= 0) return this._quiescence(gs, alpha, beta, turn, 0);

    const validMoves = gs.getValidMoves();
    if (gs.checkmate) return -CHECKMATE + ply;
    if (gs.stalemate) return STALEMATE;

    const inCheckHere = gs.in_check;

    // Reverse / static-null + prep for null-move + forward futility need static eval.
    let staticEval: number | null = null;
    if (!inCheckHere && !isRoot) {
      staticEval = turn * this.scoreBoard(gs);
      if (depth <= 3 && Math.abs(beta) < CHECKMATE - 1000) {
        const rfMargin = 120 * depth;
        if (staticEval - rfMargin >= beta) return staticEval - rfMargin;
      }
    }

    // Null-move pruning.
    if (canNull && !isRoot && !inCheckHere && depth >= 3 &&
        Math.abs(beta) < CHECKMATE - 1000 && this._hasNonPawnMaterial(gs)) {
      const R = depth >= 6 ? NULL_MOVE_R_DEEP : NULL_MOVE_R_SHALLOW;
      const savedEp = this._nullMoveForward(gs);
      const nullScore = -this._negamax(gs, depth - 1 - R, -beta, -beta + 1, -turn, ply + 1, false);
      this._nullMoveBackward(gs, savedEp);
      if (this.shouldStop()) return 0;
      if (nullScore >= beta) return beta;
    }

    this._order_moves(validMoves, ply, ttMove);

    let bestScore = -CHECKMATE * 2;
    let bestMove: Move | null = null;

    for (let moveNum = 0; moveNum < validMoves.length; moveNum++) {
      const move = validMoves[moveNum];

      // Forward futility pruning.
      if (staticEval !== null && depth <= 2 && moveNum > 0 &&
          !move.is_capture && !move.is_pawn_promotion &&
          Math.abs(alpha) < CHECKMATE - 1000) {
        if (staticEval + 150 * depth <= alpha) continue;
      }

      gs.makeMove(move);

      const useLMR = moveNum >= 3 && depth >= 3 && !inCheckHere &&
                     !move.is_capture && !move.is_pawn_promotion;

      let score: number;
      if (useLMR) {
        const reduction = moveNum < 6 ? 1 : 2;
        const reduced = Math.max(1, depth - 1 - reduction);
        score = -this._negamax(gs, reduced, -alpha - 1, -alpha, -turn, ply + 1, true);
        if (!this.shouldStop() && score > alpha) {
          score = -this._negamax(gs, depth - 1, -beta, -alpha, -turn, ply + 1, true);
        }
      } else {
        score = -this._negamax(gs, depth - 1, -beta, -alpha, -turn, ply + 1, true);
      }

      gs.undoMove();

      if (this.shouldStop()) return 0;

      if (score > bestScore) {
        bestScore = score;
        bestMove = move;
        if (isRoot) this.nextMove = move;
      }

      if (score > alpha) alpha = score;

      if (alpha >= beta) {
        if (!move.is_capture && !move.is_pawn_promotion) {
          const prev = this.killer_moves.get(ply);
          if (!prev || !move.equals(prev[0])) {
            this.killer_moves.set(ply, [move, prev ? prev[0] : null]);
          }
          const key = move.piece_moved + move.end_row + "," + move.end_col;
          this.history_table.set(key, (this.history_table.get(key) ?? 0) + depth * depth);
        }
        break;
      }
    }

    if (!this.shouldStop()) {
      let flag = TT_EXACT;
      if (bestScore <= alphaOrig) flag = TT_UPPER;
      else if (bestScore >= beta) flag = TT_LOWER;
      if (this.transposition_table.size >= MAX_TT_SIZE) {
        // Evict oldest half (Map preserves insertion order).
        const half = MAX_TT_SIZE >> 1;
        const keys = this.transposition_table.keys();
        for (let i = 0; i < half; i++) {
          const k = keys.next().value;
          if (k === undefined) break;
          this.transposition_table.delete(k as string);
        }
      }
      this.transposition_table.set(hashKey, { depth, score: bestScore, flag, bestMove });
    }

    return bestScore;
  }

  // ----- Entry point -----
  findBestMove(gs: GameState, validMoves: Move[], timeMs = 3000): Move {
    this.killer_moves.clear();
    this.history_table.clear();
    this.searchStart = performance.now();
    this.timeLimitMs = timeMs;
    this.timeUp = false;
    this.cancelFlag = false;
    this.nodes = 0;
    this.nextMove = null;

    const turn = gs.white_to_move ? 1 : -1;
    let best: Move | null = null;
    let prevScore: number | null = null;
    let completedDepth = 0;
    let lastScore = 0;

    for (let depth = 1; depth <= MAX_DEPTH; depth++) {
      this.nextMove = null;

      let a: number, b: number;
      if (prevScore === null || depth < 3) {
        a = -CHECKMATE * 2; b = CHECKMATE * 2;
      } else {
        a = prevScore - ASPIRATION_DELTA;
        b = prevScore + ASPIRATION_DELTA;
      }

      let delta = ASPIRATION_DELTA;
      let score = 0;
      while (true) {
        score = this._negamax(gs, depth, a, b, turn, 0, true);
        if (this.shouldStop()) break;
        if (score <= a) {
          a = Math.max(-CHECKMATE * 2, a - delta);
          delta *= 2;
          if (delta > 1000) { a = -CHECKMATE * 2; b = CHECKMATE * 2; }
        } else if (score >= b) {
          b = Math.min(CHECKMATE * 2, b + delta);
          delta *= 2;
          if (delta > 1000) { a = -CHECKMATE * 2; b = CHECKMATE * 2; }
        } else {
          break;
        }
      }

      if (this.shouldStop()) break;
      if (this.nextMove !== null) {
        best = this.nextMove;
        completedDepth = depth;
        lastScore = score;
        if (this.onIteration) {
          this.onIteration(depth, score, best, this.nodes, performance.now() - this.searchStart);
        }
      }
      prevScore = score;
      if (score > CHECKMATE - 1000 || score < -CHECKMATE + 1000) break;
      if (performance.now() - this.searchStart > this.timeLimitMs * 0.5) break;
    }

    if (best === null) {
      best = validMoves[Math.floor(Math.random() * validMoves.length)];
    }

    // Silence unused-var warnings for the outer caller.
    void completedDepth; void lastScore;
    return best;
  }

  // ----- Evaluation -----
  scoreBoard(gs: GameState): number {
    if (gs.checkmate) return gs.white_to_move ? -CHECKMATE : CHECKMATE;
    if (gs.stalemate) return STALEMATE;

    const board = gs.board;
    let score = 0, phase = 0;
    let wBishops = 0, bBishops = 0;
    let wKing: [number, number] | null = null, bKing: [number, number] | null = null;
    const wPawnFiles = Array<number>(8).fill(0);
    const bPawnFiles = Array<number>(8).fill(0);
    const wPawnRows: number[][] = Array.from({ length: 8 }, () => []);
    const bPawnRows: number[][] = Array.from({ length: 8 }, () => []);

    for (let r = 0; r < 8; r++) {
      const brow = board[r];
      for (let c = 0; c < 8; c++) {
        const piece = brow[c];
        if (piece === "--") continue;
        const color = piece[0], typ = piece[1];
        if (typ === "K") {
          if (color === "w") wKing = [r, c]; else bKing = [r, c];
          continue;
        }
        const base = piece_score[typ];
        const pst = piece_position_scores[piece][r][c];
        if (color === "w") score += base + pst;
        else score -= base + pst;

        const pw = PHASE_WEIGHT[typ];
        if (pw !== undefined) phase += pw;

        if (typ === "B") {
          if (color === "w") wBishops++; else bBishops++;
        } else if (typ === "p") {
          if (color === "w") { wPawnFiles[c]++; wPawnRows[c].push(r); }
          else { bPawnFiles[c]++; bPawnRows[c].push(r); }
        }
      }
    }

    if (phase > MAX_PHASE) phase = MAX_PHASE;
    const egPhase = MAX_PHASE - phase;

    if (wKing) {
      const [r, c] = wKing;
      const mg = king_mg_scores[r][c], eg = king_eg_scores[r][c];
      score += Math.floor((mg * phase + eg * egPhase) / MAX_PHASE);
    }
    if (bKing) {
      const [r, c] = bKing;
      const mg = king_mg_black[r][c], eg = king_eg_black[r][c];
      score -= Math.floor((mg * phase + eg * egPhase) / MAX_PHASE);
    }

    // King safety (mg-scaled).
    if (phase > 0) {
      if (wKing) score += Math.floor((this._kingSafety(board, wKing[0], wKing[1], "w") * phase) / MAX_PHASE);
      if (bKing) score -= Math.floor((this._kingSafety(board, bKing[0], bKing[1], "b") * phase) / MAX_PHASE);
    }

    if (wBishops >= 2) score += BISHOP_PAIR_BONUS;
    if (bBishops >= 2) score -= BISHOP_PAIR_BONUS;

    for (let c = 0; c < 8; c++) {
      if (wPawnFiles[c] > 1) score -= DOUBLED_PAWN_PENALTY * (wPawnFiles[c] - 1);
      if (bPawnFiles[c] > 1) score += DOUBLED_PAWN_PENALTY * (bPawnFiles[c] - 1);
    }
    for (let c = 0; c < 8; c++) {
      const lhw = c > 0 && wPawnFiles[c - 1] > 0;
      const rhw = c < 7 && wPawnFiles[c + 1] > 0;
      if (wPawnFiles[c] > 0 && !(lhw || rhw)) score -= ISOLATED_PAWN_PENALTY * wPawnFiles[c];
      const lhb = c > 0 && bPawnFiles[c - 1] > 0;
      const rhb = c < 7 && bPawnFiles[c + 1] > 0;
      if (bPawnFiles[c] > 0 && !(lhb || rhb)) score += ISOLATED_PAWN_PENALTY * bPawnFiles[c];
    }
    // Passed pawns.
    for (let col = 0; col < 8; col++) {
      for (const row of wPawnRows[col]) {
        let blocked = false;
        for (const cc of [col - 1, col, col + 1]) {
          if (cc < 0 || cc > 7) continue;
          for (const br of bPawnRows[cc]) {
            if (br < row) { blocked = true; break; }
          }
          if (blocked) break;
        }
        if (!blocked) {
          const advance = 6 - row;
          if (advance >= 0 && advance <= 7) {
            const mg = PASSED_PAWN_MG[advance], eg = PASSED_PAWN_EG[advance];
            score += Math.floor((mg * phase + eg * egPhase) / MAX_PHASE);
          }
        }
      }
      for (const row of bPawnRows[col]) {
        let blocked = false;
        for (const cc of [col - 1, col, col + 1]) {
          if (cc < 0 || cc > 7) continue;
          for (const wr of wPawnRows[cc]) {
            if (wr > row) { blocked = true; break; }
          }
          if (blocked) break;
        }
        if (!blocked) {
          const advance = row - 1;
          if (advance >= 0 && advance <= 7) {
            const mg = PASSED_PAWN_MG[advance], eg = PASSED_PAWN_EG[advance];
            score -= Math.floor((mg * phase + eg * egPhase) / MAX_PHASE);
          }
        }
      }
    }

    return score;
  }

  private _kingSafety(board: Board, kr: number, kc: number, color: string): number {
    let score = 0;
    const forward = color === "w" ? -1 : 1;
    const pawn = color + "p";
    for (const dc of [-1, 0, 1]) {
      const c = kc + dc;
      if (c < 0 || c > 7) continue;
      const r1 = kr + forward, r2 = kr + 2 * forward;
      let shielded = false;
      if (r1 >= 0 && r1 < 8 && board[r1][c] === pawn) { score += 12; shielded = true; }
      else if (r2 >= 0 && r2 < 8 && board[r2][c] === pawn) { score += 6; shielded = true; }
      if (!shielded) score -= 10;
    }
    return score;
  }
}
