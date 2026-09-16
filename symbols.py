"""Estruturas fundamentais para símbolos e escopos da MicroC.

Os campos formam o contrato usado pelos metadados da AST. O grupo pode
acrescentar métodos, subclasses e estruturas auxiliares sem alterar esses
campos públicos.
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
