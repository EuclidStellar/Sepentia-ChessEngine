import type { Board } from "./engine/chessengine";

interface Props {
  board: Board;
  selected: [number, number] | null;
  legalDestinations: Set<string>;
  onSquareClick: (row: number, col: number) => void;
}

export default function ChessBoard({ board, selected, legalDestinations, onSquareClick }: Props) {
  return (
    <div className="chessboard">
      {board.map((row, r) => (
        <div key={r} className="row">
          {row.map((piece, c) => {
            const isDark = (r + c) % 2 === 1;
            const isSelected = selected && selected[0] === r && selected[1] === c;
            const isLegal = legalDestinations.has(`${r},${c}`);
            return (
              <div
                key={c}
                className={
                  "square" +
                  (isDark ? " dark" : " light") +
                  (isSelected ? " selected" : "") +
                  (isLegal ? " legal" : "")
                }
                onClick={() => onSquareClick(r, c)}
              >
                {piece !== "--" && (
                  <img
                    src={`${import.meta.env.BASE_URL}pieces/${piece}.png`}
                    alt={piece}
                    draggable={false}
                  />
                )}
                {isLegal && <span className="dot" />}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
