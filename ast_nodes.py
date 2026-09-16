from __future__ import annotations

import dataclasses
import enum
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """Intervalo no fonte, com posição final exclusiva."""

    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass(slots=True, kw_only=True)
class Node:
    span: SourceSpan
    metadata: dict[str, object] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )


class TypeName(enum.Enum):
    INT = "int"
    BOOL = "bool"
    VOID = "void"


class UnaryOperator(enum.Enum):
    NEGATE = "-"
    NOT = "!"


class BinaryOperator(enum.Enum):
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    REMAINDER = "%"
    LESS = "<"
    LESS_EQUAL = "<="
    GREATER = ">"
    GREATER_EQUAL = ">="
    EQUAL = "=="
    NOT_EQUAL = "!="
    LOGICAL_AND = "&&"
    LOGICAL_OR = "||"


@dataclass(slots=True)
class Program(Node):
    functions: list[FunctionDecl]


@dataclass(slots=True)
class FunctionDecl(Node):
    return_type: TypeName
    name: str
    parameters: list[Parameter]
    body: Block


@dataclass(slots=True)
class Parameter(Node):
    type: TypeName
    name: str


@dataclass(slots=True)
class Stmt(Node):
    pass


@dataclass(slots=True)
class Block(Stmt):
    statements: list[Stmt]


@dataclass(slots=True)
class VarDecl(Stmt):
    type: TypeName
    name: str
    initializer: Expr | None


@dataclass(slots=True)
class Assignment(Stmt):
    target: IdentifierExpr
    value: Expr


@dataclass(slots=True)
class CallStmt(Stmt):
    call: CallExpr


@dataclass(slots=True)
class IfStmt(Stmt):
    condition: Expr
    then_block: Block
    else_block: Block | None


@dataclass(slots=True)
class WhileStmt(Stmt):
    condition: Expr
    body: Block


@dataclass(slots=True)
class ReturnStmt(Stmt):
    value: Expr | None


@dataclass(slots=True)
class PrintItem(Node):
    pass


@dataclass(slots=True)
class PrintStmt(Stmt):
    items: list[PrintItem]


@dataclass(slots=True)
class Expr(PrintItem):
    pass


@dataclass(slots=True)
class BinaryExpr(Expr):
    operator: BinaryOperator
    left: Expr
    right: Expr


@dataclass(slots=True)
class UnaryExpr(Expr):
    operator: UnaryOperator
    operand: Expr


@dataclass(slots=True)
class CallExpr(Expr):
    name: str
    arguments: list[Expr]


@dataclass(slots=True)
class IdentifierExpr(Expr):
    name: str


@dataclass(slots=True)
class IntLiteral(Expr):
    value: int


@dataclass(slots=True)
class BoolLiteral(Expr):
    value: bool


@dataclass(slots=True)
class StringLiteral(PrintItem):
    value: str


def ast_to_dict(node: Node) -> dict[str, Any]:
    """Converta somente dados sintáticos da AST para uma estrutura JSON."""

    result: dict[str, Any] = {"node": type(node).__name__}
    for dataclass_field in dataclasses.fields(node):
        if dataclass_field.name == "metadata":
            continue
        result[dataclass_field.name] = _json_value(getattr(node, dataclass_field.name))
    return result


def _json_value(value: Any) -> Any:
    if isinstance(value, Node):
        return ast_to_dict(value)
    if isinstance(value, SourceSpan):
        return dataclasses.asdict(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value

