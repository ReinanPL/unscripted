/**
 * Ornamentação cartográfica decorativa do mapa.
 *
 * Não é dado de capítulo — é decoração visual aplicada relativamente
 * ao viewBox dinâmico, para preencher o "vazio" entre nós com
 * vocabulário de gravura antiga. Mesma família visual dos glifos de
 * nó (traço bronze, fill discreto), mas em escala maior e fora do
 * fluxo de interação.
 *
 * Renderizada uma vez por mapa, acompanha o auto-fit do viewBox.
 * Quando o jogador revela mais nós e o viewBox se expande, a
 * ornamentação se reposiciona naturalmente.
 */

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface MapDecorationsProps {
  vb: ViewBox;
}

export function MapDecorations({ vb }: MapDecorationsProps) {
  // Posições relativas ao viewBox — clusters de ornamento ficam nos
  // quadrantes que normalmente não competem com os nós.
  const trees = [
    { x: vb.x + vb.w * 0.78, y: vb.y + vb.h * 0.22, h: 34 },
    { x: vb.x + vb.w * 0.86, y: vb.y + vb.h * 0.28, h: 24 },
    { x: vb.x + vb.w * 0.71, y: vb.y + vb.h * 0.3, h: 28 },
  ];

  // Rio: curva suave atravessando o canto inferior do mapa, evitando
  // o centro onde ficam os nós e arestas.
  const riverStart = { x: vb.x + vb.w * 0.05, y: vb.y + vb.h * 0.86 };
  const riverMid1 = { x: vb.x + vb.w * 0.3, y: vb.y + vb.h * 0.7 };
  const riverMid2 = { x: vb.x + vb.w * 0.55, y: vb.y + vb.h * 0.82 };
  const riverEnd = { x: vb.x + vb.w * 0.78, y: vb.y + vb.h * 0.68 };
  const riverPath = `M ${riverStart.x} ${riverStart.y} Q ${riverMid1.x} ${riverMid1.y} ${(riverMid1.x + riverMid2.x) / 2} ${(riverMid1.y + riverMid2.y) / 2} T ${riverEnd.x} ${riverEnd.y}`;

  // Topônimo decorativo perto do cluster de árvores — gesto narrativo,
  // não nó interativo.
  const toponym = {
    x: vb.x + vb.w * 0.79,
    y: vb.y + vb.h * 0.13,
    text: "bosque do norte",
  };

  return (
    <g className="location-graph__decorations" aria-hidden="true">
      {trees.map((tree, idx) => (
        <Tree key={`tree-${idx}`} cx={tree.x} cy={tree.y} h={tree.h} />
      ))}

      <path d={riverPath} className="location-graph__river" />

      <text
        x={toponym.x}
        y={toponym.y}
        textAnchor="middle"
        className="location-graph__toponym"
      >
        {toponym.text}
      </text>
    </g>
  );
}

interface TreeProps {
  cx: number;
  cy: number;
  /** Altura da árvore. Largura é proporcional. */
  h: number;
}

function Tree({ cx, cy, h }: TreeProps) {
  const halfW = h * 0.4;
  return (
    <g
      className="location-graph__tree"
      transform={`translate(${cx}, ${cy})`}
    >
      {/* Copa: triângulo apontado para cima, com base em y=h/2 */}
      <path
        d={`M ${-halfW} ${h / 2 - h * 0.18} L 0 ${-h / 2} L ${halfW} ${h / 2 - h * 0.18} Z`}
        className="location-graph__tree-canopy"
      />
      {/* Tronco curto */}
      <line
        x1="0"
        y1={h / 2 - h * 0.18}
        x2="0"
        y2={h / 2}
        className="location-graph__tree-trunk"
      />
    </g>
  );
}
