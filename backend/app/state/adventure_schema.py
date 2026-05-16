from __future__ import annotations

import pathlib
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class AdventureHiddenState(BaseModel):
    """Informação do mundo que o jogador não vê (GM-only).

    Distinta de state.models.HiddenState (estado oculto da partida em curso).
    Esta versão pertence à definição estática da aventura.
    """

    trait: str = ""
    notes: str = ""


class Connection(BaseModel):
    """Aresta do grafo de locações entre duas cenas da mesma aventura."""

    to: str
    description: str = ""


class ScenePosition(BaseModel):
    """Posição autoral da cena no grafo de locações (ADR-039).

    Sistema de coordenadas lógico — o frontend escolhe o viewBox SVG final
    e aplica preserveAspectRatio. Convenção: x ∈ [80, 720], y ∈ [80, 420]
    com viewBox típico 800×500. Valores fora desse intervalo são aceitos
    (o frontend ajusta), só não rendem o resultado mais agradável.
    """

    x: float
    y: float


class ImageBriefing(BaseModel):
    """Briefing escrito para gerar uma imagem fora do sistema (Nano Banana)."""

    id: str
    scene: str
    description: str
    atmosphere: str = ""
    style: str = ""
    elements: list[str] = Field(default_factory=list)


class NPC(BaseModel):
    name: str
    personality: str
    motivation: str
    knowledge: str = ""
    hidden_state: AdventureHiddenState = Field(default_factory=AdventureHiddenState)


class Encounter(BaseModel):
    id: str
    kind: Literal["combat", "social", "exploration"]
    trigger: str
    description: str
    consequences_success: str = ""
    consequences_failure: str = ""


class Scene(BaseModel):
    id: str
    name: str
    description: str
    read_aloud: str = ""
    present: list[str] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    position: ScenePosition | None = None
    # Glifo cartográfico da cena no mapa (ADR-041). Chave aberta — o
    # frontend tem um dicionário `name → <g> SVG` com fallback ao pip
    # dourado quando o ícone for desconhecido ou ausente.
    icon: str | None = None


class Chapter(BaseModel):
    id: str
    title: str
    premise: str
    background: str
    starting_scene: str
    scenes: list[Scene]
    npcs: list[NPC] = Field(default_factory=list)
    encounters: list[Encounter] = Field(default_factory=list)
    progress_condition: str
    hook_next: str = ""
    image_briefings: list[ImageBriefing] = Field(default_factory=list)
    # Título caligráfico da região no topo do mapa (ADR-041). Opcional
    # para retrocompatibilidade — capítulos sem este campo renderizam
    # o mapa sem título.
    map_title: str | None = None

    @model_validator(mode="after")
    def _validate_references(self) -> Chapter:
        scene_ids = {s.id for s in self.scenes}
        if len(scene_ids) != len(self.scenes):
            raise ValueError("ids de cenas duplicados")
        if self.starting_scene not in scene_ids:
            raise ValueError(
                f"starting_scene '{self.starting_scene}' não corresponde a nenhuma cena"
            )
        for scene in self.scenes:
            for conn in scene.connections:
                if conn.to not in scene_ids:
                    raise ValueError(
                        f"cena '{scene.id}' tem conexão para '{conn.to}', "
                        "que não existe no capítulo"
                    )
        enc_ids = [e.id for e in self.encounters]
        if len(enc_ids) != len(set(enc_ids)):
            raise ValueError("ids de encontros duplicados")
        return self

    def to_lore_text(self) -> str:
        """Serialização canônica do capítulo como texto para o RAG (corpus de lore).

        Estado oculto não entra — o NarratorAgent narra apenas o que o jogador
        pode perceber. Trait oculto fica disponível para outros agentes via outros
        meios (no v1, isso é o suficiente).
        """
        parts: list[str] = []
        parts.append(f"# {self.title}\n")
        parts.append(f"## Premissa\n{self.premise}\n")
        for scene in self.scenes:
            parts.append(f"## Cena: {scene.name}\n{scene.description}")
            if scene.read_aloud:
                parts.append(f"Texto de abertura: {scene.read_aloud}")
            if scene.present:
                parts.append(f"Presente nesta cena: {', '.join(scene.present)}")
            if scene.connections:
                conns = "; ".join(
                    f"{c.to} ({c.description})" if c.description else c.to
                    for c in scene.connections
                )
                parts.append(f"Conexões: {conns}")
        for npc in self.npcs:
            parts.append(
                f"## NPC: {npc.name}\nPersonalidade: {npc.personality}\nMotivação: {npc.motivation}"
            )
            if npc.knowledge:
                parts.append(f"O que sabe: {npc.knowledge}")
        for enc in self.encounters:
            parts.append(f"## Encontro: {enc.id} ({enc.kind})\n{enc.description}")
            parts.append(f"Gatilho: {enc.trigger}")
        return "\n\n".join(parts)


class Adventure(BaseModel):
    id: str
    title: str
    language: str = "pt"
    chapters: list[Chapter]

    @classmethod
    def from_yaml(cls, path: pathlib.Path) -> Adventure:
        """Carrega e valida uma aventura a partir de um arquivo YAML.

        Levanta `pydantic.ValidationError` para conteúdo malformado,
        `yaml.YAMLError` para YAML sintaticamente inválido,
        `FileNotFoundError` se o arquivo não existir.
        """
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return cls.model_validate(data)
