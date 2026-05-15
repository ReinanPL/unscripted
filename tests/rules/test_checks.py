from app.rules.checks import CheckResult, check
from app.rules.dice import roll


def _roll_with_total(total: int) -> object:
    """Retorna um RollResult com total fixo para testar check em isolamento."""
    result = roll("1d20", seed=0)
    # Substitui o total via model_copy para testar check independente de random
    return result.model_copy(update={"total": total, "rolls": [total]})


def test_check_sucesso_simples():
    roll_result = _roll_with_total(15)
    result = check(roll_result, difficulty=10)  # type: ignore[arg-type]
    assert isinstance(result, CheckResult)
    assert result.success is True
    assert result.roll_total == 15
    assert result.difficulty == 10
    assert result.margin == 5


def test_check_falha_simples():
    roll_result = _roll_with_total(8)
    result = check(roll_result, difficulty=15)  # type: ignore[arg-type]
    assert result.success is False
    assert result.margin == -7


def test_check_empate_na_dc_e_sucesso():
    roll_result = _roll_with_total(15)
    result = check(roll_result, difficulty=15)  # type: ignore[arg-type]
    assert result.success is True
    assert result.margin == 0


def test_check_margem_positiva_passando_por_muito():
    roll_result = _roll_with_total(20)
    result = check(roll_result, difficulty=5)  # type: ignore[arg-type]
    assert result.success is True
    assert result.margin == 15


def test_check_margem_negativa_falhando_por_muito():
    roll_result = _roll_with_total(1)
    result = check(roll_result, difficulty=20)  # type: ignore[arg-type]
    assert result.success is False
    assert result.margin == -19


def test_check_com_resultado_real_de_roll():
    # Verifica integração direta roll → check
    result = roll("1d20+5", seed=42)
    check_result = check(result, difficulty=15)
    assert check_result.roll_total == result.total
    assert check_result.success == (result.total >= 15)
    assert check_result.margin == result.total - 15


def test_check_vantagem_usa_total_correto():
    result = roll("adv:1d20", seed=10)
    check_result = check(result, difficulty=15)
    assert check_result.roll_total == result.total
    assert check_result.success == (result.total >= 15)


def test_check_desvantagem_usa_total_correto():
    result = roll("dis:1d20", seed=10)
    check_result = check(result, difficulty=15)
    assert check_result.roll_total == result.total


def test_checkresult_serializable():
    roll_result = roll("1d20", seed=0)
    result = check(roll_result, difficulty=10)
    data = result.model_dump()
    assert "success" in data
    assert "margin" in data
    assert "difficulty" in data
