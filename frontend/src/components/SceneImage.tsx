/**
 * Ilustração da cena atual (ADR-040).
 *
 * Tenta carregar /chapters/{chapter}/{imageId}.webp. Se a imagem real
 * existe (autor já gerou no Nano Banana e colocou em
 * frontend/public/chapters/), aparece direto. Caso contrário, renderiza
 * um placeholder SVG ornamentado autoral — selo de pergaminho com
 * cantoneiras douradas e o título da cena em serifada.
 *
 * Nunca substitui o mapa: o mapa é o grafo SVG (ADR-016 / ARQUITETURA
 * §12.5). Aqui é só ilustração de cena.
 */

import { useEffect, useState } from "react";

interface SceneImageProps {
  chapterDir: string;
  imageId: string;
  sceneName: string;
}

type LoadState = "loading" | "loaded" | "missing";

export function SceneImage({ chapterDir, imageId, sceneName }: SceneImageProps) {
  const src = `/chapters/${chapterDir}/${imageId}.webp`;
  const [status, setStatus] = useState<LoadState>("loading");

  // Reseta quando muda a cena.
  useEffect(() => {
    setStatus("loading");
  }, [src]);

  if (status === "missing") {
    return <SceneImagePlaceholder sceneName={sceneName} />;
  }

  return (
    <figure className="scene-image">
      <img
        className="scene-image__img"
        src={src}
        alt={sceneName}
        onLoad={() => setStatus("loaded")}
        onError={() => setStatus("missing")}
        // Esconde até carregar para não piscar broken-image antes do onError.
        style={{ opacity: status === "loaded" ? 1 : 0 }}
      />
      {status === "loading" ? (
        <div className="scene-image__loading" aria-hidden="true" />
      ) : null}
    </figure>
  );
}

function SceneImagePlaceholder({ sceneName }: { sceneName: string }) {
  return (
    <figure
      className="scene-image scene-image--placeholder"
      aria-label={sceneName}
      role="img"
    >
      <svg
        viewBox="0 0 320 200"
        preserveAspectRatio="xMidYMid meet"
        className="scene-image__seal"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <linearGradient id="seal-bg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#241a12" />
            <stop offset="100%" stopColor="#15100b" />
          </linearGradient>
        </defs>

        <rect
          x="6"
          y="6"
          width="308"
          height="188"
          fill="url(#seal-bg)"
          stroke="#7a5b25"
          strokeWidth="1"
        />
        <rect
          x="14"
          y="14"
          width="292"
          height="172"
          fill="none"
          stroke="#b88a3c"
          strokeWidth="0.6"
          opacity="0.55"
        />

        {/* Cantoneiras */}
        <SealCorner cx={14} cy={14} kind="tl" />
        <SealCorner cx={306} cy={14} kind="tr" />
        <SealCorner cx={14} cy={186} kind="bl" />
        <SealCorner cx={306} cy={186} kind="br" />

        {/* Filigrana central muito sutil */}
        <g opacity="0.18" stroke="#b88a3c" strokeWidth="0.5" fill="none">
          <path d="M 60 100 Q 160 60, 260 100" />
          <path d="M 60 100 Q 160 140, 260 100" />
          <circle cx="160" cy="100" r="3" fill="#d8a347" stroke="none" />
        </g>
      </svg>

      <figcaption className="scene-image__caption">
        <span className="scene-image__caption-text">{sceneName}</span>
      </figcaption>
    </figure>
  );
}

interface SealCornerProps {
  cx: number;
  cy: number;
  kind: "tl" | "tr" | "bl" | "br";
}

function SealCorner({ cx, cy, kind }: SealCornerProps) {
  const dx = kind === "tl" || kind === "bl" ? 1 : -1;
  const dy = kind === "tl" || kind === "tr" ? 1 : -1;
  const len = 14;
  return (
    <g stroke="#d8a347" strokeWidth="1" fill="none">
      <line x1={cx} y1={cy} x2={cx + dx * len} y2={cy} />
      <line x1={cx} y1={cy} x2={cx} y2={cy + dy * len} />
      <line
        x1={cx + dx * 4}
        y1={cy + dy * 4}
        x2={cx + dx * (len - 2)}
        y2={cy + dy * 4}
        opacity="0.5"
      />
      <line
        x1={cx + dx * 4}
        y1={cy + dy * 4}
        x2={cx + dx * 4}
        y2={cy + dy * (len - 2)}
        opacity="0.5"
      />
    </g>
  );
}
