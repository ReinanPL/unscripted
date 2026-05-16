/**
 * Rosa-dos-ventos minimalista para o canto do mapa.
 *
 * 4 pontas em estrela, círculo discreto envolvente, "N" no topo em
 * tipografia serifada. Bronze fade no corpo, bronze bright na ponta
 * norte. Sem S/L/O — gesto cartográfico minimalista é suficiente,
 * cresce o catálogo só se virar necessidade real.
 */

interface CompassProps {
  /** Centro da rosa-dos-ventos no sistema de coordenadas do viewBox. */
  cx: number;
  cy: number;
  /** Diâmetro total (incluindo as pontas externas). */
  size?: number;
}

export function Compass({ cx, cy, size = 60 }: CompassProps) {
  const r = size / 2;
  const innerR = r * 0.35;

  return (
    <g
      transform={`translate(${cx}, ${cy})`}
      className="location-graph__compass"
      aria-hidden="true"
    >
      {/* Círculo discreto envolvente */}
      <circle
        r={r * 0.85}
        className="location-graph__compass-ring"
        fill="none"
      />

      {/* Estrela de 4 pontas — paths em losangos cruzados */}
      {/* Ponta Norte (destacada) */}
      <path
        d={`M 0 ${-r} L ${innerR * 0.35} 0 L 0 ${innerR} L ${-innerR * 0.35} 0 Z`}
        className="location-graph__compass-arm location-graph__compass-arm--north"
      />
      {/* Ponta Sul */}
      <path
        d={`M 0 ${r} L ${innerR * 0.35} 0 L 0 ${-innerR} L ${-innerR * 0.35} 0 Z`}
        className="location-graph__compass-arm"
      />
      {/* Ponta Leste */}
      <path
        d={`M ${r} 0 L 0 ${innerR * 0.35} L ${-innerR} 0 L 0 ${-innerR * 0.35} Z`}
        className="location-graph__compass-arm"
      />
      {/* Ponta Oeste */}
      <path
        d={`M ${-r} 0 L 0 ${innerR * 0.35} L ${innerR} 0 L 0 ${-innerR * 0.35} Z`}
        className="location-graph__compass-arm"
      />

      {/* Letra N acima da estrela */}
      <text
        x="0"
        y={-r - size * 0.12}
        textAnchor="middle"
        className="location-graph__compass-letter"
      >
        N
      </text>
    </g>
  );
}
