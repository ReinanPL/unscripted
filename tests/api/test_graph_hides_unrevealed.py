"""Teste de invariante crítico (ADR-038).

`/graph` NUNCA expõe locações que o jogador não revelou. O endpoint
delega para `build_graph_response`, que filtra antes de devolver. Aqui
testamos a função pura, sem subir FastAPI / DB — o teste é rápido,
determinístico, e cobre o invariante onde ele realmente está.
"""

from __future__ import annotations

import json

import pytest

from app.api.graph import build_graph_response
from app.state.adventure_schema import Chapter, Connection, Scene, ScenePosition


def _make_chapter() -> Chapter:
    """Capítulo de teste com 5 cenas. Topologia:

        cozinha
           │
        taverna ─── praca ─── estrada ─── clareira
    """
    return Chapter(
        id="cap-test",
        title="cap teste",
        premise="p",
        background="b",
        starting_scene="taverna",
        progress_condition="ok",
        map_title="Região Teste",
        scenes=[
            Scene(
                id="taverna",
                name="Taverna",
                description="d",
                position=ScenePosition(x=160, y=250),
                icon="tavern",
                connections=[
                    Connection(to="praca"),
                    Connection(to="cozinha"),
                ],
            ),
            Scene(
                id="cozinha",
                name="Cozinha",
                description="d",
                position=ScenePosition(x=160, y=100),
                icon="interior_segredo",
                connections=[Connection(to="taverna")],
            ),
            Scene(
                id="praca",
                name="Praça",
                description="d",
                position=ScenePosition(x=340, y=250),
                icon="square_segredo",
                connections=[
                    Connection(to="taverna"),
                    Connection(to="estrada"),
                ],
            ),
            Scene(
                id="estrada",
                name="Estrada",
                description="d",
                position=ScenePosition(x=520, y=250),
                icon="road_segredo",
                connections=[
                    Connection(to="praca"),
                    Connection(to="clareira"),
                ],
            ),
            Scene(
                id="clareira",
                name="Clareira",
                description="d",
                position=ScenePosition(x=700, y=250),
                icon="clearing_segredo",
                connections=[Connection(to="estrada")],
            ),
        ],
    )


_HIDDEN_IDS = ("praca", "cozinha", "estrada", "clareira")
_HIDDEN_NAMES = ("Praça", "Cozinha", "Estrada", "Clareira")
# Ícones dos não-revelados usam o sufixo `_segredo` para o teste detectar
# vazamento caso o icon trafegue por engano (ADR-041).
_HIDDEN_ICONS = (
    "interior_segredo",
    "square_segredo",
    "road_segredo",
    "clearing_segredo",
)


def test_only_revealed_scene_appears_in_nodes():
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna"],
        current_location="taverna",
    )
    ids = {n.id for n in resp.nodes}
    assert ids == {"taverna"}, (
        f"esperava só 'taverna', recebeu {ids}"
    )


def test_hidden_scenes_never_appear_in_payload_string():
    """Defesa em profundidade: nenhuma cena oculta sequer aparece como
    string no JSON serializado, mesmo em campos auxiliares."""
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna"],
        current_location="taverna",
    )
    payload = json.dumps(resp.model_dump(), ensure_ascii=False)
    for hidden_id in _HIDDEN_IDS:
        assert hidden_id not in payload, (
            f"id de cena oculta '{hidden_id}' vazou no payload: {payload}"
        )
    for hidden_name in _HIDDEN_NAMES:
        assert hidden_name not in payload, (
            f"nome de cena oculta '{hidden_name}' vazou no payload"
        )
    for hidden_icon in _HIDDEN_ICONS:
        assert hidden_icon not in payload, (
            f"icon de cena oculta '{hidden_icon}' vazou no payload"
        )


def test_edge_only_when_both_endpoints_revealed():
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna", "praca"],
        current_location="taverna",
    )
    ids = {n.id for n in resp.nodes}
    assert ids == {"taverna", "praca"}
    assert len(resp.edges) == 1
    edge = resp.edges[0]
    assert {edge.source, edge.target} == {"taverna", "praca"}


