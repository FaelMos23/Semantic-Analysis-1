from __future__ import annotations

from ast_nodes import (
    Program,
    FunctionDecl,
    Block,

    VarDecl,
    Assignment,
    CallStmt,
    IfStmt,
    WhileStmt,
    ReturnStmt,
    PrintStmt,

    BinaryExpr,
    UnaryExpr,
    CallExpr,
    IdentifierExpr,
    IntLiteral,
    BoolLiteral,

    TypeName,
    UnaryOperator,
    BinaryOperator,
)

import semantic_errors as se


# para não interromper a execução do type_resolver no primeiro erro, essa classe serve para propagar que houve um erro em um
# nó filho porém deve-se procurar outros erros ainda, sem propagar o erro em si.
# esse estado NÃO pertence a TypeName e nunca é gravado nos metadados.
class UnknownType():
    pass
UNKNOWN = UnknownType()

# constante e grupos usados para checagem em BinaryExpr
INT_MAX = 2**63 - 1  # 9223372036854775807

ARITMETICOS = {
    BinaryOperator.ADD,
    BinaryOperator.SUBTRACT,
    BinaryOperator.MULTIPLY,
    BinaryOperator.DIVIDE,
    BinaryOperator.REMAINDER,
}
RELACIONAIS = {
    BinaryOperator.LESS,
    BinaryOperator.LESS_EQUAL,
    BinaryOperator.GREATER,
    BinaryOperator.GREATER_EQUAL,
}
IGUALDADE = {BinaryOperator.EQUAL, BinaryOperator.NOT_EQUAL}
LOGICOS = {BinaryOperator.LOGICAL_AND, BinaryOperator.LOGICAL_OR}


