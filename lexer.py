# lexer.py
import re

TOKENS = [
    ('COMMENT', r'//[^\n]*'),
    ('CLASS', r'class'),
    ('IF', r'if'),
    ('ELSE', r'else'),
    ('WHILE', r'while'),
    ('FOR', r'for'),
    ('DO', r'do'),
    ('INT', r'int'),
    ('FLOAT', r'float'),
    ('CHAR', r'char'),
    ('RETURN', r'return'),
    ('FLOAT_NUMBER', r'\d+\.\d+'),
    ('NUMBER', r'\d+'),
    ('CHAR_LITERAL', r'\'[^\']\''),
    ('ID', r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('LPAREN', r'\('),
    ('RPAREN', r'\)'),
    ('LBRACE', r'\{'),
    ('RBRACE', r'\}'),
    ('SEMICOLON', r';'),
    ('COMMA', r','),
    ('PLUS', r'\+'),
    ('MINUS', r'-'),
    ('MULT', r'\*'),
    ('DIV', r'/'),
    ('MOD', r'%'),
    ('EQEQ', r'=='),
    ('NEQ', r'!='),
    ('LTE', r'<='), 
    ('GTE', r'>='),
    ('EQ', r'='),
    ('LT', r'<'),
    ('GT', r'>'),
    ('STRING', r'"[^"]*"'),
    ('DOT', r'\.'),
    ('WS', r'\s+'),
]

class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value
    def __repr__(self):
        return f"Token({self.type}, {self.value})"

def lex(characters):
    pos = 0
    tokens = []
    while pos < len(characters):
        match = None
        for token_type, pattern in TOKENS:
            regex = re.compile(pattern)
            match = regex.match(characters, pos)
            if match:
                text = match.group(0)
                if token_type == 'COMMENT':
                    pos = match.end(0)
                    continue
                if token_type != 'WS':
                    if token_type == 'STRING':
                        text = text[1:-1]
                    elif token_type == 'CHAR_LITERAL':
                        text = text[1:-1]
                    tokens.append(Token(token_type, text))
                pos = match.end(0)
                break
        if not match:
            raise SyntaxError(f'Illegal character: {characters[pos]}')
    return tokens
