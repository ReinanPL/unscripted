from typing import Literal

from pydantic import BaseModel, Field

from app.state.models import Character, Flags, HistoryEntry, InventoryItem, Location


class CampaignCreateRequest(BaseModel):
    character: Literal["guerreiro", "paladino"]


class CampaignCreateResponse(BaseModel):
    campaign_id: str


class ActionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    # Se True, o backend dispara TTS por frase em paralelo ao texto e emite
    # `audio_sentence` no SSE (ADR-048). Default False: zero chamadas TTS,
    # custo zero. O frontend só seta True quando o toggle TTS está ligado.
    tts_enabled: bool = False


class ActionEvent(BaseModel):
    type: Literal[
        "chunk",
        "npc_chunk",
        "audio_sentence",
        "done",
        "error",
        "error_preserve_input",
        "rejected",
    ]
    text: str = ""
    npc_id: str | None = None
    turn_number: int | None = None
    category: str | None = None
    # Campos do audio_sentence: índice da frase no turno e MP3 base64.
    sentence_index: int | None = None
    audio_b64: str = ""
    mime: str = ""


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


class VeiledNode(BaseModel):
    """Cena cuja existência é pública mas conteúdo é oculto (ADR-042).

    Aparece no mapa como silhueta — só `id` e `position` trafegam. Por
    contrato (e por design do schema), esta classe **não tem** `name`,
    `icon`, `description`, `read_aloud`, `present`, nem `connections`.
    Adicionar qualquer campo aqui é rompimento explícito do ADR-042.
    """

    id: str
    position: GraphNodePosition


class GraphResponse(BaseModel):
    """Subgrafo de locações para o jogador (ADR-038 + ADR-042).

    `nodes` contém cenas reveladas (id, name, icon, position). `edges`
    contém apenas arestas entre dois nós revelados — adjacência com
    cenas veladas não trafega.

    `veiled_nodes` contém cenas não-reveladas como silhuetas: só `id`
    e `position`. O conteúdo (nome, ícone, descrição, NPCs, conexões)
    permanece sob o filtro de estado oculto.

    `title` corresponde ao `Chapter.map_title` (ADR-041) — metadata
    pública de capítulo, equivalente a um título de mapa em um livro.
    """

    campaign_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    veiled_nodes: list[VeiledNode] = Field(default_factory=list)
    current: str
    title: str | None = None
