import pytest
from pydantic import ValidationError

from app.agents.contracts import Ruling, TurnTrace
from app.agents.robustness import RobustnessVerdict
from app.rules.proposals import ConsequenceProposal


def _proposta_simples(hp: int = -2) -> ConsequenceProposal:
    return ConsequenceProposal(hp_delta=hp)


def test_ruling_sem_rolagem_aceita_consequencia_unica() -> None:
    r = Ruling(precisa_rolagem=False, consequencia=_proposta_simples())
    assert r.precisa_rolagem is False
    assert r.consequencia is not None
    assert r.consequencia_sucesso is None


def test_ruling_sem_rolagem_sem_consequencia_falha() -> None:
    with pytest.raises(ValidationError) as exc:
        Ruling(precisa_rolagem=False)
    assert "consequencia" in str(exc.value)


def test_ruling_com_rolagem_exige_dificuldade_e_ambas_consequencias() -> None:
    with pytest.raises(ValidationError):
        Ruling(precisa_rolagem=True, pericia="Furtividade")

    with pytest.raises(ValidationError):
        Ruling(
            precisa_rolagem=True,
            pericia="Furtividade",
            dificuldade=15,
            consequencia_sucesso=_proposta_simples(0),
        )

    r = Ruling(
        precisa_rolagem=True,
        pericia="Furtividade",
        dificuldade=15,
        consequencia_sucesso=_proposta_simples(0),
        consequencia_falha=_proposta_simples(-3),
    )
    assert r.precisa_rolagem
    assert r.dificuldade == 15


def test_ruling_carrega_npc_to_react_opcional() -> None:
    r = Ruling(
        precisa_rolagem=False,
        consequencia=_proposta_simples(0),
        npc_to_react="grimwald",
    )
    assert r.npc_to_react == "grimwald"


def test_ruling_roundtrip_json() -> None:
    original = Ruling(
        precisa_rolagem=True,
        pericia="Furtividade",
        dificuldade=18,
        notacao_dado="adv:1d20+2",
        motivo_dificuldade="Joren é veterano com percepção alta",
        consequencia_sucesso=_proposta_simples(0),
        consequencia_falha=_proposta_simples(-4),
        npc_to_react="joren",
    )
    rehydrated = Ruling.model_validate_json(original.model_dump_json())
    assert rehydrated == original


def test_turn_trace_minimal() -> None:
    trace = TurnTrace(
        turn=1,
        player_action="Pergunto a Grimwald sobre Joren.",
        robustness=RobustnessVerdict(ok=True),
    )
    assert trace.turn == 1
    assert trace.ruling is None
    assert trace.retrieval_lore == []
    assert trace.error is None


def test_turn_trace_completo() -> None:
    trace = TurnTrace(
        turn=2,
        player_action="Armo uma emboscada para Joren na clareira.",
        robustness=RobustnessVerdict(ok=True),
        ruling=Ruling(
            precisa_rolagem=True,
            pericia="Furtividade",
            dificuldade=18,
            consequencia_sucesso=_proposta_simples(0),
            consequencia_falha=_proposta_simples(-4),
            npc_to_react="joren",
        ),
        narration="Você se agacha entre os arbustos...",
        npc_reaction="Joren ergue a cabeça, o olho treinado farejando algo errado.",
        npc_id="joren",
    )
    assert trace.ruling is not None and trace.ruling.npc_to_react == "joren"
    assert trace.npc_reaction
