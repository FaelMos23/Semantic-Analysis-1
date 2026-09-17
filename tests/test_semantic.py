from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest


STARTER_ROOT = Path(__file__).parents[1]
CASES = Path(__file__).parent / "cases"
SEMANTIC_DIR = Path(
    os.environ.get("MICROC_SEMANTIC_DIR", STARTER_ROOT)
).resolve()
sys.path.insert(0, str(SEMANTIC_DIR))

from Lexer import Lexer  # noqa: E402
from ast_nodes import (  # noqa: E402
    BinaryExpr,
    Block,
    CallExpr,
    Expr,
    IdentifierExpr,
    Node,
    SourceSpan,
    StringLiteral,
    TypeName,
)
from parser import Parser  # noqa: E402
from semantic import SemanticAnalyzer  # noqa: E402
from semantic_errors import (  # noqa: E402
    SemanticDiagnostic,
    SemanticError,
    SemanticErrorKind,
)
from symbols import FunctionSymbol, Scope, Symbol, SymbolKind  # noqa: E402


def analyze(source: str):
    program = Parser(Lexer(source).scan()).parse()
    return SemanticAnalyzer().analyze(program)


def analyze_case(category: str, name: str):
    return analyze((CASES / category / name).read_text(encoding="utf-8"))


def diagnostics(source: str):
    with pytest.raises(SemanticError) as caught:
        analyze(source)
    return caught.value.diagnostics


def assert_diagnostics(items, expected):
    actual = Counter((item.kind, item.line, item.column) for item in items)
    assert actual == Counter(expected)


def descendants(node: Node):
    yield node
    for field in dataclasses.fields(node):
        if field.name == "metadata":
            continue
        value = getattr(node, field.name)
        if isinstance(value, Node):
            yield from descendants(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Node):
                    yield from descendants(item)


def test_estruturas_fundamentais_possuem_o_contrato_publicado():
    assert [field.name for field in dataclasses.fields(Symbol)] == [
        "name", "kind", "type", "declaration"
    ]
    assert [field.name for field in dataclasses.fields(FunctionSymbol)][-1] == (
        "parameter_types"
    )
    assert [field.name for field in dataclasses.fields(Scope)] == [
        "parent", "symbols"
    ]
    assert set(SymbolKind) == {
        SymbolKind.FUNCTION,
        SymbolKind.PARAMETER,
        SymbolKind.VARIABLE,
    }


def test_programa_integrado_e_anotado_com_identidade_de_simbolos():
    program = analyze_case("valid", "integrated.mc")
    assert isinstance(program.functions[0].metadata["symbol"], FunctionSymbol)
    assert isinstance(program.functions[2].body.metadata["scope"], Scope)

    declaration = program.functions[2].body.statements[0]
    initializer = declaration.initializer
    returned = program.functions[2].body.statements[2].value
    assert isinstance(initializer, CallExpr)
    assert isinstance(returned, IdentifierExpr)
    assert returned.metadata["symbol"] is declaration.metadata["symbol"]
    assert initializer.metadata["type"] is TypeName.INT
    assert returned.metadata["type"] is TypeName.INT


def test_contrato_completo_de_metadados_e_estruturas_e_publico():
    program = analyze(
        "int escolher(int x, bool ok) { if (ok) { return x; } return 0; }\n"
        "void registrar(bool valor) { print(valor); }\n"
        "int main() { int x = escolher(1, true); { bool x = false; "
        "registrar(x); } escolher(2, false); return x; }"
    )

    function_symbol = program.functions[0].metadata["symbol"]
    assert isinstance(function_symbol, FunctionSymbol)
    assert function_symbol.type is TypeName.INT
    assert function_symbol.parameter_types == (TypeName.INT, TypeName.BOOL)
    assert function_symbol.declaration is program.functions[0]

    main = program.functions[2]
    outer_scope = main.body.metadata["scope"]
    nested_block = main.body.statements[1]
    nested_scope = nested_block.metadata["scope"]
    assert outer_scope.parent is None
    assert nested_scope.parent is outer_scope

    for node in descendants(program):
        if isinstance(node, Expr):
            assert node.metadata["type"] in {
                TypeName.INT,
                TypeName.BOOL,
                TypeName.VOID,
            }
        if isinstance(node, Block):
            assert isinstance(node.metadata["scope"], Scope)
        if isinstance(node, StringLiteral):
            assert "type" not in node.metadata

    assert nested_block.statements[1].call.metadata["type"] is TypeName.VOID
    assert main.body.statements[2].call.metadata["type"] is TypeName.INT


def test_chamadas_antecipadas_e_recursao_sao_validas():
    program = analyze_case("valid", "forward_calls.mc")
    call = program.functions[0].body.statements[1].value
    target = program.functions[1].metadata["symbol"]
    assert call.metadata["symbol"] is target
    assert call.metadata["type"] is TypeName.INT


def test_limites_da_etapa_nao_antecipam_analise_de_fluxo():
    analyze_case("valid", "phase_boundary.mc")


