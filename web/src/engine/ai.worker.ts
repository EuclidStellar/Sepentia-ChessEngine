// Web Worker that runs the AI search so the UI stays responsive while the
// engine thinks. Message protocol:
//   from main: { type: "search", board, side_to_move, castling, ep,
//                move_log, position_history, time_ms }
//   from main: { type: "cancel" }
//   to main:   { type: "iteration", depth, score, move, nodes, elapsedMs }
//   to main:   { type: "result", move, nodes, elapsedMs }

import { GameState, Move, CastleRights } from "./chessengine";
import { Engine } from "./chessAI";

const engine = new Engine();

// Rebuild a GameState from the serialized snapshot the main thread sends.
function buildGameState(payload: any): GameState {
  const gs = new GameState();
  gs.board = payload.board;
  gs.white_to_move = payload.side_to_move;
  gs.current_castling_rights = new CastleRights(
    payload.castling.wks,
    payload.castling.bks,
    payload.castling.wqs,
    payload.castling.bqs,
  );
  // Castle-rights log: we only need the current one for correctness
  // during search; undo sequences within the search will push/pop their
  // own. Seed with current so the first pop isn't into an empty list.
  gs.castle_rights_log = [gs.current_castling_rights.clone()];
  gs.enpassant_possible = payload.ep;
  gs.enpassant_possible_log = [payload.ep];
  // Find king locations from the supplied board.
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      if (gs.board[r][c] === "wK") gs.white_king_location = [r, c];
      else if (gs.board[r][c] === "bK") gs.black_king_location = [r, c];
    }
  }
  // Seed position history so repetition detection works across game.
  if (Array.isArray(payload.position_history) && payload.position_history.length > 0) {
    gs.position_history = payload.position_history.slice();
  } else {
    gs.position_history = [gs.getHashKey()];
  }
  return gs;
}

self.onmessage = (e: MessageEvent) => {
  const msg = e.data;
  if (msg.type === "cancel") {
    engine.requestCancel();
    return;
  }
  if (msg.type === "reset-tt") {
    engine.resetTT();
    return;
  }
  if (msg.type !== "search") return;

  const gs = buildGameState(msg);
  const validMoves = gs.getValidMoves();

  engine.onIteration = (depth, score, move, nodes, elapsedMs) => {
    (self as any).postMessage({
      type: "iteration",
      depth, score, nodes, elapsedMs,
      move: move ? serializeMove(move) : null,
    });
  };

  const t0 = performance.now();
  const best = engine.findBestMove(gs, validMoves, msg.time_ms ?? 3000);
  const elapsedMs = performance.now() - t0;

  (self as any).postMessage({
    type: "result",
    move: serializeMove(best),
    nodes: engine.nodes,
    elapsedMs,
  });
};

function serializeMove(m: Move) {
  return {
    start_row: m.start_row, start_col: m.start_col,
    end_row: m.end_row, end_col: m.end_col,
    is_enpassant_move: m.is_enpassant_move,
    is_castle_move: m.is_castle_move,
    is_pawn_promotion: m.is_pawn_promotion,
    piece_moved: m.piece_moved,
    piece_captured: m.piece_captured,
    notation: m.toString(),
  };
}
