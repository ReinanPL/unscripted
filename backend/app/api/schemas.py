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


class GraphNodePosition(BaseModel):
    x: float
    y: float


class GraphNode(BaseModel):
    id: str
    name: str
    position: GraphNodePosition
    # Glifo cartográfico desta cena (ADR-041). Só viaja para nós que
    # estão no resultado — o filtro de `build_graph_response` garante
    # que cenas ocultas não trafegam.
    icon: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphResponse(BaseModel):
    """Subgrafo revelado de locações ao jogador (ADR-038).

    Contém apenas nós cujos ids estão em `flags.locations_revealed`
    (mais a `current_location` por defesa em profundidade). Estado oculto
    nunca trafega aqui.

    `title` corresponde ao `Chapter.map_title` (ADR-041) — metadata
    pública de capítulo, equivalente a um título de mapa em um livro.
    """

    campaign_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    current: str
    title: str | None = None
