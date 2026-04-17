import type { Move } from "./engine/chessengine";

export default function MoveLog({ moves }: { moves: Move[] }) {
  const rows: { num: number; white: string; black: string }[] = [];
  for (let i = 0; i < moves.length; i += 2) {
    rows.push({
      num: Math.floor(i / 2) + 1,
      white: moves[i].toString(),
      black: moves[i + 1]?.toString() ?? "",
    });
  }
  return (
    <div className="movelog">
      <h2>Moves</h2>
      <ol>
        {rows.map(r => (
          <li key={r.num}>
            <span className="white">{r.white}</span>
            <span className="black">{r.black}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
