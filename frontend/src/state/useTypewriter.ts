import { useEffect, useRef, useState } from "react";

/**
 * Cadência editorial para narração em streaming.
 *
 * O LLM emite tokens muito rápido — 50+ por segundo em PT-BR com OpenAI,
 * mais lento mas ainda rápido com Groq. Renderizar isso direto gera
 * uma sensação de "saída de chat" em vez de "leitura conduzida".
 *
 * Este hook recebe o `fullText` (que cresce conforme chunks chegam pelo
 * SSE) e revela ao jogador no ritmo de `charsPerSecond`, retornando
 * `displayed`. Quando o jogador termina o turno (skip=true), pula
 * direto para o fim em vez de fazê-lo esperar a animação.
 *
 * Implementação com `requestAnimationFrame` + delta de tempo: mais
 * suave que `setInterval` e respeita `prefers-reduced-motion` quando
 * o componente passa skip=true incondicionalmente.
 */

export interface UseTypewriterOptions {
  /** Pula a animação e mostra o texto completo. Útil quando o turno fecha. */
  skip?: boolean;
}

export function useTypewriter(
  fullText: string,
  charsPerSecond: number,
  options: UseTypewriterOptions = {},
): string {
  const [displayed, setDisplayed] = useState("");
  // Refs evitam que mudanças no fullText ou no skip re-criem o loop de
  // animação — o `tick` lê via ref e fica vivo por toda a vida do hook.
  const fullTextRef = useRef(fullText);
  const skipRef = useRef(!!options.skip);
  fullTextRef.current = fullText;
  skipRef.current = !!options.skip;

  useEffect(() => {
    let cancelled = false;
    let lastTs = performance.now();
    let pending = 0;

    function tick(ts: number) {
      if (cancelled) return;
      const dt = (ts - lastTs) / 1000;
      lastTs = ts;

      setDisplayed((prev) => {
        const target = fullTextRef.current;
        if (skipRef.current) return target;
        if (prev.length >= target.length) {
          // Já mostrou tudo que chegou; aguarda mais texto.
          pending = 0;
          return prev;
        }
        pending += dt * charsPerSecond;
        const wholeChars = Math.floor(pending);
        if (wholeChars <= 0) return prev;
        pending -= wholeChars;
        const nextLen = Math.min(prev.length + wholeChars, target.length);
        return target.slice(0, nextLen);
      });

      requestAnimationFrame(tick);
    }

    const handle = requestAnimationFrame(tick);
    return () => {
      cancelled = true;
      cancelAnimationFrame(handle);
    };
  }, [charsPerSecond]);

  // Reset quando o texto-alvo encolhe (turno novo no mesmo componente):
  // se `fullText` ficou menor que `displayed`, voltamos pro começo.
  useEffect(() => {
    if (fullText.length < displayed.length) {
      setDisplayed(fullText);
    }
  }, [fullText, displayed.length]);

  return displayed;
}
