// Chess engine (rules + state + move generation), ported from src/chessengine.py.
// Faithful translation: same board representation ("wK"/"bp"/"--"), same
// algorithms for pin/check detection, en-passant legality, castling, and
// repetition tracking.

export type PieceCode = string; // "wK", "bp", "--", etc.
export type Board = PieceCode[][];

export class CastleRights {
  wks: boolean;
  bks: boolean;
  wqs: boolean;
  bqs: boolean;
  constructor(wks: boolean, bks: boolean, wqs: boolean, bqs: boolean) {
    this.wks = wks;
    this.bks = bks;
    this.wqs = wqs;
    this.bqs = bqs;
  }
  clone(): CastleRights {
    return new CastleRights(this.wks, this.bks, this.wqs, this.bqs);
  }
}

export class Move {
  static ranksToRows: Record<string, number> = {
    "1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0,
  };
  static rowsToRanks: Record<number, string> = Object.fromEntries(
    Object.entries(Move.ranksToRows).map(([k, v]) => [v, k]),
  );
  static filesToCols: Record<string, number> = {
    a: 0, b: 1, c: 2, d: 3, e: 4, f: 5, g: 6, h: 7,
  };
  static colsToFiles: Record<number, string> = Object.fromEntries(
    Object.entries(Move.filesToCols).map(([k, v]) => [v, k]),
  );

  start_row: number;
  start_col: number;
  end_row: number;
  end_col: number;
  piece_moved: PieceCode;
  piece_captured: PieceCode;
  is_pawn_promotion: boolean;
  is_enpassant_move: boolean;
  is_castle_move: boolean;
  is_capture: boolean;
  moveID: number;

  constructor(
    start: [number, number],
    end: [number, number],
    board: Board,
    is_enpassant_move = false,
    is_castle_move = false,
  ) {
    this.start_row = start[0];
    this.start_col = start[1];
    this.end_row = end[0];
    this.end_col = end[1];
    this.piece_moved = board[this.start_row][this.start_col];
    this.piece_captured = board[this.end_row][this.end_col];
    this.is_pawn_promotion =
      (this.piece_moved === "wp" && this.end_row === 0) ||
      (this.piece_moved === "bp" && this.end_row === 7);
    this.is_enpassant_move = is_enpassant_move;
    if (is_enpassant_move) {
      this.piece_captured = this.piece_moved === "bp" ? "wp" : "bp";
    }
    this.is_castle_move = is_castle_move;
    this.is_capture = this.piece_captured !== "--";
    this.moveID =
      this.start_row * 1000 +
      this.start_col * 100 +
      this.end_row * 10 +
      this.end_col;
  }

  equals(other: Move | null | undefined): boolean {
    if (!other) return false;
    return this.moveID === other.moveID;
  }

  getRankFile(row: number, col: number): string {
    return Move.colsToFiles[col] + Move.rowsToRanks[row];
  }

  toString(): string {
    if (this.is_castle_move) {
      return this.end_col === 6 ? "0-0" : "0-0-0";
    }
    const end_square = this.getRankFile(this.end_row, this.end_col);
    if (this.piece_moved[1] === "p") {
      if (this.is_capture) {
        return Move.colsToFiles[this.start_col] + "x" + end_square;
      }
      return this.is_pawn_promotion ? end_square + "Q" : end_square;
    }
    return this.piece_moved[1] + (this.is_capture ? "x" : "") + end_square;
  }
}

type Pin = [number, number, number, number];   // row, col, dir_r, dir_c
type Check = [number, number, number, number]; // row, col, dir_r, dir_c
type EP = [number, number] | null;              // enpassant target square

export class GameState {
  board: Board;
  white_to_move: boolean;
  move_log: Move[];
  white_king_location: [number, number];
  black_king_location: [number, number];
  checkmate: boolean;
  stalemate: boolean;
  in_check: boolean;
  pins: Pin[];
  checks: Check[];
  enpassant_possible: EP;
  enpassant_possible_log: EP[];
  current_castling_rights: CastleRights;
  castle_rights_log: CastleRights[];
  position_history: string[];

