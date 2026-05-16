/**
 * Grafo de locações em SVG autoral (ADR-039).
 *
 * Renderiza só nós revelados — o backend já filtra (ADR-038). O nó
 * atual tem glow em bronze; arestas são linhas curvas em tom de
 * tinta envelhecida, não setas direcionadas. Sem lib de grafo:
 * complexidade proporcional para 5–15 nós.
 *
 * As coordenadas vêm em sistema lógico (viewBox 800×500). SVG cuida
 * de escalar para o tamanho do painel via preserveAspectRatio.
 */

import { useT } from "../i18n";
import type { GraphResponse } from "../api/types";
import { Compass } from "./Compass";
import { MapGlyph } from "./MapGlyphs";

const VIEW_W = 800;
const VIEW_H = 500;
const NODE_RADIUS = 18;
const NODE_RADIUS_CURRENT = 22;
// Padding em volta do bounding box dos nós revelados — espaço para
// labels acima/abaixo, título no topo, rosa-dos-ventos no canto.
const FIT_PADDING = 140;
const MIN_VIEW = 360;
// Margem do título e do compass em relação às bordas do viewBox.
const TITLE_MARGIN_TOP = 56;
const COMPASS_MARGIN = 70;
const COMPASS_SIZE = 56;

interface LocationGraphProps {
  graph: GraphResponse | null;
  loading: boolean;
}

export function LocationGraph({ graph, loading }: LocationGraphProps) {
  const t = useT();

  return (
    <div className="location-graph">
      <header className="location-graph__header">
        <h2 className="location-graph__title">{t("graph.title")}</h2>
      </header>

      <div className="location-graph__canvas">
        {/* Cantoneiras douradas — vocabulário de cartografia antiga. */}
        <span className="location-graph__corner location-graph__corner--tl" />
        <span className="location-graph__corner location-graph__corner--tr" />
        <span className="location-graph__corner location-graph__corner--bl" />
        <span className="location-graph__corner location-graph__corner--br" />

        {loading ? (
          <p className="location-graph__empty">{t("resume.loading")}</p>
        ) : !graph || graph.nodes.length === 0 ? (
          <p className="location-graph__empty">{t("graph.empty")}</p>
        ) : (
          <GraphSvg graph={graph} />
        )}
      </div>
    </div>
  );
}

interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

function computeViewBox(graph: GraphResponse): ViewBox {
  if (graph.nodes.length === 0) {
    return { x: 0, y: 0, w: VIEW_W, h: VIEW_H };
  }

  const xs = graph.nodes.map((n) => n.position.x);
  const ys = graph.nodes.map((n) => n.position.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const w = Math.max(maxX - minX + FIT_PADDING * 2, MIN_VIEW);
  const h = Math.max(maxY - minY + FIT_PADDING * 2, MIN_VIEW);

  // Centra o bounding box no viewBox final mesmo quando w/h foram
  // expandidos pelo mínimo (1 nó, ex.).
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  return { x: cx - w / 2, y: cy - h / 2, w, h };
}

function GraphSvg({ graph }: { graph: GraphResponse }) {
  const t = useT();
  const nodeById = new Map(graph.nodes.map((n) => [n.id, n]));
  const vb = computeViewBox(graph);

  return (
    <svg
      className="location-graph__svg"
      viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={t("graph.title")}
    >
      <defs>
        <filter id="graph-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        {/* Granulação de pergaminho: turbulência fractal recolorida em
            tom tabaco. Renderizada num <rect> de fundo abaixo das
            arestas, dá ao mapa textura de superfície em vez de tela. */}
        <filter
          id="graph-parchment"
          x="0%"
          y="0%"
          width="100%"
          height="100%"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.9"
            numOctaves="2"
            stitchTiles="stitch"
            seed="7"
          />
          <feColorMatrix
            values="0 0 0 0 0.45
                    0 0 0 0 0.34
                    0 0 0 0 0.18
                    0 0 0 0.10 0"
          />
        </filter>
      </defs>

      {/* Fundo texturizado do mapa — cobre o viewBox inteiro, fica
          atrás das arestas e nós. */}
      <rect
        x={vb.x}
        y={vb.y}
        width={vb.w}
        height={vb.h}
        className="location-graph__parchment"
        filter="url(#graph-parchment)"
      />

      {/* Título caligráfico da região (ADR-041) — só renderiza se o
          capítulo declarou `map_title`. */}
      {graph.title ? (
        <text
          x={vb.x + vb.w / 2}
          y={vb.y + TITLE_MARGIN_TOP}
          textAnchor="middle"
          className="location-graph__title-map"
        >
          {graph.title}
        </text>
      ) : null}

      {/* Rosa-dos-ventos no canto inferior direito. */}
      <Compass
        cx={vb.x + vb.w - COMPASS_MARGIN}
        cy={vb.y + vb.h - COMPASS_MARGIN}
        size={COMPASS_SIZE}
      />

      {/* Arestas — desenhadas antes dos nós para ficarem por baixo. */}
      <g className="location-graph__edges">
        {graph.edges.map((edge, idx) => {
          const a = nodeById.get(edge.source);
          const b = nodeById.get(edge.target);
          if (!a || !b) return null;
          return (
            <line
              key={`${edge.source}-${edge.target}-${idx}`}
              x1={a.position.x}
              y1={a.position.y}
              x2={b.position.x}
              y2={b.position.y}
              className="location-graph__edge"
            />
          );
        })}
      </g>

      {/* Nós */}
      <g className="location-graph__nodes">
        {graph.nodes.map((node) => {
          const isCurrent = node.id === graph.current;
          return (
            <g
              key={node.id}
              className={
                "location-graph__node" +
                (isCurrent ? " location-graph__node--current" : "")
              }
              transform={`translate(${node.position.x}, ${node.position.y})`}
            >
              {isCurrent ? (
                <circle
                  r={NODE_RADIUS_CURRENT + 8}
                  className="location-graph__node-halo"
                  filter="url(#graph-glow)"
                />
              ) : null}
              <circle
                r={isCurrent ? NODE_RADIUS_CURRENT : NODE_RADIUS}
                className="location-graph__node-disc"
              />
              {node.icon ? (
                <MapGlyph
                  name={node.icon}
                  size={(isCurrent ? NODE_RADIUS_CURRENT : NODE_RADIUS) * 1.4}
                />
              ) : (
                <circle
                  r={(isCurrent ? NODE_RADIUS_CURRENT : NODE_RADIUS) - 6}
                  className="location-graph__node-pip"
                />
              )}
              <text
                y={(isCurrent ? NODE_RADIUS_CURRENT : NODE_RADIUS) + 18}
                textAnchor="middle"
                className="location-graph__node-label"
              >
                {node.name}
              </text>
              {isCurrent ? (
                <text
                  y={-(NODE_RADIUS_CURRENT + 12)}
                  textAnchor="middle"
                  className="location-graph__node-here"
                >
                  {t("graph.youAreHere")}
                </text>
              ) : null}
            </g>
          );
        })}
      </g>
    </svg>
  );
}
