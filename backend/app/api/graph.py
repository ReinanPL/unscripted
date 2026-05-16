"""Construção do subgrafo de locações revelado ao jogador (ADR-038).

Função pura: recebe o capítulo, o conjunto de locações reveladas e a
locação atual, devolve o `GraphResponse` que o frontend renderiza. Não
toca em banco, agente ou LLM — é só transformação de dados.

Invariante crítico (ADR-038): nenhuma cena fora do conjunto revelado
trafega no resultado, nem como flag, nem como nome, nem como aresta.
O teste de invariante (`tests/api/test_graph_hides_unrevealed.py`)
protege isso.
"""

from __future__ import annotations

from app.api.schemas import (
    GraphEdge,
    GraphNode,
    GraphNodePosition,
    GraphResponse,
    VeiledNode,
)
from app.state.adventure_schema import Chapter, ScenePosition


def build_graph_response(
    chapter: Chapter,
    *,
    campaign_id: str,
    locations_revealed: list[str],
    current_location: str,
) -> GraphResponse:
    """Constrói o subgrafo revelado.

    A locação atual é sempre incluída no resultado, mesmo que `locations_revealed`
    não a mencione — defesa em profundidade contra estado inconsistente.
    Arestas entre duas cenas reveladas aparecem como aresta única (não-direcional
    na renderização final), sem duplicar `A→B` e `B→A`.
    """
    revealed: set[str] = set(locations_revealed) | {current_location}

    nodes: list[GraphNode] = []
    for scene in chapter.scenes:
        if scene.id not in revealed:
            continue
        position = scene.position or _fallback_position(chapter, scene.id)
        nodes.append(
            GraphNode(
                id=scene.id,
                name=scene.name,
                position=GraphNodePosition(x=position.x, y=position.y),
                icon=scene.icon,
            )
        )

    seen_pairs: set[tuple[str, str]] = set()
    edges: list[GraphEdge] = []
    for scene in chapter.scenes:
        if scene.id not in revealed:
            continue
        for conn in scene.connections:
            if conn.to not in revealed:
                continue
            pair = sorted([scene.id, conn.to])
            key: tuple[str, str] = (pair[0], pair[1])
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            edges.append(GraphEdge(source=scene.id, target=conn.to))

    # Silhuetas das cenas não-reveladas (ADR-042): só id e position
    # trafegam. O VeiledNode schema não tem campos para name/icon/etc —
    # impossível vazá-los por aqui.
    veiled_nodes: list[VeiledNode] = []
    for scene in chapter.scenes:
        if scene.id in revealed:
            continue
        position = scene.position or _fallback_position(chapter, scene.id)
        veiled_nodes.append(
            VeiledNode(
                id=scene.id,
                position=GraphNodePosition(x=position.x, y=position.y),
            )
        )

    return GraphResponse(
        campaign_id=campaign_id,
        nodes=nodes,
        edges=edges,
        veiled_nodes=veiled_nodes,
        current=current_location,
        title=chapter.map_title,
    )


def _fallback_position(chapter: Chapter, scene_id: str) -> ScenePosition:
    """Layout horizontal por índice — determinístico, legível para até ~10 nós.

    Usado apenas quando a cena revelada não declarou `position` no YAML.
    Capítulos curados explicitamente declaram (ADR-039); o fallback evita
    que um capítulo novo, ainda sem layout autoral, devolva grafo quebrado.
    """
    try:
        idx = next(i for i, s in enumerate(chapter.scenes) if s.id == scene_id)
    except StopIteration:
        return ScenePosition(x=400.0, y=250.0)
    spacing = 800.0 / max(1, len(chapter.scenes) + 1)
    return ScenePosition(x=spacing * (idx + 1), y=250.0)
