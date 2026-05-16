"""Utilitários comuns aos eval sets dos agentes.

Os eval sets vivem em `tests/evals/{robustness,referee,narrator}/` e
medem qualidade agregada — diferente dos unit tests, que validam
contratos individuais.

Convenções:
- Casos ficam em `cases.yaml` ao lado do teste (legível, editável sem
  recompilar).
- Testes que chamam LLM real são marcados com `@pytest.mark.eval`.
  Esses testes ficam fora do CI default e exigem `pytest -m eval`.
- Robustez é determinística e roda sem o marker.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture
def load_cases(request: pytest.FixtureRequest) -> Callable[..., Any]:
    """Carrega o YAML de casos ao lado do arquivo de teste. Retorna
    o que o YAML contiver (`list` ou `dict` no topo — depende do caso).

        def test_x(load_cases):
            data = load_cases()           # ./cases.yaml
            data = load_cases("alt.yaml") # ./alt.yaml
    """

    def _load(name: str = "cases.yaml") -> Any:
        base = Path(request.path).resolve().parent
        path = base / name
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)

    return _load


@pytest.fixture
def require_gemini_key() -> None:
    """Skip o teste se não houver `GEMINI_API_KEY` no ambiente."""
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY ausente; eval contra LLM real ignorado.")
