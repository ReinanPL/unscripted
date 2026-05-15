/**
 * Prévia da ficha de personagem (uso em CreateCampaign e no modal).
 *
 * Apresentação: atributos com abreviação, HP em barra simples,
 * perícias e equipamento em listas. Sem nenhum asset gráfico, sem
 * sprite do personagem — a representação é tipográfica.
 */

import { useEffect, useState } from "react";

import { useT } from "../i18n";
import { usePrevious } from "../state/usePrevious";
import type { Character, CharacterAttributes } from "../api/types";

interface CharacterSheetProps {
  character: Character;
  variant?: "preview" | "panel";
}

const ATTRIBUTE_ORDER: (keyof CharacterAttributes)[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

export function CharacterSheet({
  character,
  variant = "preview",
}: CharacterSheetProps) {
  const t = useT();
  const sheetT = (key: string) => t(`state.${key}`);
  const abbr = (a: keyof CharacterAttributes) =>
    t(`state.attributeAbbrev.${a}`);

  const hpPercent = Math.max(
    0,
    Math.min(100, (character.hp_current / Math.max(1, character.hp_max)) * 100),
  );

  // Animação de hit quando HP cai (PRD §6.6).
  const prevHp = usePrevious(character.hp_current);
  const [hitFlash, setHitFlash] = useState(false);
  useEffect(() => {
    if (prevHp === null) return;
    if (character.hp_current < prevHp) {
      setHitFlash(true);
      const handle = setTimeout(() => setHitFlash(false), 460);
      return () => clearTimeout(handle);
    }
  }, [character.hp_current, prevHp]);

  return (
    <article
      className={
        `sheet sheet--${variant}` + (hitFlash ? " fx-hp-hit" : "")
      }
    >
      <header className="sheet__header">
        <h3 className="sheet__name">{character.name}</h3>
        <span className="sheet__level">
          {sheetT("levelLabel")} {character.level}
        </span>
      </header>

      <div className="sheet__hp">
        <div className="sheet__hp-label">
          <span>{sheetT("hpLabel")}</span>
          <span className="sheet__hp-value">
            {character.hp_current}/{character.hp_max}
          </span>
        </div>
        <div
          className="sheet__hp-bar"
          role="progressbar"
          aria-valuenow={character.hp_current}
          aria-valuemin={0}
          aria-valuemax={character.hp_max}
        >
          <div className="sheet__hp-fill" style={{ width: `${hpPercent}%` }} />
        </div>
      </div>

      <section className="sheet__section">
        <h4 className="sheet__section-title">{sheetT("attributesTitle")}</h4>
        <ul className="sheet__attributes">
          {ATTRIBUTE_ORDER.map((attr) => (
            <li key={attr} className="sheet__attribute">
              <span className="sheet__attribute-abbr">{abbr(attr)}</span>
              <span className="sheet__attribute-value">
                {character.attributes[attr]}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {character.skills.length > 0 ? (
        <section className="sheet__section">
          <h4 className="sheet__section-title">{sheetT("skillsTitle")}</h4>
          <ul className="sheet__list">
            {character.skills.map((skill) => (
              <li key={skill}>{skill}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {character.equipment.length > 0 ? (
        <section className="sheet__section">
          <h4 className="sheet__section-title">{sheetT("equipmentTitle")}</h4>
          <ul className="sheet__list">
            {character.equipment.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}
