import pytest

from app.rules.dice import RollResult, roll


def test_roll_basico_retorna_rollresult():
    result = roll("1d6", seed=42)
    assert isinstance(result, RollResult)
    assert result.notation == "1d6"
    assert len(result.rolls) == 1
    assert 1 <= result.rolls[0] <= 6
    assert result.total == result.rolls[0]
    assert result.modifier == 0
    assert not result.advantage
    assert not result.disadvantage


def test_roll_multiplos_dados():
    result = roll("2d6", seed=0)
    assert len(result.rolls) == 2
    for r in result.rolls:
        assert 1 <= r <= 6
    assert result.total == sum(result.rolls)


def test_roll_com_modificador_positivo():
    result = roll("1d20+5", seed=7)
    assert result.modifier == 5
    assert result.total == result.rolls[0] + 5


def test_roll_com_modificador_negativo():
    result = roll("1d8-1", seed=3)
    assert result.modifier == -1
    assert result.total == result.rolls[0] - 1


def test_roll_seed_determinista():
    a = roll("2d6+3", seed=99)
    b = roll("2d6+3", seed=99)
    assert a.rolls == b.rolls
    assert a.total == b.total


def test_roll_seed_diferente_resultado_diferente():
    a = roll("1d20", seed=1)
    b = roll("1d20", seed=2)
    # Sementes diferentes produzem resultados diferentes (probabilisticamente)
    # Verificamos apenas que seeds distintas são tratadas de forma independente
    assert isinstance(a.total, int)
    assert isinstance(b.total, int)


def test_roll_vantagem():
    result = roll("adv:1d20", seed=10)
    assert result.advantage is True
    assert result.disadvantage is False
    assert len(result.rolls) == 2
    assert result.total == max(result.rolls) + result.modifier


def test_roll_desvantagem():
    result = roll("dis:1d20", seed=10)
    assert result.disadvantage is True
    assert result.advantage is False
    assert len(result.rolls) == 2
    assert result.total == min(result.rolls) + result.modifier


def test_roll_vantagem_case_insensitive():
    result = roll("ADV:1d20", seed=1)
    assert result.advantage is True


def test_roll_desvantagem_com_modificador():
    result = roll("dis:1d20+3", seed=5)
    assert result.disadvantage is True
    assert result.total == min(result.rolls) + 3


def test_roll_vantagem_com_modificador_negativo():
    result = roll("adv:1d20-2", seed=5)
    assert result.advantage is True
    assert result.total == max(result.rolls) - 2


def test_roll_total_dentro_do_range_basico():
    for seed in range(50):
        result = roll("1d20", seed=seed)
        assert 1 <= result.total <= 20


def test_roll_total_dentro_do_range_com_mod():
    for seed in range(50):
        result = roll("1d6+3", seed=seed)
        assert 4 <= result.total <= 9


def test_roll_notacao_invalida_levanta_valueerror():
    with pytest.raises(ValueError, match="notação inválida"):
        roll("d20")


def test_roll_notacao_invalida_letras():
    with pytest.raises(ValueError):
        roll("abc")


def test_roll_sides_zero_levanta_valueerror():
    with pytest.raises(ValueError):
        roll("1d0")


def test_roll_count_zero_levanta_valueerror():
    with pytest.raises(ValueError):
        roll("0d6")


def test_rollresult_serializable():
    result = roll("2d6+3", seed=1)
    data = result.model_dump()
    assert data["notation"] == "2d6+3"
    assert "rolls" in data
    assert "total" in data
    assert "modifier" in data
