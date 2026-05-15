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

const VIEW_W = 800;
const VIEW_H = 500;
const NODE_RADIUS = 18;
const NODE_RADIUS_CURRENT = 22;

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

function GraphSvg({ graph }: { graph: GraphResponse }) {
  const t = useT();
  const nodeById = new Map(graph.nodes.map((n) => [n.id, n]));

  return (
    <svg
      className="location-graph__svg"
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
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
      </defs>

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
              <circle
                r={(isCurrent ? NODE_RADIUS_CURRENT : NODE_RADIUS) - 6}
                className="location-graph__node-pip"
              />
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