def check_types(program: Program) -> None:
    """Determine tipos de expressões e valide seus contextos."""

    # 1. Use os símbolos anexados pela resolução de nomes.
    # 2. Determine cada expressão de baixo para cima.
    # 3. Valide operadores, chamadas, comandos e declarações.
    # 4. Anote expressões válidas e acumule os diagnósticos da passagem.

    erros: list[se.SemanticDiagnostic] = []

    def erro(kind, msg, span):
        erros.append(se.SemanticDiagnostic(kind, msg, span=span))

    def erro_void(expr):
        erro(se.SemanticErrorKind.VOID_VALUE_USED,
             "Expressões void não podem ser usadas como valor", expr.span)

    def anota(expr, res):
        # só grava tipos reais (TypeName) nos metadados
        if res is not UNKNOWN:
            expr.metadata["type"] = res
        return res

    def tipo_valor(expr):
        """Resolve uma expressão usada como VALOR: void vira erro e UNKNOWN."""
        res = bottom_up_type_resolving(expr)
        if res is TypeName.VOID:
            erro_void(expr)
            return UNKNOWN
        return res

    def tipo_da_variavel(sym):
        # variável/parâmetro declarado como void já gerou erro próprio; evita cascata
        if sym is None or sym.type is TypeName.VOID:
            return UNKNOWN
        return sym.type

    # os nós superiores buscam as folhas
    # retorno atual da função é útil apenas para verificação de retorno, mas é nulo por padrão
    def bottom_up_type_resolving(info, current_func_return=None):
        match info:
            # Nós superiores
            case Program():
                for f in info.functions:
                    bottom_up_type_resolving(f)

            case FunctionDecl():
                # parâmetros só aceitam int ou bool
                for p in info.parameters:
                    if p.type is TypeName.VOID:
                        erro(se.SemanticErrorKind.VOID_PARAMETER,
                             f"O parâmetro {p.name} não pode ser 'void'", p.span)   # usando erro geral em vez de erro de void por ser definição, em VarDecl, usamos igual

                # usado para comparar se o return é igual ao tipo esperado
                bottom_up_type_resolving(info.body, info.return_type)

            case Block():
                for s in info.statements:
                    bottom_up_type_resolving(s, current_func_return)

            # statements
            case VarDecl():
                if info.type is TypeName.VOID:
                    erro(se.SemanticErrorKind.VOID_VARIABLE,
                         f"A variável {info.name} não pode ser 'void'", info.span)

                if info.initializer is not None:
                    res = tipo_valor(info.initializer)
                    esperado = tipo_da_variavel(info.metadata.get("symbol"))

                    if res is not UNKNOWN and esperado is not UNKNOWN and res is not esperado:
                        erro(se.SemanticErrorKind.INITIALIZER_TYPE_MISMATCH,
                             f"Tipo do inicializador da variável {info.name} deve ser "
                             f"{esperado.value}, porém é {res.value}",
                             info.initializer.span)

            case Assignment():
                bottom_up_type_resolving(info.target)   # anota o tipo do alvo
                res_tgt = tipo_da_variavel(info.target.metadata.get("symbol"))
                res_val = tipo_valor(info.value)

                if res_tgt is not UNKNOWN and res_val is not UNKNOWN and res_tgt is not res_val:
                    erro(se.SemanticErrorKind.ASSIGNMENT_TYPE_MISMATCH,
                         f"A variável {info.target.name} espera receber {res_tgt.value} "
                         f"e não {res_val.value}",
                         info.value.span)

            case CallStmt():
                # chamada como comando: qualquer retorno (inclusive void) é aceito
                bottom_up_type_resolving(info.call)

            # precisamos enviar aos blocos internos a informação do retorno esperado, caso tenha uma ReturnStmt lá
            case IfStmt():
                res_cnd = tipo_valor(info.condition)
                if res_cnd is not UNKNOWN and res_cnd is not TypeName.BOOL:
                    erro(se.SemanticErrorKind.CONDITION_TYPE_MISMATCH,
                         "Condição de If Statement deve ser do tipo bool",
                         info.condition.span)

                bottom_up_type_resolving(info.then_block, current_func_return)
                if info.else_block is not None:
                    bottom_up_type_resolving(info.else_block, current_func_return)

            case WhileStmt():
                res_cnd = tipo_valor(info.condition)
                if res_cnd is not UNKNOWN and res_cnd is not TypeName.BOOL:
                    erro(se.SemanticErrorKind.CONDITION_TYPE_MISMATCH,
                         "Condição de While Statement deve ser do tipo bool",
                         info.condition.span)

                bottom_up_type_resolving(info.body, current_func_return)

            case ReturnStmt():
                if current_func_return is TypeName.VOID:
                    # não era pra ter retorno, mas tem
                    if info.value is not None:
                        bottom_up_type_resolving(info.value)   # ainda procura erros internos
                        erro(se.SemanticErrorKind.RETURN_MISMATCH,
                             "Função void não deve retornar valores", info.value.span)
                elif info.value is None:
                    # era pra ter retorno mas não tem
                    erro(se.SemanticErrorKind.RETURN_MISMATCH,
                         f"Função exige retorno do tipo {current_func_return.value}",
                         info.span)
                else:
                    # era pra ter retorno e tem, mas pode ser do tipo errado
                    res = tipo_valor(info.value)
                    if res is not UNKNOWN and res is not current_func_return:
                        erro(se.SemanticErrorKind.RETURN_MISMATCH,
                             f"Retorno inválido. Esperado {current_func_return.value}, "
                             f"recebido {res.value}",
                             info.value.span)

            case PrintStmt():
                for i in info.items:
                    # strings não recebem 'type'; só expressões são verificadas
                    if isinstance(i, (BinaryExpr, UnaryExpr, CallExpr, IdentifierExpr,
                                      IntLiteral, BoolLiteral)):
                        tipo_valor(i)

            # expressions
            case BinaryExpr():
                # ambos os lados são sempre visitados
                left = tipo_valor(info.left)
                right = tipo_valor(info.right)

                if left is UNKNOWN or right is UNKNOWN:
                    return UNKNOWN

                # em ordem: verificação de OK, resultado da operação e tipo exigido
                op = info.operator
                if op in ARITMETICOS:
                    ok, res, exig = (left is TypeName.INT and right is TypeName.INT), TypeName.INT, "int"
                elif op in RELACIONAIS:
                    ok, res, exig = (left is TypeName.INT and right is TypeName.INT), TypeName.BOOL, "int"
                elif op in IGUALDADE:
                    ok, res, exig = (left is right), TypeName.BOOL, "dois int ou dois bool"
                elif op in LOGICOS:
                    ok, res, exig = (left is TypeName.BOOL and right is TypeName.BOOL), TypeName.BOOL, "bool"
                else:
                    return UNKNOWN

                # criando comentário de erro com as informações acima
                if not ok:
                    erro(se.SemanticErrorKind.INVALID_BINARY_OPERANDS,
                         f"Operandos de '{op.value}' devem ser {exig}, recebidos "
                         f"{left.value} e {right.value}",
                         info.span)
                    return UNKNOWN

                return anota(info, res)

            case UnaryExpr():
                res = tipo_valor(info.operand)
                if res is UNKNOWN:
                    return UNKNOWN

                # '-' só aceita INT
                if info.operator is UnaryOperator.NEGATE and res is not TypeName.INT:
                    erro(se.SemanticErrorKind.INVALID_UNARY_OPERAND,
                         "Operador '-' exige tipo int", info.span)
                    return UNKNOWN

                # '!' só aceita BOOL
                if info.operator is UnaryOperator.NOT and res is not TypeName.BOOL:
                    erro(se.SemanticErrorKind.INVALID_UNARY_OPERAND,
                         "Operador '!' exige tipo bool", info.span)
                    return UNKNOWN

                return anota(info, res)

            case CallExpr():
                func_sym = info.metadata.get("symbol")
                expected_types = func_sym.parameter_types if func_sym else ()

                # só anota o erro, não dá return para não pular os argumentos
                if func_sym and len(info.arguments) != len(expected_types):
                    erro(se.SemanticErrorKind.ARITY_MISMATCH,
                         f"Número incorreto de argumentos: passados {len(info.arguments)}, "
                         f"esperados {len(expected_types)}",
                         info.span)

                for i, a in enumerate(info.arguments):
                    res_arg = tipo_valor(a)
                    if res_arg is not UNKNOWN and i < len(expected_types) \
                            and expected_types[i] is not TypeName.VOID \
                            and res_arg is not expected_types[i]:
                        erro(se.SemanticErrorKind.ARGUMENT_TYPE_MISMATCH,
                             f"Argumento {i + 1} de {info.name} espera "
                             f"{expected_types[i].value} e não {res_arg.value}",
                             a.span)

                if not func_sym:
                    return UNKNOWN
                # o tipo da chamada é o retorno declarado (mesmo com erro nos argumentos)
                return anota(info, func_sym.type)

            case IdentifierExpr():
                # buscar a sua declaração para saber o tipo
                sym = info.metadata.get("symbol")
                if sym is None:
                    return UNKNOWN
                if sym.type is TypeName.VOID:
                    # variável/parâmetro void já foi reportado na declaração
                    return UNKNOWN
                return anota(info, sym.type)

            case IntLiteral():
                # checar limite (apenas positivo, pois o '-' é um operador separado)
                if info.value > INT_MAX:
                    erro(se.SemanticErrorKind.INTEGER_LITERAL_OUT_OF_RANGE,
                         "Literal inteiro fora do limite permitido (0 a 2^63-1)",
                         info.span)
                    return UNKNOWN
                return anota(info, TypeName.INT)

            case BoolLiteral():
                return anota(info, TypeName.BOOL)

        return None

    # "main" = rodando realmente a função declarada acima
    bottom_up_type_resolving(program)

    if erros:
        raise se.SemanticError(erros)