  constructor() {
    this.board = [
      ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
      ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
      ["--", "--", "--", "--", "--", "--", "--", "--"],
      ["--", "--", "--", "--", "--", "--", "--", "--"],
      ["--", "--", "--", "--", "--", "--", "--", "--"],
      ["--", "--", "--", "--", "--", "--", "--", "--"],
      ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
      ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"],
    ];
    this.white_to_move = true;
    this.move_log = [];
    this.white_king_location = [7, 4];
    this.black_king_location = [0, 4];
    this.checkmate = false;
    this.stalemate = false;
    this.in_check = false;
    this.pins = [];
    this.checks = [];
    this.enpassant_possible = null;
    this.enpassant_possible_log = [null];
    this.current_castling_rights = new CastleRights(true, true, true, true);
    this.castle_rights_log = [this.current_castling_rights.clone()];
    this.position_history = [this.getHashKey()];
  }

  getHashKey(): string {
    // A compact, deterministic string including all position-identifying
    // data: board squares, side-to-move, castling, en-passant target.
    let s = "";
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        s += this.board[r][c];
      }
    }
    s += this.white_to_move ? "w" : "b";
    const cr = this.current_castling_rights;
    s += (cr.wks ? "K" : "-") + (cr.wqs ? "Q" : "-") +
         (cr.bks ? "k" : "-") + (cr.bqs ? "q" : "-");
    if (this.enpassant_possible) {
      s += this.enpassant_possible[0] + "," + this.enpassant_possible[1];
    } else {
      s += "-";
    }
    return s;
  }

  isRepetition(): boolean {
    if (this.position_history.length < 3) return false;
    const current = this.position_history[this.position_history.length - 1];
    for (let i = this.position_history.length - 3; i >= 0; i -= 2) {
      if (this.position_history[i] === current) return true;
    }
    return false;
  }

  makeMove(move: Move): void {
    this.board[move.start_row][move.start_col] = "--";
    this.board[move.end_row][move.end_col] = move.piece_moved;
    this.move_log.push(move);
    this.white_to_move = !this.white_to_move;
    if (move.piece_moved === "wK") {
      this.white_king_location = [move.end_row, move.end_col];
    } else if (move.piece_moved === "bK") {
      this.black_king_location = [move.end_row, move.end_col];
    }

    // Pawn promotion (auto-queen).
    if (move.is_pawn_promotion) {
      this.board[move.end_row][move.end_col] = move.piece_moved[0] + "Q";
    }

    // En passant capture.
    if (move.is_enpassant_move) {
      this.board[move.start_row][move.end_col] = "--";
    }

    // Update en-passant target.
    if (
      move.piece_moved[1] === "p" &&
      Math.abs(move.start_row - move.end_row) === 2
    ) {
      this.enpassant_possible = [
        (move.start_row + move.end_row) >> 1,
        move.start_col,
      ];
    } else {
      this.enpassant_possible = null;
    }

    // Castle: move the rook.
    if (move.is_castle_move) {
      if (move.end_col - move.start_col === 2) {
        this.board[move.end_row][move.end_col - 1] =
          this.board[move.end_row][move.end_col + 1];
        this.board[move.end_row][move.end_col + 1] = "--";
      } else {
        this.board[move.end_row][move.end_col + 1] =
          this.board[move.end_row][move.end_col - 2];
        this.board[move.end_row][move.end_col - 2] = "--";
      }
    }

    this.enpassant_possible_log.push(this.enpassant_possible);
    this.updateCastleRights(move);
    this.castle_rights_log.push(this.current_castling_rights.clone());
    this.position_history.push(this.getHashKey());
  }

  undoMove(): void {
    if (this.move_log.length === 0) return;
    const move = this.move_log.pop()!;
    this.board[move.start_row][move.start_col] = move.piece_moved;
    this.board[move.end_row][move.end_col] = move.piece_captured;
    this.white_to_move = !this.white_to_move;
    if (move.piece_moved === "wK") {
      this.white_king_location = [move.start_row, move.start_col];
    } else if (move.piece_moved === "bK") {
      this.black_king_location = [move.start_row, move.start_col];
    }
    if (move.is_enpassant_move) {
      this.board[move.end_row][move.end_col] = "--";
      this.board[move.start_row][move.end_col] = move.piece_captured;
    }

    this.enpassant_possible_log.pop();
    this.enpassant_possible =
      this.enpassant_possible_log[this.enpassant_possible_log.length - 1];

    this.castle_rights_log.pop();
    this.current_castling_rights =
      this.castle_rights_log[this.castle_rights_log.length - 1].clone();

    if (move.is_castle_move) {
      if (move.end_col - move.start_col === 2) {
        this.board[move.end_row][move.end_col + 1] =
          this.board[move.end_row][move.end_col - 1];
        this.board[move.end_row][move.end_col - 1] = "--";
      } else {
        this.board[move.end_row][move.end_col - 2] =
          this.board[move.end_row][move.end_col + 1];
        this.board[move.end_row][move.end_col + 1] = "--";
      }
    }
    this.checkmate = false;
    this.stalemate = false;
    if (this.position_history.length > 0) this.position_history.pop();
  }

  updateCastleRights(move: Move): void {
    if (move.piece_captured === "wR") {
      if (move.end_col === 0) this.current_castling_rights.wqs = false;
      else if (move.end_col === 7) this.current_castling_rights.wks = false;
    } else if (move.piece_captured === "bR") {
      if (move.end_col === 0) this.current_castling_rights.bqs = false;
      else if (move.end_col === 7) this.current_castling_rights.bks = false;
    }

    if (move.piece_moved === "wK") {
      this.current_castling_rights.wqs = false;
      this.current_castling_rights.wks = false;
    } else if (move.piece_moved === "bK") {
      this.current_castling_rights.bqs = false;
      this.current_castling_rights.bks = false;
    } else if (move.piece_moved === "wR") {
      if (move.start_row === 7) {
        if (move.start_col === 0) this.current_castling_rights.wqs = false;
        else if (move.start_col === 7) this.current_castling_rights.wks = false;
      }
    } else if (move.piece_moved === "bR") {
      if (move.start_row === 0) {
        if (move.start_col === 0) this.current_castling_rights.bqs = false;
        else if (move.start_col === 7) this.current_castling_rights.bks = false;
      }
    }
  }

  getValidMoves(): Move[] {
    const tempCastleRights = this.current_castling_rights.clone();
    let moves: Move[] = [];
    const { in_check, pins, checks } = this.checkForPinsAndChecks();
    this.in_check = in_check;
    this.pins = pins;
    this.checks = checks;

    const [king_row, king_col] = this.white_to_move
      ? this.white_king_location
      : this.black_king_location;

    if (this.in_check) {
      if (this.checks.length === 1) {
        moves = this.getAllPossibleMoves();
        const check = this.checks[0];
        const [check_row, check_col, dr, dc] = check;
        const piece_checking = this.board[check_row][check_col];
        let valid_squares: [number, number][] = [];
        if (piece_checking[1] === "N") {
          valid_squares = [[check_row, check_col]];
        } else {
          for (let i = 1; i < 8; i++) {
            const valid_square: [number, number] = [
              king_row + dr * i,
              king_col + dc * i,
            ];
            valid_squares.push(valid_square);
            if (valid_square[0] === check_row && valid_square[1] === check_col) {
              break;
            }
          }
        }
        // Filter moves that don't block check or move king.
        for (let i = moves.length - 1; i >= 0; i--) {
          if (moves[i].piece_moved[1] !== "K") {
            const er = moves[i].end_row;
            const ec = moves[i].end_col;
            let keep = false;
            for (const sq of valid_squares) {
              if (sq[0] === er && sq[1] === ec) {
                keep = true;
                break;
              }
            }
            if (!keep) moves.splice(i, 1);
          }
        }
      } else {
        // Double check: king must move.
        this.getKingMoves(king_row, king_col, moves);
      }
    } else {
      moves = this.getAllPossibleMoves();
      const [kr, kc] = this.white_to_move
        ? this.white_king_location
        : this.black_king_location;
      this.getCastleMoves(kr, kc, moves);
    }

    if (moves.length === 0) {
      if (this.inCheck()) this.checkmate = true;
      else this.stalemate = true;
    } else {
      this.checkmate = false;
      this.stalemate = false;
    }

    this.current_castling_rights = tempCastleRights;
    return moves;
  }

  inCheck(): boolean {
    const [r, c] = this.white_to_move
      ? this.white_king_location
      : this.black_king_location;
    return this.squareUnderAttack(r, c);
  }

  squareUnderAttack(row: number, col: number): boolean {
    this.white_to_move = !this.white_to_move;
    const opp = this.getAllPossibleMoves();
    this.white_to_move = !this.white_to_move;
    for (const m of opp) {
      if (m.end_row === row && m.end_col === col) return true;
    }
    return false;
  }

  getAllPossibleMoves(): Move[] {
    const moves: Move[] = [];
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const turn = this.board[r][c][0];
        if (
          (turn === "w" && this.white_to_move) ||
          (turn === "b" && !this.white_to_move)
        ) {
          const piece = this.board[r][c][1];
          switch (piece) {
            case "p": this.getPawnMoves(r, c, moves); break;
            case "R": this.getRookMoves(r, c, moves); break;
            case "N": this.getKnightMoves(r, c, moves); break;
            case "B": this.getBishopMoves(r, c, moves); break;
            case "Q": this.getQueenMoves(r, c, moves); break;
            case "K": this.getKingMoves(r, c, moves); break;
          }
        }
      }
    }
    return moves;
  }

  checkForPinsAndChecks(): { in_check: boolean; pins: Pin[]; checks: Check[] } {
    const pins: Pin[] = [];
    const checks: Check[] = [];
    let in_check = false;
    let enemy_color: string, ally_color: string, start_row: number, start_col: number;
    if (this.white_to_move) {
      enemy_color = "b"; ally_color = "w";
      [start_row, start_col] = this.white_king_location;
    } else {
      enemy_color = "w"; ally_color = "b";
      [start_row, start_col] = this.black_king_location;
    }
    const directions: [number, number][] = [
      [-1, 0], [0, -1], [1, 0], [0, 1],
      [-1, -1], [-1, 1], [1, -1], [1, 1],
    ];
    for (let j = 0; j < directions.length; j++) {
      const dir = directions[j];
      let possible_pin: Pin | null = null;
      for (let i = 1; i < 8; i++) {
        const end_row = start_row + dir[0] * i;
        const end_col = start_col + dir[1] * i;
        if (end_row < 0 || end_row > 7 || end_col < 0 || end_col > 7) break;
        const end_piece = this.board[end_row][end_col];
        if (end_piece[0] === ally_color && end_piece[1] !== "K") {
          if (possible_pin === null) {
            possible_pin = [end_row, end_col, dir[0], dir[1]];
          } else {
            break;
          }
        } else if (end_piece[0] === enemy_color) {
          const enemy_type = end_piece[1];
          const isRook = j >= 0 && j <= 3 && enemy_type === "R";
          const isBishop = j >= 4 && j <= 7 && enemy_type === "B";
          const isPawn = i === 1 && enemy_type === "p" &&
            ((enemy_color === "w" && j >= 6 && j <= 7) ||
              (enemy_color === "b" && j >= 4 && j <= 5));
          const isQueen = enemy_type === "Q";
          const isKing = i === 1 && enemy_type === "K";
          if (isRook || isBishop || isPawn || isQueen || isKing) {
            if (possible_pin === null) {
              in_check = true;
              checks.push([end_row, end_col, dir[0], dir[1]]);
              break;
            } else {
              pins.push(possible_pin);
              break;
            }
          } else {
            break;
          }
        }
      }
    }
    const knight_moves: [number, number][] = [
      [-2, -1], [-2, 1], [-1, 2], [1, 2], [2, -1], [2, 1], [-1, -2], [1, -2],
    ];
    for (const m of knight_moves) {
      const er = start_row + m[0];
      const ec = start_col + m[1];
      if (er >= 0 && er <= 7 && ec >= 0 && ec <= 7) {
        const p = this.board[er][ec];
        if (p[0] === enemy_color && p[1] === "N") {
          in_check = true;
          checks.push([er, ec, m[0], m[1]]);
        }
      }
    }
    return { in_check, pins, checks };
  }

  getPawnMoves(row: number, col: number, moves: Move[]): void {
    let piece_pinned = false;
    let pin_direction: [number, number] | null = null;
    for (let i = this.pins.length - 1; i >= 0; i--) {
      if (this.pins[i][0] === row && this.pins[i][1] === col) {
        piece_pinned = true;
        pin_direction = [this.pins[i][2], this.pins[i][3]];
        this.pins.splice(i, 1);
        break;
      }
    }
    let move_amount: number, start_row: number, enemy_color: string;
    let king_row: number, king_col: number;
    if (this.white_to_move) {
      move_amount = -1; start_row = 6; enemy_color = "b";
      [king_row, king_col] = this.white_king_location;
    } else {
      move_amount = 1; start_row = 1; enemy_color = "w";
      [king_row, king_col] = this.black_king_location;
    }

    const pinDirEq = (a: number, b: number): boolean =>
      pin_direction !== null && pin_direction[0] === a && pin_direction[1] === b;

    if (this.board[row + move_amount][col] === "--") {
      if (!piece_pinned || pinDirEq(move_amount, 0)) {
        moves.push(new Move([row, col], [row + move_amount, col], this.board));
        if (row === start_row && this.board[row + 2 * move_amount][col] === "--") {
          moves.push(new Move([row, col], [row + 2 * move_amount, col], this.board));
        }
      }
    }
    // Captures + en-passant both sides.
    for (const dc of [-1, 1]) {
      const nc = col + dc;
      if (nc < 0 || nc > 7) continue;
      if (!piece_pinned || pinDirEq(move_amount, dc)) {
        if (this.board[row + move_amount][nc][0] === enemy_color) {
          moves.push(new Move([row, col], [row + move_amount, nc], this.board));
        }
        const ep = this.enpassant_possible;
        if (ep && ep[0] === row + move_amount && ep[1] === nc) {
          let attacking_piece = false;
          let blocking_piece = false;
          if (king_row === row) {
            let inside_range: number[], outside_range: number[];
            if (king_col < col) {
              inside_range = rangeExcl(king_col + 1, dc === -1 ? col - 1 : col);
              outside_range = rangeExcl(dc === -1 ? col + 1 : col + 2, 8);
            } else {
              inside_range = rangeDescExcl(
                king_col - 1,
                dc === -1 ? col : col + 1,
              );
              outside_range = rangeDescExcl(
                dc === -1 ? col - 2 : col - 1,
                -1,
              );
            }
            for (const i of inside_range) {
              if (this.board[row][i] !== "--") blocking_piece = true;
            }
            for (const i of outside_range) {
              const sq = this.board[row][i];
              if (sq[0] === enemy_color && (sq[1] === "R" || sq[1] === "Q")) {
                attacking_piece = true;
              } else if (sq !== "--") {
                blocking_piece = true;
              }
            }
          }
          if (!attacking_piece || blocking_piece) {
            moves.push(new Move([row, col], [row + move_amount, nc], this.board, true));
          }
        }
      }
    }
  }

  getRookMoves(row: number, col: number, moves: Move[]): void {
    let piece_pinned = false;
    let pin_direction: [number, number] | null = null;
    for (let i = this.pins.length - 1; i >= 0; i--) {
      if (this.pins[i][0] === row && this.pins[i][1] === col) {
        piece_pinned = true;
        pin_direction = [this.pins[i][2], this.pins[i][3]];
        if (this.board[row][col][1] !== "Q") this.pins.splice(i, 1);
        break;
      }
    }
    const directions: [number, number][] = [
      [-1, 0], [0, -1], [1, 0], [0, 1],
    ];
    const enemy_color = this.white_to_move ? "b" : "w";
    for (const dir of directions) {
      for (let i = 1; i < 8; i++) {
        const er = row + dir[0] * i;
        const ec = col + dir[1] * i;
        if (er < 0 || er > 7 || ec < 0 || ec > 7) break;
        if (
          !piece_pinned ||
          (pin_direction !== null &&
            (pin_direction[0] === dir[0] && pin_direction[1] === dir[1])) ||
          (pin_direction !== null &&
            (pin_direction[0] === -dir[0] && pin_direction[1] === -dir[1]))
        ) {
          const ep = this.board[er][ec];
          if (ep === "--") {
            moves.push(new Move([row, col], [er, ec], this.board));
          } else if (ep[0] === enemy_color) {
            moves.push(new Move([row, col], [er, ec], this.board));
            break;
          } else {
            break;
          }
        }
      }
    }
  }

  getKnightMoves(row: number, col: number, moves: Move[]): void {
    let piece_pinned = false;
    for (let i = this.pins.length - 1; i >= 0; i--) {
      if (this.pins[i][0] === row && this.pins[i][1] === col) {
        piece_pinned = true;
        this.pins.splice(i, 1);
        break;
      }
    }
    const knight_moves: [number, number][] = [
      [-2, -1], [-2, 1], [-1, 2], [1, 2], [2, -1], [2, 1], [-1, -2], [1, -2],
    ];
    const ally_color = this.white_to_move ? "w" : "b";
    for (const m of knight_moves) {
      const er = row + m[0];
      const ec = col + m[1];
      if (er >= 0 && er <= 7 && ec >= 0 && ec <= 7) {
        if (!piece_pinned) {
          const ep = this.board[er][ec];
          if (ep[0] !== ally_color) {
            moves.push(new Move([row, col], [er, ec], this.board));
          }
        }
      }
    }
  }

  getBishopMoves(row: number, col: number, moves: Move[]): void {
    let piece_pinned = false;
    let pin_direction: [number, number] | null = null;
    for (let i = this.pins.length - 1; i >= 0; i--) {
      if (this.pins[i][0] === row && this.pins[i][1] === col) {
        piece_pinned = true;
        pin_direction = [this.pins[i][2], this.pins[i][3]];
        this.pins.splice(i, 1);
        break;
      }
    }
    const directions: [number, number][] = [
      [-1, -1], [-1, 1], [1, 1], [1, -1],
    ];
    const enemy_color = this.white_to_move ? "b" : "w";
    for (const dir of directions) {
      for (let i = 1; i < 8; i++) {
        const er = row + dir[0] * i;
        const ec = col + dir[1] * i;
        if (er < 0 || er > 7 || ec < 0 || ec > 7) break;
        if (
          !piece_pinned ||
          (pin_direction !== null &&
            (pin_direction[0] === dir[0] && pin_direction[1] === dir[1])) ||
          (pin_direction !== null &&
            (pin_direction[0] === -dir[0] && pin_direction[1] === -dir[1]))
        ) {
          const ep = this.board[er][ec];
          if (ep === "--") {
            moves.push(new Move([row, col], [er, ec], this.board));
          } else if (ep[0] === enemy_color) {
            moves.push(new Move([row, col], [er, ec], this.board));
            break;
          } else {
            break;
          }
        }
      }
    }
  }

  getQueenMoves(row: number, col: number, moves: Move[]): void {
    this.getBishopMoves(row, col, moves);
    this.getRookMoves(row, col, moves);
  }

  getKingMoves(row: number, col: number, moves: Move[]): void {
    const row_moves = [-1, -1, -1, 0, 0, 1, 1, 1];
    const col_moves = [-1, 0, 1, -1, 1, -1, 0, 1];
    const ally_color = this.white_to_move ? "w" : "b";
    for (let i = 0; i < 8; i++) {
      const er = row + row_moves[i];
      const ec = col + col_moves[i];
      if (er >= 0 && er <= 7 && ec >= 0 && ec <= 7) {
        const ep = this.board[er][ec];
        if (ep[0] !== ally_color) {
          const saved = ally_color === "w"
            ? this.white_king_location
            : this.black_king_location;
          if (ally_color === "w") this.white_king_location = [er, ec];
          else this.black_king_location = [er, ec];
          const { in_check } = this.checkForPinsAndChecks();
          if (!in_check) {
            moves.push(new Move([row, col], [er, ec], this.board));
          }
          if (ally_color === "w") this.white_king_location = saved;
          else this.black_king_location = saved;
        }
      }
    }
  }

  getCastleMoves(row: number, col: number, moves: Move[]): void {
    if (this.squareUnderAttack(row, col)) return;
    if (
      (this.white_to_move && this.current_castling_rights.wks) ||
      (!this.white_to_move && this.current_castling_rights.bks)
    ) {
      this.getKingsideCastleMoves(row, col, moves);
    }
    if (
      (this.white_to_move && this.current_castling_rights.wqs) ||
      (!this.white_to_move && this.current_castling_rights.bqs)
    ) {
      this.getQueensideCastleMoves(row, col, moves);
    }
  }

  getKingsideCastleMoves(row: number, col: number, moves: Move[]): void {
    if (
      this.board[row][col + 1] === "--" &&
      this.board[row][col + 2] === "--"
    ) {
      if (
        !this.squareUnderAttack(row, col + 1) &&
        !this.squareUnderAttack(row, col + 2)
      ) {
        moves.push(new Move([row, col], [row, col + 2], this.board, false, true));
      }
    }
  }

  getQueensideCastleMoves(row: number, col: number, moves: Move[]): void {
    if (
      this.board[row][col - 1] === "--" &&
      this.board[row][col - 2] === "--" &&
      this.board[row][col - 3] === "--"
    ) {
      if (
        !this.squareUnderAttack(row, col - 1) &&
        !this.squareUnderAttack(row, col - 2)
      ) {
        moves.push(new Move([row, col], [row, col - 2], this.board, false, true));
      }
    }
  }
}

// Helper ranges mirroring Python range(start, stop) / range(start, stop, -1)
function rangeExcl(start: number, stop: number): number[] {
  const out: number[] = [];
  for (let i = start; i < stop; i++) out.push(i);
  return out;
}
function rangeDescExcl(start: number, stop: number): number[] {
  const out: number[] = [];
  for (let i = start; i > stop; i--) out.push(i);
  return out;
}
