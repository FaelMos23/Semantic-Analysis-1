from __future__ import annotations

from collections.abc import Sequence

from Lexer import Token, TokenKind
from ast_nodes import (
    Block,
    Expr,
    FunctionDecl,
    Node,
    Parameter,
    PrintItem,
    Program,
    SourceSpan,
    Stmt,
    StringLiteral,
    TypeName,
    # Luiza
    IdentifierExpr,
    Assignment,
    CallExpr,
    CallStmt,
    VarDecl,
    IfStmt,
    # Rafael
    WhileStmt,
    ReturnStmt,
    PrintStmt,
    BinaryExpr,
    BinaryOperator,
    # Maria
    UnaryExpr,
    UnaryOperator,
    IntLiteral,
    BoolLiteral,
)


TYPE_START = {TokenKind.KW_INT, TokenKind.KW_BOOL, TokenKind.KW_VOID}
EXPRESSION_START = {
    TokenKind.IDENTIFIER,
    TokenKind.INT_LITERAL,
    TokenKind.KW_FALSE,
    TokenKind.KW_TRUE,
    TokenKind.LEFT_PAREN,
    TokenKind.LOGICAL_NOT,
    TokenKind.MINUS,
}
STATEMENT_START = TYPE_START | {
    TokenKind.IDENTIFIER,
    TokenKind.KW_IF,
    TokenKind.KW_WHILE,
    TokenKind.KW_RETURN,
    TokenKind.KW_PRINT,
    TokenKind.LEFT_BRACE,
}


TYPE_BY_TOKEN = {
    TokenKind.KW_INT: TypeName.INT,
    TokenKind.KW_BOOL: TypeName.BOOL,
    TokenKind.KW_VOID: TypeName.VOID,
}


class ParserError(Exception):
    def __init__(self, token: Token, expected: set[TokenKind]):
        self.token = token
        self.expected = frozenset(expected)
        super().__init__()

    @property
    def line(self) -> int:
        return self.token.line

    @property
    def column(self) -> int:
        return self.token.column

    def __str__(self) -> str:
        names = ", ".join(kind.name for kind in sorted(
            self.expected,
            key=lambda kind: kind.value,
        ))
        return (
            f"erro sintático em {self.line}:{self.column}: esperado {{{names}}}, "
            f"encontrado {self.token.kind.name} ({self.token.lexeme!r})"
        )