def test_erros_de_nomes_sao_acumulados_com_coordenadas():
    items = diagnostics((CASES / "invalid" / "names.mc").read_text())
    assert_diagnostics(items, [
        (SemanticErrorKind.UNDECLARED_VARIABLE, 2, 5),
        (SemanticErrorKind.UNDECLARED_FUNCTION, 3, 5),
        (SemanticErrorKind.UNDECLARED_VARIABLE, 3, 13),
    ])


def test_redeclaracoes_sao_locais_e_funcoes_sao_globais():
    items = diagnostics(
        "int f(int x, int x) { int x; { int x; } return 0; }\n"
        "int f() { return 0; }\n"
        "int main() { return 0; }\n"
    )
    assert Counter(item.kind for item in items) == Counter({
        SemanticErrorKind.DUPLICATE_FUNCTION: 1,
        SemanticErrorKind.DUPLICATE_DECLARATION: 2,
    })
    assert all(item.line >= 1 and item.column >= 1 for item in items)


def test_contextos_de_tipo_produzem_categorias_especificas():
    items = diagnostics((CASES / "invalid" / "types.mc").read_text())
    assert_diagnostics(items, [
        (SemanticErrorKind.INITIALIZER_TYPE_MISMATCH, 2, 13),
        (SemanticErrorKind.ASSIGNMENT_TYPE_MISMATCH, 3, 9),
        (SemanticErrorKind.CONDITION_TYPE_MISMATCH, 4, 9),
        (SemanticErrorKind.CONDITION_TYPE_MISMATCH, 5, 12),
        (SemanticErrorKind.RETURN_MISMATCH, 6, 12),
    ])


def test_chamadas_validam_void_aridade_e_argumentos():
    items = diagnostics((CASES / "invalid" / "calls.mc").read_text())
    assert_diagnostics(items, [
        (SemanticErrorKind.VOID_VALUE_USED, 8, 13),
        (SemanticErrorKind.ARITY_MISMATCH, 9, 5),
        (SemanticErrorKind.ARGUMENT_TYPE_MISMATCH, 9, 14),
    ])


def test_operadores_unarios_binarios_e_tipos_resultantes():
    valid = analyze(
        "bool iguais(int a, int b) { return -a + b < 0 == !(a == b); }\n"
        "int main() { return 0; }"
    )
    expression = valid.functions[0].body.statements[0].value
    assert isinstance(expression, BinaryExpr)
    assert expression.metadata["type"] is TypeName.BOOL

    items = diagnostics(
        "int main() { int x = -true; bool b = 1 && false; "
        "bool c = 1 == true; return 0; }"
    )
    assert Counter(item.kind for item in items) == Counter({
        SemanticErrorKind.INVALID_UNARY_OPERAND: 1,
        SemanticErrorKind.INVALID_BINARY_OPERANDS: 2,
    })
    assert all(item.line == 1 and item.column >= 1 for item in items)


def test_void_em_declaracoes_e_limite_do_literal():
    items = diagnostics(
        "void f(void p) { void x = 0; }\n"
        "int main() { int n = 9223372036854775808; return 0; }"
    )
    assert_diagnostics(items, [
        (SemanticErrorKind.VOID_PARAMETER, 1, 8),
        (SemanticErrorKind.VOID_VARIABLE, 1, 18),
        (SemanticErrorKind.INTEGER_LITERAL_OUT_OF_RANGE, 2, 22),
    ])


@pytest.mark.parametrize(
    "source",
    ["", "void main() {}", "int main(int x) { return x; }"],
)
def test_main_deve_possuir_assinatura_exata(source: str):
    items = diagnostics(source)
    assert items[0].kind is SemanticErrorKind.INVALID_MAIN
    assert (items[0].line, items[0].column) == (1, 1)


def test_semantic_error_fornecido_possui_formato_fixo():
    diagnostic = SemanticDiagnostic(
        SemanticErrorKind.INVALID_MAIN,
        "mensagem livre",
        SourceSpan(3, 7, 3, 8),
    )
    error = SemanticError([diagnostic])
    assert error.diagnostics == (diagnostic,)
    assert str(error) == (
        "erro semântico [invalid_main] em 3:7: mensagem livre"
    )
    with pytest.raises(ValueError):
        SemanticError([])


def test_runner_distingue_sucesso_e_erro_semantico(tmp_path: Path):
    valid = tmp_path / "valid.mc"
    valid.write_text("int main() { return 0; }\n", encoding="ascii")
    result = subprocess.run(
        [sys.executable, str(SEMANTIC_DIR / "runner.py"), str(valid)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == "programa válido na Análise Semântica 1\n"

    invalid = tmp_path / "invalid.mc"
    invalid.write_text("int main() { x = 1; return 0; }\n", encoding="ascii")
    result = subprocess.run(
        [sys.executable, str(SEMANTIC_DIR / "runner.py"), str(invalid)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "[undeclared_variable] em 1:14" in result.stderr
