/**
 * Caixa de entrada da ação do jogador.
 *
 * Comportamento:
 *   - Enter envia, Shift+Enter quebra linha.
 *   - Durante o turno (disabled), input fica em readonly visual.
 *   - O valor é controlado externamente — o pai (Play) preserva a
 *     entrada quando o backend falha (ADR-020).
 *   - VoiceButton à esquerda quando o navegador suporta MediaRecorder.
 *     Transcrição retornada concatena ao valor atual (não substitui).
 */

import { useRef, useEffect } from "react";

import { useT } from "../i18n";
import { VoiceButton } from "./VoiceButton";

interface ActionInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  /** Auto-focus após carregar a tela / depois de um done. */
  focusKey?: string | number;
  /** Aviso opcional do pai quando a voz cai no stub vazio. */
  onVoiceUnavailable?: () => void;
}

export function ActionInput({
  value,
  onChange,
  onSubmit,
  disabled,
  focusKey,
  onVoiceUnavailable,
}: ActionInputProps) {
  const t = useT();
  const ref = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (disabled) return;
    ref.current?.focus();
  }, [disabled, focusKey]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled && value.trim().length > 0) {
        onSubmit();
      }
    }
  }

  function handleTranscript(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;
    onChange(value ? `${value} ${trimmed}`.trim() : trimmed);
  }

  return (
    <form
      className="action-input"
      onSubmit={(e) => {
        e.preventDefault();
        if (!disabled && value.trim().length > 0) onSubmit();
      }}
    >
      <VoiceButton
        onTranscript={handleTranscript}
        onUnavailable={onVoiceUnavailable}
        disabled={disabled}
      />
      <textarea
        ref={ref}
        className="action-input__field"
        rows={2}
        placeholder={t("play.inputPlaceholder")}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        aria-label={t("play.inputPlaceholder")}
      />
      <button
        type="submit"
        className="action-input__submit"
        disabled={disabled || value.trim().length === 0}
      >
        {disabled ? t("play.submitting") : t("play.submit")}
      </button>
    </form>
  );
}
