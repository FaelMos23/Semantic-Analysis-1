import enum

# POSS nos nomes de estados significa 'possível'

class States(enum.Enum):
    INITIAL = 1

    # Comments
    POSS_COMMENT = 2
    LINE_COMMENT = 3
    BLOCK_COMMENT = 4
    POSS_END_BLOCK_COMMENT = 5

    # Operators
    POSS_EQUAL_EQUAL = 6
    POSS_LESS_EQUAL = 7
    POSS_GREATER_EQUAL = 8
    POSS_NOT_EQUAL = 9
    POSS_LOGICAL_AND = 10
    POSS_LOGICAL_OR = 11

    # Identifiers and Literals
    IDENTIFIER = 12       # Handles both variable names AND reserved words
    INT_LITERAL = 13
    STRING_LITERAL = 14
    STRING_SLASH = 15


class StateMachine:
    def __init__(self):
        self.currState = States.INITIAL
        self.complete_token = False
        self.single_definition = {'+', '-', '*', '%', '(', ')', '{', '}', ',', ';', 'EOF'}
        self.valid = True

    def isAlpha(self, c):
        if (ord('a') <= ord(c) <= ord('z')) or (ord('A') <= ord(c) <= ord('Z')) or c == '_':
            return True
        return False

    def isNum(self, c):
        if ord('0') <= ord(c) <= ord('9'):
            return True
        return False

    def transition(self, c: chr):   # returns a list:  [valid: bool, complete_token: bool, info: str]
                                    # some symbols are used on info:
                                    #                               - info[0] == '&' means redo last character

                                    #                               - info[1] == '&' means is one of the three below
                                    #                               - info[2] == '&' means identifier
                                    #                               - info[2] == '|' means int_literal
                                    #                               - info[2] == '[' means string_literal
        self.valid = True
        self.complete_token = False
        if ord(c) > 127: # not ASCII
            return [False, False, "Not ASCII character"]


        match(self.currState):
            case States.INITIAL:
                match(c):
                    case ' ' | '\t' | '\r':   # skip through ALL spaces
                        return [True, False, "NEXT"]
                    case '\n':   # skip through new_lines
                        return [True, False, "NEXT"]
                    case '/':
                        self.currState = States.POSS_COMMENT
                    case '=':
                        self.currState = States.POSS_EQUAL_EQUAL
                    case '<':
                        self.currState = States.POSS_LESS_EQUAL
                    case '>':
                        self.currState = States.POSS_GREATER_EQUAL
                    case '!':
                        self.currState = States.POSS_NOT_EQUAL
                    case '&':
                        self.currState = States.POSS_LOGICAL_AND
                    case '|':
                        self.currState = States.POSS_LOGICAL_OR
                    case '\"':
                        self.currState = States.STRING_LITERAL
                    case _: # default
                        if c in self.single_definition:
                            return [True, True, c]
                        elif self.isAlpha(c):
                            self.currState = States.IDENTIFIER
                        elif self.isNum(c):
                            self.currState = States.INT_LITERAL
                        else:
                            return [False, False, "Not a recognized start of token"]
                return [True, False, ""]
            case States.POSS_COMMENT:
                match(c):
                    case '/':
                        self.currState = States.LINE_COMMENT
                    case '*':
                        self.currState = States.BLOCK_COMMENT
                    case _: # division
                        self.currState = States.INITIAL
                        return [True, True, "&"]
                return [True, False, ""]

            case States.LINE_COMMENT:
                if c == '\n':
                    self.currState = States.INITIAL
                    return [True, False, "NEXT"] # Flag that a comment ended
                return [True, False, ""]
            
            case States.BLOCK_COMMENT:
                if c == '*':
                    self.currState = States.POSS_END_BLOCK_COMMENT
                return [True, False, ""]
            
            case States.POSS_END_BLOCK_COMMENT:
                if c == '/':
                    self.currState = States.INITIAL
                    return [True, False, "NEXT"] # Flag that a comment ended
                else:
                    self.currState = States.BLOCK_COMMENT
                return [True, False, ""]
            
            case States.POSS_EQUAL_EQUAL:
                self.currState = States.INITIAL
                if c == '=':
                    return [True, True, ""]
                else:
                    return [True, True, "&"]    

            case States.POSS_LESS_EQUAL:
                self.currState = States.INITIAL
                if c == '=':
                    return [True, True, ""]
                else:
                    return [True, True, "&"]    

            case States.POSS_GREATER_EQUAL:
                self.currState = States.INITIAL
                if c == '=':
                    return [True, True, ""]
                else:
                    return [True, True, "&"]   

            case States.POSS_NOT_EQUAL:
                self.currState = States.INITIAL
                if c == '=':
                    return [True, True, ""]
                else:
                    return [True, True, "&"]    

            case States.POSS_LOGICAL_AND:
                self.currState = States.INITIAL
                if c == '&':
                    return [True, True, ""]
                else:
                    return [False, False, "Bitwise AND not allowed"]

            case States.POSS_LOGICAL_OR:
                self.currState = States.INITIAL
                if c == '|':
                    return [True, True, ""]
                else:
                    return [False, False, "Bitwise OR not allowed"]

            case States.IDENTIFIER:
                if self.isAlpha(c) or self.isNum(c):
                    return [True, False, ""] 
                elif c == ' ':
                    self.currState = States.INITIAL
                    return [True, True, " &&"]   
                else:
                    self.currState = States.INITIAL
                    return [True, True, "&&&"]  

            case States.INT_LITERAL:
                if self.isNum(c):
                    return [True, False, ""] 
                elif c == ' ':
                    self.currState = States.INITIAL
                    return [True, True, " &|"]
                else:
                    self.currState = States.INITIAL
                    return [True, True, "&&|"]  

            case States.STRING_LITERAL:
                if c == '\"':
                    self.currState = States.INITIAL
                    return [True, True, "  ["]  # Fixed to include closing quote
                elif c == '\\':
                    self.currState = States.STRING_SLASH
                    return [True, False, ""]
                elif c == '\n':
                    return [False, False, "Unclosed string literal"] # newline in string is an error
                else:
                    return [True, False, ""]

            case States.STRING_SLASH:
                poss_next_slash = {'n', 't', '\"', '\\'}
                if c in poss_next_slash:
                    self.currState = States.STRING_LITERAL
                    return [True, False, ""]
                else:
                    return [False, False, "Not accepted: \'\\" + c + "\'"]


        return [False, False, f"missing return in state {self.currState}"]