class Parser:
    def __init__(self, tokens: Sequence[Token]):
        self.tokens = list(tokens)
        if not self.tokens:
            raise ValueError("a sequência de tokens deve terminar em EOF")
        if self.tokens[-1].kind is not TokenKind.EOF:
            raise ValueError("o último token deve ser EOF")
        if any(token.kind is TokenKind.EOF for token in self.tokens[:-1]):
            raise ValueError("EOF deve aparecer uma única vez, no final")
        self.current = 0

    def peek(self, offset: int = 0) -> Token:
        index = min(self.current + offset, len(self.tokens) - 1)
        return self.tokens[index]

    def check(self, kind: TokenKind) -> bool:
        return self.peek().kind is kind

    def advance(self) -> Token:
        token = self.peek()
        if self.current < len(self.tokens) - 1:
            self.current += 1
        return token

    def match(self, *kinds: TokenKind) -> Token | None:
        if self.peek().kind in kinds:
            return self.advance()
        return None

    def expect(self, kinds: TokenKind | set[TokenKind]) -> Token:
        expected = kinds if isinstance(kinds, set) else {kinds}
        token = self.peek()
        if token.kind not in expected:
            raise ParserError(token, set(expected))
        return self.advance()

    @staticmethod
    def _token_span(token: Token) -> SourceSpan:
        return SourceSpan(
            token.line,
            token.column,
            token.line,
            token.column + len(token.lexeme),
        )

    @staticmethod
    def _start(value: Token | Node) -> tuple[int, int]:
        if isinstance(value, Node):
            return value.span.start_line, value.span.start_column
        return value.line, value.column

    @staticmethod
    def _end(value: Token | Node) -> tuple[int, int]:
        if isinstance(value, Node):
            return value.span.end_line, value.span.end_column
        return value.line, value.column + len(value.lexeme)

    @classmethod
    def _span(cls, first: Token | Node, last: Token | Node) -> SourceSpan:
        start_line, start_column = cls._start(first)
        end_line, end_column = cls._end(last)
        return SourceSpan(start_line, start_column, end_line, end_column)

    def parse(self) -> Program:
        return self.parse_program()

    # program ::= function* EOF
    def parse_program(self) -> Program:
        start = self.peek()
        functions: list[FunctionDecl] = []
        while self.peek().kind in TYPE_START:
            functions.append(self.parse_function())
        eof = self.expect(TokenKind.EOF)
        return Program(functions, span=self._span(start, eof))

    # function ::= type IDENTIFIER ... block
    def parse_function(self) -> FunctionDecl:
        start = self.peek()
        return_type = self.parse_type()
        name = self.expect(TokenKind.IDENTIFIER)
        self.expect(TokenKind.LEFT_PAREN)
        parameters = (
            self.parse_parameter_list()
            if self.peek().kind in TYPE_START
            else []
        )
        self.expect(TokenKind.RIGHT_PAREN)
        body = self.parse_block()
        return FunctionDecl(
            return_type,
            name.lexeme,
            parameters,
            body,
            span=self._span(start, body),
        )

    # type ::= KW_INT | KW_BOOL | KW_VOID
    def parse_type(self) -> TypeName:
        token = self.expect(TYPE_START)
        return TYPE_BY_TOKEN[token.kind]

    # LUIZA - próx. 7
    # parameter_list ::= parameter (COMMA parameter)*
    def parse_parameter_list(self) -> list[Parameter]:
        params: list[Parameter] = []
        hasNext = True

        while hasNext:
            params.append(self.parse_parameter())
            if self.check(TokenKind.RIGHT_PAREN):   # fim da lista de parâmetros
                hasNext = False
            else:
                self.expect(TokenKind.COMMA)        # continuação da lista de parâmetros

        return params
    
    # parameter ::= type IDENTIFIER
    def parse_parameter(self) -> Parameter:
        start = self.peek()
        t = self.parse_type()
        end = self.expect(TokenKind.IDENTIFIER)

        return Parameter(
            t,
            end.lexeme,
            span= self._span(start, end)
        )
    
    # block ::= LEFT_BRACE statement* RIGHT_BRACE
    def parse_block(self) -> Block:
        start = self.expect(TokenKind.LEFT_BRACE)

        # similar a como o programa trata funções
        bloco: list[Stmt] = []

        hasNext = True
        while hasNext:
            next_elem = self.peek()

            if next_elem.kind in STATEMENT_START:        # ainda há pelo menos mais uma statement
                bloco.append(self.parse_statement())
            else:
                hasNext = False                     # fim das statements
                end = self.expect(TokenKind.RIGHT_BRACE)

        return Block(
            bloco,
            span=self._span(start, end)
        )

    # statement ::= declaration | id_or_call_statement | if_statement | while_statement | return_statement | print_statement | block
    def parse_statement(self) -> Stmt:
        # usar switch case?

        match(self.peek().kind):
            case TokenKind.KW_IF:
                return self.parse_if_statement()

            case TokenKind.KW_WHILE:
                return self.parse_while_statement()
            
            case TokenKind.KW_RETURN:
                return self.parse_return_statement()
            
            case TokenKind.KW_PRINT:
                return self.parse_print_statement()
            
            case TokenKind.LEFT_BRACE:
                return self.parse_block()

            case _:
                # se não é nenhuma acima, pode ser declaração, que começa com 'type'
                if self.peek().kind in TYPE_START:
                    return self.parse_declaration()

                # última opção é id_or_call, que começa com IDENTIFIER
                if self.check(TokenKind.IDENTIFIER):
                    return self.parse_id_or_call_statement()

    # id_or_call_statement ::= IDENTIFIER (ASSIGN expression | LEFT_PAREN arguments RIGHT_PAREN) SEMICOLON
    def parse_id_or_call_statement(self) -> Stmt:
        id_token = self.expect(TokenKind.IDENTIFIER)

        exp_or_args = self.peek()
        if exp_or_args.kind == TokenKind.ASSIGN:
            self.advance()
            
            # valor atribuído
            value_node = self.parse_expression()
            end_token = self.expect(TokenKind.SEMICOLON)

            # Assignments(target[IdentifierExpr], value)
            target_node = IdentifierExpr(
                id_token.lexeme, 
                span=self._token_span(id_token)
            )

            return Assignment(
                target_node,
                value_node,
                span=self._span(id_token, end_token)
            )

        elif exp_or_args.kind == TokenKind.LEFT_PAREN:
            self.advance()
            
            args = self.parse_arguments()
            r_paren = self.expect(TokenKind.RIGHT_PAREN)
            end_token = self.expect(TokenKind.SEMICOLON)

            # CallStmt(call[CallExpr])
            call_expr = CallExpr(
                id_token.lexeme,
                args,
                span=self._span(id_token, r_paren)
            )

            return CallStmt(
                call= call_expr,
                span= self._span(id_token, end_token)
            )

        else:
            raise ParserError(exp_or_args, {TokenKind.ASSIGN, TokenKind.LEFT_PAREN})

    # declaration ::= type IDENTIFIER (ASSIGN expression)? SEMICOLON
    def parse_declaration(self) -> Stmt:
        start_token = self.expect(TYPE_START)
        
        decl_type = TYPE_BY_TOKEN[start_token.kind]

        id_token = self.expect(TokenKind.IDENTIFIER)

        poss_expr = None

        # checando possível expressão
        if self.peek().kind == TokenKind.ASSIGN:
            self.advance()
            poss_expr = self.parse_expression()

        end_token = self.expect(TokenKind.SEMICOLON)

        return VarDecl(
            type=decl_type,
            name=id_token.lexeme,
            initializer=poss_expr,
            span=self._span(start_token, end_token)
        )

    # if_statement ::= KW_IF LEFT_PAREN expression RIGHT_PAREN block (KW_ELSE block)?
    def parse_if_statement(self) -> Stmt:
        start = self.expect(TokenKind.KW_IF)

        # (cond)
        self.expect(TokenKind.LEFT_PAREN)
        cond = self.parse_expression()
        self.expect(TokenKind.RIGHT_PAREN)

        # {then_block}
        then_block = self.parse_block()
        end = self.peek(-1)

        # possível existênca do bloco else
        else_block = None
        if self.peek().kind == TokenKind.KW_ELSE:
            self.advance()
            else_block = self.parse_block()
            end = self.peek(-1)

        return IfStmt(
            condition= cond,
            then_block= then_block,
            else_block= else_block,
            span= self._span(start, end)
        )

    # RAFAEL - próx. 8
    # while_statement ::= KW_WHILE LEFT_PAREN expression RIGHT_PAREN block
    def parse_while_statement(self) -> Stmt:
        start = self.expect(TokenKind.KW_WHILE)

        # (cond)
        self.expect(TokenKind.LEFT_PAREN)
        cond = self.parse_expression()
        self.expect(TokenKind.RIGHT_PAREN)

        # {block}
        body = self.parse_block()
        end = self.peek(-1)

        return WhileStmt(
            condition= cond,
            body= body,
            span= self._span(start, end)
        )

    # return_statement ::= KW_RETURN expression? SEMICOLON
    def parse_return_statement(self) -> Stmt:
        start = self.expect(TokenKind.KW_RETURN)

        if self.peek().kind != TokenKind.SEMICOLON:
            val = self.parse_expression()
        else: val = None

        end = self.expect(TokenKind.SEMICOLON)

        return ReturnStmt(
            value= val,
            span= self._span(start, end)
        )

    # print_statement ::= KW_PRINT LEFT_PAREN print_item (COMMA print_item)* RIGHT_PAREN SEMICOLON
    def parse_print_statement(self) -> Stmt:
        start = self.expect(TokenKind.KW_PRINT)
        items: list[PrintItem] = []

        self.expect(TokenKind.LEFT_PAREN)

        items.append(self.parse_print_item())

        while self.peek().kind == TokenKind.COMMA:
            self.advance()
            items.append(self.parse_print_item())

        self.expect(TokenKind.RIGHT_PAREN)

        end = self.expect(TokenKind.SEMICOLON)
        
        return PrintStmt(
            items= items,
            span= self._span(start, end)
        )

    # print_item ::= expression | string_literals
    def parse_print_item(self) -> PrintItem:
        start = self.peek()

        if start.kind in EXPRESSION_START:
            return self.parse_expression()
        else:
            return self.parse_string_literals()

    # string_literals ::= STRING_LITERAL+
    def parse_string_literals(self) -> StringLiteral:
        start = self.expect(TokenKind.STRING_LITERAL)
        curr_total_str = start.value
        end = start

        while self.peek().kind == TokenKind.STRING_LITERAL:
            end = self.advance()
            curr_total_str += end.value

        return StringLiteral(
            curr_total_str,
            span=self._span(start, end)
        )

    # expression ::= logical_or
    def parse_expression(self) -> Expr:
        return self.parse_logical_or()

