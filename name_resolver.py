from __future__ import annotations

from ast_nodes import (
    Program,
    TypeName,
    Block,
    Expr,
    
    VarDecl,
    IdentifierExpr,
    CallExpr,

    Assignment,
    CallStmt,
    ReturnStmt,
    PrintStmt,
    IfStmt,
    WhileStmt,
    
    BinaryExpr,
    UnaryExpr,
    
    IntLiteral,
)

import semantic_errors as se

from symbols import (
    FunctionSymbol,
    Symbol,
    Scope,
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
        f.metadata["symbol"] = functs_symb[-1]  # último símbolo adicionado
        # o escopo necessita dos símbolos declarados naquele escopo, portanto será adicionado durante o check_block

    # checando funções duplicadas
    funcs_vistas = set()
    for fn in functs_name:
        if functs_name.count(fn) > 1 and fn not in funcs_vistas:

            # isso corrige o erro do diagnótico abaixo aparecer mais de uma vez na lista de erros
            funcs_vistas.add(fn)

            erros.append(
                se.SemanticDiagnostic(
                    se.SemanticErrorKind.DUPLICATE_FUNCTION,
                    f"A função {fn} se encontra com mais de uma declaração",
                    span= functs[functs_name.index(fn)].span
                )
            )


    # escopo global
    global_symbs = dict()
    for f in functs_symb:
        global_symbs[f.name] = f
    global_scope = Scope(
        parent=None,
        symbols=global_symbs
    )
    program.metadata["scope"] = global_scope



    # 2. Valide a existência e a assinatura de main.
    if "main" not in functs_name:   # existência
        erros.append(
            se.SemanticDiagnostic(
                se.SemanticErrorKind.INVALID_MAIN,
                "Falta de função main no programa",
                span= se.SourceSpan(1, 1, 1, 1) # para main ausente, usamos o início do program
            )
        )

    # main existe, mas sua assinatura está errada
    elif functs[functs_name.index("main")].return_type != TypeName.INT or len(functs[functs_name.index("main")].parameters) != 0:   # assinatura
        erros.append(
            se.SemanticDiagnostic(
                se.SemanticErrorKind.INVALID_MAIN,
                "Função main não possui assinatura correta",
                span= functs[functs_name.index("main")].span 
            )
        )



    # 3. Percorra os corpos em ordem, criando um escopo para cada bloco.
    # 4. Anote declarações, usos e blocos na AST.

    # apenas 'IfStmt' e 'WhileStmt' possuem blocos

    # procura resolução do nome no escopo atual, se não encontrar sobre para escopos-pais
    def find_var(name, scope) -> Symbol | None:
        current = scope
        while current is not None:
            if name in current.symbols:
                return current.symbols[name]
            current = current.parent
        return None

    # precisamos visitar todas as expressões em um statement, e.g: 'return dobro(2) + 1;', 'dobro(2)' é uma CallExpr e '1' é um IntLiteral 
    def visit_expr(expr: Expr, scope):
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
                # variável encontrada
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

                # adicionando info aos metadados
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

        # sem ações para BoolLiteral 

        elif type(expr) == BinaryExpr:
            visit_expr(expr.left, scope)
            visit_expr(expr.right, scope)

        elif type(expr) == UnaryExpr:
            visit_expr(expr.operand, scope)


    # precisamos checar os blocos de forma recursiva, pois 'if' e 'while' criam novos blocos internos
    def check_block(params, bl: Block, parent_scope) -> list[Scope]:
        statements = bl.statements


        # symbols
        symbols = dict()

        # parâmetros
        if params:
            for p in params:
                if p.type == TypeName.VOID:
                    erros.append(se.SemanticDiagnostic(
                            se.SemanticErrorKind.VOID_PARAMETER,
                            f"O parâmetro {p.name} não pode ser \'void\'",
                            span= p.span
                        ))

                sym = Symbol(
                    p.name, 
                    SymbolKind.PARAMETER, 
                    p.type, 
                    p
                )
                if p.name in symbols:
                    erros.append(se.SemanticDiagnostic(
                        se.SemanticErrorKind.DUPLICATE_DECLARATION,
                        f"A variável {p.name} já foi previamente declarada",
                        span=p.span
                    ))

                symbols[p.name] = sym
                p.metadata["symbol"] = sym

        curr_scope = Scope(
            parent=parent_scope,
            symbols=symbols
        )


        for s in statements:
            if type(s) == VarDecl:
                if s.name in symbols:
                    erros.append(se.SemanticDiagnostic(
                        se.SemanticErrorKind.DUPLICATE_DECLARATION,
                        f"A variável {s.name} já foi previamente declarada",
                        span=s.span
                    ))
                if s.type == TypeName.VOID:
                    erros.append(se.SemanticDiagnostic(
                        se.SemanticErrorKind.VOID_VARIABLE,
                        f"A variável {s.name} não pode ser \'void\'",
                        span=s.span
                    ))

                sym = Symbol(
                    s.name, 
                    SymbolKind.VARIABLE, 
                    s.type, 
                    s
                )
                s.metadata["symbol"] = sym

                # adicionando símbolo no escopo
                curr_scope.symbols[s.name] = sym

                # expressões de inicialização e.g.: 'int x = y + 2;'
                visit_expr(s.initializer, curr_scope)

            # para outros statements, verificaremos as expressões internas
            elif type(s) == Assignment:
                visit_expr(s.target, curr_scope)
                visit_expr(s.value, curr_scope)

            elif type(s) == CallStmt:
                visit_expr(s.call, curr_scope)

            elif type(s) == IfStmt:
                visit_expr(s.condition, curr_scope)
                check_block(None, s.then_block, curr_scope)
                if s.else_block:
                    check_block(None, s.else_block, curr_scope)

            elif type(s) == WhileStmt:
                visit_expr(s.condition, curr_scope)
                check_block(None, s.body, curr_scope)

            elif type(s) == ReturnStmt:
                visit_expr(s.value, curr_scope)

            elif type(s) == PrintStmt:
                for item in s.items:
                    if hasattr(item, 'span'): # tomando cuidado para lidar com expressões, não strings
                        visit_expr(item, curr_scope)

            # verifica o if, seu bloco e o bloco de else, se houver 
            elif type(s) == IfStmt:
                visit_expr(s.condition, curr_scope)
                check_block(None, s.then_block, curr_scope)
                if s.else_block:
                    check_block(None, s.else_block, curr_scope)

            # verifica o while e seu bloco
            elif type(s) == WhileStmt:
                visit_expr(s.condition, curr_scope)
                check_block(None, s.body, curr_scope)
        
        # adicionar metadado do escopo ao bloco atual, com todas as definições
        bl.metadata["scope"] = curr_scope

    
    for f in functs:
        check_block(f.parameters, f.body, global_scope)



    # 5. Acumule os diagnósticos desta passagem antes de lançar SemanticError.
    if erros:
        raise se.SemanticError(erros)