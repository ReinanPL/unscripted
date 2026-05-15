/**
 * Previews das fichas de personagem para a tela de criação.
 *
 * Espelham `content/characters/{guerreiro,paladino}.yaml`. O backend é
 * a fonte de verdade — quando a partida é criada, ele carrega o YAML
 * e instancia o estado real. Estes presets servem apenas para o
 * jogador comparar antes de escolher.
 *
 * Se os YAMLs mudarem, atualize este arquivo (e considere expor um
 * endpoint /characters como evolução natural quando houver mais que 2).
 */

import type { Character, CharacterClass } from "../api/types";

export const CHARACTER_PRESETS: Record<CharacterClass, Character> = {
  guerreiro: {
    name: "Guerreiro",
    character_class: "guerreiro",
    level: 1,
    hp_current: 12,
    hp_max: 12,
    attributes: {
      strength: 16,
      dexterity: 12,
      constitution: 15,
      intelligence: 10,
      wisdom: 11,
      charisma: 10,
    },
    skills: ["Atletismo", "Intimidação"],
    equipment: [
      "Espada longa",
      "Escudo",
      "Cota de malha",
      "Mochila de aventureiro",
    ],
  },
  paladino: {
    name: "Paladino",
    character_class: "paladino",
    level: 1,
    hp_current: 11,
    hp_max: 11,
    attributes: {
      strength: 15,
      dexterity: 10,
      constitution: 13,
      intelligence: 10,
      wisdom: 12,
      charisma: 16,
    },
    skills: ["Medicina", "Persuasão"],
    equipment: [
      "Espada longa",
      "Escudo",
      "Cota de malha",
      "Símbolo sagrado",
      "Mochila de aventureiro",
    ],
  },
};

export const CHARACTER_ORDER: CharacterClass[] = ["guerreiro", "paladino"];
