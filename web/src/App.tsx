import { useEffect, useMemo, useRef, useState } from "react";
import { GameState, Move } from "./engine/chessengine";
import ChessBoard from "./ChessBoard";
import MoveLog from "./MoveLog";
import "./App.css";

interface SearchUpdate {
  depth: number;
  score: number;
  nodes: number;
  elapsedMs: number;
  moveNotation: string | null;
}

export default function App() {
  const gsRef = useRef(new GameState());
  const [, setTick] = useState(0);
  const bump = () => setTick(t => t + 1);

  const [validMoves, setValidMoves] = useState<Move[]>(() =>
    gsRef.current.getValidMoves(),
  );
  const [selected, setSelected] = useState<[number, number] | null>(null);
  const [playerWhite, setPlayerWhite] = useState(true);
  const [playerBlack, setPlayerBlack] = useState(false);
  const [aiThinking, setAiThinking] = useState(false);
  const [searchInfo, setSearchInfo] = useState<SearchUpdate | null>(null);
  const [timeMs, setTimeMs] = useState(3000);

  const workerRef = useRef<Worker | null>(null);
  const validMovesRef = useRef<Move[]>(validMoves);
  useEffect(() => { validMovesRef.current = validMoves; }, [validMoves]);

  useEffect(() => {
    const w = new Worker(new URL("./engine/ai.worker.ts", import.meta.url), {
      type: "module",
    });
    workerRef.current = w;
    w.onmessage = (e: MessageEvent) => {
      const msg = e.data;
      if (msg.type === "iteration") {
        setSearchInfo({
          depth: msg.depth,
          score: msg.score,
          nodes: msg.nodes,
          elapsedMs: msg.elapsedMs,
          moveNotation: msg.move?.notation ?? null,
        });
      } else if (msg.type === "result") {
        applyAIMove(msg.move);
        setAiThinking(false);
      }
    };
    return () => { w.terminate(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const gs = gsRef.current;
    const isHumanTurn =
      (gs.white_to_move && playerWhite) || (!gs.white_to_move && playerBlack);
    if (isHumanTurn || gs.checkmate || gs.stalemate || aiThinking) return;
    if (!workerRef.current) return;

    setAiThinking(true);
    setSearchInfo(null);
    workerRef.current.postMessage({
      type: "search",
      board: gs.board.map(row => row.slice()),
      side_to_move: gs.white_to_move,
      castling: {
        wks: gs.current_castling_rights.wks,
        bks: gs.current_castling_rights.bks,
        wqs: gs.current_castling_rights.wqs,
        bqs: gs.current_castling_rights.bqs,
      },
      ep: gs.enpassant_possible,
      position_history: gs.position_history.slice(),
      time_ms: timeMs,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aiThinking, playerWhite, playerBlack, timeMs, validMoves]);

  function applyAIMove(serialized: any) {
    if (!serialized) return;
    const gs = gsRef.current;
    const match = validMovesRef.current.find(m =>
      m.start_row === serialized.start_row &&
      m.start_col === serialized.start_col &&
      m.end_row === serialized.end_row &&
      m.end_col === serialized.end_col,
    );
    if (!match) return;
    gs.makeMove(match);
    setValidMoves(gs.getValidMoves());
    setSelected(null);
    bump();
  }

  function onSquareClick(row: number, col: number) {
    const gs = gsRef.current;
    const isHumanTurn =
      (gs.white_to_move && playerWhite) || (!gs.white_to_move && playerBlack);
    if (!isHumanTurn || aiThinking || gs.checkmate || gs.stalemate) return;

    if (selected === null) {
      if (gs.board[row][col] !== "--") {
        const turn = gs.board[row][col][0];
        if ((turn === "w" && gs.white_to_move) || (turn === "b" && !gs.white_to_move)) {
          setSelected([row, col]);
        }
      }
      return;
    }
    const [sr, sc] = selected;
    if (sr === row && sc === col) {
      setSelected(null);
      return;
    }
    for (const m of validMoves) {
      if (m.start_row === sr && m.start_col === sc && m.end_row === row && m.end_col === col) {
        gs.makeMove(m);
        setValidMoves(gs.getValidMoves());
        setSelected(null);
        bump();
        return;
      }
    }
    const other = gs.board[row][col];
    if (other !== "--") {
      const turn = other[0];
      if ((turn === "w" && gs.white_to_move) || (turn === "b" && !gs.white_to_move)) {
        setSelected([row, col]);
        return;
      }
    }
    setSelected(null);
  }

  function onUndo() {
    if (workerRef.current && aiThinking) {
      workerRef.current.postMessage({ type: "cancel" });
    }
    const gs = gsRef.current;
    gs.undoMove();
    setValidMoves(gs.getValidMoves());
    setSelected(null);
    setAiThinking(false);
    bump();
  }

  function onReset() {
    if (workerRef.current) {
      workerRef.current.postMessage({ type: "cancel" });
      workerRef.current.postMessage({ type: "reset-tt" });
    }
    gsRef.current = new GameState();
    setValidMoves(gsRef.current.getValidMoves());
    setSelected(null);
    setAiThinking(false);
    setSearchInfo(null);
    bump();
  }

  const legalDestinations = useMemo(() => {
    if (selected === null) return new Set<string>();
    const [sr, sc] = selected;
    const dests = new Set<string>();
    for (const m of validMoves) {
      if (m.start_row === sr && m.start_col === sc) {
        dests.add(`${m.end_row},${m.end_col}`);
      }
    }
    return dests;
  }, [selected, validMoves]);

  const gs = gsRef.current;

  return (
    <div className="app">
      <div className="sidebar">
        <h1>Sepentia</h1>
        <div className="status">
          {gs.checkmate
            ? `Checkmate — ${gs.white_to_move ? "Black" : "White"} wins`
            : gs.stalemate
            ? "Stalemate"
            : `${gs.white_to_move ? "White" : "Black"} to move`}
        </div>
        <div className="controls">
          <label>
            <input type="checkbox" checked={playerWhite}
                   onChange={e => setPlayerWhite(e.target.checked)} />
            Human plays White
          </label>
          <label>
            <input type="checkbox" checked={playerBlack}
                   onChange={e => setPlayerBlack(e.target.checked)} />
            Human plays Black
          </label>
          <label>
            Think time: {(timeMs / 1000).toFixed(1)}s
            <input type="range" min={500} max={10000} step={500}
                   value={timeMs}
                   onChange={e => setTimeMs(parseInt(e.target.value, 10))} />
          </label>
          <div className="buttons">
            <button onClick={onUndo}>Undo</button>
            <button onClick={onReset}>Reset</button>
          </div>
        </div>
        {aiThinking && <div className="thinking">AI thinking…</div>}
        {searchInfo && (
          <div className="search-info">
            <div>depth <b>{searchInfo.depth}</b></div>
            <div>score <b>{(searchInfo.score / 100).toFixed(2)}</b></div>
            <div>nodes <b>{searchInfo.nodes.toLocaleString()}</b></div>
            <div>time <b>{(searchInfo.elapsedMs / 1000).toFixed(2)}s</b></div>
            {searchInfo.moveNotation && <div>best <b>{searchInfo.moveNotation}</b></div>}
          </div>
        )}
      </div>

      <div className="board-wrap">
        <ChessBoard
          board={gs.board}
          selected={selected}
          legalDestinations={legalDestinations}
          onSquareClick={onSquareClick}
        />
      </div>

      <div className="movelog-wrap">
        <MoveLog moves={gs.move_log} />
      </div>
    </div>
  );
}