def test_edge_to_hidden_neighbor_not_included():
    """Cena revelada com vizinho oculto: aresta NÃO aparece."""
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna"],
        current_location="taverna",
    )
    assert resp.edges == []


def test_current_location_always_included_even_if_not_in_revealed():
    """Defesa em profundidade: estado inconsistente (locations_revealed
    sem a current_location) não derruba a resposta — a current é sempre
    incluída."""
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=[],
        current_location="estrada",
    )
    ids = {n.id for n in resp.nodes}
    assert ids == {"estrada"}
    assert resp.current == "estrada"


def test_edges_are_deduplicated_when_both_directions_exist():
    """Conexões bidirecionais (A→B e B→A) viram uma aresta só no payload."""
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna", "praca", "estrada"],
        current_location="praca",
    )
    pairs = {tuple(sorted([e.source, e.target])) for e in resp.edges}
    assert pairs == {("praca", "taverna"), ("estrada", "praca")}
    assert len(resp.edges) == len(pairs)  # nenhuma duplicata


def test_position_preserved_from_yaml_authoring():
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna"],
        current_location="taverna",
    )
    taverna = next(n for n in resp.nodes if n.id == "taverna")
    assert taverna.position.x == pytest.approx(160.0)
    assert taverna.position.y == pytest.approx(250.0)


def test_icon_propagated_for_revealed_scene():
    """Cenas reveladas propagam o `icon` autoral para o frontend (ADR-041)."""
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna"],
        current_location="taverna",
    )
    taverna = next(n for n in resp.nodes if n.id == "taverna")
    assert taverna.icon == "tavern"


def test_icon_is_optional():
    """Cena sem `icon` declarada vira `None` no payload — frontend decide
    o fallback (pip dourado)."""
    chapter = Chapter(
        id="cap",
        title="t",
        premise="p",
        background="b",
        starting_scene="a",
        progress_condition="ok",
        scenes=[Scene(id="a", name="A", description="d")],
    )
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["a"],
        current_location="a",
    )
    assert resp.nodes[0].icon is None


def test_map_title_is_public_metadata():
    """`map_title` é metadata pública do capítulo (ADR-041) — aparece
    no payload independente de quantas cenas o jogador revelou,
    inclusive no turno 0 (apenas a starting_scene revelada)."""
    chapter = _make_chapter()
    resp_t0 = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna"],
        current_location="taverna",
    )
    assert resp_t0.title == "Região Teste"

    resp_explorado = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna", "praca", "estrada", "clareira", "cozinha"],
        current_location="clareira",
    )
    assert resp_explorado.title == "Região Teste"


def test_map_title_none_when_chapter_omits_it():
    """Capítulos sem `map_title` declarado devolvem `title=None`. O
    frontend simplesmente não renderiza o título nesse caso."""
    chapter = Chapter(
        id="cap",
        title="t",
        premise="p",
        background="b",
        starting_scene="a",
        progress_condition="ok",
        scenes=[Scene(id="a", name="A", description="d")],
    )
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["a"],
        current_location="a",
    )
    assert resp.title is None


def test_fallback_position_used_when_yaml_omits_it():
    chapter = Chapter(
        id="cap",
        title="t",
        premise="p",
        background="b",
        starting_scene="a",
        progress_condition="ok",
        scenes=[
            Scene(id="a", name="A", description="d", connections=[Connection(to="b")]),
            Scene(id="b", name="B", description="d"),
        ],
    )
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["a", "b"],
        current_location="a",
    )
    assert {n.id for n in resp.nodes} == {"a", "b"}
    a = next(n for n in resp.nodes if n.id == "a")
    b = next(n for n in resp.nodes if n.id == "b")
    # layout determinístico: x cresce com índice; mesma y
    assert a.position.x < b.position.x
    assert a.position.y == b.position.y == pytest.approx(250.0)
