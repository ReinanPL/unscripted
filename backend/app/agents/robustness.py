"""Validação determinística de robustez da entrada do jogador (ADR-026).

Barra três categorias antes que qualquer agente LLM seja invocado:
- declaração de resultado (PRD §8.1)
- tentativa abusiva / injeção de prompt (PRD §8.2)
- conteúdo proibido (PRD §9)

Heurística simples de regex com listas de padrões. Trade-off explícito:
falsos positivos/negativos são aceitáveis na v1 — ver ADR-026.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

RobustnessCategory = Literal[
    "declaracao_de_resultado",
    "injecao",
    "conteudo_proibido",
]


class RobustnessVerdict(BaseModel):
    """Veredito da validação. `ok=False` ⇒ turno não consumido, aviso vermelho.

    `matched` traz o trecho exato que casou — alimenta observabilidade
    (painel "pensamento do mestre") e facilita ajustes nos padrões.
    """

    ok: bool
    category: RobustnessCategory | None = None
    reason: str = ""
    matched: str = ""


_DECLARACAO_PATTERNS: list[tuple[str, str]] = [
    (
        r"\b(mato|matar|derroto|derrotar|elimino|eliminar|destruo|destruir|"
        r"aniquilo|aniquilar|abato|abater)\b.{0,60}\b("
        r"instantaneamente|na hora|de uma vez|automaticamente|"
        r"sem (chance|resist[êe]ncia|dificuldade|esfor[çc]o|luta|rea[çc][ãa]o|"
        r"poss[íi]vel\s+rea[çc][ãa]o))\b",
        "ação declara o resultado em vez de tentar (ex.: 'mato X instantaneamente')",
    ),
    (
        r"\b(consigo|tenho sucesso|ganho|ven[çc]o|acerto|passo (no|na))\b.{0,40}\b("
        r"automaticamente|sem (rolagem|teste|dificuldade|esfor[çc]o|falhar)|"
        r"de qualquer jeito|com certeza absoluta)\b",
        "ação assume sucesso automático",
    ),
    (
        r"\bsou (imune|invenc[íi]vel|imortal|invuner[áa]vel)\b",
        "ação declara invulnerabilidade",
    ),
    (
        r"\bcr[íi]tico\s+autom[áa]tico\b",
        "ação declara crítico automático",
    ),
    (
        r"\bpego\b.{0,40}\b(tesouro|ouro|loot|recompensa)\b.{0,40}\b("
        r"sem (luta|resist[êe]ncia|dificuldade)|automaticamente|na hora)\b",
        "ação declara a recompensa em vez de tentar obtê-la",
    ),
]

_INJECAO_PATTERNS: list[tuple[str, str]] = [
    (
        r"\b(ignor[ea]r?|desconsider[ea]r?|esque[çc]a?|esque[çc]er)\b.{0,40}\b("
        r"instru[çc][õo]es?|regras|prompt|sistema|tudo|everything|all\s+rules?)\b",
        "tentativa de instrução para o sistema ignorar regras",
    ),
    (
        r"\b(voc[êe]|you)\b\s+(agora|now)\s+(é|e|s[ãa]o|is|are)\b",
        "tentativa de redefinir o papel do agente",
    ),
    (
        r"\b(system|sistema)\s*prompt\b",
        "menção explícita a prompt de sistema",
    ),
    (
        r"<\s*/?\s*(system|assistant|user)\s*>",
        "tags falsas simulando mensagem do sistema",
    ),
    (
        r"\b(jailbreak|dan\s+mode|developer\s+mode|modo\s+desenvolvedor|"
        r"modo\s+admin|admin\s+mode)\b",
        "termo conhecido de jailbreak",
    ),
    (
        r"\b(nova\s+instru[çc][ãa]o|new\s+instructions?)\b",
        "tentativa de injetar instruções novas",
    ),
    (
        r"\b(act\s+as|aja\s+como)\s+(if|se)\b",
        "tentativa de reescrever o papel do agente via roleplay-prompt",
    ),
]

_PROIBIDO_PATTERNS: list[tuple[str, str]] = [
    (
        # Verbos de violência gráfica em qualquer conjugação razoável.
        # `\B?` permite raízes terminadas em "a" ou "i" antes do sufixo
        # verbal (estripo, estripar, estripou, decapita, decapito, etc.).
        r"\b(estri[pp][aeiou][rmsuod]*|esquartej[aeiou][rmsuod]*|"
        r"decapit[aeiou][rmsuod]*|arranc[aeiou][rmsuod]*\s+os?\s+(olhos|membros)|"
        r"v[íi]sceras|entranhas?|jorra[rsm]?\s+sangue|"
        r"[óo]rg[ãa]os\s+expostos|sangue\s+escorrendo\s+pelas)\b",
        "descrição explícita de violência gráfica (gore)",
    ),
    (
        r"\btortur[oaei]r?\b",
        "tortura como ato narrativo (fora da política de conteúdo)",
    ),
    (
        r"\b(sexo|sexual(mente)?|orgasmo|gozar|tes[ãa]o|excita[çc][ãa]o\s+sexual|"
        r"penetra[çc][ãa]o\s+sexual|nudez\s+expl[íi]cita)\b",
        "conteúdo sexual fora do escopo do projeto",
    ),
    (
        r"\b(estupr[oa]r?|abuso\s+sexual|viol[êe]ncia\s+sexual)\b",
        "conteúdo proibido (violência sexual)",
    ),
]


def _first_match(text: str, patterns: list[tuple[str, str]]) -> tuple[str, str] | None:
    for pattern, reason in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(0), reason
    return None


def validate_player_input(text: str) -> RobustnessVerdict:
    """Aplica a heurística e retorna o veredito (ADR-026)."""
    normalized = text.strip()
    if not normalized:
        return RobustnessVerdict(ok=True)

    categories: tuple[tuple[RobustnessCategory, list[tuple[str, str]]], ...] = (
        ("declaracao_de_resultado", _DECLARACAO_PATTERNS),
        ("injecao", _INJECAO_PATTERNS),
        ("conteudo_proibido", _PROIBIDO_PATTERNS),
    )
    for category, patterns in categories:
        hit = _first_match(normalized, patterns)
        if hit is not None:
            matched, reason = hit
            return RobustnessVerdict(
                ok=False,
                category=category,
                reason=reason,
                matched=matched,
            )

    return RobustnessVerdict(ok=True)
