import { useCallback, useEffect, useRef } from "react";

/**
 * Fila de áudios para narração falada — toca em ordem.
 *
 * Mantém um `<HTMLAudioElement>` singleton e uma fila de Blobs. Cada
 * `enqueue()` adiciona ao fim; se nada estiver tocando, dispara o
 * primeiro. Quando termina um áudio, dispara o próximo.
 *
 * `clear()` interrompe imediatamente o que estiver tocando, esvazia a
 * fila e revoga os object URLs pendentes. Usado quando o jogador
 * desliga o toggle mid-turno (ADR-049).
 *
 * Não conhece sentenceIndex hoje — turno-inteiro-em-um-áudio é
 * suficiente para o Bloco 2. Bloco 3 (sincronia de frase) introduz
 * `enqueue(blob, index)` para tocar em ordem mesmo quando os áudios
 * chegam fora de ordem do SSE.
 */

export interface AudioQueue {
  enqueue: (blob: Blob) => void;
  clear: () => void;
  /** Cria o elemento de áudio dentro de um user gesture (ex.: click do
   *  toggle). Toca um buffer silencioso e pausa — destrava a política
   *  de autoplay do browser para chamadas subsequentes. */
  unlock: () => void;
}

export function useAudioQueue(): AudioQueue {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const queueRef = useRef<string[]>([]); // object URLs aguardando

  // Garante o elemento <audio> singleton. Não montamos no DOM porque
  // áudio sem controle visual não precisa estar lá — basta uma
  // instância que toca em background.
  function getAudio(): HTMLAudioElement {
    if (audioRef.current) return audioRef.current;
    const el = new Audio();
    el.preload = "auto";
    el.addEventListener("ended", playNext);
    el.addEventListener("error", playNext);
    audioRef.current = el;
    return el;
  }

  function playNext() {
    const el = audioRef.current;
    if (!el) return;
    const previousSrc = el.src;
    const next = queueRef.current.shift();
    if (next) {
      el.src = next;
      el.play().catch(() => {
        // Autoplay bloqueado ou erro de decode — tenta a próxima.
        playNext();
      });
    } else {
      el.removeAttribute("src");
    }
    if (previousSrc && previousSrc.startsWith("blob:")) {
      URL.revokeObjectURL(previousSrc);
    }
  }

  const enqueue = useCallback((blob: Blob) => {
    const url = URL.createObjectURL(blob);
    const el = getAudio();
    if (el.paused && !el.src) {
      el.src = url;
      el.play()
        .then(() => console.info("[tts] audio playing", url))
        .catch((err) => {
          console.warn("[tts] audio play() blocked or failed", err);
          // Mantém o URL na fila pra próxima oportunidade.
          queueRef.current.unshift(url);
        });
    } else {
      console.info("[tts] enqueued (audio busy)", url);
      queueRef.current.push(url);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const unlock = useCallback(() => {
    const el = getAudio();
    if (!el.paused) return;
    // WAV mínimo (44 bytes header + 0 bytes data) — buffer silencioso
    // só pra atravessar a política de autoplay. Não toca som audível.
    const silent =
      "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=";
    el.src = silent;
    el.play()
      .then(() => {
        // Sucesso: o browser aceitou o play. Limpa o src vazio para
        // a próxima enqueue começar do zero.
        el.pause();
        el.removeAttribute("src");
      })
      .catch(() => {
        // Se nem assim destravou, próxima enqueue tentará de novo.
        el.removeAttribute("src");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const clear = useCallback(() => {
    const el = audioRef.current;
    if (el) {
      el.pause();
      const currentSrc = el.src;
      el.removeAttribute("src");
      if (currentSrc && currentSrc.startsWith("blob:")) {
        URL.revokeObjectURL(currentSrc);
      }
    }
    queueRef.current.forEach((url) => {
      if (url.startsWith("blob:")) URL.revokeObjectURL(url);
    });
    queueRef.current = [];
  }, []);

  // Cleanup ao desmontar: para tudo, revoga URLs, remove listeners.
  useEffect(() => {
    return () => {
      const el = audioRef.current;
      if (el) {
        el.pause();
        el.removeEventListener("ended", playNext);
        el.removeEventListener("error", playNext);
      }
      queueRef.current.forEach((url) => {
        if (url.startsWith("blob:")) URL.revokeObjectURL(url);
      });
      queueRef.current = [];
      audioRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { enqueue, clear, unlock };
}
