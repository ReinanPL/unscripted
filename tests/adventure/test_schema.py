import pathlib

import pytest
from pydantic import ValidationError

from app.state.adventure_schema import Adventure

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_valid_chapter_loads():
    adv = Adventure.from_yaml(FIXTURES / "valid_chapter.yaml")
    assert adv.id == "cap-test-01"
    assert len(adv.chapters) == 1
    chap = adv.chapters[0]
    assert chap.starting_scene == "praca"
    assert {s.id for s in chap.scenes} == {"praca", "taverna"}
    assert chap.npcs[0].hidden_state.trait.startswith("Antigo soldado")


def test_malformed_chapter_rejected_bad_reference():
    with pytest.raises(ValidationError) as exc:
        Adventure.from_yaml(FIXTURES / "malformed_chapter_bad_ref.yaml")
    assert "lugar_que_nao_existe" in str(exc.value)


def test_malformed_chapter_rejected_missing_field():
    with pytest.raises(ValidationError):
        Adventure.from_yaml(FIXTURES / "malformed_chapter_missing_field.yaml")


def test_starting_scene_must_exist():
    data = {
        "id": "x",
        "title": "x",
        "chapters": [
            {
                "id": "c1",
                "title": "c1",
                "premise": "p",
                "background": "b",
                "starting_scene": "fantasma",
                "progress_condition": "ok",
                "scenes": [
                    {"id": "real", "name": "Real", "description": "d"},
                ],
            }
        ],
    }
    with pytest.raises(ValidationError) as exc:
        Adventure.model_validate(data)
    assert "starting_scene" in str(exc.value)


def test_to_lore_text_contains_scene_and_npc():
    adv = Adventure.from_yaml(FIXTURES / "valid_chapter.yaml")
    text = adv.chapters[0].to_lore_text()
    assert "Praça da vila" in text
    assert "Velho Tomás" in text
    assert "Antigo soldado" not in text


def test_to_lore_text_omits_hidden_state():
    """Estado oculto da aventura nunca vai para o corpus de lore."""
    adv = Adventure.from_yaml(FIXTURES / "valid_chapter.yaml")
    text = adv.chapters[0].to_lore_text()
    assert "Antigo soldado" not in text
    assert "Não revela seu passado" not in text
