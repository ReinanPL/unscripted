from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class CharacterAttributes(BaseModel):
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int


class Character(BaseModel):
    name: str
    character_class: Literal["guerreiro", "paladino"]
    level: int = 1
    hp_current: int
    hp_max: int
    attributes: CharacterAttributes
    skills: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)


class InventoryItem(BaseModel):
    name: str
    description: str = ""
    quantity: int = 1


class Location(BaseModel):
    id: str
    name: str
    description: str = ""


class Flags(BaseModel):
    objectives_completed: list[str] = Field(default_factory=list)
    events_occurred: list[str] = Field(default_factory=list)
    locations_revealed: list[str] = Field(default_factory=list)


class HistoryEntry(BaseModel):
    turn: int
    player_action: str
    narration: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HiddenState(BaseModel):
    """Estado do mundo que o jogador não vê. Nunca exposto pelo GET /state."""

    gm_notes: str = ""
    npc_hidden_info: dict[str, str] = Field(default_factory=dict)


class GameState(BaseModel):
    character: Character
    inventory: list[InventoryItem] = Field(default_factory=list)
    location: Location
    flags: Flags = Field(default_factory=Flags)
    history: list[HistoryEntry] = Field(default_factory=list)
    hidden_state: HiddenState = Field(default_factory=HiddenState)
