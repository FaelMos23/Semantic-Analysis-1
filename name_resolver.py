from __future__ import annotations

from ast_nodes import (
    Program,
    
    IdentifierExpr,
    CallExpr,
    
    BinaryExpr,
    UnaryExpr,
    
    IntLiteral,
)

import semantic_errors as se

from symbols import (
    FunctionSymbol,
    Symbol,
    SymbolKind,
)


def resolve_names(program: Program) -> None:
    """Construa escopos, símbolos e vínculos entre usos e declarações."""

    erros: se.SemanticError.diagnostics = []

    functs = []
    functs_name = []
    functs_symb = []

    # 1. Colete todas as assinaturas de função.
    for f in program.functions:
        functs.append(f)
        functs_name.append(f.name)

        params = ()
        for p in f.parameters:
            params = params + (p.type,)

        functs_symb.append(FunctionSymbol(
            f.name,
            SymbolKind.FUNCTION,
            f.return_type,
            f,
            parameter_types= params
        ))

        # adicionando informação na AST
        f.metadata[f.name] = functs_symb[-1]

    # checando funções duplicadas
    funcs_vistas = set()
    for fn in functs_name:
        if functs_name.count(fn) > 1 and fn not in funcs_vistas:

            # o erro de função duplicada deve aparecer apenas uma vez, se existir
            funcs_vistas.add(fn)

            erros.append(
                se.SemanticDiagnostic(
                    se.SemanticErrorKind.DUPLICATE_FUNCTION,
                    f"A função {fn} se encontra com mais de uma declaração",
                    span= functs[functs_name.index(fn)].span
                )
            )



    # 2. Valide a existência e a assinatura de main.
    # TODO


    # 3. Percorra os corpos em ordem, criando um escopo para cada bloco.
    # 4. Anote declarações, usos e blocos na AST.

    # variáveis podem ser usadas de declarações de escopos-pais
    def find_var(name, scope) -> Symbol | None:
        current = scope
        while current is not None:
            if name in current.symbols:
                return current.symbols[name]
            current = current.parent
        return None

    # precisamos visitar todas as expressões em um statement, e.g: 'return dobro(2) + 1;', 'dobro(2)' é uma CallExpr e '1' é um IntLiteral 
    def visit_expr(expr, scope):
        if expr is None:
            return
        
        if type(expr) == IdentifierExpr:
            resolved = find_var(expr.name, scope)
            if not resolved:
                erros.append(se.SemanticDiagnostic(
                    se.SemanticErrorKind.UNDECLARED_VARIABLE,
                    f"A variável {expr.name} não foi declarada",
                    span=expr.span
                ))
            else:
                expr.metadata["symbol"] = resolved

        elif type(expr) == CallExpr:
            if expr.name not in functs_name:
                erros.append(se.SemanticDiagnostic(
                    se.SemanticErrorKind.UNDECLARED_FUNCTION,
                    f"A função {expr.name} não foi declarada",
                    span=expr.span
                ))
            else:
                # expressão conhecida
                func_sym = functs_symb[functs_name.index(expr.name)]
                expr.metadata["symbol"] = func_sym
                
                # verificar se quantidade de argumentos passados é igual a quantidade de parâmetros requisitados = aridade
                if len(expr.arguments) != len(func_sym.parameter_types):
                    erros.append(se.SemanticDiagnostic(
                        se.SemanticErrorKind.ARITY_MISMATCH,
                        f"Número incorreto de argumentos fornecido, n° de argumentos passados: {len(expr.arguments)}, n° de argumentos requisitados: {len(func_sym.parameter_types)}",
                        span=expr.span
                    ))
            
            # recursivamente checa argumentos, para casos como 'dobro(dobro(4))'
            for arg in expr.arguments:
                visit_expr(arg, scope)

        elif type(expr) == IntLiteral:
            # checar limite de valor inteiro (apenas positivo pois o menos não faz parte de IntLiteral)
            if expr.value > 9223372036854775807:
                erros.append(se.SemanticDiagnostic(
                    se.SemanticErrorKind.INTEGER_LITERAL_OUT_OF_RANGE,
                    "Literal inteiro fora dos limites permitidos",
                    span=expr.span
                ))
                
        elif type(expr) == BinaryExpr:
            visit_expr(expr.left, scope)
            visit_expr(expr.right, scope)
            
        elif type(expr) == UnaryExpr:
            visit_expr(expr.operand, scope)

    # precisamos checar os blocos de forma recursiva, pois 'if' e 'while' criam novos blocos internos
    # TODO: função de checar blocos

    # TODO: utilizar a função de checar blocos


    # 5. Acumule os diagnósticos desta passagem antes de lançar SemanticError.
    if erros:
        raise se.SemanticError(erros)