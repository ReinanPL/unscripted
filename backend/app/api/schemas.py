from typing import Literal

from pydantic import BaseModel, Field

from app.state.models import Character, Flags, HistoryEntry, InventoryItem, Location


class CampaignCreateRequest(BaseModel):
    character: Literal["guerreiro", "paladino"]


class CampaignCreateResponse(BaseModel):
    campaign_id: str


class ActionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ActionEvent(BaseModel):
    type: Literal[
        "chunk",
        "npc_chunk",
        "done",
        "error",
        "error_preserve_input",
        "rejected",
    ]
    text: str = ""
    npc_id: str | None = None
    turn_number: int | None = None
    category: str | None = None


class CampaignStateResponse(BaseModel):
    campaign_id: str
    character: Character
    inventory: list[InventoryItem]
    location: Location
    flags: Flags


class CampaignLogResponse(BaseModel):
    campaign_id: str
    history: list[HistoryEntry]


class TurnTraceResponse(BaseModel):
    campaign_id: str
    turn_number: int
    trace: dict  # type: ignore[type-arg]
