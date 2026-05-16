/**
 * Toggle de narração falada — botão no header da zona play.
 *
 * Estado vive no `useTtsToggle` (persistido em localStorage). Quando
 * o jogador desliga, o `Play.tsx` é responsável por chamar
 * `audioQueue.clear()` para interromper áudio mid-stream — este
 * componente só reflete o estado e expõe o setter.
 *
 * Ícone autoral (SVG inline), mesma estética dos outros botões do
 * header. Riscado quando off; sólido quando on. ADR-049.
 */

import { useT } from "../i18n";

interface TtsToggleProps {
  enabled: boolean;
  onChange: (next: boolean) => void;
}

export function TtsToggle({ enabled, onChange }: TtsToggleProps) {
  const t = useT();
  const label = enabled ? t("voice.ttsOn") : t("voice.ttsOff");
  return (
    <button
      type="button"
      className={`tts-toggle tts-toggle--${enabled ? "on" : "off"}`}
      onClick={() => onChange(!enabled)}
      aria-pressed={enabled}
      aria-label={label}
      title={label}
    >
      <SpeakerIcon active={enabled} />
    </button>
  );
}

function SpeakerIcon({ active }: { active: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M3.75 9.75v4.5a.75.75 0 0 0 .75.75h3.69l4.06 3.5a.75.75 0 0 0 1.25-.57V5.57a.75.75 0 0 0-1.25-.57l-4.06 3.5H4.5a.75.75 0 0 0-.75.75Z"
        fill="currentColor"
      />
      {active ? (
        <>
          <path
            d="M16 8.5a.75.75 0 0 1 1.06 0 5 5 0 0 1 0 7.06.75.75 0 1 1-1.06-1.06 3.5 3.5 0 0 0 0-4.94.75.75 0 0 1 0-1.06Z"
            fill="currentColor"
          />
          <path
            d="M18.5 6a.75.75 0 0 1 1.06 0 8.5 8.5 0 0 1 0 12.06.75.75 0 1 1-1.06-1.06 7 7 0 0 0 0-9.94A.75.75 0 0 1 18.5 6Z"
            fill="currentColor"
            opacity="0.6"
          />
        </>
      ) : (
        <line
          x1="4"
          y1="20"
          x2="20"
          y2="4"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}
