"""Contrato fixo de símbolos e escopos da MicroC.

Não altere este arquivo. Crie estruturas e operações auxiliares nos módulos das
passagens quando precisar de outra organização interna.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from ast_nodes import FunctionDecl, Node, TypeName


class SymbolKind(enum.Enum):
    FUNCTION = "function"
    PARAMETER = "parameter"
    VARIABLE = "variable"


@dataclass(slots=True, eq=False)
class Symbol:
    name: str
    kind: SymbolKind
    type: TypeName
    declaration: Node


@dataclass(slots=True, eq=False)
class FunctionSymbol(Symbol):
    declaration: FunctionDecl
    parameter_types: tuple[TypeName, ...]


@dataclass(slots=True, eq=False)
class Scope:
    parent: Scope | None
    symbols: dict[str, Symbol] = field(default_factory=dict)
