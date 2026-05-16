/**
 * Glifos cartográficos dos nós do mapa (ADR-041).
 *
 * Cada glifo é um <g> SVG no mesmo traço bronze, mesma altura visual.
 * Recebe um `name` (chave aberta — vem do YAML do capítulo via /graph)
 * e retorna o desenho correspondente, ou `null` se desconhecido (o
 * componente que chama cuida do fallback ao pip dourado atual).
 *
 * Convenção de desenho: stroke = `currentColor` (frontend tematiza),
 * fill = `none` no path principal, traços ~1.6, centralizado em (0,0)
 * num quadro lógico de ~24×24. O LocationGraph aplica `transform`
 * para escalar/posicionar dentro do círculo do nó.
 */

interface MapGlyphProps {
  name: string | null | undefined;
  size?: number;
}

export function MapGlyph({ name, size = 22 }: MapGlyphProps) {
  const renderer = GLYPHS[name ?? ""];
  if (!renderer) return null;
  const half = size / 2;
  return (
    <g
      className="location-graph__glyph"
      transform={`scale(${size / 24}) translate(${-12}, ${-12})`}
      data-glyph={name}
      aria-hidden="true"
      // O viewBox lógico de cada glifo é 24×24 centrado em (12,12).
      // O transform acima posiciona em (0,0) e escala para `size`.
      data-size={half}
    >
      {renderer()}
    </g>
  );
}

type Renderer = () => JSX.Element;

const GLYPHS: Record<string, Renderer> = {
  // Caneca de cerveja: corpo retangular arredondado + alça à direita +
  // espuma como duas elevações no topo.
  tavern: () => (
    <>
      {/* Espuma */}
      <path
        d="M8 8 Q10 6 12 8 Q14 6 16 8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      {/* Corpo da caneca */}
      <rect
        x="7"
        y="9"
        width="8"
        height="10"
        rx="0.8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      {/* Alça */}
      <path
        d="M15 11 Q18 11.5 18 14 Q18 16.5 15 17"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      {/* Listra horizontal */}
      <line
        x1="7.4"
        y1="13"
        x2="14.6"
        y2="13"
        stroke="currentColor"
        strokeWidth="1"
        opacity="0.7"
      />
    </>
  ),

  // Recinto fechado: arco/porta com nicho interior.
  interior: () => (
    <>
      {/* Moldura externa (porta arqueada) */}
      <path
        d="M7 19 L7 12 Q7 7 12 7 Q17 7 17 12 L17 19 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      {/* Nicho interno menor */}
      <path
        d="M10 19 L10 14 Q10 11 12 11 Q14 11 14 14 L14 19"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        opacity="0.75"
      />
    </>
  ),

  // Praça/poço: cruz central marcando ponto + 4 pedras nos cantos.
  square: () => (
    <>
      {/* Cruz central */}
      <line
        x1="12"
        y1="8"
        x2="12"
        y2="16"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <line
        x1="8"
        y1="12"
        x2="16"
        y2="12"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      {/* 4 pedras dispostas */}
      <circle cx="7" cy="7" r="1" fill="currentColor" opacity="0.85" />
      <circle cx="17" cy="7" r="1" fill="currentColor" opacity="0.85" />
      <circle cx="7" cy="17" r="1" fill="currentColor" opacity="0.85" />
      <circle cx="17" cy="17" r="1" fill="currentColor" opacity="0.85" />
    </>
  ),

  // Estrada: linha sinuosa entre duas árvores estilizadas.
  road: () => (
    <>
      {/* Caminho sinuoso */}
      <path
        d="M6 18 Q10 14 12 12 Q14 10 18 6"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      {/* Árvore 1 (canto inferior esquerdo) */}
      <path
        d="M5 16 L5 19 M3.5 17 L5 14.5 L6.5 17 Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="0.8"
        strokeLinejoin="round"
        opacity="0.85"
      />
      {/* Árvore 2 (canto superior direito) */}
      <path
        d="M19 5 L19 8 M17.5 6 L19 3.5 L20.5 6 Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="0.8"
        strokeLinejoin="round"
        opacity="0.85"
      />
    </>
  ),

  // Clareira: chama estilizada (fogueira no centro).
  clearing: () => (
    <>
      {/* Chama externa */}
      <path
        d="M12 5 Q15 9 14.5 13 Q14 17 12 19 Q10 17 9.5 13 Q9 9 12 5 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      {/* Chama interna */}
      <path
        d="M12 10 Q13.2 12 12.8 14.5 Q12.3 16 12 17 Q11.7 16 11.2 14.5 Q10.8 12 12 10 Z"
        fill="currentColor"
        opacity="0.55"
      />
    </>
  ),
};