# logical_or ::= logical_and (LOGICAL_OR logical_and)*
    def parse_logical_or(self) -> Expr:
        e = self.parse_logical_and()

        # adicionando 2° e outras partes lógicas, se existirem
        while self.peek().kind == TokenKind.LOGICAL_OR:
            self.advance()
            
            # direita
            right_e = self.parse_logical_and()
            
            # cria expressão binária com informações acima e o resultado se torna o 'e' do próximo loop
            e = BinaryExpr(
                operator=BinaryOperator.LOGICAL_OR,
                left=e,
                right=right_e,
                span=self._span(e, right_e) # _span aceita Nodes além de Tokens
            )

        return e

    # logical_and ::= equality (LOGICAL_AND equality)*
    def parse_logical_and(self) -> Expr:
        e = self.parse_equality()

        # adicionando 2° e outras partes lógicas, se existirem
        while self.peek().kind == TokenKind.LOGICAL_AND:
            self.advance()
            
            # direita
            right_e = self.parse_equality()
            
            # cria expressão binária com informações acima e o resultado se torna o 'e' do próximo loop
            e = BinaryExpr(
                operator=BinaryOperator.LOGICAL_AND,
                left=e,
                right=right_e,
                span=self._span(e, right_e) # _span aceita Nodes além de Tokens
            )

        return e

    # MARIA - próx. 7
    # equality ::= relational ((EQUAL_EQUAL | NOT_EQUAL) relational)*
    def parse_equality(self) -> Expr:
        e = self.parse_relational()

        # adicionando 2° e outras partes lógicas, se existirem
        while self.peek().kind == TokenKind.EQUAL_EQUAL or self.peek().kind == TokenKind.NOT_EQUAL:
            cmp = self.advance().kind
            
            # direita
            right_e = self.parse_relational()

            ops = {TokenKind.EQUAL_EQUAL: BinaryOperator.EQUAL, TokenKind.NOT_EQUAL: BinaryOperator.NOT_EQUAL}
            
            # cria expressão binária com informações acima e o resultado se torna o 'e' do próximo loop
            e = BinaryExpr(
                operator=ops[cmp],
                left=e,
                right=right_e,
                span=self._span(e, right_e) # _span aceita Nodes além de Tokens
            )

        return e

    # relational ::= additive ((LESS | LESS_EQUAL | GREATER | GREATER_EQUAL) additive)*
    def parse_relational(self) -> Expr:
        e = self.parse_additive()

        # adicionando 2° e outras partes lógicas, se existirem
        while self.peek().kind == TokenKind.LESS or self.peek().kind == TokenKind.LESS_EQUAL or self.peek().kind == TokenKind.GREATER or self.peek().kind == TokenKind.GREATER_EQUAL:
            cmp = self.advance().kind
            
            # direita
            right_e = self.parse_additive()

            ops = {TokenKind.LESS: BinaryOperator.LESS, TokenKind.LESS_EQUAL: BinaryOperator.LESS_EQUAL, TokenKind.GREATER: BinaryOperator.GREATER, TokenKind.GREATER_EQUAL: BinaryOperator.GREATER_EQUAL}
            
            # cria expressão binária com informações acima e o resultado se torna o 'e' do próximo loop
            e = BinaryExpr(
                operator=ops[cmp],
                left=e,
                right=right_e,
                span=self._span(e, right_e) # _span aceita Nodes além de Tokens
            )

        return e

    # additive ::= multiplicative ((PLUS | MINUS) multiplicative)*
    def parse_additive(self) -> Expr:
        e = self.parse_multiplicative()

        # adicionando 2° e outras partes lógicas, se existirem
        while self.peek().kind == TokenKind.PLUS or self.peek().kind == TokenKind.MINUS:
            cmp = self.advance().kind
            
            # direita
            right_e = self.parse_multiplicative()

            ops = {TokenKind.PLUS: BinaryOperator.ADD, TokenKind.MINUS: BinaryOperator.SUBTRACT}
            
            # cria expressão binária com informações acima e o resultado se torna o 'e' do próximo loop
            e = BinaryExpr(
                operator=ops[cmp],
                left=e,
                right=right_e,
                span=self._span(e, right_e) # _span aceita Nodes além de Tokens
            )

        return e

    # multiplicative ::= unary ((STAR | SLASH | PERCENT) unary)*
    def parse_multiplicative(self) -> Expr:
        e = self.parse_unary()

        # adicionando 2° e outras partes lógicas, se existirem
        while self.peek().kind == TokenKind.STAR or self.peek().kind == TokenKind.SLASH or self.peek().kind == TokenKind.PERCENT:
            cmp = self.advance().kind
            
            # direita
            right_e = self.parse_unary()

            ops = {TokenKind.STAR: BinaryOperator.MULTIPLY, TokenKind.SLASH: BinaryOperator.DIVIDE, TokenKind.PERCENT: BinaryOperator.REMAINDER}
            
            # cria expressão binária com informações acima e o resultado se torna o 'e' do próximo loop
            e = BinaryExpr(
                operator=ops[cmp],
                left=e,
                right=right_e,
                span=self._span(e, right_e) # _span aceita Nodes além de Tokens
            )

        return e

    # unary ::= (LOGICAL_NOT | MINUS) unary | primary
    def parse_unary(self) -> Expr:
        if self.peek().kind == TokenKind.LOGICAL_NOT or self.peek().kind == TokenKind.MINUS:
            ue = self.advance()
            operand = self.parse_unary()

            ops = {TokenKind.LOGICAL_NOT: UnaryOperator.NOT, TokenKind.MINUS: UnaryOperator.NEGATE}

            return UnaryExpr(
                operator= ops[ue.kind],
                operand= operand,
                span= self._span(ue, operand)
            )

        else:
            return self.parse_primary()

    # primary ::= LEFT_PAREN expression RIGHT_PAREN | IDENTIFIER (LEFT_PAREN arguments RIGHT_PAREN)? | INT_LITERAL | KW_TRUE | KW_FALSE
    def parse_primary(self) -> Expr:
        start = self.peek()

        poss_tok = {TokenKind.INT_LITERAL, TokenKind.KW_TRUE, TokenKind.KW_FALSE}

        if start.kind == TokenKind.LEFT_PAREN:
            self.advance()
            exp = self.parse_expression()
            self.expect(TokenKind.RIGHT_PAREN)

            return exp 
        
        elif start.kind == TokenKind.IDENTIFIER:
            id = self.advance()

            # é função?
            if self.peek().kind == TokenKind.LEFT_PAREN:
                self.advance()
                args = self.parse_arguments()
                r_paren = self.expect(TokenKind.RIGHT_PAREN)
                
                return CallExpr(
                    name=id.lexeme,
                    arguments=args,
                    span=self._span(id, r_paren)
                )

            # se não for função, é variável
            return IdentifierExpr(
                name=id.lexeme,
                span=self._span(id, id)
            )

        else:
            t = self.expect(poss_tok)
            match(t.kind):
                case TokenKind.INT_LITERAL:
                    return IntLiteral(
                        value= t.value,
                        span= self._span(t, t)
                    )
                case TokenKind.KW_TRUE:
                    return BoolLiteral(
                        value= t.value,
                        span= self._span(t, t)
                    )
                case TokenKind.KW_FALSE:
                    return BoolLiteral(
                        value= t.value,
                        span= self._span(t, t)
                    )

    # arguments ::= (expression (COMMA expression)*)?
    def parse_arguments(self) -> list[Expr]:
        exprs: list[Expr] = []

        if self.peek().kind in EXPRESSION_START:
            exprs.append(self.parse_expression())

            while self.peek().kind ==  TokenKind.COMMA:
                self.advance()
                exprs.append(self.parse_expression())

        return exprs