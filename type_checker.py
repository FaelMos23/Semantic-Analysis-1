from __future__ import annotations

from ast_nodes import Program


def check_types(program: Program) -> None:
    """Determine tipos de expressões e valide seus contextos."""

    # 1. Use os símbolos anexados pela resolução de nomes.
    # 2. Determine cada expressão de baixo para cima.
    # 3. Valide operadores, chamadas, comandos e declarações.
    # 4. Anote expressões válidas e acumule os diagnósticos da passagem.
    raise NotImplementedError("implemente a verificação de tipos")
