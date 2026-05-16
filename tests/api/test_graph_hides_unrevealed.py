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
from app.api.schemas import VeiledNode
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
    """Defesa em profundidade: ADR-042 permite ids de não-revelados em
    `veiled_nodes`, mas nomes e ícones NUNCA vazam — em lugar nenhum
    do payload. Ids também não podem aparecer em `nodes` (revelados)
    nem em `edges`.
    """
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna"],
        current_location="taverna",
    )
    payload = json.dumps(resp.model_dump(), ensure_ascii=False)

    # Nomes e ícones nunca aparecem em lugar algum do payload.
    for hidden_name in _HIDDEN_NAMES:
        assert hidden_name not in payload, (
            f"nome de cena oculta '{hidden_name}' vazou no payload"
        )
    for hidden_icon in _HIDDEN_ICONS:
        assert hidden_icon not in payload, (
            f"icon de cena oculta '{hidden_icon}' vazou no payload"
        )

    # Ids de cenas ocultas: aparecem em veiled_nodes (ADR-042), mas
    # nunca em nodes revelados nem em edges.
    revealed_ids = {n.id for n in resp.nodes}
    edge_ids = {e.source for e in resp.edges} | {e.target for e in resp.edges}
    for hidden_id in _HIDDEN_IDS:
        assert hidden_id not in revealed_ids, (
            f"id de cena oculta '{hidden_id}' apareceu em nodes (revelados)"
        )
        assert hidden_id not in edge_ids, (
            f"id de cena oculta '{hidden_id}' apareceu em edges"
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


def test_unrevealed_scenes_appear_as_veiled_nodes():
    """ADR-042: cenas não-reveladas aparecem como silhuetas em
    `veiled_nodes` com `id` + `position`, nada mais. As 4 cenas ocultas
    do `_make_chapter()` devem estar todas presentes quando só a
    taverna está revelada."""
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna"],
        current_location="taverna",
    )
    veiled_ids = {v.id for v in resp.veiled_nodes}
    assert veiled_ids == set(_HIDDEN_IDS), (
        f"esperava silhuetas para {_HIDDEN_IDS}, recebeu {veiled_ids}"
    )
    # Posições preservadas — o frontend depende disso para auto-fit.
    by_id = {v.id: v.position for v in resp.veiled_nodes}
    assert by_id["cozinha"].x == 160 and by_id["cozinha"].y == 100
    assert by_id["clareira"].x == 700 and by_id["clareira"].y == 250


def test_veiled_node_has_no_name_or_icon():
    """Cinto + suspensório: VeiledNode tem APENAS `id` e `position`.
    Para cada campo sensível conhecido — name, icon, description,
    read_aloud, present, connections — assert que NÃO existe no schema.
    Defesa contra 'alguém adicionou campo aparentemente inocente'."""
    fields = set(VeiledNode.model_fields.keys())
    assert fields == {"id", "position"}, (
        f"VeiledNode deveria ter exatamente {{'id', 'position'}}, tem {fields}"
    )
    forbidden = ("name", "icon", "description", "read_aloud", "present", "connections")
    for field in forbidden:
        assert field not in fields, (
            f"VeiledNode ganhou o campo '{field}' — rompimento explícito do ADR-042"
        )


def test_revealed_scene_not_in_veiled_nodes():
    """Cena revelada aparece em `nodes`, nunca em `veiled_nodes`.
    Sem duplicação entre as duas listas."""
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna", "praca"],
        current_location="taverna",
    )
    revealed_ids = {n.id for n in resp.nodes}
    veiled_ids = {v.id for v in resp.veiled_nodes}
    assert revealed_ids == {"taverna", "praca"}
    assert veiled_ids.isdisjoint(revealed_ids), (
        f"ids duplicados entre nodes e veiled_nodes: "
        f"{revealed_ids & veiled_ids}"
    )
    assert "taverna" not in veiled_ids
    assert "praca" not in veiled_ids


def test_current_location_not_in_veiled_nodes():
    """Defesa em profundidade: mesmo que `locations_revealed` esteja
    inconsistente (sem a current), a cena onde o jogador está aparece
    como nó completo em `nodes`, nunca como silhueta em `veiled_nodes`.
    Senão um bug futuro que filtre a current das duas listas faz a
    localização do jogador sumir do mapa silenciosamente."""
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=[],
        current_location="estrada",
    )
    veiled_ids = {v.id for v in resp.veiled_nodes}
    revealed_ids = {n.id for n in resp.nodes}

    # (a) não pode estar velada
    assert "estrada" not in veiled_ids, (
        "current_location apareceu em veiled_nodes — jogador veria silhueta no próprio lugar"
    )
    # (b) deve estar revelada (visível no mapa)
    assert "estrada" in revealed_ids, (
        "current_location sumiu do mapa: não está em nodes nem em veiled_nodes"
    )


def test_no_edges_to_veiled_nodes():
    """ADR-042: arestas envolvendo cenas veladas não trafegam.
    Adjacência narrativa permanece oculta — o jogador descobre conexões
    ao explorar, não pelo mapa parcial."""
    chapter = _make_chapter()
    resp = build_graph_response(
        chapter,
        campaign_id="cid",
        locations_revealed=["taverna"],
        current_location="taverna",
    )
    veiled_ids = {v.id for v in resp.veiled_nodes}
    for edge in resp.edges:
        assert edge.source not in veiled_ids, (
            f"aresta '{edge.source}→{edge.target}' tem ponta velada '{edge.source}'"
        )
        assert edge.target not in veiled_ids, (
            f"aresta '{edge.source}→{edge.target}' tem ponta velada '{edge.target}'"
        )


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
