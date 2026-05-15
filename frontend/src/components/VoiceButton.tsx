/**
 * Botão de gravar voz no input do jogador.
 *
 * v1 ADR-014: a UI existe; o backend stub responde texto vazio (não há
 * STT real ainda). Comportamento:
 *
 *   - Sem MediaRecorder no navegador: botão ausente.
 *   - Click em "idle" → pede mic, começa a gravar (anel pulsando).
 *   - Click em "recording" → para, envia ao backend, vai para "sending".
 *   - Resposta com texto → onTranscript(text). Resposta vazia → onUnavailable().
 *   - Falha do mic / rede → estado volta a "idle", onError() opcional.
 */

import { useEffect, useRef, useState } from "react";

import { sttFromBlob } from "../api/voice";
import { useT } from "../i18n";

type VoiceState = "idle" | "recording" | "sending";

interface VoiceButtonProps {
  onTranscript: (text: string) => void;
  onUnavailable?: () => void;
  onError?: (message: string) => void;
  disabled?: boolean;
}

export function VoiceButton({
  onTranscript,
  onUnavailable,
  onError,
  disabled,
}: VoiceButtonProps) {
  const t = useT();
  const [state, setState] = useState<VoiceState>("idle");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const supported =
    typeof navigator !== "undefined" &&
    typeof navigator.mediaDevices !== "undefined" &&
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined";

  useEffect(() => {
    return () => {
      // Cleanup: se ainda gravando ao desmontar, para tudo.
      const rec = recorderRef.current;
      if (rec && rec.state !== "inactive") {
        try {
          rec.stop();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  if (!supported) {
    return null;
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        setState("sending");
        try {
          const resp = await sttFromBlob(blob);
          if (resp.text && resp.text.trim().length > 0) {
            onTranscript(resp.text);
          } else if (onUnavailable) {
            onUnavailable();
          }
        } catch (cause) {
          if (onError) {
            onError(cause instanceof Error ? cause.message : "voice failed");
          }
        } finally {
          setState("idle");
        }
      };

      recorder.start();
      setState("recording");
    } catch (cause) {
      setState("idle");
      if (onError) {
        onError(cause instanceof Error ? cause.message : "mic denied");
      }
    }
  }

  function stopRecording() {
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") {
      rec.stop();
    }
  }

  const recording = state === "recording";
  const label = recording ? t("voice.stop") : t("voice.record");

  return (
    <button
      type="button"
      className={`voice-button voice-button--${state}`}
      onClick={recording ? stopRecording : startRecording}
      disabled={disabled || state === "sending"}
      aria-label={label}
      title={label}
      aria-pressed={recording}
    >
      <MicIcon active={recording} />
    </button>
  );
}

function MicIcon({ active }: { active: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M12 2.5a3.25 3.25 0 0 0-3.25 3.25v6.5a3.25 3.25 0 1 0 6.5 0v-6.5A3.25 3.25 0 0 0 12 2.5Zm-6 9.25a.75.75 0 0 1 1.5 0 4.5 4.5 0 0 0 9 0 .75.75 0 1 1 1.5 0 6 6 0 0 1-5.25 5.954V20.25h2.5a.75.75 0 0 1 0 1.5h-6.5a.75.75 0 0 1 0-1.5h2.5v-2.546A6 6 0 0 1 6 11.75Z"
        fill="currentColor"
      />
      {active ? (
        <circle
          cx="12"
          cy="12"
          r="11"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          opacity="0.4"
        />
      ) : null}
    </svg>
  );
}
