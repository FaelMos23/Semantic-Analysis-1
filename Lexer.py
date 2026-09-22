from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Iterator

import states

class TokenKind(enum.Enum):
    """Classe já implementada: nomes e números não devem ser alterados."""

    EOF = -1

    IDENTIFIER = 1
    INT_LITERAL = 2
    STRING_LITERAL = 3

    KW_INT = 10
    KW_BOOL = 11
    KW_VOID = 12
    KW_TRUE = 13
    KW_FALSE = 14
    KW_IF = 15
    KW_ELSE = 16
    KW_WHILE = 17
    KW_RETURN = 18
    KW_PRINT = 19

    PLUS = 20
    MINUS = 21
    STAR = 22
    SLASH = 23
    PERCENT = 24
    LESS = 25
    LESS_EQUAL = 26
    GREATER = 27
    GREATER_EQUAL = 28
    EQUAL_EQUAL = 29
    NOT_EQUAL = 30
    LOGICAL_AND = 31
    LOGICAL_OR = 32
    LOGICAL_NOT = 33
    ASSIGN = 34

    LEFT_PAREN = 40
    RIGHT_PAREN = 41
    LEFT_BRACE = 42
    RIGHT_BRACE = 43
    COMMA = 44
    SEMICOLON = 45


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    lexeme: str
    value: int | str | bool | None
    line: int
    column: int

    def __str__(self) -> str:
        return (
            f"<{self.kind.value}, {self.kind.name}, {self.lexeme!r}, "
            f"{self.value!r}, {self.line}, {self.column}>"
        )


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def __str__(self) -> str:
        return f"erro léxico em {self.line}:{self.column}: {self.message}"


class Lexer:
    """Converte texto-fonte MicroC em uma sequência de tokens."""

    def __init__(self, source: str):
        self.source = source
        # TODO: inicialize aqui o estado exigido por sua estratégia.
        self.reserved_words = {"int", "bool", "void", "true", "false", "if", "else", "while", "return", "print"}
        self.known_tokens = {
            '&': TokenKind.IDENTIFIER,
            '|': TokenKind.INT_LITERAL,
            '[': TokenKind.STRING_LITERAL,
            "int" : TokenKind.KW_INT,
            "bool" : TokenKind.KW_BOOL,
            "void" : TokenKind.KW_VOID,
            "true" : TokenKind.KW_TRUE,
            "false" : TokenKind.KW_FALSE,
            "if" : TokenKind.KW_IF,
            "else" : TokenKind.KW_ELSE,
            "while" : TokenKind.KW_WHILE,
            "return" : TokenKind.KW_RETURN,
            "print" : TokenKind.KW_PRINT,
            "+" : TokenKind.PLUS,
            "-" : TokenKind.MINUS,
            "*" : TokenKind.STAR,
            "/" : TokenKind.SLASH,
            "%" : TokenKind.PERCENT,
            "<" : TokenKind.LESS,
            "<=" : TokenKind.LESS_EQUAL,
            ">" : TokenKind.GREATER,
            ">=" : TokenKind.GREATER_EQUAL,
            "==" : TokenKind.EQUAL_EQUAL,
            "!=" : TokenKind.NOT_EQUAL,
            "&&" : TokenKind.LOGICAL_AND,
            "||" : TokenKind.LOGICAL_OR,
            "!" : TokenKind.LOGICAL_NOT,
            "=" : TokenKind.ASSIGN,
            "(" : TokenKind.LEFT_PAREN,
            ")" : TokenKind.RIGHT_PAREN,
            "{" : TokenKind.LEFT_BRACE,
            "}" : TokenKind.RIGHT_BRACE,
            "," : TokenKind.COMMA,
            ";" : TokenKind.SEMICOLON
        }
        self.st_mac = states.StateMachine()


    def tokens(self) -> Iterator[Token]:
        """Produza todos os tokens significativos e um único EOF ao final."""
        word = ""
        line = 1
        column = 1
        initial_line = 1
        initial_col = 1
        initial_idx = 0
        next_token = False
        skippables = {' ', '\n', '\t', '\r'}

        self.source += ' '  # added that because we check for next character to make sure that a token is complete

        # Use enumerate to get an absolute index for safe string slicing
        for idx, c in enumerate(self.source):
            redo = True
            
            while redo:
                redo = False
                valid, complete_token, info = self.st_mac.transition(c)

                if valid:
                    # Capture token start position precisely when leaving INITIAL state
                    if self.st_mac.currState != states.States.INITIAL and next_token:
                        initial_line = line
                        initial_col = column
                        initial_idx = idx
                        next_token = False

                    if complete_token:
                        key = 0
                        
                        if next_token and c not in skippables:
                            initial_line = line
                            initial_col = column
                            initial_idx = idx
                            next_token = False

                        if (len(info) > 0 and info[0] == '&') or (len(info) > 2 and info[1] == '&'):    
                            word = self.source[initial_idx : idx]
                        else:
                            word = self.source[initial_idx : idx + 1]

                        if len(info) > 2 and (info[1] == '&' or info[1] == ' '): 
                            if info[2] == '|':      
                                value = int(word)
                                key = info[2]   
                            elif info[2] == '[':    
                                value = bytes(word[1:-1], "utf-8").decode("unicode_escape") # value of string literals has \n an endline
                                key = info[2]
                            else:                   
                                if word in self.reserved_words:
                                    key = word
                                    if word == 'true':
                                        value = True
                                    elif word == 'false':
                                        value = False
                                    else:
                                        value = None
                                else:
                                    key = info[2]
                                    value = word
                        else:
                            value = None

                        if key == 0:
                            if len(word) == 0:
                                word = c
                            key = word
                            
                        tok = Token(self.known_tokens[key], word, value, initial_line, initial_col)
                        yield(tok)
                        word = ""
                        next_token = True
                    else:
                        if info == "NEXT":
                            next_token = True
                        elif next_token and c not in [' ', '\n', '\t', '\r']:
                            initial_line = line
                            initial_col = column
                            initial_idx = idx
                            next_token = False
                else:
                    if c == '\n':
                        err_col = column 
                    elif self.st_mac.currState == states.States.STRING_SLASH:   # only allows \n, \t, \\, \"
                        err_col = column - 1
                    elif next_token:    # if this is true when the error occurs, there is a non-recognized character
                        err_col = column
                    else:   # middle of a token errors, like '&' or '|'
                        err_col = initial_col
                        
                    raise LexerError(info, line, err_col)

                redo = len(info) > 0 and info[0] == '&'

            if c == '\n':
                line += 1
                column = 1
            else:
                column += 1

        if self.st_mac.currState in (states.States.BLOCK_COMMENT, states.States.POSS_END_BLOCK_COMMENT, states.States.STRING_LITERAL, states.States.STRING_SLASH):
            raise LexerError("Unclosed token at EOF", initial_line, initial_col)
  
        yield Token(TokenKind["EOF"], "", None, line, column-1)

    def scan(self) -> list[Token]:
        return list(self.tokens())